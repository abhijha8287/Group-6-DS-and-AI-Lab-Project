"""Offline tests for the restricted OpenRouter adapter."""
import copy
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.models import llm
from voice_agent.models.budget import BudgetError, CostLedger
from voice_agent.models.openrouter_free import FreeOpenRouterClient, MODEL, URL


class FreeOpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.json"
        self.data = {"starting_credit_usd": "1", "allocations": {"pilot": "1"},
                     "models": {MODEL: {"provider": "openrouter_free", "no_charge_only": True,
                                        "input_usd_per_million": "0", "output_usd_per_million": "0",
                                        "max_input_tokens": 262144}},
                     "batches": [{"id": "test", "allocation": "pilot", "model": MODEL,
                                  "approved": True, "approval_reference": "offline", "max_cost_usd": "0",
                                  "limits": {"max_requests": 3, "max_output_tokens": 800,
                                             "max_request_bytes": 64000, "max_retries": 0,
                                             "max_caller_turns": 12, "max_tool_steps": 8,
                                             "max_audio_seconds": 0}, "requests": []}]}
        self.save()
        self.budget = CostLedger(self.path, "test")
        self.events = []
        self.client = FreeOpenRouterClient(self.budget, "secret-key", self.events.append)
        self.messages = [{"role": "user", "content": "hello"}]
        self.response = {"provider": "Google AI Studio", "model": MODEL,
                         "choices": [{"message": {"role": "assistant", "content": None,
                                      "tool_calls": [{"id": "call1", "type": "function", "function": {
                                          "name": "lookup", "arguments": '{"x": 1}'}}]}}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 3, "cost": 0, "is_byok": False,
                                   "cost_details": {"upstream_inference_cost": None}}}

    def save(self):
        self.path.write_text(json.dumps(self.data))

    def stored(self):
        return json.loads(self.path.read_text())["batches"][0]

    def reply(self, data=None, raw=None):
        response = Mock(status=200)
        response.read.return_value = raw if raw is not None else json.dumps(data or self.response).encode()
        manager = Mock()
        manager.__enter__ = Mock(return_value=response)
        manager.__exit__ = Mock(return_value=False)
        return manager

    def test_success_routing_and_reconciliation(self):
        def send(request, timeout):
            self.assertEqual(self.stored()["requests"][0]["status"], "pending")
            self.assertEqual(request.full_url, URL)
            self.assertEqual(timeout, 30)
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], MODEL)
            self.assertEqual(payload["provider"], {"only": ["google-ai-studio"], "order": ["google-ai-studio"],
                             "allow_fallbacks": False, "require_parameters": True,
                             "max_price": {"prompt": 0, "completion": 0}, "data_collection": "deny"})
            self.assertEqual(payload["reasoning"], {"enabled": False, "exclude": True})
            self.assertEqual((payload["temperature"], payload["max_tokens"], payload["stream"]), (0, 800, False))
            self.assertNotIn("usage", payload)
            return self.reply()
        with patch.object(llm._HTTP, "open", side_effect=send):
            result = self.client.complete(self.messages, tools=[{"name": "lookup", "parameters": {"type": "object"}}])
        self.assertEqual(result.tool_calls[0]["arguments"], {"x": 1})
        self.assertGreaterEqual(result.latency_s, 0)
        record = self.stored()["requests"][0]
        self.assertEqual((record["status"], record["role"], record["attempt"]), ("reconciled", "AGENT", 0))
        self.assertEqual(float(record["reserve_max_cost_usd"]), 0)
        self.assertNotIn("secret-key", repr(self.events))
        self.assertEqual([e["event"] for e in self.events], ["request", "response"])

    def test_setup_refusals_do_not_send(self):
        mutations = [lambda d: d["batches"][0].update(approved=False),
                     lambda d: d["models"][MODEL].update(input_usd_per_million="1"),
                     lambda d: d["models"][MODEL].update(provider="openai"),
                     lambda d: d["models"][MODEL].update(no_charge_only=False),
                     lambda d: d["models"][MODEL].update(max_input_tokens=1),
                     lambda d: d["batches"][0].update(max_cost_usd="1"),
                     lambda d: d["batches"][0]["limits"].update(max_retries=1),
                     lambda d: d["batches"][0]["limits"].update(max_output_tokens=799),
                     lambda d: d["batches"][0]["limits"].update(max_request_bytes=64001)]
        original = copy.deepcopy(self.data)
        with patch.object(llm._HTTP, "open") as send:
            with self.assertRaises(BudgetError):
                FreeOpenRouterClient(None, "key").complete(self.messages)
            for mutate in mutations:
                self.data = copy.deepcopy(original)
                mutate(self.data)
                self.save()
                with self.assertRaises(BudgetError):
                    self.client.complete(self.messages)
            send.assert_not_called()

    def test_bad_response_halts_and_preserves_raw(self):
        cases = [{"usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 1}},
                 {"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
                 {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": False}},
                 {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0, "is_byok": True}},
                 {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0, "cost_details": {"upstream_inference_cost": 1}}},
                 {"usage": None}, {"usage": {"prompt_tokens": -1, "completion_tokens": 1, "cost": 0}},
                 {"provider": "other"}, {"model": "other"},
                 {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{"type": "custom"}]}}]}]
        original = copy.deepcopy(self.data)
        for override in cases + [None]:
            with self.subTest(override=override):
                self.data = copy.deepcopy(original)
                self.save()
                self.events.clear()
                data = {**self.response, **(override or {})}
                raw = b"not json" if override is None else json.dumps(data).encode()
                with patch.object(llm._HTTP, "open", return_value=self.reply(raw=raw)) as send:
                    with self.assertRaises((BudgetError, llm.LLMError)):
                        self.client.complete(self.messages)
                    with self.assertRaises(BudgetError):
                        self.client.complete(self.messages)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(self.events[-1]["raw_response"], raw)
                self.assertTrue(self.stored()["halted"])
                self.assertEqual(self.stored()["requests"][0]["status"], "failed")

    def test_bad_argument_json_uses_shared_parser_not_provider_halt(self):
        response=copy.deepcopy(self.response)
        response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]="not-json"
        with patch.object(llm._HTTP,"open",return_value=self.reply(data=response)):
            result=self.client.complete(self.messages)
        self.assertEqual(result.tool_calls[0]["arguments"],{"_unparsed":"not-json"})
        self.assertFalse(self.stored().get("halted",False))

    def test_missing_or_unknown_byok_halts(self):
        for marker in (None,"false",0):
            self.save()
            response=copy.deepcopy(self.response);response["usage"]["is_byok"]=marker
            with patch.object(llm._HTTP,"open",return_value=self.reply(data=response)):
                with self.assertRaises(BudgetError):self.client.complete(self.messages)
            self.assertTrue(self.stored()["halted"])

    def test_normalized_model_and_journal_failure(self):
        response = {**self.response, "model": MODEL.removesuffix(":free")}
        with patch.object(llm._HTTP, "open", return_value=self.reply(data=response)):
            self.client.complete(self.messages)
        self.assertEqual(self.stored()["requests"][0]["status"], "reconciled")
        self.client.journal = Mock(side_effect=RuntimeError("secret-key"))
        with patch.object(llm._HTTP, "open") as send:
            with self.assertRaises(llm.LLMError) as raised:
                self.client.complete(self.messages)
            send.assert_not_called()
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertTrue(self.stored()["halted"])
        self.assertEqual(self.stored()["requests"][-1]["status"], "failed")

    def test_http_error_closed_and_secret_not_in_exception(self):
        body = io.BytesIO(b"secret-key provider body")
        error = urllib.error.HTTPError(URL, 429, "secret-key", {}, body)
        with patch.object(llm._HTTP, "open", side_effect=error) as send:
            with self.assertRaises(llm.LLMError) as raised:
                self.client.complete(self.messages)
        self.assertTrue(body.closed)
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertEqual(self.events[-1]["raw_response"], b"secret-key provider body")
        self.assertEqual(send.call_count, 1)
        self.assertTrue(self.stored()["halted"])

    def test_invalid_input_no_reservation(self):
        variants = [dict(json_mode=True), dict(temperature=1), dict(max_tokens=801),
                    dict(tools=[{"type": "web_search"}]),
                    dict(messages=[{"role": "user", "content": [{"type": "image_url"}]}]),
                    dict(messages=[{"role": "user", "content": "x" * 65000}])]
        with patch.object(llm._HTTP, "open") as send:
            for kwargs in variants:
                kwargs.setdefault("messages", self.messages)
                with self.assertRaises(BudgetError):
                    self.client.complete(**kwargs)
            send.assert_not_called()
        self.assertEqual(self.stored()["requests"], [])


if __name__ == "__main__":
    unittest.main()
