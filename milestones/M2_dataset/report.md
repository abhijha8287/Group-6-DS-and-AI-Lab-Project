# M2 Dataset Report

## 1. Objective

The objective of Milestone 2 (M2) is to prepare a reproducible synthetic dataset for evaluating voice agents that handle small-business enquiries, lead qualification, CRM updates, and follow-up decisions.

The dataset supports the project:

**Voice Agents for Small-Business Enquiries and Lead Follow-up: Single-Agent vs Multi-Agent**

It covers three fictional businesses and includes business knowledge documents, CRM seed data, interaction history, test conversations, and outbound-contact validation cases.

## 2. Business Domains

The dataset covers the following fictional businesses:

| Business ID | Business Name | Primary Use Case |
|---|---|---|
| `brightsmile` | BrightSmile Dental Studio | Dental service enquiries, appointment interest, and clinical-question escalation |
| `sungrid` | SunGrid Rooftop Solar | Solar installation enquiries and lead qualification |
| `urbannest` | UrbanNest Furniture | Product enquiries, delivery, returns, and custom-order escalation |

Each business has its own knowledge document containing services, frequently asked questions, policies, qualification fields, and general agent rules.

The knowledge documents are designed to help agents provide business-specific answers without inventing prices, availability, policies, savings, or other unsupported information.

## 3. Dataset Inventory

| Dataset Component | Records / Files | Purpose |
|---|---:|---|
| Business knowledge documents | 3 files | Business-specific information and policies |
| CRM seed data | 180 contacts | Synthetic customer and lead records |
| Interaction history | 180 records | Previous interaction information for CRM contacts |
| Development scenarios | 96 | Development and iteration |
| Test scenarios | 24 | Held-out evaluation |
| Total conversation scenarios | 120 | Evaluation across eight scenario categories |
| Outbound-contact checks | 30 | Follow-up eligibility and duplicate-contact safeguards |

All generated records are synthetic and intended for project testing. The phone numbers and contact information must not be used to contact real people.

## 4. Conversation Scenario Design

The dataset contains 120 synthetic conversation scenarios distributed across eight categories.

| Category | Purpose |
|---|---|
| `faq` | Answer common business-related questions |
| `new_lead` | Qualify a potential new customer |
| `existing_lead_update` | Handle updates from an existing lead |
| `callback` | Handle callback requests and related consent |
| `escalation` | Identify cases that require human assistance |
| `policy_probe` | Test compliance with business policies |
| `ambiguous_identity` | Test identity confirmation when records may be confused |
| `prompt_injection` | Test resistance to instructions that conflict with agent rules |

Each scenario includes the business identifier, business name, category, caller goal, expected action, expected business identifier, consent requirement, expected CRM action, expected lead and callback statuses, escalation expectation, and identity-confirmation expectation.

These expected outcomes provide a starting point for evaluating agent behavior. They should be refined into precise, independently verifiable expected CRM states before being treated as a complete evaluation benchmark.

## 5. Development and Test Split

The dataset is split deterministically by business and scenario category.

| Business | Development | Test | Total |
|---|---:|---:|---:|
| BrightSmile Dental Studio | 32 | 8 | 40 |
| SunGrid Rooftop Solar | 32 | 8 | 40 |
| UrbanNest Furniture | 32 | 8 | 40 |
| **Total** | **96** | **24** | **120** |

Each business has five scenarios in each category before splitting. Four scenarios per category are assigned to development and one to testing.

Consequently, the test set contains three scenarios per category: one from each business.

The split is deterministic, making dataset generation reproducible. However, because related scenarios may share templates or patterns, the split alone does not guarantee that development and test scenarios are semantically independent.

## 6. CRM Seed Data

The CRM seed dataset contains 180 synthetic contacts, with 60 contacts per business.

The current schema includes:

- `contact_id`
- `business_id`
- `name`
- `phone`
- `lead_status`
- `consent_to_follow_up`
- `opted_out`
- `last_contacted_days_ago`
- `previous_interaction_count`
- `last_interaction_type`
- `callback_status`

The dataset includes duplicate-name cases to test whether the agent confirms identity before updating the wrong contact. In particular, multiple contacts share the name `Alex Morgan`, while their contact identifiers remain unique.

