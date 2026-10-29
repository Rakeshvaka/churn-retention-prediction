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

## 3. AI Prompt History

ChatGPT was used to assist with code review, debugging, testing, reproducibility checks, and documentation.

### Prompt topics and development activities

The following records describe the assistance used during the project. They are a reconstructed summary, not a complete verbatim transcript of every prompt.

1. **Synthetic-data generator review**
   - Reviewed the generator, entity relationships, business rules, and deliberate anomaly injection.
   - Checked the output structure and validation approach.

2. **Retention experiment metrics**
   - Reviewed treatment and control retention rates, offer costs, incremental retention lift, and cost per additional retained customer.
   - Updated the metrics logic to exclude labelled campaign-contact anomalies and labelled retention-outcome anomalies from the clean experiment metrics.

3. **Automated testing**
   - Reviewed the existing tests for reproducibility, structural integrity, anomaly detection, and retention metrics.
   - Added a test checking that control-group offer cost is zero, retention rates are within valid bounds, and labelled campaign anomalies are excluded from experiment assignments.

4. **Reproducibility verification**
   - Used the same seed and scale to generate two datasets.
   - Compared corresponding CSV files using SHA-256 hashes.

5. **Documentation and submission review**
   - Reviewed the README and identified the need for AI usage documentation.
   - Documented project assumptions, limitations, testing activities, and submission considerations.

### Verbatim prompt record

This section must be completed before submission. Add the exact prompts submitted to ChatGPT and any other AI tools used, including prompts from earlier development sessions where available.

Do not describe the reconstructed topics above as a complete prompt history. Preserve the original wording when copying prompts from the conversation records.

### Human review and validation

The developer reviewed the proposed code changes, ran the automated test suite, inspected generated validation metrics, and verified that two CSV output sets matched for the same seed and scale.

The latest recorded test result was six passing tests. These checks provide evidence of the tested behavior but do not prove that the project is free from defects or ready for production.


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