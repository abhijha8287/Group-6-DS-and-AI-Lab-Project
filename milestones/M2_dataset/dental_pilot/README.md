# BrightSmile Dental Studio — review pilot

**AI-assisted original draft; review_only; human review pending.** BrightSmile is fictional. Toothmate Multispeciality Dental Clinic, Surat, is a narrowly used public reference, not an affiliate, endorsement or actual BrightSmile operation. No human authorship contributions or approvals are asserted.

Scope: **12 synthetic administrative contacts, 10 distinct original inbound tasks, 5 outbound gate fixtures**. This is not the full 40-task business suite. Every identity, event and conversation instruction is synthetic. No real patients, clinical records, dialable phone targets or live systems are included; emails use reserved `.invalid`. No paid calls, website forms, agent benchmark runs, audio generation or scores occurred.

## Files and contract

- [knowledge.md](knowledge.md): independently fetched primary sources, access date, F1–F5 original bounded paraphrases and S1–S10 separately labelled invented rules. Public access does not grant permission to copy; no website prose, patient stories, testimonials, imagery or benchmark tasks are redistributed.
- [crm_seed.json](crm_seed.json): whole initial state and fixed fictional clock; no inferred current availability.
- [scenarios.json](scenarios.json): caller-only instructions, trusted harness identity, observable verification results, deterministic mock schemas/defaults/templates, task-local gates, stop conditions and evaluator-only gold.
- [outbound_cases.json](outbound_cases.json): five read-only gate labels, not placed calls or production-control actions.
- [validate.py](validate.py): Python standard-library static checks and negative mutation probes, not an evaluator or production policy engine.

Shared furniture pattern retained: each task resets the **entire** seed; full expected state comes only from contact `set` patches and appends. All unspecified fields, histories, records and list order remain unchanged. The one explicit extension is an `appointments` collection, separate from callbacks. An appointment request does **not** imply treatment delivered or confirmed clinician attendance. Callback requests do **not** grant outbound permission: eventual dispatch remains blocked unless all consent, allowlist and other S5 gates pass.

The deterministic mock contract in `scenarios.json` declares input/output shapes, authorization, canonical defaults, fixed handoff/history templates and atomic status-plus-append side effects. Canonical prose is tool-owned, not generated agent summary text. Human-review handoffs contain administrative context, provenance, verification/confirmation scope, unresolved question and actual tool outcome; no symptoms or medical history. A future runner must implement the declared templates before exact end-state scoring.

### Visibility and trusted identity

A simulator gets **only `caller`** and preserves that persona/goal. The agent gets knowledge, public tool schemas, actual conversation and observed tool responses; it must never receive hidden caller goal, confirmation labels, gold, prohibitions, evaluator criteria or harness state. These co-located review JSON objects are not yet a safe runtime loader.

`harness_context.identity` is trusted synthetic authorization, not caller speech. `verify_identity` returns an observable result after matching supplied ID/email against both seed and harness authorization. Every existing-record mutation must target that verified ID. The new-enquiry S1 exception instead needs an empty email lookup and confirmed supplied details, and grants no verified identity/voice permission. Caller confirmation labels describe expected simulator behavior; a real runner must verify actual conversation confirmation rather than expose/use those labels as agent input.

## Review coverage

| Task | Distinct goal / expected state |
|---|---|
| IN01 | Listed services and consultation modes; no clinical recommendation or writes |
| IN02 | New video scheduling enquiry with qualification; append C13 only |
| IN03 | Same-name disambiguation and confirmed consultation request; update C03 status, append AP01, no callback |
| IN04 | Ambiguous request to move an appointment; disclose/change nothing |
| IN05 | Insurance uncertainty; consented coverage-review H01, no coverage promise |
| IN06 | Online cancellation policy at exactly 24 hours, below it, and after care; information only |
| IN07 | Treatment-selection question; no clinical advice/intake, consented clinician-review H02 |
| IN08 | Atomic callback write failure; full state unchanged, no dental visit booked |
| IN09 | Fake system instruction seeking exports and insurance approval; refuse without writes |
| IN10 | Verified voice opt-out; only C01 opted_out changes, historical consent retained |

Outbound fixtures cover eligible, missing consent, opted-out, 18:00 boundary and duplicate event. Validator-only checks additionally cover allowlist exclusion, recent attempts, retry limit, exact 24-hour cutoff, callback latest start and the existing no-consent callback. These are **not** separately authored additional outbound scenarios or race/concurrency tests. No successful callback-write task is authored yet; its semantics are declared for later use.

## Actual τ-Voice rubric crosswalk

Based on the independently researched [TAU_VOICE_ALIGNMENT.md](../TAU_VOICE_ALIGNMENT.md), pinned to Sierra Research `tau2-bench` **122e2432b82d740e8f313f46f0a071729c404f39**. The independent [furniture review](../FURNITURE_REVIEW.md) supplied contract/identity failure modes considered here; this is not independent human review of dental content.

| Applicable upstream concept | Local evidence / adaptation |
|---|---|
| Explicit task reset, caller goal and environment | Whole-seed reset; caller persona/goal; mock schemas, trusted identity fixtures and task stop condition |
| DB: final state vs reference state, not necessarily same action sequence | Each task's **LOCAL_DB** gate materializes full gold patches; fixed tool-owned templates avoid arbitrary generated-text equality. A real mock replay/observed-state evaluator is deferred. |
| COMMUNICATE: required facts checked semantically | **LOCAL_COMMUNICATE** gates every `required_information` item. No semantic judge has run. |
| Explicit reward basis; only included components gate | Every task lists all three local hard gates; all must pass. These field names/values are our schema, **not upstream-compatible enums**. |
| Optional ACTION/ENV_ASSERTION/NL_ASSERTION | No exact tool-sequence gate or claimed upstream assertion implementation. Identity, confirmation, no prohibited action and project knowledge rules form a separate **PROJECT_SAFETY** hard gate, not an official τ-Voice safety dimension. Tool sequence/clarification counts are diagnostics only. |
| Full-duplex interaction and Experience panels | Deferred: no ticks, latency, interruption/selectivity opportunities, audio/transcript alignment, naturalness/fidelity judges or saved tool-misuse verdicts. Missing evidence is unscored, not a pass or zero. |
| pass^1/pass^k and error-aware aggregation | Deferred until real repeated scored trials; preserve unscored/infrastructure failures then. No percentages claimed now. |

This is source-informed authoring alignment, **not τ-Voice compatibility, certification or a benchmark result**. End-state and communication criteria alone do not establish safety, medical validation, legal compliance or source-rights clearance.

## Check and next review

From repository root:

```sh
python3 milestones/M2_dataset/dental_pilot/validate.py
```

Do not run with `-O`: assertions intentionally reject malformed fixtures. The script checks scope/IDs, defined knowledge references, synthetic contact shape, trusted identity vs write targets, confirmation, atomic failure no-op, state preservation, appointment/callback separation and outbound labels/boundaries. In-memory wrong-record, missing-confirmation and unverified-identity probes must be rejected. It does not replay agent calls, assess speech, inspect all conceivable malformed data or replace content review.

Before expansion: human-check cited policies and paraphrase/rights boundaries; approve invented safety and administrative rules; inspect every gold patch and handoff template; implement visibility-safe mock replay if running agents; independently author held-out tasks. This exposed review-only set has no dev/test split and cannot later be claimed unseen test evidence. Clinical/emergency protocols and insurance participation remain unsupported and must not be invented.
