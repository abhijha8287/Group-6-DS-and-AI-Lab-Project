"""Small-scale end-to-end run for Milestone 3.

Modes:
  llm                      LLM agent + LLM caller + LLM judge (needs LLM_PROVIDER/LLM_MODEL in .env)
  oracle                   harness check: replays the expected tool calls (no LLM)
  control_skip_confirmation, control_skip_verification
                           negative controls that must be blocked (no LLM)

Examples:
  python3 scripts/run_m3_pipeline.py --mode oracle
  python3 scripts/run_m3_pipeline.py --mode llm --tasks IN01 IN02
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import load_business, select_tasks  # noqa: E402
from voice_agent.models.llm import make_client  # noqa: E402
from voice_agent.pipelines.episode import run_subset  # noqa: E402
from voice_agent.utils.common import load_env  # noqa: E402

MODES = ["llm", "oracle", "control_skip_confirmation", "control_skip_verification"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--business", default="solar", choices=["solar"],
                        help="M3 tools are implemented for solar only")
    parser.add_argument("--mode", default="oracle", choices=MODES)
    parser.add_argument("--tasks", nargs="*", help="task IDs (default: the 10 pilot dev tasks)")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    load_env()
    pack = load_business(args.business)
    tasks = select_tasks(pack, args.tasks, split="dev")
    clients = {}
    if args.mode == "llm":
        clients = {role.lower(): make_client(role) for role in ("AGENT", "SIMULATOR", "JUDGE")}
    run = run_subset(pack, tasks, args.mode, clients, run_id=args.run_id)
    print(json.dumps(run["summary"], indent=2))
    print(f"Saved to {run['out_dir']}")


if __name__ == "__main__":
    main()
