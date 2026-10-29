# Dental pilot — independent AI review

**Verdict: promising original review dataset; targeted validation changes required before treating its static authoring gate as dependable.** The current authored gold states inspected are consistent with their intended tasks. The required findings below are demonstrated validation blind spots, not evidence that an agent has violated policy or that the current gold is wrong. Human source/policy approval remains pending.

Scope reviewed: every file in `dental_pilot/` (`README.md`, `knowledge.md`, `crm_seed.json`, `scenarios.json`, `outbound_cases.json`, `validate.py`), plus `TAU_VOICE_ALIGNMENT.md` and the dataset overview. Review performed by an independent AI reviewer on 2026-10-29. No pilot edits, paid calls, production runner, agent trials or upstream web research were performed. Scope remains **12 contacts / 10 inbound tasks / 5 outbound gate fixtures**.

## Required findings

### R1 — Bind gold to the caller request and successful tool result

**Path:** `dental_pilot/validate.py:133–160`; `scenarios.json`, IN02, IN03, IN05 and IN07.

The validator checks some relations within gold/tool fixtures but misses their essential connections to the task and declared canonical effects:

- **IN03:** change both `gold.appointments[0].at` and `tool_results.check_appointment_availability.at` to `2026-11-05T16:00:00+05:30`, leaving the caller's explicitly confirmed request and required spoken date at 4 November. Validation accepts this contradictory task. Available does not mean requested or confirmed.
- **IN05:** change only `gold.handoffs[0].id` to `H99`; validation accepts it although `create_handoff` reports `H01`. Change only its reason to `clinical_question_out_of_scope`; validation also accepts it despite the insurance task and fixed reason-to-template contract. IN07 uses the same unchecked handoff path.
- **IN02:** remove `tool_results.create_lead.success`; validation still accepts a new contact despite the declared output schema and success-before-write rule.

This can silently turn malformed authored fixtures into a wrong-record artifact or misleading gold reward target. It is not a request for exhaustive schema validation or exact agent action sequences.

**Smallest fix:** assert appointment time/mode equal the caller's supplied time/mode as well as the available fixture; assert each handoff's ID, reason and canonical template agree with its successful result and the declared task template; require `success is True` for each successful write fixture. Keep canonical text tool-owned and semantic communication separate. Add a few in-memory rejection probes for these relations. No runtime implementation is needed for this fix.

### R2 — Validate authorization on the attempted failed write, not only persisted gold

**Path:** `dental_pilot/validate.py:117–132,161–164`; `scenarios.json`, IN08.

IN08 attempts an existing-contact callback write, so S1 still requires verified C09 identity even though the write fails atomically. Removing both `harness_context.identity` (setting it to null) and `tool_results.verify_identity` is accepted by `scenario_check`. The caller still supplies C09/email and the callback availability/failure fixtures remain. `existing_targets` is empty because gold is a no-op, and therefore the authorization requirement disappears.

This is a structural task-consistency gap: an atomic no-op does not prove the attempted operation was authorized. The ordinary IN03 unverified-identity probe does not exercise this branch.

**Smallest fix:** for IN08's declared callback attempt, require trusted identity and its matching observable verification result independently of gold mutations, bound to the caller-provided contact/email. Add the missing-identity-plus-missing-verification rejection probe. Preserve the expected full-state no-op and failure communication. No synthetic verification result should be substituted for actual conversational/tool evidence in a future runner.

## What is already sound

### Provenance, originality and clinical/privacy boundaries

- F1–F5 are narrow attributed paraphrases with primary URLs, access date and explicit limits. S1–S10, availability, identities and consent evidence are separately identified as invented sandbox choices. Fictional adoption is not represented as the source clinic's actual operation. Source truth/rights were **not independently re-fetched or legally cleared in this review**; human source review remains necessary, as already disclosed.
- No copied benchmark dialogue is apparent in the reviewed artifacts. Originality here means distinct authored task content; it is not an exhaustive external plagiarism determination.
- No real patients, telephone destinations, clinical histories, insurance identifiers, payment data or live integrations appear. Contacts use synthetic names and reserved `.invalid` emails. Clinical questions are redirected without diagnosis, medication, symptom collection, treatment recommendation or invented emergency protocol. These administrative tasks do not establish clinical safety or emergency readiness.
- Policy answers in IN06 preserve online-payment scope, exactly-24-hour versus below-24-hour distinctions, and the distinction between information and executing cancellation/refund. IN05 does not infer insurance participation from unknown coverage.

### Meaningful pilot coverage

