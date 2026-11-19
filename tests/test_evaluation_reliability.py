"""Offline evaluator contract and attempt-retention regressions; no provider calls."""

import copy
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business
from voice_agent.evaluation.evaluator import score, validate_verdict
from voice_agent.inference.retrieval import BM25Index
from voice_agent.models.llm import Completion, LLMError
from voice_agent.pipelines.episode import run_episode, run_subset, summarise
from voice_agent.utils.common import write_json

SOLAR = load_business("solar")
TASK = SOLAR.scenario("IN01")


def verdict_for(task=TASK):
    return {
        "required": [{"item": i + 1, "met": True, "evidence": "Synthetic agent quote."}
                     for i in range(len(task["required_information"]))],
        "prohibited": [{"item": i + 1, "violated": False, "evidence": "No prohibited action."}
                       for i in range(len(task["prohibited_actions"]))],
        "false_success_claim": False,
    }


def client_for(text):
    client = Mock()
    client.complete.return_value = Completion(content=text, usage={"input_tokens": 10, "output_tokens": 2})
    return client


def score_text(text, state=None, log=None):
    return score(TASK, SOLAR.seed, SOLAR.seed if state is None else state, [], log or [],
                 judge_client=client_for(text))


class TestJudgeValidation(unittest.TestCase):
    def test_valid_boolean_scores_and_out_of_order_ids(self):
        verdict = verdict_for()
        verdict["required"].reverse()
        result = score_text(json.dumps(verdict))
        self.assertEqual(result["judge_status"], "valid")
        self.assertEqual(result["reward"], 1)
        self.assertEqual(result["cause_classification"], "none")
        verdict["required"][0]["met"] = False
        failed = score_text(json.dumps(verdict))
        self.assertEqual(failed["judge_status"], "valid")
        self.assertFalse(failed["communicate_pass"])
        self.assertEqual(failed["reward"], 0)
        self.assertEqual(failed["cause_classification"], "agent")

    def test_invalid_verdicts_are_evaluation_errors_not_agent_failures(self):
        mutations = [
            ("missing root field", lambda v: v.pop("false_success_claim")),
            ("extra root field", lambda v: v.update(unexpected=True)),
            ("missing required item", lambda v: v["required"].pop()),
            ("missing prohibited item", lambda v: v["prohibited"].pop()),
            ("empty required", lambda v: v.update(required=[])),
            ("empty prohibited", lambda v: v.update(prohibited=[])),
            ("duplicate required ID", lambda v: v["required"][1].update(item=1)),
            ("duplicate prohibited ID", lambda v: v["prohibited"][1].update(item=1)),
            ("unknown required ID", lambda v: v["required"][0].update(item=99)),
            ("unknown prohibited ID", lambda v: v["prohibited"][0].update(item=99)),
            ("zero ID", lambda v: v["required"][0].update(item=0)),
            ("boolean ID", lambda v: v["required"][0].update(item=True)),
            ("float ID", lambda v: v["required"][0].update(item=1.0)),
            ("string ID", lambda v: v["required"][0].update(item="1")),
            ("string met", lambda v: v["required"][0].update(met="false")),
            ("integer violated", lambda v: v["prohibited"][0].update(violated=0)),
            ("null flag", lambda v: v["required"][0].update(met=None)),
            ("string false success", lambda v: v.update(false_success_claim="false")),
            ("integer false success", lambda v: v.update(false_success_claim=0)),
            ("missing evidence", lambda v: v["required"][0].pop("evidence")),
            ("blank evidence", lambda v: v["required"][0].update(evidence="  ")),
            ("numeric evidence", lambda v: v["prohibited"][0].update(evidence=123)),
            ("missing flag", lambda v: v["required"][0].pop("met")),
            ("extra entry field", lambda v: v["required"][0].update(other="value")),
            ("nonobject entry", lambda v: v["required"].__setitem__(0, "bad")),
            ("nonlist group", lambda v: v.update(prohibited={})),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                verdict = verdict_for()
                mutate(verdict)
                raw = json.dumps(verdict)
                result = score_text(raw)
                self.assertTrue(result["db_pass"])
                self.assertEqual(result["judge_status"], "error")
                self.assertEqual(result["cause_classification"], "judge")
                self.assertEqual(result["issues"][0]["code"], "evaluation_error")
                self.assertEqual(result["judge_attempt"]["raw_response"], raw)
                self.assertEqual(result["judge_attempt"]["usage"]["input_tokens"], 10)
                for key in ("communicate_pass", "safety_pass", "false_success_claim", "reward"):
                    self.assertIsNone(result[key], key)

    def test_malformed_json_root_and_duplicate_json_keys(self):
        for raw in ("not JSON", "{} trailing", "[]", "null", '{"required":[],"required":[]}'):
            with self.subTest(raw=raw):
                result = score_text(raw)
                self.assertEqual(result["judge_status"], "error")
                self.assertIsNone(result["reward"])
                self.assertEqual(result["judge_attempt"]["raw_response"], raw)

    def test_empty_rubrics_accept_only_empty_groups(self):
        task = {"required_information": [], "prohibited_actions": []}
        validate_verdict({"required": [], "prohibited": [], "false_success_claim": False}, task)

    def test_infrastructure_error_is_not_invalid_verdict_or_agent_failure(self):
        client = Mock()
        client.complete.side_effect = LLMError("synthetic timeout")
        result = score(TASK, SOLAR.seed, SOLAR.seed, [], [], client)
        self.assertEqual(result["judge_status"], "error")
        self.assertEqual(result["cause_classification"], "infrastructure")
        self.assertEqual(result["issues"][0]["stage"], "judge")
        self.assertIsNone(result["reward"])
        self.assertIsNone(result["judge_attempt"]["raw_response"])
        self.assertIn("Grading rules", result["judge_attempt"]["prompt"])

    def test_deterministic_state_and_tools_survive_invalid_judgment(self):
        state = copy.deepcopy(SOLAR.seed)
        state["contacts"][0]["name"] = "Changed synthetic name"
        tool_log = [{"tool": "update_lead", "blocked": "identity_not_verified",
                     "result": {"success": False, "error": "identity_not_verified", "atomic": True}}]
        result = score_text("{}", state, tool_log)
        self.assertFalse(result["db_pass"])
        self.assertTrue(result["db_diff"])
        self.assertEqual(result["tool_log"], tool_log)
        self.assertEqual(result["blocked_unsafe_attempts"], ["update_lead:identity_not_verified"])
        self.assertEqual(result["cause_classification"], "mixed")
        self.assertIsNone(result["reward"])

    def test_no_judge_is_explicitly_unjudged(self):
        result = score(TASK, SOLAR.seed, SOLAR.seed, [], [])
        self.assertEqual(result["judge_status"], "not_requested")
        self.assertIsNone(result["judge_attempt"])
        self.assertIsNone(result["false_success_claim"])
        self.assertIsNone(result["reward"])

    def test_prompt_requires_spoken_information_not_silence_or_retrieval(self):
        tool = {"type": "tool", "name": "search_docs", "arguments": {},
                "result": {"long": "x" * 600, "tail": "must remain visible"}}
        client = client_for(json.dumps(verdict_for()))
        result = score(TASK, SOLAR.seed, SOLAR.seed, [tool], [], client)
        prompt = result["judge_attempt"]["prompt"]
        self.assertIn("Silence about a topic is NOT conveying", prompt)
        self.assertIn("Only AGENT speech counts", prompt)
        self.assertIn("must remain visible", prompt)

    def test_saved_in01_is_invalid_but_in09_still_needs_semantic_review(self):
        historical = json.loads((Path(__file__).resolve().parents[1] /
                                 "experiments/runs/m3_llm_qwen3-8b_local/results.json").read_text())
        for task_id, expected_status in (("IN01", "error"), ("IN09", "valid")):
            with self.subTest(task_id=task_id):
                original = next(r for r in historical["results"] if r["task_id"] == task_id)
                verdict = {k: v for k, v in original["judge"].items() if k != "usage"}
                task = SOLAR.scenario(task_id)
                result = score(task, SOLAR.seed, SOLAR.seed, original["turns"], [],
                               client_for(json.dumps(verdict)))
                self.assertEqual(result["judge_status"], expected_status)
                self.assertEqual(original["reward"], 0 if task_id == "IN01" else 1)
                if task_id == "IN01":
                    self.assertIsNone(result["reward"])
                else:
                    self.assertEqual(result["reward"], 1)  # schema validation cannot adjudicate meaning


class TestEpisodeRetention(unittest.TestCase):
    def test_invalid_judgments_keep_both_tasks_and_refuse_run_overwrite(self):
        clients = {"agent": client_for("Goodbye."), "simulator": client_for("Question."),
                   "judge": client_for("{}")}
        with tempfile.TemporaryDirectory() as tmp:
            tasks = [SOLAR.scenario(t) for t in ("IN01", "IN09")]
            run = run_subset(SOLAR, tasks, "llm", clients, run_id="attempt", out_dir=Path(tmp), log=lambda *_: None)
            path = Path(run["out_dir"]) / "results.json"
            saved = json.loads(path.read_text())
            self.assertEqual(saved["run_status"], "complete")
            self.assertEqual(len(saved["results"]), 2)
            self.assertEqual(run["summary"]["evaluation_error_tasks"], 2)
            self.assertEqual(run["summary"]["scored_tasks"], 0)
            self.assertIsNone(run["summary"]["task_success_rate"])
            self.assertIsNone(run["summary"]["false_success_claims"])
            self.assertTrue(all(r["judge_attempt"]["raw_response"] == "{}" for r in saved["results"]))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                run_subset(SOLAR, tasks, "llm", clients, run_id="attempt", out_dir=Path(tmp))
            self.assertEqual(path.read_bytes(), before)

    def test_partial_tool_trace_survives_agent_transport_failure(self):
        agent = Mock()
        agent.complete.side_effect = [Completion(content="", tool_calls=[{"id": "t1", "name": "search_docs",
                                                              "arguments": {"query": "subsidy"}}]),
                                      LLMError("synthetic transport failure")]
        judge = Mock()
        result = run_episode(TASK, SOLAR, "llm", {"agent": agent, "simulator": client_for("Question"),
                                                   "judge": judge}, [], BM25Index([]))
        self.assertTrue(result["status"].startswith("error"))
        self.assertEqual(result["cause_classification"], "infrastructure")
        self.assertEqual(len(result["tool_log"]), 1)
        self.assertEqual(sum(t["type"] == "tool" for t in result["turns"]), 1)
        self.assertIsNone(result["reward"])
        judge.complete.assert_not_called()

    def test_repeat_stop_and_judge_failure_have_separate_causes(self):
        clients = {"agent": client_for("What else?"), "simulator": client_for("No."),
                   "judge": client_for("{}")}
        result = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
        self.assertEqual(result["status"], "caller_repeat_stop")
        self.assertEqual(result["cause_classification"], "mixed")
        self.assertEqual({i["category"] for i in result["issues"]}, {"simulator", "judge"})
        self.assertEqual(result["issues"][-1]["discarded_caller_text"], "No.")
        self.assertIsNone(result["reward"])
        clients["judge"] = client_for(json.dumps(verdict_for()))
        passed = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
        self.assertEqual(passed["reward"], 1)
        self.assertEqual(passed["cause_classification"], "simulator")

    def test_component_exception_is_not_a_scored_agent_failure(self):
        for component in ("agent", "simulator"):
            with self.subTest(component=component):
                clients = {"agent": client_for("Goodbye."), "simulator": client_for("Question")}
                clients[component].complete.side_effect = ValueError("synthetic component failure")
                result = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
                self.assertEqual(result["cause_classification"], component)
                self.assertIsNone(result["reward"])

    def test_summary_reports_invalid_coverage_without_silent_exclusion(self):
        clients = {"agent": client_for("Goodbye."), "simulator": client_for("Question"),
                   "judge": client_for(json.dumps(verdict_for()))}
        valid = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
        clients["judge"] = client_for("{}")
        invalid = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
        summary = summarise([valid, invalid])
        self.assertEqual(summary["scored_tasks"], 1)
        self.assertEqual(summary["unscored_tasks"], 1)
        self.assertEqual(summary["judged_tasks"], 1)
        self.assertEqual(summary["evaluation_error_tasks"], 1)
        self.assertIsNone(summary["task_success_rate"])
        self.assertEqual(summary["task_success_rate_scored"], 1)
        self.assertIsNone(summary["communicate_rate"])
        self.assertIsNone(summary["safety_rate"])
        self.assertIsNone(summary["false_success_claims"])
        self.assertEqual(summary["communicate_rate_judged"], 1)
        self.assertEqual(summary["safety_rate_judged"], 1)
        self.assertEqual(summary["false_success_claims_judged"], 0)

    def test_scoring_error_preserves_current_trace_and_state(self):
        agent = Mock()
        agent.complete.side_effect = [Completion(content="", tool_calls=[
            {"id": "t1", "name": "search_docs", "arguments": {"query": "subsidy"}}]),
            Completion(content="Goodbye.")]
        judge = Mock()
        with patch("voice_agent.evaluation.evaluator.expected_state", side_effect=ValueError("bad gold")):
            result = run_episode(TASK, SOLAR, "llm", {"agent": agent,
                                 "simulator": client_for("Question"), "judge": judge}, [], BM25Index([]))
        self.assertIsNone(result["db_pass"])
        self.assertIsNone(result["db_diff"])
        self.assertIsNone(result["reward"])
        self.assertEqual(result["cause_classification"], "infrastructure")
        self.assertEqual(result["issues"][0]["stage"], "scoring")
        self.assertEqual(len(result["tool_log"]), 1)
        self.assertTrue(result["turns"])
        self.assertEqual(result["final_state"], SOLAR.seed)
        judge.complete.assert_not_called()

    def test_trace_error_and_transport_failure_both_classified(self):
        agent = Mock()
        agent.name, agent.usage = "synthetic", {}
        agent.greeting.return_value = "Welcome."

        def fail_after_trace(text, sandbox, trace):
            trace.append({"type": "error", "error": "tool_round_limit"})
            raise LLMError("synthetic transport failure")

        agent.turn.side_effect = fail_after_trace
        with patch("voice_agent.pipelines.episode.SingleAgent", return_value=agent):
            result = run_episode(TASK, SOLAR, "llm", {"agent": None,
                                 "simulator": client_for("Question")}, [], BM25Index([]))
        self.assertEqual(result["cause_classification"], "mixed")
        self.assertEqual({i["category"] for i in result["issues"]}, {"agent", "infrastructure"})
        self.assertEqual(sum(t["type"] == "error" for t in result["turns"]), 1)

    def test_failed_checkpoint_keeps_prior_and_current_tasks(self):
        failed_once = False

        def checkpoint(path, data):
            nonlocal failed_once
            if path.name == "results.json" and len(data["results"]) == 2 and not failed_once:
                failed_once = True
                raise OSError("synthetic checkpoint failure")
            write_json(path, data)

        with tempfile.TemporaryDirectory() as tmp:
            with patch("voice_agent.pipelines.episode.write_json", side_effect=checkpoint):
                with self.assertRaises(OSError):
                    run_subset(SOLAR, [TASK, SOLAR.scenario("IN09")], "oracle", {},
                               run_id="checkpoint", out_dir=Path(tmp), log=lambda *_: None)
            out = Path(tmp) / "checkpoint"
            saved = json.loads((out / "results.json").read_text())
            self.assertEqual(saved["run_status"], "error")
            self.assertEqual([r["task_id"] for r in saved["results"]], ["IN01", "IN09"])
            self.assertTrue((out / "run_error.json").is_file())

    def test_unknown_write_task_coverage_cannot_report_perfect_rate(self):
        known = run_episode(SOLAR.scenario("IN02"), SOLAR, "oracle", {}, [], BM25Index([]))
        unknown = copy.deepcopy(known)
        unknown.update(writes_expected=None, db_pass=None)
        summary = summarise([known, unknown])
        self.assertIsNone(summary["db_pass_rate_write_tasks"])
        self.assertIsNone(summary["db_pass_rate"])
        self.assertEqual(summary["crm_scored_tasks"], 1)

    def test_partial_run_has_no_whole_run_success_metrics(self):
        clients = {"agent": client_for("Goodbye."), "simulator": client_for("Question"),
                   "judge": client_for(json.dumps(verdict_for()))}
        valid = run_episode(TASK, SOLAR, "llm", clients, [], BM25Index([]))
        summary = summarise([valid], planned_tasks=2)
        self.assertEqual(summary["unrecorded_tasks"], 1)
        for key in ("task_success_rate", "db_pass_rate", "communicate_rate", "safety_rate",
                    "false_success_claims"):
            self.assertIsNone(summary[key], key)
        self.assertEqual(summary["task_success_rate_scored"], 1)

    def test_projection_failure_keeps_canonical_checkpoint_with_state(self):
        def fail_projection(path, data):
            if path.name == "final_states.json" and data:
                raise OSError("synthetic projection write failure")
            write_json(path, data)

        with tempfile.TemporaryDirectory() as tmp:
            with patch("voice_agent.pipelines.episode.write_json", side_effect=fail_projection):
                with self.assertRaises(OSError):
                    run_subset(SOLAR, [SOLAR.scenario("IN02"), TASK], "oracle", {},
                               run_id="projection", out_dir=Path(tmp), log=lambda *_: None)
            out = Path(tmp) / "projection"
            saved = json.loads((out / "results.json").read_text())
            self.assertEqual(saved["run_status"], "error")
            self.assertEqual(saved["results"][0]["task_id"], "IN02")
            self.assertEqual(len(saved["results"][0]["final_state"]["contacts"]), 13)
            self.assertIsNone(saved["summary"]["db_pass_rate"])
            self.assertEqual(json.loads((out / "final_states.json").read_text()), {})
            self.assertEqual(json.loads((out / "run_error.json").read_text())["task_id"], "IN02")

    def test_preprocessing_failure_keeps_attempt_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("voice_agent.pipelines.episode.chunk_knowledge", side_effect=ValueError("bad fixture")):
                with self.assertRaises(ValueError):
                    run_subset(SOLAR, [TASK], "oracle", {}, run_id="broken", out_dir=Path(tmp))
            out = Path(tmp) / "broken"
            self.assertEqual(json.loads((out / "results.json").read_text())["run_status"], "error")
            self.assertEqual(json.loads((out / "run_error.json").read_text())["category"], "infrastructure")


class TestPipelineCLI(unittest.TestCase):
    def test_saved_evaluation_and_episode_errors_exit_nonzero(self):
        script = Path(__file__).resolve().parents[1] / "scripts/run_m3_pipeline.py"
        main = runpy.run_path(str(script))["main"]
        for errors, status in ((1, "completed"), (0, "error: synthetic failure")):
            with self.subTest(errors=errors, status=status):
                saved = {"summary": {"evaluation_error_tasks": errors}, "out_dir": "synthetic",
                         "results": [{"status": status}]}
                with patch.dict(main.__globals__, {"run_subset": Mock(return_value=saved), "load_env": Mock()}), \
                        patch.object(sys, "argv", [str(script), "--mode", "oracle"]), \
                        patch("builtins.print"):
                    with self.assertRaises(SystemExit) as raised:
                        main()
                    self.assertEqual(raised.exception.code, 1)


class TestAtomicWrites(unittest.TestCase):
    def test_failed_replace_does_not_truncate_prior_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            write_json(path, {"attempts": [1]})
            previous = path.read_bytes()
            with patch.object(Path, "replace", side_effect=OSError("synthetic disk failure")):
                with self.assertRaises(OSError):
                    write_json(path, {"attempts": [1, 2]})
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(list(Path(tmp).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
