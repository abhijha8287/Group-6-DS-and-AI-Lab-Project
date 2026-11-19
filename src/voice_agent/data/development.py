"""Frozen, exposed development inputs. This loader never reads held-out files."""

from dataclasses import replace
from pathlib import Path
import hashlib
import json

from voice_agent.data.loader import BusinessPack
from voice_agent.data.preprocess import check_views, chunk_knowledge, task_views, validate_knowledge_sources
from voice_agent.evaluation.evaluator import expected_state
from voice_agent.inference.crm import TOOL_NAMES
from voice_agent.utils.common import REPO_ROOT, deep_copy, parse_time, read_json

DEVELOPMENT_DIR = REPO_ROOT / "milestones/M4_training/development"
FILES = ("core.json", "crm_seed.json", "supplemental.json", "sources.json",
         "documents/short.md", "documents/large.md")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def load_development(root: Path = DEVELOPMENT_DIR):
    manifest = read_json(root / "manifest.json")
    if manifest["version"] != "m4-development-v1" or set(manifest["file_sha256"]) != set(FILES):
        raise ValueError("Unknown development version/input set")
    for partition in ("held_out", "held_out_audio"):
        plan = manifest[partition]
        if plan["ids"] or plan["actual_case_count"] != 0 or plan["evaluation_allowed"] is not False:
            raise ValueError("This exposed development loader cannot certify or load a held-out set")
    for name in FILES:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != manifest["file_sha256"][name]:
            raise ValueError(f"Frozen development input changed: {name}; create a reviewed new version")
    core = read_json(root / "core.json")["scenarios"]
    extra = read_json(root / "supplemental.json")["scenarios"]
    if [t["id"] for t in core] != [f"IN{i:02d}" for i in range(1, 11)]:
        raise ValueError("Exactly the ten original core development scenarios are required")
    tasks = core + extra
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)) or ids != manifest["development_ids"]:
        raise ValueError("Duplicate scenarios or split membership mismatch")
    seed = read_json(root / "crm_seed.json")
    packs = {}
    for variant in ("short", "large"):
        pack = BusinessPack("solar", "SunGrid Rooftop Solar",
                            (root / f"documents/{variant}.md").read_text(encoding="utf-8"), seed)
        validate_knowledge_sources(pack)
        packs[variant] = pack
    for task in tasks:
        validate_task(task, packs)
        if digest(task) != manifest["scenario_sha256"][task["id"]]:
            raise ValueError(f"Frozen scenario changed: {task['id']}")
    return manifest, tasks, packs


def case_pack(task, packs):
    variant = task.get("document_variant", "short")
    if variant not in packs:
        raise ValueError("Only frozen short/large documents may enter an episode")
    pack = packs[variant]
    seed = deep_copy(pack.seed)
    override = task["environment"].get("snapshot_at")
    if override is not None:
        parse_time(override)
        seed["snapshot_at"] = override
    return replace(pack, seed=seed, scenarios=[task])


def validate_task(task, packs):
    views = task_views(task)
    check_views(views)
    if not isinstance(task["tool_results"], dict) or not set(task["tool_results"]) <= TOOL_NAMES:
        raise ValueError("Unknown tool fixture")
    if set(task["environment"]) - {"identity_fixture", "snapshot_at"}:
        raise ValueError("Unknown trusted environment fields")
    pack = case_pack(task, packs)
    known = {c["section_id"] for c in chunk_knowledge(pack)}
    if not task["knowledge_ids"] or not set(task["knowledge_ids"]) <= known:
        raise ValueError(f"Unknown knowledge sections: {task['id']}")
    for field in ("required_information", "prohibited_actions"):
        if (not isinstance(task[field], list) or not task[field]
                or any(not isinstance(v, str) or not v.strip() for v in task[field])):
            raise ValueError(f"Missing communication/safety rubric: {task['id']}")
    if set(task["gold"]) != {"contact_updates", "new_contacts", "callbacks", "handoffs"}:
        raise ValueError("Invalid expected-state patch contract")
    initial_ids = {c["id"] for c in pack.seed["contacts"]}
    for patch in task["gold"]["contact_updates"]:
        if patch["id"] not in initial_ids or not isinstance(patch["set"], dict) or not patch["set"]:
            raise ValueError("Invalid expected contact update")
    final = expected_state(pack.seed, task["gold"])
    for collection in ("contacts", "callbacks", "handoffs"):
        ids = [v["id"] for v in final[collection]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate expected {collection} IDs")
    contacts = {c["id"] for c in final["contacts"]}
    if any(v["contact_id"] not in contacts for name in ("callbacks", "handoffs") for v in final[name]):
        raise ValueError("Expected record refers to an unknown contact")
    fixture = task["environment"].get("identity_fixture")
    if fixture is not None:
        if (not isinstance(fixture, dict) or set(fixture) != {"contact_id", "email", "verification_succeeds"}
                or type(fixture["verification_succeeds"]) is not bool):
            raise ValueError("Invalid trusted identity fixture")
        if fixture["verification_succeeds"]:
            contact = next((c for c in pack.seed["contacts"] if c["id"] == fixture["contact_id"]), None)
            if contact is None or contact["email"] != fixture["email"]:
                raise ValueError("Successful identity fixture does not bind a seeded contact")
    return final
