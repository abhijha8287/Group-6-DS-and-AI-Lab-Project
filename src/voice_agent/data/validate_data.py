
"""Validate the synthetic M2 datasets."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"

EXPECTED_BUSINESSES = {"brightsmile", "sungrid", "urbannest"}


def read_csv(relative_path):
    path = DATA / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")

    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_crm():
    rows = read_csv("raw/crm_seed.csv")
    require(len(rows) == 180, f"Expected 180 CRM rows, got {len(rows)}")

    ids = [row["contact_id"] for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate CRM contact IDs found")

    businesses = {row["business_id"] for row in rows}
    require(businesses == EXPECTED_BUSINESSES, "Unexpected CRM business IDs")

    for row in rows:
        require(row["consent_to_follow_up"] in {"True", "False"},
                "Invalid consent value")
        require(row["opted_out"] in {"True", "False"},
                "Invalid opt-out value")
        require(
            not (
                row["consent_to_follow_up"] == "True"
                and row["opted_out"] == "True"
            ),
            f"Opted-out contact has consent: {row['contact_id']}",
        )

    print(f"PASS: CRM records ({len(rows)})")


def validate_scenarios():
    dev = read_csv("splits/dev.csv")
    test = read_csv("splits/test.csv")
    rows = dev + test

    require(len(dev) == 96, f"Expected 96 dev scenarios, got {len(dev)}")
    require(len(test) == 24, f"Expected 24 test scenarios, got {len(test)}")
    require(len(rows) == 120, "Expected 120 scenarios")

    ids = [row["scenario_id"] for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate scenario IDs found")

    require(
        {row["business_id"] for row in rows} == EXPECTED_BUSINESSES,
        "Unexpected scenario business IDs",
    )

    dev_ids = {row["scenario_id"] for row in dev}
    test_ids = {row["scenario_id"] for row in test}
    require(not (dev_ids & test_ids), "Dev/test scenario overlap")

    for row in rows:
        require(row["caller_goal"].strip(), "Empty caller goal")
        require(row["expected_action"].strip(), "Missing expected action")

    print(f"PASS: Scenarios (dev={len(dev)}, test={len(test)})")


def validate_outbound():
    rows = read_csv("raw/outbound_checks.csv")
    require(len(rows) == 30, f"Expected 30 outbound cases, got {len(rows)}")

    ids = [row["case_id"] for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate outbound case IDs")

    for row in rows:
        if row["consent"] != "True" or row["opted_out"] == "True":
            require(
                row["expected_action"] == "block_contact",
                f"Unsafe outbound expectation: {row['case_id']}",
            )

        if row["out_of_hours"] == "True":
            require(
                row["expected_action"] == "block_contact",
                f"Out-of-hours case should be blocked: {row['case_id']}",
            )

    print(f"PASS: Outbound checks ({len(rows)})")


def validate_business_docs():
    for business_id in EXPECTED_BUSINESSES:
        path = DATA / "raw" / "business_docs" / f"{business_id}.md"
        require(path.exists(), f"Missing business document: {path.name}")
        require(path.stat().st_size > 0, f"Empty business document: {path.name}")

    print(f"PASS: Business knowledge documents ({len(EXPECTED_BUSINESSES)})")


def main():
    validate_business_docs()
    validate_crm()
    validate_scenarios()
    validate_outbound()
    print("All M2 dataset validation checks passed.")


if __name__ == "__main__":
    main()
