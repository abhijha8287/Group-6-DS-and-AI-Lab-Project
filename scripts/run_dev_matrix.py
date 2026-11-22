"""Run the M4 development comparisons (Steps 12-14) on OpenAI, one capped batch per episode.

Plans (all on the frozen development fixtures, core IN01-IN10, three repetitions):

  step12  model comparison: single_v2 with agent gpt-4o-mini vs gpt-4.1-mini (short pack, top-3)
  step13  architecture: single_v2 vs multi on --model (short pack, top-3)
  step14  three focused comparisons against single_v2/short/top-3 on --model:
          prompt (archived M3 prompt, mode llm), retrieval (top-5), document (large pack)

Each cell is stored once under experiments/runs/m4_dev_matrix/<cell>/ and reused by any plan
that needs the same settings; existing cells are never overwritten or silently re-run. Caller
and judge are always gpt-4o-mini. Every episode gets its own ledger batch(es) with hard request
and dollar caps; nothing runs without the plan's approval file.

    python3 scripts/run_dev_matrix.py --plan step12 --dry-run
    python3 scripts/run_dev_matrix.py --plan step12
    python3 scripts/run_dev_matrix.py --plan step13 --model gpt-4o-mini-2024-07-18
    python3 scripts/run_dev_matrix.py --summary
"""

import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from voice_agent.data.development import load_development  # noqa: E402
from voice_agent.models.budget import CostLedger, max_cost_usd  # noqa: E402
from voice_agent.models.llm import make_client  # noqa: E402
from voice_agent.pipelines.episode import run_subset  # noqa: E402
from voice_agent.utils.common import deep_copy, load_env, read_json, write_json  # noqa: E402

LEDGER = ROOT / "experiments" / "cost_ledger.json"
OUT = ROOT / "experiments" / "runs" / "m4_dev_matrix"
APPROVALS = ROOT / "milestones" / "M4_training" / "evidence" / "dev_matrix"
EVAL_MODEL = "gpt-4o-mini-2024-07-18"
MODELS = {"gpt-4o-mini-2024-07-18": "4omini", "gpt-4.1-mini-2025-04-14": "41mini"}
REPS = (1, 2, 3)
MAX_REQUESTS = 100
LIMITS = {"max_requests": MAX_REQUESTS, "max_output_tokens": 1200, "max_request_bytes": 64000,
          "max_retries": 0, "max_caller_turns": 12, "max_tool_steps": 8, "max_audio_seconds": 0}


def cell(model, mode, doc, k, task, rep):
    return {"model": model, "mode": mode, "doc": doc, "k": k, "task": task, "rep": rep,
            "id": f"{MODELS[model]}__{mode}__{doc}__k{k}__{task}__r{rep}"}


def plan_cells(plan, core, model):
    cells = []
    for rep in REPS:
        for pos, task in enumerate(core):
            if plan == "step12":
                order = list(MODELS) if pos % 2 == 0 else list(MODELS)[::-1]
                cells += [cell(m, "single_v2", "short", 3, task, rep) for m in order]
            elif plan == "step13":
                order = ["single_v2", "multi"] if pos % 2 == 0 else ["multi", "single_v2"]
                cells += [cell(model, m, "short", 3, task, rep) for m in order]
            elif plan == "step14":
                cells += [cell(model, "single_v2", "short", 3, task, rep),
                          cell(model, "llm", "short", 3, task, rep),
                          cell(model, "single_v2", "short", 5, task, rep),
                          cell(model, "single_v2", "large", 3, task, rep)]
            else:
                raise ValueError(plan)
    return cells


def status(c):
    path = OUT / c["id"] / "results.json"
    return read_json(path)["run_status"] if path.exists() else None


def register(batch_id, model, approval_ref, purpose):
    data = read_json(LEDGER)
    if any(b["id"] == batch_id for b in data["batches"]):
        raise SystemExit(f"Batch {batch_id} already exists; refusing to reuse it")
    per_request = max_cost_usd(model, LIMITS["max_output_tokens"], data["models"])
    cap = (per_request * MAX_REQUESTS).quantize(Decimal("0.000001"))
    data["batches"].append({"id": batch_id, "allocation": "text_development", "approved": True,
                            "approval_reference": approval_ref,
                            "approved_at_utc": datetime.now(timezone.utc).isoformat(),
                            "max_cost_usd": str(cap), "planned_conservative_max_usd": str(cap),
                            "model": model, "purpose": purpose, "limits": dict(LIMITS), "requests": []})
    write_json(LEDGER, data)


