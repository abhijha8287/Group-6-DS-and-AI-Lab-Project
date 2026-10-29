# M2: Dataset

## Three-business review pilot

**Status: Original pilot fixtures authored and accepted by independent AI judges for review-only use; human approval remains pending.** All three original pilot validators have passed. Expanded inbound and outbound datasets and a development/test review manifest have also been generated. The expanded outbound cases passed a separate static gate-consistency check.

This is a review-stage M2 dataset, not a completed M2 submission or a benchmark result. No voice calls, paid evaluations, or external CRM writes have been performed.

| Fictional business | Public fact reference | Review files |
|---|---|---|
| UrbanNest Furniture | IKEA India | [Furniture pilot](furniture_pilot/README.md) |
| SunGrid Rooftop Solar | SolarSquare | [Solar pilot](solar_pilot/README.md) |
| BrightSmile Dental Studio | Toothmate | [Dental pilot](dental_pilot/README.md) |

Each original pilot contains **12 synthetic contacts, 10 original inbound scenarios, and 5 outbound gate fixtures** (36 contacts, 30 inbound scenarios, and 15 outbound fixtures across all three businesses).

All three original offline validators have passed their implemented fixture checks. Independent AI judges rechecked the original pilot fixes; their findings and follow-up resolutions are documented in the business review files. AI acceptance is limited to review-only task authoring and does not constitute human approval, runtime safety certification, or evidence of agent performance.

Published business facts are cited, bounded paraphrases. Their adoption into each fictional business is explicitly a sandbox assumption. CRM identities, consent evidence, availability, and outcomes are synthetic. No affiliation with the reference businesses is implied, and no external benchmark tasks are redistributed.

## τ-Voice rubric and review

Read [TAU_VOICE_ALIGNMENT.md](TAU_VOICE_ALIGNMENT.md) for the inspected upstream commit, official task-reward and voice-metric distinctions, authoring checklist, custom safety gates, and measurement limitations.

Independent AI judges record findings and follow-up resolutions in:

- [FURNITURE_REVIEW.md](FURNITURE_REVIEW.md)
- [SOLAR_REVIEW.md](SOLAR_REVIEW.md)
- [DENTAL_REVIEW.md](DENTAL_REVIEW.md)

Read the latest follow-up verdicts rather than treating historical findings as current. AI acceptance is limited to review-only task authoring, never human approval or runtime safety certification.

Our target is **original task definitions aligned with the applicable end-state and communication evaluation principles**, not a claim of upstream file-format compatibility. Tool contracts, trusted identity state, and hidden evaluation fields must be explicit.

Full-duplex interaction metrics and speech-quality judges require actual run evidence and remain unmeasured. Consent, opt-out, retry, and deduplication gates are project-specific requirements, not additional official τ-Voice metrics.

## M2 review order and requirements

The review order is:

1. Review each knowledge pack, distinguishing sourced facts from invented policy choices.
2. Inspect caller goals, mock-tool contracts, and expected changes, including no-write cases.
3. Run the local validator linked in each pilot. A pass proves only the implemented fixture checks, not that an agent succeeds.
4. Resolve independent review findings and record human approval before treating the data as approved.

Full M2 requires approximately 40 inbound scenarios per business (120 total), 30 outbound cases, 50–100 contacts per business, separately authored or appropriately protected development/test data, broader scenario coverage, human source/policy review, and a milestone report and presentation.

No completed human contributions or benchmark scores are asserted here.

## M2 dataset expansion status

### 1. Dataset inventory

Three fictional business pilots are included: UrbanNest Furniture, SunGrid Rooftop Solar, and BrightSmile Dental Studio.

| Dataset component | Per business | Total | Status |
|---|---:|---:|---|
| Original pilot contacts | 12 | 36 | Existing fixtures; original validators passed |
| Expanded contact dataset | 50 | 150 | Generated; review and file inventory should be confirmed |
| Original inbound scenarios | 10 | 30 | Existing pilot fixtures |
| Expanded inbound scenarios | 40 | 120 | Generated; pending human review |
| Original outbound gate fixtures | 5 | 15 | Existing pilot fixtures |
| Expanded outbound gate cases | 10 | 30 | Generated; static gate-consistency check passed |
| Development-review partition | 28 | 84 | Manifest created |
| Test-review partition | 12 | 36 | Manifest created; not a validated held-out test set |

**Important:** The original pilot files remain separate from the expanded generated artifacts. The original validators continue to validate the original fixtures; they do not automatically validate the expanded inbound or contact datasets.

### 2. Generated artifacts

