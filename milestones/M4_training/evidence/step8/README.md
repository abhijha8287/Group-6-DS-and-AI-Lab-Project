# Step 8 evidence

Scope: offline definition, arithmetic tests and a blocked prospective development plan. No model comparison, provider request, audio session, heldout authoring or next-milestone work occurred.

- Full M1 §5 targets and measurement rules: `../../measurement_protocol.md`.
- Fixed grid/runtime/control/implementation gaps: `../../comparison_plan.md` and `../../comparison_settings.json` with sibling checksum.
- `measurement-tests-first.json`: retained targeted import failure; fixed test import path, not application runtime.
- `unit-tests-first.{log,json}`: first complete 113-test pass and source hashes at that time.
- `unit-tests-final.{log,json}`: final post-freeze 113-test pass, zero skips, exact tested source hashes.
- `freeze-first.*`, `freeze-check.*`, `freeze-check-final.*`: real commands, outputs and exits. Integrity pass means the **blocked registration is intact**, not approved/executable.
- `freeze-refuse-overwrite.*`: second creation attempt fails with expected exit 1; no force or replacement.
- `review-resolution.md`: AI findings/corrections and limits; not human semantic or privacy approval.
- `preexisting-hashes.json`, `final-verification.json`: preservation proof, including canonical ledger and old results. Only explicit append-only progress/log updates are allowed; original prefixes are checked by hash. Earlier evidence/checksums remain historical snapshots, including their then-current progress/log hashes.
- `conversation-export.jsonl`: sanitized visible Step 8 messages/tool receipts through final verification setup; private reasoning/signatures and known environment secrets omitted. Final helper output/reply are outside that snapshot.
- `SHA256SUMS`: byte hashes for Step 8 implementation, contracts, frozen settings, new evidence, progress/log and unchanged ledger.

Reproduce offline:

```sh
python3 scripts/check_comparison_freeze.py
python3 -m unittest discover -s tests -v
```

No new metric values are asserted from missing artifacts. Full action/claim review, normalized exporter, M1 treatment, real trigger/dial/audio evidence, judge calibration and independent custody remain missing. Repeated development attempts never become independent heldout scenarios. Application usage-priced costs are estimates, not provider invoices/balance verification. Pi harness/subagent usage is separate from project API-key usage.
