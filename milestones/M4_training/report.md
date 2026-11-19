# Milestone 4: Development and Experimental Preparation

**Project:** Voice Agents for Small-Business Enquiries and Lead Follow-up: Single-Agent vs Multi-Agent  
**Group 6:** Srijan · Abhishek Jha · Sarwar Karim Akhand · Omkar Shankar Pawar  
**Milestone date:** 19 November 2026  
**Status:** Partial milestone report. Text-pipeline reliability, development data, measurement definitions and two paid diagnostics are documented. Multi-agent, voice and controlled comparative evaluation remain incomplete. This is not a completed architecture-selection report.

## 1. Summary

M4 extends the M3 text-mode agent and sandbox rather than training a new model. Work so far addresses judge-output validation, error reporting, preservation of failed attempts, paid-request accounting, policy-document preparation, development fixtures and prospective comparison settings.

The latest saved offline suite records **124 passed, zero skipped**. Deterministic checks reproduce the ten pilot CRM end states and block the intended unsafe writes. These are harness checks, not evidence of LLM task success. A paid read-only diagnostic successfully exercised caller → agent/tool → answer → judge; an earlier diagnostic failed strict judge validation and remains preserved as a failure.

No specialist business-agent runtime, LiveKit audio path, independent held-out set or registered model/architecture comparison has been completed. No real outbound calls were made. Human policy/relevance review and historical score adjudication remain pending.

Primary evidence: [progress record](progress.md), [experiment log](../../experiments/EXPERIMENT_LOG.md), [paid smoke report](paid_smoke_report.md).

## 2. Scope, data and preprocessing

Solar is the main evaluated business. Furniture and Dental remain part of the existing deterministic outbound-gate regression, not a broader M4 agent evaluation. Contacts, caller scenarios, CRM changes and operational policies are synthetic. The CRM is resettable and in memory; it is not a production database or live authentication service.

The original Solar pilot contains ten tasks, five sourced reference facts and ten invented sandbox rules. Preprocessing produces 15 chunks and separates agent, caller, evaluator and trusted harness views. M4 adds document-qualified section/chunk IDs and preserves provenance through retrieval without changing legacy hit IDs.

| Development artifact | Recorded inventory | Interpretation |
|---|---|---|
| Short policy pack | 1 document; 979 words; 15 chunks; approximately 1,718 tokens | Original fact/rule content |
| Large policy pack | 1 document; 5,523 words; 53 chunks; approximately 9,048 tokens | Adds fictional exceptions, dated versions, cross-references and distractors |
| Retrieval questions | 14 answerable + 6 unanswerable | Draft relevance/answer annotations; human review pending |
| Frozen development scenarios | IN01–IN10 + DEV11–DEV16 | 16 exposed cases, not an independent test set |
| Protected held-out cases | 0 text / 0 audio | Deferred; evaluation disabled |

Document token counts use a characters/4 estimate, not a billing tokenizer. Public references and invented sandbox rules remain separate. Citation does not grant third-party redistribution rights. Source pages were not freshly reverified in the policy-pack step, and human source/rights/policy approval is not claimed.

See [policy pack report](policy_packs_report.md), [source register](policy_packs/sources.json), [review request](policy_packs/REVIEW_REQUEST.md), [development manifest](development/manifest.json) and [development guide](development/README.md).

## 3. Implemented system and planned treatment

### 3.1 Current single-agent baseline

The text episode loads synthetic data, resets the CRM, and alternates a simulated caller with one LLM agent. The agent can retrieve business knowledge using local BM25 and invoke CRM tools through a shared validation layer. Exact CRM comparisons are scored separately from language judgments. Transcripts, tool results, final states, usage and errors are saved.

- Maximum admitted caller turns: **12**. Greeting, agent messages and tool steps do not consume caller turns.
- Maximum tool/model rounds per caller turn: **8**; paid controls also limit actual function calls.
- Existing-record writes require fixture-backed identity verification and confirmation; opt-out and new-lead cases have documented exceptions.
- Confirmation detection remains a known limitation: it is not robust action-bound consent. Fixture identity is not live authentication.
- The outbound gate checks consent, allowlist, opt-out, hours, recency, attempt limits and duplicate events. It makes decisions only; it does not dial, enqueue or persist attempts.

Implementation: [agent](../../src/voice_agent/inference/agent.py), [CRM/validation](../../src/voice_agent/inference/crm.py), [retrieval](../../src/voice_agent/inference/retrieval.py), [episode runner](../../src/voice_agent/pipelines/episode.py), [outbound gate](../../src/voice_agent/inference/outbound_gate.py).

### 3.2 Multi-agent and voice status

The specialist multi-agent candidate remains proposed, not implemented. Separate caller and judge roles do not constitute that treatment. No architecture superiority or adoption decision is supported.

