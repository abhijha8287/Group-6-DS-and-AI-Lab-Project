# UrbanNest Furniture — pilot knowledge

**AI-assisted original draft; human review pending.** UrbanNest Furniture is a fictional enquiry-and-handoff sandbox, not an IKEA clone or affiliate. These documents do not represent actual IKEA operations. The public facts below are narrowly paraphrased references; the sandbox rules are invented independently.

## Source register

Accessed **2026-10-28** (local system date). Public pages can contain conflicting or stale details. This is neither a comprehensive policy summary nor a live policy feed; consult the source and a human for case-specific decisions. Citation does not assert a licence to reuse source material.

| Source | Public reference | Used for |
|---|---|---|
| R1 | [IKEA India return policy](https://www.ikea.com/in/en/customer-service/returns-claims/return-policy/) | F1, F2 |
| R2 | [IKEA India FAQ](https://www.ikea.com/in/en/customer-service/faq-pub7f08ed41/) | F3, F4; basis for the F5 inference |

## Reference facts

| ID | Meaning | Bounded paraphrase |
|---|---|---|
| F1 | conditional365days | R1 describes returns within 365 days subject to eligibility. Opened or assembled items may be accepted with a receipt, with the refund provided on a refund card. This does not establish eligibility for an individual item. |
| F2 | excludedcustomworktops | R1 excludes custom worktops, gift cards, plants and food from that returns offer. Do not promise a custom-worktop return. |
| F3 | stockneedscheck | R2 directs customers to product pages for stock information. Availability needs checking; this pilot has no live stock evidence. |
| F4 | deliveryPINcheck | R2 makes delivery availability dependent on PIN-code serviceability. Collect the PIN code for a check, not a delivery promise. |
| F5 | cancellationrequestnotproof | R2 describes requesting cancellation through the order-confirmation link or customer service. **Our conservative inference:** making that request is not proof that cancellation succeeded. This is not a literal stated business policy or a guaranteed cancellation outcome. |

For this fictional experiment only, UrbanNest adopts F1–F4 as limited hypothetical policies; F5 remains an outcome-verification inference. This adoption is our sandbox design, not evidence of a real UrbanNest business. These references support enquiry answers only. Do not invent catalogue items, prices, delivery dates, cancellation guarantees or additional policy details. UrbanNest's sandbox cannot execute the referenced retail processes.

## Invented sandbox rules

**Every S rule is a pilot design choice, not an IKEA fact and not a claim of legal compliance.** These are requirements for later implementation and review, not evidence that a functioning agent or CRM API exists.

| ID | Rule |
|---|---|
| S1 | Before modifying an existing contact or attaching a callback/handoff, establish identity using `contact_id` plus verified email. A stated email alone is not verification. Harness-owned synthetic verification stands in for future authentication: only a successful agent-visible `verify_identity` result establishes session authorization for that contact. `environment.identity_verified` is evaluator-only expected checkpoint state, never caller authority or an initial grant; see [mock-tool contract](MOCK_TOOLS.md). A new enquiry may be created from caller-confirmed supplied details after checking for an existing email; it does not establish verified identity or outbound consent. |
| S2 | Obtain the caller's explicit confirmation before CRM writes or scheduling a callback. S8 is the opt-out exception: no extra confirmation after verified identity. |
| S3 | Only enquiry/lead updates, callback requests and structured human handoffs are permitted. Never execute payments, refunds, orders, cancellations or returns. Discussing a request is not executing it. |
| S4 | Callback hours are daily, **10:00 inclusive to 18:00 exclusive, Asia/Kolkata**; callback duration is **30 minutes**, and the entire slot must end by 18:00 (latest start 17:30). Outbound eligibility checks only call start time, not a guaranteed duration. Do not promise a slot without a successful tool result. |
| S5 | Outbound eligibility requires **all** of: sandbox destination allowlist membership, explicit recorded consent, not opted out, within S4 hours, no attempt in the last 24 hours, fewer than 2 prior attempts, and an event not already processed (event deduplication). A website enquiry or import alone is not consent. Requested callbacks also require these gates at eventual dispatch; recording a request grants no consent or allowlist exception. C12/CB00 and C09 remain blocked without applicable consent and allowlist membership. |
| S6 | Matching names, including identical names, never prove identity or authorise a record merge. |
| S7 | Escalate unsupported or uncertain information instead of inventing an answer. Custom design enquiries go to a human; do not invent specifications or commitments. |
| S8 | Once identity is verified, immediately record an opt-out without asking for an additional confirmation. Stop outbound eligibility; do not turn the opt-out into a sales conversation. If identity is unverified, do not modify an arbitrary record. |
| S9 | For a new enquiry, ask for `category`, `budget_inr`, `pincode` and `timeline_days`. Record provided information without inventing missing values. There is **no automated qualification decision threshold** in this pilot; pass the context to a human. |
| S10 | Tool failure, an unchecked result or a pending request must never be reported as success. Explain that completion is unconfirmed; do not claim a CRM update, callback or handoff occurred. |

## Answer and handoff boundary

Use the applicable F and S IDs when reviewing expected answers and actions. Explain return eligibility conditionally, check rather than promise stock or delivery, and distinguish a cancellation request from a completed cancellation. General informational answers need not cause CRM writes.

A human handoff should preserve the enquiry, provided qualification fields, relevant fact/rule IDs, unresolved questions and the actual tool outcome. Identity, caller confirmation and permitted-action checks still apply to writing that summary. No real phone numbers, addresses or product prices are supplied by this knowledge base.
