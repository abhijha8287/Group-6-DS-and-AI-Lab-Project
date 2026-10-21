# Problem Statement

**Title:** Voice Agents for Small-Business Enquiries and Lead Follow-up: Single-Agent vs Multi-Agent

**Problem statement score:** `__ / __` _(add the score as communicated by the instructors)_

## Problem

Small businesses miss inbound calls when staff are busy, follow up slowly (or not at all) on website sign-ups, enquiry forms and prospect lists, and lose context when an enquiry is handed to a person. We are building a voice agent that answers enquiries from each business's own documents, qualifies leads using the business's rules, updates a CRM correctly, arranges callbacks with a handoff summary, and places outbound follow-up calls **only** when consent, opt-out, calling-hour and duplicate checks pass.

We will also measure whether a **multi-agent** design (a conversation agent plus knowledge, qualification and CRM/handoff specialists) is better enough than a **single-agent** design to justify its extra coordination, latency and cost.

## Scope

- **In:** three fictional businesses with reviewed documents/policies and a resettable CRM sandbox; inbound calls; consent-gated outbound calls from list imports and website-form triggers (controlled test list); callback + summary handoff; a validation layer for all CRM writes; browser voice demo first, then controlled phone calls.
- **Out:** purchases/payments; live call transfer (later, optional); calling the public; treating sign-up as consent; model training; production CRM integrations.

## Stakeholders

Small-business owners, front-desk/sales staff, callers/prospects, regulators/telecom providers, developers, and course evaluators.

## Objectives (summary)

| ID | Objective | Target |
|---|---|---|
| O1 | Task success (CRM end-state + information conveyed) | ≥ 85% text / ≥ 80% voice |
| O2 | CRM write accuracy | ≥ 95%; wrong-record ≤ 1% |
| O3 | Policy compliance; unconfirmed actions | ≥ 95%; 0 |
| O4 | Factual accuracy vs business docs | ≥ 95% |
| O5 | False "success" claims to caller | 0 |
| O6 | Escalation precision / recall | ≥ 0.90 |
| O7 | Disallowed or duplicate outbound calls | 0 |
| O8 | Follow-up trigger recall; trigger latency | 100%; ≤ 60 s |
| O9 | Voice-to-voice latency p50 / p95 | ≤ 1.5 s / ≤ 3.0 s |
| O10 | Cost per call-minute | ≤ US$0.15 |
| O11 | Adopt multi-agent only if +≥5 pp on O1/O3 with ≤ +500 ms p95 and ≤ +50% cost | decision rule |

Full details, the literature review and references: [`milestones/M1_problem_literature/report.md`](../milestones/M1_problem_literature/report.md).