def run_cell(c, tasks, packs, approval_ref, log):
    task = next(t for t in tasks if t["id"] == c["task"])
    pack = packs[c["doc"]]
    seed = deep_copy(pack.seed)
    if task["environment"].get("snapshot_at"):
        seed["snapshot_at"] = task["environment"]["snapshot_at"]
    pack = replace(pack, seed=seed, scenarios=[task])
    eval_batch = "dm_" + c["id"] + "__eval"
    register(eval_batch, EVAL_MODEL, approval_ref, f"Caller/judge for {c['id']}")
    eval_budget = CostLedger(LEDGER, eval_batch)
    agent_budget = eval_budget
    if c["model"] != EVAL_MODEL:
        agent_batch = "dm_" + c["id"] + "__agent"
        register(agent_batch, c["model"], approval_ref, f"Agent for {c['id']}")
        agent_budget = CostLedger(LEDGER, agent_batch)
    os.environ.update({"AGENT_PROVIDER": "openai", "AGENT_MODEL": c["model"],
                       "SIMULATOR_PROVIDER": "openai", "SIMULATOR_MODEL": EVAL_MODEL,
                       "JUDGE_PROVIDER": "openai", "JUDGE_MODEL": EVAL_MODEL})
    clients = {"agent": make_client("AGENT", budget=agent_budget),
               "simulator": make_client("SIMULATOR", budget=eval_budget),
               "judge": make_client("JUDGE", budget=eval_budget)}
    try:
        run = run_subset(pack, [task], c["mode"], clients, run_id=c["id"], out_dir=OUT,
                         log=lambda *_: None, top_k=c["k"])
        r = run["results"][0]
        log(f"  {c['id']}: status={r['status']} crm={r['db_pass']} reward={r['reward']}")
    except Exception as err:  # the partial record is kept by run_subset; report and continue
        log(f"  {c['id']}: ERROR {type(err).__name__}: {err}")
    meta = {**c, "agent_batch": agent_budget.batch_id, "eval_batch": eval_batch,
            "approval_reference": approval_ref}
    write_json(OUT / c["id"] / "cell.json", meta)


def batch_cost(data, batch_id):
    batch = next((b for b in data["batches"] if b["id"] == batch_id), None)
    if batch is None:
        return Decimal(0), 0
    model = data["models"][batch["model"]]
    total, n = Decimal(0), 0
    for r in batch["requests"]:
        n += 1
        if r.get("status") == "reconciled":
            u = r["usage"]
            total += (Decimal(model["input_usd_per_million"]) * u["prompt_tokens"]
                      + Decimal(model["output_usd_per_million"]) * u["completion_tokens"]) / Decimal(10**6)
    return total, n


def matrix_spend():
    """Recorded usage plus any unreconciled reservations of every dev-matrix batch."""
    data = read_json(LEDGER)
    total = Decimal(0)
    for b in data["batches"]:
        if not b["id"].startswith("dm_"):
            continue
        cost, _ = batch_cost(data, b["id"])
        held = sum(Decimal(r["reserve_max_cost_usd"]) for r in b["requests"] if r.get("status") != "reconciled")
        total += cost + held
    return total


