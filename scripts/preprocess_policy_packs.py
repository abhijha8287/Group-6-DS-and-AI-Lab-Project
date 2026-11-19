"""Build isolated Solar policy packs and measure section-level BM25 Recall@k offline."""

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_agent.data.loader import BusinessPack
from voice_agent.data.preprocess import ROW, chunk_knowledge, estimate_tokens, validate_knowledge_sources
from voice_agent.inference.retrieval import BM25Index
from voice_agent.utils.common import REPO_ROOT, read_json, write_json

PACK_ROOT = REPO_ROOT / "milestones/M4_training/policy_packs"
KS = (1, 3, 5, 10)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root):
    sources = read_json(root / "sources.json")
    annotations = read_json(root / "questions.json")
    date.fromisoformat(annotations["as_of"])
    for source_id in ("R1", "R2", "SYNTHETIC"):
        entry = sources[source_id]
        if not all(isinstance(entry.get(k), str) and entry[k].strip()
                   for k in ("permission_status", "license", "human_review")):
            raise ValueError(f"Missing permission/license/review metadata for {source_id}")
    packs = {}
    for variant in ("short", "large"):
        relative = f"{variant}/knowledge.md"
        path = root / relative
        text = path.read_text(encoding="utf-8")
        pack = BusinessPack("solar", "SunGrid Rooftop Solar", text, {"business_id": "sungrid_policy_draft"})
        validate_knowledge_sources(pack)
        chunks = chunk_knowledge(pack, document_id=f"{variant}/knowledge")
        if not chunks:
            raise ValueError(f"Empty pack: {variant}")
        sections = []
        lines = {m.group(1): i for i, line in enumerate(text.splitlines(), 1)
                 if (m := ROW.match(line.strip())) and not m.group(1).startswith("R")}
        for chunk in chunks:
            if chunk["kind"] == "sourced_fact":
                if not chunk["sources"]:
                    raise ValueError(f"Unattributed factual section: {chunk['section_id']}")
                for source in chunk["sources"]:
                    entry = sources[source["id"]]
                    if (entry["url"] != source["url"]
                            or entry["historical_access_date"] != source["access_date"]
                            or chunk["section_id"] not in entry["inherited_claim_ids"]):
                        raise ValueError(f"Source register mismatch: {chunk['section_id']}")
                    source["metadata"] = entry
            else:
                chunk["sources"] = [{"id": "SYNTHETIC", "metadata": sources["SYNTHETIC"]}]
            sections.append({"section_id": chunk["section_id"], "chunk_id": chunk["chunk_id"],
                             "line_number": lines[chunk["section_id"]],
                             "source_ids": [s["id"] for s in chunk["sources"]],
                             "text_sha256": hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()})
        packs[variant] = {"chunks": chunks, "statistics": {
            "document_count": 1, "document_path": relative, "document_sha256": sha256(path),
            "word_count_whitespace_including_markdown": len(text.split()),
            "estimated_document_tokens_char4": estimate_tokens(text),
            "section_text_word_count_whitespace": sum(len(c["text"].split()) for c in chunks),
            "estimated_section_tokens_sum_char4": sum(c["approx_tokens"] for c in chunks),
            "section_count": len(chunks), "chunk_count": len(chunks),
            "markdown_heading_count": sum(bool(re.match(r"^#+ ", line)) for line in text.splitlines()),
            "sourced_fact_count": sum(c["kind"] == "sourced_fact" for c in chunks),
            "sandbox_rule_count": sum(c["kind"] == "sandbox_rule" for c in chunks),
            "sections": sections}}
    short = {c["section_id"]: c for c in packs["short"]["chunks"]}
    large = {c["section_id"]: c for c in packs["large"]["chunks"]}
    if not all(i in large and c["text"] == large[i]["text"] for i, c in short.items()):
        raise ValueError("Shared source sections must be identical across both packs")
    extra = [c for i, c in large.items() if i not in short]
    if not extra or any(c["kind"] != "sandbox_rule" for c in extra):
        raise ValueError("Expansion must add explicitly synthetic sandbox sections")
    if len({c["text"] for c in large.values()}) != len(large):
        raise ValueError("Repeated sections are not policy complexity")
    seen = set()
    questions = annotations["questions"]
    for q in questions:
        if not isinstance(q["id"], str) or not q["id"] or q["id"] in seen:
            raise ValueError("Question IDs must be nonempty and unique")
        seen.add(q["id"])
        if type(q["answerable"]) is not bool or not isinstance(q["question"], str) or not q["question"].strip():
            raise ValueError(f"Invalid question: {q['id']}")
        for field in ("required_section_ids", "supporting_boundary_section_ids"):
            ids = q[field]
            if (not isinstance(ids, list) or any(not isinstance(i, str) for i in ids)
                    or len(set(ids)) != len(ids) or not set(ids) <= set(short)):
                raise ValueError(f"Unknown/duplicate source annotation: {q['id']} {field}")
        if not isinstance(q["annotation_rationale"], str) or not q["annotation_rationale"].strip():
            raise ValueError(f"Missing annotation rationale: {q['id']}")
        relevant = q["relevant_section_ids_by_pack"]
        if not isinstance(relevant, dict) or set(relevant) != {"short", "large"}:
            raise ValueError(f"Both pack-specific relevance annotations are required: {q['id']}")
        for variant in packs:
            ids = relevant[variant]
            known = {c["section_id"] for c in packs[variant]["chunks"]}
            if (not isinstance(ids, list) or any(not isinstance(i, str) for i in ids)
                    or len(set(ids)) != len(ids) or not set(ids) <= known
                    or (q["answerable"] and not set(q["required_section_ids"]) <= set(ids))
                    or (not q["answerable"] and ids)):
                raise ValueError(f"Invalid pack-specific relevance: {q['id']} {variant}")
        if not isinstance(q["expected_answer"], str):
            raise ValueError(f"Expected answer must be text: {q['id']}")
        if (not isinstance(q["missing_information"], list)
                or any(not isinstance(item, str) or not item.strip() for item in q["missing_information"])):
            raise ValueError(f"Missing-information annotations must be a list of text: {q['id']}")
        if q["answerable"]:
            if not q["required_section_ids"] or not q["expected_answer"].strip() or q["expected_action"] != "answer":
                raise ValueError(f"Answerable question lacks an answer/gold sections: {q['id']}")
        elif (q["required_section_ids"] or q["expected_action"] not in ("clarification", "escalation")
              or not q["missing_information"]):
            raise ValueError(f"Unanswerable question needs missing information, not gold answer sections: {q['id']}")
    if not any(q["answerable"] for q in questions) or not any(not q["answerable"] for q in questions):
        raise ValueError("Both answerable and unanswerable questions are required")
    return packs, annotations, sources


