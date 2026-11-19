"""Exercise approved Step 11 diagnostic with fake HTTP only."""
import json
import runpy
from unittest.mock import patch

import test_text_smoke as base
from voice_agent.models import llm
from voice_agent.models.budget import CostLedger
from voice_agent.utils.common import write_json

STEP11 = runpy.run_path(str(base.ROOT / "scripts/run_step11_smoke.py"))


class Step11SmokeTests(base.TextSmokeTests):
    def setUp(self):
        super().setUp()
        self.data["batches"][0]["id"] = STEP11["BATCH_ID"]
        write_json(self.path, self.data)
        self.budget = CostLedger(self.path, STEP11["BATCH_ID"])

    def run_smoke(self):
        return STEP11["run"](self.out, self.budget, "offline-secret-key")

    def test_context_artifacts_and_explicit_evidence_instruction(self):
        with patch.object(llm._HTTP, "open", side_effect=self.responses()) as send:
            result = self.run_smoke()
        self.assertEqual(result["status"], "passed")
        payload = json.loads(send.call_args_list[-1].args[0].data)
        self.assertIn("even when violated is false", payload["messages"][0]["content"])
        crm = json.loads((self.out/"crm.json").read_text())
        self.assertEqual(crm["initial"], crm["final"])
        self.assertEqual(crm["diff"], [])
        self.assertEqual(len(json.loads((self.out/"retrieved_sources.json").read_text())["sources"]),1)

    def test_saved_paid_step11_verdict_replays_with_unchanged_validator(self):
        saved=json.loads((base.ROOT / "experiments/runs/m4_step11_smoke_001/results.json").read_text())
        verdict=base.SMOKE["_parse_json"](saved["judge_attempt"]["raw_response"])
        base.SMOKE["validate_verdict"](verdict,saved["task"])
        self.assertEqual(saved["status"],"passed")
        self.assertTrue(all(v["met"] for v in verdict["required"]))
        self.assertTrue(all(v["evidence"].strip() for v in verdict["prohibited"]))

    def test_consumed_step11_batch_never_sends(self):
        self.data["batches"][0]["requests"] = [{"id":"already-used"}]
        write_json(self.path,self.data)
        with patch.object(llm._HTTP,"open") as send:
            result=self.run_smoke()
        self.assertEqual(result["status"],"error")
        send.assert_not_called()
