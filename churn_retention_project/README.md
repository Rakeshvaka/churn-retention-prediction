# Churn Prediction & Retention Experiment

A reproducible synthetic-data project for identifying likely churn, applying retention-offer eligibility rules, and evaluating randomized treatment/control campaigns. All records are synthetic.

## Requirements
- Python 3.10+
- `pip install -r requirements.txt`

## Quick start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/generate_data.py --scale 500 --seed 20261022 --out data/sample
python -m pytest
```

## Full dataset
```bash
python src/generate_data.py --scale 20000 --seed 20261022 --out data/generated
```
The generator creates CSV and JSON for the ten core entities, a separate `ground_truth.csv`, `source_manifest.json` with row counts and SHA-256 checksums, and `validation_summary.json`. Use `--no-anomalies` for clean baseline output. Edge-case injection is deterministic and separately labelled.

## Business definitions
- **Prediction date:** 2026-01-01.
- **Observation window:** 18 monthly snapshots from 2024-07 through 2025-12.
- **Prediction horizon:** 90 days after prediction date.
- **Churn label:** `churned_within_horizon=1` when the synthetic outcome process assigns a churn event during the 90-day horizon. `churn_date` is generated within the horizon; the intentionally invalid edge case is labelled in `ground_truth.csv`.
- **Feature timing:** risk score uses pre-prediction usage, failed billing events, and support cases. `ground_truth.csv` is never used as an input feature.
- **Offer eligibility:** active rule, risk threshold, allowed segment, discount ceiling, and minimum margin must all pass.
- **Experiment:** eligible customers receive one seeded offer selection and are randomized 50/50 into `TREATMENT` or `CONTROL`. Treatment is marked `SENT`; control is `HOLDOUT`. Retention outcomes are recorded at 90 days. The synthetic outcome process includes a treatment effect; compare groups to estimate incremental lift, not correlation alone.
- **Margin calculation:** estimated monthly margin after offer = monthly price after discount minus offer unit cost for treatment; control cost is zero. This is a simplified synthetic proxy, not a financial accounting measure.

## Entity relationships
- Customer 1:N Subscription (this baseline creates one subscription per customer; schema allows multiple).
- Subscription 1:N UsageSnapshot and BillingEvent.
- Customer 1:N SupportCase; each support case may optionally reference a Subscription.
- Offer 1:N EligibilityRule; rule effective dates govern eligibility.
- Customer 1:N CampaignContact over time; this single-campaign sample generates one contact/assignment per customer.
- CampaignContact 1:0..1 RetentionOutcome in the clean baseline; the injected multiple-attribution anomaly is labelled.
- Customer 1:0..1 ChurnOutcome per prediction date/horizon in this dataset.
- Many-to-many relationships, if expanded to multiple campaigns/offers per customer, should be modeled using CampaignContact as a bridge between Customer and Offer.

## Core validation
The generator performs structural validation and business-rule validation.

**Structural checks**
- Primary-key uniqueness
- Foreign-key integrity
- Valid enumeration values
- Nonnegative usage values

**Business-rule anomaly detection**

The validation summary reports detected violations for four categories:

1. `INELIGIBLE_OFFER_SENT` — an ineligible customer receives an offer.
2. `TREATMENT_CONTROL_LEAKAGE` — a control-group customer receives a treatment offer.
3. `CHURN_BEFORE_PREDICTION_DATE` — a positive churn label has a missing or invalid churn date outside the prediction horizon.
4. `MULTIPLE_OFFER_ATTRIBUTION` — a customer has multiple retention outcomes in a single-campaign dataset.

The `validation_summary.json` file reports `detected_business_rule_violations` separately from `expected_anomalies_detected_by_label`. The first counts records matching each rule; the second counts deliberately labelled anomaly fixtures. Counts can differ when multiple records match a rule.

**Retention experiment metrics**

The validation summary also reports:
- Number of customers assigned to treatment and control.
- Missing retention outcomes and outcome completeness rates by group.
- Retention rate and total offer cost for each group.
- Incremental retention lift, calculated as treatment retention rate minus control retention rate.
- Cost per additional retained customer, calculated using the difference in retained-customer counts and treatment offer cost.

These metrics describe the synthetic experiment. They do not establish statistical significance or guarantee real-world campaign performance.

The anomalies are deliberate test fixtures. Use `issue_type` and `ground_truth.csv` to identify the injected records. Do not treat the intentionally injected dataset as fully clean.

## Reproducibility
Run the same command twice with the same seed and compare `source_manifest.json` checksums. The seed and scale are configurable. Do not commit large generated output unless your repository policy requires it; commit a small sample and the generator.

## Public GitHub submission checklist
1. Create a public repository.
2. Commit source, tests, README, requirements, and a small sample.
3. Do not upload secrets, real customer data, or personal information.
4. Push the repository and verify that a clean clone can run the quick-start commands.
