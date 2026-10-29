
#!/usr/bin/env python3
"""Generate reproducible synthetic contacts for the M2 dataset.

Run from the repository root:
    python scripts/generate_m2_contacts.py --target-per-business 50

Reads existing pilot CRM seeds and writes separate generated files.
Does not overwrite pilot seeds or generate scenario labels.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PILOTS = {
    "furniture": ROOT / "milestones/M2_dataset/furniture_pilot/crm_seed.json",
    "solar": ROOT / "milestones/M2_dataset/solar_pilot/crm_seed.json",
    "dental": ROOT / "milestones/M2_dataset/dental_pilot/crm_seed.json",
}

OUT_DIR = ROOT / "milestones/M2_dataset/generated_contacts"

FIRST_NAMES = [
    "Aarav", "Diya", "Ishaan", "Mira", "Neel", "Riya",
    "Kabir", "Tara", "Vihaan", "Anaya", "Reyansh", "Ira",
    "Aditi", "Dev", "Nila", "Zoya", "Arjun", "Meera",
    "Kavya", "Omar", "Sana", "Rohan", "Pia", "Nikhil",
]

LAST_LABEL = "Synthetic"

FURNITURE_VALUES = {
    "category": [
        "desk", "chair", "sofa", "shelf", "worktop",
        "bed", "dining_table", None,
    ],
    "budget_inr": [
        None, 3500, 5000, 7500, 10000, 15000,
        25000, 40000, 60000,
    ],
    "pincode": [
        None, "560001", "560034", "400001", "400050",
        "110001", "122001", "411001",
    ],
    "timeline_days": [None, 3, 7, 14, 21, 30, 45, 60, 90],
}

SOLAR_VALUES = {
    "home_ownership": ["owner", "tenant", "family_owned", "unknown"],
    "roof_type": ["RCC", "metal_sheet", "tile", "unknown", None],
    "roof_access": [True, False, None],
    "roof_permission": [
        "self_reported_owner",
        "owner_permission_pending",
        "tenant_permission_pending",
        "unknown",
    ],
    "shading": [
        "unknown",
        "no_known_shading",
        "morning_neighbour_shadow",
        "afternoon_tree_shadow",
        "partial_roof_shading",
    ],
    "monthly_bill_inr": [
        None, 1200, 1800, 2500, 3500, 5000, 7500, 10000,
    ],
    "location": [
        "Pune", "Nashik", "Nagpur", "Mumbai",
        "Thane", "Kolhapur", "Aurangabad",
    ],
    "pincode": [
        None, "411001", "422001", "440001",
        "400001", "400601", "416001",
    ],
    "timeline_days": [None, 14, 30, 45, 60, 90, 120],
}

DENTAL_VALUES = {
    "requested_service": [
        "consultation",
        "cleaning_enquiry",
        "whitening_enquiry",
        "implant_enquiry",
        "appointment_information",
    ],
    "visit_mode": ["in_clinic", "video", None],
    "timing_preference": [
        "next_week",
        "next_week_morning",
        "next_week_evening",
        "weekend",
        "flexible",
        None,
    ],
}


def read_json(path: Path) -> dict:
    """Load an existing pilot seed."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required pilot seed not found: {path}"
        )

    return json.loads(path.read_text(encoding="utf-8"))


def contact_id_number(contact_id: str) -> int:
    """Extract the numeric part of a contact ID such as C12."""
    match = re.fullmatch(r"C(\d+)", contact_id)

    if not match:
        raise ValueError(
            f"Unexpected contact ID format: {contact_id!r}"
        )

    return int(match.group(1))


def synthetic_contact(
    template: dict,
    business: str,
    number: int,
    rng: random.Random,
) -> dict:
    """Create a synthetic contact and reset interaction state."""
    contact = copy.deepcopy(template)

    first = FIRST_NAMES[
        (number + rng.randrange(len(FIRST_NAMES)))
        % len(FIRST_NAMES)
    ]

    contact["id"] = f"C{number:02d}"
    contact["name"] = f"{first} {LAST_LABEL} {number:02d}"
    contact["email"] = (
        f"synthetic.{business}.{number:03d}@example.invalid"
    )

    # Reset consent and prior interaction state.
    contact["status"] = "new"
    contact["consent"] = False
    contact["consent_record"] = None
    contact["opted_out"] = False
    contact["attempts"] = 0
    contact["last_attempt_at"] = None
    contact["history"] = [
        "Synthetic generated fixture; "
        "no prior interaction or outbound permission."
    ]

    value_sets = {
        "furniture": FURNITURE_VALUES,
        "solar": SOLAR_VALUES,
        "dental": DENTAL_VALUES,
    }[business]

    for field, choices in value_sets.items():
        if field in contact:
            contact[field] = rng.choice(choices)

    # Keep solar permission labels reasonably consistent
    # with the synthetic ownership field.
    if business == "solar":
        if contact.get("home_ownership") == "tenant":
            contact["roof_permission"] = rng.choice(
                ["tenant_permission_pending", "unknown"]
            )
        elif contact.get("home_ownership") == "owner":
            contact["roof_permission"] = rng.choice(
                ["self_reported_owner", "unknown"]
            )

    return contact



