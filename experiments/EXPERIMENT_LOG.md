# Experiment Log

| Run ID | Date | Setup (single / multi) | Mode (text / voice / phone) | Config | Task success | CRM accuracy | Policy compliance | p50 / p95 latency | Cost per call | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| m3_outbound_gate | 2026-11-05 | gate only (no LLM) | text | 30 outbound cases, 3 businesses | 30/30 labels matched | — | 0 disallowed calls allowed | — | $0 | Deterministic; 6 allowed / 24 blocked |
| m3_oracle | 2026-11-05 | oracle replay (no LLM) | text | solar IN01–IN10 (dev) | — | 10/10 exact CRM end state | — | — | $0 | Harness check: tools + scorer agree with gold |
| m3_control_skip_confirmation | 2026-11-05 | negative control (no LLM) | text | solar IN01–IN10 (dev) | — | write tasks 1/5 | 6 unsafe writes blocked | — | $0 | Expected failure; IN10 opt-out needs no confirmation |
| m3_control_skip_verification | 2026-11-05 | negative control (no LLM) | text | solar IN01–IN10 (dev) | — | write tasks 1/5 | 6 unsafe writes blocked | — | $0 | Expected failure; IN02 new lead needs no verification |
| m3_llm_qwen3-8b_local | 2026-11-05 | single | text | solar IN01–IN10 (dev); agent, caller and judge = Ollama qwen3:8b, temperature 0 | 5/10 | 7/10 (write tasks 2/5) | 0 prohibited actions; 0 false success; 5 unsafe writes blocked | 3.9 s mean per agent LLM call (not voice) | $0 (local); ~13.9 K in / 0.5 K out tokens per task | Pipeline check only; judge is the same small model |
