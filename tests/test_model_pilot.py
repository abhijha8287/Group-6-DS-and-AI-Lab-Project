"""Pilot preparation and fake execution only. Never sends inference requests."""
import copy
import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from voice_agent.data.development import load_development,case_pack
from voice_agent.evaluation.evaluator import expected_state
from voice_agent.models import llm
from voice_agent.models.budget import CostLedger,BudgetError
from voice_agent.pipelines.episode import run_episode
from voice_agent.data.preprocess import chunk_knowledge
from voice_agent.inference.retrieval import BM25Index

PILOT=runpy.run_path(str(ROOT/"scripts/run_model_pilot.py"))


class ModelPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ledger=self.root/"ledger.json"
        self.ledger.write_bytes((ROOT/"experiments/cost_ledger.json").read_bytes())
        self.settings=self.root/"settings.json";self.settings.write_text('{}')
        self.value=PILOT["plan"]()
        self.approval=dict(approved=True,group_id=PILOT["GROUP"],settings_sha256=PILOT["sha"](self.settings),
            max_openai_cost_usd="7.17840",max_openrouter_cost_usd="0",user_reply="offline-only test",approval_reference="offline-test")
        self.globals=PILOT["execute"].__globals__

    def test_matrix_and_subbatches_do_not_raise_hard_cap(self):
        self.assertEqual(len(self.value["slots"]),6)
        self.assertEqual(len(self.value["batches"]),12)
        self.assertEqual([x["candidate"] for x in self.value["slots"]],["gemma","openai","openai","gemma","gemma","openai"])
        self.assertTrue(all(b["limits"]["max_requests"]<=100 for b in self.value["batches"]))
        self.assertEqual({s["scenario_id"] for s in self.value["slots"]},{"IN02"})

    def test_invalid_approval_never_creates_output_or_ledger_change(self):
        before=self.ledger.read_bytes();bad={**self.approval,"max_openai_cost_usd":"9"}
        approval_path=self.root/"approval.json";approval_path.write_text(json.dumps(bad))
        with patch.dict(self.globals,{"ROOT":self.root,"LEDGER":self.ledger,"SETTINGS":self.settings,"check":lambda:self.value,"load_env":lambda:None}),patch.dict(os.environ,{"OPENAI_API_KEY":"offline-a","OPENROUTER_API_KEY":"offline-b"}):
            with self.assertRaisesRegex(ValueError,"approval"):PILOT["execute"](approval_path)
        self.assertFalse((self.root/"experiments").exists())
        self.assertEqual(self.ledger.read_bytes(),before)

    def test_registration_requires_matching_approval_and_is_once_only(self):
        with patch.dict(self.globals,{"LEDGER":self.ledger,"SETTINGS":self.settings}):
            bad={**self.approval,"approved":False}
            with self.assertRaises(ValueError):PILOT["register"](self.value,bad)
            PILOT["register"](self.value,self.approval)
            data=json.loads(self.ledger.read_text())
            self.assertEqual(len(data["batches"]),14)
            self.assertEqual(data["models"][PILOT["GEMMA"]]["provider"],"openrouter_free")
            with self.assertRaises(ValueError):PILOT["register"](self.value,self.approval)
            gemma_batch=next(b for b in self.value["batches"] if b["model"]==PILOT["GEMMA"])
            with patch.object(llm._HTTP,"open") as send:
                with self.assertRaises(BudgetError):
                    llm._post(llm.OPENAI_URL,{"model":PILOT["GEMMA"],"messages":[],"max_completion_tokens":800,"service_tier":"default","n":1},{},30,budget=CostLedger(self.ledger,gemma_batch["id"]))
                send.assert_not_called()

    def test_zero_filled_report_does_not_claim_success_or_latency(self):
        result=PILOT["report"]([])
        self.assertEqual(result["planned_attempts"],6)
        for row in result["candidates"].values():
            self.assertEqual(row["machine_task_success"]["unknown"],3)
            self.assertIsNone(row["machine_task_success"]["valid_rate"])
            self.assertIsNone(row["agent_total_seconds_p50"])
            self.assertIsNone(row["factual_accuracy"])

    def test_complete_fake_run_and_mid_group_stop_keep_records(self):
        _,tasks,packs=load_development()
        def episode(task,pack,mode,clients,chunks,index,**kwargs):
            self.assertTrue(kwargs["stop_on_protocol_issue"])
            return dict(status="completed",judge_status="valid",reward=1,db_pass=True,safety_pass=True,
                issues=[],turns=[],final_state=expected_state(pack.seed,task["gold"]),
                usage={"agent":{"latency_s":0,"llm_calls":0}})
        for failing in (False,True):
            root=self.root/("failure" if failing else "complete");root.mkdir()
            ledger=root/"ledger.json";ledger.write_bytes(self.ledger.read_bytes())
            settings=root/"settings.json";settings.write_text('{}')
            approval_path=root/"approval.json";approval_path.write_text(json.dumps(self.approval))
            def maybe_fail(*args,**kwargs):
                value=episode(*args,**kwargs)
                if failing:value.update(status="caller_repeat_stop",judge_status="not_requested",reward=None)
                return value
            with patch.dict(self.globals,{"ROOT":root,"LEDGER":ledger,"SETTINGS":settings,"check":lambda:self.value,
                "load_env":lambda:None,"run_episode":maybe_fail}),patch.dict(os.environ,{"OPENAI_API_KEY":"offline-a","OPENROUTER_API_KEY":"offline-b"}),patch.object(llm._HTTP,"open") as send:
                code=PILOT["execute"](approval_path)
                with self.assertRaises(FileExistsError):PILOT["execute"](approval_path)
                send.assert_not_called()
            saved=json.loads((root/"experiments/runs"/PILOT["GROUP"]/"results.json").read_text())
            self.assertEqual(len(saved["records"]),1 if failing else 6)
            self.assertEqual(code,1 if failing else 0)
            self.assertIn("costs",saved)

    def test_known_simulator_stop_does_not_call_paid_judge(self):
        _,tasks,packs=load_development();task=next(t for t in tasks if t["id"]=="IN02")
        pack=case_pack(task,packs);chunks=chunk_knowledge(pack)
        index=BM25Index([c for c in chunks if c["kind"]=="sourced_fact"])
        class Caller:
            usage={"llm_calls":0}
            def reply(self,text):return "same caller message"
        class Agent:
            name="offline";usage={"input_tokens":0,"output_tokens":0,"llm_calls":0,"latency_s":0}
            def greeting(self):return "Hello?"
            def turn(self,*args):return "Anything else?"
        judge=Mock()
        with patch("voice_agent.pipelines.episode.SingleAgent",return_value=Agent()),patch("voice_agent.pipelines.episode.LLMCaller",return_value=Caller()):
            result=run_episode(task,pack,"llm",{"agent":Mock(),"simulator":Mock(),"judge":judge},chunks,index,stop_on_protocol_issue=True)
        self.assertEqual(result["status"],"caller_repeat_stop")
        self.assertEqual(result["judge_status"],"not_requested")
        judge.complete.assert_not_called()

    def test_tool_checkpoints_are_independent_and_secrets_redacted(self):
        _,tasks,packs=load_development();task=next(t for t in tasks if t["id"]=="IN02")
        pack=case_pack(task,packs)
        from voice_agent.inference.crm import CRMSandbox
        from voice_agent.data.preprocess import task_views
        sandbox=CRMSandbox(pack.seed,task_views(task)["harness"])
        events=[];sandbox.checkpoint=events.append
        sandbox.execute("find_lead",{"email":"synthetic@example.invalid"})
        events[0]["state"]["contacts"].clear()
        self.assertTrue(sandbox.state["contacts"])
        self.assertEqual(PILOT["safe"]("offline-secret",["offline-secret"]),"[REDACTED]")
