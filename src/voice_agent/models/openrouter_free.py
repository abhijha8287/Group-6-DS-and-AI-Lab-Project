"""Restricted, ledger-authorized OpenRouter free text adapter."""

import json
import math
import time
import urllib.error
import urllib.request
from decimal import Decimal

from voice_agent.models import llm
from voice_agent.models.budget import BudgetError, CostLedger, _money, _price
from voice_agent.models.llm import Completion, LLMError, OpenAICompatibleClient

MODEL = "google/gemma-4-26b-a4b-it:free"
URL = "https://openrouter.ai/api/v1/chat/completions"


def _zero(value):
    return type(value) in (int, float) and math.isfinite(value) and value == 0


def _setup(budget):
    if type(budget) is not CostLedger:
        raise BudgetError("An approved CostLedger is required")
    with budget._locked():
        data, batch, _, _ = budget._load()
        model = data["models"].get(MODEL)
        if (batch.get("model") != MODEL or not isinstance(model, dict)
                or model.get("provider") != "openrouter_free" or model.get("no_charge_only") is not True
                or _price(model) != (Decimal(0), Decimal(0), 262144)
                or _money(batch["max_cost_usd"]) != 0):
            raise BudgetError("Free model catalog or batch mismatch")
        limits = batch["limits"]
        if (limits["max_retries"] != 0 or limits["max_output_tokens"] != 800
                or limits["max_request_bytes"] > 64000):
            raise BudgetError("Free batch limits mismatch")


def _messages(messages):
    if not isinstance(messages, list):
        raise BudgetError("Messages must be a list")
    for m in messages:
        if not isinstance(m, dict) or m.get("role") not in ("system", "user", "assistant", "tool"):
            raise BudgetError("Invalid text message")
        role = m["role"]
        allowed = {"role", "content"} | ({"tool_calls"} if role == "assistant" else set()) | ({"tool_call_id"} if role == "tool" else set())
        if set(m) - allowed or not isinstance(m.get("content"), str):
            raise BudgetError("Only text messages are allowed")
        if role == "tool" and (not isinstance(m.get("tool_call_id"), str) or not m["tool_call_id"]):
            raise BudgetError("Invalid tool result")
        if "tool_calls" in m:
            calls = m["tool_calls"]
            if not isinstance(calls, list):
                raise BudgetError("Invalid tool calls")
            for c in calls:
                if (not isinstance(c, dict) or set(c) != {"id", "name", "arguments"}
                        or not isinstance(c["id"], str) or not c["id"]
                        or not isinstance(c["name"], str) or not c["name"]):
                    raise BudgetError("Invalid function call")


def _response(data):
    if not isinstance(data, dict) or data.get("provider") != "Google AI Studio" or data.get("model") not in (MODEL, MODEL.removesuffix(":free")):
        raise BudgetError("Unexpected response provider or model")
    usage = data.get("usage")
    if not isinstance(usage, dict) or not _zero(usage.get("cost")) or usage.get("is_byok") is True:
        raise BudgetError("Unexpected or missing response cost")
    details = usage.get("cost_details")
    if details is not None:
        if not isinstance(details, dict):
            raise BudgetError("Invalid cost details")
        for key, value in details.items():
            if key.startswith("upstream_inference") and value is not None and not _zero(value):
                raise BudgetError("Unexpected upstream cost")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise BudgetError("Invalid response choices")
    message = choices[0].get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant" or not isinstance(message.get("content"), (str, type(None))):
        raise BudgetError("Invalid response message")
    calls = message.get("tool_calls", [])
    if not isinstance(calls, list):
        raise BudgetError("Invalid response tool calls")
    for call in calls:
        if (not isinstance(call, dict) or set(call) != {"id", "type", "function"}
                or call["type"] != "function" or not isinstance(call["id"], str) or not call["id"]
                or not isinstance(call["function"], dict) or set(call["function"]) != {"name", "arguments"}
                or not isinstance(call["function"]["name"], str) or not call["function"]["name"]
                or not isinstance(call["function"]["arguments"], str)):
            raise BudgetError("Invalid response function call")
        # Let the shared parser/sandbox handle bad argument JSON, as for direct OpenAI.
    return OpenAICompatibleClient.from_wire(data)


class FreeOpenRouterClient:
    def __init__(self, budget, api_key, journal=None, role="AGENT", timeout=30):
        if role != "AGENT":
            raise BudgetError("Only the AGENT role is allowed")
        self.budget, self.api_key, self.journal = budget, api_key, journal
        self.role, self.timeout, self.model = role, timeout, MODEL

    def complete(self, messages, tools=None, temperature=0.0, max_tokens=800, json_mode=False) -> Completion:
        if (type(temperature) not in (int, float) or temperature != 0 or type(max_tokens) is not int
                or not 1 <= max_tokens <= 800 or json_mode is not False):
            raise BudgetError("Invalid free request options")
        _messages(messages)
        if tools is not None and (not isinstance(tools, list) or any(
                not isinstance(t, dict) or set(t) - {"name", "description", "parameters", "strict"}
                or not isinstance(t.get("name"), str) or not t["name"]
                or not isinstance(t.get("parameters"), dict)
                or ("description" in t and not isinstance(t["description"], str))
                or ("strict" in t and type(t["strict"]) is not bool) for t in tools)):
            raise BudgetError("Only local function schemas are allowed")
        payload = {"model": MODEL, "messages": OpenAICompatibleClient.to_wire(messages),
                   "temperature": 0, "max_tokens": max_tokens, "stream": False,
                   "reasoning": {"enabled": False, "exclude": True},
                   "provider": {"only": ["google-ai-studio"], "order": ["google-ai-studio"],
                                "allow_fallbacks": False, "require_parameters": True,
                                "max_price": {"prompt": 0, "completion": 0}, "data_collection": "deny"}}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        try:
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            raise BudgetError("Invalid JSON request") from None
        if len(body) > 64000:
            raise BudgetError("Request exceeds free text limit")
        if not isinstance(self.api_key, str) or not self.api_key:
            raise BudgetError("OpenRouter API key is required")
        _setup(self.budget)
        reservation = self.budget.reserve(MODEL, max_tokens, len(body), "AGENT", 0)
        start = time.perf_counter()
        try:
            _setup(self.budget)
            request = urllib.request.Request(URL, data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
            if self.journal is not None:
                self.journal({"event": "request", "request_id": reservation, "role": "AGENT", "attempt": 0, "payload": payload})
            with llm._HTTP.open(request, timeout=min(self.timeout, 30.0)) as response:
                raw = response.read()
                if self.journal is not None:
                    self.journal({"event": "response", "request_id": reservation, "http_status": response.status, "raw_response": raw})
            data = json.loads(raw.decode("utf-8"))
            result = _response(data)
            self.budget.reconcile(reservation, data["usage"])
            result.latency_s = time.perf_counter() - start
            return result
        except Exception as err:
            if isinstance(err, urllib.error.HTTPError):
                try:
                    raw_error = err.read() if self.journal is not None else None
                    if self.journal is not None:
                        self.journal({"event": "error", "request_id": reservation, "error_type": "HTTPError",
                                      "http_status": err.code, "raw_response": raw_error})
                except Exception:
                    pass
                finally:
                    try:
                        err.close()
                    except Exception:
                        pass
            try:
                self.budget.fail(reservation, type(err).__name__, halt=True)
            except BudgetError:
                # Reconciliation itself may already have recorded the failure and halt.
                self.budget.halt("RequestFailure")
            if isinstance(err, BudgetError):
                raise BudgetError("Free request failed; batch halted") from None
            raise LLMError("Free request failed; batch halted") from None
