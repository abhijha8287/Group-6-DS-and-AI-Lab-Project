"""Offline tests for the M3 pipeline (no LLM, no network).

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business, select_tasks  # noqa: E402
from voice_agent.data.preprocess import AGENT_FORBIDDEN, chunk_knowledge, task_views, estimate_tokens # noqa: E402
from voice_agent.evaluation.evaluator import expected_state  # noqa: E402
from voice_agent.inference.crm import CRMSandbox, is_confirmation  # noqa: E402
from voice_agent.inference.outbound_gate import evaluate  # noqa: E402
from voice_agent.inference.retrieval import BM25Index  # noqa: E402
from voice_agent.models.llm import AnthropicClient, OpenAICompatibleClient  # noqa: E402
from voice_agent.pipelines.episode import run_subset  # noqa: E402
from voice_agent.data.preprocess import validate_knowledge_sources

SOLAR = load_business("solar")


def sandbox_for(task_id):
    return CRMSandbox(SOLAR.seed, task_views(SOLAR.scenario(task_id))["harness"])


class TestData(unittest.TestCase):
    def test_chunks_one_per_row(self):
        chunks = chunk_knowledge(SOLAR)
        self.assertEqual(len(chunks), 15)
        self.assertEqual({c["kind"] for c in chunks}, {"sourced_fact", "sandbox_rule"})
        self.assertTrue(all(c["sources"] for c in chunks if c["kind"] == "sourced_fact"))

    def test_agent_view_has_no_answer_key(self):
        for task in SOLAR.scenarios:
            self.assertFalse(AGENT_FORBIDDEN & set(task_views(task)["agent"]))

    def test_test_split_refused_for_dev_runs(self):
        with self.assertRaises(ValueError):
            select_tasks(SOLAR, ["IN35"], split="dev")

    def test_retrieval_finds_blackout_fact(self):
        index = BM25Index([c for c in chunk_knowledge(SOLAR) if c["kind"] == "sourced_fact"])
        self.assertEqual(index.search("blackout grid connected battery")[0]["id"], "F2")


class TestOutboundGate(unittest.TestCase):
    def test_all_30_cases_match_labels(self):
        for key in ("solar", "dental", "furniture"):
            pack = load_business(key)
            for case in pack.outbound_cases:
                self.assertEqual(evaluate(pack.seed, case), case["expected"], f"{key}/{case['id']}")

    def test_unknown_contact_fails_closed(self):
        case = {"contact_id": "C99", "event_id": "X", "at": "2026-11-02T11:00:00+05:30"}
        self.assertEqual(evaluate(SOLAR.seed, case), {"allowed": False, "reasons": ["unknown_contact"]})

    def test_hours_checked_in_india_time(self):
        # 05:30 UTC is 11:00 IST, so the hour rule must not block it.
        case = dict(SOLAR.outbound_cases[0], at="2026-11-02T05:30:00+00:00")
        self.assertNotIn("outside_calling_hours", evaluate(SOLAR.seed, case)["reasons"])


class TestValidationLayer(unittest.TestCase):
    def test_write_needs_verification(self):
        box = sandbox_for("IN03")
        box.confirmed = True
        result = box.execute("update_lead", {"contact_id": "C03", "set": {"roof_permission": "unknown"}})
        self.assertEqual(result["error"], "identity_not_verified")

    def test_write_needs_confirmation_and_right_target(self):
        box = sandbox_for("IN03")
        box.execute("verify_identity", {"contact_id": "C03", "email": "kiran.b@example.invalid"})
        args = {"contact_id": "C03", "set": {"roof_permission": "landlord_approval_pending"}}
        self.assertEqual(box.execute("update_lead", args)["error"], "caller_confirmation_missing")
        box.confirmed = True
        wrong = {"contact_id": "C02", "set": {"roof_permission": "landlord_approval_pending"}}
        self.assertEqual(box.execute("update_lead", wrong)["error"], "wrong_target_contact")
        self.assertTrue(box.execute("update_lead", args)["success"])

    def test_failed_write_is_atomic(self):
        box = sandbox_for("IN08")
        before = SOLAR.seed
        box.execute("verify_identity", {"contact_id": "C09", "email": "samar@example.invalid"})
        box.confirmed = True
        result = box.execute("update_lead", {"contact_id": "C09", "set": {"shading": "afternoon_water_tank_shadow"}})
        self.assertFalse(result["success"])
        self.assertEqual(box.state, before)

    def test_name_alone_cannot_verify(self):
        box = sandbox_for("IN04")
        self.assertFalse(box.execute("verify_identity", {"contact_id": "C02", "email": "kiran.a@example.invalid"})["success"])

    def test_confirmation_rule(self):
        self.assertTrue(is_confirmation("Shall I save it?", "Yes, I confirm."))
        self.assertTrue(is_confirmation("Shall I save it?", "Sure, go ahead"))
        self.assertFalse(is_confirmation("I saved it.", "Yes"))          # no question asked
        self.assertFalse(is_confirmation("Shall I save it?", "No, not yet"))
        self.assertFalse(is_confirmation("Shall I save it?", "Stop all voice follow-up"))


class TestEndToEndWithoutLLM(unittest.TestCase):
    def test_oracle_reproduces_every_gold_state(self):
        run = run_subset(SOLAR, select_tasks(SOLAR, [t["id"] for t in SOLAR.scenarios]), "oracle", {},
                         run_id="unittest_oracle", out_dir=Path(self._tmp()), log=lambda *_: None)
        self.assertEqual(run["summary"]["db_pass_rate"], 1.0)

    def test_skipping_confirmation_is_blocked(self):
        run = run_subset(SOLAR, select_tasks(SOLAR, ["IN03", "IN05"]), "control_skip_confirmation", {},
                         run_id="unittest_control", out_dir=Path(self._tmp()), log=lambda *_: None)
        self.assertEqual(run["summary"]["db_pass_rate"], 0.0)
        self.assertGreater(run["summary"]["blocked_unsafe_attempts"], 0)

    def test_expected_state_keeps_history(self):
        state = expected_state(SOLAR.seed, SOLAR.scenario("IN10")["gold"])
        c01 = next(c for c in state["contacts"] if c["id"] == "C01")
        self.assertTrue(c01["opted_out"] and c01["consent"] and c01["history"])

    def _tmp(self):
        import tempfile
        return tempfile.mkdtemp()


class TestProviderAdapters(unittest.TestCase):
    MESSAGES = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "t1", "name": "find_lead", "arguments": {"email": "a@example.invalid"}}]},
        {"role": "tool", "tool_call_id": "t1", "content": "{\"success\": true}"},
    ]

    def test_openai_round_trip(self):
        wire = OpenAICompatibleClient.to_wire(self.MESSAGES)
        self.assertEqual(wire[2]["tool_calls"][0]["function"]["name"], "find_lead")
        reply = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "x", "function": {"name": "search_docs", "arguments": "{\"query\": \"subsidy\"}"}}]}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2}}
        parsed = OpenAICompatibleClient.from_wire(reply)
        self.assertEqual(parsed.tool_calls[0]["arguments"], {"query": "subsidy"})
        self.assertEqual(parsed.usage["input_tokens"], 10)

    def test_anthropic_round_trip(self):
        system, wire = AnthropicClient.to_wire(self.MESSAGES)
        self.assertEqual(system, "sys")
        self.assertEqual(wire[1]["content"][0]["type"], "tool_use")
        self.assertEqual(wire[2]["content"][0]["type"], "tool_result")
        reply = {"content": [{"type": "text", "text": "ok"},
                             {"type": "tool_use", "id": "u", "name": "find_lead", "input": {"email": "b"}}],
                 "usage": {"input_tokens": 7, "output_tokens": 3}}
        parsed = AnthropicClient.from_wire(reply)
        self.assertEqual((parsed.content, parsed.tool_calls[0]["name"]), ("ok", "find_lead"))



class TestPreprocessing(unittest.TestCase):

    def test_token_estimation_is_positive(self):
        self.assertGreater(estimate_tokens("Hello world"), 0)

    def test_empty_text_token_estimation(self):
        self.assertEqual(estimate_tokens(""), 1)

    def test_token_estimation_is_deterministic(self):
        text = "This is a sample knowledge chunk."
        self.assertEqual(
            estimate_tokens(text),
            estimate_tokens(text)
        )

    def test_business_isolation_in_chunks(self):
        dental = load_business("dental")
        furniture = load_business("furniture")

        dental_chunks = chunk_knowledge(dental)
        furniture_chunks = chunk_knowledge(furniture)

        for chunk in dental_chunks:
            self.assertEqual(
                chunk["business_id"],
                "brightsmile_pilot"
            )

        for chunk in furniture_chunks:
            self.assertEqual(
                chunk["business_id"],
                "urbannest_pilot"
            )

    def test_agent_view_contains_only_task_id(self):
        for task in SOLAR.scenarios:
            views = task_views(task)

            self.assertEqual(
                set(views["agent"].keys()),
                {"id"}
            )

    def test_agent_view_rejects_answer_key_leakage(self):
        views = task_views(SOLAR.scenarios[0])

        views["agent"]["gold"] = {"some": "answer"}

        with self.assertRaises(AssertionError):
            from voice_agent.data.preprocess import check_views
            check_views(views)
    
    def test_all_knowledge_sources_exist(self):
        for business in ("solar", "dental", "furniture"):
            pack = load_business(business)
            validate_knowledge_sources(pack)



if __name__ == "__main__":
    unittest.main()