The selected future audio direction is browser audio ↔ local LiveKit ↔ direct OpenAI Realtime, with CRM/retrieval behind the same validator. This replaces the earlier cascaded-stack proposal. LiveKit, a browser audio client, a token endpoint and audio evaluation are not built. Deepgram/Cartesia evaluation is deferred. Local transport does not make model usage free; speech options documented in planning are not tested or enabled capabilities.

## 4. Reliability changes and historical corrections

### 4.1 Judge and run integrity

The evaluator now rejects missing, duplicate, unknown or malformed rubric verdicts, non-boolean labels, empty evidence and duplicate JSON keys. Invalid judgments produce explicit evaluation errors and null language/reward fields, not automatic agent failures or passes. Raw prompts, responses and usage remain available.

Run reporting separates agent, simulator, judge, infrastructure and mixed issues. Partial coverage is explicit; checkpoint writes use atomic replacement; new run directories cannot overwrite historical runs. Tool outcomes and exact CRM state remain independently inspectable.

See [judge reliability report](judging_reliability.md), [evaluator](../../src/voice_agent/evaluation/evaluator.py) and [regression tests](../../tests/test_evaluation_reliability.py).

### 4.2 M3 corrections, without rewriting history

- **Turn limit:** source and M3 slides use 12 caller turns; the M3 report's 14-turn statement is inconsistent. A boundary regression was added.
- **Test count:** source history progresses from 17 to 23 to 24 tests. The fresh M4 baseline executed 24. This does not independently verify historical pass claims.
- **Repeat stops:** original IN01, IN02, IN04 and IN09 rewards are 0, 0, 1 and 1. Repeat-stop is a termination reason, not an automatic failure; none reached the turn limit.
- **Judge problems:** IN01 omits a required verdict; IN09 has a structurally valid but disputed semantic verdict. Agent/caller issues also occur in these cases. The historical 5/10 aggregate is preserved, not presented as a corrected score.

Full case evidence and uncertainty: [baseline audit](baseline_audit.md). Proposed corrections remain [pending human adjudication](adjudication.json). This report and its acknowledgement do not approve those labels.

## 5. Recorded checks and experiments

These rows describe different checks with different denominators. They must not be combined into one agent success rate.

| Check | Saved result | What it establishes / excludes |
|---|---|---|
| Latest offline suite | 124 passed; 0 skipped | Deterministic regression coverage; not a fresh execution for this report |
| Solar oracle | 10/10 exact CRM states | Harness/fixture agreement; language unjudged |
| Skip-confirmation control | 6 intended blocks; 6/10 state matches; 1/5 write-task matches | Opt-out legitimately needs no extra confirmation |
| Skip-verification control | 6 intended blocks; 6/10 state matches; 1/5 write-task matches | New-lead creation does not require existing-record verification |
| Outbound gate | 30/30 expected labels; 0 false allows | Offline decisions, not actual calls |
| Expanded development fixture audit | 16/16 full expected states/outcomes matched | Fixtures, not LLM communication or injection robustness |
| Short / large draft retrieval Recall@3 | 90.48% / 74.27% | Annotated relevant-set recall on 14 answerable questions |
| Short / large canonical-core coverage@3 | 100% / 78.57% | Separate metric; relevance sets differ across packs |
| Paid Step 5 diagnostic | CLI exit 1; four HTTP 200 responses | Strict judge rejected empty evidence; failure retained |
| Paid Step 11 diagnostic | CLI exit 0; four HTTP 200 responses | One read-only tool continuation and valid judge schema; not full task evaluation |

Retrieval any-relevant hit rate@3 is 100% for both packs on the 14 answerable questions. This does not establish answer accuracy, calibrated abstention, temporal reasoning or broad long-document robustness. Unjudged language/false-success fields are unknown, not verified zeros.

Evidence directories: [Step 2](evidence/step2/), [Step 4](evidence/step4/), [Step 6](evidence/step6/), [Step 7](evidence/step7/), [Step 11](evidence/step11_smoke_001/). Saved runs: [oracle](../../experiments/runs/m4_step5_oracle/), [final controls](../../experiments/runs/m4_step4_control_skip_confirmation_final/), [verification control](../../experiments/runs/m4_step4_control_skip_verification_final/), [gate](../../experiments/runs/m4_step4_outbound_gate/), [policy packs](../../experiments/runs/m4_step6_policy_packs_final/) and [development audit](../../experiments/runs/m4_step7_development_stop/).

## 6. Concrete evidence examples

### Grounded paid answer

In `m4_step11_smoke_001`, the agent called `search_docs` against the synthetic source fixture `SMOKE-FACT-1` and answered:

> SunGrid cannot guarantee subsidy approval, as a human must review eligibility.

