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
| M2: Dataset report | [milestones/M2_dataset/report.md](milestones/M2_dataset/report.md) | In progress (human review pending) |
| M2: Dataset files | [milestones/M2_dataset](milestones/M2_dataset) | Synthetic data, validators, splits |
| M3: Architecture report | [milestones/M3_architecture/report.md](milestones/M3_architecture/report.md) | In review |
| M3: Slides | [milestones/M3_architecture/slides.pdf](milestones/M3_architecture/slides.pdf) | Draft for review meeting |
| M4: Development | [milestones/M4_training](milestones/M4_training) | Upcoming |
| M5: Evaluation | [milestones/M5_evaluation](milestones/M5_evaluation) | Upcoming |
| M6: Deployment | [milestones/M6_deployment](milestones/M6_deployment) | Upcoming |
| Work log / contributions | [WORKLOG.md](WORKLOG.md) | Updated every milestone |
| Architecture | [docs/architecture.md](docs/architecture.md) | Links to M3 diagrams |
| Experiment log | [experiments/EXPERIMENT_LOG.md](experiments/EXPERIMENT_LOG.md) | — |
| Final report / demo | [final/](final/) | End of project |

## Planned stack

LiveKit (real-time audio, SIP telephony) · streaming STT · LLM with tool calling · TTS · retrieval over business documents · CRM sandbox (FastAPI + PostgreSQL) with a validation layer · telephony provider for controlled phone tests.

## Repository structure

```
problem_statement/   approved problem, scope, stakeholders, objectives
milestones/          one folder per milestone (report.md, slides.pdf, assets/); M2 data lives in M2_dataset/
final/               final report, presentation, demo links
src/voice_agent/     reusable code (data, pipelines, evaluation, inference, utils, ...)
configs/             YAML configs (businesses, agents, evaluation)
data/                local generated/processed data, git-ignored (M2 dataset is in milestones/M2_dataset/)
scripts/             CLI entry points
experiments/         experiment log and small run outputs
notebooks/           exploration and analysis
deployment/          demo app and deployment notes
tests/               tests
docs/                architecture, data card, model card, reproducibility
```

## Setup

The M3 text-mode pipeline needs only **Python 3.9+** (standard library; nothing to install).

```bash
python3 -m unittest discover -s tests                     # 17 offline tests
python3 scripts/preprocess_m3.py --business solar         # chunks, task views, token report -> data/processed/
python3 scripts/run_outbound_gate.py                      # outbound gate on all 30 cases
python3 scripts/run_m3_pipeline.py --mode oracle          # harness check (no LLM)
cp .env.example .env                                      # set LLM_PROVIDER, LLM_MODEL and the API key
python3 scripts/run_m3_pipeline.py --mode llm             # LLM agent + simulated caller + judge, 10 dev tasks
```

**M3 implementation files:**

| Part | File |
|---|---|
| Data loading, split selection | [src/voice_agent/data/loader.py](src/voice_agent/data/loader.py) |
| Preprocessing (chunks, task views) | [src/voice_agent/data/preprocess.py](src/voice_agent/data/preprocess.py) |
| Retrieval (BM25) | [src/voice_agent/inference/retrieval.py](src/voice_agent/inference/retrieval.py) |
| CRM sandbox, validation layer, tools | [src/voice_agent/inference/crm.py](src/voice_agent/inference/crm.py) |
| Outbound gate | [src/voice_agent/inference/outbound_gate.py](src/voice_agent/inference/outbound_gate.py) |
| Single agent (+ oracle/controls) | [src/voice_agent/inference/agent.py](src/voice_agent/inference/agent.py) |
| LLM client (OpenAI, Anthropic, Groq, Ollama) | [src/voice_agent/models/llm.py](src/voice_agent/models/llm.py) |
| Simulated caller | [src/voice_agent/evaluation/simulator.py](src/voice_agent/evaluation/simulator.py) |
| Evaluator + LLM judge | [src/voice_agent/evaluation/evaluator.py](src/voice_agent/evaluation/evaluator.py) |
| Episode runner | [src/voice_agent/pipelines/episode.py](src/voice_agent/pipelines/episode.py) |
| Scripts | [scripts/preprocess_m3.py](scripts/preprocess_m3.py), [scripts/run_outbound_gate.py](scripts/run_outbound_gate.py), [scripts/run_m3_pipeline.py](scripts/run_m3_pipeline.py) |
| Tests | [tests/test_m3_pipeline.py](tests/test_m3_pipeline.py) |
| Run outputs | [experiments/runs/](experiments/runs), [experiments/EXPERIMENT_LOG.md](experiments/EXPERIMENT_LOG.md) |

Details and results: [M3 report, Section 4](milestones/M3_architecture/report.md#4-end-to-end-pipeline-verification) and [docs/reproducibility.md](docs/reproducibility.md).
