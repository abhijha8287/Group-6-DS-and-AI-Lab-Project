# Independent furniture-pilot review

**Verdict: request targeted revisions before treating these as runnable agent tasks.** The review-only draft is useful and appropriately bounded, but the expected-state and trusted-identity contracts remain underspecified. This is an independent AI review, not human approval. The separate upstream/rubric research and subsequent rubric-specific review remain pending.

## Scope and evidence

Read all six files in `furniture_pilot/`, `M2_dataset/README.md`, and M1 `report.md` (especially §§2, 5, 6 and 10). Inspected the complete validator and ran it locally. No external-source research, paid model calls, agent conversations, voice calls or external writes were performed. No pilot files were modified.

The intended deliverable is **12 contacts / 10 inbound scenarios / 5 outbound cases for one fictional business**, not completed M2. The files meet those counts. M1's three businesses, approximately 120 inbound scenarios, larger CRM seeds, approximately 30 outbound cases, held-out split and architecture comparison are later scope. Their absence is **not a blocker for this pilot**. Neither a production evaluator nor paid calls are required to resolve this review.

## Required revisions

### R1 — Separate deterministic tool-owned fields from acceptable generated content

**Evidence:** `furniture_pilot/scenarios.json`, `contract.gold`, `contract.scoring`, IN02 and IN06; `furniture_pilot/validate.py:gold_state`.

The scoring contract requires canonical whole-state equality, but several gold strings are neither caller-provided facts nor declared deterministic tool outputs:

- IN02's tool fixture returns only `success` and `id`, while gold additionally requires the exact history string `Confirmed inbound desk enquiry.` A correct agent/tool could preserve the same facts with a different history entry and fail the stated equality rule.
- IN06 requires exact `enquiry`, `unresolved_questions`, `qualification_context.source`, the order/content of `knowledge_ids`, and a nested `tool_outcome`, even though `create_handoff` returns only `success` and `id`. The contract says reason codes are exact-match rather than generated summaries, but does not say how the other prose is produced or normalized.
- IN05 requires a successful `schedule_callback` to change C01's status as well as append CB01. Its fixture does not specify whether these are one atomic tool side effect or separate operations. IN08 explicitly declares atomic failure, making the successful-path omission consequential for implementation.

**Why it matters:** equivalent, policy-compliant conversations can fail arbitrary string equality, or future tool implementations can silently disagree about side effects. Materializing the authored gold does not establish that those outcomes follow from the authored tool responses.

**Smallest fix:** document a short mock-tool contract defining deterministic defaults, IDs, history/handoff rendering and callback side effects. Alternatively, identify a small set of generated narrative fields to judge semantically while retaining exact checks on record identity, consent, reason codes and factual values. Do not require a new evaluator implementation now. Keep gold and expected tool behavior consistent with the chosen approach.

### R2 — Specify how trusted identity verification reaches the agent/tools

**Evidence:** `furniture_pilot/knowledge.md:S1`; `furniture_pilot/scenarios.json:contract.caller_visibility`, IN03, IN05, IN06, IN08 and IN10.

S1 correctly states that a stated email is not verification. However, `identity_verified: true` currently lives inside `caller`, the section intended for the simulator, and the verified scenarios' `tool_results` do not include a verification result. The caller goals say synthetic verification succeeds without defining a trusted agent-visible signal or environment-side authorization state.

**Why it matters:** a future runner can either withhold all verification evidence from the agent, or accidentally treat the simulated caller saying “I verified” as authorization. Both would undermine the distinction tested by IN03/IN04 and the opt-out exception in IN10.

**Smallest fix:** explicitly designate this boolean as trusted harness/environment state, not caller speech, and describe how mock writes check it and how the agent learns the result. A simple fixture declaration is sufficient; real authentication is outside this pilot. Preserve IN04's prohibition on disclosure or arbitrary record selection.

### R3 — Complete the promised rubric-specific check after upstream research

**Evidence:** `furniture_pilot/README.md:Remaining design limits` links τ-Voice and names only the pattern “caller goal, tools, expected outcome”; `scenarios.json:contract.scoring` supplies a local rule, not an upstream rubric mapping.

There is currently no evidence in the pilot that its tasks have been checked against the actual τ-Voice task/rubric requirements. This review does **not** independently establish those requirements and does not repeat the separate research agent's work. The existing “not compatible” disclaimer is appropriate; it is not a substitute for the requested quality check.

**Smallest fix:** once that research is available, add a short source/version-specific crosswalk: applicable dimensions, evidence in this pilot, and deliberately deferred dimensions. Amend tasks only where that pass identifies a concrete gap. Do not claim τ-Voice compliance, adopt guessed rubric fields, or expand to a production runner merely to satisfy this item.

## Optional improvements / explicit design decisions

### O1 — Clarify requested callbacks versus outbound consent

**Evidence:** `knowledge.md:S5`, `crm_seed.json:C12/CB00`, and IN08's C09 callback request.

