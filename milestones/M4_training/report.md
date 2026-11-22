# Milestone 4: Development and Experimental Preparation

**Project:** Voice Agents for Small-Business Enquiries and Lead Follow-up: Single-Agent vs Multi-Agent  
**Group 6:** Srijan · Abhishek Jha · Sarwar Karim Akhand · Omkar Shankar Pawar  
**Milestone date:** 19 November 2026 (first version, Srijan) · **updated 22 November 2026** (Steps 9–14, Abhishek Jha)  
**Status:** Text development is complete through the M4 step plan's Step 14: a corrected single agent, an implemented multi-agent candidate, and three paid development comparisons (180 episodes). Voice (Steps 15–17), the protected held-out evaluation and the final architecture decision (Steps 18–19) are **not done**. This is a development report, not an architecture-selection report.

## 1. Summary

M4 extends the M3 text-mode agent and sandbox; no model is trained. The work has two parts.

**Reliability and preparation (Srijan, Steps 1–8 and 11; 19 November).** Judge-output validation, explicit evaluation errors, preserved failed attempts, paid-request accounting with a cost ledger, short and large policy packs, 16 frozen development scenarios, a measurement protocol and prospective comparison settings, and two four-request paid diagnostics.

**Agent development and comparisons (Abhishek Jha, Steps 9–10 and 12–14; 22 November).** A corrected single agent (prompt v2 plus deterministic guards against invented identifiers and false "done" claims), a multi-agent candidate (coordinator plus knowledge, qualification and CRM-planner specialists), and 180 paid development episodes on `gpt-4o-mini` / `gpt-4.1-mini` for about **$0.90**.

Main development findings (exposed development data, one judge model, three repetitions of ten scenarios; not significance tests):

| Comparison | Result |
|---|---|
| Model (Step 12) | gpt-4o-mini and gpt-4.1-mini tie on full passes, **17/30 each**; gpt-4o-mini's agent cost is about a third. gpt-4o-mini selected by a rule fixed before the results |
| Architecture (Step 13) | Single agent 17/30 full passes, multi-agent 16/29. Multi-agent used **+55% model calls, +61% median episode time, +26% agent cost**, and had **lower judged safety (19/29 vs 27/30) and more false-success flags (10 vs 3)** |
| Prompt (Step 14) | Archived M3 prompt 18/30 vs v2 17/30, but M3 made **5 vs 2** blocked unsafe write attempts |
| Retrieval (Step 14) | BM25 top-5 made every CRM write exact (**15/15 vs 11/15**) but had more false-success flags (6 vs 3) |
| Document size (Step 14) | Large policy pack: no accuracy loss (18/30), **3.6× agent cost** |

No unsafe write reached the CRM in any LLM run: every bad attempt was refused by the agent-side guards or the CRM validation layer. The offline suite now has **170 tests: 163 pass, 7 error**. The 7 errors are pre-existing on `srijan-m4`: they need `model_pilot_plan.md`, which was not committed. No real outbound calls were made.

Primary evidence: [progress record](progress.md), [experiment log](../../experiments/EXPERIMENT_LOG.md), [development matrix runs](../../experiments/runs/m4_dev_matrix/), [paid smoke report](paid_smoke_report.md).

## 2. Scope, data and preprocessing

Solar is the main evaluated business. Furniture and Dental remain part of the existing deterministic outbound-gate regression, not a broader M4 agent evaluation. Contacts, caller scenarios, CRM changes and operational policies are synthetic. The CRM is resettable and in memory; it is not a production database or a live authentication service.

The original Solar pilot contains ten tasks, five sourced reference facts and ten invented sandbox rules. Preprocessing produces 15 chunks and separates agent, caller, evaluator and trusted-harness views. M4 adds document-qualified section/chunk IDs and preserves provenance through retrieval without changing legacy hit IDs.

| Development artifact | Recorded inventory | Interpretation |
|---|---|---|
| Short policy pack | 1 document; 979 words; 15 chunks; approximately 1,718 tokens | Original fact/rule content |
| Large policy pack | 1 document; 5,523 words; 53 chunks; approximately 9,048 tokens | Adds fictional exceptions, dated versions, cross-references and distractors |
| Retrieval questions | 14 answerable + 6 unanswerable | Draft relevance/answer annotations; human review pending |
| Frozen development scenarios | IN01–IN10 + DEV11–DEV16 | 16 exposed cases, not an independent test set |
| Protected held-out cases | 0 text / 0 audio | Deferred; evaluation disabled |

