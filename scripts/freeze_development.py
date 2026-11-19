"""Freeze the exposed ten-case Solar core and development supplements once; no holdout authoring."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from voice_agent.data.development import DEVELOPMENT_DIR, FILES, digest, load_development
from voice_agent.utils.common import REPO_ROOT, read_json, write_json


def freeze(root=DEVELOPMENT_DIR):
    if any((root/name).exists() for name in (*FILES[:2], *FILES[3:], "manifest.json")):
        raise FileExistsError("Frozen inputs already exist; do not overwrite. Use a reviewed new version.")
    pilot = REPO_ROOT / "milestones/M2_dataset/solar_pilot"
    policy = REPO_ROOT / "milestones/M4_training/policy_packs"
    inputs = {"core.json": pilot/"scenarios.json", "crm_seed.json": pilot/"crm_seed.json",
              "sources.json": policy/"sources.json", "documents/short.md": policy/"short/knowledge.md",
              "documents/large.md": policy/"large/knowledge.md"}
    extra = read_json(root/"supplemental.json")["scenarios"]
    core = read_json(inputs["core.json"])["scenarios"]
    if len(core) != 10 or not extra:
        raise ValueError("Ten core cases and targeted additions are required")
    for name, source in inputs.items():
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    split_path = REPO_ROOT/"milestones/M2_dataset/generated_splits/m2_split_manifest.json"
    legacy = read_json(split_path)
    solar = legacy["businesses"]["solar"]
    manifest = {
        "version": "m4-development-v1", "status": "frozen_development_review_only",
        "human_review": "pending", "core_metadata": "verbatim historical M2 snapshot, not current execution claims",
        "core_ids": [t["id"] for t in core], "targeted_ids": [t["id"] for t in extra],
        "development_ids": [t["id"] for t in core+extra],
        "scenario_sha256": {t["id"]: digest(t) for t in core+extra},
        "file_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in FILES},
        "origins": {name: {"path": str(source.relative_to(REPO_ROOT)),
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()} for name,source in inputs.items()},
        "legacy_split": {"path": str(split_path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(split_path.read_bytes()).hexdigest(), "status": legacy["status"],
            "scoring_allowed": legacy["scoring_allowed"],
            "former_development_review_ids": solar["development_review_ids"],
            "former_test_review_ids": solar["test_review_ids"],
            "classification": "All 40 expansions are development/review, not independently untouched test data. This does not assert every answer was opened."},
        "clock_rule": "Reset full frozen seed per scenario; environment.snapshot_at may override only snapshot_at. No other starting-state override.",
        "views": {"agent": "id only, never OracleAgent", "simulator": "caller only",
                  "evaluator": "gold and communication/safety rubric", "harness": "environment and tool_results"},
        "held_out": {"status": "deferred_by_user", "decision": "Development only; defer holdout",
            "ids": [], "actual_case_count": 0, "planned_minimum_text_cases": 10,
            "evaluation_allowed": False, "author": None, "reviewer": None, "reviewed_at": None,
            "brief_status": "prepared_not_dispatched", "answer_keys_created": False,
            "access_control": "No independent boundary in this shared workspace; external custodian required before creation"},
        "held_out_audio": {"status": "reservation_only_deferred", "planned_separate_cases": 3,
            "ids": [], "actual_case_count": 0, "author": None, "reviewer": None, "reviewed_at": None,
            "review_status": "not_created_not_reviewed", "audio_seconds": 0,
            "evaluation_allowed": False, "key_location": None,
            "access_control": "Not implemented. Future custodian must store separately outside agent/repo access; .gitignore is not a boundary."}}
    write_json(root/"manifest.json", manifest)
    load_development(root)  # self-check every frozen input/view before declaring the freeze usable
    return manifest


if __name__ == "__main__":
    result = freeze()
    print(f"Frozen {len(result['core_ids'])} core + {len(result['targeted_ids'])} targeted development cases; holdout deferred")
