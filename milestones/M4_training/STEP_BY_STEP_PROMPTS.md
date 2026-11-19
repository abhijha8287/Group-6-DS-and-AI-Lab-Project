# Milestone 4 — Detailed Steps

Follow these steps in order. Complete and review one step before starting the next. Keep the agent conversation and the actual test/call logs for submission.

The deadline is November 19. The available OpenAI credit is $20. Ask before each paid batch. Use synthetic data and a sandbox CRM; do not make real outbound calls.

## 1. Check the repository and the current implementation

1. Check that the current branch is `srijan-m4`. Check for uncommitted changes before editing anything.
2. Fetch `origin/main` and inspect new changes. Do not merge or discard work automatically.
3. Read these files:
   - `problem_statement/problem_statement.md`
   - `milestones/M1_problem_literature/report.md`, especially the objectives
   - `milestones/M3_architecture/report.md`
   - `experiments/EXPERIMENT_LOG.md`
   - `WORKLOG.md`
4. Inspect the source and identify the code for the agent, retrieval, CRM, consent checks, caller simulator, evaluator, and episode runner.
5. Check whether multi-agent, LiveKit, STT, and TTS actually run. Separate implemented features from diagrams and proposed features.
6. Check the environment setup and dependencies. Check whether credentials are present without printing their values.
7. Write down what already works, what is missing, and which files need changes. Keep this in `milestones/M4_training/progress.md` and update it as work proceeds.
8. Keep Solar as the main evaluated business unless the team approves broader coverage. Use STT → agent/tools → TTS through LiveKit as the minimum voice path.

**Stop when:** the starting implementation and missing work are clear, with file references. Ask for missing access or scope decisions. Do not make paid calls.

## 2. Run the existing tests and baseline checks

1. Follow the repository's setup instructions. Record Python and dependency versions.
2. Run `python3 -m unittest discover -s tests -v` in the documented environment.
3. Save the command, output, exit code, current commit, and number of executed/skipped tests.
4. Compare the actual result with the report's 17 tests and the worklog's 24/24 claim. Explain whether these refer to different versions or cannot be verified historically.
5. Run the existing oracle replay, outbound gate, and negative controls after checking that they make no paid calls. Use new output directories so old results remain unchanged.
6. Check that the oracle matches expected CRM states and negative controls block the intended unsafe actions. Explain any legitimate exceptions.
7. Fix reproducible code/test defects with focused regression tests. Do not change expected answers just to make a test pass.

**Stop when:** the local baseline checks pass, or a specific blocker is documented. Record current results separately from historical claims.

## 3. Resolve the M3 turn-limit and repeat-stop inconsistencies

1. Read the episode loop and determine the effective caller-turn limit. The current source uses `MAX_CALLER_TURNS = 12`; verify this before documenting it.
2. Compare this with the M3 report's 14-turn statement and the slides. Define whether the greeting, caller messages, agent messages, and tool steps count.
3. Add a small boundary test for the actual turn limit.
4. Open the original M3 results and transcripts for **IN01, IN02, IN04, and IN09**. These are the saved `caller_repeat_stop` cases.
5. For each case, identify the repeated caller message, preceding agent response, relevant tool calls, and final CRM state.
6. Explain whether the issue came from the agent, caller simulator, judge, or more than one component. Do not treat every repeat-stop as task failure.
7. Write the audit in `milestones/M4_training/baseline_audit.md`. Link the original evidence and propose corrections to the report/slides without overwriting old runs.

**Stop when:** all four cases and the turn-count discrepancy have an evidence-backed explanation. Mark uncertain historical details as uncertain.

## 4. Fix judge and scoring reliability

