# M2 — Synthetic Dataset and Validation

## 1. Objective

Build a reproducible synthetic dataset for evaluating single-agent and multi-agent voice systems across three fictional businesses. The dataset supports knowledge-grounded responses, CRM updates, lead qualification, consent-aware follow-up, and safety evaluation.

## 2. Businesses

| Business ID | Business | Main enquiry types |
|---|---|---|
| `brightsmile` | BrightSmile Dental Studio | Check-ups, cleaning, aligner consultations |
| `sungrid` | SunGrid Rooftop Solar | Solar installation, site surveys, consultations |
| `urbannest` | UrbanNest Furniture | Catalogue, delivery, custom orders |

Business knowledge documents contain service information, business hours, policies, and safety rules.

## 3. Dataset inventory

| Dataset | Size | Purpose |
|---|---:|---|
| Business knowledge documents | 3 | Ground responses in business-specific information |
| CRM seed records | 180 | 60 synthetic contacts per business |
| Development scenarios | 96 | Iterative development and prompt testing |
| Held-out test scenarios | 24 | Final evaluation |
| Outbound checks | 30 | Initial consent and contact-eligibility checks |

All generated records are synthetic.

## 4. Scenario categories

The scenario generator covers eight categories:

- Frequently asked questions
- New lead qualification
- Existing lead updates
- Callback requests
- Escalation
- Policy probes
- Ambiguous identity
- Prompt injection

Each scenario contains a scenario ID, business ID, caller goal, expected action, and consent-related metadata.

## 5. CRM schema

The CRM seed CSV contains:

- `contact_id`: unique synthetic contact identifier
- `business_id`: associated business
- `name`: synthetic contact name
- `phone`: synthetic phone-like identifier
- `lead_status`: initial lead status
- `consent_to_follow_up`: follow-up consent flag
- `opted_out`: opt-out flag
- `last_contacted_days_ago`: synthetic contact-history field

## 6. Output structure

Generated files are written locally under the repository's `data/` directory:

- `data/raw/business_docs/`: business knowledge documents
- `data/raw/crm_seed.csv`: CRM seed records
- `data/raw/outbound_checks.csv`: outbound eligibility cases
- `data/splits/dev.csv`: development scenarios
- `data/splits/test.csv`: held-out scenarios

The repository's `.gitignore` excludes generated data files. Only approved scripts and documentation should be committed unless the team agrees to change that policy.

## 7. Reproduction

From the repository root, run:

```bash
python scripts/m2/generate_business_data.py
python src/voice_agent/data/validate_data.py
```

The generator uses a fixed random seed for reproducibility. The validator checks file existence, row counts, required values, unique IDs, business IDs, development/test separation, and basic outbound safety expectations.

## 8. Validation results

The initial validation run passed:

- Business knowledge documents: 3
- CRM records: 180
- Scenarios: 96 development and 24 test
- Outbound checks: 30

Console result: `All M2 dataset validation checks passed.`

## 9. Limitations and next steps

This is an initial synthetic dataset, not a complete evaluation benchmark.

1. Expand the outbound suite to explicitly test prior contact, retry limits, duplicate submissions, contact windows, and consent changes.
2. Add detailed gold CRM end states to scenarios, including expected field values and escalation outcomes.
3. Introduce controlled near-duplicate identities for record-matching tests.
4. Review the development/test split methodology and prevent related scenarios from leaking across splits.
5. Implement document chunking, embeddings, retrieval, and business-level filtering.
6. Review the dataset with teammates before using it for final single-agent versus multi-agent comparisons.

## 10. Contribution

Initial M2 contribution: implemented synthetic business-document, CRM, scenario, and outbound-case generation; added structural validation; and documented reproduction steps and known limitations.

Update this section with any additional work and team-review outcomes before the milestone submission.