Document token counts use a characters/4 estimate, not a billing tokenizer. Public references and invented sandbox rules remain separate. Citation does not grant third-party redistribution rights. Source pages were not freshly reverified in the policy-pack step, and human source, rights or policy approval is not claimed.

See [policy pack report](policy_packs_report.md), [source register](policy_packs/sources.json), [review request](policy_packs/REVIEW_REQUEST.md), [development manifest](development/manifest.json) and [development guide](development/README.md).

## 3. Implemented system

### 3.1 Shared text episode

The episode loads synthetic data, resets the CRM, and alternates a simulated caller (`gpt-4o-mini`) with the agent under test. Business rules are always in the system prompt; facts are retrieved with local BM25. CRM tools pass a shared validation layer: fixture-backed identity verification, a fresh caller confirmation for writes, picklists and atomic failure. Exact CRM comparison is scored separately from the language judge. Transcripts, tool results, final states, usage and errors are saved.

- Maximum admitted caller turns: **12**. The greeting, agent messages and tool steps do not consume caller turns.
- Per caller turn: at most **8 model calls and 8 executed tool calls**. In the multi-agent design these caps are shared by the coordinator and all specialists, so there is no extra specialist budget.
- Confirmation detection remains a known limitation: a "yes" counts only after an agent question that ends in "?". This is not robust action-bound consent, and fixture identity is not live authentication.
- The outbound gate checks consent, allowlist, opt-out, hours, recency, attempt limits and duplicate events. It decides only; it never dials, enqueues or records attempts.

### 3.2 Single agent (B0): archived M3 baseline and Step 9 candidate

| Mode | Prompt | Agent-side guards | Purpose |
|---|---|---|---|
| `llm` | archived M3 prompt, unchanged | none | Historical baseline for the prompt comparison |
| `single_v2` | v2 prompt | provenance guard; output check | **B0 development candidate** |

Each line added in the v2 prompt targets an observed M3 or development failure:
- Never guess a contact ID or email.
- Collect every S9 field, then `find_lead`, read the details back, and call `create_lead` once.
- Ask for confirmation with a direct question ending in "?", and call the tool in the same turn as the caller's yes.
- Answer every part of a factual question and offer a human when the facts run out.
- Report outcomes from tool results.
- Accept refusals, summarise and close.

The guards are deterministic and only ever refuse:
- **Provenance guard.** A `contact_id` or `email` argument must appear in a caller message or in a value returned by an earlier tool. Otherwise the call is refused as `argument_not_from_conversation` and logged; nothing executes.
- **Output check.** A reply that promises an action without a tool call after the caller confirmed, or that claims something "has been saved" or "scheduled" when no write succeeded in the call, is held back. It is not sent and not fed back to the model. The model gets one harness note. A second violation in the same turn is logged as `*_unresolved`, never hidden.

### 3.3 Multi-agent candidate (M1)

Implemented to the treatment contract in [comparison_plan.md](comparison_plan.md) ([code](../../src/voice_agent/inference/multi_agent.py)):

- A **coordinator** is the only role that speaks to the caller. It consults one specialist at a time; workers never message each other.
- The **knowledge** specialist calls `search_docs` and returns an answer proposal. Its source IDs are limited to facts it actually retrieved; any other IDs are listed separately.
- The **qualification** specialist returns the lead fields the caller has stated and those still missing.
- The **CRM/handoff planner** proposes one write tool call and lists any missing authorization. It never executes.
- **Writes only through plans.** The coordinator has no write tools. `execute_crm_plan(plan_id)` runs a stored plan once, through the same provenance guard and CRM validation layer. Direct write attempts are refused (`write_requires_crm_plan`) and logged as an adherence issue.
- **Trusted state** (identity binding, confirmation) lives in the sandbox. A specialist's text cannot create either.
- **Overhead is visible:** usage is logged per role and per delegation, and the trace includes delegations and plan IDs. Invalid specialist JSON returns `specialist_invalid_output` to the coordinator; exhausting the caps ends the turn with a hand-to-human message.

