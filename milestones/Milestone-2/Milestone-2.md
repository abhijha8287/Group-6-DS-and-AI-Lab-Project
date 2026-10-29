# Milestone 2: Dataset and Data Preparation

**Project:** Voice Agents for Small-Business Enquiries and Lead Follow-up: Single-Agent vs Multi-Agent

**Group:** 6 · DS and AI Lab, IIT Madras

**Submission date:** 29 October 2026

**Status:** Work in progress. Dataset preparation artifacts are submitted with the limitations below; this is not a completed evaluation benchmark or evidence of agent performance.

## 1. Objective and scope

We prepare a synthetic, resettable small-business sandbox for comparing single-agent and multi-agent workflows. The data covers UrbanNest Furniture, SunGrid Rooftop Solar and BrightSmile Dental Studio. Tasks concern enquiries, qualification, identity-sensitive CRM changes, callback/handoff requests and consent-gated outbound eligibility. Payments, public calling, production CRM writes and clinical advice are excluded.

The [M1 plan](../M1_problem_literature/report.md#6-datasets-and-baselines) proposed about 40 inbound scenarios and 50–100 contacts per business, an outbound gate suite, reviewed knowledge and development/held-out test data. Generated expansions now target those record counts, but record quantity does not establish reviewed coverage or independent evaluation readiness. We will finish content review, integration and protected test authoring. No model is trained or fine-tuned in this project.

## 2. Dataset and data sources

### 2.1 Sources, ownership and usage constraints

| Fictional business | Public primary references | Local source register |
|---|---|---|
| UrbanNest Furniture | [IKEA India returns](https://www.ikea.com/in/en/customer-service/returns-claims/return-policy/) and [FAQ](https://www.ikea.com/in/en/customer-service/faq-pub7f08ed41/) | [Furniture knowledge](../M2_dataset/furniture_pilot/knowledge.md), accessed 28 October 2026 |
| SunGrid Rooftop Solar | [SolarSquare](https://www.solarsquare.in/) and [cancellation policy](https://www.solarsquare.in/cancellation-policy/) | [Solar knowledge](../M2_dataset/solar_pilot/knowledge.md), accessed 29 October 2026 |
| BrightSmile Dental Studio | [Toothmate](https://www.toothmate.co.in/) and [refund policy](https://www.toothmate.co.in/refund-policy) | [Dental knowledge](../M2_dataset/dental_pilot/knowledge.md), accessed 29 October 2026 |

The primary pages were inspected during AI-assisted authoring/review; source registers record the narrow adopted facts and limits. Sources can change and are not live policy feeds. Reference businesses own their original material; citation does not grant redistribution rights. Our packs use bounded paraphrases, not copied customer records, images, testimonials or benchmark tasks. Comprehensive human rights/policy clearance is not claimed.

Contacts, identities, consent evidence, events, caller instructions, expected outcomes and operational policies are original AI-assisted synthetic project artifacts. The named businesses are fictional and unaffiliated with the reference businesses. Fact IDs `F*` distinguish sourced references from invented sandbox rules `S*`. The repository has an [MIT license](../../LICENSE); this does not relicense third-party source material. Use these artifacts only as sandbox data, not as real customers, verified business advice or legal/clinical compliance evidence. Emails use reserved `.invalid` addresses; outbound fixtures use synthetic identifiers, not authorization to call anyone.

### 2.2 Formats and inventory

The dataset uses UTF-8 Markdown for knowledge, JSON for CRM/task/gate records and split manifests, and standard-library Python for preparation and static validation.

| Component | Per business | Total | Meaning |
|---|---:|---:|---|
| Original pilot contacts | 12 | 36 | Resettable fixture seed |
| Original inbound tasks | 10 | 30 | Detailed caller goals, trusted identity, tool responses and gold changes |
| Original outbound cases | 5 | 15 | Offline gate fixtures |
| Generated contact files | 50 | 150 | Include 12 original + 38 new per business; separate from the pilot seed |
| Expanded inbound files | 40 | 120 | Include the original 10 per business; not 120 additional independent tasks |
| Expanded outbound files | 10 | 30 | Include original cases; not 30 additional fixtures |
| Development-review manifest | 28 | 84 | Provisional organizational partition |
| Test-review manifest | 12 | 36 | Exposed review partition, not a validated held-out set |

Artifacts and script links are listed in the [dataset README](../M2_dataset/README.md). Pilot and expanded counts must not be added together as distinct tasks or contacts without checking their overlap and intended role.

## 3. Feature distribution and dataset quality

### 3.1 Features and characteristics

All three businesses have equal record-count representation in each inventory tier. The pilots use a common family of IDs, contact history, consent, opt-out, retry/recency and expected-state fields, with domain-specific qualification fields. Furniture collects category, budget, PIN and timeline; solar collects roof/property context, bill, location and timeline; dental collects only administrative service, visit mode and timing preferences, not clinical records.

Pilot tasks cover FAQ/no-write answers, new enquiries, verified writes, ambiguity, handoffs, policy boundaries, atomic tool failure, prompt injection and opt-out. Outbound cases exercise permission and suppression decisions. Exact category mixtures differ by business; equal numbers do not imply equal difficulty. All fixtures are synthetic English-language text, not recorded conversations or observed agent trajectories.

### 3.2 Verified expanded-data profile

Offline inspection of the expanded artifacts at `f2bd392` found the following. These are fixture statistics, not model results.

| Check | Furniture | Solar | Dental |
|---|---:|---:|---:|
| Contacts | 50 | 50 | 50 |
| Duplicate contact IDs within business | 0 | 0 | 0 |
| Duplicate contact emails within business | 0 | 0 | 0 |
| Missing contact schema keys | 0 | 0 | 0 |
| Top-level null field values | 115 | 136 | 115 |
| Expanded inbound tasks with no gold mutation | 35 / 40 | 35 / 40 | 35 / 40 |

All 150 emails use `@example.invalid`; no contact has a phone field. Each business uses IDs C01–C50, so bare IDs deliberately repeat across businesses. Two email values also repeat across solar and dental: identities must be keyed by business plus contact ID, not a global bare ID/email. All 114 newly added contacts have no consent, no opt-out, zero attempts and null consent evidence/last-attempt time.

Feature distribution: furniture category counts are desk 6, chair 7, sofa 6, shelf 7, worktop 7, bed 7, dining_table 4 and null 6. Solar ownership counts are owner 17, tenant 13, unknown 13, family_owned 5, co_owner 1 and null 1. Dental service counts are consultation 13, whitening 17, implant 10, appointment_information 6, cleaning 3 and null 1. These generated labels still require review against intended business vocabulary.

Most nulls are interaction-state placeholders: each business has 48 null last-attempt timestamps and 45 null consent records. Other nulls represent intentionally unknown qualification preferences. The 30 added inbound tasks per business are ten topic templates with three variants, all no-write. Therefore the expansions are heavily weighted toward information/refusal tasks and do not broaden mutating CRM coverage proportionately. Category strings include variant suffixes; counting distinct labels would overstate independent intent diversity.

### 3.3 Missing values, inconsistencies, noise and duplicates

- **Missing values:** null qualification fields are intentionally unknown, not zero, negative eligibility or permission to infer values. Do not impute consent, identity, roof suitability or clinical information. Unknown business facts require uncertainty/handoff rather than invented answers.
- **Inconsistencies:** original validators check selected identity/confirmation bindings, canonical effects, unchanged history, atomic failures and gate labels. The generated contact and inbound files require separate checks and human review; a pilot pass does not certify expansions or integration.
- **Duplicates:** repeated names are intentional identity challenges; names alone must not authorize updates. IDs are scoped to a business/reset environment. Expanded files include pilot-derived content, and template variants are not independent observations. Split ID disjointness is insufficient to establish semantic independence.
- **Noise and realism:** no sensor noise, ASR errors or real caller variation is measured. Fixed tool results, exact handoff templates, deterministic availability and synthetic verification simplify the environment. They support debugging, not naturalistic voice-quality claims.
- **Quality evidence:** all three original pilot validators and the expanded outbound consistency check are runnable below. AI review histories retain findings and corrections. Human source/policy and expanded-data approval remain pending; Abhishek's reported review/coordination is not represented as blanket approval of every generated record.

### 3.4 Adequacy and expansion

The original pilots provide inspectable examples of safety constraints and expected effects. The larger generated artifacts broaden the authoring pool but do not yet prove complete policy coverage, realistic task diversity or scoring correctness. The current release is adequate for schema/preparation review and early integration design, not final single-/multi-agent comparison. Expansion and supplementary public text/speech corpora may support later sanity checks, subject to license and task-alignment review; no external benchmark dataset is bundled here.

## 4. Dataset splits and leakage prevention

**Training:** not applicable; the project uses pretrained speech/language models and compares system designs rather than training weights.

**Development/validation:** all current published pilot and expansion artifacts are review-stage material. Development is for prompt/tool iteration; validation will assess authoring/integration changes. The committed manifest assigns 28 development-review and 12 test-review scenario IDs per business. These labels describe organization, not proof of generalization.

**Test:** there is no certified unseen test set in this submission. Reviewers and authors have already accessed these files. The 36 test-review entries must not be reported as independent held-out benchmark evidence. We will author/freeze protected tasks before final comparison and keep development/validation/test manifests separate.

**Observed overlap checks:** the manifest assigns IN01–IN28 to development-review and IN29–IN40 to test-review for each business. Inspection found no ID intersections, exact duplicate scenarios after removing IDs, or cross-partition matches of the combined topic signature (knowledge references, required information, prohibited actions and gold). These checks do not prove semantic independence: both partitions share the generator, variant patterns and mostly empty-gold structure, and have been exposed for review.

**Further leakage prevention:** check normalized caller goals, copied templates, related task families, linked contacts and expected-state patterns across partitions. Group related scenarios together and inspect semantic near-duplicates before freezing a final test set. Business policy documents can be shared with an agent as intended retrieval knowledge; hidden gold, caller goals, confirmation labels and harness-owned identity must not enter its context. Static partition assignment alone does not satisfy these checks. Unresolved overlap is a reported limitation, not a claimed pass.

## 5. Synthetic data generation and design choices

The original pilots were AI-assisted drafts grounded in limited public references, then reviewed with independent AI agents and deterministic negative controls. Original authoring prompts and model settings were not archived as a complete reproducible generation transcript; do not claim bit-for-bit regeneration of the original drafting process. The committed artifacts are the frozen source for reproducing validation.

The expansion scripts deterministically derive additional synthetic contacts/scenarios/gates from the project fixtures. They do not scrape patient/customer data or run live tools. Generation scripts and committed outputs are retained so preparation can be inspected and repeated. Generated variants remain pending review; changing a date, ID or field alone does not create a new independent evaluation case.

Design choices include fictional businesses for safety, explicit rule IDs for traceability, independent whole-seed resets for reproducibility, caller confirmation before writes, separate trusted identity, no-write/refusal gold, and atomic failure fixtures. Fixed tool-owned handoff templates make exact state comparison possible but do not score generated conversational summaries.

## 6. Multiple datasets and subtask alignment

Use the business/domain identifier to select its knowledge and CRM state. A task resets that business's original seed, supplies caller-only instructions to the simulator and observed tool responses to the agent, and keeps gold/criteria/harness authorization evaluator-only. Gold expresses permitted field patches and record appends; unrelated contacts, history and consent evidence remain unchanged. Required communicated facts are distinct from expected database state.

The outbound suite checks eligibility using synthetic contacts/events, consent, opt-out, allowlist, time, recency, retry and deduplication state. It never dials or enqueues. Requested callbacks do not bypass dispatch gates. Expanded contacts and scenario documents must be reconciled with the seed and tool contracts before a runner consumes them; no automatic live integration is claimed. In particular, generated contacts already contain C13, while the original new-enquiry tasks expect to create C13. Do not replace their pilot seeds with the expanded files without remapping task identities and expected effects. Dental appointment requests are distinct from callbacks and delivered clinical care.

## 7. Model-specific data requirements

### 7.1 RAG-based setup

**Actual document preparation:** narrow source facts were paraphrased into Markdown knowledge packs, assigned stable `F*` IDs and separated from invented `S*` policies. Citations, source dates and business boundaries are preserved. No embedding index has been built or evaluated.

**Proposed chunking:** start with one fact/policy row or coherent headed section per chunk, retaining business ID, fact/rule ID, source URL/date and assumption status. Compare this with fixed 300–500-token chunks with modest overlap. Avoid separating a policy condition from its exception or blending businesses. Measure token lengths with the selected tokenizer when the runtime model is chosen; no measured token budget is claimed now.

**Vector-store exploration:** a direct/lexical lookup over these small packs may suffice initially. Compare local FAISS or Chroma for an embedding prototype with PostgreSQL/pgvector if shared persistent retrieval is needed. These are options, not installed or tested components. Enforce business metadata filtering and retrieve only knowledge—not evaluator-only task fields. Retrieval quality and grounded answers will be tested during integration.

### 7.2 Speech-based setup

This release contains no recorded/generated audio, transcripts aligned to waveforms, sampling measurements or speech-quality results. Future preparation will retain original sample rates/channels, resample consistently to each STT/TTS provider's required format, reject clipped/unintelligible files, and record duration, speaker/turn boundaries, transcript version and alignment timestamps. Validate intelligibility and alignment before scoring ASR or full-duplex timing. Do not report absent audio measurements as zero errors or successful voice tests.

### 7.3 Vision and LLM fine-tuning

Vision labels and instruction-response training datasets are not applicable. Prompt preparation must separate agent-visible knowledge and tool schemas from simulator instructions and hidden evaluation fields. Runtime context/token limits will be measured for the chosen models in M3; no training-format or model-weight artifacts are claimed.

## 8. Reproducibility and validation

Use Python 3 with the standard library and Asia/Kolkata timezone support. Run from repository root, without `python -O` because the fixture validators use assertions. Inspect generation scripts first and regenerate into a disposable clone/worktree: they write derived artifacts. Do not overwrite reviewed outputs in a working tree containing uncommitted changes.

Original pilot validation:

```sh
python3 -B milestones/M2_dataset/furniture_pilot/validate.py
python3 -B milestones/M2_dataset/solar_pilot/validate.py
python3 -B milestones/M2_dataset/dental_pilot/validate.py
```

Expanded preparation and static checks:

```sh
python3 -B scripts/generate_m2_contacts.py --target-per-business 50
python3 -B scripts/expand_m2_scenarios.py
python3 -B scripts/expand_m2_outbound.py
python3 -B scripts/create_m2_split_manifest.py
python3 -B scripts/validate_m2_outbound.py
```

**Results reproduced for this documentation:** all three pilot validators passed; the expanded outbound check matched 30/30 expected labels (6 allowed, 24 blocked). Independent offline extraction/regeneration reproduced the nine expanded contact/scenario/outbound JSON files byte-for-byte; manifest differences were path separators between Windows and POSIX, not evidence of a protected split. Existing contact field checks passed on 150 expanded contacts, and all 120 scenarios referenced defined knowledge IDs. No expanded end-to-end replay or comprehensive semantic evaluation was performed.

A PASS establishes only the implemented fixture assertions or static gate-label consistency. No live CRM, phone call, agent conversation, semantic scoring, benchmark run or human approval follows from these commands. The [README](../M2_dataset/README.md) and [review histories](../M2_dataset/DENTAL_REVIEW.md) distinguish original and expanded validation scope.

## 9. Remaining work and completion plan

We will finish expanded schema/content and seed/task integration checks, resolve duplicate/template and split issues, complete human source/policy review, and freeze a genuinely protected final evaluation set. We will refine RAG preparation and audio requirements during M3 integration. Review slides and any remaining member acknowledgement/roll-number details still need completion. These are explicit outstanding items, not work represented as already finished. No deadline extension or acceptance of incomplete requirements is assumed.

## 10. Individual contributions

| Member | M2 contribution and evidence |
|---|---|
| Srijan | Coordinated AI-assisted pilot authoring/review, source and contract checks, dental-validator repairs and rejection controls; organized the WIP branch and prepared submission documentation and contribution/acknowledgement updates. Pilot commits: `25ad148`, `2efa053`. |
| Abhishek Jha | M2 review and coordination, as confirmed by Srijan. Entry and authorized acknowledgement recorded by Srijan because Abhishek is unavailable; no specific code authorship or blanket dataset approval is inferred. |
| Sarwar Karim Akhand | Expanded synthetic contacts, inbound/outbound artifacts, provisional review split, generation/checking scripts and progress documentation, evidenced by main commits `4fad21f` and `f2bd392`. Personal acknowledgement pending. |
| Omkar Shankar Pawar | M2 contribution details and personal acknowledgement pending confirmation; no completed contribution is invented. |

See [WORKLOG.md](../../WORKLOG.md) for milestone-specific records. AI tools assisted authoring, coding, review and documentation; the team remains responsible for checking limitations and correcting errors. AI verdicts are not personal signatures.

## 11. Acknowledgement

This acknowledgement records participation and responsibility for the disclosed submission, including its outstanding work. It is not a claim that all data is human-approved, all requirements are complete, or benchmark results exist. Srijan requested his acknowledgement and confirmed that Abhishek authorized him to acknowledge on Abhishek's behalf. The proxy entry below is deliberately explicit and is not presented as Abhishek's personal signature. Roll numbers were not supplied and must be completed by the members.

| Name | Roll No. | Signature | Date |
|---|---|---|---|
| Srijan | Pending — member to supply | S. — entered at Srijan's request | 29 October 2026 |
| Abhishek Jha | Pending — member to supply | Srijan, on behalf of Abhishek Jha, with authorization (proxy acknowledgement) | 29 October 2026 |
| Sarwar Karim Akhand | Pending — member to supply | Pending personal acknowledgement | — |
| Omkar Shankar Pawar | Pending — member to supply | Pending personal acknowledgement | — |

**Administrative limitation:** a proxy or pending roll/signature entry may not satisfy the course's final acknowledgement check. The bot preview requested Name / Roll No. / Signature on the default branch; its exact validation rules and acceptance of proxy acknowledgement have not been verified. Obtain missing roll numbers, remaining personal acknowledgements and TA confirmation if a personal signature is required. This report must be merged into `main` before the deadline to be visible to the default-branch check.

## References

- [Official milestone requirements](https://bsc-iitm.github.io/dsai-lab-project/milestones.html#milestone-2).
- [M1 problem and literature report](../M1_problem_literature/report.md).
- [Dataset inventory, artifacts and preparation status](../M2_dataset/README.md).
- [Furniture source register](../M2_dataset/furniture_pilot/knowledge.md), [solar source register](../M2_dataset/solar_pilot/knowledge.md), [dental source register](../M2_dataset/dental_pilot/knowledge.md).
- [τ-Voice source crosswalk and claims boundary](../M2_dataset/TAU_VOICE_ALIGNMENT.md). No upstream compatibility or benchmark score is asserted.
