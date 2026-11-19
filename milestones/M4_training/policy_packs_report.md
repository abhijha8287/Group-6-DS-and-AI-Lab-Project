# Step 6 — reproducible Solar policy document packs

Status: **artifacts ready for human review; factual claims, rights, policies and answer annotations remain unapproved**. No paid provider request was made in this step. No default agent pack, original scenario, CRM fixture, historical score or human adjudication was changed.

## Format and implementation

The existing M2 Solar `knowledge.md` stores F-numbered factual paraphrases, S-numbered invented rules and R-numbered source-register rows. `chunk_knowledge()` makes one whole F/S row per chunk; it does not split paragraphs or tokenize to a fixed model window. Keeping the row intact keeps conditions and exceptions together. The short document is byte-identical to that inherited pilot document. The large document retains every core row verbatim.

Shared preprocessing now adds stable `document_id`, `section_id` and `chunk_id` fields, rejects duplicate section IDs, and accepts an explicit document ID. Default IDs are business-qualified. `BM25Index.search()` preserves stored metadata rather than reducing hits to text/ID/score; existing `id`, `text` and `score` fields remain. The new builder uses the isolated `sungrid_policy_draft` business namespace and separate `short/knowledge` and `large/knowledge` document IDs. For example, `large/knowledge#F2` retains external source R1; synthetic rules retain source `SYNTHETIC` and its review/permission metadata.

`questions.json` and retrieval reports are evaluator-only. Only knowledge chunks enter the index. The standalone comparison indexes both facts and policies; the existing agent instead searches facts and places policy rules in its system prompt. This is not a runtime agent evaluation or a switch to the expanded pack.

## Final inventory

Counts below include each full Markdown document. Word counts use whitespace splitting. Token counts use the existing `max(1, round(characters / 4))` estimate, **not a model tokenizer or provider usage**.

| Measure | Short | Large |
|---|---:|---:|
| Documents | 1 | 1 |
| Words, including Markdown | 979 | 5,523 |
| Estimated document tokens | 1,718 | 9,048 |
| Indexed F/S sections | 15 | 53 |
| Chunks, one per section | 15 | 53 |
| Markdown headings, separately | 5 | 7 |
| Sourced factual sections | 5 | 5 |
| Invented policy sections | 10 | 48 |
| Section-text words, excluding document framing | 597 | 4,844 |
| Sum of section token estimates | 1,095 | 8,074 |

The final manifest records document and individual section text hashes, source IDs, line numbers, input hashes, implementation hashes and generated artifact hashes. No timestamp or random identifier enters generated outputs. Independent builds in separate processes produced byte-identical files in the checked environment.

## What adds complexity

- S11–S34 clarify callback versus visit, identity versus consent, enquiry versus cancellation, uncertain roof rights/shading, absent versus negative values, failed saves, provenance and caller-asserted authority. These are refinements, not 24 independent new capabilities.
- S35–S44 add plausible but irrelevant office, procurement, inventory, meeting and equipment-loan material with similar terms.
- S45 states precedence: inherited F1–F5/S1–S10 remain controlling boundaries.
- S46 adds fictional dispute-review priority versions before/after 2026-11-15, a known deadline within 48 hours, and an ambiguous-deadline exception. These labels are not new supported CRM fields.
- S47 changes fictional visitor notice before/after 2026-11-10, with an accessibility exception that permits review, not entry approval.
- S48 changes fictional review-copy format before/after 2026-11-01, with an accessibility plain-text exception.

The pack is a snapshot as of 2026-11-19. Earlier dates are explicitly invented version histories, not legal dates. No software chooses versions or executes these new policies. A reviewer has concrete dated/exception examples to check; temporal reasoning has **not** been evaluated.

## Sources and permissions

`policy_packs/sources.json` distinguishes:

| ID | Origin | Recorded access | Permission/license |
|---|---|---|---|
| R1 | `https://www.solarsquare.in/` | Inherited 2026-10-29 | Unknown/not granted; license unknown |
| R2 | `https://www.solarsquare.in/cancellation-policy/` | Inherited 2026-10-29 | Unknown/not granted; license unknown |
| SYNTHETIC | Original fictional project draft, S1–S48 | Not an external source | No external rights implied; human review pending |