The saved source text, arguments, response and strict judgment are in [the actual run](../../experiments/runs/m4_step11_smoke_001/). The initial/expected/final CRM is unchanged. This is a deterministic read-only source fixture, not a BM25 or CRM-write benchmark.

### Confirmed CRM write — oracle only

In [the Step 5 oracle](../../experiments/runs/m4_step5_oracle/), IN02 first finds no match for the synthetic email `diya@example.invalid`. The script asks “Shall I save these enquiry details?” and receives “Yes, I confirm.” `create_lead` then succeeds with new contact `C13`, bill ₹3,700, Pune, and timeline 60 days. Outbound consent remains false. Full arguments and the final state are in `results.json`; the starting seed is [the Solar pilot seed](../M2_dataset/solar_pilot/crm_seed.json).

This verifies the scripted write path, not that an LLM collected or confirmed those details correctly.

### Unsafe-write rejection — negative control

The [skip-verification control](../../experiments/runs/m4_step4_control_skip_verification_final/) records six existing-record write blocks with `identity_not_verified`. Its permitted new-lead exception is intentional. This is deterministic enforcement evidence, not a claim that an LLM resisted every attack.

### Genuine observed failure

The [first paid diagnostic](../../experiments/runs/m4_step5_smoke_001/) returned `violated: false` with empty evidence for a prohibited item. The strict validator rejected the judgment; the CLI exited 1 and language reward remained unknown. The later diagnostic changed only its diagnostic instruction to require nonempty evidence and did not repair or relabel the old result.

Separately, oracle IN08 returns `fixture_atomic_write_failed` for an update to C09 and leaves the CRM unchanged. Matching that unchanged end state alone does not prove the correct failure explanation was given to a caller.

## 7. Models, configuration and cost

The two authorized paid diagnostics used **`gpt-4o-mini-2024-07-18`**, direct OpenAI Chat Completions, default tier, temperature 0 and n=1. Each made four requests: caller, agent tool request, agent answer and judge; zero retries, no audio and no CRM writes. Request output caps were 200/800/800/1200 tokens, with a 30-second request timeout and one read-only tool step. The snapshot worked at the recorded execution time; future access is not guaranteed.

Recorded pricing is $0.15 per million input text tokens and $0.60 per million output text tokens. These are the saved experiment assumptions, not a fresh pricing verification for this report. Exact provider references, access dates, model/deprecation limits and voice options are in [the model/spending plan](model_and_spending_plan.md).

| Diagnostic | Input / output tokens, all roles | Usage-priced estimate |
|---|---|---|
| Step 5, invalid judge | 834 / 149 | $0.00021450 |
| Step 11, accepted judge | 905 / 166 | $0.00023535 |
| **Cumulative** | **1,739 / 315** | **$0.00044985** |

Step 11 agent service cost is $0.00006120; caller/judge overhead is $0.00017415. All eight requests across both diagnostics are reconciled with no held reservations. The remaining estimate against user-reported $20 credit is $19.99955015, not a verified account balance or invoice. Pi assistant/research usage is separate. No call minutes exist, so cost per voice minute is undefined; text HTTP latency is not voice latency.

The [ledger](../../experiments/cost_ledger.json) reserves conservative cost before each paid attempt and includes caller, judge and retries. Planned allocations are $1 smoke, $9 text, $4 audio, $4 held-out and $2 reserve. Neither unused credit nor an earlier approval authorizes another batch.

The frozen worst-case conversation requires up to 109 requests and bounds at $2.14104 for the enabled model. This exceeds the current 100-request batch cap; paired architectures with three repetitions bound at $12.84624, above the $9 text allocation. A small diagnostic cannot forecast the full matrix. Execution needs a prospective design/budget amendment and explicit approval.

## 8. Comparison design, stability and generalization

[Comparison settings](comparison_settings.json), their [checksum](comparison_settings.sha256), the [comparison plan](comparison_plan.md) and [measurement protocol](measurement_protocol.md) define prospective development work:

- 2 model snapshots × 2 architectures × 2 document sizes × 10 core cases × 3 repetitions = **240 planned slots**.
- Six targeted development cases × 2 models × 2 architectures = **24 separate slots**.
- All comparison execution remains disabled. The second model and multi-agent runtime are not ready; **zero registered comparison slots have run**.
- Consistency across all three repetitions (`pass^3`) is separate from any-success `pass@3`. Invalid judging retains unknown components and explicit coverage.
- Planned architecture inference uses paired scenario-level analysis, not a claim that repeated runs are independent tasks. No significance or architecture-gain result exists yet.

The later smoke wrapper changes the frozen source set. The integrity checker correctly rejects this drift; the original freeze was not silently rewritten. An explicit prospective amendment is required before comparison execution.

There are no repeated full-agent results, protected test results, WER measurements, voice latency distributions or audio-cost results. Development fixtures are exposed. No stability, unseen-enquiry generalization, production compliance or superior architecture claim is supported.