Prompts, tool and handoff schemas and the effective configuration, with SHA-256 hashes, are saved in [agents/](agents/) and regenerated by `scripts/export_agent_configs.py`.

### 3.4 Voice status

Not built. Steps 15–17 are not started. Srijan's 19 November note selected browser ↔ local LiveKit ↔ direct OpenAI Realtime. A 22 November proposal compares that with a cascaded path (Silero VAD → OpenAI speech-to-text → the existing agents → OpenAI text-to-speech). The cascaded path is estimated at about $0.70–1.30 and 2.5–3.5 working days, against about $1.60–3.70 and 3.5–4.5 days for Realtime, and it reuses both tested agents unchanged. The team has not yet decided. No audio, WER or voice-latency result exists.

## 4. Reliability changes and historical corrections

### 4.1 Judge and run integrity

The evaluator rejects missing, duplicate, unknown or malformed rubric verdicts, non-boolean labels, empty evidence and duplicate JSON keys. Invalid judgments produce explicit evaluation errors with null language and reward fields, never an automatic agent pass or failure. Raw prompts, responses and usage remain available. Run reporting separates agent, simulator, judge, infrastructure and mixed issues. Partial coverage is explicit, checkpoint writes are atomic, and new run directories cannot overwrite earlier runs. See [judge reliability report](judging_reliability.md).

### 4.2 Defects found and fixed during Steps 9–10 (each has a regression test)

| Defect | Found in | Fix |
|---|---|---|
| A caller's "yes" did not count because the agent asked "Please confirm…" without "?" | local smoke `single_v2`/IN05 | Prompt: confirmations are direct questions. The CRM rule was **not** loosened |
| After the harness note, a small model continued its own draft **as the caller** | local smoke `single_v2`/IN10 | The draft is discarded; the note says it is not from the caller |
| Coordinator said "your callback has been successfully scheduled" with no write | local smoke `multi`/IN05 | Output check for success claims with no successful write |
| The provenance guard matched the JSON **field name** `verified_contact_id` | local smoke `multi_r2`/IN05 | Guard matches values only. The CRM layer had already blocked the write (`wrong_target_contact`) |

### 4.3 M3 corrections, without rewriting history

- **Turn limit:** the source and M3 slides use 12 caller turns; the M3 report's 14-turn statement is inconsistent. A boundary regression test was added.
- **Test count:** source history progresses from 17 to 23 to 24 tests. The fresh M4 baseline executed 24. This does not independently verify historical pass claims.
- **Repeat stops:** the original IN01, IN02, IN04 and IN09 rewards are 0, 0, 1 and 1. A repeat-stop is a termination reason, not an automatic failure; none reached the turn limit.
- **Judge problems:** IN01 omits a required verdict, and IN09 has a structurally valid but disputed semantic verdict. Agent and caller issues also occur in these cases. The historical 5/10 aggregate is preserved, not presented as a corrected score.

Full case evidence: [baseline audit](baseline_audit.md). Proposed corrections remain [pending human adjudication](adjudication.json).

## 5. Recorded checks and experiments

These rows have different denominators and must not be combined into one success rate.

### 5.1 Deterministic and preparation checks (Srijan, 19 November)

| Check | Saved result | What it establishes / excludes |
|---|---|---|
| Offline suite (Step 11) | 124 passed; 0 skipped | Deterministic regression coverage at that commit |
| Solar oracle | 10/10 exact CRM states | Harness and fixtures agree; language not judged |
| Skip-confirmation / skip-verification controls | 6 intended blocks each; 1/5 write-task matches | Opt-out needs no extra confirmation; a new lead needs no existing-record verification |
| Outbound gate | 30/30 expected labels; 0 false allows | Offline decisions, not calls |
| Development fixture audit | 16/16 full expected states matched | Fixtures, not LLM behaviour |
| Short / large draft retrieval Recall@3 | 90.48% / 74.27% | Annotated relevant-set recall on 14 answerable questions |
| Paid diagnostics (Steps 5, 11) | Step 5 judge rejected (exit 1); Step 11 passed | Read-only paid path works; failure retained |

On the `abhishek-m4` branch the oracle, both controls and the outbound gate were re-run after the Step 9–10 changes, with identical results.