1. Inspect how the evaluator checks required information and prohibited actions.
2. Examine IN01's incomplete criterion verdict and IN09's lenient verdict against their exact rubrics and transcripts.
3. Check for missing, duplicate, unknown, and malformed judge verdicts.
4. Make incomplete or invalid judgments explicit evaluation errors. Do not silently turn them into passes or ordinary agent failures.
5. Keep deterministic CRM state comparisons and tool outcomes separate from language judgments.
6. Record agent errors, simulator errors, judge errors, infrastructure errors, and mixed causes separately. Preserve all attempted runs.
7. Add regression tests for changed validation and scoring behavior. Run the full deterministic suite again.
8. Prepare a separate adjudication file with original score, proposed correction, evidence, reason, and reviewer. A human must confirm reviewed labels; leave them pending until that happens.

**Stop when:** invalid judge outputs are detected, tests pass, and disputed outcomes are ready for human review. Do not overwrite the original M3 scores.

## 5. Verify model choices and set spending limits

1. Inspect the existing model client and determine which providers and tool-call formats it supports.
2. Use official provider documentation to verify one affordable OpenAI text model and feasible STT/TTS options. Record exact model IDs, URLs, access dates, and pricing units.
3. Check local model availability. Use local models for development checks where practical.
4. Check LiveKit setup and any separate provider costs. OpenAI credit does not cover LiveKit, Deepgram, Cartesia, or telephony charges.
5. Start a simple cost ledger under `experiments/`. Record approved allocation, estimated spend, recorded usage, and remaining credit.
6. Use these proposed ceilings unless the team approves a change:
   - $1: smoke tests and calibration.
   - $9: text development, including caller and judge.
   - $4: audio experiments.
   - $4: held-out evaluation.
   - $2: reserve, used only with approval.
7. Set hard limits on output tokens, requests, caller turns, tool steps, retries, and audio duration. Reserve a conservative maximum cost before each request or batch.
8. Test cost calculations and limit enforcement without paid calls. Count simulator, judge, and retry usage too.
9. Show the proposed first smoke test, its purpose, and its maximum cost. Ask for approval before running it.

**Stop when:** model names/prices are verified, cost controls are tested, and the next paid action has a clear spending cap. Stop earlier if usage cannot be bounded.

## 6. Add larger policy documents

1. Inspect the existing Solar knowledge format and chunking code.
2. Keep sourced facts separate from synthetic sandbox policies. Record source permissions and clearly label invented policies.
3. Create a short pack and a larger pack with the same answers to matched questions.
4. Expand the larger pack with meaningful policy exceptions, similar terms, cross-references, irrelevant sections, and effective dates. Do not add repeated filler just to increase size.
5. Include questions that cannot be answered from the documents and should lead to clarification or escalation.
6. Record document count, word/token count, section count, chunk count, source metadata, and content hashes.
7. Annotate the relevant source sections for retrieval questions so Recall@k can be measured.
8. Test preprocessing and confirm that chunk/source IDs survive retrieval.
9. Ask a team member to review policy assumptions and factual claims.

**Stop when:** both packs are reproducible, the larger pack adds real complexity, and sources/answer annotations are reviewable. Do not claim robustness beyond the scale actually tested.

## 7. Prepare development scenarios and protect the held-out set

1. Inspect the existing split manifest. Treat `review_only` expansions as development/review data, not untouched test data.
2. Freeze 10 core development scenarios. Add targeted cases where needed for CRM creation/update, identity, consent, opt-out, escalation, prompt injection, missing information, and long-document questions.
3. Check every scenario's starting CRM, caller information, expected final state, required communication, and prohibited actions.
4. Preserve the four views: agent, simulator, evaluator, and trusted harness. Test that answer keys and privileged fixtures cannot enter agent prompts or retrieved documents.
5. Give an independent author/reviewer a schema and coverage brief for at least 10 new held-out scenarios. Keep held-out answer keys out of the implementation agent's conversation.
6. Reserve a separate small held-out audio subset. Record who reviewed it and how access is restricted.
7. Save a manifest with scenario IDs, split membership, data/document hashes, and versions.
8. If independent holdout protection is not possible, explain that limitation and ask how to proceed. Do not rename exposed data as held-out.

**Stop when:** development fixtures are valid, leakage checks pass, and the held-out creation/review process is agreed. Do not inspect held-out answers during development.

## 8. Define metrics and freeze the comparison settings

