# Frozen comparison plan — m4-comparison-v1

This is a prospective development plan, **not permission to run it**. All cells are blocked. The ten original cases, six targeted cases and all old review partitions are exposed development data. No independent test cases or audio runs exist. Earlier exploratory runs and the four-request paid diagnostic are not results of this plan.

Read `measurement_protocol.md` for the complete M1 O1–O11 targets, definitions, denominators, missing-data rules and decision analysis. `comparison_settings.json` is the machine-readable plan; its sibling `.sha256` seals its bytes. Changing both is possible for a filesystem owner: this is an audit trail, not independent custody or a security boundary.

## Fixed matrix

| Model index | Agent and all specialist model snapshot | Status |
|---|---|---|
| M0 | `gpt-4o-mini-2024-07-18` | Deprecated; access was demonstrated by the earlier diagnostic, not guaranteed for future runs |
| M1 | `gpt-4.1-mini-2025-04-14` | Deprecated candidate; not enabled in the paid cost catalog, access unverified |

The model index M1 is distinct from **architecture M1**, the multi-agent treatment.

Each model has these four core cells:

| Architecture | Document | Scenarios | Repetitions | Attempts per model |
|---|---|---|---|---:|
| B0 single-agent | short | IN01–IN10 | 1, 2, 3 | 30 |
| B0 single-agent | large | IN01–IN10 | 1, 2, 3 | 30 |
| M1 multi-agent | short | IN01–IN10 | 1, 2, 3 | 30 |
| M1 multi-agent | large | IN01–IN10 | 1, 2, 3 | 30 |

**Eight cells, 240 planned core attempts, ten unique scenarios—not 240 independent scenarios.** All cells start with the complete frozen seed, retaining contacts and history. Only the case's frozen `snapshot_at` may change. For the core document axis, substitute only the chosen frozen public document; keep callers, gold, fixture results and clocks identical. A future runner must support and attest this substitution: the existing M3 CLI does not implement this plan.

**Targeted validation:** DEV11–DEV16, one repetition per model/architecture, **24 additional attempts**. Use each case's assigned short/large document; never run a long-only case against the short document. These are regression checks, not an extra model-quality sample, and do not enter core rates or three-run consistency. Total planned development slots: **264**. This is not a cost estimate or a promise that the $9 text allocation can complete them.

Comparisons fixed before execution:
- Architecture: B0 versus M1 within the same model/document.
- Model: M0 versus M1 within the same architecture/document.
- Document size: short versus large within the same model/architecture.
- Report every registered cell and its coverage, not just favorable pairs.
- The single **future O11 primary architecture pair** is `M0-B0-short` versus `M0-M1-short`. Other development pairs are sensitivity analyses, not additional adoption tests. O11 still requires a new protected-set/runtime amendment and real voice/cost evidence. No development p-value authorizes adoption.

## Shared controls

- Caller and judge: direct OpenAI Chat Completions, `gpt-4o-mini-2024-07-18`, temperature 0, default service tier, `n=1`; caller output cap 200, judge 1200. Agent and specialist output cap 800. No requested API seed; temperature zero is not a determinism guarantee. No model/provider fallback.
- Caller: hash-pinned `LLMCaller` prompt, same exposed persona/goal/provided fields and full mirrored dialogue per scenario; no private evaluator/harness fields. Goal-permitted confirmations start `Yes, I confirm`; refusals start `No`. `###STOP###` ends the dialogue; the current empty-output-to-STOP rule is retained and must be counted, not silently fixed mid-comparison.
- Limits: 12 caller generations per episode; eight agent-model calls, eight tool rounds and eight executed tool calls per caller turn. All specialists share the model/tool caps with the coordinator. No extra specialist budget. Zero HTTP retries, judge repairs, replacement scenarios or replacement repetition slots. Timeout 30 seconds, request size cap 64,000 bytes; sequential execution, concurrency one. Caps are not a paid batch authorization; the future batch must set corresponding request and dollar ceilings in the existing ledger.
- Retrieval: existing BM25 `k1=1.5`, `b=0.75`, top-k 3, stable document order on ties. Agent retrieves fact chunks; policies are supplied in the system prompt, identically for both architectures. Standalone retrieval analysis uses all fact/policy chunks and k=1,3,5,10, clearly separated from agent-path recall. No embeddings, reranking or document additions.
- Shared tool schemas, trusted identity binding, CRM registry, confirmation and safety validation; no direct worker writes or broader permissions. Same frozen business clock in Asia/Kolkata; no real-time business-rule clock.
- Scorer: `m4-metrics-v1`, hash-pinned evaluator, judge prompt, null propagation, metric arithmetic and this protocol. Invalid judgments stay invalid; no repaired verdicts or retroactive historical labels. Reviewed annotations are a separate versioned layer, never edits to transcripts or original scores.
- No tuning, prompt changes or observed-case additions between paired cells. Raw requests/responses, usage, all attempts and per-metric invalid reasons are retained. No existing run directory is overwritten.