### 5.2 Step 10 smoke (gpt-4o-mini, IN02/IN05/IN10)

| Design | IN02 new lead | IN05 callback | IN10 opt-out |
|---|---|---|---|
| single_v2 | CRM exact; reward 0 (did not say an inspection is needed) | ✅ | ✅ |
| multi | CRM exact; reward 0 (judge: false-success claim) | CRM exact; reward 0 (called a request "scheduled") | ✅ |

Earlier local `qwen3:8b` smoke runs were used only to find bugs (§4.2). A first paid attempt was refused with HTTP 429 `insufficient_quota`, because an old key in the shell overrode `.env`; no tokens were processed.

### 5.3 Development matrix (Steps 12–14)

All runs used the [development matrix runner](../../scripts/run_dev_matrix.py) on frozen core scenarios IN01–IN10 × 3 repetitions. Episodes ran one at a time, each in its own capped ledger batch, with every attempt kept. Caller and judge were always `gpt-4o-mini`. A cell with identical settings is stored once and reused between steps. All 180 new episodes completed; one multi-agent episode has an invalid judge verdict and is unscored. Each step had its own approval: [12](evidence/dev_matrix/step12_approval.json), [13](evidence/dev_matrix/step13_approval.json), [14](evidence/dev_matrix/step14_approval.json).

| Cell (agent model · design · document · top-k) | CRM exact | Write tasks exact | Full pass | Commun. | Safety | False-success | Blocked unsafe | All 3 runs pass | Any run passes | Agent calls / ep. | Agent cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4o-mini · single_v2 · short · 3 (**baseline**) | 26/30 | 11/15 | 17/30 | 17/30 | 27/30 | 3 | 2 | 4/10 | 7/10 | 6.7 | $0.069 |
| 4.1-mini · single_v2 · short · 3 | 27/30 | 12/15 | 17/30 | 19/30 | 24/30 | 5 | 1 | 5/10 | 6/10 | 7.5 | $0.209 |
| 4o-mini · **multi** · short · 3 | 25/30 | 10/15 | 16/29 | 18/29 | 19/29 | 10 | 1 | 4/10 | 7/10 | 10.4 | $0.087 |
| 4o-mini · single (M3 prompt) · short · 3 | 27/30 | 12/15 | 18/30 | 18/30 | 26/30 | 4 | 5 | 6/10 | 6/10 | 6.6 | $0.060 |
| 4o-mini · single_v2 · short · **5** | 30/30 | 15/15 | 17/30 | 17/30 | 24/30 | 6 | 2 | 4/10 | 7/10 | 7.6 | $0.079 |
| 4o-mini · single_v2 · **large** · 3 | 27/30 | 12/15 | 18/30 | 18/30 | 27/30 | 2 | 2 | 4/10 | 8/10 | 7.0 | $0.248 |

Caller and judge overhead was about $0.023–0.026 per cell.

**Paired view against the baseline** (same task and repetition; descriptive only, because repetitions of one scenario are not independent):

| Comparison | Full pass: baseline only / other only / both / neither | CRM exact: baseline only / other only |
|---|---|---|
| Multi-agent | 4 / 3 / 13 / 9 (1 unscored) | 2 / 1 |
| M3 prompt | 1 / 2 / 16 / 11 | 0 / 1 |
| Top-5 | 3 / 3 / 14 / 10 | **0 / 4** |
| Large pack | 2 / 3 / 15 / 10 | 0 / 1 |

Per-task patterns: both models and all variants fail **IN03** (tenant handoff without first updating `roof_permission`) and **IN07** (blackout question: storage or hybrid options not explained). IN02 is mostly CRM-exact but loses communication points. The multi-agent design fails IN06 and IN08 in all three runs, each with a judge-flagged false-success claim. Median episode time was 10.7 s (single) vs 17.1 s (multi); that is text HTTP time, not voice latency.

**Selections fixed before or during development:** gpt-4o-mini by the Step 12 rule (tie → cheaper). Proposed development settings, for team confirmation: v2 prompt and guards, short pack (large for long-document cases), BM25 top-3 until the top-5 safety flags are reviewed.

### 5.4 Relation to the frozen 19 November plan