1. Read the full M1 O1–O11 definitions and retain their original targets.
2. Define task completion using correct CRM state, required information, and safety conditions.
3. Report CRM exact-state accuracy for all tasks and separately for write tasks. Include wrong-record and duplicate-lead rates.
4. Report policy violations, unconfirmed actions, false-success claims, and blocked unsafe attempts separately.
5. Define factual accuracy, unsupported claims, escalation precision/recall, handoff completeness, outbound gating, and follow-up trigger metrics.
6. Define retrieval Recall@k and answer faithfulness using reviewed source annotations.
7. Define STT WER, critical-field accuracy, and a fixed transcript normalization policy.
8. Define voice latency as end of caller speech to first audible agent response. Record component timings separately.
9. Report cost per conversation and call-minute. Separate agent service cost from simulator/judge evaluation overhead.
10. Specify metric denominators, exclusions, undefined cases, and invalid runs. Show attempt-based counts as well as valid-run scores.
11. Use three repetitions for core model/architecture comparisons. Report all-three-run consistency; do not confuse this with pass@3, which means at least one success.
12. Freeze caller settings, turn/tool/retry limits, scorer version, runtime settings, and experiment matrix. Repeated runs of one scenario are not independent new scenarios.

**Stop when:** another person can calculate each metric from the saved artifacts and the planned comparisons are fixed before running them.

## 9. Fix the single-agent development problems

1. Read the development failure transcripts and inspect prompts, tool schemas, CRM validation, and affected callers.
2. Fix invented contact IDs/emails. Use caller-supplied information and trusted tool results instead.
3. Make the agent collect required fields before creating an incomplete lead that it cannot safely finish updating.
4. Keep identity verification, confirmation, consent, and opt-out rules intact. Do not weaken them to improve scores.
5. Make the agent check tool results before claiming an action succeeded.
6. Improve clarification, refusal handling, and conversation closure using development evidence.
7. Save the original M3 prompt and the corrected prompt as separate comparison artifacts.
8. Add focused regression tests for changed behavior and security boundaries. Run the common suite.
9. Save the effective single-agent configuration, including model, prompt, tool schemas, retrieval, temperature, and limits.

**Stop when:** the candidate is runnable, tests pass, and unresolved model-dependent behavior is listed. Do not tune using held-out scenarios.

## 10. Implement the multi-agent candidate

1. Reuse the existing client, retrieval, CRM sandbox, and evaluation interfaces.
2. Use a conversation agent for dialogue/retrieval and a CRM specialist for structured updates/follow-ups. Only the conversation agent speaks to the caller.
3. Define the handoff fields and the information each role can see.
4. Give both designs equivalent business facts and permissions. Keep the same deterministic validation layer.
5. Pass trusted identity and confirmation state through trusted code. A specialist's text must not create consent or identity verification.
6. Bound handoffs and tool loops. Handle specialist failures with a clear error or escalation.
7. Log role-specific calls, tokens, handoffs, and tool actions so multi-agent overhead remains visible.
8. Test missing identity, consent/refusal, tool rejection, handoff failure, and termination.
9. Run both designs through the same smoke scenarios and scorer. Confirm that multi mode really invokes a specialist rather than changing a label.
10. Save both prompts, handoff schema, tools, and effective configuration.

**Stop when:** both candidates run through the same evaluation contract and all relevant tests pass. Do not start paid comparisons yet.

## 11. Run a small paid smoke test

1. Show the exact model, roles, scenario IDs, request/token/retry limits, maximum cost, and remaining balance.
2. Ask for explicit approval of this batch only. Stop if the setup differs from the approved one.
3. Run a small development case that exercises tool calling and scoring, not just a greeting.
4. Save the transcript, retrieved sources, tool arguments/results, CRM diff, judgment, timings, and usage.
5. Check that the provider response and tool-call format work with the pipeline.
6. Calculate actual recorded usage costs and update the ledger. Distinguish estimated costs from billed costs.
7. Use measured usage and conservative limits to estimate the remaining experiment batches.

