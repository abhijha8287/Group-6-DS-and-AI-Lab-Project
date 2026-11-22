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

During the original Step 6 work, no source was freshly fetched or reverified; only existing narrow factual paraphrases were inherited. The current-page review recorded below is a separate inspection on 2026-11-22 and does not verify the historical 2026-10-29 access record. No third-party source prose, media or customer records were imported. Public availability and paraphrasing are not a rights clearance or a legal assurance. The policy knowledge documents and source claims have not been silently rewritten or approved. No refund entitlement, current subsidy amount or engineering approval is introduced.

## Sarwar source verification findings — 2026-11-22

The following findings record a current-page inspection on **2026-11-22**. They are not evidence that the same page content was accessed on the historical **2026-10-29** date recorded for R1 and R2. The repository's historical access verification remains pending. Source reuse permission and licensing also remain pending; this review makes no legal-clearance claim. These findings are documentation for human review only: F1–F5 in the policy knowledge documents and their source claims remain unchanged, and the pack remains unapproved.

**Supplementary evidence distinction:** The URLs listed in the F1–F5 table are additional official SolarSquare pages inspected for this human review on 2026-11-22. They are supplementary review evidence, not proof of the historical 2026-10-29 access record and not an automatic change to the original R1/R2 source mappings in `sources.json`. Any change to canonical source attribution requires separate review and approval.