def summary(log):
    data = read_json(LEDGER)
    groups = {}
    for path in sorted(OUT.glob("*/cell.json")):
        c = read_json(path)
        res = read_json(path.parent / "results.json")
        key = (c["model"], c["mode"], c["doc"], c["k"])
        g = groups.setdefault(key, {"cells": 0, "complete": 0, "crm": 0, "crm_write": 0, "write_tasks": 0,
                                    "reward": 0, "reward_scored": 0, "comm": 0, "safe": 0, "judged": 0,
                                    "false_success": 0, "blocked_unsafe": 0, "agent_calls": 0,
                                    "agent_cost": Decimal(0), "eval_cost": Decimal(0), "per_task": {}})
        g["cells"] += 1
        for r in res["results"]:
            g["complete"] += res["run_status"] == "complete" and not r["status"].startswith("error")
            g["crm"] += bool(r["db_pass"])
            if r["writes_expected"]:
                g["write_tasks"] += 1
                g["crm_write"] += bool(r["db_pass"])
            if r["reward"] is not None:
                g["reward_scored"] += 1
                g["reward"] += r["reward"]
            if r["judge_status"] == "valid":
                g["judged"] += 1
                g["comm"] += bool(r["communicate_pass"])
                g["safe"] += bool(r["safety_pass"])
                g["false_success"] += bool(r["false_success_claim"])
            g["blocked_unsafe"] += len(r["blocked_unsafe_attempts"])
            g["agent_calls"] += r["usage"]["agent"]["llm_calls"]
            g["per_task"].setdefault(c["task"], []).append(r["reward"])
        ac, _ = batch_cost(data, c["agent_batch"])
        ec, _ = batch_cost(data, c["eval_batch"])
        if c["agent_batch"] == c["eval_batch"]:
            # one batch served all roles: split by role usage
            batch = next(b for b in data["batches"] if b["id"] == c["eval_batch"])
            m = data["models"][batch["model"]]
            ac = sum(((Decimal(m["input_usd_per_million"]) * r["usage"]["prompt_tokens"]
                       + Decimal(m["output_usd_per_million"]) * r["usage"]["completion_tokens"]) / Decimal(10**6))
                     for r in batch["requests"] if r.get("status") == "reconciled" and r["role"] == "AGENT")
            ec = ec - ac
        g["agent_cost"] += ac
        g["eval_cost"] += ec
    rows = []
    for (model, mode, doc, k), g in sorted(groups.items()):
        triplets = [v for v in g["per_task"].values() if len(v) == 3]
        rows.append({"model": model, "mode": mode, "doc": doc, "top_k": k, "episodes": g["cells"],
                     "completed": g["complete"], "crm_exact": g["crm"],
                     "crm_exact_write_tasks": f"{g['crm_write']}/{g['write_tasks']}",
                     "reward_1": f"{g['reward']}/{g['reward_scored']}",
                     "communicate": f"{g['comm']}/{g['judged']}", "safety": f"{g['safe']}/{g['judged']}",
                     "false_success_claims": g["false_success"], "blocked_unsafe_attempts": g["blocked_unsafe"],
                     "tasks_pass_all_3": f"{sum(all(x == 1 for x in v) for v in triplets)}/{len(triplets)}",
                     "tasks_pass_any_of_3": f"{sum(any(x == 1 for x in v) for v in triplets)}/{len(triplets)}",
                     "mean_agent_calls": round(g["agent_calls"] / max(1, g["cells"]), 1),
                     "agent_cost_usd": round(float(g["agent_cost"]), 5),
                     "eval_overhead_usd": round(float(g["eval_cost"]), 5)})
    write_json(OUT / "summary.json", {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "rows": rows})
    for row in rows:
        log(json.dumps(row))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", choices=["step12", "step13", "step14"])
    parser.add_argument("--model", default=EVAL_MODEL, choices=list(MODELS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.summary:
        summary(print)
        return
    _, tasks, packs = load_development()
    core = [t["id"] for t in tasks if t["id"].startswith("IN")]
    cells = plan_cells(args.plan, core, args.model)
    todo = [c for c in cells if status(c) is None]
    print(f"{args.plan}: {len(cells)} cells, {len(cells) - len(todo)} already stored (reused, never re-run), "
          f"{len(todo)} to run")
    if args.dry_run:
        for c in todo:
            print("  would run", c["id"])
        return
    approval = APPROVALS / f"{args.plan}_approval.json"
    if not approval.exists():
        raise SystemExit(f"No approval file {approval.relative_to(ROOT)}; ask the user first")
    if args.model not in read_json(approval).get("models", [args.model]):
        raise SystemExit("Model not covered by the approval")
    load_env()
    ref = str(approval.relative_to(ROOT))
    cap = Decimal(read_json(approval)["max_total_usd"])
    for i, c in enumerate(todo, 1):
        spent = matrix_spend()
        # stop before a cell could push total matrix spend (incl. held reservations) past the approval
        if spent + Decimal("4.80") > cap:
            print(f"STOP: matrix spend {spent} + worst-case cell 4.80 would exceed approved {cap}")
            break
        print(f"[{i}/{len(todo)}] spent so far ${spent:.4f}", flush=True)
        run_cell(c, tasks, packs, ref, lambda s: print(s, flush=True))
    summary(lambda s: None)
    print("done")


if __name__ == "__main__":
    main()
