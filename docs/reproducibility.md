# Reproducibility

## Environment

- Python 3.9+ standard library only for the M3 pipeline (tested on Python 3.15.2, macOS, Apple M5, 16 GB).
- No dataset download: the synthetic dataset is committed under `milestones/M2_dataset/`.
- Secrets live in `.env` (git-ignored). Copy `.env.example` and set `LLM_PROVIDER`, `LLM_MODEL` and the matching key. Per-role overrides (`AGENT_*`, `SIMULATOR_*`, `JUDGE_*`) let the judge use a different model from the agent.

## What is deterministic

| Step | Deterministic? | Notes |
|---|---|---|
| Preprocessing (`scripts/preprocess_m3.py`) | Yes | Same input files give the same chunks and views |
| Outbound gate (`scripts/run_outbound_gate.py`) | Yes | Pure function of CRM seed + event |
| Oracle and control runs (`--mode oracle`, `--mode control_skip_*`) | Yes | No LLM |
| LLM runs (`--mode llm`) | No | Temperature 0 reduces but does not remove variation; provider-side model updates also change results. Record provider, model and date for every run in `experiments/EXPERIMENT_LOG.md`, and use repeated runs (pass^k) from M5 |

## Run outputs

Each run writes to `experiments/runs/<run_id>/`: `results.json` (scores, transcripts, token usage), `final_states.json` (CRM after each task) and `transcripts/<task>.txt`.

## Local model used for the M3 verification run

Ollama 0.40.14 with `qwen3:8b` (thinking disabled via `reasoning_effort: none`). Set `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen3:8b`. Install Ollama and run `ollama pull qwen3:8b` first.