#### Expanded inbound scenarios

- `generated_scenarios/furniture_scenarios_expanded.json`
- `generated_scenarios/solar_scenarios_expanded.json`
- `generated_scenarios/dental_scenarios_expanded.json`

Each expanded inbound file contains 40 scenarios: the original 10 plus 30 generated scenarios. Generated scenarios remain pending human review and must not be treated as approved scoring fixtures.

#### Expanded outbound cases

- `generated_outbound_cases/furniture_outbound_expanded.json`
- `generated_outbound_cases/solar_outbound_expanded.json`
- `generated_outbound_cases/dental_outbound_expanded.json`

Each expanded outbound file contains 10 cases: the original 5 plus 5 generated cases. The added cases are marked for review and are not approved benchmark evidence.

#### Development/test review manifest

- `generated_splits/m2_split_manifest.json`

The manifest organizes each business's 40 inbound scenarios into 28 development-review scenarios and 12 test-review scenarios.

These are **provisional organizational review partitions only**. The generated test-review scenarios are not an independently authored or protected held-out evaluation set. This manifest alone does not satisfy the final M2 evaluation-split requirement.

### 3. Generation and validation scripts

The following scripts were used to generate or check the expanded artifacts:

- `scripts/expand_m2_scenarios.py`
- `scripts/expand_m2_outbound.py`
- `scripts/validate_m2_outbound.py`
- `scripts/create_m2_split_manifest.py`

#### Validation results

The original furniture, solar, and dental pilot validators passed their existing fixture checks.

The expanded outbound validation script reported:

- Furniture: 10 cases with matching expected gate outcomes.
- Solar: 10 cases with matching expected gate outcomes.
- Dental: 10 cases with matching expected gate outcomes.
- **Total: 30 outbound cases checked.**

The expanded outbound check compares expected gate outcomes with the static rule logic reproduced by the validation script. It is a consistency check, not a live call test or an agent evaluation. The original pilot validators have not thereby been shown to validate the expanded artifacts.

The expansion script also reported 40 inbound scenarios per business and a review manifest with 28 development-review and 12 test-review scenarios per business.

These results establish only the checks explicitly described above. They do not establish agent performance, successful real-world calls, source-rights clearance, clinical or business-policy validity, or human approval.

### 4. Review and evaluation limitations

All generated expansions remain **review-only and pending human review**.

The following limitations apply:

- Generated inbound scenarios have not yet received final human content and policy approval.
- Expanded outbound cases have passed a static consistency check, but still require review against the intended consent, allowlist, opt-out, retry, calling-hours, duplicate-event, and recent-attempt policies.
- The expanded contact dataset's exact files and review status must be confirmed before it is treated as an approved dataset.
- The development-review and test-review partitions are not a validated benchmark split.
- The test-review partition must not be described as a validated held-out test set, and its results must not be reported as benchmark performance.
- No voice calls, paid evaluations, or external CRM writes were performed during these generation and static-validation steps.
- No agent benchmark scores are claimed.

### 5. Remaining work

1. **Review inbound scenarios:** Check correctness, realism, duplication, policy boundaries, caller goals, expected CRM changes, and no-write cases.
2. **Review outbound cases:** Confirm each expected gate outcome against the intended business-specific rules and synthetic CRM state.
3. **Review contacts:** Confirm the generated contact files, record counts, schema consistency, identity uniqueness, and synthetic-data status.
4. **Review knowledge packs:** Check citations, permitted use, source-derived facts, and fictional business policy assumptions.
5. **Record human decisions:** Log the reviewer, review date, findings, corrections, and approval or rejection for each business.
6. **Establish evaluation splits:** Create a separately authored or appropriately protected held-out test set before claiming independent evaluation results.
7. **Run expanded-data checks:** Add and run checks appropriate to the expanded inbound, contact, and outbound datasets without replacing the original pilot validators.
8. **Prepare the M2 report and presentation:** Report verified inventory, validation results, review findings, limitations, and any actual agent-evaluation results. Clearly distinguish static checks from runtime evidence.

## Current milestone status

**Completed:** Original pilot fixtures and their local validation checks; generation of expanded inbound scenarios, expanded outbound cases, and the provisional review-split manifest; static consistency check of all 30 expanded outbound cases.

**Pending:** Human review and approval, confirmation of the expanded contact artifacts, review of generated inbound and outbound content, an appropriately protected held-out evaluation set, broader expanded-data validation, and the M2 report and presentation.

**Overall status: M2 dataset expansion in progress. Human approval and final evaluation readiness have not been established.**