**Stop when:** the complete paid path works and its cost is accounted for. Ask before any further paid calls.

## 12. Compare the local and OpenAI text models

1. Use the same single-agent architecture, prompt, documents, retrieval, tools, caller policy, scorer, and initial CRM for both models.
2. Use the frozen core development scenarios with three repetitions each. Do not use the old M3 scores as a controlled substitute for rerunning the baseline.
3. Show the full run matrix and maximum batch cost. Obtain approval before execution.
4. Interleave candidate order where practical and record timing conditions. Save generated caller messages; identical caller settings do not guarantee identical dialogues.
5. Run only this comparison. Keep failures and interrupted runs in the record.
6. Compare task success, CRM accuracy, compliance, factual accuracy, consistency, latency, and cost with raw counts.
7. Have a human review failures and disputed judgments. Keep unreviewed labels visibly pending.
8. Select a common model for the architecture comparison based on the evidence and budget.
9. Update `experiments/EXPERIMENT_LOG.md` with setting, change, result, cost, limitation, and artifact link.

**Stop when:** the model comparison is documented and the common model is selected. Do not automatically start the next batch.

## 13. Compare single-agent and multi-agent in text

1. Use the selected common model and frozen development scenarios, with three repetitions per scenario.
2. Hold documents, retrieval, caller settings, scorer, initial CRM, permissions, and limits fixed.
3. Show and approve the batch cost before running it. Reuse an earlier run only if all relevant settings and hashes match.
4. Record specialist calls and handoff overhead as part of multi-agent cost/latency.
5. Compare per-scenario outcomes, CRM changes, policy/consent behavior, handoff failures, consistency, latency, and cost.
6. Separate agent problems from simulator, judge, and infrastructure problems. Explain mixed causes where needed.
7. Report paired results and uncertainty. Do not count each turn or repetition as an independent new task.
8. Record the development findings without making the final held-out architecture decision.

**Stop when:** the comparison has complete traces, reviewed failures, and a clear explanation of the trade-offs.

## 14. Test prompts, retrieval settings, and document size

1. Compare the archived M3 prompt with the corrected prompt, holding other factors fixed.
2. Compare BM25 top-3 with top-5 on the same documents and questions.
3. Compare matched short and larger policy packs with the same relevant answers.
4. Keep this as three focused comparisons, not every possible combination.
5. Show scenarios, repetitions, compatible reusable runs, and estimated cost. Get approval before paid calls. Agree on scope reductions before seeing results.
6. Measure retrieval Recall@k and inspect answer faithfulness. Report BM25's embedding model as not applicable.
7. Show exact document/chunk sizes and identify failures involving exceptions, irrelevant sections, missing facts, or source confusion.
8. Update the experiment summary and save all prompt/config versions.
9. Select development settings for both architecture candidates before voice and held-out evaluation.

**Stop when:** each planned comparison is complete or an approved omission is explicit, and conclusions link to actual results.

## 15. Build the LiveKit voice path

1. Read current official integration documentation for the selected LiveKit/STT/TTS components.
2. Check dependencies and ask before installations that affect shared environments or incur costs.
3. Connect VAD/end-of-turn detection → STT → the existing agent/tools → TTS → playback.
4. Reuse the same CRM/consent checks for both agent architectures.
5. Record model/package versions, language, sample rate, channels, encoding, VAD, end-of-turn, and interruption settings.
6. Add component timestamps using a consistent clock and clearly define the playback measurement boundary.
7. Test format conversion, disconnects, interruptions, partial responses, and failed tools with focused local/mocked checks.
8. Obtain approval before paid audio calls. Demonstrate a real LiveKit session rather than canned prerecorded output.
9. Save session evidence and instructions to reproduce it.

**Stop when:** live audio reaches the agent and audible generated output returns through the stated transport. If access or transport is missing, report the blocker rather than calling a text test a voice demonstration.

## 16. Prepare audio and compare STT/TTS options

