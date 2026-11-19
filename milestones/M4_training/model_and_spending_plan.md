# Step 5 — verified model options and spending controls

Access date for all sources below: **2026-11-19**. Prices are USD, standard API rates unless stated otherwise. During the original verification, public documentation was fetched and **no project paid model, voice, telephony, or account-balance request was made**. The later explicitly authorized text smoke is recorded in the execution update below. Pi conversation/research/review usage is separate from this project's API-key ledger. These checks establish documented options, not access on this account or model quality.

## Existing client and compatibility

`src/voice_agent/models/llm.py` uses standard-library HTTP, not a provider SDK:

| Adapter / configured provider | Wire format | Tool calls and results |
| --- | --- | --- |
| OpenAI-compatible: `openai`, `groq`, `ollama` | `POST /chat/completions` below the configured base URL | Request `tools[].type=function`, JSON Schema parameters; assistant `tool_calls[].function.{name,arguments}` with JSON-string arguments; replies use `role=tool` and `tool_call_id`. |
| `anthropic` | `POST /v1/messages` | `tools[].input_schema`; assistant `tool_use` blocks with object `input`; user `tool_result` blocks with `tool_use_id`. Parallel results share one user turn. |

The internal message format normalizes tools to `{id,name,arguments}`. Malformed function-argument JSON becomes `_unparsed` for sandbox validation. Chat Completions JSON mode is supported; it is not a substitute for Step 4 verdict validation. Anthropic's `json_mode` argument has no implementation. There is no Responses, streaming, Realtime/WebRTC/WebSocket, STT, TTS, LiveKit or telephony implementation.

**Wire compatibility does not authorize spending.** Paid execution is now restricted to the exact direct OpenAI Chat Completions endpoint and an explicitly approved, priced text batch. Groq, Anthropic, custom remote endpoints, hosted tools, images and audio are blocked. Their adapters remain available for offline wire-format tests. Local Ollama remains available at loopback port 11434, with zero automatic retries. HTTP redirects are disabled.

## Verified models and prices

### Affordable text candidate for the first diagnostic

