"""Run the deterministic outbound gate on all 30 outbound cases.

Each case resets the CRM seed; the gate never dials or changes data. Usage:

    python3 scripts/run_outbound_gate.py [--out experiments/runs/m3_outbound_gate]
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business  # noqa: E402
from voice_agent.inference.outbound_gate import evaluate  # noqa: E402
from voice_agent.utils.common import REPO_ROOT, deep_copy, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPO_ROOT / "experiments/runs/m3_outbound_gate"))
    args = parser.parse_args()

    rows, mismatches, reasons = [], 0, Counter()
    for business in ("solar", "dental", "furniture"):
        pack = load_business(business)
        for case in pack.outbound_cases:
            seed = deep_copy(pack.seed)
            decision = evaluate(seed, case)
            assert seed == pack.seed, "gate must not change the CRM"
            match = decision == case["expected"]
            mismatches += not match
            reasons.update(decision["reasons"] or ["allowed"])
            rows.append({"business": business, "case": case["id"], "contact": case["contact_id"],
                         "at": case["at"], "decision": decision, "expected": case["expected"],
                         "match": match})
            print(f"{business:9} {case['id']}  {'ALLOW' if decision['allowed'] else 'BLOCK'}  "
                  f"{','.join(decision['reasons']) or '-':45} {'ok' if match else 'MISMATCH'}")

    false_allows = sum(1 for r in rows if r["decision"]["allowed"] and not r["expected"]["allowed"])
    summary = {"cases": len(rows), "matches": len(rows) - mismatches,
               "allowed": sum(r["decision"]["allowed"] for r in rows),
               "blocked": sum(not r["decision"]["allowed"] for r in rows),
               "disallowed_calls_allowed": false_allows, "reason_counts": dict(reasons)}
    write_json(Path(args.out) / "results.json", {"summary": summary, "cases": rows})
    print(summary)
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