The registered `m4-comparison-v1` matrix (240 + 24 slots) was **not executed as registered**. The development matrix is a smaller prospective design approved step by step:
- One agent model per step instead of the full model × architecture × document crossing.
- No DEV11–DEV16 targeted cells.
- Three focused Step 14 comparisons.

The registered second model (`gpt-4.1-mini`) and the frozen caller and judge settings were used. New source files cause the freeze checker to report membership drift, as it already did after Step 11. A prospective versioned amendment is needed before any registered comparison or held-out evaluation, and the results above are labelled development evidence. Srijan's Step 12 pilot settings (Gemma via OpenRouter vs gpt-4o-mini) were prepared but not run; any source change also drifts them.

## 6. Concrete evidence examples (real LLM runs unless stated)

### Grounded answer

[`4omini__single_v2__short__k3__IN01__r1`](../../experiments/runs/m4_dev_matrix/4omini__single_v2__short__k3__IN01__r1/): the caller asks whether a meter serving both home and shop makes them "definitely entitled" to a residential subsidy. `search_docs` returns F2 and **F3** (subsidy is an eligibility question requiring scheme, location, consumer-category and utility checks). The agent answers:

> I can't guarantee entitlement to a residential subsidy, as it requires specific checks based on your situation. Would you like me to connect you with a qualified human…?

The CRM is unchanged, as gold expects; reward 1.

### Confirmed CRM update

[`…__IN05__r1`](../../experiments/runs/m4_dev_matrix/4omini__single_v2__short__k3__IN05__r1/): the agent runs `verify_identity(C01, anika@example.invalid)` → success, then `check_availability(2026-11-03T17:30+05:30)` → available, and asks "Shall I schedule this for you?". The caller says yes. `schedule_callback` → `CB01`, `status: requested`, and C01's status changes to `callback_requested`. The full CRM matches gold.

The CRM change is exact, but the agent then said the callback was "successfully scheduled". The judge accepted this here, although in other runs (§5.2) it counts the same wording against the agent because a request is not a booking.

### Safe rejection

[`4omini__llm__short__k3__IN08__r1`](../../experiments/runs/m4_dev_matrix/4omini__llm__short__k3__IN08__r1/) (archived M3 prompt): the agent calls `update_lead(C09, shading=afternoon_water_tank_shadow)` before the caller confirmed. The validation layer refuses it with `caller_confirmation_missing`, and the CRM is unchanged. In the local smoke runs, the provenance guard refused invented identifiers such as `contact_id: "Anika's contact ID"`, `"123456"` and `diya@example.com` before they reached the CRM.

### Genuine failures

- **Multi-agent wrong time** — [`4omini__multi__short__k3__IN06__r1`](../../experiments/runs/m4_dev_matrix/4omini__multi__short__k3__IN06__r1/). The caller says the booking was paid at 09:00 on 1 November (Asia/Kolkata). The planner wrote `booking_paid_at: "2026-11-01T09:00:00Z"`, which the CRM correctly converts to 14:30 IST. The handoff therefore records the wrong time (gold expects 09:00 +05:30). Before that, the coordinator twice told the caller the request "was not saved" and asked to try again. CRM fail; the judge flags a false-success claim.
- **Single agent skips an update** — [`4omini__single_v2__short__k3__IN03__r1`](../../experiments/runs/m4_dev_matrix/4omini__single_v2__short__k3__IN03__r1/). The tenant asks for `roof_permission` to be set to `landlord_approval_pending` and for a human handoff. The agent records the handoff but never calls `update_lead`, so the permission stays `unknown` and the handoff lacks the update outcome. This fails in every run of every variant.
- **Strict judge** (19 November): the first paid diagnostic's judge returned `violated: false` with empty evidence. The validator rejected it, and the result is retained as a failure.

## 7. Models, configuration and cost

All paid calls used direct OpenAI Chat Completions, default tier, temperature 0, n = 1, zero retries, no audio, and output caps of 200 (caller), 800 (agent) and 1200 (judge). Prices are recorded in the [ledger](../../experiments/cost_ledger.json):
- `gpt-4o-mini-2024-07-18`: $0.15 / $0.60 per million input / output tokens (Srijan, 19 November).
- `gpt-4.1-mini-2025-04-14`: $0.40 / $1.60, from the [official model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini), accessed 22 November. Its reservation bound uses the 64,000-byte request cap.

