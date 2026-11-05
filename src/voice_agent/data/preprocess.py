"""Preprocessing for the M3 pipeline.

Three steps, none of which learns from data (so nothing is fitted on any split):

1. ``chunk_knowledge``: one chunk per fact (F*) or sandbox rule (S*) row, with
   business ID, kind and source metadata, so a rule never gets separated from
   its exception and businesses never mix.
2. ``task_views``: split each scenario into the agent, simulator and evaluator
   views. The agent never sees the caller goal, fixtures or the answer key.
3. ``estimate_tokens``: an approximate token count (no tokenizer is bundled;
   real counts come from provider usage reports during runs).
"""

from __future__ import annotations

import re

from voice_agent.data.loader import BusinessPack

ROW = re.compile(r"^\|\s*([FSR]\d+)\s*\|\s*(.+?)\s*\|\s*$")
URL = re.compile(r"https?://\S+?(?=\s*\|)")

AGENT_FORBIDDEN = {"caller", "environment", "tool_results", "gold", "evaluation_criteria",
                   "required_information", "prohibited_actions"}


def estimate_tokens(text: str) -> int:
    """About 4 characters per token for English text (rough planning figure)."""
    return max(1, round(len(text) / 4))


def _sources(knowledge_md: str) -> dict:
    """Map source IDs (R1, R2, ...) to (url, access date) from the source register."""
    out = {}
    for line in knowledge_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"R\d+", cells[0]) and cells[1].startswith("http"):
            out[cells[0]] = {"url": cells[1], "access_date": cells[2]}
    return out


def chunk_knowledge(pack: BusinessPack) -> list[dict]:
    sources = _sources(pack.knowledge_md)
    chunks = []
    for line in pack.knowledge_md.splitlines():
        match = ROW.match(line.strip())
        if not match or match.group(1).startswith("R"):
            continue
        fact_id, text = match.group(1), match.group(2).strip()
        cited = sorted(set(re.findall(r"\bR\d+\b", text)))
        chunks.append({
            "business_id": pack.seed["business_id"],
            "fact_id": fact_id,
            "kind": "sourced_fact" if fact_id.startswith("F") else "sandbox_rule",
            "sources": [dict(id=r, **sources[r]) for r in cited if r in sources],
            "text": text,
            "approx_tokens": estimate_tokens(text),
        })
    return chunks


def task_views(task: dict) -> dict:
    """Split one scenario into the three views required by the dataset contract."""
    # The agent gets nothing task-specific beyond an ID: its knowledge and tools are
    # the same for every task, and everything else arrives through the conversation.
    agent = {"id": task["id"]}
    simulator = {"id": task["id"], "caller": task["caller"]}
    evaluator = {
        "id": task["id"],
        "gold": task["gold"],
        "required_information": task["required_information"],
        "prohibited_actions": task["prohibited_actions"],
        "evaluation_criteria": task["evaluation_criteria"],
    }
    harness = {"id": task["id"], "environment": task["environment"], "tool_results": task["tool_results"]}
    return {"agent": agent, "simulator": simulator, "evaluator": evaluator, "harness": harness}


def check_views(views: dict) -> None:
    """Fail loudly if any answer-key field could reach the agent."""
    leaked = AGENT_FORBIDDEN & set(views["agent"])
    if leaked:
        raise AssertionError(f"Agent view leaks {sorted(leaked)}")
