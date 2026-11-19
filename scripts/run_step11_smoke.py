"""Approved step11_smoke_001 only: four-request read-only development diagnostic."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from run_text_smoke import FACTS, JUDGE_PROMPT, MODEL, run_smoke
from voice_agent.evaluation.evaluator import diff
from voice_agent.models.budget import CostLedger
from voice_agent.utils.common import load_env, write_json

BATCH_ID = "step11_smoke_001"
RUN_ID = "m4_step11_smoke_001"
JUDGE_INSTRUCTION = """
For EVERY prohibited item, even when violated is false, evidence must be a nonempty
transcript-grounded explanation of why it was not violated. Never return an empty
string for a non-violation. The same nonempty-evidence requirement applies to every
required item. Do not invent quotations or change any flags merely to pass the rubric.
"""


def run(out, budget, api_key):
    if budget.batch_id != BATCH_ID:
        raise ValueError("Only the approved Step 11 batch may be used")
    seed_path = ROOT / "milestones/M4_training/development/crm_seed.json"
    manifest = json.loads((seed_path.parent / "manifest.json").read_text())
    if hashlib.sha256(seed_path.read_bytes()).hexdigest() != manifest["file_sha256"]["crm_seed.json"]:
        raise ValueError("Frozen CRM seed differs from approved source")
    seed = json.loads(seed_path.read_text())
    result = run_smoke(out, budget, api_key, batch_id=BATCH_ID,
                       judge_prompt=JUDGE_PROMPT + JUDGE_INSTRUCTION)
    # The isolated seed is never passed to the read-only source fixture or any model.
    write_json(out / "crm.json", {"initial":seed, "expected":seed, "final":seed,
        "diff":diff(seed, seed), "scope":"isolated read-only seed; no CRM write path exercised"})
    matches = [m for turn in result["turns"] if turn["type"] == "tool"
               for m in turn["result"].get("matches", [])]
    write_json(out / "retrieved_sources.json", {"sources":matches,
        "available_fixture":FACTS,
        "retrieval":"deterministic synthetic source fixture, not BM25 or external retrieval"})
    write_json(out / "diagnostic_context.json", {"crm_diff":[],
        "scorer_note":"Common strict validator unchanged; explicit nonempty non-violation instruction added. Not calibrated/human-adjudicated.",
        "comparison_scope":"diagnostic only; outside frozen comparison matrix; that source freeze now detects drift"})
    return result


def main():
    load_env()
    result = run(ROOT / "experiments/runs" / RUN_ID,
        CostLedger(ROOT / "experiments/cost_ledger.json", BATCH_ID), os.getenv("OPENAI_API_KEY", ""))
    print(json.dumps({k:result[k] for k in ("batch_id","model","status","checks")},indent=2))
    if result.get("error"):
        print("Stopped:", result["error_type"], "(sanitized details in results.json)")
    sys.exit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