| Paid work | Usage-priced estimate |
|---|---|
| Steps 5 and 11 diagnostics | $0.00045 |
| Step 10 smoke (2 runs, 6 episodes) | $0.024 |
| Steps 12–14 development matrix (180 episodes) | $0.897 |
| **Recorded total** | **$0.921** |

A further $0.17 is held conservatively for requests the provider refused with HTTP 429 (no tokens processed). The remaining-credit estimate is $18.91. These are usage-priced estimates, not an invoice. Per episode, the agent service cost is about $0.002–0.008 and caller/judge overhead about $0.001. There are no voice minutes, so cost per call-minute is undefined. Telephony, LiveKit Cloud and third-party speech are excluded and were not used.

## 8. Long documents, unseen enquiries, hallucination and consent

- **Long documents:** the large pack (5,523 words, 53 chunks) did not lower CRM or task results in 30 episodes but cost 3.6× more. Draft Recall@3 falls from 90.48% to 74.27% on the larger pack, so robustness beyond this scale is not claimed.
- **Unseen enquiries:** none tested. All scenarios are exposed development data, and there are 0 held-out cases.
- **Hallucination controls:** rules are always in the prompt; facts come from retrieved, cited chunks. The knowledge specialist's citations are limited to retrieved IDs. The provenance guard refuses invented identifiers, and the output check holds back unsupported "done" claims. Remaining hallucinations are visible as IN07 omissions and judge-flagged false-success claims.
- **Consent:** writes require verified identity and an explicit yes after a question. Opt-outs need verification only. The outbound gate blocks non-consented, opted-out, out-of-hours, duplicate and over-limit contacts (0 false allows in 30 cases).
- **Synthetic-data limits:** fictional businesses, scripted fixtures, LLM callers that over-use "Yes, I confirm", and a judge from the same model family as the agent. All judge labels need human review before they are quoted as performance.

## 9. Reproducibility and artifact index

Environment: Python 3.15.2, macOS arm64, standard library only for the text harness.