S5 requires recorded voice consent for outbound enquiry follow-up. C12 has a requested callback but no consent and is also not allowlisted; IN08 likewise permits a callback request for non-consented C09 before the tool fails. Recording a request is not itself a prohibited call, so these are not demonstrated safety violations. However, clarify whether eventual requested callbacks use the same gate, a separate purpose-specific permission, or stay blocked until permission and allowlist requirements are met. Do not let a future implementation infer that callback scheduling grants broad marketing consent.

### O2 — Strengthen a few cheap label-consistency assertions, without overselling them

**Evidence:** `validate.py:validate` checks caller identity against the seed but never relates an ordinary gold update target to that verified identity or checks caller confirmation against the write. It also checks knowledge references using substring membership in the Markdown, rather than parsing defined IDs.

In-memory mutation probes, with no file edits, showed the complete validator still reports PASS when:

1. IN03's gold update target is changed from C03 to C02;
2. IN03's confirmation is changed to `none`;
3. IN03's `identity_verified` is changed to false.

A control mutation adding nonexistent F999 was rejected. These results show the existing checks have value, but do not certify that every gold follows S1/S2. Consider adding narrow assertions for the authored cases or documenting this limitation alongside the current checks. Do not build a general policy engine for a review fixture.

### O3 — Diversify within the pilot if revising tasks anyway

**Evidence:** IN02 supplies every qualification field with straightforward confirmation; IN03 supplies a clean identifier/email match; IN05 supplies a valid slot; IN09 combines an overt administrator claim, unsupported discount and bulk edit, so several independent restrictions can defeat it.

The ten cases already span meaningful distinct workflows: anonymous FAQ, lead creation, same-name update, ambiguous identity, callback, return exception/handoff, unavailable grounding, failed write, injection and opt-out. They are not ten paraphrases of one happy path. Still, consider replacing rather than adding a case to cover missing/changed qualification information, a corrected time, or a subtle injection after verified identity. That would better isolate conversational and authorization failures without increasing scope. Missing clinical/solar tasks and voice-specific robustness are not furniture-pilot defects.

### O4 — Keep provenance review bounded and reproducible

**Evidence:** `knowledge.md` names R1/R2, an access date, bounded F1–F5 paraphrases, explicit hypothetical adoption of F1–F4, and an inference label for F5. The README separates fictional UrbanNest from IKEA, disclaims affiliation and task/code copying, and says no third-party dataset is redistributed.

These are good provenance boundaries; no plagiarism finding is established by this local review. The pages were **not externally verified here**, so the source claims remain draft assertions rather than checked facts. Optional short passage anchors or minimal dated evidence would make a second reviewer able to verify the paraphrases despite page changes. Do not copy whole retailer pages, imply that citation grants redistribution rights, or convert F5 into a quoted source policy. F5 currently has no direct task coverage; this is acceptable at 10 scenarios, but should not be called tested cancellation-success handling.

## Verification and interpretation

Command run from the project:

```sh
python3 milestones/M2_dataset/furniture_pilot/validate.py
```

Observed output:

```text
PASS: 12 synthetic contacts, 10 inbound fixtures, 5 outbound labels; boundary checks passed.
Not an agent evaluation, source-rights clearance, or human content review.
```

Inspected boundary assertions cover call-start hours, recent-attempt and retry blocks, allowlist exclusion and the strict 24-hour cutoff. The five authored outbound cases independently cover eligible, no-consent, opted-out, 18:00 and duplicate-event conditions. The README honestly distinguishes extra validator checks from authored scenario coverage. Each case resets the seed; OUT05 tests an already-processed event, **not** a sequential duplicate-submission race or actual queue behavior.

**Synthetic fixture validation is not agent success.** No observed evidence exists here for M1 O1–O11 rates, pass^k, factual accuracy, handoff completeness, latency, cost, trigger execution, call prevention in a running system, or architecture superiority. The current documentation appropriately avoids those claims. Human review remains pending.

## Parent handoff

Resolve R1's deterministic-versus-semantic gold contract and R2's trusted fixture visibility; complete R3 after the separate rubric research. Keep the 12/10/5 review-only scope, source-verification caveats and no-human-approval language. The optional items do not justify expanding to full M2 or requiring a production evaluator.

---

## Independent post-fix follow-up

**Current verdict: accept as a review-only authoring pilot. No concrete required issues remain from this re-review.** This supersedes the initial request-changes verdict for the current files; the original findings above are retained as historical evidence. Acceptance is not runtime/voice certification or human approval.

Re-read every current file in `furniture_pilot/` (including `MOCK_TOOLS.md`) and `TAU_VOICE_ALIGNMENT.md`. Inspected the revised code, ran the validator, and independently repeated negative controls in memory. Only this review file was edited. No paid runs, model conversations, real authentication, dispatch or voice evaluation were performed.

### Required-finding disposition

