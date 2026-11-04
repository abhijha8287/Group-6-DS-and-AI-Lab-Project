# Data

All data in this project is **synthetic** and is generated for three fictional businesses (see `milestones/M1_problem_literature/report.md`, Section 6). Raw and processed files are git-ignored; only this README is tracked.

| Folder | Contents |
|---|---|
| `raw/` | Business knowledge documents (catalogue, FAQs, policies, hours, qualification rules), CRM seed records, consent/opt-out records |
| `processed/` | Chunked + embedded knowledge base, normalised CRM seed SQL |
| `splits/` | Scenario suite split into `dev` (prompt iteration) and `test` (held out for final comparison) |

The committed Milestone 2 dataset (pilots, generated contacts, scenarios, outbound cases and split manifest) is in [`milestones/M2_dataset/`](../milestones/M2_dataset/README.md), with the report at [`milestones/M2_dataset/report.md`](../milestones/M2_dataset/report.md). Generation scripts are in `scripts/`.