| Claim | Current official page evidence inspected on 2026-11-22 | Bounded finding for review |
|---|---|---|
| F1 | [SolarSquare Know More Solar](https://www.solarsquare.in/know-more-solar/), “Precision designs…” / roof survey discussion (page lines 215–235); [SolarSquare commercial page](https://www.solarsquare.in/commercial/) (redirects to `/commercial-solar-panel/`), “Great solar starts with precision designs” (lines 208–210); [Solar panel direction and angle article](https://www.solarsquare.in/blog/what-should-be-the-best-angle-for-a-solar-panel-does-direction-matter/), direction/tilt overview (lines 157–169), “Shadow Analysis” (208–210), and angle FAQ (218–226). | Partially supported. Pages describe roof survey, measurements, shadow analysis, orientation/direction assessment, and tilt/angle assessment. Do not infer that every specific roof type or structural detail in F1 was verified by these pages. Roof access, property permission, and structural suitability remain distinct. |
| F2 | [On-grid vs off-grid vs hybrid solar inverters](https://www.solarsquare.in/blog/on-grid-vs-off-grid-vs-hybrid-solar-inverters/), comparison table (lines 176–183), hybrid outage explanation (273–277), and on-grid/hybrid comparison (325–330). | Supported at the system-type and general blackout-behaviour level. Preserve the page's configuration limits: backup depends on compatible battery storage and configured backup loads; duration/load support depends on system and battery conditions. Do not promise backup for a particular installation. |
| F3 | [PM Surya Ghar page](https://www.solarsquare.in/pm-surya-ghar-muft-bijli-yojana/), “Eligibility & documents” (lines 242–246). | Supported as a residential-versus-commercial/industrial distinction on this SolarSquare page. It does not determine an individual's eligibility; do not infer entitlement from this source. |
| F4 | [SolarSquare homepage](https://www.solarsquare.in/), “Calculate your savings” form (lines 238–258; additional enquiry form lines 599–625); [Commercial solar page](https://www.solarsquare.in/commercial/) (redirects to `/commercial-solar-panel/`), pricing qualifications (lines 275–298). | Supported. The homepage requests a PIN code and average monthly electricity bill. Commercial price information is expressly indicative, not fixed, and described as dependent on multiple factors. Neither input nor indicative pricing establishes a caller's final price, savings, serviceability, or installation date. |
| F5 | [SolarSquare cancellation policy](https://www.solarsquare.in/cancellation-policy/), written-request rule and stage table (lines 143–163); change-of-mind clause (lines 165–170); other refund qualifications in sections 3–9. | Supported that the page requires a written request and specifies stage-dependent cancellation/refund outcomes. Preserve all stated qualifications and the conflict between parts of the page; escalate ambiguous cases for human interpretation. This does not authorize a refund determination or execution. |

The evidence locations above refer to the rendered page text inspected on 2026-11-22 and may move or change. No source content was added to the policy-pack knowledge documents. The findings do not resolve source rights, license terms, historical access verification, or human approval.

## Sarwar S1–S48 consistency audit — 2026-11-22

**Status: complete consistency review; pack approval remains pending.** The full S1–S48 set was reviewed together across both policy documents and checked against `questions.json`, `sources.json`, policy-pack preprocessing/validation, and DEV11–DEV16. Exactly one confirmed internal inconsistency was corrected. No source claims or source attributions were changed. The frozen development inputs were not changed.

### Confirmed defect and correction

| Section / files | Before | After | Related evaluator correction |
|---|---|---|---|
| S3 in `policy_packs/short/knowledge.md` and `policy_packs/large/knowledge.md` | “Only enquiry field updates, callback requests, opt-outs and structured human handoffs are supported.” | “Supported actions are new-enquiry creation only under S1's no-match and explicit-confirmation exception, enquiry field updates, callback requests, opt-outs and structured human handoffs.” | Q07 in `policy_packs/questions.json` now includes the qualified new-enquiry action, requires canonical sections S1 and S3, and labels both as relevant in both packs. |

S1 explicitly permits creation of a new enquiry after a no-match email lookup and explicit confirmation, while the former S3 stated an exhaustive supported-action list that omitted creation. Since S3 describes the action boundary, the omission made S1 and S3 inconsistent and made Q07's former supported-action answer incomplete. S3 now names the exception without broadening it; all prohibitions remain. The copies of shared S3 text are identical in the short and large policy packs.

### Other reviewed sections

- **S1–S10:** No other confirmed contradiction found in identity binding, duplicate handling, new-enquiry limits, voice consent, callback prerequisites, outbound gates, opt-out, CRM scope, or atomic failure behavior. S2's confirmation rule retains the explicit S8 opt-out exception. S3's existing prohibitions remain intact.
- **S11–S34:** No confirmed contradiction found in callback versus visit, enquiry versus cancellation, missing identity/contact data, roof permission/safety, unknown versus negative fields, cancellation escalation, callback save failures, handoff provenance, or caller-asserted authority.
- **S35–S44:** The office, visitor, procurement, inventory, meeting, and equipment examples remain explicitly fictional and do not add a customer CRM, calendar, purchasing, stock, document-delivery, or outbound capability.
- **S45:** Precedence remains consistent: additional sections do not override F1–F5/S1–S10 or create permissions.
- **S46–S48:** The date ranges and stated exceptions are internally consistent as fictional text. S46 labels are not CRM fields; S47's accessibility exception permits review only; S48 does not assert that a copy was generated or delivered. No temporal engine is claimed.

### Cross-file and implementation checks

- `questions.json`: Q07 was the only evaluator item needing correction. Other expected answers and canonical versus pack-specific section annotations remain unchanged in this correction pass.
- `sources.json`: R1 remains mapped to F1–F4 and R2 to F5; permission/license and historical-access status remain as recorded. No source claims were changed to satisfy policy annotations.
- Preprocessing and validation: `scripts/preprocess_policy_packs.py` and `src/voice_agent/data/preprocess.py` enforce structural IDs, source metadata, and annotation integrity, but did not enforce semantic agreement between the S1 exception and S3's supported-action list. No code defect requiring implementation changes was found. A targeted regression test was added to `tests/test_policy_packs.py` for the S3/Q07 relationship.
- DEV11–DEV16: Expected states and communication requirements remain consistent with their frozen snapshot. DEV11 declines contact details and therefore does not exercise successful new-enquiry creation; DEV12–DEV16 do not exercise the corrected action-list omission. The frozen documents, scenario JSON, and manifest were left unchanged.

### Possible improvements and human decisions

- **Possible clarity improvement, S46:** Specify the reference instant for deciding whether a known deadline is “within 48 hours.” This is not a contradiction in the current fictional text.
- **Possible clarity improvement, S47:** Define how “calendar days before” is counted near midnight or when a visitor request arrives on the proposed date. This is not a contradiction in the current fictional text.
- Human review remains required for the intended policy meanings and the pending F1–F5 source/rights questions recorded above. This audit does not approve the policy pack or resolve source permission, licensing, or historical access verification.

### Tests

Added `test_new_enquiry_exception_is_in_supported_actions_and_q07` to `tests/test_policy_packs.py`. Test execution was attempted with `python -m unittest discover -s tests -p test_policy_packs.py -v` and the analogous `test_development.py` command. Both could not start: the discovered Python 3.11 virtual environment points to a missing Windows Store runtime, and the available standalone Python 3.13 runtime lacks the standard library `encodings` module. Therefore no test pass is claimed; rerun both commands in a complete Python environment.

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
