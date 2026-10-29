# M2: Dataset — work in progress

**WIP: this branch contains our initial dataset pilots, not the completed Milestone 2 submission.** We will finish the dataset quality/coverage analysis, document preparation and split/leakage strategy, complete teammate source/policy review, and add the milestone report, contribution updates and review slides. The larger dataset scope proposed in M1 remains outstanding unless explicitly revised and justified in the M2 report. Pilot validation and AI review do not mean the milestone is complete.

## Three-business review pilot

**Status: all three pilots authored and accepted by independent AI judges as review-only datasets; no required review findings remain. Human approval is pending.** This is a pilot, not the full M2 submission or a benchmark result. No voice calls, paid evaluations or external CRM writes are made.

| Fictional business | Public fact reference | Review files |
|---|---|---|
| UrbanNest Furniture | IKEA India | [Furniture pilot](furniture_pilot/README.md) |
| SunGrid Rooftop Solar | SolarSquare | [Solar pilot](solar_pilot/README.md) |
| BrightSmile Dental Studio | Toothmate | [Dental pilot](dental_pilot/README.md) |

Each pilot contains **12 synthetic contacts, 10 original inbound scenarios and 5 outbound gate fixtures** (36 / 30 / 15 total). All three offline validators have passed. Independent judges rechecked the fixes and rejected the tested malformed-fixture controls; see their latest follow-ups below. Published business facts are cited, bounded paraphrases; adoption into a fictional business is explicitly a sandbox assumption. CRM identities, consent evidence, availability and outcomes are synthetic. No affiliation with reference businesses is implied, and no external benchmark tasks are redistributed.

## τ-Voice rubric and review

Read [TAU_VOICE_ALIGNMENT.md](TAU_VOICE_ALIGNMENT.md) for the inspected upstream commit, official task-reward/voice-metric distinctions, authoring checklist, custom safety gates and measurement limitations. Independent AI judges record findings and follow-up resolutions in [FURNITURE_REVIEW.md](FURNITURE_REVIEW.md), [SOLAR_REVIEW.md](SOLAR_REVIEW.md) and [DENTAL_REVIEW.md](DENTAL_REVIEW.md). Read their latest follow-up verdicts rather than treating historical findings as current. AI acceptance is limited to review-only task authoring, never human approval or runtime safety certification.

Our target is **original task definitions aligned with the applicable end-state and communication evaluation principles**, not a claim of upstream file-format compatibility. Tool contracts, trusted identity state and hidden evaluation fields must be explicit. Full-duplex interaction metrics and speech-quality judges require actual run evidence and remain unmeasured. Consent, opt-out, retry and deduplication gates are our project-specific requirements, not additional official τ-Voice metrics.

## Review order and remaining M2 scope

1. Review each knowledge pack: sourced facts versus invented policy choices.
2. Inspect caller goals, mock-tool contracts and expected changes, including no-write cases.
3. Run the local validator linked in each pilot; a pass proves only the implemented fixture checks, not that an agent succeeds.
4. Resolve independent review findings and record human approval before expanding.

All exposed pilots are **review-only**, never unseen final-test evidence. Full M2 still requires the M1 scale (approximately 40 inbound scenarios per business / 120 total, plus 30 outbound cases and 50–100 contacts per business), separately authored dev/test splits, broader coverage, human source/policy review and the milestone report/presentation. No completed human contributions or benchmark scores are asserted here.
