# Design Decisions, Assumptions, and Limitations

## 1. Project Overview

The Churn Prediction & Retention Experiment project generates synthetic customer, subscription, usage, billing, support, churn, and retention data. It demonstrates how churn-related behavior can support risk scoring, offer eligibility, and randomized retention experiments.

All records are synthetic. The results are for development and demonstration, not real customer decision-making.

## 2. Design Decisions

### 2.1 Reproducible Data Generation

**Decision:** Use a configurable random seed, with `20261022` as the default.

**Reason:** A fixed seed makes it possible to regenerate the same dataset and investigate unexpected results. The scale and output directory are configurable through command-line arguments.

**Verification:** Two runs using scale `100` and seed `20261022` produced matching CSV file hashes.

### 2.2 Related Synthetic Behavior

**Decision:** Generate churn-related behavior using a latent risk score and related signals, including usage decline, failed payments, and support cases.

**Reason:** This creates relationships between the synthetic customer behavior and generated churn labels instead of assigning every label independently of behavior.

**Limitation:** The relationships are simulated assumptions. They do not establish that these signals predict churn accurately in a real customer population.

### 2.3 Prediction Date and Observation Window

**Decision:** Use a prediction date of `2026-01-01`, an 18-month observation window from July 2024 through December 2025, and a 90-day prediction horizon.

**Reason:** A fixed time boundary makes the feature window and target horizon explicit and repeatable.

**Limitation:** This is a static synthetic dataset, not a continuously updated production data pipeline.

### 2.4 Offer Eligibility

**Decision:** An offer is eligible only when the applicable active rule, minimum risk score, allowed customer segment, discount ceiling, and minimum margin requirements are satisfied.

**Reason:** Explicit rules make eligibility decisions explainable and testable.

**Limitation:** The offer costs, discounts, and margin calculations are simplified examples and do not represent a complete financial model.

### 2.5 Treatment and Control Groups

**Decision:** Eligible customers are assigned to treatment or control using seeded randomization. Treatment records are marked `SENT`, while control records are marked `HOLDOUT`.

**Reason:** A comparison between the two groups demonstrates how incremental retention lift and offer costs can be measured.

**Limitation:** The generated experiment is synthetic. Observed lift does not prove real-world