1. Use consented recordings or clearly labelled synthetic speech. Remove personal data before committing or sharing it.
2. Prepare 20–30 development utterances with exact reference transcripts and 5–10 complete development conversations.
3. Include clean/noisy audio, emails, numbers, dates, corrections, hesitation, consent, refusal, and opt-out.
4. Record provenance, speaker/synthetic voice, format, duration, and noise transformations. Keep held-out audio unopened.
5. Compare two feasible STT options/settings on identical clips and two TTS options/settings on identical text. Label settings comparisons accurately.
6. Obtain batch approval before paid execution.
7. Calculate WER using the frozen normalization policy and report critical-field accuracy separately.
8. Measure TTS time-to-first-audio, failures, duration, and cost. Ask a human to listen for intelligibility and consent wording; do not invent naturalness ratings.
9. Explain limits of synthetic speakers, accent coverage, and dataset size.
10. Save reference/hypothesis transcripts, alignments, audio, timings, and costs. Select a fixed development voice configuration.

**Stop when:** speech comparisons are reproducible and human listening checks are completed or explicitly pending.

## 17. Test complete voice conversations

1. Use paired development scenarios and the selected common speech settings for both architectures.
2. Include a grounded answer, confirmed CRM change, refusal/opt-out, and any real failures observed.
3. Show the cost and obtain approval before paid sessions.
4. Run at least one real LiveKit session per candidate. Save approved audio alongside sources, tools, and CRM traces.
5. Compare reference-text input with STT input to isolate speech-induced errors.
6. Measure end of caller speech to first audible response, component timings, p50/p95, sample count, and cost per conversation/minute.
7. Do not substitute LLM-call time or downloaded-file generation time for live voice latency.
8. Inspect interruptions, disconnects, incorrect transcriptions, and partial CRM effects.
9. Freeze the two candidates' voice settings and document remaining limitations.

**Stop when:** both candidates have real audio evidence and comparable measurements. Do not claim broad voice reliability from a few sessions.

## 18. Freeze candidates before opening held-out data

1. Check that scoring, safety tests, development experiments, and audio evidence are complete.
2. Freeze code commit, model IDs, prompts, tools, handoffs, documents, retrieval, speech settings, caller, scorer, limits, and hardware/runtime details.
3. Save hashes and an exact held-out run manifest before inspecting held-out answers.
4. Estimate at least 10 held-out text scenarios, three repetitions per architecture, and the sealed paired audio subset. Include caller, judge, and retries in the estimate.
5. If this exceeds remaining credit, stop and agree on a smaller explicitly limited study before opening the test set.
6. Record the M1 decision rule: adopt multi-agent only with at least +5 percentage points on O1 or O3, statistical support, no more than +500 ms p95 voice latency, and no more than +50% cost per call. Check the full M1 definitions and protect against safety regression.
7. Plan paired scenario-level analysis and human review of every held-out outcome. Small samples may lead to an inconclusive result.
8. Ask for approval of the final batch and permission to open held-out data.

**Stop when:** the candidates/protocol are frozen and the human has approved the exact evaluation. Do not start the held-out run automatically.

## 19. Run held-out evaluation and select the architecture

1. Confirm approval, remaining balance, and frozen hashes before dispatch.
2. Run only the approved manifest. Evaluation code may use answer keys; candidate agents receive only permitted views.
3. Preserve all attempted runs. Do not tune prompts, tools, retrieval, or scoring based on held-out outcomes.
4. Stop affected runs on wrong-record writes, unauthorized actions, leaked answers, or unbounded costs. Keep evidence and explain the defect.
5. Prepare every outcome for human review with transcript, sources, tool trace, CRM diff, and machine judgment. Leave human verdicts pending until supplied.
6. Aggregate reviewed results with raw counts, paired outcomes, uncertainty, all-three-run consistency, latency, and cost. Report invalid runs and exclusions.
7. Compare results with O1–O11. Mark missing metrics as not measured rather than implying success.
8. Apply the original architecture rule. If multi-agent does not meet it, or evidence is incomplete/inconclusive, retain single-agent and explain why.
9. Write `milestones/M4_training/architecture_decision.md` and an objective scorecard.
10. Treat post-test fixes as a new version requiring fresh evaluation, or label them exploratory. Do not silently rerun until the original test set passes.

