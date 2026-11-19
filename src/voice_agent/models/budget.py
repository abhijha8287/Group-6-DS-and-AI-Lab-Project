"""Offline, conservative cost reservations for a shared text-only budget."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

try:
    import fcntl
except ImportError:  # No safe cross-process locking on this platform.
    fcntl = None

from voice_agent.utils.common import write_json


class BudgetError(RuntimeError):
    """The ledger is invalid, unavailable, or cannot authorize a request."""


def _money(value):
    if not isinstance(value, str):
        raise BudgetError("Money must be a decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise BudgetError("Invalid money") from exc
    if not amount.is_finite() or amount < 0:
        raise BudgetError("Money must be finite and nonnegative")
    return amount


def _int(value, minimum, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise BudgetError("Invalid integer limit or token count")
    return value


def _price(model):
    if not isinstance(model, dict):
        raise BudgetError("Invalid model catalog entry")
    try:
        return (_money(model["input_usd_per_million"]),
                _money(model["output_usd_per_million"]),
                _int(model["max_input_tokens"], 1))
    except KeyError as exc:
        raise BudgetError("Incomplete model catalog entry") from exc


def max_cost_usd(model: str, max_output_tokens: int, catalog: dict) -> Decimal:
    """Price the entire input context and requested output at uncached rates."""
    try:
        input_price, output_price, max_input = _price(catalog[model])
        _int(max_output_tokens, 1, 1200)
        with localcontext() as ctx:
            prices = (input_price, output_price)
            ctx.prec = max(28, max(p.adjusted() for p in prices) - min(p.as_tuple().exponent for p in prices)
                           + len(str(max_input)) + len(str(max_output_tokens)) + 12)
            return (input_price * max_input + output_price * max_output_tokens) / Decimal(1_000_000)
    except (KeyError, TypeError) as exc:
        raise BudgetError("Unknown model") from exc


def _usage_cost(usage, model, max_output):
    if not isinstance(usage, dict):
        raise BudgetError("Missing usage")
    input_price, output_price, max_input = _price(model)
    try:
        prompt = _int(usage["prompt_tokens"], 0, max_input)
        completion = _int(usage["completion_tokens"], 0, max_output)
    except KeyError as exc:
        raise BudgetError("Missing usage tokens") from exc
    return (input_price * prompt + output_price * completion) / Decimal(1_000_000)


def _limits(batch):
    limits = batch.get("limits")
    if not isinstance(limits, dict):
        raise BudgetError("Missing limits")
    for name, low, high in (("max_requests", 1, 100), ("max_output_tokens", 1, 1200),
                            ("max_request_bytes", 1, 256000), ("max_retries", 0, 1),
                            ("max_caller_turns", 1, 12), ("max_tool_steps", 1, 8),
                            ("max_audio_seconds", 0, 0)):
        if name not in limits:
            raise BudgetError("Missing limit: " + name)
        _int(limits[name], low, high)
    return limits


class CostLedger:
    def __init__(self, path: Path, batch_id: str):
        self.path = Path(path)
        self.batch_id = batch_id

    @contextmanager
    def _locked(self):
        if fcntl is None:
            raise BudgetError("Cross-process locking unavailable")
        try:
            with self.path.with_name(self.path.name + ".lock").open("a") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                try:
                    with localcontext() as ctx:
                        ctx.prec = 256
                        yield
                finally:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except (OSError, InvalidOperation, OverflowError) as exc:
            raise BudgetError("Ledger lock or I/O failed") from exc

    def _save(self, data):
        write_json(self.path, data)
        # A request must not leave the machine before its reservation is durable.
        with self.path.open("rb") as handle:
            os.fsync(handle.fileno())
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _load(self):
        try:
            with self.path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict) or not isinstance(data["models"], dict) or not isinstance(data["allocations"], dict) or not isinstance(data["batches"], list):
                raise BudgetError("Invalid ledger")
            credit = _money(data["starting_credit_usd"])
            allocations = {name: _money(value) for name, value in data["allocations"].items()}
            batches = data["batches"]
            if any(not isinstance(batch, dict) for batch in batches):
                raise BudgetError("Invalid batch")
            ids = [batch.get("id") for batch in batches]
            if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
                raise BudgetError("Invalid batch IDs")
            matches = [batch for batch in batches if batch["id"] == self.batch_id]
            if len(matches) != 1:
                raise BudgetError("Batch not found")
            target = matches[0]
            if target.get("approved") is not True or not isinstance(target.get("approval_reference"), str) or not target["approval_reference"].strip():
                raise BudgetError("Batch is not approved")
            for batch in batches:
                if batch.get("allocation") not in allocations:
                    raise BudgetError("Unknown allocation")
                ceiling = _money(batch["max_cost_usd"])
                if ceiling > allocations[batch["allocation"]] or ceiling > credit:
                    raise BudgetError("Batch ceiling exceeds allocation or credit")
                if batch.get("model") not in data["models"]:
                    raise BudgetError("Unknown model")
                _price(data["models"][batch["model"]])
                _limits(batch)
                if not isinstance(batch.get("requests"), list):
                    raise BudgetError("Invalid requests")
            return data, target, credit, allocations
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BudgetError("Cannot read valid ledger") from exc

    def _totals(self, data, credit):
        recorded = Decimal(0)
        held = Decimal(0)
        batch_costs = {}
        allocation_costs = {name: Decimal(0) for name in data["allocations"]}
        for batch in data["batches"]:
            subtotal = Decimal(0)
            seen = set()
            for request in batch["requests"]:
                if not isinstance(request, dict) or not isinstance(request.get("id"), str) or request["id"] in seen:
                    raise BudgetError("Invalid request entry")
                seen.add(request["id"])
                reservation = _money(request.get("reserve_max_cost_usd"))
                # Never trust a stored reservation smaller than the full-context price.
                maximum = _int(request.get("max_output_tokens"), 1, batch["limits"]["max_output_tokens"])
                required = max_cost_usd(batch["model"], maximum, data["models"])
                if reservation < required:
                    raise BudgetError("Reservation below full-context cost")
                cost = reservation
                if request.get("status") == "reconciled":
                    try:
                        cost = _usage_cost(request.get("usage"), data["models"][batch["model"]], maximum)
                    except BudgetError:
                        held += reservation
                    else:
                        recorded += cost
                else:
                    held += reservation
                subtotal += cost
            batch_costs[batch["id"]] = subtotal
            allocation_costs[batch["allocation"]] += subtotal
        data["totals"] = {"recorded_usage_usd": str(recorded), "unreconciled_max_usd": str(held),
                          "remaining_credit_estimate_usd": str(credit - recorded - held)}
        return batch_costs, allocation_costs, recorded + held

    @property
    def limits(self):
        with self._locked():
            _, batch, _, _ = self._load()
            return dict(_limits(batch))

    def reserve(self, model: str, max_output_tokens: int, request_bytes: int, role: str, attempt: int) -> str:
        with self._locked():
            data, batch, credit, allocations = self._load()
            limits = _limits(batch)
            if any(b.get("halted", False) is not False for b in data["batches"]):
                raise BudgetError("Ledger has a halted batch; billing review is required")
            if model != batch["model"] or role not in ("AGENT", "SIMULATOR", "JUDGE"):
                raise BudgetError("Model or role not permitted")
            _int(max_output_tokens, 1, limits["max_output_tokens"])
            _int(request_bytes, 1, limits["max_request_bytes"])
            _int(attempt, 0, limits["max_retries"])
            if len(batch["requests"]) >= limits["max_requests"]:
                raise BudgetError("Request count exceeded")
            batch_costs, allocation_costs, total = self._totals(data, credit)
            # A lost response or failed halt write must block every later paid send.
            if any(r.get("status") == "pending" for b in data["batches"] for r in b["requests"]):
                raise BudgetError("Pending request requires reconciliation before further paid calls")
            cost = max_cost_usd(model, max_output_tokens, data["models"])
            if (batch_costs[batch["id"]] + cost > _money(batch["max_cost_usd"])
                    or allocation_costs[batch["allocation"]] + cost > allocations[batch["allocation"]]
                    or total + cost > credit):
                raise BudgetError("Budget exceeded")
            request_id = f"{self.batch_id}-{len(batch['requests']) + 1}"
            if any(r["id"] == request_id for r in batch["requests"]):
                raise BudgetError("Duplicate request ID")
            batch["requests"].append({"id": request_id, "model": model, "role": role,
                                      "attempt": attempt, "timestamp": datetime.now(timezone.utc).isoformat(),
                                      "max_output_tokens": max_output_tokens, "request_bytes": request_bytes,
                                      "reserve_max_cost_usd": str(cost), "status": "pending"})
            self._totals(data, credit)
            self._save(data)
            return request_id

    def _finish(self, request_id, usage=None, error_type=None, halt=False):
        with self._locked():
            data, batch, credit, _ = self._load()
            self._totals(data, credit)
            matches = [request for request in batch["requests"] if request["id"] == request_id]
            if len(matches) != 1 or matches[0].get("status") != "pending":
                raise BudgetError("Request not pending")
            request = matches[0]
            error = None
            if error_type is not None:
                request.update(status="failed", error_type=error_type)
                if halt:
                    batch.update(halted=True, halt_reason=error_type)
            else:
                try:
                    _usage_cost(usage, data["models"][batch["model"]], request["max_output_tokens"])
                except BudgetError as exc:
                    request.update(status="failed", error_type="invalid_usage")
                    batch.update(halted=True, halt_reason="invalid_usage")
                    error = exc
                else:
                    request.update(status="reconciled", usage={"prompt_tokens": usage["prompt_tokens"],
                                                               "completion_tokens": usage["completion_tokens"]})
            self._totals(data, credit)
            self._save(data)
            if error:
                raise error

    def halt(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason or len(reason) > 100 or not all(c.isalnum() or c in "_-" for c in reason):
            raise BudgetError("Invalid halt reason")
        with self._locked():
            data, batch, credit, _ = self._load()
            batch.update(halted=True, halt_reason=reason)
            self._totals(data, credit)
            self._save(data)

    def reconcile(self, request_id: str, usage: dict) -> None:
        self._finish(request_id, usage=usage)

    def fail(self, request_id: str, error_type: str, *, halt: bool = False) -> None:
        if not isinstance(error_type, str) or not error_type or len(error_type) > 100 or not all(c.isalnum() or c in "_-" for c in error_type):
            raise BudgetError("Invalid error type")
        self._finish(request_id, error_type=error_type, halt=halt)
