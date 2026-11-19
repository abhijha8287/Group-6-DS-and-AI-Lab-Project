"""Offline budget accounting tests using synthetic catalog prices."""
import copy
import json
import multiprocessing
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.models.budget import BudgetError, CostLedger, max_cost_usd
from voice_agent.utils.common import write_json


def fixture():
    return {
        "starting_credit_usd": "1.00",
        "models": {"synthetic": {"input_usd_per_million": "0.15", "output_usd_per_million": "0.60", "max_input_tokens": 128000}},
        "allocations": {"test": "1.00"},
        "batches": [{"id": "batch", "allocation": "test", "approved": True, "approval_reference": "offline-test",
                     "max_cost_usd": "1.00", "model": "synthetic", "limits": {"max_requests": 10,
                     "max_output_tokens": 1200, "max_request_bytes": 256000, "max_retries": 1,
                     "max_caller_turns": 12, "max_tool_steps": 8, "max_audio_seconds": 0}, "requests": []}],
    }


def reserve_process(path, queue):
    try:
        queue.put(CostLedger(Path(path), "batch").reserve("synthetic", 1200, 100, "AGENT", 0))
    except BudgetError:
        queue.put("rejected")


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.json"
        self.data = fixture()
        self.save()
        self.ledger = CostLedger(self.path, "batch")

    def save(self):
        write_json(self.path, self.data)

    def read(self):
        return json.loads(self.path.read_text())

    def reserve(self, **overrides):
        args = dict(model="synthetic", max_output_tokens=1200, request_bytes=100, role="AGENT", attempt=0)
        args.update(overrides)
        return self.ledger.reserve(**args)

    def test_exact_full_context_and_usage(self):
        self.assertEqual(max_cost_usd("synthetic", 1200, self.data["models"]), Decimal("0.019920"))
        request = self.reserve()
        self.ledger.reconcile(request, {"prompt_tokens": 100, "completion_tokens": 20, "cached_tokens": 999})
        totals = self.read()["totals"]
        self.assertEqual(Decimal(totals["recorded_usage_usd"]), Decimal("0.000027"))
        self.assertEqual(Decimal(totals["unreconciled_max_usd"]), 0)
        self.assertEqual(Decimal(totals["remaining_credit_estimate_usd"]), Decimal("0.999973"))
        self.assertEqual(self.ledger.limits["max_requests"], 10)

    def test_approval_catalog_and_limits_fail_closed(self):
        cases = [lambda d: d["batches"][0].update(approved=False),
                 lambda d: d["batches"][0].update(approval_reference=" "),
                 lambda d: d["batches"][0].update(model="unknown"),
                 lambda d: d["batches"][0]["limits"].update(max_audio_seconds=1),
                 lambda d: d["batches"][0]["limits"].update(max_caller_turns=13),
                 lambda d: d["batches"][0]["limits"].update(max_tool_steps=9),
                 lambda d: d["batches"][0]["limits"].update(max_requests=True),
                 lambda d: d["models"]["synthetic"].update(input_usd_per_million="NaN")]
        for mutate in cases:
            with self.subTest(mutate=mutate):
                self.data = fixture()
                mutate(self.data)
                self.save()
                with self.assertRaises(BudgetError):
                    self.reserve()
                self.assertEqual(self.read()["batches"][0]["requests"], [])

    def test_request_caps_and_types(self):
        for args in ({"max_output_tokens": 1201}, {"max_output_tokens": True}, {"request_bytes": 256001},
                     {"request_bytes": False}, {"attempt": 2}, {"attempt": True}, {"role": "OTHER"},
                     {"model": "other"}):
            with self.subTest(args=args), self.assertRaises(BudgetError):
                self.reserve(**args)
        self.assertEqual(self.read()["batches"][0]["requests"], [])

    def test_batch_allocation_and_global_limits(self):
        for dimension in ("batch", "allocation", "global"):
            with self.subTest(dimension=dimension):
                self.data = fixture()
                if dimension == "batch":
                    self.data["batches"][0]["max_cost_usd"] = "0.03"
                else:
                    self.data["batches"][0]["max_cost_usd"] = "0.03"
                    second = copy.deepcopy(self.data["batches"][0])
                    second["id"] = "second"
                    if dimension == "allocation":
                        self.data["allocations"]["test"] = "0.03"
                    else:
                        self.data["starting_credit_usd"] = "0.03"
                        self.data["allocations"]["other"] = "1.00"
                        second["allocation"] = "other"
                    self.data["batches"].append(second)
                self.save()
                request = self.reserve()
                self.ledger.fail(request, "timeout")
                with self.assertRaises(BudgetError):
                    (self.ledger if dimension == "batch" else CostLedger(self.path, "second")).reserve("synthetic", 1200, 1, "JUDGE", 0)

    def test_failed_and_invalid_usage_hold_and_halt(self):
        for usage in (None, {}, {"prompt_tokens": True, "completion_tokens": 1},
                      {"prompt_tokens": 128001, "completion_tokens": 1},
                      {"prompt_tokens": 0, "completion_tokens": 1201},
                      {"prompt_tokens": -1, "completion_tokens": 0}):
            with self.subTest(usage=usage):
                self.data = fixture()
                self.save()
                request = self.reserve()
                with self.assertRaises(BudgetError):
                    self.ledger.reconcile(request, usage)
                data = self.read()
                self.assertTrue(data["batches"][0]["halted"])
                self.assertEqual(data["batches"][0]["requests"][0]["status"], "failed")
                self.assertEqual(Decimal(data["totals"]["unreconciled_max_usd"]), Decimal("0.019920"))
                with self.assertRaises(BudgetError):
                    self.reserve()
        self.data = fixture()
        self.save()
        request = self.reserve()
        self.ledger.fail(request, "timeout")
        self.assertEqual(Decimal(self.read()["totals"]["unreconciled_max_usd"]), Decimal("0.019920"))
        with self.assertRaises(BudgetError):
            self.ledger.reconcile(request, {"prompt_tokens": 0, "completion_tokens": 0})

    def test_shared_instances_retry_and_halt(self):
        first = self.reserve(role="AGENT")
        second = CostLedger(self.path, "batch")
        with self.assertRaises(BudgetError):
            second.reserve("synthetic", 1200, 12, "SIMULATOR", 1)
        self.ledger.reconcile(first, {"prompt_tokens": 1, "completion_tokens": 1})
        retry = second.reserve("synthetic", 1200, 12, "SIMULATOR", 1)
        second.fail(retry, "timeout")
        third = second.reserve("synthetic", 1200, 12, "JUDGE", 0)
        self.assertEqual([first, retry, third], ["batch-1", "batch-2", "batch-3"])
        second.halt("unexpected_service_tier")
        self.assertEqual(self.read()["batches"][0]["halt_reason"], "unexpected_service_tier")
        with self.assertRaises(BudgetError):
            self.reserve()
        second.reconcile(third, {"prompt_tokens": 1, "completion_tokens": 1})

    def test_halted_usage_blocks_other_approved_batches_too(self):
        other = copy.deepcopy(self.data["batches"][0])
        other["id"] = "other"
        self.data["batches"].append(other)
        self.save()
        request = self.reserve()
        self.ledger.fail(request, "unexpected_tier", halt=True)
        with self.assertRaises(BudgetError):
            CostLedger(self.path, "other").reserve("synthetic", 1200, 100, "JUDGE", 0)
        self.assertEqual(self.read()["batches"][1]["requests"], [])

    def test_failed_request_and_halt_are_one_locked_update(self):
        request = self.reserve()
        writer_entered, reader_started = Event(), Event()
        writes = []

        def capture_write(path, data):
            writes.append(copy.deepcopy(data))
            writer_entered.set()
            self.assertTrue(reader_started.wait(5))
            write_json(path, data)

        def competing_reservation():
            reader_started.set()
            with self.assertRaises(BudgetError):
                CostLedger(self.path, "batch").reserve("synthetic", 1200, 100, "JUDGE", 0)

        with ThreadPoolExecutor(max_workers=2) as pool, \
                patch("voice_agent.models.budget.write_json", side_effect=capture_write):
            failure = pool.submit(self.ledger.fail, request, "unexpected_tier", halt=True)
            self.assertTrue(writer_entered.wait(5))
            competitor = pool.submit(competing_reservation)
            failure.result(timeout=10)
            competitor.result(timeout=10)
        self.assertEqual(len(writes), 1)
        self.assertTrue(writes[0]["batches"][0]["halted"])
        self.assertEqual(writes[0]["batches"][0]["requests"][0]["status"], "failed")
        self.assertEqual(len(self.read()["batches"][0]["requests"]), 1)

    def test_process_lock_no_lost_update(self):
        self.data["batches"][0]["limits"]["max_requests"] = 1
        self.save()
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        processes = [ctx.Process(target=reserve_process, args=(str(self.path), queue)) for _ in range(4)]
        for process in processes:
            process.start()
        results = [queue.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(20)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(results.count("batch-1"), 1)
        self.assertEqual(results.count("rejected"), 3)
        self.assertEqual(len(self.read()["batches"][0]["requests"]), 1)

    def test_unavailable_lock_fails_closed(self):
        with patch("voice_agent.models.budget.fcntl", None), self.assertRaises(BudgetError):
            self.reserve()


if __name__ == "__main__":
    unittest.main()
