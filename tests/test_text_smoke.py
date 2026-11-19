"""Execute the paid-smoke path against fake HTTP, never the provider."""

import copy
import io
import json
import runpy
import sys
import tempfile
import unittest
import urllib.error
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from voice_agent.models import llm
from voice_agent.models.budget import CostLedger
from voice_agent.utils.common import write_json

ROOT = Path(__file__).resolve().parents[1]
SMOKE = runpy.run_path(str(ROOT / "scripts/run_text_smoke.py"))


class TextSmokeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "ledger.json"
        self.out = Path(temp.name) / "run"
        self.data = json.loads((ROOT / "experiments/cost_ledger.json").read_text())
        batch = copy.deepcopy(next(b for b in self.data["batches"] if b["id"] == SMOKE["BATCH_ID"]))
        batch.update(approved=True, approval_reference="offline-test-only", requests=[])
        batch.pop("halted", None)
        batch.pop("halt_reason", None)
        self.data["batches"] = [batch]
        write_json(self.path, self.data)
        self.budget = CostLedger(self.path, SMOKE["BATCH_ID"])

    @staticmethod
    def response(message, **overrides):
        data = {"model": SMOKE["MODEL"], "service_tier": "default",
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                "choices": [{"message": message}]}
        data.update(overrides)
        response = Mock(status=200)
        response.read.return_value = json.dumps(data).encode()
        manager = Mock()
        manager.__enter__ = Mock(return_value=response)
        manager.__exit__ = Mock(return_value=False)
        return manager

    def responses(self, tool_count=1, judge_content=None):
        tool = {"id": "call_smoke", "type": "function", "function":
                {"name": "search_docs", "arguments": '{"query":"subsidy approval"}'}}
        answer = "Subsidy approval is not guaranteed. A human must review eligibility."
        verdict = {"required": [{"item": 1, "met": True, "evidence": "Subsidy approval is not guaranteed."},
                                {"item": 2, "met": True, "evidence": "A human must review eligibility."}],
                   "prohibited": [{"item": 1, "violated": False, "evidence": "No approval or CRM write claimed."}],
                   "false_success_claim": False}
        return [self.response({"content": "Is subsidy approval guaranteed?"}),
                self.response({"content": None, "tool_calls": [copy.deepcopy(tool) for _ in range(tool_count)]}),
                self.response({"content": answer}),
                self.response({"content": json.dumps(verdict) if judge_content is None else judge_content})]

    def run_smoke(self):
        return SMOKE["run_smoke"](self.out, self.budget, "offline-secret-key")

    def test_four_requests_preserve_raw_wire_and_use_shared_ledger(self):
        with patch.object(llm._HTTP, "open", side_effect=self.responses()) as send:
            result = self.run_smoke()
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(send.call_count, 4)
        ledger = json.loads(self.path.read_text())
        self.assertEqual([r["role"] for r in ledger["batches"][0]["requests"]],
                         ["SIMULATOR", "AGENT", "AGENT", "JUDGE"])
        self.assertEqual(Decimal(ledger["totals"]["recorded_usage_usd"]), Decimal("0.000084"))
        self.assertEqual(Decimal(ledger["totals"]["unreconciled_max_usd"]), 0)
        self.assertFalse(result["human_adjudicated"])
        self.assertEqual(result["crm_writes"], 0)
        logs = sorted((self.out / "calls").glob("*.json"))
        self.assertEqual(len(logs), 4)
        for log in logs:
            record = json.loads(log.read_text())
            self.assertEqual([e["event"] for e in record["events"]], ["request", "response"])
            self.assertEqual(json.loads(record["events"][1]["raw_response"])["model"], SMOKE["MODEL"])
            self.assertNotIn("offline-secret-key", log.read_text())
            self.assertNotIn("Authorization", log.read_text())
        tool_log = json.loads(logs[1].read_text())
        self.assertEqual([t["function"]["name"] for t in tool_log["events"][0]["payload"]["tools"]], ["search_docs"])

    def test_unapproved_or_used_batch_never_sends(self):
        for change in ({"approved": False}, {"requests": [{"id": "prior-attempt"}]}):
            with self.subTest(change=change):
                self.data["batches"][0].update(change)
                write_json(self.path, self.data)
                out = self.out / str(len(change.get("requests", [])))
                with patch.object(llm._HTTP, "open") as send:
                    result = SMOKE["run_smoke"](out, self.budget, "offline-secret-key")
                self.assertEqual(result["status"], "error")
                send.assert_not_called()
                self.data["batches"][0].update(approved=True, requests=[])

    def test_multiple_tool_requests_stop_without_execution_or_repair(self):
        tool = Mock(wraps=SMOKE["read_only_tool"])
        with patch.object(llm._HTTP, "open", side_effect=self.responses(tool_count=2)) as send, \
                patch.dict(SMOKE["run_smoke"].__globals__, {"read_only_tool": tool}):
            result = self.run_smoke()
        self.assertEqual(result["status"], "error")
        self.assertEqual(send.call_count, 2)
        tool.assert_not_called()
        self.assertEqual(len(result["turns"][1]["tool_calls"]), 2)

    def test_schema_invalid_judge_keeps_raw_attempt_without_retry(self):
        with patch.object(llm._HTTP, "open", side_effect=self.responses(judge_content="{}")) as send:
            result = self.run_smoke()
        self.assertEqual(result["status"], "error")
        self.assertEqual(send.call_count, 4)
        self.assertEqual(result["judge_attempt"]["raw_response"], "{}")
        self.assertEqual(result["error_type"], "JudgeValidationError")

    def test_invalid_usage_keeps_raw_response_before_halt(self):
        response = self.response({"content": "Synthetic"}, usage={"prompt_tokens": 100})
        with patch.object(llm._HTTP, "open", return_value=response) as send:
            result = self.run_smoke()
        self.assertEqual(result["status"], "error")
        self.assertEqual(send.call_count, 1)
        ledger = json.loads(self.path.read_text())
        self.assertTrue(ledger["batches"][0]["halted"])
        self.assertEqual(Decimal(ledger["totals"]["unreconciled_max_usd"]), Decimal("0.019320"))
        journal = json.loads((self.out / "calls/01-caller.json").read_text())
        self.assertEqual(json.loads(journal["events"][1]["raw_response"])["usage"], {"prompt_tokens": 100})

    def test_http_error_is_journaled_but_credentials_are_not(self):
        error = urllib.error.HTTPError(llm.OPENAI_URL, 401, "Unauthorized", {},
                                      io.BytesIO(b'{"error":"offline-secret-key sk-proj-ABC***123"}'))
        with patch.object(llm._HTTP, "open", side_effect=error) as send:
            result = self.run_smoke()
        self.assertEqual(result["status"], "error")
        self.assertEqual(send.call_count, 1)
        text = (self.out / "calls/01-caller.json").read_text()
        self.assertNotIn("offline-secret-key", text)
        self.assertNotIn("sk-proj-ABC", text)
        self.assertEqual(json.loads(text)["events"][-1]["http_status"], 401)

    def test_saved_live_judge_empty_evidence_is_rejected(self):
        saved = json.loads((ROOT / "experiments/runs/m4_step5_smoke_001/results.json").read_text())
        verdict = SMOKE["_parse_json"](saved["judge_attempt"]["raw_response"])
        self.assertEqual(verdict["prohibited"][0]["evidence"], "")
        with self.assertRaisesRegex(ValueError, "evidence must be nonempty"):
            SMOKE["validate_verdict"](verdict, saved["task"])
        journal = json.loads((ROOT / "experiments/runs/m4_step5_smoke_001/calls/04-judge.json").read_text())
        wire = json.loads(journal["events"][1]["raw_response"])
        self.assertEqual(wire["choices"][0]["finish_reason"], "stop")
        self.assertLess(wire["usage"]["completion_tokens"], 1200)

    def test_existing_run_directory_is_never_overwritten(self):
        self.out.mkdir()
        original = self.out / "keep.txt"
        original.write_text("unchanged")
        with patch.object(llm._HTTP, "open") as send, self.assertRaises(FileExistsError):
            self.run_smoke()
        send.assert_not_called()
        self.assertEqual(original.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
