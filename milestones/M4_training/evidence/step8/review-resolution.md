# Step 8 technical review and corrections

AI technical review is not human semantic approval, independent holdout review, judge calibration or execution permission. No provider/network requests, new heldout cases or audio runs were involved.

## Initial review

Reviewer `92b1b44f-7c99-40c` compared the full M1 §5 objectives and confirmed all original numerical targets were retained. It reported three important issues:

1. **Insufficient matrix validation.** The initial checker verified shape/hash/runtime but could accept changed scenario/model/count or nested authorization values before sealing. Corrected: compare the complete settings against the registered plan using sorted JSON serialization, after membership/hash/runtime gates. This also preserves JSON type distinctions. Totals are derived from checked cells. Regression tests change model, scenario, temperature, targeted count and nested voice/heldout authorization, plus repetition slots, hash/membership/runtime and top-level authorization.
2. **Final state is not a complete write audit.** A bad write can be reversed. Corrected: retain all-task and write-task exact-state accuracy, but separately require complete reviewed action scope and no spurious committed writes for original M1 O2 accuracy. Undoing a bad write does not erase it. Unknown audit means unknown original O2, even if exact state is known.
3. **Escalation unit mismatch.** Counting suggestions over cases could exceed 100%. Corrected: one binary prediction per attempt, explicit TP/FP/FN/TN, repeated suggestions count once; suggestions remain separate from persisted handoffs.

The reviewer initially ran 13 focused offline tests, passing. Its follow-up verified the three corrections and ran 14 focused tests, passing. These are arithmetic/integrity tests, not measured model outcomes.

## Follow-up terminology finding

The reviewer found inconsistent cost wording after the estimate basis was clarified. The parent replaced “observed actual subtotal” and the remaining cost-row wording with **observed usage-priced subtotal / application estimate**, keeping reservations separate and invoice reconciliation distinct. This final wording correction was parent-checked; no further independent approval is claimed.

Other parent clarifications retained before sealing: preserve Unicode combining marks in WER; exact critical-field canonical rules; explicit queue/immediate-call eligibility and 60-second deadline; literal M1 already-contacted calls versus sandbox 24-hour retries; one primary architecture pair for the two-endpoint Holm family; actual audible speech rather than model or transport timestamps; source/caller/action claim scopes; draft annotation and telemetry gaps.

## Attempts retained

The first targeted measurement-test invocation failed at import because the new test lacked this repository's `src` path setup. Receipt: `measurement-tests-first.json`. Fixed using the existing test pattern, not a runtime/package change. The first full suite passed 113 tests; its receipt and tested hashes are preserved separately from final post-freeze checks. Freeze creation/check and overwrite-refusal commands also have separate logs and exit receipts.

No historical scores, policy/data inputs, pending adjudications, canonical ledger or user README/prompts were changed. The existing progress and experiment-log files receive explicit Step 8 append-only entries. Any future runtime implementation, annotation approval or model change needs a prospective amendment before new comparison observations; never silently rewrite this seal.
