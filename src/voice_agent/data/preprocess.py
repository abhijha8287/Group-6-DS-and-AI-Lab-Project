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
from voice_agent.utils.common import deep_copy

ROW = re.compile(r"^\|\s*([FSR]\d+)\s*\|\s*(.+?)\s*\|\s*$")
URL = re.compile(r"https?://\S+?(?=\s*\|)")

AGENT_FORBIDDEN = {"caller", "environment", "tool_results", "gold", "evaluation_criteria",
                   "required_information", "prohibited_actions"}


def estimate_tokens(text: str) -> int:
    """About 4 characters per token for English text (rough planning figure)."""
    return max(1, round(len(text) / 4))




def _sources(knowledge_md: str) -> dict:
    """Map source IDs to URLs and optional access dates from the source register."""
    out = {}

    for line in knowledge_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]

        if len(cells) < 3 or not re.fullmatch(r"R\d+", cells[0]):
            continue

        source_id = cells[0]
        url = cells[1]
        # Support Markdown links: [title](URL)
        markdown_link = re.search(r"\]\((https?://[^)]+)\)", url)
        if markdown_link:
            url = markdown_link.group(1)

        if not url.startswith("http"):
            continue

        # Solar format: ID | URL | Access date | Description
        # Dental/Furniture format: ID | URL | Description
        access_date = cells[2] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[2]) else None

        out[source_id] = {
            "url": url,
            "access_date": access_date,
        }

    return out



def validate_knowledge_sources(pack: BusinessPack) -> None:
    """Ensure every source cited by a fact exists in the source register."""
    sources = _sources(pack.knowledge_md)

    for line in pack.knowledge_md.splitlines():
        match = ROW.match(line.strip())

        if not match or match.group(1).startswith("R"):
            continue

        fact_id, text = match.group(1), match.group(2)
        cited = set(re.findall(r"\bR\d+\b", text))

        missing = cited - set(sources)

        if missing:
            raise ValueError(
                f"{fact_id} references missing sources: {sorted(missing)}"
            )


def chunk_knowledge(pack: BusinessPack, *, document_id: str | None = None) -> list[dict]:
    sources = _sources(pack.knowledge_md)
    document_id = document_id if document_id is not None else f"{pack.key}/knowledge"
    if not isinstance(document_id, str) or not document_id.strip() or "#" in document_id:
        raise ValueError("document_id must be nonempty and cannot contain #")
    chunks = []
    seen = set()
    for line in pack.knowledge_md.splitlines():
        match = ROW.match(line.strip())
        if not match or match.group(1).startswith("R"):
            continue
        fact_id, text = match.group(1), match.group(2).strip()
        if fact_id in seen:
            raise ValueError(f"Duplicate knowledge section: {fact_id}")
        seen.add(fact_id)
        cited = sorted(set(re.findall(r"\bR\d+\b", text)))
        chunks.append({
            "document_id": document_id,
            "section_id": fact_id,
            "chunk_id": f"{document_id}#{fact_id}",
            "business_id": pack.seed["business_id"],
            "fact_id": fact_id,
            "kind": "sourced_fact" if fact_id.startswith("F") else "sandbox_rule",
            "sources": [dict(id=r, **sources[r]) for r in cited if r in sources],
            "text": text,
            "approx_tokens": estimate_tokens(text),
        })
    return chunks


def task_views(task: dict) -> dict:
    """Copy one scenario into agent, simulator, evaluator and trusted-harness views."""
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
    return {role: deep_copy(view) for role, view in
            {"agent": agent, "simulator": simulator, "evaluator": evaluator, "harness": harness}.items()}


def check_views(views: dict) -> None:
    """Fail loudly if any answer-key field could reach the agent."""
    fields = {
        "agent": {"id"}, "simulator": {"id", "caller"},
        "evaluator": {"id", "gold", "required_information", "prohibited_actions", "evaluation_criteria"},
        "harness": {"id", "environment", "tool_results"},
    }
    if (not isinstance(views, dict) or set(views) != set(fields)
            or any(not isinstance(v, dict) for v in views.values())):
        raise AssertionError("Exactly four role dictionaries are required")
    task_id = views["agent"].get("id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise AssertionError("Agent task ID must be nonempty text, never a nested payload")
    for role, allowed in fields.items():
        if set(views[role]) != allowed or views[role]["id"] != task_id:
            raise AssertionError(f"Invalid {role} view fields or mismatched task ID")
    caller = views["simulator"]["caller"]
    if not isinstance(caller, dict) or set(caller) != {"persona", "goal", "provided_fields", "confirmation"}:
        raise AssertionError("Simulator must receive only the caller contract")
    if (not isinstance(caller["provided_fields"], dict)
            or any(not isinstance(caller[k], str) for k in ("persona", "goal", "confirmation"))):
        raise AssertionError("Invalid caller field types")
    private = AGENT_FORBIDDEN | {"identity_fixture", "verification_succeeds", "expected_final_state", "expected_answer"}

    def check_public(value):
        if isinstance(value, dict):
            if private & set(value):
                raise AssertionError("Privileged fields in simulator view")
            for child in value.values():
                check_public(child)
        elif isinstance(value, list):
            for child in value:
                check_public(child)

    check_public(caller)
