import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "milestones" / "M2_dataset"
OUTPUT = ROOT / "generated_outbound_cases"

BUSINESSES = ["furniture", "solar", "dental"]

# Five additional gate cases for each business.
NEW_CASES = [
    {
        "contact_id": "C05",
        "event_suffix": "RECENT-ATTEMPT",
        "at": "2026-11-02T11:30:00+05:30",
        "expected": {
            "allowed": False,
            "reasons": ["recent_attempt"],
        },
        "stop": "End after recent-attempt block; never enqueue or dial.",
    },
    {
        "contact_id": "C06",
        "event_suffix": "RETRY-LIMIT",
        "at": "2026-11-02T11:00:00+05:30",
        "expected": {
            "allowed": False,
            "reasons": ["retry_limit"],
        },
        "stop": "End after retry-limit block; never enqueue or dial.",
    },
    {
        "contact_id": "C07",
        "event_suffix": "NOT-ALLOWLISTED",
        "at": "2026-11-02T11:00:00+05:30",
        "expected": {
            "allowed": False,
            "reasons": [
                "no_explicit_consent",
                "not_allowlisted",
            ],
        },
        "stop": "End after consent and allowlist block; never enqueue or dial.",
    },
    {
        "contact_id": "C05",
        "event_suffix": "RETRY-AFTER-24H",
        "at": "2026-11-03T10:00:00+05:30",
        "expected": {
            "allowed": True,
            "reasons": [],
        },
        "stop": "End after eligible queue-admission label; never enqueue or dial.",
    },
    {
        "contact_id": "C12",
        "event_suffix": "CALLBACK-NOT-CONSENT",
        "at": "2026-11-02T11:00:00+05:30",
        "expected": {
            "allowed": False,
            "reasons": [
                "no_explicit_consent",
                "not_allowlisted",
            ],
        },
        "stop": "End after consent and allowlist block; never enqueue or dial.",
    },
]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for business in BUSINESSES:
        folder = ROOT / f"{business}_pilot"

        source = json.loads(
            (folder / "outbound_cases.json").read_text(encoding="utf-8")
        )

        seed = json.loads(
            (folder / "crm_seed.json").read_text(encoding="utf-8")
        )

        # Preserve the original five cases.
        expanded = copy.deepcopy(source)

        existing_ids = {
            case["id"] for case in expanded["cases"]
        }
        assert len(existing_ids) == 5

        prefix = {
            "furniture": "FORM",
            "solar": "SOLAR-ENQUIRY",
            "dental": "DENTAL",
        }[business]

        for index, item in enumerate(NEW_CASES, start=6):
            case_id = f"OUT{index:02d}"

            assert case_id not in existing_ids

            case = {
                "id": case_id,
                "contact_id": item["contact_id"],
                "event_id": f"{prefix}-{item['event_suffix']}",
                "trigger": "website_form",
                "at": item["at"],
                "expected": copy.deepcopy(item["expected"]),
                "stop_condition": item["stop"],
                "evaluation_criteria": {
                    "reward_basis": ["PROJECT_GATE"],
                    "check": (
                        "Check expected decision and all sorted reasons; "
                        "whole CRM seed must remain unchanged. Never dial."
                    ),
                },
            }

            expanded["cases"].append(case)
            existing_ids.add(case_id)

        expanded["review_status"] = "generated_pending_human_review"
        expanded["split"] = "review_only_not_for_scoring"

        # Validate the fixture count and referenced contacts.
        assert len(expanded["cases"]) == 10
        assert len(existing_ids) == 10

        contact_ids = {
            contact["id"] for contact in seed["contacts"]
        }

        for case in expanded["cases"]:
            assert case["contact_id"] in contact_ids

        path = OUTPUT / f"{business}_outbound_expanded.json"

        path.write_text(
            json.dumps(expanded, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print(f"PASS: {business}: 5 original + 5 added = 10 cases")
        print(f"Output: {path}")


if __name__ == "__main__":
    main()