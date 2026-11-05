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
from voice_agent.evaluation.evaluator import score, transcript_text
from voice_agent.evaluation.simulator import STOP, LLMCaller, ScriptedCaller
from voice_agent.inference.agent import OracleAgent, SingleAgent
from voice_agent.inference.crm import CRMSandbox
from voice_agent.inference.retrieval import BM25Index
from voice_agent.utils.common import RUNS_DIR, write_json

MAX_CALLER_TURNS = 12
# The call ends when the agent signs off without asking anything further.
SIGN_OFF = re.compile(r"\b(goodbye|bye|have a (great|good|nice) day)\b", re.I)


def agent_ended_call(text: str) -> bool:
    return bool(SIGN_OFF.search(text)) and not text.rstrip().endswith("?")


def run_episode(task: dict, pack: BusinessPack, mode: str, clients: dict, chunks: list[dict],
                index: BM25Index) -> dict:
    views = task_views(task)
    check_views(views)
    sandbox = CRMSandbox(pack.seed, views["harness"], index)
    rules = [c for c in chunks if c["kind"] == "sandbox_rule"]

    if mode == "llm":
        agent = SingleAgent(clients["agent"], pack.name, rules, pack.seed["snapshot_at"])
        caller = LLMCaller(clients["simulator"], views["simulator"]["caller"])
    elif mode == "oracle":
        agent, caller = OracleAgent(task), ScriptedCaller(views["simulator"]["caller"])
    elif mode.startswith("control_skip_"):
        agent = OracleAgent(task, skip=mode.removeprefix("control_skip_"))
        caller = ScriptedCaller(views["simulator"]["caller"])
    else:
        raise ValueError(f"unknown mode {mode}")

    turns: list[dict] = []
    status = "completed"
    started = time.perf_counter()
    agent_text = agent.greeting()
    turns.append({"type": "agent", "text": agent_text})
    previous_caller = None
    try:
        for _ in range(MAX_CALLER_TURNS):
            if agent_ended_call(agent_text):
                break
            caller_text = caller.reply(agent_text)
            if STOP in caller_text:
                break
            if mode == "llm" and caller_text == previous_caller:  # LLM caller stuck repeating itself
                status = "caller_repeat_stop"
                break
            previous_caller = caller_text
            turns.append({"type": "caller", "text": caller_text})
            sandbox.on_caller_turn(agent_text, caller_text)
            trace: list[dict] = []
            agent_text = agent.turn(caller_text, sandbox, trace)
            turns += trace
            turns.append({"type": "agent", "text": agent_text})
        else:
            status = "turn_limit"
    except Exception as err:  # keep the partial record; the failure is reported
        status = f"error: {err}"
    elapsed = time.perf_counter() - started

    result = score(task, pack.seed, sandbox.state, turns, sandbox.log,
                   judge_client=clients.get("judge") if mode == "llm" else None)
    result.update({
        "mode": agent.name,
        "status": status,
        "turns": turns,
        "final_state": sandbox.state,
        "usage": {"agent": agent.usage, "simulator": caller.usage},
        "wall_time_s": round(elapsed, 2),
    })
    return result


def run_subset(pack: BusinessPack, tasks: list[dict], mode: str, clients: dict,
               run_id: str | None = None, out_dir=None, log=print) -> dict:
    chunks = chunk_knowledge(pack)
    index = BM25Index([c for c in chunks if c["kind"] == "sourced_fact"])
    run_id = run_id or f"{datetime.now():%Y%m%d-%H%M}_{pack.key}_{mode}"
    out = (out_dir or RUNS_DIR) / run_id
    results = []
    for task in tasks:
        log(f"[{run_id}] {task['id']} ({task['category']}) ...")
        record = run_episode(task, pack, mode, clients, chunks, index)
        log(f"    status={record['status']} db_pass={record['db_pass']} "
            f"communicate={record['communicate_pass']} safety={record['safety_pass']} "
            f"reward={record['reward']} time={record['wall_time_s']}s")
        results.append(record)
        (out / "transcripts").mkdir(parents=True, exist_ok=True)
        (out / "transcripts" / f"{task['id']}.txt").write_text(
            transcript_text(record["turns"]) + "\n", encoding="utf-8")
    summary = summarise(results)
    write_json(out / "results.json", {"run_id": run_id, "business": pack.key, "mode": mode,
                                      "summary": summary,
                                      "results": [{k: v for k, v in r.items() if k != "final_state"}
                                                  for r in results]})
    write_json(out / "final_states.json", {r["task_id"]: r["final_state"] for r in results})
    return {"run_id": run_id, "out_dir": str(out), "summary": summary, "results": results}


def _rate(values):
    values = [v for v in values if v is not None]
    return None if not values else round(sum(bool(v) for v in values) / len(values), 3)


def summarise(results: list[dict]) -> dict:
    write_tasks = [r for r in results if r["writes_expected"]]
    tokens_in = sum(r["usage"]["agent"]["input_tokens"] + r["usage"]["simulator"]["input_tokens"]
                    for r in results)
    tokens_out = sum(r["usage"]["agent"]["output_tokens"] + r["usage"]["simulator"]["output_tokens"]
                     for r in results)
    agent_calls = sum(r["usage"]["agent"]["llm_calls"] for r in results)
    agent_latency = sum(r["usage"]["agent"]["latency_s"] for r in results)
    return {
        "tasks": len(results),
        "completed_without_error": sum(not r["status"].startswith("error") for r in results),
        "statuses": {s: sum(r["status"] == s for r in results) for s in sorted({r["status"] for r in results})},
        "task_success_rate": _rate([r["reward"] for r in results]),
        "db_pass_rate": _rate([r["db_pass"] for r in results]),
        "db_pass_rate_write_tasks": _rate([r["db_pass"] for r in write_tasks]),
        "communicate_rate": _rate([r["communicate_pass"] for r in results]),
        "safety_rate": _rate([r["safety_pass"] for r in results]),
        "false_success_claims": sum(bool(r["false_success_claim"]) for r in results),
        "blocked_unsafe_attempts": sum(len(r["blocked_unsafe_attempts"]) for r in results),
        "agent_llm_calls": agent_calls,
        "mean_agent_llm_latency_s": round(agent_latency / agent_calls, 2) if agent_calls else None,
        "tokens_in_agent_plus_simulator": tokens_in,
        "tokens_out_agent_plus_simulator": tokens_out,
    }
