"""Validate frozen development fixtures offline; never load or create held-out answers."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.development import case_pack, digest, load_development
from voice_agent.data.preprocess import check_views, chunk_knowledge, task_views
from voice_agent.evaluation.evaluator import expected_state
from voice_agent.inference.retrieval import BM25Index
from voice_agent.pipelines.episode import run_episode
from voice_agent.utils.common import write_json


def check(out):
    manifest, tasks, packs = load_development()
    out.mkdir(parents=True, exist_ok=False)
    records = []
    write_json(out / "input_manifest.json", manifest)
    for task in tasks:
        pack = case_pack(task, packs)
        views = task_views(task)
        check_views(views)
        for role, view in views.items():
            write_json(out / "views" / task["id"] / f"{role}.json", view)
        chunks = chunk_knowledge(pack, document_id=f"m4-development-v1/{task.get('document_variant', 'short')}")
        index = BM25Index([c for c in chunks if c["kind"] == "sourced_fact"])
        # Oracle is an explicit answer-key reader, not a leakage-free model or dialogue-quality test.
        result = run_episode(task, pack, "oracle", {}, chunks, index)
        errors = []
        for name, fixture in task["tool_results"].items():
            observed = [entry["result"] for entry in result["tool_log"] if entry["tool"] == name]
            expected = dict(fixture)
            if name == "find_lead" and "matches" in expected:
                expected = {"email": expected["email"], "match_found": bool(expected["matches"])}
            if not observed or not any(all(k in actual and actual[k] == v for k, v in expected.items()) for actual in observed):
                errors.append(f"Fixture result mismatch or tool not exercised: {name}")
        start, end = pack.seed, expected_state(pack.seed, task["gold"])
        write_json(out / "states" / f"{task['id']}.start.json", start)
        write_json(out / "states" / f"{task['id']}.expected.json", end)
        write_json(out / "episodes" / f"{task['id']}.json", result)
        record = {"id": task["id"], "split": "development_core" if task["id"].startswith("IN") else "development_targeted",
                  "scenario_sha256": digest(task), "starting_crm_sha256": digest(start),
                  "expected_crm_sha256": digest(end), "document_variant": task.get("document_variant", "short"),
                  "knowledge_ids": task["knowledge_ids"], "caller_contract_structure_checked": True,
                  "caller_semantic_review": "pending_human_review; oracle does not test caller behavior",
                  "rubric_structure_checked": True, "communication_semantics": "pending_human_review; not model-tested",
                  "state_matches": result["db_pass"], "judge_status": result["judge_status"],
                  "fixture_errors": errors, "status": result["status"]}
        records.append(record)
        write_json(out / "checks.json", {"records": records, "planned": len(tasks), "paid_requests": 0,
                                         "held_out_status": "deferred_by_user; no answers created or loaded"})
    passed = all(r["state_matches"] is True and not r["fixture_errors"] and r["status"] == "completed" for r in records)
    summary = {"fixture_checks_passed": passed, "cases": len(records), "core": 10,
               "targeted": len(records)-10, "paid_requests": 0, "human_review": "pending",
               "language_scored": False, "held_out_evaluation_allowed": False}
    write_json(out / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory, never overwrite")
    args = parser.parse_args()
    summary = check(args.output)
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["fixture_checks_passed"] else 1)


if __name__ == "__main__":
    main()