The ten tasks are not just paraphrased booking variants: service FAQ; new qualified enquiry; same-name identity-sensitive appointment request; ambiguous identity refusal; insurance handoff; cancellation-policy boundaries; clinical-boundary handoff; atomic callback failure; caller prompt injection; and opt-out with consent history retained. Dental-specific policy and clinical-administrative boundaries give meaningful differentiation from a generic sales skin.

The five outbound cases separately cover eligible, missing consent, opted-out, closing-hour boundary and duplicate event. Allowlist/recent-attempt/retry/callback-boundary checks are validator probes, **not additional authored scenarios**. The already-disclosed absence of a successful callback task and held-out split does not block this bounded review scope.

### Gold, tools, identity and confirmation

- Whole-seed reset, fixed clock, full-state preservation, deterministic IDs, atomic status-plus-append writes and fixed handoff/history templates are explicit. Current IN03 correctly changes C03 only and appends AP01; current IN05/IN07 save administrative review requests; IN08 preserves all state; IN10 changes only C01 opt-out while retaining historical consent.
- An appointment **request** is distinct from confirmed clinician attendance or delivered care. Callbacks are a separate collection, and a saved inbound callback is not permission to dispatch: S5 consent/allowlist gates still apply. Existing CB00 without outbound consent is deliberately coherent with that distinction.
- Trusted harness authorization is not caller speech. Observable `verify_identity` results are required by the written contract before existing-record writes. New-enquiry creation has a separately bounded empty-email-lookup exception and grants neither identity verification nor voice consent.
- Explicit confirmation covers writes and requested time/mode, with the deliberate verified opt-out exception. Hidden caller confirmation labels are authoring fixtures, not proof that a live agent obtained confirmation.
- Exact-state equality applies to canonical tool-owned fields; spoken required facts are semantic. This avoids penalizing harmless utterance paraphrases. Fixed tool templates are not a scored generated handoff summary, which the README acknowledges.

### Actual rubric alignment and visibility

The crosswalk correctly distinguishes upstream DB end-state and semantic COMMUNICATE principles from local `LOCAL_DB`, `LOCAL_COMMUNICATE` and `PROJECT_SAFETY` labels. All three local components explicitly gate each task; safe alternative tool paths are allowed rather than requiring a reference sequence. Stop conditions, failure/refusal/no-op outcomes and unchanged-state invariants are authored.

Agent visibility is explicitly restricted to knowledge, public schemas, conversation and observed results. Caller-only goals, gold, prohibitions, reward criteria and harness authorization are hidden. Co-location in a review file is not itself a leak; **passing that whole file to an agent would be**. The README correctly says no safe runtime loader exists yet. A future implementation must enforce that boundary and actual confirmation/verification rather than trusting hidden expected labels.

No agent success, pass^k, audio interaction, latency/selectivity, naturalness/fidelity, clinical validation or human approval is inferred from these artifacts. The explicit upstream pin and limitations are appropriately cautious; this is conceptual authoring alignment, not upstream format compatibility or benchmark certification.

## Verification performed

Ran from the repository environment:

```sh
python3 milestones/M2_dataset/dental_pilot/validate.py
```

Result: **PASS**, 12 contacts / 10 inbound / 5 outbound, including its built-in negative probes. This proves only the assertions implemented by the script.

Independently imported the validator and called `scenario_check` with deep-copied seed/tasks and knowledge IDs parsed from `knowledge.md`. All mutations were in memory; no fixtures were rewritten:

| Probe | Observed result | Interpretation |
|---|---|---|
| IN03 gold update targets C02 instead of verified C03 | Rejected | Basic wrong-record guard works |
| IN03 confirmation label changed to `none` | Rejected | Authored missing-confirmation guard works |
| IN03 trusted identity `verified=false` | Rejected | Basic unverified-identity guard works |
| IN03 appointment/availability moved to 5 Nov; caller still requests 4 Nov | Accepted | R1 |
| IN05 handoff ID changed to H99 | Accepted | R1 |
| IN05 handoff reason changed to clinical question | Accepted | R1 |
| IN02 successful-create flag omitted | Accepted | R1 |
| IN08 identity removed and verification result removed | Accepted | R2 |
| IN08 identity, supplied identifiers and verification all consistently changed to C02 | Accepted | Not itself a defect: this rewrites the authorized task persona consistently; no attempted-call target exists to demonstrate a wrong-target violation |

The last probe is included to distinguish a real authorization bypass from a legitimate internally consistent synthetic task variant. Static validation is **never agent success**, and these probes are not agent trajectories or behavioral safety tests.

## Optional follow-ups, not release blockers for this scope