def validate_generated(
    business: str,
    seed: dict,
    contacts: list[dict],
    target: int,
) -> None:
    """Validate contact IDs and safe state for newly generated records."""

    assert len(contacts) == target, (
        f"{business}: expected {target} contacts, got {len(contacts)}"
    )

    ids = [contact["id"] for contact in contacts]
    emails = [contact["email"] for contact in contacts]

    assert len(ids) == len(set(ids)), (
        f"{business}: duplicate contact IDs"
    )
    assert len(emails) == len(set(emails)), (
        f"{business}: duplicate emails"
    )
    assert all(
        email.endswith("@example.invalid") for email in emails
    )
    assert all(
        contact["id"].startswith("C") for contact in contacts
    )

    # Ensure every original pilot contact is retained.
    original_ids = {
        contact["id"] for contact in seed["contacts"]
    }
    assert original_ids.issubset(set(ids)), (
        f"{business}: original seed contacts missing"
    )

    # Original contacts may legitimately have historical consent,
    # opt-outs, or previous attempts. Check only newly generated ones.
    generated = [
        contact for contact in contacts
        if contact["id"] not in original_ids
    ]

    expected_generated = target - len(seed["contacts"])
    assert len(generated) == expected_generated, (
        f"{business}: expected {expected_generated} new contacts, "
        f"got {len(generated)}"
    )

    assert all(
        contact["consent"] is False
        and contact["consent_record"] is None
        and contact["opted_out"] is False
        and contact["attempts"] == 0
        and contact["last_attempt_at"] is None
        for contact in generated
    ), (
        f"{business}: generated contact has unsafe interaction state"
    )


def generate(
    business: str,
    seed: dict,
    target: int,
    base_seed: int,
) -> dict:
    """Retain original contacts and append synthetic contacts."""
    originals = copy.deepcopy(seed["contacts"])

    if target < len(originals):
        raise ValueError(
            f"Target must be at least {len(originals)} "
            f"for {business}"
        )

    rng = random.Random(f"{base_seed}:{business}")
    contacts = originals
    templates = originals[:]

    next_number = (
        max(contact_id_number(c["id"]) for c in originals) + 1
    )

    while len(contacts) < target:
        template_index = (
            next_number - len(originals) - 1
        ) % len(templates)

        template = templates[template_index]

        contacts.append(
            synthetic_contact(
                template=template,
                business=business,
                number=next_number,
                rng=rng,
            )
        )

        next_number += 1

    validate_generated(business, seed, contacts, target)

    return {
        "business_id": seed.get("business_id", business),
        "synthetic": True,
        "review_status": "generated_pending_human_review",
        "split": "development_candidate_not_yet_split",
        "generation": {
            "script": "generate_m2_contacts.py",
            "seed": base_seed,
            "target_per_business": target,
            "method": (
                "Retain existing seed contacts; generate "
                "schema-compatible synthetic contacts; reset "
                "generated consent and interaction state."
            ),
        },
        "limitations": [
            "Contacts only; no inbound scenarios or outbound "
            "test cases are generated.",
            "Generated fields require human review for realism "
            "and policy consistency.",
            "Generated contacts have no outbound consent.",
            "These records are not observed agent outcomes "
            "or benchmark results.",
        ],
        "contacts": contacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--target-per-business",
        type=int,
        default=50,
        help=(
            "Total contacts per business, including existing "
            "seed contacts (default: 50)"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20261029,
        help="Deterministic generation seed",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Output directory",
    )

    args = parser.parse_args()

    if args.target_per_business < 1:
        parser.error("--target-per-business must be positive")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    total = 0

    for business, path in PILOTS.items():
        seed = read_json(path)

        result = generate(
            business=business,
            seed=seed,
            target=args.target_per_business,
            base_seed=args.seed,
        )

        output_path = (
            args.output_dir / f"{business}_contacts.json"
        )

        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        total += len(result["contacts"])

        print(
            f"PASS: {business}: {len(result['contacts'])} "
            f"synthetic contacts -> {output_path}"
        )

    print(
        f"PASS: generated {total} contacts "
        f"across {len(PILOTS)} businesses."
    )
    print(
        "Review-only contact expansion. Inbound scenarios, "
        "outbound cases, and agent evaluation are not generated."
    )


if __name__ == "__main__":
    main()
