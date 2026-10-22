# Group 6: Voice Agents for Small-Business Enquiries and Lead Follow-up

DS and AI Lab Project, IIT Madras

A voice agent that answers small-business enquiries, qualifies leads, updates a CRM and follows up with prospects (only with consent), plus a controlled comparison of **single-agent vs multi-agent** designs on correctness, policy compliance, CRM accuracy, latency and cost.

## Team

| Member | Initials |
|---|---|
| Abhishek Jha | A.J. |
| Srijan | S. |
| Sarwar Karim Akhand | S.K.A. |
| Omkar Shankar Pawar | O.S.P. |

Instructors/TAs with access: @PulkitMangal09, @AlapeAniruddha

## Documents

| Deliverable | Link | Status |
|---|---|---|
| Problem statement (with score) | [problem_statement/problem_statement.md](problem_statement/problem_statement.md) | ✅ |
| M1: Problem & literature review | [milestones/M1_problem_literature/report.md](milestones/M1_problem_literature/report.md) | ✅ Submitted |
| M1: Slides | [milestones/M1_problem_literature/slides.pdf](milestones/M1_problem_literature/slides.pdf) | ✅ |
| M2: Dataset | [milestones/M2_dataset](milestones/M2_dataset) | Upcoming |
| M3: Architecture | [milestones/M3_architecture](milestones/M3_architecture) | Upcoming |
| M4: Development | [milestones/M4_training](milestones/M4_training) | Upcoming |
| M5: Evaluation | [milestones/M5_evaluation](milestones/M5_evaluation) | Upcoming |
| M6: Deployment | [milestones/M6_deployment](milestones/M6_deployment) | Upcoming |
| Work log / contributions | [WORKLOG.md](WORKLOG.md) | Updated every milestone |
| Architecture | [docs/architecture.md](docs/architecture.md) | Draft |
| Experiment log | [experiments/EXPERIMENT_LOG.md](experiments/EXPERIMENT_LOG.md) | — |
| Final report / demo | [final/](final/) | End of project |

## Planned stack

LiveKit (real-time audio, SIP telephony) · streaming STT · LLM with tool calling · TTS · retrieval over business documents · CRM sandbox (FastAPI + PostgreSQL) with a validation layer · telephony provider for controlled phone tests.

## Repository structure

```
problem_statement/   approved problem, scope, stakeholders, objectives
milestones/          one folder per milestone (report.md, slides.pdf, assets/)
final/               final report, presentation, demo links
src/voice_agent/     reusable code (data, pipelines, evaluation, inference, utils, ...)
configs/             YAML configs (businesses, agents, evaluation)
data/                git-ignored synthetic data (only README tracked)
scripts/             CLI entry points
experiments/         experiment log and small run outputs
notebooks/           exploration and analysis
deployment/          demo app and deployment notes
tests/               tests
docs/                architecture, data card, model card, reproducibility
```

## Setup

_Will be added at M3 when the first prototype runs._ Copy `.env.example` to `.env` and fill in the keys.