## 9. Reproducibility and artifact index

Saved evidence records the checked environment as Python 3.15.2 on macOS arm64. The text harness uses the standard library. Runtime/source hashes and command receipts are in the per-step evidence directories; a commit alone does not identify the uncommitted working tree. No clean-environment reproduction or fresh runtime test was performed while writing this report.

Free verification entry points:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/preprocess_m3.py --business solar
```

Do not run the paid smoke wrappers as routine verification: their approvals are consumed. Other run/check/freeze commands and exact options are recorded in their linked guides and command receipts. Existing run directories and frozen artifacts must not be overwritten.

| Artifact | Location |
|---|---|
| Step plan and dated record | [Plan](STEP_BY_STEP_PROMPTS.md), [progress](progress.md) |
| Prompts/tool schemas/LLM adapter | [Agent](../../src/voice_agent/inference/agent.py), [CRM](../../src/voice_agent/inference/crm.py), [adapter](../../src/voice_agent/models/llm.py) |
| Corpus/questions/provenance | [Policy packs](policy_packs/), [questions](policy_packs/questions.json), [sources](policy_packs/sources.json) |
| Development cases and private-test boundary | [Development](development/), [independent author brief](development/INDEPENDENT_AUTHOR_BRIEF.md) |
| Measurement implementation | [Measurement helpers](../../src/voice_agent/evaluation/measurement.py), [tests](../../tests/test_measurement.py) |
| Budget controls | [Budget module](../../src/voice_agent/models/budget.py), [ledger](../../experiments/cost_ledger.json) |
| Configuration template | [.env.example](../../.env.example); private `.env` is excluded |
| Raw runs, receipts and conversations | [Runs](../../experiments/runs/), [evidence](evidence/) |
| Contributions | [WORKLOG.md](../../WORKLOG.md#milestone-4-development-and-experimental-preparation-due-19-nov-2026) |
| Audio, trained weights and checkpoints | Not available / not applicable: no audio collected and no fine-tuning performed |

There is no optimizer, training loss, epoch count or learned checkpoint. Experimental variables are model snapshots, prompts, retrieval/document settings, architecture, tool limits and evaluation protocol.

## 10. Remaining work and current decision

**Decision: retain the single-agent implementation as the development baseline; defer architecture selection.** This is not a finding that single-agent is better.

Outstanding work includes single-agent task-quality fixes, specialist runtime, calibrated human-reviewed labels, independent protected test custody, approved representative paid pilots, comparison/budget amendments, full repeated text experiments, LiveKit/Realtime implementation and audio evaluation. Final slides, complete member contributions and acknowledgements, package verification and course-format confirmation are also pending.

Source/rights review, judge adjudication and policy annotation review are separate approvals. The acknowledgement below does not complete them. No further paid calls, commits, pushes or public submission are authorized by this report.

## 11. Contributions and AI assistance

| Member | M4 contribution record |
|---|---|
| Srijan | Directed the AI-assisted M4 development workflow and scope decisions, selected local LiveKit with direct OpenAI Realtime as the future voice direction, approved the two bounded text diagnostics, deferred held-out authoring, and requested preparation of this report, worklog and personal acknowledgement. Policy self-review was selected but remains pending. |
| Abhishek Jha | M4 contribution statement and personal confirmation pending. |
| Sarwar Karim Akhand | M4 contribution statement and personal confirmation pending. |
| Omkar Shankar Pawar | M4 contribution statement and personal confirmation pending. |

AI assistants generated or assisted code, tests, synthetic fixtures, technical reviews and documentation. These outputs are not attributed as manually authored code by Srijan or as work by another member without confirmation. AI review and passing checks do not constitute blanket human verification. Hours are not recorded retrospectively. See [WORKLOG.md](../../WORKLOG.md).

## 12. Member acknowledgement

This acknowledgement records participation and responsibility for the disclosed partial M4 work and its limitations. It does not assert that all requirements are complete, every artifact has been personally reviewed, disputed scores are approved, or the whole team has signed. External references and AI assistance are disclosed in this report and its linked source registers.

| Name | Roll No. | Signature (initials) | Date |
|---|---|---|---|
| Srijan | 22f3002208 | S. | 19 November 2026 |
| Abhishek Jha | 23f3004013 | Pending | Pending |
| Sarwar Karim Akhand | 21f1006953 | Pending | Pending |
| Omkar Shankar Pawar | 23f1001898 | Pending | Pending |

Srijan's initials were entered by the assistant at his explicit request in this session. Other members' roll numbers are carried from prior milestone records; their M4 signatures are not carried forward. Each must supply their own acknowledgement. Whether assistant-entered initials satisfy the course's personal-signature/own-commit requirement still needs confirmation; this file has not been committed or submitted.
