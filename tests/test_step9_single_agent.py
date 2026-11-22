"""M4 Step 9: corrected single agent (prompt v2 + agent-side guards). Offline, no model calls."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.development import case_pack, load_development  # noqa: E402
from voice_agent.data.preprocess import chunk_knowledge, task_views  # noqa: E402
from voice_agent.inference.agent import (PROMPTS, ProvenanceGuard, SingleAgent,  # noqa: E402
                                         promised_without_action, system_prompt)
from voice_agent.inference.crm import CRMSandbox  # noqa: E402
from voice_agent.inference.retrieval import BM25Index  # noqa: E402
from voice_agent.models.llm import Completion  # noqa: E402
from voice_agent.pipelines.episode import run_episode  # noqa: E402

AT = "2026-11-03T17:30:00+05:30"


class Scripted:
    def __init__(self, replies):
        self.replies, self.calls = iter(replies), []

    def complete(self, messages, **kwargs):
        self.calls.append(copy.deepcopy({"messages": messages, "kwargs": kwargs}))
        return next(self.replies)


def setup(index):
    _, tasks, packs = load_development()
    task = copy.deepcopy(tasks[index])
    pack = case_pack(task, packs)
    chunks = chunk_knowledge(pack)
    return task, pack, chunks, BM25Index([c for c in chunks if c["kind"] == "sourced_fact"])


def call(name, args, cid="t"):
    return {"id": cid, "name": name, "arguments": args}


class PromptVersions(unittest.TestCase):
    def test_m3_prompt_is_the_default_and_unchanged(self):
        task, pack, chunks, _ = setup(0)
        rules = [c for c in chunks if c["kind"] == "sandbox_rule"]
        agent = SingleAgent(Scripted([]), pack.name, rules, pack.seed["snapshot_at"])
        self.assertEqual(agent.messages[0]["content"], system_prompt(pack.name, rules, pack.seed["snapshot_at"]))
        self.assertFalse(agent.guards)
        self.assertEqual(agent.name, "single_agent")

    def test_v2_prompt_targets_observed_failures(self):
        text = PROMPTS["v2"]("SunGrid", [], "2026-11-02T11:00:00+05:30")
        for phrase in ("Never guess, invent or construct a contact ID or email",
                       "call the tool in that same turn",
                       "Call create_lead once with everything",
                       "do not ask for it again",
                       "Answer every part of the question"):
            self.assertIn(phrase, text)
        with self.assertRaises(ValueError):
            SingleAgent(Scripted([]), "x", [], "2026-11-02T11:00:00+05:30", prompt_version="v9")


class Provenance(unittest.TestCase):
    def test_guard_accepts_only_seen_values(self):
        guard = ProvenanceGuard()
        guard.observe_caller("I'm C03, email kiran.b@example.invalid")
        self.assertIsNone(guard.unknown_field({"contact_id": "C03", "email": "KIRAN.B@example.invalid"}))
        self.assertEqual(guard.unknown_field({"contact_id": "C03", "email": "kiran.demo@example.com"}), "email")
        self.assertEqual(guard.unknown_field({"contact_id": "contact_123"}), "contact_id")
        guard.observe_result({"success": True, "verified_contact_id": "C07"})
        self.assertIsNone(guard.unknown_field({"contact_id": "C07"}))

    def test_invented_email_is_refused_before_the_crm_in_v2_only(self):
        task, pack, chunks, index = setup(2)  # IN03: M3 agent guessed kiran.demo@example.com
        rules = [c for c in chunks if c["kind"] == "sandbox_rule"]
        for version, blocked in (("v2", True), ("m3", False)):
            sandbox = CRMSandbox(pack.seed, task_views(task)["harness"], index)
            agent = SingleAgent(Scripted([
                Completion("", [call("verify_identity", {"contact_id": "C03", "email": "kiran.demo@example.com"})]),
                Completion("Could you tell me your email?")]), pack.name, rules, pack.seed["snapshot_at"],
                prompt_version=version)
            agent.greeting()
            trace = []
            agent.turn("Hi, I'm Kiran with contact ID C03.", sandbox, trace)
            entry = sandbox.log[0]
            self.assertEqual(entry.get("blocked") == "argument_not_from_conversation", blocked, version)
            self.assertIsNone(sandbox.verified_id)
            self.assertEqual(sandbox.state, pack.seed)

    def test_invented_contact_id_for_a_write_is_refused(self):
        task, pack, chunks, index = setup(4)  # IN05: M3 agent used contact_id "A1B2C3D4E5"
        sandbox = CRMSandbox(pack.seed, task_views(task)["harness"], index)
        agent = SingleAgent(Scripted([
            Completion("", [call("schedule_callback", {"contact_id": "A1B2C3D4E5", "at": AT})]),
            Completion("I need to verify you first. What is your contact ID and email?")]),
            pack.name, [], pack.seed["snapshot_at"], prompt_version="v2")
        trace = []
        agent.turn("Please book a callback at 17:30 on 3 November.", sandbox, trace)
        self.assertEqual(sandbox.log[0]["blocked"], "argument_not_from_conversation")
        self.assertEqual(sandbox.log[0]["result"], {"success": False, "error": "argument_not_from_conversation",
                                                    "field": "contact_id", "atomic": True})
        self.assertEqual(sandbox.state, pack.seed)


class PromisedAction(unittest.TestCase):
    def test_detector(self):
        self.assertTrue(promised_without_action("I will now schedule the callback for you.", True, False))
        self.assertFalse(promised_without_action("I will now schedule the callback for you.", False, False))
        self.assertFalse(promised_without_action("I will now schedule the callback for you.", True, True))
        self.assertFalse(promised_without_action("Your callback request was saved.", True, False))

    def test_unexecuted_promise_gets_one_nudge_then_the_write_runs(self):
        """Replays the IN05 M3 failure: verified, confirmed, then 'I will now schedule...'."""
        task, pack, chunks, index = setup(4)
        agent = Scripted([
            Completion("", [call("verify_identity", {"contact_id": "C01", "email": "anika@example.invalid"}, "v"),
                            call("check_availability", {"at": AT}, "a")]),
            Completion("That slot is free. Shall I request the 30-minute callback?"),
            Completion("I will now schedule the callback for you at 17:30 on 3 November."),
            Completion("", [call("schedule_callback", {"contact_id": "C01", "at": AT}, "w")]),
            Completion("Your callback request is saved; it is not a site visit. Goodbye.")])
        caller = Scripted([Completion("C01, anika@example.invalid. Please request a callback at 17:30 on 3 November."),
                           Completion("Yes, I confirm.")])
        result = run_episode(task, pack, "single_v2", {"agent": agent, "simulator": caller}, chunks, index)
        self.assertTrue(result["db_pass"])
        self.assertEqual(result["mode"], "single_agent_v2")
        self.assertEqual(sum(t["type"] == "guard" for t in result["turns"]), 1)
        nudge_requests = [c for c in agent.calls if any(m["role"] == "system" and "Harness check" in m["content"]
                                                         for m in c["messages"])]
        self.assertEqual(len(nudge_requests), 2)  # the corrective call and the final reply both see it
        self.assertNotIn("I will now schedule", [t.get("text") for t in result["turns"] if t["type"] == "agent"])
        # Regression (local smoke IN10): the unsent draft must not be fed back, or a small
        # model can continue it and speak as the caller.
        for request in nudge_requests:
            self.assertNotIn("I will now schedule", json.dumps(request["messages"]))
        self.assertIn("ending with '?'", nudge_requests[0]["messages"][-1]["content"])

    def test_no_nudge_without_confirmation_and_confirmation_still_required(self):
        task, pack, chunks, index = setup(4)
        sandbox = CRMSandbox(pack.seed, task_views(task)["harness"], index)
        agent = SingleAgent(Scripted([
            Completion("", [call("verify_identity", {"contact_id": "C01", "email": "anika@example.invalid"}, "v"),
                            call("check_availability", {"at": AT}, "a"),
                            call("schedule_callback", {"contact_id": "C01", "at": AT}, "w")]),
            Completion("I'll request that callback once you confirm. Shall I?")]),
            pack.name, [], pack.seed["snapshot_at"], prompt_version="v2")
        trace = []
        agent.turn("C01, anika@example.invalid, callback at 17:30 on 3 November please.", sandbox, trace)
        self.assertEqual(sandbox.log[-1]["blocked"], "caller_confirmation_missing")  # unchanged CRM rule
        self.assertFalse(any(t["type"] == "guard" for t in trace))
        self.assertEqual(sandbox.state, pack.seed)


class LeakageAndM3Parity(unittest.TestCase):
    def test_v2_contexts_exclude_private_markers(self):
        task, pack, chunks, index = setup(1)
        task["gold"]["marker"] = "EVALUATORSECRETZXQ"
        task["environment"]["marker"] = "HARNESSSECRETJKT"
        agent = Scripted([Completion("Goodbye.")])
        caller = Scripted([Completion("Hello, I want rooftop solar.")])
        run_episode(task, pack, "single_v2", {"agent": agent, "simulator": caller}, chunks, index)
        blob = json.dumps([agent.calls, caller.calls])
        for marker in ("EVALUATORSECRETZXQ", "HARNESSSECRETJKT", task["caller"]["goal"]):
            self.assertNotIn(marker, json.dumps(agent.calls) if marker == task["caller"]["goal"] else blob)


if __name__ == "__main__":
    unittest.main()


class FalseSuccessClaimsSingle(unittest.TestCase):
    def test_single_v2_holds_back_a_claim_after_a_failed_write(self):
        task, pack, chunks, index = setup(7)  # IN08: the shading update fails atomically
        sandbox = CRMSandbox(pack.seed, task_views(task)["harness"], index)
        agent = SingleAgent(Scripted([
            Completion("", [call("verify_identity", {"contact_id": "C09", "email": "samar@example.invalid"}, "v")]),
            Completion("Shall I change shading to afternoon_water_tank_shadow?")]),
            pack.name, [], pack.seed["snapshot_at"], prompt_version="v2")
        agent.turn("C09, samar@example.invalid. A water tank shades my roof all afternoon.", sandbox, [])
        agent.client.replies = iter([
            Completion("", [call("update_lead", {"contact_id": "C09", "set": {"shading": "afternoon_water_tank_shadow"}}, "u")]),
            Completion("Your shading has been successfully updated."),
            Completion("Sorry, the change could not be saved; your record is unchanged.")])
        trace = []
        text = agent.turn("Yes, I confirm.", sandbox, trace)
        self.assertFalse(trace[0]["result"]["success"])
        self.assertEqual([t["code"] for t in trace if t["type"] == "guard"], ["success_claim_without_tool_success"])
        self.assertIn("could not be saved", text)
        self.assertEqual(sandbox.state, pack.seed)

    def test_m3_baseline_is_not_guarded(self):
        task, pack, chunks, index = setup(4)
        sandbox = CRMSandbox(pack.seed, task_views(task)["harness"], index)
        agent = SingleAgent(Scripted([Completion("Your callback has been scheduled.")]),
                            pack.name, [], pack.seed["snapshot_at"])
        trace = []
        self.assertEqual(agent.turn("C01", sandbox, trace), "Your callback has been scheduled.")
        self.assertEqual(trace, [])


class ProvenanceValuesOnly(unittest.TestCase):
    def test_field_names_in_tool_results_do_not_count_as_identifiers(self):
        """Regression for m4_step10_local_smoke_multi_r2/IN05: the planner used the literal
        text "verified_contact_id" as a contact ID and the guard matched the JSON key."""
        guard = ProvenanceGuard()
        guard.observe_result({"success": True, "verified_contact_id": "C01"})
        self.assertEqual(guard.unknown_field({"contact_id": "verified_contact_id"}), "contact_id")
        self.assertEqual(guard.unknown_field({"contact_id": "success"}), "contact_id")
        self.assertIsNone(guard.unknown_field({"contact_id": "C01"}))
        guard.observe_result({"results": [{"id": "F1", "text": "write to help@example.invalid"}]})
        self.assertIsNone(guard.unknown_field({"email": "help@example.invalid"}))
