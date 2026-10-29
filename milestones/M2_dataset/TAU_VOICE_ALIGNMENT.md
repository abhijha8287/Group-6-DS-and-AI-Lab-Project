# τ-Voice alignment: dataset authoring rubric

**Purpose.** Use this as a quality and evidence checklist for the three original business pilots. It maps the current τ-Voice/τ-bench implementation to this project; it does **not** make our data compatible with τ-bench, nor certify a score. No benchmark runs, traces, judge verdicts, audio, or human reviews exist for this pilot. Official benchmark criteria below are distinguished from our project-specific consent and CRM requirements.

## Pinned primary-source basis

Inspected Sierra Research's `tau2-bench` repository at **`122e2432b82d740e8f313f46f0a071729c404f39`** (HEAD obtained with `git ls-remote`; shallow checkout used to inspect files). Use commit-pinned links, not mutable `main` links:

- [Voice full-duplex docs](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/src/tau2/voice/README.md): real-time, full-duplex audio user simulator/agent; configurable speech complexity; tick-based trajectories.
- [Task evaluation docs](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/docs/evaluation.md) and [task schema](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/src/tau2/data_model/tasks.py): reward components and gating semantics.
- [Voice interaction metrics](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/docs/interaction-metrics.md) and [implementation](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/src/tau2/metrics/voice_interaction_metrics.py): trajectory-derived voice-turn metrics.
- [τ-Voice paper-aligned glossary](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/docs/glossary.md#interaction): call-level interaction and generation-quality definitions.
- [Voice-v2 publication pipeline](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/docs/voice-v2-publication.md): provenance, frozen task frame, traces, and judge evidence requirements.

The checked-out commit has these primary sources. A paper PDF was not independently located/verified in this inspection; implementation docs explicitly state the interaction thresholds align with the paper's analysis pipeline. Do not attribute unpublished or unverified rubric details to the paper.

## What the official rubric actually scores

### Task outcome (primary success)

A task's final reward is the **product** of components explicitly listed in `evaluation_criteria.reward_basis`. The schema default is `[DB, COMMUNICATE]`, but always inspect the task's explicit basis. DB success means the final database state matches the state produced by replaying a reference solution on a fresh environment; it does **not** require the exact same tool-call sequence. `actions` are a reference path, and are a hard trajectory requirement only when `ACTION` is included. `COMMUNICATE` checks each required fact (semantic judge by default at this revision; substring mode is configurable). `ENV_ASSERTION` and experimental `NL_ASSERTION` gate only when explicitly included. Fields outside reward_basis may be diagnostics, not score.

This yields the central authoring requirement: define unambiguous initial state, caller goal, available tools/environment, reproducible gold end-state, and required user-facing information. Include task-level negative outcomes (e.g. correct refusal/no mutation), not just successful writes. Every task must say which fields are reward-gating and which are diagnostic.

### Voice interaction (separate from task reward)

τ-Voice also reports interaction quality from **full-duplex tick-level trajectories**, independent of task reward and without extra judge calls: response latency `L_R` and response rate `R_R`; yield latency `L_Y` and yield rate `R_Y`; agent interruption rate `I_A`; correct handling/selectivity for backchannels, vocal tics, and non-directed speech (`S_BC`, `S_VT`, `S_ND`). Ticks default to 200 ms. A real interruption is yielded if the agent stops within 2 s. Backchannel/tic/non-directed signals are errors if the agent yields within 1 s while speaking; tics/non-directed speech during silence are errors if agent responds within 2 s. The end-of-call stop tick is excluded. Rates are supported by event counts; leaderboard suppresses rates with fewer than 10 events. Overall interaction measures average available domain values; counts sum. These require actual tick-bearing voice runs; scenario text alone cannot measure them.

Voice-v2's call-level interaction panel flags nonresponse, interruption, selectivity, monologue (>45 s floor hold), and tool misuse. The first four are trace-derived; tool misuse requires its saved judge verdict. A call fails with at least two known flags, passes if even all unknown flags could not bring it to two, otherwise is unscored. This is a separate quality diagnostic, not the ordinary task reward.

Voice-v2 generation quality (“Experience”) is also distinct: aligned agent utterances are judged for naturalness and speech fidelity. A call passes if at most 25% eligible utterances have an issue; it is unscored unless both judges completely cover/pair utterances. Missing Live transcripts are excluded as recording gaps, not silently treated as passes/failures. Judges are post-run diagnostics and do not change task reward. Do not claim this for the current pilot: there are no audio utterances or judge runs.

### Aggregation and reliability

Report task success as scored reward/pass^1 over **scored** trials, retaining infrastructure-error/unscored counts separately. `pass^k` is the share of tasks that pass in every one of k repeated trials; it measures consistency, not average reward. Preserve per-task and per-trial outcomes so aggregate percentages can be recomputed. Voice panels aggregate only where evidence/opportunities exist, include counts/coverage, and do not turn unavailable measurements into zero or success.

## Adaptation to the three pilots: author/reviewer checklist

Apply to **each** business and each scenario before expansion. A reviewer should be able to answer yes/no from the artifact, not infer author intent.

1. **Task record and reset.** Give stable task ID, business/domain, split (`dev`/`test` once created), initial CRM/environment snapshot, caller goal/persona, all caller-provided facts and when revealed, allowed tools with input/output schemas and side effects, deterministic reset, stop/termination condition, and source/version for every business fact. Distinguish reference solution from required trajectory.
2. **Gold and reward.** Specify exact allowed final-state patch and unchanged-state invariants (including unrelated contacts/fields); list required spoken facts; enumerate prohibited claims/actions; explicitly mark reward-gating state assertions and communication criteria vs diagnostics. Include valid alternative paths. For refusal, ambiguity, tool failure, and no-op tasks, gold must say what must remain unchanged and what the agent tells the caller.
3. **Realistic difficulty and reproducibility.** Caller instructions should support natural clarification, not expose gold or rubric. Include enough state/context to require correct tool choice and sequencing; avoid tests solvable by keyword-only scripts. Tool outcomes should follow declared schemas and be deterministic/replayable, with failures represented as observed tool results. Review near-duplicates and identity evidence; require the task to test safe disambiguation rather than a magic pre-verified flag unless that is deliberately the interface.
4. **Coverage by pilot.** Across the three businesses, ensure distinct domain facts/policies, tool schemas, task intents and meaningful state transitions—not merely three brand skins. Cover inbound answer/qualification, multi-turn clarification, correct update/create, identity/duplicate handling, policy-bound refusal, human handoff, failure recovery, and out-of-scope/unknown facts. Track coverage by scenario tags and state transition; keep a held-out test split that authors/reviewers do not tune against.
5. **Voice evidence (only if claiming voice quality).** Run actual full-duplex calls with tick-level speech/turn annotations and audio/transcript alignment. Include real opportunities for interruption, backchannel, tic and non-directed selectivity; report counts and missing opportunities. Record provider/model/config, speech complexity, tick duration, caller simulator/voice and run commit. Score latency/turn-taking from traces; run speech-fidelity/naturalness judges only with complete paired utterance evidence. Text-only simulations cannot support voice claims.
6. **Human QA and release.** Independent reviewer checks policy/fact correctness, ambiguity, accessibility of caller wording, tool fixture realism, gold-state minimality, leakage between splits, and reproducibility; record reviewer, date, changes and resolution. Run structural validation, then scenario-level gold replay/negative tests. Publish coverage and exclusions. A local JSON validator is not behavioral evaluation.

### Project-specific safety rubric (not τ-Voice's official rubric)

Our own required hard gates are consent/opt-out, allowed destination, calling hours, recent-attempt/retry limits, event deduplication, identity verification, and no fabricated callback/call/stock/price claims. These are appropriate custom CRM-policy criteria and should be encoded as explicit state assertions/prohibited actions plus communication facts where relevant. Do **not** describe them as official τ-Voice dimensions. In particular, legal/policy compliance is not established merely by a high τ task reward; the project must report its own hard-violation counts, with zero tolerance for disallowed outbound calls.

## Current furniture pilot: rubric gaps to fix before treating as high-quality

Repository evidence: [`furniture_pilot/README.md`](furniture_pilot/README.md), [`scenarios.json`](furniture_pilot/scenarios.json), [`outbound_cases.json`](furniture_pilot/outbound_cases.json), [`crm_seed.json`](furniture_pilot/crm_seed.json), [`knowledge.md`](furniture_pilot/knowledge.md), and [`validate.py`](furniture_pilot/validate.py).

- Existing 10 inbound cases and 5 outbound cases are a useful original draft, but have **no dev/test split**, human review, agent traces, repeated trials, audio, or scored outcome. They cannot evidence success rate, pass^k, latency, interaction, or generation quality.
- `identity_verified` and tool outcomes are fixture inputs, and `gold`/caller fields are packaged together; this is not yet a runnable agent/simulator task schema. Separate agent-visible task context from evaluator-only gold/prohibitions to prevent leakage.
- Gold patches + whole-seed reset are useful; extend the validator/replay to assert every unchanged field and outbound side effect, not only internal dataset consistency. The current JSON validator does not establish that an agent executed a task correctly.
- Existing furniture coverage is explicitly incomplete: retry-limit, recent-contact and allowlist are only seeded/validator-checked, not individually authored review scenarios; add scenarios for each and boundary/interaction combinations. There is no scored generated handoff summary, inventory tool or voice interaction opportunity.
- Fixed structured handoff reason/context is not equivalent to evaluating a generated summary. Scripted fixtures cannot establish tool reliability or naturalistic voice performance. Preserve these as pilot limitations rather than grading dimensions.
- Expand the same checklist independently for the other two pilots; do not assume furniture criteria/schema automatically cover their domain policies.

## Licensing and claims boundary

This document summarizes publicly available benchmark semantics and links to upstream source; it copies no τ-bench task, source code, task text, or benchmark data. Keep our scenarios original and retain attribution for any later reuse. Upstream repository files are under the license in its [`LICENSE`](https://github.com/sierra-research/tau2-bench/blob/122e2432b82d740e8f313f46f0a071729c404f39/LICENSE); verify that license and applicable obligations before copying any code/data. Safe claim today: “our pilot uses a related end-state evaluation pattern as inspiration.” Unsafe claims: “τ-Voice compatible,” “τ-Voice scored,” or “voice quality validated” absent a compatible runner, required artifacts, and actual independently reviewed runs.