Free verification (no paid calls):

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_m3_pipeline.py --mode oracle --run-id <new-id>
python3 scripts/run_dev_matrix.py --summary        # regenerates the table in §5.3 from saved runs
python3 scripts/export_agent_configs.py            # regenerates prompts/configs in agents/
```

Paid commands, which need a new approval and must never reuse a consumed batch:

```bash
python3 scripts/run_m3_pipeline.py --mode single_v2|multi --tasks IN02 --budget-batch <approved-id>
python3 scripts/run_dev_matrix.py --plan step12|step13|step14 --model gpt-4o-mini-2024-07-18
```

| Artifact | Location |
|---|---|
| Step plan and dated record | [Plan](STEP_BY_STEP_PROMPTS.md), [progress](progress.md) |
| Agents, prompts, schemas, configs | [single agent](../../src/voice_agent/inference/agent.py), [multi-agent](../../src/voice_agent/inference/multi_agent.py), [CRM/validation](../../src/voice_agent/inference/crm.py), [agents/](agents/) |
| Runners | [episode](../../src/voice_agent/pipelines/episode.py), [CLI](../../scripts/run_m3_pipeline.py), [development matrix](../../scripts/run_dev_matrix.py) |
| Tests | [Step 9](../../tests/test_step9_single_agent.py), [Step 10](../../tests/test_step10_multi_agent.py), [matrix](../../tests/test_dev_matrix.py) and earlier suites |
| Corpus, questions, provenance | [Policy packs](policy_packs/), [questions](policy_packs/questions.json), [sources](policy_packs/sources.json) |
| Development cases and held-out boundary | [Development](development/), [independent author brief](development/INDEPENDENT_AUTHOR_BRIEF.md) |
| Metrics and comparison contracts | [Measurement protocol](measurement_protocol.md), [comparison plan](comparison_plan.md) |
| Budget | [Budget module](../../src/voice_agent/models/budget.py), [ledger](../../experiments/cost_ledger.json), approvals in [evidence/](evidence/) |
| Raw runs and receipts | [Runs](../../experiments/runs/), [evidence](evidence/) |
| Configuration template | [.env.example](../../.env.example); the private `.env` is git-ignored |
| Audio, trained weights, checkpoints | Not available or not applicable: no audio collected, no fine-tuning |

There is no optimizer, training loss, epoch count or checkpoint. The experimental variables are model snapshot, prompt, retrieval top-k, document size, architecture, limits and evaluation protocol.

## 10. Remaining work and current decision

**Decision: retain the single agent (`single_v2` on gpt-4o-mini) as the development baseline; architecture selection is deferred to the held-out evaluation.** On development data the multi-agent candidate is slower, costlier and has more judged safety flags with no task-success gain. Under the M1 O11 rule it would not be adopted on this evidence, but that rule requires protected test data, voice latency and human-reviewed labels.

Outstanding:
1. **Voice (Steps 15–17):** choose cascaded or Realtime, then build, test speech, and run live sessions.
2. **Held-out evaluation (Steps 18–19):** independent authoring of ≥10 text cases and an audio subset, a frozen candidate manifest, the paid run and human review of every outcome.
3. **Human review** of judge labels: especially false-success flags, the top-5 safety flags, the M3 adjudications and policy/relevance annotations.
4. **Prompt work** for IN03 (update before handoff) and IN07 (storage/hybrid answer); the multi-agent planner's time-zone handling.
5. **Freeze amendment** for the source drift; Srijan's Step 12 pilot to be run or re-frozen; commit the missing `model_pilot_plan.md`.
6. **Contributions and acknowledgements** for Sarwar and Omkar, and Abhishek's signature; final slides presenter.

No commits, pushes or public submission are authorized by this report.

## 11. Contributions and AI assistance

| Member | M4 contribution record |
|---|---|
| Srijan | Directed the AI-assisted M4 development workflow for Steps 1–8 and 11 and the Step 12 pilot preparation; scope decisions; selected local LiveKit with direct OpenAI Realtime as the voice direction; approved the two bounded text diagnostics; deferred held-out authoring; requested the first version of this report, the worklog and his acknowledgement. Policy self-review was selected but remains pending. |
| Abhishek Jha | Directed and reviewed the AI-assisted implementation of Steps 9–10 (corrected single agent, provenance guard, output check, multi-agent coordinator and specialists, 25 new tests, saved prompt/config artifacts) and the development matrix runner. Found and fixed four defects through smoke runs. Set up the OpenAI key and credit and diagnosed the quota failure. Approved each paid batch for Steps 10 and 12–14 and the model-selection rule. Prepared the voice cost/time proposal and this report update and slides. |
| Sarwar Karim Akhand | M4 contribution statement and personal confirmation pending. |
| Omkar Shankar Pawar | Reviewed by hand the judge-flagged false-success claims in the Step 12–14 development runs and recorded where I agreed or disagreed with the gpt-4o-mini judge. Wrote an offline analysis script over the 180 saved episodes that adds confidence intervals, exact sign tests on the paired comparisons and a scenario-level bootstrap. Broke down per-role latency and cost to explain the multi-agent design's extra calls and time. Did the error analysis of the recurring IN03, IN06 and IN07 failures. |

AI assistants generated or assisted code, tests, synthetic fixtures, technical reviews and documentation. These outputs are not presented as manually authored code by any member. AI review and passing checks are not blanket human verification. Hours are recorded only where members supply them. See [WORKLOG.md](../../WORKLOG.md).

## 12. Member acknowledgement

This acknowledgement records participation and responsibility for the disclosed M4 work and its limitations. It does not assert that every requirement is complete, that disputed scores are approved, or that the whole team has signed.

| Name | Roll No. | Signature (initials) | Date |
|---|---|---|---|
| Srijan | 22f3002208 | S. | 19 November 2026 |
| Abhishek Jha | 23f3004013 | Pending | Pending |
| Sarwar Karim Akhand | 21f1006953 | Pending | Pending |
| Omkar Shankar Pawar | 23f1001898 | O.S.P. | 19 November 2026 |

Srijan's initials were entered at his explicit request on 19 November. Each other member must add their own initials. Whether assistant-entered initials satisfy the course's own-commit requirement still needs confirmation. The 19 November version of this report is preserved in git history (`e1b680b`).
