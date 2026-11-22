# Pilot preparation review

No inference was approved or executed during preparation. Read-only account metadata checks are not generation calls. Unit test outputs referring to complete six-slot runs are **temporary fake-HTTP fixtures**, not experiment results.

## Changes and scope

- New zero-cost-only OpenRouter adapter, fixed Gemma/free ID and Google AI Studio provider. No paid/model/provider fallback, BYOK or other endpoints. Explicit zero response cost and literal is_byok=false required; unknown evidence stops the group. Canonical ledger records every request. OpenRouter credit is not pooled into OpenAI credit.
- Existing direct OpenAI transport rejects another provider's model catalog entry. Optional journal injection records actual requests/responses with no authorization headers.
- Both arms use the same corrected nonempty-evidence judge instruction and unchanged strict validator. Historical verdicts/prompts/results are preserved, not regraded.
- Optional sandbox tool checkpoints preserve state/logs after each actual tool, before later model calls. Default old callers remain compatible; per-tool snapshots are independent copies.
- Pilot uses one current SingleAgent episode per logical attempt, with separate agent/evaluation financial sub-batches solely to preserve the existing100-request cap. No new turns/tool rounds or counter resets are added.

## AI review findings and resolution

Reviewer `7fde56c6-8692-4e2` identified:
1. Known caller-repeat errors could still trigger a paid judge. Fixed with an opt-in pilot stop rule applied to BOTH arms; noncompletion/simulator/infrastructure issues skip judgment, including initial STOP. Existing default behavior stays compatible; no historical results change.
2. Missing/unknown BYOK status was treated as not true. Fixed: require literal false; null/string/0/missing are not proof and halt.
3. Invalid approval could create an output directory before being rejected. Fixed: validate the complete approval before creating output, then revalidate at registration. No overwrite remains allowed for real started attempts.
4. Cost summary was promised but absent. Added per-attempt canonical-ledger service/evaluation subtotals, unknown request counts and request IDs; raw provider response evidence remains in journals. No invented finite cost from unknown usage.

Additional parity fix: malformed model tool-argument JSON goes through the shared parser/sandbox for both providers, not an immediate provider halt only for Gemma.

Follow-up targeted review reported all four addressed and no remaining must-fix issue in that scope. It did not run the full suite or perform network/inference, create a freeze, inspect private keys or change files. Parent full suite passed139 tests; final checks and hashes are recorded separately. This review is not independent human semantic approval, privacy custody or model calibration.

## Worktree preservation note

Final comparison against the preparation snapshot detected an additional change to `milestones/M4_training/README.md`. HEAD is now `e1b680b19586efceb21bd95021cd4bb5e2354540` (Add M4 development work, experiment results and report), rather than the earlier `4a61dedf732a2427a9cbf35ff5f9b6dff1f726d9`. The README now matches HEAD and has679 bytes. No commit/reset/restore/README edit was issued in this preparation workflow; it is left as found, not restored from a hash or overwritten. Its former/current hashes are recorded separately. README is not a pilot runtime/input source. Do not claim every preexisting file stayed unchanged; the canonical ledger, historical experiment records, old comparison seal, and all other non-amended snapshot files did stay unchanged. Current frozen source integrity and tested-source hashes are checked separately from Git history.

## Remaining limits

Single IN02 case is N=1 independent scenario; three repetitions do not make it three new cases. Human failure/dispute/coverage/action/claim review remains pending. Strict reviewed completion and factual accuracy stay null until annotated. Provider quota, strict data-policy routing, missing BYOK/cost evidence or changing aliases can stop the pilot. Never relax caps/routing or replace an attempt without a new explicit agreement. No common model is selected during preparation, and Steps13–14 are not started.
