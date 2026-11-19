"""Development-only validation and context-leakage tests; no held-out answers or API calls."""

import copy
import hashlib
import json
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from voice_agent.data.development import DEVELOPMENT_DIR, case_pack, load_development, validate_task
from voice_agent.data.preprocess import check_views, chunk_knowledge, task_views
from voice_agent.inference.agent import SingleAgent
from voice_agent.inference.crm import CRMSandbox
from voice_agent.inference.retrieval import BM25Index
from voice_agent.models.llm import Completion
from voice_agent.pipelines.episode import run_episode

ROOT = Path(__file__).resolve().parents[1]


class RecordingClient:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.requests = []

    def complete(self, messages, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        self.requests.append(copy.deepcopy({"messages": messages, "kwargs": kwargs}))
        return next(self.replies)


class DevelopmentTests(unittest.TestCase):
    def test_frozen_core_and_holdout_deferral(self):
        manifest, tasks, _ = load_development()
        self.assertEqual(len(tasks), 16)
        self.assertEqual(manifest["core_ids"], [f"IN{i:02d}" for i in range(1,11)])
        self.assertEqual((DEVELOPMENT_DIR/"core.json").read_bytes(),
                         (ROOT/"milestones/M2_dataset/solar_pilot/scenarios.json").read_bytes())
        self.assertEqual(len(manifest["legacy_split"]["former_test_review_ids"]), 12)
        self.assertEqual(manifest["held_out"]["actual_case_count"], 0)
        self.assertFalse(manifest["held_out"]["evaluation_allowed"])
        self.assertEqual(manifest["held_out_audio"]["planned_separate_cases"], 3)
        self.assertEqual(manifest["held_out_audio"]["actual_case_count"], 0)
        self.assertIsNone(manifest["held_out_audio"]["reviewer"])

    def test_hash_drift_and_unexpected_file_membership_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"dev"
            shutil.copytree(DEVELOPMENT_DIR, root)
            # An unrelated file is never discovered or parsed by this loader.
            (root/"unrelated_private_sentinel.txt").write_text("not JSON; not a scenario or answer key")
            load_development(root)
            path = root/"documents/large.md"
            path.write_text(path.read_text()+"\n| S999 | EVALUATORSECRETZXQ |\n")
            with self.assertRaisesRegex(ValueError, "Frozen development input changed"):
                load_development(root)
            manifest = json.loads((root/"manifest.json").read_text())
            manifest["file_sha256"]["unexpected.json"] = "0"*64
            (root/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "input set"):
                load_development(root)

    def test_nested_role_leaks_and_nontext_agent_id_rejected(self):
        _, tasks, _ = load_development()
        for payload in ({"gold": {}}, {"extra": {"verification_succeeds": True}},
                        {"extra": [{"tool_results": {}}]}):
            views = task_views(tasks[0])
            views["simulator"]["caller"]["provided_fields"].update(payload)
            with self.assertRaises(AssertionError):
                check_views(views)
        for payload in ({"gold": "private"}, []):
            views = task_views(tasks[0]); views["agent"]["id"] = payload
            with self.assertRaises(AssertionError):
                check_views(views)
        views = task_views(tasks[0]); views["agent"]["metadata"] = {"gold": "private"}
        with self.assertRaises(AssertionError):
            check_views(views)

    def test_views_do_not_share_mutable_objects(self):
        _, tasks, _ = load_development()
        task = copy.deepcopy(tasks[2])
        shared = {"roof_permission": "landlord_approval_pending"}
        task["caller"]["provided_fields"] = shared
        task["gold"]["contact_updates"][0]["set"] = shared
        views = task_views(task)
        views["simulator"]["caller"]["provided_fields"]["roof_permission"] = "changed"
        self.assertEqual(views["evaluator"]["gold"]["contact_updates"][0]["set"]["roof_permission"], "landlord_approval_pending")
        self.assertEqual(shared["roof_permission"], "landlord_approval_pending")

    def test_actual_llm_path_does_not_pass_private_markers_to_clients_or_documents(self):
        _, tasks, packs = load_development()
        task = copy.deepcopy(tasks[0])
        markers = ["EVALUATORSECRETZXQ", "HARNESSSECRETJKT", "RUBRICSECRETWVP"]
        task["gold"]["unused_private_marker"] = markers[0]
        task["environment"]["unused_private_marker"] = markers[1]
        task["required_information"].append(markers[2])
        pack = case_pack(task, packs)
        chunks = chunk_knowledge(pack)
        index = BM25Index(chunks)
        agent = RecordingClient([Completion("Goodbye.")])
        caller = RecordingClient([Completion("Hello, I have a question.")])
        run_episode(task, pack, "llm", {"agent":agent, "simulator":caller}, chunks, index)
        self.assertEqual(len(agent.calls), 1)
        self.assertEqual(len(caller.calls), 1)
        contexts = json.dumps([agent.requests, caller.requests, chunks])
        for marker in markers:
            self.assertNotIn(marker, contexts)
            self.assertEqual(index.search(marker), [])
        self.assertNotIn(task["caller"]["goal"], json.dumps(agent.calls))

    def test_multiturn_episode_contexts_after_retrieval_and_writes_exclude_private_markers(self):
        _, tasks, packs = load_development()
        task = copy.deepcopy(tasks[4])
        markers = ["EVALUATORSECRETZXQ", "HARNESSSECRETJKT", "RUBRICSECRETWVP"]
        task["gold"]["unused_private_marker"] = markers[0]
        task["environment"]["unused_private_marker"] = markers[1]
        task["required_information"].append(markers[2])
        pack = case_pack(task, packs)
        chunks = chunk_knowledge(pack)
        index = BM25Index([c for c in chunks if c["kind"]=="sourced_fact"])
        at = "2026-11-03T17:30:00+05:30"
        agent = RecordingClient([
            Completion("", [
                {"id":"v","name":"verify_identity","arguments":{"contact_id":"C01","email":"anika@example.invalid"}},
                {"id":"a","name":"check_availability","arguments":{"at":at}},
                {"id":"s","name":"search_docs","arguments":{"query":"blackout grid-connected safety"}}]),
            Completion("That slot is free. Shall I request the callback?"),
            Completion("", [{"id":"w","name":"schedule_callback","arguments":{"contact_id":"C01","at":at}}]),
            Completion("The callback request was saved. Goodbye.")])
        caller = RecordingClient([Completion("C01, anika@example.invalid; please request that callback."),
                                  Completion("Yes, I confirm.")])
        result = run_episode(task,pack,"llm",{"agent":agent,"simulator":caller},chunks,index)
        self.assertTrue(result["db_pass"])
        self.assertIsNone(result["reward"])
        self.assertEqual((len(agent.calls),len(caller.calls)),(4,2))
        self.assertEqual([x["tool"] for x in result["tool_log"]],
                         ["verify_identity","check_availability","search_docs","schedule_callback"])
        contexts = json.dumps([agent.requests,caller.requests])
        for marker in markers:self.assertNotIn(marker,contexts)
        self.assertNotIn(task["caller"]["goal"],json.dumps(agent.calls))
        retrieved = next(x["result"]["results"] for x in result["tool_log"] if x["tool"]=="search_docs")
        self.assertTrue(retrieved)
        for marker in markers:self.assertNotIn(marker,json.dumps(retrieved))

    def test_trusted_identity_truth_is_not_dumped_into_observed_tool_result(self):
        _, tasks, packs = load_development()
        task = copy.deepcopy(tasks[4]); task["environment"]["marker"] = "HARNESSSECRETJKT"
        pack = case_pack(task, packs)
        sandbox = CRMSandbox(pack.seed, task_views(task)["harness"])
        client = RecordingClient([
            Completion("", [{"id":"verify1","name":"verify_identity","arguments":
                              {"contact_id":"C01","email":"anika@example.invalid"}}]),
            Completion("Goodbye.")])
        agent = SingleAgent(client, pack.name, [], pack.seed["snapshot_at"])
        agent.turn("My contact ID is C01 and email is anika@example.invalid.", sandbox, [])
        observed = json.loads(next(m["content"] for m in agent.messages if m["role"]=="tool"))
        self.assertEqual(observed, {"success":True,"verified_contact_id":"C01"})
        self.assertNotIn("HARNESSSECRETJKT", json.dumps(client.calls))
        self.assertNotIn("verification_succeeds", json.dumps(client.calls))

    def test_deferred_partitions_cannot_be_enabled_by_metadata(self):
        for partition in ("held_out","held_out_audio"):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/"dev";shutil.copytree(DEVELOPMENT_DIR,root)
                manifest=json.loads((root/"manifest.json").read_text())
                manifest[partition]["evaluation_allowed"]=True
                (root/"manifest.json").write_text(json.dumps(manifest))
                with patch.object(Path, "read_bytes", side_effect=AssertionError("Do not open case contents before the partition gate")):
                    with self.assertRaisesRegex(ValueError,"held-out"):
                        load_development(root)

    def test_invalid_case_schema_and_clock_reset(self):
        _, tasks, packs = load_development()
        task = copy.deepcopy(tasks[0]);task["knowledge_ids"] = ["S999"]
        with self.assertRaisesRegex(ValueError,"knowledge"):
            validate_task(task,packs)
        long_case = next(t for t in tasks if t["id"]=="DEV15")
        pack = case_pack(long_case,packs)
        self.assertEqual(pack.seed["snapshot_at"], "2026-11-19T11:00:00+05:30")
        self.assertEqual(packs["large"].seed["snapshot_at"], "2026-11-02T11:00:00+05:30")
        self.assertEqual(pack.seed["contacts"], packs["large"].seed["contacts"])

    def test_freeze_refuses_overwrite_and_fixture_audit_matches_every_state(self):
        freeze = runpy.run_path(str(ROOT/"scripts/freeze_development.py"))["freeze"]
        with self.assertRaises(FileExistsError):
            freeze()
        checker = runpy.run_path(str(ROOT/"scripts/check_development.py"))["check"]
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/"check"
            summary=checker(out)
            self.assertTrue(summary["fixture_checks_passed"])
            self.assertEqual(summary["cases"],16)
            self.assertFalse(summary["language_scored"])
            expected=json.loads((out/"states/DEV13.expected.json").read_text())
            contact=next(c for c in expected["contacts"] if c["id"]=="C02")
            self.assertFalse(contact["consent"])
            self.assertIsNone(contact["consent_record"])
            start=json.loads((out/"states/DEV14.start.json").read_text())
            end=json.loads((out/"states/DEV14.expected.json").read_text())
            self.assertEqual(start,end)
            with self.assertRaises(FileExistsError):checker(out)


if __name__ == "__main__":
    unittest.main()
