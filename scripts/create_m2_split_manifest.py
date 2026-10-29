
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "milestones" / "M2_dataset"

BUSINESSES = ["furniture", "solar", "dental"]
OUTPUT_DIR = ROOT / "generated_splits"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    manifest = {
        "milestone": "M2",
        "status": "review_only",
        "scoring_allowed": False,
        "human_review_required": True,
        "warning": (
            "Proposed organizational split only. Generated scenarios are not "
            "an independently authored or validated held-out benchmark. "
            "Do not use the test partition for tuning or claim benchmark results."
        ),
        "businesses": {},
    }

    for business in BUSINESSES:
        path = (
            ROOT
            / "generated_scenarios"
            / f"{business}_scenarios_expanded.json"
        )

        if not path.exists():
            raise FileNotFoundError(f"Missing scenario file: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))

        # Support either a top-level list or a dictionary containing scenarios.
        if isinstance(data, list):
            scenarios = data
        elif isinstance(data, dict):
            scenarios = data.get("scenarios")
            if not isinstance(scenarios, list):
                raise ValueError(
                    f"{business}: expected a 'scenarios' list in {path.name}"
                )
        else:
            raise ValueError(f"{business}: unsupported JSON structure")

        ids = [item.get("scenario_id", item.get("id")) for item in scenarios]

        if any(scenario_id is None for scenario_id in ids):
            raise ValueError(
                f"{business}: some scenarios have no scenario_id or id. "
                "Inspect the JSON structure before creating a split."
            )

        if len(ids) != len(set(ids)):
            raise ValueError(f"{business}: duplicate scenario IDs detected")

        if len(scenarios) != 40:
            raise ValueError(
                f"{business}: expected 40 scenarios, found {len(scenarios)}"
            )

        # Preserve original fixtures in the development review partition.
        # Generated scenarios are distributed deterministically for organization,
        # not claimed to be an independent test set.
        original = scenarios[:10]
        generated = scenarios[10:]

        dev = original + generated[:18]
        test_review = generated[18:]

        manifest["businesses"][business] = {
            "source_file": str(path.relative_to(ROOT)),
            "total_scenarios": len(scenarios),
            "development_review_ids": [
                item.get("scenario_id", item.get("id")) for item in dev
            ],
            "test_review_ids": [
                item.get("scenario_id", item.get("id"))
                for item in test_review
            ],
            "development_review_count": len(dev),
            "test_review_count": len(test_review),
            "status": "pending_human_review",
        }

        print(
            f"PASS: {business}: {len(dev)} development-review, "
            f"{len(test_review)} test-review scenarios"
        )

    output = OUTPUT_DIR / "m2_split_manifest.json"
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nCreated: {output}")
    print("Review-only manifest; not a validated benchmark split.")


if __name__ == "__main__":
    main()
