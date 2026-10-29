import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parents[1]
    / "milestones"
    / "M2_dataset"
)

EXPANDED = ROOT / "generated_outbound_cases"
BUSINESSES = ["furniture", "solar", "dental"]


def time_of(value):
    dt = datetime.fromisoformat(value)
    assert dt.tzinfo is not None, "Timezone required"
    return dt


def evaluate(seed, case):
    contacts = {
        contact["id"]: contact
        for contact in seed["contacts"]
    }

    cid = case["contact_id"]

    if cid not in contacts:
        raise ValueError(f"Unknown contact: {cid}")

    contact = contacts[cid]
    now = time_of(case["at"])
    record = contact["consent_record"]

    consent = (
        contact["consent"]
        and record is not None
        and record["purpose"] == "enquiry_followup"
        and record["channel"] == "voice"
        and time_of(record["recorded_at"]) <= now
    )

    last_attempt = contact["last_attempt_at"]

    checks = {
        "not_allowlisted": (
            cid not in seed["outbound_allowlist"]
        ),
        "no_explicit_consent": not consent,
        "opted_out": contact["opted_out"],
        "outside_calling_hours": not (
            10 <= now.hour < 18
        ),
        "retry_limit": contact["attempts"] >= 2,
        "duplicate_event": (
            case["event_id"] in seed["processed_event_ids"]
        ),
        "recent_attempt": (
            last_attempt is not None
            and now - time_of(last_attempt)
            < timedelta(hours=24)
        ),
    }

    reasons = sorted(
        name for name, blocked in checks.items()
        if blocked
    )

    return {
        "allowed": not reasons,
        "reasons": reasons,
    }


def main():
    total = 0

    for business in BUSINESSES:
        seed_path = ROOT / f"{business}_pilot" / "crm_seed.json"
        cases_path = (
            EXPANDED / f"{business}_outbound_expanded.json"
        )

        seed = json.loads(
            seed_path.read_text(encoding="utf-8")
        )
        data = json.loads(
            cases_path.read_text(encoding="utf-8")
        )

        cases = data["cases"]

        assert len(cases) == 10, (
            f"{business}: expected 10 cases"
        )
        assert len({c["id"] for c in cases}) == 10, (
            f"{business}: duplicate case IDs"
        )

        for case in cases:
            actual = evaluate(seed, case)
            expected = case["expected"]

            assert actual == expected, (
                f"{business}/{case['id']} mismatch\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )

        print(
            f"PASS: {business}: "
            f"{len(cases)} cases have matching gate outcomes"
        )
        total += len(cases)

    print(f"\nPASS: all {total} outbound cases checked.")
    print("Static gate check only; no calls were placed.")


if __name__ == "__main__":
    main()