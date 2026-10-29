# AI Usage and Contribution Record

## 1. AI Tools Used

ChatGPT was used as an assistance tool during development of the Churn Prediction & Retention Experiment synthetic-data project.

## 2. Where AI Assistance Was Used

AI assistance supported:
- Reviewing the synthetic-data generator and its business rules.
- Reviewing retention experiment metrics and treatment/control cost handling.
- Identifying opportunities to strengthen automated tests.
- Explaining reproducibility checks using a fixed random seed and SHA-256 file hashes.
- Reviewing project documentation and identifying missing submission materials.

## 3. Prompts and Assistance Record

The prompts below summarize the assistance topics used during this development session. They are not a verbatim export of every prompt submitted to the AI tool.

1. Review and update the retention metrics logic to exclude deliberately injected anomalies.
2. Review the existing automated tests and identify additional checks for retention metrics.
3. Verify that generated datasets are reproducible when the same seed and scale are used.
4. Review project documentation and identify missing submission requirements.

**Important:** Add the complete, verbatim prompts submitted to every AI tool before submission. Include prompts from earlier development sessions and any other AI tools used. Do not present this summary as the complete prompt history.

## 4. Work Personally Reviewed and Verified

The project developer:
- Reviewed the generated code changes.
- Ran the automated tests; the latest recorded result was six passing tests.
- Generated a 1,000-customer sample and reviewed the validation summary.
- Generated two 100-customer datasets using the same seed and scale.
- Compared the generated CSV files using SHA-256 hashes; the comparison reported no differences.

## 5. Assumptions and Limitations

- All generated records are synthetic and are not real customer records.
- The treatment effect and retention outcomes are simulated; observed lift is not evidence of real-world campaign effectiveness.
- Cost and margin calculations are simplified estimates.
- The project tests a single-campaign experiment and deliberately injects labelled anomalies.
- Automated checks do not establish statistical significance or guarantee production readiness.

## 6. Final Review

Before submission, review the complete source code, test results, dependencies, business rules, and generated outputs. Confirm that the repository includes the complete AI prompt history required by the assignment and that all claims in this document match the work actually performed.