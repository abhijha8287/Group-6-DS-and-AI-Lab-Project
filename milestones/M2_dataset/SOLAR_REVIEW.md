# Independent solar-pilot review

**Verdict: request one targeted verification revision; the authored 12/10/5 content is suitable for continued pilot review, not runnable-task or human approval.** No incorrect current gold value was found against the declared mock contract. The remaining required issue is that the validator accepts gold that the declared tools cannot produce. Do not expand the pilot or require paid calls to resolve it.

## Scope and evidence

Independent AI review of all six `solar_pilot/` files: `README.md`, `knowledge.md`, `crm_seed.json`, `scenarios.json`, `outbound_cases.json`, and complete `validate.py`. Also read `TAU_VOICE_ALIGNMENT.md`, `FURNITURE_REVIEW.md`, and the M2 README. Applied the alignment document's research pinned to upstream **`122e2432b82d740e8f313f46f0a071729c404f39`**; did not redo upstream research or independently refetch business sources.

Ran the offline validator and independent, narrow in-memory mutation probes. No API/network calls, voice/model runs, real authentication, CRM writes, pilot edits or commits. Review date: 2026-10-29. Human source/policy/rights review remains pending.

## Required revision

### R1 — Check canonical tool effects independently of the gold being materialized

**Evidence:** `solar_pilot/validate.py:57–106` (`check_authorization`), `:109–146` (`gold_state`), and `:214–233` (gold/state preservation assertions); `solar_pilot/README.md:45–86` (canonical defaults and handoff registry).

The author has substantially resolved furniture R1 **in the specification**: new-contact defaults/history, atomic callback effects, handoff templates, caller-versus-seed provenance and ordered knowledge/question arrays are explicit. The present gold agrees with those declarations on manual inspection. However, the executable checks do not establish that agreement:

- Handoffs need nonempty fields, a pending status, a matching create-result envelope and known knowledge IDs. The validator does not enforce the two allowed reason codes, canonical prose/arrays, caller-confirmed values or seed-derived context.
- Callbacks check time, target, ID and status, but not the fixed `purpose:"requested_enquiry"` or full canonical record shape.
- New contacts check caller-supplied fields and consent, but not all tool-owned defaults or the fixed IN02 history.
- Whole-state preservation assertions follow construction by copying the seed and appending gold. They establish patch mechanics, not an independently derived expected tool result.

**Reproduction:** each row below changes only the named value in a fresh in-memory document; the **complete `validate()` still passes**, including its built-in regressions:

| Mutation | Declared contract it violates |
|---|---|
| IN06 handoff `reason_code = "automatic_refund_approved"` | Closed two-code handoff registry; no approval tool |
| IN06 handoff `qualification_context.caller_confirmed.written_cancellation_sent = true` | Caller explicitly supplies false; tool must copy confirmed values |
| IN05 callback `purpose = "marketing"` | Callback purpose is fixed to requested enquiry |
| IN02 new-contact `status = "installation_approved"` | `create_lead` defaults status to `new`; no installation approval capability |
| IN02 new-contact `history = ["Installation approved."]` | Exact tool-owned intake history is declared |

These are validator false negatives, **not evidence that the current authored labels contain those defects or that an actual agent performed unsafe actions**. The status/history probes also show why known IDs and successful envelopes alone are insufficient.

**Smallest fix:** add bounded contract-consistency assertions for these authored fixtures: compare each complete new contact, callback and handoff against an expectation derived from caller fields, seed fields, fixed defaults/templates and observed envelopes—not copied from `gold`. Assert the successful handoff envelope/ID and prerequisite update outcome as applicable. Retain one small regression loop that rejects the mutations above. This can be a few local assertions/template expectations; no production runner, generic policy engine or extra task is required. Keep the explicit “not agent evaluation” disclaimer.

**Acceptance:** baseline still passes; wrong-target/no-confirmation/failed-identity probes and the five contract probes all reject. Do not describe this as executing tools or grading a conversation.

## Applicable checklist assessment

### Task content, safety and domain diversity — satisfactory within pilot scope

Counts are exactly **12 contacts / 10 inbound tasks / 5 outbound labels**. IDs, reserved `.invalid` emails, synthetic-only contact targets and complete-seed reset are explicit. C02/C03 are meaningful same-name records, not duplicate IDs. Historical CB00/H00 are preserved.

The task set is not merely furniture with renamed products:

- IN01 tests mixed residential/shop subsidy uncertainty rather than unsupported entitlement.
- IN02 captures roof rights/access/type, shading, bill, locality/PIN and timeline without inferring design, savings or consent.
- IN03 combines tenant permission correction with an engineering/rights handoff and unreconfirmed seed context.
- IN06 preserves a cancellation-policy conflict instead of inventing a refund decision; its payment time is correctly 26 hours before the seed snapshot.
- IN07 refuses anti-islanding bypass instructions and invented battery sizing; declining contact capture correctly leaves no record.
- IN04, IN08, IN09 and IN10 cover identity ambiguity, atomic failure without unauthorized fallback, privileged caller injection and verified opt-out respectively.