Consent and opt-out states are represented separately. An opted-out contact must not be treated as eligible for follow-up merely because a previous consent field is true.

## 7. Interaction History

The interaction-history dataset contains 180 synthetic records, with one interaction record associated with each CRM contact.

Its fields include:

- `interaction_id`
- `contact_id`
- `business_id`
- `interaction_type`
- `outcome`
- `days_ago`

The dataset can support future testing of context-aware follow-up, previous-interaction retrieval, and CRM update workflows.

The current structure represents one interaction per contact and should not be interpreted as a complete multi-interaction history for every customer.

## 8. Outbound-Contact Checks

The outbound-contact dataset contains 30 synthetic test cases covering seven case types:

- Eligible contact
- Missing consent
- Opted-out contact
- Outside contact hours
- Already contacted
- Retry limit reached
- Duplicate submission

The dataset includes the following decision fields:

- `consent`
- `opted_out`
- `in_contact_hours`
- `already_contacted`
- `retry_limit_reached`
- `duplicate_submission`
- `expected_action`

The expected behavior is to block outbound contact if consent is absent, the contact has opted out, contact is outside the configured hours, the contact has already been contacted, the retry limit has been reached, or the submission is a duplicate. Contact is eligible only when none of these blocking conditions applies.

These are project-level test rules. The production system will need explicitly configured business policies and applicable legal and regulatory requirements.

## 9. Output Structure

The generator produces the following files:

```text
data/
├── raw/
│   ├── business_docs/
│   │   ├── brightsmile.md
│   │   ├── sungrid.md
│   │   └── urbannest.md
│   ├── crm_seed.csv
│   ├── interaction_history.csv
│   └── outbound_checks.csv
└── splits/
    ├── dev.csv
    └── test.csv
```

The generated data is excluded from version control by the repository's `.gitignore` configuration. The generation and validation scripts, documentation, and dataset schema information can be tracked without committing the generated CSV files.

## 10. Reproduction

Run the following commands from the repository root in PowerShell:

```powershell
python scripts/m2/generate_business_data.py
python -m src.voice_agent.data.validate_data
```

The generation script creates the synthetic dataset. The validation script checks the business documents, CRM records, interaction history, conversation scenarios, and outbound-contact cases.

## 11. Validation Results

The latest validation run reported:

| Validation Check | Result |
|---|---|
| Business knowledge documents | PASS — 3 files |
| CRM records | PASS — 180 records |
| Interaction history | PASS — 180 records |
| Duplicate-name identity cases | PASS — 6 records |
| Development and test scenarios | PASS — 96 development and 24 test |
| Outbound-contact checks | PASS — 30 cases |
| Overall validation | PASS |

The development/test distribution was also checked manually using PowerShell.

- Each business has 32 development scenarios.
- Each business has 8 test scenarios.
- Each of the eight categories has 3 test scenarios.
- The test and development sets contain distinct scenario identifiers.

The results confirm that the current dataset passes the implemented structural and rule-based validation checks. They do not establish that every expected agent response or CRM outcome is semantically correct.

## 12. Limitations and Next Steps

The following improvements remain relevant:

1. **Gold CRM end states:** Define exact expected field values before and after each scenario, including which fields must change and which must remain unchanged.
2. **Scenario validation:** Extend automated checks to verify category coverage and per-business distribution.
3. **Identity resolution:** Expand ambiguous-identity cases to test multiple possible matches and insufficient identifying information.
4. **Knowledge retrieval:** Connect business documents to a retrieval pipeline and evaluate whether answers are grounded in the correct document.
5. **Consent and follow-up:** Test consent capture, opt-out handling, duplicate submissions, retry limits, and configured contact hours in the agent workflow.
6. **Agent evaluation:** Compare single-agent and multi-agent implementations using the same test scenarios and consistent evaluation criteria.
7. **Data quality:** Review scenario wording, expected actions, and edge cases to reduce ambiguity and improve reproducibility.

## 13. Contribution Summary

This milestone contribution focuses on synthetic business knowledge documents, CRM seed data, interaction-history generation, conversation scenario generation, outbound-contact test cases, and automated dataset validation.

The resulting dataset provides a reproducible starting point for integrating and evaluating voice-agent workflows across three small-business domains.
