"""Preprocess the knowledge and tasks for the M3 pipeline.

Writes (git-ignored) data/processed/<business>/chunks.jsonl, one view file per
task, and a token report. Usage:

    python3 scripts/preprocess_m3.py --business solar
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business  # noqa: E402
from voice_agent.data.preprocess import check_views, chunk_knowledge, estimate_tokens, task_views  # noqa: E402
from voice_agent.inference.agent import system_prompt  # noqa: E402
from voice_agent.inference.crm import TOOL_SCHEMAS  # noqa: E402
from voice_agent.utils.common import PROCESSED_DIR, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--business", default="solar", choices=["solar", "dental", "furniture"])
    args = parser.parse_args()

    pack = load_business(args.business)
    out = PROCESSED_DIR / args.business
    chunks = chunk_knowledge(pack)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    for task in pack.scenarios:
        views = task_views(task)
        check_views(views)
        for name, view in views.items():
            write_json(out / "views" / task["id"] / f"{name}.json", view)

    rules = [c for c in chunks if c["kind"] == "sandbox_rule"]
    prompt = system_prompt(pack.name, rules, pack.seed["snapshot_at"])
    tools = json.dumps(TOOL_SCHEMAS)
    facts = [c for c in chunks if c["kind"] == "sourced_fact"]
    report = {
        "business": args.business,
        "chunks": len(chunks),
        "sourced_facts": len(facts),
        "sandbox_rules": len(rules),
        "chunk_tokens_approx": {"min": min(c["approx_tokens"] for c in chunks),
                                "max": max(c["approx_tokens"] for c in chunks),
                                "total": sum(c["approx_tokens"] for c in chunks)},
        "system_prompt_tokens_approx": estimate_tokens(prompt),
        "tool_schema_tokens_approx": estimate_tokens(tools),
        "tasks_with_views": len(pack.scenarios),
        "note": "Approximate (characters / 4). Real counts come from provider usage in runs.",
    }
    write_json(out / "token_report.json", report)
    print(json.dumps(report, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