IN05's 17:30 callback ends at 18:00, and calendar/save success are distinct prerequisites. Stop conditions are individually declared. Five no-op tasks require whole-state equality; successful updates are minimal and preserve history/consent. No actual task asks the agent to provide dangerous electrical instructions or certify a roof.

### Deterministic mocks, gold and reward — specified; verification gap R1

Manual comparison found IN02's defaults/history, IN03/IN06's fixed handoff fields and caller/seed provenance, IN05's atomic callback/status change, IN08's unchanged state and IN10's opt-out-only patch consistent with the README. Exact structured handoff strings are tool-owned fixtures, not arbitrary agent-generated summaries. This resolves the main **specification** ambiguity in furniture R1, without claiming a scored natural-language summary.

Each scenario explicitly uses project-local `CUSTOM_DB × COMMUNICATE × PROJECT_SAFETY`; required information is conjunctive and semantic, prohibitions/sandbox rules are safety gates, and diagnostics are empty. Reference tool fixtures are not presented as a required exact action sequence. Authorization, confirmation and availability prerequisites still constrain valid alternatives. End-state construction is not reference-tool execution: R1 remains the narrow missing check.

### Caller/environment/evaluator boundaries — satisfactory specification, not tested isolation

`README.md:33–41` and `scenarios.json:contract` explicitly partition caller instructions, harness-only fixture state, agent-visible schemas/knowledge/observed results, and evaluator-only labels. Gold/prohibitions/confirmation labels are not agent inputs. Caller utterances cannot establish trusted verification. Successful `verify_identity` binds subsequent existing-record writes to one ID; verified explicit opt-out is the separate authorization exception. New-contact creation requires a no-match lookup and confirmed-data token, not a fabricated verified identity.

This resolves furniture R2 at the intended fixture-specification level. The combined JSON remains unsafe to pass wholesale to an agent; no partitioning harness has run. Confirmation tokens are a future trusted-harness obligation, not proof that conversational confirmation was observed. Static mutation rejection cannot test token issuance or runtime leakage. Fixed handoff templates in the tool specification describe tool-owned behavior; they are not hidden caller instructions, though they make this exposed pilot unsuitable as an unseen test.

### Callback consent and outbound safety — satisfactory bounded labels

S4/S5 and the README explicitly say requested callbacks grant no outbound permission and eventual dispatch must pass **all** gates. C12/CB00 is correctly blocked by missing consent and allowlisting; recording a callback is not dialing. Opt-out preserves the historical grant while overriding future admission. IN05 does not modify consent or promise attendance/site visits.

The five outbound cases cover eligible, no-consent, opted-out, 18:00 and processed-event labels. Validator regressions separately cover retry/recency/allowlist, malformed/future consent, unknown IDs, combined failures, calling-hour and callback boundaries. Strictly less than 24 hours is blocked; exactly 24 hours is not blocked by recency alone. Cases reset independently and perform no queue or attempt side effects. They do not prove dispatch suppression, retry implementation or race-safe deduplication.

### Facts, assumptions and research boundary — appropriately separated, human checks outstanding

`knowledge.md` identifies two dated business sources, labels F1–F5 as bounded paraphrases hypothetically adopted by fictional SunGrid, marks S1–S10 as invented, and excludes the attempted 404 URL from evidence. Structural suitability, subsidy entitlement, backup design and price are not inferred from bill/PIN/roof access. Cancellation tension is retained as uncertainty. No affiliation, redistribution rights or government approval is claimed.

This review checked internal use/provenance labels, **not whether the live source pages actually support every paraphrase**. Especially F5's alleged contradiction remains subject to the stated human source check. Source facts must not be promoted to verified official eligibility or fictional-company contractual obligations. The existing disclaimers and restricted outcomes are appropriate for this pilot; no new upstream research or paid call is required.

The crosswalk correctly separates explicit task reward from full-duplex interaction, naturalness/fidelity and repeated-trial reliability, using the pinned alignment document. It does not claim upstream enum/schema compatibility. Furniture R3's missing crosswalk is addressed for solar; the earlier furniture review's research-pending statement is historical, not a reason to repeat that research.

### Release/limitations — honest and incomplete by design

All files remain `review_only` and pending human review. No held-out split, agent trace, audio, semantic judge, pass rate, pass^k, latency, cost or tool-reliability evidence is claimed. Fixed authentication/calendar/results, closed templates, absent queue/race tests and lack of separately authored retry/recency/allowlist cases are disclosed. Those are not reasons to demand full M2 or voice runs for this 12/10/5 review.

## Optional improvements, not release blockers for this pilot