**Stop when:** the team can accept an explicit final architecture with supported results and limitations. Unresolved consequential safety failures block deployment.

## 20. Write the report and select real examples

1. Create `milestones/M4_training/report.md` using saved evidence, not expected outcomes.
2. Include dataset/preprocessing recap, complete configuration, both designs, experiments, metrics, stability/generalization, artifacts, findings, and final decision.
3. Explain that optimizer, training loss, epochs, weights, and checkpoints are not applicable without fine-tuning. Document prompts and pipeline settings as experimental variables.
4. Include a grounded answer, confirmed CRM update, safe rejection, and genuine failure. Show source IDs/text, relevant conversation, tool result, and before/after CRM effect.
5. Explain long-document behavior, unseen enquiries, hallucination controls, consent checks, and synthetic-data limitations.
6. Generate tables from saved results. Keep counts and metric definitions consistent across artifacts.
7. Verify model/pricing claims using official sources. Separate estimated/billed cost, free tiers, local compute, evaluation overhead, and excluded telephony.
8. List prompts, configs, schemas, corpus, scenarios, audio references, scripts, raw logs, results, and environment files with working links.
9. Explain the M3 judge corrections, turn limit, test-count reconciliation, and all four repeat-stop cases.

**Stop when:** each report claim has evidence or an explicit limitation. Leave missing reviews/measurements visibly pending.

## 21. Prepare slides, contributions, and acknowledgements

1. Prepare slides covering the implemented system, experiment setup, results, audio/long-document evidence, failures, final decision, and next improvements.
2. Use one presenter and one coherent narrative. Ask the team to select the presenter; do not assume a name.
3. Cross-check all counts, model IDs, limits, metrics, costs, and architecture conclusions against the report and saved results.
4. Get actual contribution statements from every member. Distinguish agent-generated code from each person's direction, review, tests, and analysis.
5. Update the contribution slide, report, and `WORKLOG.md` with confirmed work. Keep historical entries; make corrections explicit and member-approved.
6. Ask every member to add their own initials-only acknowledgement. Do not sign for them.
7. Prepare speaker notes and rehearse without unnecessary handovers.

**Stop when:** slides and report agree, contributions are confirmed, one presenter is selected, and required acknowledgements are supplied. List missing member actions explicitly.

## 22. Verify the package and stop before submission

1. Follow setup from a clean environment where feasible. Record any limitation if a clean setup cannot be tested.
2. Rebuild preprocessing, run deterministic tests/oracle/controls, and regenerate aggregate tables from saved results. Default verification must not make paid calls.
3. Review actual changes and affected callers for correctness, validation, consent, tests, and unnecessary complexity.
4. Check dependencies and `.env.example`. Inspect tracked/staged files for secrets, private environment dumps, personal data, and unapproved recordings.
5. Verify artifact paths, hashes, run counts, citations, audio files, report tables, slides, contribution records, and acknowledgements.
6. Save authentic agent conversation exports and voice-call logs. Inspect transcripts for accidental secrets; label any redactions. Confirm the required transcript format with the TA.
7. Produce a final checklist with completed items, missing items, missed targets, and known limitations.
8. Ask for explicit authorization before commit, push, or public submission. Do not change production accounts or make real calls.

**Stop when:** verification passes and a human approves the submission. If required evidence, signatures, or safety checks are missing, report the blocker instead of claiming completion.

## If something goes wrong

- Preserve the failed run and its logs.
- Identify the defect with evidence before changing code or settings.
- Fix the smallest affected component and add a regression test.
- Explain which comparisons must be repeated.
- Ask before spending more or changing a frozen evaluation contract.
- After two failed repair/check cycles for the same blocker, stop and ask for a decision.

Creating this checklist does not execute experiments, authorize spending, or prove completion. Update `progress.md` with actual checks and artifact paths as work happens.