Source: [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini), cross-checked against [official API pricing](https://developers.openai.com/api/docs/pricing).

- Pin **`gpt-4o-mini-2024-07-18`**, not the moving alias `gpt-4o-mini`.
- Input **$0.15 / 1 million text tokens**; output **$0.60 / 1 million text tokens**. Cached input is $0.075 / million; the ledger deliberately assumes **no cache discount**.
- Documented context window: **128,000 tokens**. Documented model output maximum: **16,384 tokens**. Application output maximum: **1,200 tokens**, including tool-call arguments.
- Chat Completions, function calling and structured outputs are documented. The client now sends `max_completion_tokens`, `n=1`, and `service_tier="default"` to direct OpenAI.
- [Chat Completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create): `max_completion_tokens` bounds generated tokens; `max_tokens` is deprecated. Exact live parameter acceptance and account access remain untested.
- **The official page marks this snapshot deprecated.** This is a low-cost compatibility/calibration candidate, not a long-term model commitment. If unavailable, stop; do not silently substitute a model, endpoint or price. No nondeprecated text replacement was selected or certified in this step.

For comparison, [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), snapshot `gpt-4.1-mini-2025-04-14`, is documented at $0.40 input / $1.60 output per million text tokens, 1,047,576 context, and is also marked deprecated. It is **not enabled** in the cost ledger. Model choice and judge accuracy still need calibration, not inference from price or schema validity.

### Feasible speech options by documentation — execution remains blocked

All token prices in this table are **per 1 million tokens**, not per minute. No audio model is enabled in the ledger.

| Purpose and exact ID | Documented price | Status / qualification |
| --- | --- | --- |
| Direct speech-to-speech candidate: [`gpt-realtime-2.1-mini`](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini) | Text input/output **$0.60 / $2.40**; audio input/output **$10 / $20**. Cached input: text $0.06, audio $0.30. | Official default snapshot has the same ID; no separate dated snapshot listed. Audio/text input and output, function calling, 128,000 context and 32,000 max output tokens documented. This stays within the approved direct OpenAI Realtime family; it is a candidate, not a new deployment. |
| Original Realtime reference: [`gpt-realtime-2025-08-28`](https://developers.openai.com/api/docs/models/gpt-realtime), alias `gpt-realtime` | Text input/output **$4 / $16**; audio input/output **$32 / $64**; cached input $0.40 for both. | Deprecated. LiveKit plugin's documented default is still `gpt-realtime`; future setup must select a reviewed model explicitly, not inherit that default. |
| Separate STT: [`gpt-transcribe`](https://developers.openai.com/api/docs/models/gpt-transcribe) | **$0.0045 / audio minute**, model page's audio-duration pricing unit. | File and Realtime input transcription documented. Default snapshot has the same ID. Not integrated or enabled. |
| Separate STT comparison: [`gpt-4o-mini-transcribe-2025-12-15`](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe) | Model/pricing tables list **$1.25 input / $5 output per million tokens**; pricing page estimates **$0.003 / minute**. | Deprecated; transcription guide gives shutdown **2027-02-26**. Do not turn the estimated minute rate into a hard token-cost bound. |
| Separate STT fallback: [`whisper-1`](https://developers.openai.com/api/docs/models/whisper-1) | **$0.006 / minute** | Deprecated; documented shutdown **2027-02-26**. |
| Separate TTS: [`gpt-4o-mini-tts-2025-12-15`](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts) | **$0.60 / million text input tokens**, **$12 / million audio output tokens** | Deprecated; TTS guide gives shutdown **2027-01-06**. Not a long-term recommendation. |
| Separate TTS fallback: [`tts-1`](https://developers.openai.com/api/docs/models/tts-1) | **$15 / 1 million input characters** | Character pricing is not token pricing. Deprecated; documented shutdown **2027-01-06**. |

Additional official sources: [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text), [TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech), [Realtime cost guide](https://developers.openai.com/api/docs/guides/realtime-costs), [API pricing](https://developers.openai.com/api/docs/pricing).

Separate STT → text agent → TTS is an alternative architecture, not an automatic extra charge in a direct speech-to-speech session. Optional Realtime input transcription can add charges. The Realtime cost guide describes approximate audio-token rates and repeated history per response; **input duration alone does not bound output, repeated context, response count, retries or optional transcription**. Newer reasoning-capable Realtime models need model-specific accounting as well. Therefore the present hard audio limit is **0 seconds / 0 audio requests**. The $4 allocation is not permission to run an unbounded session.

## Local development and LiveKit readiness

Actual checks are in `evidence/step5/environment.json` and `environment-followup.json`:

- Python 3.15.2 is available. No Ollama executable or responding `/api/tags` at `127.0.0.1:11434`; no Ollama or LM Studio app found in `/Applications`.
- No `livekit-server` or `lk` executable; `127.0.0.1:7880` refused connection. Python distributions `livekit`, `livekit-agents`, `livekit-plugins-openai`, `openai` and `tiktoken` are absent in this interpreter.
- Docker is available/running, but no matching local-model/LiveKit container was found. Other running services were left untouched.
- OpenAI key presence was checked without displaying its value. LiveKit/Deepgram/Cartesia configuration was absent in the checked environment. Presence is not authentication or a credit-balance check.
- No runtime, SDK or model weights were installed or downloaded. Use deterministic oracle/sandbox checks and mocked completions now. Do not call a remote API and label it a local test. After a truly local Ollama model is installed, a local caller or judge can share a run with paid roles; only paid attempts enter the currency ledger. Do not route “local” endpoints to paid cloud models.

[LiveKit local setup](https://docs.livekit.io/transport/self-hosting/local/) documents `brew install livekit`, then `livekit-server --dev`, bound to `127.0.0.1:7880` by default. These commands were **not** run. Development credentials in that page are public examples, not production credentials.

[LiveKit OpenAI Realtime plugin](https://docs.livekit.io/agents/models/realtime/plugins/openai/) documents the direct plugin with `OPENAI_API_KEY`, Python installation `livekit-agents[openai]~=1.8`, and distinguishes it from **LiveKit Inference**, which uses LiveKit credentials and is billed by LiveKit Cloud. The current Python 3.15 environment's package compatibility is not verified; do not install dependencies blindly.

**Cost ownership:** local self-hosting does not use LiveKit Cloud session allowances, but still uses local compute/network resources. Hosted servers, LiveKit Cloud transport/agent hosting/Inference, Deepgram, Cartesia, SIP carriers, phone numbers and telephony minutes have separate billing. **The $20 OpenAI credit does not pay those bills.** [LiveKit pricing](https://livekit.io/pricing) advertises 1,000 free agent-session minutes monthly, but this does not mean unlimited free transport, inference or telephony; plan eligibility, quotas and overages were not activated or verified. No Cloud plan or non-OpenAI service is approved. Deepgram/Cartesia and all real outbound calls remain deferred.

## Ledger and enforcement

Canonical file: **`experiments/cost_ledger.json`**. Starting credit is the user's reported $20, not an authenticated balance or verified expiry. The table is the **pre-approval planning snapshot**; see the execution update for current usage. These are planning ceilings, not per-batch authorization:

| Allocation | Ceiling | Approved paid batches | Recorded usage / unresolved reservations |
| --- | ---: | ---: | ---: |
| Smoke tests/calibration | $1 | 0 | $0 / $0 |
| Text development, including caller and judge | $9 | 0 | $0 / $0 |
| Audio experiments | $4 | 0 | $0 / $0 |
| Held-out evaluation | $4 | 0 | $0 / $0 |
| Reserve — explicit approval only | $2 | 0 | $0 / $0 |
| **Total** | **$20** | **0** | **$0 / $0; $20 estimated remaining** |

`CostLedger` uses Decimal arithmetic, a cross-process lock and atomic replacement. Each save syncs the ledger file and directory. A reservation is persisted **before each actual HTTP attempt**. No SDK retry or redirect can send an uncounted request. Lock/sync/write errors fail closed. There is only **one in-flight paid request across the ledger**; unresolved pending requests block later sends, including after a crash or failed halt update. A halted batch also blocks other approved batches until billing review. Recovery needs reconciliation, not deletion/reset of the ledger. Do not delete its lock, copy/restore an older ledger, or edit approvals/ceilings while workers are active. A new run ID does not reset budget or request counts.

Requirements for a paid request:

1. Batch exists, is explicitly approved, and has a nonempty approval reference to the user's authorization. The current proposed batch has `approved=false`; all paid calls are blocked.
2. Exact model matches its catalog entry; endpoint is direct OpenAI Chat Completions; text-only, one completion, standard/default tier, local function tools only. Returned model and tier must match before usage reconciliation.
3. Reserve **full documented input context × uncached input rate + capped output × output rate**. This is intentionally larger than an expected bill and needs no tokenizer guess. The request-byte limit is a separate payload-size cap, **not** a claimed token-count estimator.
4. Check global credit, allocation, batch dollar cap, request count and retry count under the same lock. Each HTTP retry consumes another request and reservation, even if no response arrives.
5. Reconcile only real nonnegative integer `prompt_tokens` and `completion_tokens` within reserved bounds. Cached discounts are ignored. Failed/lost requests keep the full reservation; missing/invalid usage or unexpected model/tier halts the batch. Nonretryable transport failures and successful HTTP responses with malformed JSON syntax or a non-object JSON root halt too. A schema-invalid judge verdict is a separate evaluation error; valid token usage can still be reconciled. Errors remain infrastructure/evaluation issues, not ordinary zero-reward model failures.

| Limit | Hard application maximum | Proposed first smoke |
| --- | ---: | ---: |
| Paid HTTP attempts across agent/caller/judge/retries | 100 per batch, plus dollar ceilings | **4 total** |
| Output tokens, including tool arguments | 1,200/request | Caller 200, agent ≤800 each, judge ≤1,200; hard global cap 1,200 |
| Input | Model's documented 128,000-token context upper bound used for reservation; serialized request ≤256,000 bytes | ≤64,000 serialized bytes; reserve all 128,000 input tokens regardless |
| Caller generations | ≤12/episode; paid batch can lower it | **1**, enforced by this batch's limit |
| Agent tool rounds | 8/caller turn | Diagnostic has one read-only tool result |
| Actual executed tool calls, including parallel calls | ≤8/caller turn; paid batch can lower it | **1**, enforced by this batch's limit; expose one read-only tool |
| HTTP retries | ≤1, each separately reserved; default 0 | **0** |
| Audio | **0 seconds / 0 requests** | **0** |

The generic M3 pipeline accepts `--budget-batch APPROVED_BATCH_ID` and passes the same ledger to all roles. It records batch IDs in new run manifests. Do **not** use a full ten-task pipeline as the proposed four-request diagnostic. Historic `tokens_*_agent_plus_simulator` summary fields still exclude the judge by design; the **cost ledger**, not those fields, is the accounting source for all paid roles and retries. Local-model usage is separate, zero-provider-cost development usage, with existing finite episode/turn/tool loops.

Limits are application-side bounds for this project's one canonical ledger. They do not cover API-key use outside this client, another checkout/ledger, external account spending, taxes, price changes or a provider violating requested model/tier/token limits. Unexpected model/tier usage could already have been billed before the response is checked. Verify prices again before approving later batches, and check the provider balance/expiry separately. No provider-console hard cap was configured or claimed. Filesystem durability depends on the OS/device honoring sync operations; this is not a multi-file transaction or a hardware power-loss test. Approval references are audit records, not cryptographic proof of human authorization; automation must never self-approve or edit ceilings to bypass a refusal.

## Proposed next paid action — approval required

**Batch `step5_smoke_001`: synthetic four-request text diagnostic, maximum authorization $0.10 from the $1 smoke allocation.**

1. One caller request: generate a single synthetic Solar question (≤200 output tokens).
2. One agent request: request a read-only `search_docs`-style local function (≤800 output tokens). Expose no CRM write/export tool.
3. Execute at most that one local read-only function, then one agent follow-up request using its result (≤800 output tokens). Stop early on malformed, missing or multiple requested tool calls; do not generate extra requests to “fix” them.
4. One judge request: return the complete structured verdict for the diagnostic's explicit rubric (≤1,200 output tokens). Validate it with Step 4 validation. This is a compatibility/calibration check, **not a regrade or held-out score**.

Purpose: confirm snapshot access, bounded Chat Completions parameters, function-call round trip, caller behavior, structured-judge parsing and usage accounting. Retain actual prompts/messages, raw responses, verdict attempts, command/log/exit status and ledger entries in a **new** run directory. No original scenario labels or human adjudications change. There will be no retry, audio or telephone call.

Conservative uniform bound (even though not every request uses 1,200 output tokens):

```text
per attempt = (128,000 × $0.15 + 1,200 × $0.60) / 1,000,000
            = $0.019920
four attempts = $0.079680 < $0.100000 authorization ceiling
```

The cap, not an optimistic expected token count, governs approval. Recorded usage may be much lower; an unavailable model may fail early and leave its conservative reservation held. No substitute model is authorized. **Ask the user to approve this named batch and ceiling before changing its approval fields or running any paid request.**

## Offline verification and stop boundary

Tests cover exact cost math; unapproved/unknown models; per-request, batch, allocation and total limits; all paid roles; actual HTTP retries; lost/invalid usage; unexpected tiers/models; malformed successful responses; pre-send write/sync failures; concurrent reservation/halt; a failed halt write recovered by another instance; local/paid mixtures; actual parallel tool-call counts and reduced caller limits. HTTP is mocked; no credits are consumed. Final test and command receipts are under `evidence/step5/`. Historical runs are hash-checked, not regraded.

**Original stop boundary: pending paid-smoke approval.** Audio implementation/experiments, model-quality claims, held-out evaluation, provider-console changes and real outbound calls are outside this step.

## Execution update — explicitly authorized text smoke, 2026-11-19

The user selected **“Paid smoke — maximum $0.10”**. Approval was recorded before dispatch in `evidence/step5_smoke_001/approval.json` and the canonical ledger. Command: `python3 scripts/run_text_smoke.py --run-id m4_step5_smoke_001`.

- Four paid requests, all HTTP 200, expected snapshot and default tier; no retries. Caller and one read-only local fixture tool round trip worked. This confirms model/parameter access at that time, not future availability or model quality.
- The judge produced valid JSON but an **invalid verdict**: prohibited item 1 had empty evidence. The strict validator rejected it. CLI exit **1** is intentional evidence of the diagnostic failure; no accepted language reward was produced. The model used 109/1,200 judge output tokens and finished with `stop`, so increasing the token limit is not justified by this result.
- Usage: **834 input / 149 output tokens** across caller, agent and judge. Recorded uncached token-priced cost: **$0.00021450**; unresolved reservations **$0**. Estimated remaining credit **$19.99978550**; smoke allocation remaining **$0.99978550**. These are not authenticated provider balances/invoices.
- Offline runner preflight: **80 tests passed**. Post-run regression suite, including replay of this actual rejected verdict: **81 tests passed**, zero skips, exit 0. Those tests made no paid requests.
- Actual conversation and raw request/response journals: `experiments/runs/m4_step5_smoke_001/`. Receipts, approval and cost/preservation summaries: `evidence/step5_smoke_001/`. Original benchmark runs and pending human adjudications are unchanged.

**This batch is consumed: zero requests remain authorized.** No automatic repair, replacement model or weaker validator was used. A revised judge calibration and any further paid batch need a new plan and explicit approval. Audio/telephone work remains blocked.