def retrieval_report(chunks, questions, variant):
    index = BM25Index(chunks)
    rows = []
    for q in questions:
        hits = index.search(q["question"], k=max(KS))
        gold = set(q["relevant_section_ids_by_pack"][variant])
        core = set(q["required_section_ids"])
        recalls = {str(k): len(gold & {h["section_id"] for h in hits[:k]}) / len(gold)
                   for k in KS} if q["answerable"] else None
        core_recalls = {str(k): len(core & {h["section_id"] for h in hits[:k]}) / len(core)
                        for k in KS} if q["answerable"] else None
        hit_at_k = {str(k): bool(gold & {h["section_id"] for h in hits[:k]})
                    for k in KS} if q["answerable"] else None
        rows.append({"question_id": q["id"], "question": q["question"], "answerable": q["answerable"],
                     "required_section_ids": q["required_section_ids"], "recall_at_k": recalls,
                     "relevant_section_ids": sorted(gold), "canonical_core_recall_at_k": core_recalls,
                     "any_relevant_hit_at_k": hit_at_k,
                     "expected_action": q["expected_action"],
                     "supporting_boundary_section_ids": q["supporting_boundary_section_ids"],
                     "hits": [{key: hit[key] for key in
                               ("chunk_id", "document_id", "section_id", "sources", "score")} for hit in hits]})
    answerable = [r for r in rows if r["answerable"]]
    return {"method": "BM25 defaults; all sourced and synthetic sections indexed together; macro recall over draft pack-specific relevance labels",
            "annotation_status": "AI draft, human review pending; relevance not certified exhaustive",
            "canonical_core_metric": "Separate coverage of identical core source IDs, not exhaustive relevance recall or answer accuracy",
            "ks": list(KS), "answerable_denominator": len(answerable),
            "unanswerable_count_excluded_from_recall": len(rows)-len(answerable),
            "macro_recall_at_k": {str(k): sum(r["recall_at_k"][str(k)] for r in answerable)/len(answerable) for k in KS},
            "macro_canonical_core_recall_at_k": {str(k): sum(r["canonical_core_recall_at_k"][str(k)] for r in answerable)/len(answerable) for k in KS},
            "any_relevant_hit_rate_at_k": {str(k): sum(r["any_relevant_hit_at_k"][str(k)] for r in answerable)/len(answerable) for k in KS},
            "abstention_accuracy": None, "answer_accuracy": None,
            "limitations": "Retrieval only. No generated answers, temporal rule engine, or clarification/escalation behavior tested.",
            "questions": rows}


def build(root, out):
    packs, annotations, sources = prepare(root)
    out.mkdir(parents=True, exist_ok=False)
    reports = {}
    for variant, pack in packs.items():
        write_json(out / f"{variant}_chunks.json", pack["chunks"])
        reports[variant] = retrieval_report(pack["chunks"], annotations["questions"], variant)
    write_json(out / "retrieval.json", reports)
    inputs = ["short/knowledge.md", "large/knowledge.md", "questions.json", "sources.json"]
    write_json(out / "manifest.json", {
        "as_of": annotations["as_of"], "business": "solar", "business_id": "sungrid_policy_draft",
        "variants": {v: p["statistics"] for v, p in packs.items()},
        "question_count": len(annotations["questions"]), "source_metadata": sources,
        "input_sha256": {name: sha256(root / name) for name in inputs},
        "implementation_sha256": {name: sha256(REPO_ROOT / name) for name in (
            "scripts/preprocess_policy_packs.py", "src/voice_agent/data/preprocess.py",
            "src/voice_agent/inference/retrieval.py", "src/voice_agent/data/loader.py", "src/voice_agent/utils/common.py")},
        "output_sha256": {p.name: sha256(p) for p in sorted(out.glob("*.json"))},
        "token_count_method": "estimate_tokens: max(1, round(characters/4)); not a model tokenizer or billed usage",
        "chunking": "One complete F/S table row per chunk/section; no overlap or paragraph splitting",
        "relevance_definition": annotations["relevance_definition"],
        "human_review": "pending; see policy_packs/REVIEW_REQUEST.md",
        "paid_requests": 0})
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing directories are refused")
    args = parser.parse_args()
    reports = build(PACK_ROOT, args.output)
    for variant, report in reports.items():
        print(variant, report["macro_recall_at_k"], "answerable n=", report["answerable_denominator"])
    print(f"Saved to {args.output}; no provider requests")


if __name__ == "__main__":
    main()
