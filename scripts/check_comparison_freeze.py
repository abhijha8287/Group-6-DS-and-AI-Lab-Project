"""Freeze/check a non-executable comparison plan. Never creates clients or dispatches runs."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from voice_agent.data.development import load_development

SETTINGS = Path("milestones/M4_training/comparison_settings.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(root, expected=None):
    files = set((root / "src/voice_agent").rglob("*.py")) | set((root / "scripts").glob("*.py"))
    files |= {root / "milestones/M4_training/development" / name for name in
              ("manifest.json", "core.json", "crm_seed.json", "supplemental.json", "sources.json",
               "documents/short.md", "documents/large.md", "README.md", "CASE_REVIEW.md",
               "INDEPENDENT_AUTHOR_BRIEF.md", "authoring_schema.json")}
    files |= {root / f for f in ("milestones/M1_problem_literature/report.md",
              "milestones/M4_training/measurement_protocol.md", "milestones/M4_training/comparison_plan.md",
              "milestones/M4_training/policy_packs/questions.json", "milestones/M4_training/policy_packs/sources.json")}
    if expected is not None and {str(f.relative_to(root)) for f in files} != set(expected):
        raise ValueError("Source/input membership drift; new files were not read")
    return {str(f.relative_to(root)): sha(f) for f in sorted(files)}


def runtime():
    return {"python":platform.python_version(), "implementation":platform.python_implementation(),
            "system":platform.system(), "machine":platform.machine()}


def plan():
    manifest, _, _ = load_development()
    models = ["gpt-4o-mini-2024-07-18", "gpt-4.1-mini-2025-04-14"]
    cells = [{"id":f"M{m}-{architecture}-{pack}", "model":model, "architecture":architecture,
              "pack":pack, "scenario_ids":manifest["core_ids"], "repetitions":[1,2,3],
              "planned_attempts":30, "execution_allowed":False}
             for m,model in enumerate(models) for architecture in ("B0","M1") for pack in ("short","large")]
    return {
        "version":"m4-comparison-v1", "scorer_version":"m4-metrics-v1", "status":"preregistered_blocked",
        "execution_allowed":False, "approved_batch_id":None,
        "scope":"exposed development comparisons only; no heldout or voice execution",
        "runtime":runtime(), "input_sha256":inputs(ROOT),
        "dataset_version":manifest["version"], "core_cells":cells, "core_planned_attempts":240,
        "targeted_validation":{"scenario_ids":manifest["targeted_ids"], "models":models,
            "architectures":["B0","M1"], "repetitions":[1], "pack":"case-assigned, never cross-pack",
            "planned_attempts":24, "pool_into_core_scores":False, "execution_allowed":False},
        "execution_order":"repetition 1,2,3; core IDs in manifest order; pack short then large; model M0 then M1; architectures B0,M1 on odd core positions and M1,B0 on even; targeted validation afterwards",
        "roles":{"provider":"openai", "endpoint":"https://api.openai.com/v1/chat/completions",
            "service_tier":"default", "n":1, "temperature":0.0,
            "agent_model":"cell model, also every specialist", "agent_output_tokens":800,
            "simulator_model":models[0], "simulator_output_tokens":200,
            "judge_model":models[0], "judge_output_tokens":1200,
            "seed":None, "seed_policy":"API seed not requested; temperature zero does not promise deterministic output",
            "fallbacks":False, "env_overrides":"must be rejected by future runner if not identical to this plan"},
        "limits":{"caller_generations_per_episode":12, "agent_model_calls_per_caller_turn_pooled":8,
            "tool_rounds_per_caller_turn":8, "executed_tool_calls_per_caller_turn_pooled":8,
            "http_retries":0, "judge_repairs":0, "scenario_replacements":0,
            "request_timeout_seconds":30, "max_request_bytes":64000, "concurrency":1},
        "caller":{"class":"LLMCaller", "prompt":"hash-pinned simulator.py::caller_prompt",
            "inputs":"only task_views.simulator; no evaluator or raw harness payload",
            "confirmation":"goal-permitted next reply starts Yes, I confirm; refusals start No",
            "stop":"###STOP###, empty completion also treated as STOP by pinned implementation",
            "history":"full mirrored dialogue; no truncation, summarization or hidden gold",
            "greeting":"Hello, you've reached SunGrid Rooftop Solar. How can I help you today?"},
        "retrieval":{"implementation":"BM25Index", "k1":1.5, "b":0.75, "agent_top_k":3,
            "agent_index":"fact chunks only; all policy chunks supplied in system prompt",
            "offline_recall_k":[1,3,5,10], "offline_index":"all fact and policy chunks, reported separately from agent-path retrieval",
            "tie_break":"stable document section order; no reranker, embeddings or randomization",
            "annotations":"pack-specific policy_packs/questions.json; human review pending"},
        "crm":{"reset":"fresh complete frozen seed per attempt; only manifest-approved case snapshot_at override",
            "clock":"frozen per-case snapshot_at, Asia/Kolkata; never live wall clock for business rules",
            "writes":"identical sandbox schemas, registry and validation layer in both architectures",
            "identity":"same trusted identity binding; no model-provided bypass"},
        "architectures":{"B0":"pinned SingleAgent; direct tools, no specialists",
            "M1":{"implementation":"not implemented; prospective code/prompt freeze required before any execution",
                "topology":"sequential conversation coordinator plus knowledge, qualification and CRM/handoff-planner specialists; no parallel workers or worker-to-worker calls",
                "dispatch":"knowledge for factual questions; qualification for lead qualification; CRM planner before any CRM write including opt-out; applicable order knowledge, qualification, planner",
                "access":"specialists see only observed caller facts, relevant public policy and authorized tool observations for their role; never simulator persona/goal, rubric, fixtures or expected states",
                "authority":"specialists propose only; coordinator alone executes existing tools through unchanged validation",
                "budgets":"all coordinator and specialist model calls share the 8-call per-caller budget; all actual tools share 8-step budget; delegations are logged and never free/unlimited",
                "financial_role":"AGENT for every specialist, with separate agent_role tags for attribution"}},
        "analysis":{"primary_unit":"scenario", "repetitions":3, "all_three":"pass^3, not pass@3",
            "policy_probe_core_ids":manifest["core_ids"], "policy_probe_basis":"all core rubrics probe policy/safety; semantic review pending; no outcome-dependent selection",
            "primary_architecture_test":"future heldout only; paired repetition 1 exact McNemar O1 strict and O3, Holm family alpha 0.05",
            "primary_architecture_pair":["M0-B0-short", "M0-M1-short"],
            "other_cells":"development model/document/architecture sensitivity analyses, not extra adoption tests",
            "bootstrap_resamples":10000, "bootstrap_seed":20261119, "quantiles":"nearest_rank",
            "bootstrap_unit":"scenario cluster; retain both architectures, repetitions, turns and costs together",
            "targeted_inference":False, "development_adoption_claims":False},
        "voice":{"in_v1_matrix":False, "execution_allowed":False, "reason":"no audio runtime/instrumentation; no STT/TTS/caller audio settings certified",
            "future_constraint":"same local LiveKit plus direct OpenAI Realtime stack in both architectures; requires separate prospective exact model/SDK/voice/VAD/audio/caller/runtime freeze and approval; no cascaded substitute"},
        "heldout":{"actual_text_cases":0, "actual_audio_cases":0, "evaluation_allowed":False,
            "reason":"user deferred; no independent custodian or protected answers"},
        "spending":{"ledger":"experiments/cost_ledger.json", "new_authorization":False,
            "smoke_batch":"step5_smoke_001 consumed, cannot reuse", "text_allocation_usd":"9.00 planning only, not approval",
            "agent_cost_roles":"AGENT including all specialists; STT/TTS/realtime if later authorized",
            "evaluation_overhead_roles":["SIMULATOR","JUDGE"],
            "cost_basis":"application estimate: actual metered usage times same frozen published prices; unknown usage bound separate; not verified invoice",
            "prices":"Step 5 dated source audit is historical planning, not current billing guarantee; fresh access/pricing and caps required per paid batch",
            "insufficient_budget":"stop, retain partial attempts and unknowns; no refills, model substitutions or unrecorded reruns"},
        "blockers":["explicit paid batch approval absent", "semantic source/scenario and relevance review pending",
            "judge calibration and pending historical adjudications unresolved", "comparison runner and normalized annotation/telemetry export not implemented",
            "M1 architecture not implemented or code/prompt frozen", "second model not enabled in cost catalog; both snapshots deprecated and access must be checked with approval",
            "voice and independent heldout explicitly excluded"]}


def check(settings, root=ROOT):
    if settings["version"] != "m4-comparison-v1" or settings["execution_allowed"] is not False:
        raise ValueError("Not the frozen blocked plan; create a prospective amendment instead")
    if settings["input_sha256"] != inputs(root, settings["input_sha256"]):
        raise ValueError("Frozen input/source drift (including added or removed code)")
    if settings["runtime"] != runtime():
        raise ValueError("Runtime differs from freeze")
    cells = settings["core_cells"]
    if len(cells)!=8 or len({c["id"] for c in cells})!=8:
        raise ValueError("Core matrix must have 8 unique cells")
    if any(c["repetitions"] != [1,2,3] or len(c["scenario_ids"])!=10 or len(set(c["scenario_ids"]))!=10 or c["execution_allowed"] is not False for c in cells):
        raise ValueError("Invalid cell slots or execution authorization")
    expected = plan()
    if json.dumps(settings, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("Registered settings differ, including matrix values or nested authorization")
    return {"integrity":"pass", "execution_allowed":False, "core_cells":len(cells),
            "core_planned_attempts":sum(c["planned_attempts"] for c in cells),
            "targeted_validation_attempts":settings["targeted_validation"]["planned_attempts"],
            "blockers":settings["blockers"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", help="Create once; refuses existing settings or checksum")
    args = parser.parse_args()
    path = ROOT / SETTINGS
    checksum = path.with_suffix(".sha256")
    if args.freeze:
        if path.exists() or checksum.exists():
            raise FileExistsError("Freeze exists; preserve it and register a prospective amendment")
        settings = plan()
        check(settings)
        with path.open("x") as stream:
            stream.write(json.dumps(settings,indent=2)+"\n")
        with checksum.open("x") as stream:
            stream.write(sha(path)+"\n")
    if sha(path) != checksum.read_text().strip():
        raise ValueError("Comparison settings checksum mismatch")
    print(json.dumps(check(json.loads(path.read_text())),indent=2))


if __name__ == "__main__":
    main()
