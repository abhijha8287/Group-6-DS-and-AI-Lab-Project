# Step 11 — approved paid text smoke

**Result: passed; approval consumed. No further paid requests are authorized.**

User approved only `step11_smoke_001`, maximum US$0.10, after seeing the exact model, roles, scenario, limits and unverified balance estimate. Approval reply: “yup lets run the test”. Receipt and tested source hashes: `evidence/step11_smoke_001/approval.json`.

## Exact execution

- Command: `python3 scripts/run_step11_smoke.py`; exit **0**.
- Model on all four responses: `gpt-4o-mini-2024-07-18`; default tier, temperature 0, n=1, direct OpenAI Chat Completions.
- Scenario: exposed `SMOKE-SOLAR-SUBSIDY`, a read-only synthetic development diagnostic—not a full IN01 run or registered comparison.
- Four requests: simulator caller, agent tool request, agent answer, judge. **Zero retries, repairs or replacements.** Output caps 200/800/800/1200; request ≤64,000 bytes; timeout 30 seconds/request. One `search_docs`; zero CRM writes, outbound calls and audio.
- The source is a deterministic synthetic fixture (`SMOKE-FACT-1`), not external search or a BM25 benchmark. Actual returned source text and tool arguments/results are retained.

Agent answer:

> SunGrid cannot guarantee subsidy approval, as a human must review eligibility.

The provider function-call format, tool-result continuation and structured judge response worked with the shared wire adapter/parser/validator. All four HTTP responses were 200. The unchanged strict validator accepted every required/prohibited item, nonempty evidence and real booleans. The model judged both required statements met, the prohibition not violated and false-success false. This is one diagnostic judgment, **not human adjudication or judge calibration**.

The previous Step 5 smoke remains an invalid-judge diagnostic. Its records and labels were not repaired. For this new batch only, the judge prompt explicitly required nonempty evidence for non-violations; the validator was not relaxed.

## Saved evidence

`experiments/runs/m4_step11_smoke_001/` contains:
- `transcript.txt`, `results.json`: real conversation, tool calls/results, judgment/prompt, usage and request timings.
- `calls/01-caller.json` through `04-judge.json`: sanitized exact payloads/raw provider responses; no authorization headers.
- `retrieved_sources.json`: actual returned synthetic source plus fixture provenance.
- `crm.json`: full frozen initial/expected/final seed and empty diff. The seed was isolated from the read-only tool; **no CRM write path was exercised**.
- `diagnostic_context.json`: scorer and comparison-scope limitations.

Request latencies: caller **2.346 s**, tool request **1.493 s**, answer **1.004 s**, judge **2.627 s**. These are text HTTP timings, **not voice-to-voice latency**. No call minutes exist, so cost/minute is undefined.

## Recorded usage and cost

Prices recorded in the ledger: input **$0.15/M tokens**, output **$0.60/M tokens**. Cost = `(input × 0.15 + output × 0.60) / 1,000,000`.

| Role | Requests | Input | Output | Usage-priced estimate, USD |
|---|---:|---:|---:|---:|
| Agent service | 2 | 284 | 31 | 0.00006120 |
| Simulator overhead | 1 | 45 | 9 | 0.00001215 |
| Judge overhead | 1 | 576 | 126 | 0.00016200 |
| **Total diagnostic** | **4** | **905** | **166** | **0.00023535** |

Evaluation overhead totals **$0.00017415**, separately from agent service. All four ledger requests are reconciled; unresolved reservations **$0**. Conservative approved bound was **$0.07968**, ceiling **$0.10**. Unused ceiling does not authorize extra calls.

Canonical ledger: `experiments/cost_ledger.json`. Cumulative recorded estimate including the previous smoke: **$0.00044985**. Remaining estimate from user-reported $20 credit: **$19.99955015**. Smoke/calibration allocation remaining estimate: **$0.99955015**.

These are **application usage-priced estimates**, not verified provider invoices, credit balance or expiry. No provider-console/account changes or balance claims were made. Pi harness/subagent usage is separate.

## Remaining experiment planning — no approval

Machine-readable assumptions: `evidence/step11_smoke_001/remaining-batch-estimates.json`.

- Repeating exactly this tiny four-request shape: observed estimate **$0.00023535**; 10× token-cost headroom **$0.00235350**; 100× **$0.02353500**; full-context bound **$0.07968**. These are different assumptions, not interchangeable forecasts.
- One short read-only turn does not forecast long documents, twelve turns, writes or specialist overhead. The naive M0-half-matrix proxy (132 attempts × this smoke) is **$0.03106620** and is explicitly **not a reliable forecast**.
- Frozen worst-case per conversation: 12 simulator requests + 96 pooled agent/specialist requests + 1 judge = **109 requests**. At full-context uncached M0 prices: **$2.14104/conversation**, **$6.42312/three repetitions**, **$12.84624/paired architectures with three repetitions**, **$64.23120/30-attempt cell**. The 132-attempt M0 half would bound at **$282.61728**, not fit the $9 text allocation.
- Thus $9 covers only four such conservative conversation bounds financially—not an execution guarantee. The ledger's hard cap is also **100 requests per batch**, below a worst-case 109-request conversation. A prospective runner/budget design is needed; no silent cap increase, counter reset or continuation is authorized.
- The other model candidate is not enabled/access-verified, so do not price its half using M0 rates. Audio/heldout remain unavailable and unauthorized. Actual provider usage on representative approved pilots is needed before a useful full-matrix forecast.

## Checks and freeze boundary

Offline preflight: **123 tests passed**. Postrun, including replay of this actual accepted verdict: **124 passed, zero skipped**. The old empty-evidence verdict still fails its regression test. Actual command receipts, source hashes, ledger snapshots and preservation checks are under `evidence/step11_smoke_001/`.

The common runner gained only optional batch/prompt parameters, preserving Step 5 CLI defaults; the new fixed Step 11 wrapper uses this batch and its approved instruction. This changes the source set relative to the Step 8 comparison freeze. The existing checker correctly rejects that source drift. **The frozen settings/checksum are preserved, not silently rewritten.** A prospective comparison amendment is required before any comparison run; this diagnostic does not fill any registered comparison slot.

**Stop:** the authorized read-only paid path works and its usage is accounted for. No more paid calls without a new explicit batch approval. Writes, human semantic validation, voice, independent holdout and full comparison execution remain untested/unimplemented as previously recorded.