No source was freshly fetched or reverified in this step. Only existing narrow factual paraphrases were inherited; no third-party source prose, media or customer records were imported. Public availability and paraphrasing are not a rights clearance or a legal assurance. The historical cancellation ambiguity remains unresolved; no refund entitlement, current subsidy amount or engineering approval is introduced.

## Questions and retrieval annotations

One shared evaluator file contains **14 matched answerable questions and 6 unanswerable questions**. Shared canonical sections and expected answers cannot drift between packs. Unanswerable cases cover refund amount, a particular roof's suitability, a specific system's backup capability, live callback availability/saved state, duplicate-name identity and guaranteed subsidy amount. Each records missing information, a clarification/escalation action and supporting boundary sections. No agent response or successful abstention is inferred from retrieval alone.

Two evidence concepts are deliberately separate:

1. `required_section_ids`: identical canonical core evidence. Its metric is **canonical-core coverage**, not exhaustive relevance recall.
2. `relevant_section_ids_by_pack`: draft direct alternative or partial evidence in each pack, with mere cross-references/generic restrictions excluded. **Annotated relevance Recall@k** uses these labels. They await human review and are not certified exhaustive.

Any-relevant hit rate means at least one labeled relevant section was found. A partial supporting section need not answer every clause. More relevant sections in the larger pack also change the recall denominator. None of these metrics measures complete-answer accuracy.

Final default BM25 results, **14 answerable questions only**:

| Metric | Short | Large |
|---|---:|---:|
| Annotated relevance Recall@1 | 80.95% | 33.12% |
| Annotated relevance Recall@3 | 90.48% | 74.27% |
| Annotated relevance Recall@5 | 94.05% | 82.74% |
| Annotated relevance Recall@10 | 97.62% | 92.18% |
| Canonical-core coverage@3 | 100% | 78.57% |
| Any-relevant hit rate@3 | 100% | 100% |

Six unanswerable questions are excluded from recall denominators, with recall null, not zero or a fabricated perfect score. Answer and abstention accuracy are null. Per-question ranks, chunk/document/section IDs and source metadata are retained in `retrieval.json`. An initial canonical-only run is preserved separately; its old `macro_recall_at_k` field must be read as canonical-core coverage, not the final annotated relevance metric.

## Checks, artifacts and reproduction

- Final command: `python3 -m unittest discover -s tests -v` — **89 passed, 0 skipped, exit 0**. The earlier 87-test run is retained.
- Tests cover original pilot preservation, shared core sections, metadata surviving retrieval, disjoint variant chunk IDs, malformed annotations, unknown/duplicate IDs, source metadata, correct metric denominators, valid alternative evidence, dated-policy text presence, hashes, deterministic generation and overwrite refusal.
- Final build: `python3 scripts/preprocess_policy_packs.py --output experiments/runs/m4_step6_policy_packs_final` — exit 0. Another process built into a temporary new directory and all four generated files matched byte-for-byte.
- Reproduce into a **new** directory: `python3 scripts/preprocess_policy_packs.py --output /tmp/solar-policy-check-NEW`. Existing directories are refused; do not remove historical outputs to rerun.
- Initial output retained: `experiments/runs/m4_step6_policy_packs/`. Final output: `experiments/runs/m4_step6_policy_packs_final/`.
- Evidence: `evidence/step6/`, including all commands/logs, initial input/code snapshots, reproducibility hashes, review resolution and preservation checks.

The AI technical reviewer identified incomplete relevance labeling and insufficient new conditional/date complexity. Both were corrected; follow-up found no further important issue within its read-only scope. This was **not human review** and did not verify external source claims or permissions.

## Human review request and stop boundary

`policy_packs/REVIEW_REQUEST.md` asks a team member to check source claims and rights, operational assumptions, exceptions, dates, precedence, answers and relevance labels. The user selected **“I'll review it myself”** in the structured handoff. The reviewer field now records the user as the pending reviewer; review date and decision remain blank. No findings or approval have been received, and no external teammate was contacted. Assignment is not completed review or factual/rights approval.

Stop here with the artifacts ready for review. This exercise covers only **two documents, 15/53 chunks, 14 answerable and 6 unanswerable questions**, using deterministic lexical retrieval. It establishes no generated-answer, clarification/escalation, audio, latency, large-corpus, production, factual-accuracy or legal-compliance robustness.
