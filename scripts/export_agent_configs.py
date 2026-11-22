"""Save the effective agent configurations for M4 Steps 9 and 10 (offline, no model calls).

Writes milestones/M4_training/agents/: each prompt as its own text file (the
archived M3 prompt, the Step 9 single-agent prompt and the four Step 10
multi-agent role prompts), the tool and delegation schemas, and one
effective_config.json with limits, retrieval settings and SHA-256 hashes.

    python3 scripts/export_agent_configs.py
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from voice_agent.data.loader import load_business  # noqa: E402
from voice_agent.data.preprocess import chunk_knowledge  # noqa: E402
from voice_agent.inference import multi_agent as ma  # noqa: E402
from voice_agent.inference.agent import (CLAIM_NUDGE, MAX_TOOL_ROUNDS, MAX_TOOL_STEPS, PROMISE,  # noqa: E402
                                         PROMISE_NUDGE, PROMPTS, SUCCESS_CLAIM)
from voice_agent.inference.crm import TOOL_SCHEMAS  # noqa: E402
from voice_agent.inference.retrieval import BM25Index  # noqa: E402
from voice_agent.pipelines.episode import MAX_CALLER_TURNS  # noqa: E402

OUT = ROOT / "milestones" / "M4_training" / "agents"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    pack = load_business("solar")
    rules = [c for c in chunk_knowledge(pack) if c["kind"] == "sandbox_rule"]
    clock = pack.seed["snapshot_at"]
    agent = ma.MultiAgent(None, pack.name, rules, clock)
    texts = {
        "single_agent_m3_prompt.txt": PROMPTS["m3"](pack.name, rules, clock),
        "single_agent_v2_prompt.txt": PROMPTS["v2"](pack.name, rules, clock),
        **{f"multi_agent_{role}_prompt.txt": agent.prompts[role] for role in ma.ROLES},
    }
    schemas = {
        "single_agent_tools.json": TOOL_SCHEMAS,
        "multi_agent_coordinator_tools.json": ma.COORDINATOR_TOOLS,
        "multi_agent_planner_write_schemas.json": ma.WRITE_SCHEMAS,
        "multi_agent_handoff_contract.json": {
            "only_speaker": "coordinator",
            "dispatch": "sequential; one specialist at a time; no worker-to-worker messages",
            "roles": {
                "knowledge": {"sees": ["coordinator question", "business rules", "its own search_docs results"],
                              "tools": ["search_docs"],
                              "returns": {"answer": "str", "source_ids": "retrieved fact IDs only",
                                          "unretrieved_source_ids": "IDs claimed but not retrieved",
                                          "enough_information": "bool"}},
                "qualification": {"sees": ["caller/agent dialogue text", "rule S9"], "tools": [],
                                  "returns": {"known_fields": "caller-stated lead fields",
                                              "missing_fields": "list", "declined_or_unknown": "list"}},
                "planner": {"sees": ["coordinator goal", "caller/agent dialogue text",
                                     "tool results the coordinator observed", "write tool schemas",
                                     "business rules"], "tools": [],
                            "returns": {"plan_id": "P<n>", "tool": "one write tool",
                                        "arguments": "object", "missing_authorization": "list",
                                        "caller_summary": "str"}},
            },
            "never_seen_by_any_role": ["caller goal/persona", "harness fixtures", "trusted identity truth",
                                       "gold state", "required information", "prohibited actions"],
            "execution": "coordinator only, via execute_crm_plan(plan_id); each plan runs at most once; "
                         "direct write calls are refused with write_requires_crm_plan",
            "trusted_state": "identity binding and caller confirmation stay in the CRM sandbox; "
                             "specialist text cannot create either",
            "failure_handling": "invalid specialist JSON returns specialist_invalid_output to the coordinator; "
                                "cap exhaustion ends the turn with a hand-to-human message",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, text in texts.items():
        (OUT / name).write_text(text + "\n", encoding="utf-8")
        hashes[name] = sha(text + "\n")
    for name, value in schemas.items():
        body = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        (OUT / name).write_text(body, encoding="utf-8")
        hashes[name] = sha(body)
    index = BM25Index([])
    config = {
        "business": "solar",
        "business_clock": clock,
        "model": "set per run (AGENT_MODEL / LLM_MODEL); both designs use the same client for every role",
        "temperature": 0.0,
        "agent_max_output_tokens": 800,
        "limits": {"max_caller_turns": MAX_CALLER_TURNS,
                   "max_model_calls_per_caller_turn": MAX_TOOL_ROUNDS,
                   "max_tool_steps_per_caller_turn": MAX_TOOL_STEPS,
                   "multi_agent_specialists_share_these_caps": True,
                   "knowledge_specialist_search_rounds": ma.MAX_SPECIALIST_ROUNDS},
        "retrieval": {"method": "BM25 over F* fact chunks", "k1": index.k1, "b": index.b, "top_k": 3,
                      "rules": "all S* rules in every system prompt", "embedding_model": "not applicable"},
        "designs": {
            "llm": {"class": "SingleAgent", "prompt": "single_agent_m3_prompt.txt", "guards": "none",
                    "note": "archived M3 baseline, behaviour unchanged"},
            "single_v2": {"class": "SingleAgent", "prompt": "single_agent_v2_prompt.txt",
                          "guards": ["provenance: contact_id/email must come from the caller or a tool result",
                                     "promised action without a tool call, or a success claim with no "
                                     "successful write in the call: draft held back, one corrective nudge "
                                     "per turn; a repeat is logged as *_unresolved"],
                          "tools": "single_agent_tools.json"},
            "multi": {"class": "MultiAgent",
                      "prompts": [f"multi_agent_{r}_prompt.txt" for r in ma.ROLES],
                      "guards": "same two guards as single_v2",
                      "tools": "multi_agent_coordinator_tools.json",
                      "handoff_contract": "multi_agent_handoff_contract.json"},
        },
        "promise_pattern": PROMISE.pattern,
        "promise_nudge": PROMISE_NUDGE,
        "success_claim_pattern": SUCCESS_CLAIM.pattern,
        "success_claim_nudge": CLAIM_NUDGE,
        "validation_layer": "src/voice_agent/inference/crm.py, unchanged rules, shared by all designs",
        "sha256": hashes,
    }
    (OUT / "effective_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    print(f"Wrote {len(hashes) + 1} files to {OUT}")


if __name__ == "__main__":
    main()
