"""Model transport and runtime limits, with every HTTP send mocked."""
import copy
import json
import sys
import tempfile
import unittest
import urllib.error
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business
from voice_agent.inference.agent import SingleAgent
from voice_agent.inference.retrieval import BM25Index
from voice_agent.models import llm
from voice_agent.models.budget import BudgetError, CostLedger, max_cost_usd
from voice_agent.pipelines import episode
from voice_agent.utils.common import write_json

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-4o-mini-2024-07-18"


class CostControlTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "ledger.json"
        self.data = json.loads((ROOT / "experiments/cost_ledger.json").read_text())
        self.batch = next(b for b in self.data["batches"] if b["id"] == "step5_smoke_001")
        self.data["batches"] = [self.batch]
        self.batch["requests"] = []
        self.batch.pop("halted", None)
        self.batch.pop("halt_reason", None)
        self.batch.update(approved=True, approval_reference="offline-test-only")
        self.save()
        self.budget = CostLedger(self.path, self.batch["id"])

    def save(self):
        write_json(self.path, self.data)

    def read(self):
        return json.loads(self.path.read_text())

    def client(self, role="AGENT"):
        return llm.OpenAICompatibleClient(MODEL, "https://api.openai.com/v1",
                                          "offline-test-key", budget=self.budget, role=role)

    @staticmethod
    def response(**overrides):
        data = {"model": MODEL, "service_tier": "default",
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                "choices": [{"message": {"content": "Synthetic reply"}}]}
        data.update(overrides)
        response = Mock()
        response.read.return_value = json.dumps(data).encode()
        manager = Mock()
        manager.__enter__ = Mock(return_value=response)
        manager.__exit__ = Mock(return_value=False)
        return manager

    def test_proposal_bound_and_unapproved_copy(self):
        bound = max_cost_usd(MODEL, 1200, self.data["models"])
        self.assertEqual(bound, Decimal("0.019920"))
        self.assertEqual(bound * 4, Decimal("0.079680"))
        self.assertLess(bound * 4, Decimal("0.10"))
        self.batch.update(approved=False, approval_reference=None)
        self.save()
        with patch.object(llm._HTTP, "open") as send, self.assertRaises(BudgetError):
            self.client().complete([{"role": "user", "content": "Synthetic"}])
        send.assert_not_called()

    def test_four_roles_reserve_before_send_and_share_request_cap(self):
        def send(request, timeout):
            stored = self.read()
            entry = stored["batches"][0]["requests"][-1]
            self.assertEqual(entry["status"], "pending")
            self.assertGreater(Decimal(stored["totals"]["unreconciled_max_usd"]), 0)
            payload = json.loads(request.data)
            self.assertEqual(payload["max_completion_tokens"], 800)
            self.assertNotIn("max_tokens", payload)
            self.assertEqual((payload["service_tier"], payload["n"]), ("default", 1))
            self.assertLessEqual(timeout, 30)
            return self.response()
        with patch.object(llm._HTTP, "open", side_effect=send) as send:
            for role in ("SIMULATOR", "AGENT", "AGENT", "JUDGE"):
                self.client(role).complete([{"role": "user", "content": "Synthetic"}])
            with self.assertRaises(BudgetError):
                self.client().complete([{"role": "user", "content": "Fifth call must not send"}])
        self.assertEqual(send.call_count, 4)
        stored = self.read()
        self.assertEqual([r["role"] for r in stored["batches"][0]["requests"]],
                         ["SIMULATOR", "AGENT", "AGENT", "JUDGE"])
        self.assertEqual(Decimal(stored["totals"]["recorded_usage_usd"]), Decimal("0.000084"))
        self.assertEqual(Decimal(stored["totals"]["unreconciled_max_usd"]), 0)

    def test_each_http_retry_is_reserved_and_unknown_cost_is_held(self):
        self.batch["limits"].update(max_retries=1)
        self.save()
        with patch.object(llm._HTTP, "open", side_effect=[urllib.error.URLError("offline"), self.response()]) as send, \
                patch.object(llm.time, "sleep"):
            self.client("SIMULATOR").complete([{"role": "user", "content": "Synthetic"}])
        self.assertEqual(send.call_count, 2)
        stored = self.read()
        self.assertEqual([r["attempt"] for r in stored["batches"][0]["requests"]], [0, 1])
        self.assertEqual([r["status"] for r in stored["batches"][0]["requests"]], ["failed", "reconciled"])
        self.assertEqual(Decimal(stored["totals"]["unreconciled_max_usd"]), Decimal("0.019680"))
        self.assertEqual(Decimal(stored["totals"]["recorded_usage_usd"]), Decimal("0.000021"))

    def test_retry_cannot_bypass_request_count(self):
        self.batch["limits"].update(max_retries=1, max_requests=1)
        self.save()
        with patch.object(llm._HTTP, "open", side_effect=TimeoutError("offline")) as send, \
                patch.object(llm.time, "sleep"), self.assertRaises(BudgetError):
            self.client().complete([{"role": "user", "content": "Synthetic"}])
        self.assertEqual(send.call_count, 1)
        self.assertEqual(len(self.read()["batches"][0]["requests"]), 1)

    def test_bad_usage_model_or_tier_halts_without_refund(self):
        for overrides in ({"usage": None}, {"usage": {"prompt_tokens": 100}},
                          {"service_tier": "priority"}, {"model": "unexpected"}):
            with self.subTest(overrides=overrides):
                self.save()
                with patch.object(llm._HTTP, "open", return_value=self.response(**overrides)) as send:
                    with self.assertRaises(BudgetError):
                        self.client().complete([{"role": "user", "content": "Synthetic"}])
                    with self.assertRaises(BudgetError):
                        self.client().complete([{"role": "user", "content": "Must stay stopped"}])
                self.assertEqual(send.call_count, 1)
                stored = self.read()
                self.assertTrue(stored["batches"][0]["halted"])
                self.assertEqual(Decimal(stored["totals"]["unreconciled_max_usd"]), Decimal("0.019680"))
                self.assertEqual(Decimal(stored["totals"]["recorded_usage_usd"]), 0)

    def test_failed_halt_write_leaves_pending_interlock_for_other_process(self):
        def save_unless_halted(path, data):
            if data["batches"][0].get("halted"):
                raise OSError("offline halt write failure")
            write_json(path, data)

        with patch.object(llm._HTTP, "open", return_value=self.response(service_tier="priority")) as send:
            with patch("voice_agent.models.budget.write_json", side_effect=save_unless_halted), \
                    self.assertRaises(BudgetError):
                self.client().complete([{"role": "user", "content": "Synthetic"}])
            other = self.client()
            other.budget = CostLedger(self.path, self.batch["id"])
            with self.assertRaises(BudgetError):
                other.complete([{"role": "user", "content": "I/O restored, but pending must block"}])
        self.assertEqual(send.call_count, 1)
        stored = self.read()
        self.assertEqual(stored["batches"][0]["requests"][0]["status"], "pending")
        self.assertEqual(Decimal(stored["totals"]["unreconciled_max_usd"]), Decimal("0.019680"))

    def test_ledger_write_failure_prevents_send(self):
        with patch("voice_agent.models.budget.write_json", side_effect=OSError("offline disk failure")), \
                patch.object(llm._HTTP, "open") as send, self.assertRaises(BudgetError):
            self.client().complete([{"role": "user", "content": "Synthetic"}])
        send.assert_not_called()
        self.assertEqual(self.read()["batches"][0]["requests"], [])

    def test_remote_endpoints_audio_hosted_tools_and_output_limits_are_blocked(self):
        payload = {"model": MODEL, "messages": [{"role": "user", "content": "Synthetic"}],
                   "max_completion_tokens": 800, "n": 1, "service_tier": "default"}
        variants = [{"modalities": ["audio"]}, {"stream": True}, {"n": 2},
                    {"max_completion_tokens": 1201}, {"max_completion_tokens": True},
                    {"messages": [{"role": "user", "content": [{"type": "image_url"}]}]},
                    {"messages": [{"role": "assistant", "content": "", "audio": {"id": "offline"}}]},
                    {"tools": [{"type": "web_search"}]}]
        with patch.object(llm._HTTP, "open") as send:
            for extra in variants:
                with self.subTest(extra=extra), self.assertRaises(BudgetError):
                    llm._post(llm.OPENAI_URL, {**payload, **extra}, {}, 30, budget=self.budget)
            for url in ("https://api.anthropic.com/v1/messages", "https://api.groq.com/openai/v1/chat/completions",
                        "https://custom.invalid/chat/completions", "https://api.openai.com/v1/realtime"):
                with self.subTest(url=url), self.assertRaises(BudgetError):
                    llm._post(url, payload, {}, 30, budget=self.budget)
            with self.assertRaises(BudgetError):
                llm._post(llm.OPENAI_URL, payload, {}, 30)
        send.assert_not_called()
        self.assertEqual(self.read()["batches"][0]["requests"], [])

    def test_malformed_successful_responses_halt_without_refund(self):
        for body in (b"[]", b"null", b"not JSON"):
            with self.subTest(body=body):
                self.save()
                response = self.response()
                response.__enter__.return_value.read.return_value = body
                with patch.object(llm._HTTP, "open", return_value=response) as send:
                    with self.assertRaises((BudgetError, llm.LLMError)):
                        self.client().complete([{"role": "user", "content": "Synthetic"}])
                    with self.assertRaises(BudgetError):
                        self.client().complete([{"role": "user", "content": "Must stay stopped"}])
                self.assertEqual(send.call_count, 1)
                stored = self.read()
                self.assertTrue(stored["batches"][0]["halted"])
                self.assertEqual(Decimal(stored["totals"]["unreconciled_max_usd"]), Decimal("0.019680"))

    def test_reservation_file_and_directory_sync_precede_http(self):
        events = []
        response = self.response()
        with patch("voice_agent.models.budget.os.fsync", side_effect=lambda fd: events.append("sync")), \
                patch.object(llm._HTTP, "open", side_effect=lambda *a, **kw: (events.append("send"), response)[1]):
            self.client().complete([{"role": "user", "content": "Synthetic"}])
        self.assertEqual(events, ["sync", "sync", "send", "sync", "sync"])
        for sync_results in ([OSError("file sync failed")], [None, OSError("directory sync failed")]):
            self.save()
            with patch("voice_agent.models.budget.os.fsync", side_effect=sync_results), \
                    patch.object(llm._HTTP, "open") as send, self.assertRaises(BudgetError):
                self.client().complete([{"role": "user", "content": "Synthetic"}])
            send.assert_not_called()

    def test_local_simulator_can_share_a_run_with_paid_agent(self):
        local = llm.OpenAICompatibleClient("synthetic-local", "http://127.0.0.1:11434/v1",
                                           budget=self.budget, role="SIMULATOR")
        with patch.object(llm._HTTP, "open", return_value=self.response()) as send:
            local.complete([{"role": "user", "content": "Synthetic local caller"}])
            self.assertEqual(self.read()["batches"][0]["requests"], [])
            self.client().complete([{"role": "user", "content": "Synthetic paid agent"}])
        self.assertEqual(send.call_count, 2)
        self.assertEqual([r["role"] for r in self.read()["batches"][0]["requests"]], ["AGENT"])

    def test_local_ollama_has_no_implicit_http_retries(self):
        client = llm.OpenAICompatibleClient("synthetic-local", "http://localhost:11434/v1")
        with patch.object(llm._HTTP, "open", side_effect=TimeoutError("offline")) as send, \
                self.assertRaises(llm.LLMError):
            client.complete([{"role": "user", "content": "Synthetic"}])
        self.assertEqual(send.call_count, 1)

    def test_tool_step_limit_counts_parallel_calls_not_only_rounds(self):
        call = {"id": "offline", "name": "search_docs", "arguments": {"query": "solar"}}
        for budget, first_count, expected_count in ((None, 8, 8), (self.budget, 2, 0)):
            with self.subTest(budget=budget):
                if budget:
                    self.batch["limits"]["max_tool_steps"] = 1
                    self.save()
                client = SimpleNamespace(budget=budget, complete=Mock(side_effect=[
                    llm.Completion("", tool_calls=[copy.deepcopy(call) for _ in range(first_count)]),
                    llm.Completion("", tool_calls=[call])]))
                agent = SingleAgent(client, "Synthetic Solar", [], "2026-11-19")
                sandbox, trace = Mock(), []
                sandbox.execute.return_value = {"success": True}
                agent.turn("Synthetic caller", sandbox, trace)
                self.assertEqual(sandbox.execute.call_count, expected_count)
                errors = [t for t in trace if t.get("error") == "tool_step_limit"]
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0]["requested_tool_calls"])

    def test_budget_refusal_is_infrastructure_not_agent_failure(self):
        self.batch.update(approved=False, approval_reference=None)
        self.save()
        solar = load_business("solar")
        task = solar.scenario("IN01")
        with patch.object(llm._HTTP, "open") as send:
            run = episode.run_episode(task, solar, "llm",
                                      {"agent": self.client(), "simulator": self.client("SIMULATOR"),
                                       "judge": self.client("JUDGE")}, [], BM25Index([]))
            judged = episode.score(task, solar.seed, solar.seed, [], [], judge_client=self.client("JUDGE"))
        send.assert_not_called()
        for result in (run, judged):
            self.assertTrue(result["db_pass"])
            self.assertIsNone(result["reward"])
            self.assertEqual(result["cause_classification"], "infrastructure")
        self.assertEqual(judged["judge_status"], "error")

    def test_approved_batch_can_reduce_caller_turn_limit(self):
        self.batch["limits"]["max_caller_turns"] = 1
        self.save()
        agent, caller = Mock(), Mock()
        agent.name, agent.usage, caller.usage = "offline", {}, {}
        agent.greeting.return_value = "Welcome."
        agent.turn.return_value = "Please continue."
        caller.reply.side_effect = ["First synthetic question", "Second must not be generated"]
        solar = load_business("solar")
        with patch.object(episode, "SingleAgent", return_value=agent), \
                patch.object(episode, "LLMCaller", return_value=caller):
            result = episode.run_episode(solar.scenario("IN01"), solar, "llm",
                                         {"agent": SimpleNamespace(budget=self.budget), "simulator": None},
                                         [], BM25Index([]))
        self.assertEqual(result["status"], "turn_limit")
        self.assertEqual(caller.reply.call_count, 1)
        self.assertEqual(agent.turn.call_count, 1)


if __name__ == "__main__":
    unittest.main()
