# Step 5 review resolution

Review scope: new budget module and model transport, their caller/judge/CLI integrations, runtime caller/tool caps, and offline cost tests. Previous Step 4 changes were not re-reviewed as a new feature. No project model request was sent.

## Concrete findings and fixes

1. **Failure + halt were separate ledger writes.** `fail(..., halt=True)` now records both in one locked atomic save. A competing reservation test confirms the next worker sees the halt, not an intermediate failed-but-open state.
2. **A successful HTTP response with a non-object JSON root did not halt.** Non-object roots now fail/halt atomically. JSON syntax/decode failures halt through the nonretryable error path. Full reservation stays held. Regression cases: `[]`, `null`, and invalid JSON.
3. **Atomic replacement alone was not a persistence barrier before dispatch.** Ledger saves now sync the file and parent directory while holding the lock. Tests assert sync → sync → HTTP ordering and no HTTP on either file-sync or directory-sync failure. This is not a physical power-loss test; OS/device semantics still apply.
4. **A shared paid-run ledger rejected a genuinely local caller.** Recognized loopback Ollama requests now use zero-provider-cost transport while retaining the run's caller/tool limits. A mixed local simulator/paid agent test checks that only the paid request consumes the currency ledger. Local cloud proxies are not authorized.
5. **A failed halt write could leave only a pending reservation.** The ledger now admits only one in-flight paid request, across all batches. Pending entries block later reservations. The regression injects a halt-write failure after the mocked paid response, restores I/O, then checks that a separate ledger instance cannot send again.
6. **Parent hardening:** a halted batch also blocks other approved batches until billing review. This prevents another pre-approved batch from proceeding with unresolved billing assumptions. Cross-batch regression added.

Tool-step rejection records the actual discarded model text and requested calls in the error trace. Tests count parallel calls, not only LLM/tool rounds. Budget refusals are tested as infrastructure/evaluation errors, with deterministic CRM state retained and reward unknown.

## Verification and review boundary

- Full deterministic suites: 66/66, then 70/70, then 72/72, finally **73/73**, no skips and exit 0. Every output/receipt is retained.
- Final tested Python-source hashes: `checks-final-stop.json`.
- The independent reviewer checked the first fixes and identified finding 5. Findings 5–6 were then fixed, inspected by the parent and tested; there was no additional independent post-fix approval. The review conversations are retained as evidence, not a human approval.
- No paid API, model availability, real usage, voice, phone, provider-console or physical crash test was run.

## Remaining bounds and risks

- Model-token arithmetic assumes the documented model/context, unchanged prices and requested default tier. A provider violating these assumptions could already have billed a different amount before the response is checked. This is not a provider-enforced billing cap.
- One canonical ledger cannot account for unrelated key use or copies/older restored ledgers. Operator edits must not run concurrently with workers. Approval records are not cryptographic proof of human authorization.
- The user's $20 balance/expiry is not authenticated. The selected text snapshot is deprecated and live access is unknown. No fallback is approved.
- Audio duration alone does not bound Realtime spend. Audio remains disabled, not provisionally covered by a guessed per-minute figure.
