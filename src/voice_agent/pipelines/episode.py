"""Run tasks end to end: load -> preprocess -> converse -> score -> save.

One episode = one task: reset the CRM from the seed, let the simulated caller
and the agent talk in text, execute tool calls through the validation layer,
then score the final CRM state and transcript.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from voice_agent.data.loader import BusinessPack
from voice_agent.data.preprocess import check_views, chunk_knowledge, task_views
from voice_agent.evaluation.evaluator import classify_issues, score, transcript_text
from voice_agent.evaluation.simulator import STOP, LLMCaller, ScriptedCaller
from voice_agent.inference.agent import OracleAgent, SingleAgent
from voice_agent.inference.crm import CRMSandbox
from voice_agent.inference.retrieval import BM25Index
from voice_agent.models.budget import BudgetError, CostLedger
from voice_agent.models.llm import LLMError
from voice_agent.utils.common import RUNS_DIR, write_json

MAX_CALLER_TURNS = 12
# The call ends when the agent signs off without asking anything further.
SIGN_OFF = re.compile(r"\b(goodbye|bye|have a (great|good|nice) day)\b", re.I)


def agent_ended_call(text: str) -> bool:
    return bool(SIGN_OFF.search(text)) and not text.rstrip().endswith("?")


def run_episode(task: dict, pack: BusinessPack, mode: str, clients: dict, chunks: list[dict],
                index: BM25Index, *, checkpoint=None, stop_on_protocol_issue=False) -> dict:
    views = task_views(task)
    check_views(views)
    sandbox = CRMSandbox(pack.seed, views["harness"], index)
    sandbox.checkpoint = checkpoint
    rules = [c for c in chunks if c["kind"] == "sandbox_rule"]

    turns: list[dict] = []
    issues: list[dict] = []
    agent = caller = None
    stage, status = "agent", "completed"
    started = time.perf_counter()
    try:
        if mode == "llm":
            agent = SingleAgent(clients["agent"], pack.name, rules, pack.seed["snapshot_at"])
            stage = "simulator"
            caller = LLMCaller(clients["simulator"], views["simulator"]["caller"])
        elif mode == "oracle":
            agent, caller = OracleAgent(task), ScriptedCaller(views["simulator"]["caller"])
        elif mode.startswith("control_skip_"):
            agent = OracleAgent(task, skip=mode.removeprefix("control_skip_"))
            caller = ScriptedCaller(views["simulator"]["caller"])
        else:
            raise ValueError(f"unknown mode {mode}")
        stage = "agent"
        agent_text = agent.greeting()
        turns.append({"type": "agent", "text": agent_text})
        previous_caller = None
        budget = getattr(clients.get("agent"), "budget", None) if mode == "llm" else None
        caller_limit = budget.limits["max_caller_turns"] if isinstance(budget, CostLedger) else MAX_CALLER_TURNS
        for _ in range(caller_limit):
            if agent_ended_call(agent_text):
                break
            stage = "simulator"
            caller_text = caller.reply(agent_text)
            if STOP in caller_text:
                if stop_on_protocol_issue and not any(t["type"] == "caller" for t in turns):
                    status = "caller_early_stop"
                    issues.append({"category": "simulator", "stage": stage, "code": status,
                                   "message": "Caller stopped before exercising the scenario."})
                break
            if mode == "llm" and caller_text == previous_caller:  # LLM caller stuck repeating itself
                status = "caller_repeat_stop"
                issues.append({"category": "simulator", "stage": stage, "code": status,
                               "message": "Repeat guard ended the episode; goal coverage needs review.",
                               "discarded_caller_text": caller_text})
                break
            previous_caller = caller_text
            turns.append({"type": "caller", "text": caller_text})
            stage = "infrastructure"
            sandbox.on_caller_turn(agent_text, caller_text)
            stage = "agent"
            trace: list[dict] = []
            try:
                agent_text = agent.turn(caller_text, sandbox, trace)
            finally:
                turns += trace  # retain successful tools even if the following model call fails
                for entry in trace:
                    if entry["type"] == "error":
                        issues.append({"category": "agent", "stage": stage,
                                       "code": entry["error"], "message": "Agent trace reported an error."})
            turns.append({"type": "agent", "text": agent_text})
        else:
            status = "turn_limit"
    except Exception as err:  # keep the partial record; the failure is reported
        status = f"error: {err}"
        category = "infrastructure" if isinstance(err, (BudgetError, LLMError, OSError, TimeoutError)) else stage
        issues.append({"category": category, "stage": stage, "code": "episode_error",
                       "message": str(err), "error_type": type(err).__name__})
    elapsed = time.perf_counter() - started

    judge_allowed = mode == "llm" and not status.startswith("error")
    if stop_on_protocol_issue and (status != "completed" or any(
            i["category"] in ("simulator", "infrastructure", "judge") for i in issues)):
        judge_allowed = False
    result = score(task, pack.seed, sandbox.state, turns, sandbox.log,
                   judge_client=clients.get("judge") if judge_allowed else None)
    if mode == "llm":
        for entry in sandbox.log:
            if entry.get("blocked"):
                issues.append({"category": "agent", "stage": "tools", "code": "tool_validation_block",
                               "message": f"{entry['tool']}:{entry['blocked']}"})
    result["issues"] += issues
    result["cause_classification"] = classify_issues(result["issues"])
    result.update({
        "mode": agent.name if agent is not None else mode,
        "status": status,
        "turns": turns,
        "final_state": sandbox.state,
        "usage": {"agent": agent.usage if agent is not None else
                  {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0, "latency_s": 0.0},
                  "simulator": caller.usage if caller is not None else
                  {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0}},
        "wall_time_s": round(elapsed, 2),
    })
    return result


def run_subset(pack: BusinessPack, tasks: list[dict], mode: str, clients: dict,
               run_id: str | None = None, out_dir=None, log=print) -> dict:
    run_id = run_id or f"{datetime.now():%Y%m%d-%H%M}_{pack.key}_{mode}"
    out = (out_dir or RUNS_DIR) / run_id
    out.mkdir(parents=True, exist_ok=False)  # retries must use a new ID, never replace an attempt
    results = []
    budget_batches = sorted({c.budget.batch_id for c in clients.values()
                             if isinstance(getattr(c, "budget", None), CostLedger)})

    def save(status):
        write_json(out / "results.json", {"run_id": run_id, "business": pack.key, "mode": mode,
                                          "run_status": status, "planned_tasks": len(tasks),
                                          "cost_ledger_batches": budget_batches,
                                          "summary": summarise(results, planned_tasks=len(tasks)),
                                          "results": results})  # canonical checkpoint includes each CRM state
        write_json(out / "final_states.json", {r["task_id"]: r["final_state"] for r in results})

    save("running")
    current_task = None
    try:
        chunks = chunk_knowledge(pack)
        index = BM25Index([c for c in chunks if c["kind"] == "sourced_fact"])
        for task in tasks:
            current_task = task["id"]
            log(f"[{run_id}] {task['id']} ({task['category']}) ...")
            record = run_episode(task, pack, mode, clients, chunks, index)
            results.append(record)
            save("running")
            log(f"    status={record['status']} db_pass={record['db_pass']} "
                f"judge={record['judge_status']} reward={record['reward']} time={record['wall_time_s']}s")
            (out / "transcripts").mkdir(parents=True, exist_ok=True)
            (out / "transcripts" / f"{task['id']}.txt").write_text(
                transcript_text(record["turns"]) + "\n", encoding="utf-8")
    except Exception as err:
        write_json(out / "run_error.json", {"category": "infrastructure", "task_id": current_task,
                                           "error_type": type(err).__name__, "message": str(err)})
        save("error")
        raise
    save("complete")
    return {"run_id": run_id, "out_dir": str(out), "cost_ledger_batches": budget_batches,
            "summary": summarise(results, planned_tasks=len(tasks)), "results": results}


def _rate(values):
    if not values or any(v is None for v in values):
        return None
    return round(sum(bool(v) for v in values) / len(values), 3)


def summarise(results: list[dict], planned_tasks: int | None = None) -> dict:
    planned_tasks = len(results) if planned_tasks is None else planned_tasks
    complete_coverage = len(results) == planned_tasks
    write_tasks = [r for r in results if r["writes_expected"]]
    tokens_in = sum(r["usage"]["agent"]["input_tokens"] + r["usage"]["simulator"]["input_tokens"]
                    for r in results)
    tokens_out = sum(r["usage"]["agent"]["output_tokens"] + r["usage"]["simulator"]["output_tokens"]
                     for r in results)
    agent_calls = sum(r["usage"]["agent"]["llm_calls"] for r in results)
    agent_latency = sum(r["usage"]["agent"]["latency_s"] for r in results)
    scored = [r for r in results if r["reward"] is not None]
    judged = [r for r in results if r["judge_status"] == "valid"]
    return {
        "tasks": len(results),
        "planned_tasks": planned_tasks,
        "unrecorded_tasks": planned_tasks - len(results),
        "completed_without_error": sum(not r["status"].startswith("error") for r in results),
        "statuses": {s: sum(r["status"] == s for r in results) for s in sorted({r["status"] for r in results})},
        "scored_tasks": len(scored),
        "unscored_tasks": len(results) - len(scored),
        "judged_tasks": len(judged),
        "evaluation_error_tasks": sum(any(i["code"] == "evaluation_error" for i in r["issues"])
                                      for r in results),
        "crm_scored_tasks": sum(r["db_pass"] is not None for r in results),
        "cause_counts": {c: sum(r["cause_classification"] == c for r in results)
                         for c in sorted({r["cause_classification"] for r in results})},
        "task_success_rate": _rate([r["reward"] for r in results]) if complete_coverage else None,
        "task_success_rate_scored": _rate([r["reward"] for r in scored]),
        "db_pass_rate": _rate([r["db_pass"] for r in results]) if complete_coverage else None,
        "db_pass_rate_write_tasks": (_rate([r["db_pass"] for r in write_tasks])
                                     if complete_coverage and all(r["writes_expected"] is not None for r in results)
                                     else None),
        "communicate_rate": _rate([r["communicate_pass"] for r in results]) if complete_coverage else None,
        "safety_rate": _rate([r["safety_pass"] for r in results]) if complete_coverage else None,
        "communicate_rate_judged": _rate([r["communicate_pass"] for r in judged]),
        "safety_rate_judged": _rate([r["safety_pass"] for r in judged]),
        "false_success_claims": (sum(r["false_success_claim"] for r in judged)
                                 if judged and len(judged) == planned_tasks else None),
        "false_success_claims_judged": sum(r["false_success_claim"] for r in judged) if judged else None,
        "blocked_unsafe_attempts": sum(len(r["blocked_unsafe_attempts"]) for r in results),
        "agent_llm_calls": agent_calls,
        "mean_agent_llm_latency_s": round(agent_latency / agent_calls, 2) if agent_calls else None,
        "tokens_in_agent_plus_simulator": tokens_in,
        "tokens_out_agent_plus_simulator": tokens_out,
    }