Fixed order: repetitions 1→2→3; core IDs in manifest order; short then large; model M0 then M1; B0→M1 on odd core positions and M1→B0 on even positions. Targeted validation follows, in targeted-ID/model/architecture order. On an interruption, retain pending slots and resume only through an explicitly approved continuation that preserves slot identity. No hidden replacement runs.

## Treatment contract, not an implementation claim

B0 is the existing `SingleAgent`, which calls shared tools directly. M1 is a sequential conversation coordinator with knowledge, qualification and CRM/handoff-planner specialists, all using the cell's agent model. No parallel workers or worker-to-worker communication.

The coordinator requests knowledge help for factual questions, qualification help for lead qualification, and a CRM plan before any write (including opt-out). Applicable order: knowledge, qualification, planner. Knowledge returns an answer proposal and public source IDs; qualification returns observed known/missing fields; planner returns proposed existing-tool arguments and missing authorization. Specialists see only role-relevant observed facts, public policies and authorized tool observations—not simulator goals, fixtures, rubric, gold or trusted identity bypasses. The coordinator alone executes proposed calls through unchanged sandbox validation. Any omitted required delegation is logged as a treatment-adherence issue; do not reclassify that episode as a single-agent run.

**M1 does not exist yet.** Exact treatment prompts, response schemas, dispatch implementation and the normalized measurement exporter must be code-frozen in a prospective version before its first run. Keep the registered data, controls and comparisons unless a reasoned amendment is filed before seeing new comparison results. This v1 does not pretend that unimplemented code was frozen.

## Runtime and evidence

The JSON records the current exact Python version/implementation, OS family and machine architecture, plus hashes of every current `src/voice_agent/**/*.py` and `scripts/*.py` file. It also pins the M1 report, metric/comparison contracts, selected named development inputs/public guides, and draft relevance/source annotations. New or removed source files cause membership drift before they are opened by the checker. This does not freeze every OS library or prove host timing stability; a prospective execution attestation must record OS/build, CPU/load, network/region, wall/monotonic clocks and all installed package versions. Pair cells on the same host/network setup, record changes, and invalidate timing comparisons if the controlled environment differs.

Per attempt save: exact effective settings/client/model/service tier, source and input hashes, scorer/annotation versions, raw prompts and results (including worker delegations), full initial/expected/final states, ranked retrieval/context supplied before each claim, validated rubric and reviewer labels, typed action/claim/handoff/STT/audio/event records, cost request IDs and duration clocks. The measurement protocol defines the record fields. Configuration and implementation drift is not an agent failure; it makes the affected comparison nonconforming. Never infer a missing measurement from an empty array without an explicit complete-observation flag.

Run the **offline integrity check only**:

```sh
python3 scripts/check_comparison_freeze.py
python3 -m unittest discover -s tests -v
```

Initial creation uses `--freeze` once. It refuses an existing settings file or checksum. There is no `--force`, dispatch mode, API client or ledger mutation. Preserve v1 and its receipts; any later revision needs a new version/path and an explicit before-results rationale. Pinning a file is not permission to execute it.

## Blockers and excluded work

- No paid batch is approved. `step5_smoke_001` is consumed. The $9 text allocation and other allocations remain planning ceilings, not permission or provider guarantees. Every future paid batch needs explicit approval, model/pricing checks, conservative reservations and role/request/cost caps in `experiments/cost_ledger.json`. No second ledger, automatic refill or substitution.
- Source, scenario, relevance and escalation/critical-field annotations need human review; the judge needs calibration and adjudication. Existing outputs do not contain all normalized evidence required by this protocol.
- The comparison runner/exporter and M1 treatment are absent. A successful integrity check means **the blocked plan is intact**, not ready to run.
- Voice is outside v1's matrix. Metric definitions are fixed, but voice model snapshot, LiveKit/SDK/build, output voice, VAD, codec/sample rate, caller synthesis, STT/reference policy implementation and playback timing must be prospectively registered and verified before voice experiments. The previously chosen direction remains local LiveKit plus direct OpenAI Realtime, not a newly substituted cascade.
- Protected holdout remains deferred: zero actual text/audio cases, no author/reviewer/custodian. A future ≥10 text +3 separate audio plan is not an implemented dataset or private store. No held-out answers are needed or accessed here.

**Stop:** definitions and the development comparison grid are fixed before new runs; execution and final architecture adoption remain blocked. Nothing in this step authorizes the next milestone.