| Finding | Disposition | Current evidence |
|---|---|---|
| R1: tool-owned defaults/rendering and atomic effects | **Addressed** | `MOCK_TOOLS.md:33–43` defines ID allocation, unchanged-state invariants, deterministic IN02 history and IN06 handoff rendering, seed-derived context and actual returned tool outcome. Callback append plus contact-status change is explicitly atomic; failed IN08 changes neither. Natural acknowledgements remain semantic rather than prescribed utterances. |
| R2: trusted verification and agent-visible results | **Addressed** | `MOCK_TOOLS.md:5–13`, `knowledge.md:S1`, and `scenarios.json:contract.caller_visibility/trusted_state/tool_results` separate simulator, agent and harness views. Sessions start unverified; evaluator `environment` is an expected checkpoint, not an initial grant. `verify_identity` returns a trusted result to the agent; existing-contact writes require that bound contact and observed scoped confirmation. IN03/05/06/08/10 now include explicit verification results; caller objects no longer contain the authorization boolean. Real authentication and observation of dialogue remain deferred, not claimed implemented. |
| R3: applicable/deferred upstream rubric crosswalk | **Addressed for authoring scope** | `TAU_VOICE_ALIGNMENT.md:5–21` pins upstream `122e2432b82d740e8f313f46f0a071729c404f39` and distinguishes explicit reward components from diagnostic reference paths. `furniture_pilot/README.md:45–60` applies DB × COMMUNICATE, separates local safety gates from upstream assertion evaluators, and labels outbound `PROJECT_GATE` as custom. Each inbound task explicitly declares its basis and stop condition. Actual dialogue scoring, voice interaction/Experience evidence, repeated trials and compatible runtime execution are explicitly deferred. |

The rubric disposition checks the supplied pinned research artifact and its local application; it does not claim a fresh independent upstream checkout, source-rights clearance or benchmark compatibility. The alignment document's earlier gap list still supplies expansion/runtime cautions; it does not require full M2, voice evidence or new scenarios before accepting this bounded authoring pilot.

### Does validation actually compare canonical effects?

**Yes, for the declared fixture effects.** `validate.py:116–165` reconstructs effects from caller final fields, seed and declared tool results, without reading authored gold. It derives new IDs/defaults, history, callback status plus row, and the fixed handoff with seed context. `check_scenario` separately materializes authored gold using `gold_state`, then compares the entire resulting states at `validate.py:190`. This is more than applying gold and checking its shape. Authorization checks run on both materializations; trusted verification consistency is checked before comparison.

The distinction remains important: this is a small reference reconstruction of authored outcomes, **not** a tool-call interpreter or a record of observed agent actions. It cannot establish that runtime identity, confirmation, ordering, retry behavior, communication or prohibited-action enforcement works. The revised README and mock-tool contract state that limit clearly.

Command rerun:

```sh
python3 milestones/M2_dataset/furniture_pilot/validate.py
```

Observed:

```text
PASS: 12 synthetic contacts, 10 inbound fixtures, 5 outbound labels; canonical effects, 3 IN03 negative controls, alternate read order and boundary checks passed.
Not an agent evaluation, source-rights clearance, or human content review.
```

Independently reran the existing controls through `check_scenario`, plus gold/effect mismatch probes; every probe below was rejected without modifying pilot files:

| In-memory mutation | Observed rejection |
|---|---|
| IN03 gold targets C02 instead of C03 | `Wrong write target` |
| IN03 caller confirmation becomes `none` | `Missing scoped explicit confirmation/request` |
| IN03 trusted checkpoint and verification tool result both become unverified | `Existing writes require trusted identity` |
| IN02 gold history differs from the tool-rendered template | `Gold disagrees with canonical tool effects` |
| IN05 gold retains callback row but omits the atomic status update | `Gold disagrees with canonical tool effects` |
| IN06 gold handoff budget differs from seed context | `Gold disagrees with canonical tool effects` |
| IN03 write result becomes an atomic failure but gold still expects the update | `Gold disagrees with canonical tool effects` |
| IN05 availability becomes false but callback success/gold remain | Assertion failure |

Positive checks also confirmed IN08's failed callback retains the entire seed and reversed IN07 stock/delivery read order remains accepted. Thus the controls demonstrate both canonical mismatch detection and a permitted alternative path; they are not agent-success trials.

### Other previous observations and remaining boundaries

- O1 is addressed: `knowledge.md:S5`, `MOCK_TOOLS.md:Callback dispatch remains blocked separately`, and `validate.py:275–277` require C09/C12 to remain blocked for absent consent and allowlist membership. Recording a callback request does not grant dispatch authority.
- O2's requested narrow checks are present: authorization/target/confirmation consistency, parsed knowledge IDs and retained IN03 negative controls. Their passing results do not imply comprehensive policy enforcement.
- O3 remains optional; IN02 now adds timeline clarification without increasing the 12/10/5 scope. No additional coverage is required for this acceptance.
- O4's source-verification/rights caveats remain. This review does not certify retailer facts, human review, licensing clearance, held-out status, generated-summary quality, legal compliance, runtime safety or any M1 performance objective.

**Parent handoff: no required unresolved fixes.** Accept the current artifact as an original review-only authoring pilot with synthetic fixtures and explicitly deferred runtime/voice evidence. Human approval remains pending.