- **O1 — More conversational discrimination on the next edit.** IN02 supplies every intake field cleanly; IN09 combines obvious administrator language, export, bulk edits and impossible approvals. Replacing—not adding—a case with one corrected/missing qualification field or a subtler injection after verification would isolate clarification or authorization behavior better. Current ten-case diversity is sufficient to review.
- **O2 — Make future mock implementation less interpretive.** The tool table identifies inputs/effects, and the handoff registry types its context. Before implementing a runner, turn implicit input types/optional-null rules and confirmation-token scope/lifecycle into small explicit schemas. No new dependency or runner is required now.
- **O3 — Preserve minimal source anchors at human review.** Dated clause/FAQ anchors would make F1–F5 easier to recheck, especially F5, without copying whole pages or reopening upstream rubric research.

## Tests performed

Baseline command:

```sh
python3 milestones/M2_dataset/solar_pilot/validate.py
```

Observed:

```text
PASS: 12 synthetic contacts; 10 distinct inbound fixtures; 5 outbound labels; boundary checks.
Fixture consistency only: no agent runs, benchmark scores, source-rights clearance or human approval.
```

Independent probes imported `validate.py` locally, deep-copied all three JSON documents per probe, temporarily replaced the module's `load` with an in-memory loader and called complete `validate()`. No fixtures were written:

| Probe | Result |
|---|---|
| IN03 update target C03 → C02 | Rejected, `AssertionError` |
| IN03 confirmation → `none` | Rejected, `AssertionError` |
| IN03 trusted verification set false, observed result changed to `verification_failed`, writes retained | Rejected, `AssertionError` |
| Five canonical-contract mutations listed in R1 | All accepted — verification gap |

The first three independently confirm improvement over furniture O2; they do not imply general authorization correctness. No actual tool contract was executed. **Changed path: only `milestones/M2_dataset/SOLAR_REVIEW.md`.** Resolve R1 with small offline checks, retain all limitation claims and obtain the already-planned human review before expansion.

## Follow-up — R1 resolved

**Current verdict: suitable as a review-only 12/10/5 authoring pilot; no required findings remain from this review.** This follow-up supersedes the original request-changes verdict above while preserving its findings and original test results. Human source/policy/rights approval remains pending; this is independent AI review, not runnable-system or benchmark certification.

### Actual revision inspected

Read the complete revised `solar_pilot/validate.py`, not just the author's summary. `canonical_changes` (`:109–187`) derives expected patches and complete appended records without reading gold:

- New contacts use caller fields, sequential seed-derived IDs and explicit canonical status, consent, attempts, timestamp and history defaults.
- Callbacks use caller time, availability/success envelopes, seed-derived ID, fixed purpose/status and the atomic contact-status patch.
- Handoffs use the closed templates, caller-confirmed fields, seed-derived unreconfirmed context, fixed knowledge/question arrays and successful tool envelopes. IN03 explicitly requires its matching successful permission update; IN06 checks the 26-hour interval and cancellation-stage facts.
- Failed IN08 updates and IN10 opt-out effects are explicitly represented.

`gold_state` now checks complete gold equality against those independent expectations before materialization (`:190–193`). Extra/missing record fields and altered canonical values therefore cannot pass merely because gold was copied into an expected state. The five retained canonical mutation regressions begin at `:361`; the original three authorization regressions remain. This is the bounded contract-consistency fix requested in R1, not a production tool runner.

### Verification repeated independently

Ran `python3 -B milestones/M2_dataset/solar_pilot/validate.py`:

```text
PASS: 12 synthetic contacts; 10 distinct inbound fixtures; 5 outbound labels; boundary checks.
PASS: 3 authorization and 5 canonical-contract mutation probes rejected.
Fixture consistency only: no agent runs, benchmark scores, source-rights clearance or human approval.
```

Separately imported the revised module with bytecode writing disabled, deep-copied all documents for each probe, replaced only its in-memory loader and called complete `validate()`. Repeated the exact five mutations originally accepted:

| Independent mutation | Revised result |
|---|---|
| IN06 reason → `automatic_refund_approved` | Rejected: canonical-contract equality assertion |
| IN06 gold written-cancellation flag → true | Rejected: canonical-contract equality assertion |
| IN05 callback purpose → `marketing` | Rejected: canonical-contract equality assertion |
| IN02 new-contact status → `installation_approved` | Rejected: canonical-contract equality assertion |
| IN02 history → `["Installation approved."]` | Rejected: canonical-contract equality assertion |

Also independently repeated wrong-record, missing-confirmation and failed-trusted-identity-with-writes probes: all rejected with `AssertionError`. Confirmed loaded JSON documents were unchanged afterward.

**Disposition:** R1 resolved. O1–O3 remain optional, not pilot blockers. Existing limitations concerning runtime isolation, actual confirmation, source verification, voice evidence and human approval remain unchanged. No pilot files were edited during this follow-up, no scope was expanded, and no API calls or commits were made. Only `milestones/M2_dataset/SOLAR_REVIEW.md` was changed by this follow-up.