- When separately authoring a later held-out set, include a successful callback request whose eventual dispatch is blocked, an observed failed-identity response, and a caller correction/confirmation withdrawal. Do not expand to 40 tasks merely to satisfy this review.
- Before any agent execution, implement a visibility-safe loader and deterministic mock replay with full observed-state comparison and independent conversation safety/confirmation checks. That deferred implementation is not required to keep this artifact a clearly labelled review-only dataset.
- Record human policy/source review and resolution of R1/R2; retain original review-only status for these already exposed tasks rather than retroactively calling them unseen test evidence.

**Changed path:** `milestones/M2_dataset/DENTAL_REVIEW.md` only. Pilot content was not edited.

## Follow-up — 2026-10-29: R1/R2 resolution

**Updated verdict: ACCEPT as a review-only pilot (12 contacts / 10 inbound / 5 outbound). Required findings outstanding: none.** This follow-up supersedes the initial change-request verdict, not its preserved evidence or limitations. Human source/policy approval remains pending; acceptance is independent AI artifact review, not human approval or agent/voice performance evidence.

Inspected the revised `dental_pilot/validate.py` in full rather than relying on the author's summary. Re-ran its static validation and independently repeated every original malformed probe on deep-copied in-memory fixtures, importing with `python3 -B` to avoid writing a bytecode cache. No pilot files were edited.

### Finding status

- **R1 — Addressed.** Present successful-write fixtures require strict `success is True`. Appointment time and mode must match caller-provided fields as well as availability. `canonical_handoff` independently defines the two declared tool-owned templates; complete gold equality checks their IDs, reasons, administrative text, authorization, qualification provenance, knowledge references and result envelopes. This is canonical fixture consistency, not an exact agent-trajectory or utterance-text requirement.
- **R2 — Addressed.** IN08 explicitly requires trusted identity even with no persisted gold changes. The shared checks then require successful observable verification bound to the same seed record and caller-supplied ID/email. The callback availability is also bound to the supplied time and valid callback slot; its result must remain a failure and gold unchanged.

### Verification results

`python3 milestones/M2_dataset/dental_pilot/validate.py` **passed**. Inspected the built-in probe construction: **17 rejection probes** are executed (5 appointment/identity/confirmation, 6 handoff, 1 lead-success, 1 failed-attempt identity and 4 other missing-success probes); none escaped rejection.

Independent rerun of the original review probes:

| Probe | Revised result |
|---|---|
| IN03 wrong-record gold update to C02 | Rejected |
| IN03 no confirmation | Rejected |
| IN03 unverified trusted identity | Rejected |
| IN03 appointment and availability shifted to 5 Nov, caller still requests 4 Nov | Rejected |
| IN05 handoff ID changed to H99 | Rejected |
| IN05 handoff reason changed to clinical question | Rejected |
| IN02 successful-create flag omitted | Rejected |
| IN08 trusted identity and verification result both removed | Rejected |

The consistently rewritten authorized IN08 persona control remained accepted, as expected; that was never a required defect. All eight malformed original probes were rejected by assertions, and the seed remained unchanged.

No new required findings arose within this bounded follow-up. Earlier optional future-work suggestions remain optional for review-only acceptance. Static checks establish authored-fixture consistency only: no runtime implementation, paid calls, expanded dataset or voice runs are required by this verdict, and none were performed. Only this report was changed during the follow-up.

## Additional adversarial review: operation scope and appointment defaults

A later independent review found three reproducible validator gaps despite the current authored gold remaining coherent:

- **R3:** IN05 accepted an extra same-contact `opted_out=true` patch under handoff-only confirmation; IN07 shared this gap.
- **R4:** IN03 accepted appointment `purpose=root_canal_treatment` and `status=pending`, contrary to the declared consultation/request defaults.
- **R5:** IN02 accepted an empty lookup result for an email different from the caller's supplied email.

**Repairs:** `scenario_check` now restricts nonempty gold collections to each task's authorized operation, compares the complete appointment and result envelope against canonical defaults, and binds new-contact lookup to the supplied email and actual seed matches. These validate expected fixture effects, not an agent's tool sequence. No scenario or business policy was changed.

The dental validator now includes **32 rejection probes**: the previous 17 plus four appointment-field/result controls, four handoff-side-effect controls, two lookup controls and five unauthorized-callback controls. `python3 -B milestones/M2_dataset/dental_pilot/validate.py` passes with all probes rejected. Furniture and solar validators also pass. An independent read-only reviewer then confirmed all ten baseline tasks still pass and rejected 72 additional in-memory mutations, including the reported defects, IN07 equivalents, coordinated appointment-status corruption and unauthorized side effects. No required issue remained within the repair scope. These results remain static fixture checks, not runtime safety or completed M2 evidence.
