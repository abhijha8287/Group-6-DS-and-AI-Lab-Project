"""Load one business pack from the committed M2 dataset and select task subsets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from voice_agent.utils.common import DATASET_DIR, PILOT_DIRS, read_json

SPLIT_MANIFEST = DATASET_DIR / "generated_splits" / "m2_split_manifest.json"

BUSINESS_NAMES = {
    "solar": "SunGrid Rooftop Solar",
    "dental": "BrightSmile Dental Studio",
    "furniture": "UrbanNest Furniture",
}


@dataclass
class BusinessPack:
    key: str
    name: str
    knowledge_md: str
    seed: dict
    scenarios: list = field(default_factory=list)
    outbound_cases: list = field(default_factory=list)
    dev_ids: list = field(default_factory=list)
    test_ids: list = field(default_factory=list)

    def scenario(self, task_id: str) -> dict:
        for task in self.scenarios:
            if task["id"] == task_id:
                return task
        raise KeyError(f"{self.key}: unknown task {task_id}")


def load_business(key: str, expanded: bool = False) -> BusinessPack:
    """Load knowledge, CRM seed, scenarios, outbound cases and split IDs.

    ``expanded=False`` returns the 10 hand-reviewed pilot tasks, which are the
    only tasks that carry full tool-result fixtures. ``expanded=True`` returns
    all 40 generated tasks (IN11-IN40 are no-write tasks).
    """
    pilot: Path = PILOT_DIRS[key]
    if expanded:
        scenarios = read_json(DATASET_DIR / "generated_scenarios" / f"{key}_scenarios_expanded.json")
    else:
        scenarios = read_json(pilot / "scenarios.json")
    outbound = read_json(DATASET_DIR / "generated_outbound_cases" / f"{key}_outbound_expanded.json")
    manifest = read_json(SPLIT_MANIFEST)["businesses"][key]
    return BusinessPack(
        key=key,
        name=BUSINESS_NAMES[key],
        knowledge_md=(pilot / "knowledge.md").read_text(encoding="utf-8"),
        seed=read_json(pilot / "crm_seed.json"),
        scenarios=scenarios["scenarios"],
        outbound_cases=outbound["cases"],
        dev_ids=manifest["development_review_ids"],
        test_ids=manifest["test_review_ids"],
    )


def select_tasks(pack: BusinessPack, ids: list[str] | None = None, split: str = "dev") -> list[dict]:
    """Return tasks from one split only. Test IDs are refused unless split='test'."""
    allowed = set(pack.dev_ids if split == "dev" else pack.test_ids)
    chosen = ids or [t["id"] for t in pack.scenarios if t["id"] in allowed]
    leaked = [i for i in chosen if i not in allowed]
    if leaked:
        raise ValueError(f"Tasks {leaked} are not in the {split} split")
    return [pack.scenario(i) for i in chosen]
