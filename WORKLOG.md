# Work Log and Individual Contributions

Updated at every milestone. Each member records their **own** entries.

## Work Division

| Member | Area | Main work | Objectives owned | Lead milestone |
|---|---|---|---|---|
| **Srijan** | Backend + agentic AI | CRM sandbox API, validation layer, single-agent and multi-agent versions, tools, prompts | O2, O3, O5 | M3, M4 |
| **Abhishek Jha** | Voice, telephony + outbound | LiveKit pipeline, speech-to-text and text-to-speech, latency tuning, telephony, website-form trigger, task queue, outbound gate, deployment | O7, O8, O9, O10 | M6 (and the telephony part of M4) |
| **Sarwar Karim Akhand** | Data + knowledge base | Three fictional businesses (documents, policies, qualification rules), CRM seed data, consent and opt-out records, the ~120 test conversations with expected CRM end states, the 30 outbound checks, document retrieval setup | O4 (data side) | M2 |
| **Omkar Shankar Pawar** | Evaluation + research | Simulated callers, automated test harness, metrics and scoring with an LLM judge, latency and cost tracking, statistical comparison of single vs multi-agent, error analysis, keeping the report and literature up to date | O1, O6, O11 | M5 |

Objective IDs (O1–O11) refer to Section 5 of the [M1 report](milestones/M1_problem_literature/report.md#5-measurable-objectives).

**Weekly pairings:**
- Abhishek + Srijan: connecting speech to the agent
- Srijan + Sarwar: CRM data model and test data
- Srijan + Omkar: logs and traces the evaluation needs

Every member presents their own area at each milestone review and commits from their own account.

## Milestone 1: Problem Statement and Literature Review (due 22 Oct 2026)

| Member | Contributions | Approx. hours |
|---|---|---|
| Abhishek Jha (A.J.) | Created the repository and structure; drafted the problem statement, scope, stakeholders and objectives; coordinated the M1 report; proposed the work division; prepared the review slides | |
| Srijan (S.) | Contributed to the voice-agent proposal, backend workflow and single-agent vs multi-agent comparison | |
| Sarwar Karim Akhand (S.K.A.) | Reviewed the project requirements and discussed M2 data and knowledge-base needs, including synthetic business documents, CRM seed data, consent/opt-out records, and test scenarios. | |
| Omkar Shankar Pawar (O.S.P.) | Conducted research on the problem statement and evaluation of single-agent vs. multi-agent systems using automated tests, performance metrics, cost and latency tracking, and error analysis.| |

## Milestone 2: Dataset and Data Preparation (due 29 Oct 2026)

Status: dataset preparation submission in progress; generated expansions remain review-only. See the [M2 report](milestones/Milestone-2/Milestone-2.md) for validation scope, pending work and acknowledgement details. Hours are not estimated retrospectively.

| Member | Contributions | Approx. hours |
|---|---|---|
| Srijan (S.) | Coordinated AI-assisted pilot authoring and independent review; checked source/knowledge and CRM/tool contracts; addressed dental fixture-validation defects with negative controls; organized the WIP m2 branch; prepared milestone documentation and contribution/acknowledgement updates. Pilot work is recorded in commits 25ad148 and 2efa053. | Not recorded |
| Abhishek Jha (A.J.) | M2 review and coordination, confirmed by Srijan. This entry is recorded by Srijan while Abhishek is unavailable, with explicit authorization for the proxy acknowledgement in the report. No unverified implementation or comprehensive data approval is attributed. | Not recorded |
| Sarwar Karim Akhand (S.K.A.) | Generated expanded contact, inbound and outbound artifacts and a provisional review-split manifest; added preparation/static-check scripts and progress documentation (commits 4fad21f and f2bd392). Entry summarized from commit evidence; personal confirmation/signature pending. | Not recorded |
| Omkar Shankar Pawar (O.S.P.) | M2 contribution details awaiting the member's confirmation. | Not recorded |

AI tools assisted authoring, implementation, review and documentation. Generated data, static validation and AI acceptance do not constitute runtime evaluation or blanket human approval. Members remain responsible for verifying the recorded work and limitations.

### Meetings / decisions

| Date | Attendees | Decisions |
|---|---|---|
| 29 Oct 2026 | Srijan; Abhishek's authorization reported by Srijan | Record Srijan's acknowledgement and an explicitly labelled authorized proxy acknowledgement for Abhishek. Keep roll numbers and other members' signatures pending until supplied; do not imply a meeting or personal signature occurred. |
