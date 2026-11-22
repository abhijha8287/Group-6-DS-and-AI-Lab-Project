# M4 package verification (Step 22) — 22 November 2026, branch `abhishek-m4`

Verified on the local working tree, Python 3.15.2, macOS arm64. Default verification made **no paid calls**.

## Completed checks

| Check | Result | Evidence |
|---|---|---|
| Offline test suite | 170 run: 163 pass, **7 errors** (pre-existing on `srijan-m4`: `tests/test_model_pilot.py` needs the uncommitted `model_pilot_plan.md`) | `python3 -m unittest discover -s tests` |
| Oracle replay | 10/10 exact CRM states | `experiments/runs/m4_step22_verify_oracle/` |
| Negative controls | 6 blocked unsafe writes each; 1/5 write tasks (legitimate exceptions) | `experiments/runs/m4_step22_verify_control_*` |
| Outbound gate | 30/30 labels, 0 disallowed calls allowed | `experiments/runs/m4_step22_verify_gate/` |
| Development matrix | 180 cells stored; summary regenerated from saved runs (6 cells) | `python3 scripts/run_dev_matrix.py --summary` |
| Report links | All relative links in `report.md` resolve | link check |
| Secrets | No API keys in tracked or new files; `.env` is git-ignored and was never printed | pattern scan |
| Slides | `slides.pptx` validated (schema check passed) and exported to `slides.pdf`; 16 slides checked visually | this folder |
| Report ↔ slides numbers | Same counts, costs and model IDs (generated from `summary.json` and the ledger) | manual cross-check |

## Missing items (blockers for a complete M4)

- [ ] Voice Steps 15–17: team must choose cascaded vs Realtime; nothing built.
- [ ] Held-out Steps 18–19: needs ≥10 independently authored cases; 0 exist.
- [ ] Human review of judge labels (false-success flags, top-5 safety flags, M3 adjudications) and policy/relevance annotations.
- [ ] Contributions and initials from Sarwar and Omkar; Abhishek's initials and hours.
- [ ] Presenter for the slides (one presenter; to be chosen by the team).
- [ ] Prospective amendment for the comparison freeze (source drift); Srijan's Step 12 pilot to be run or re-frozen; commit `model_pilot_plan.md`.
- [ ] Clean-environment reproduction not tested (same machine only).
- [ ] Transcript/conversation-log format for submission to be confirmed with the TA.

## Missed targets and known limitations

- No metric is measured on protected data; all results are exposed development data with a gpt-4o-mini judge.
- O9 (voice latency), O10 (cost per call-minute) and WER are **not measured**.
- Repetitions are not independent; paired counts are descriptive.

**Commit, push or public submission is not authorized by this checklist and needs explicit approval.**
