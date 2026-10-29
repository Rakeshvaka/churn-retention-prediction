import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_data import generate, validate_tables

def test_reproducible_small_dataset(tmp_path):
    a, va = generate(scale=30, seed=20261022, out=tmp_path / "a", inject_anomalies=False)
    b, vb = generate(scale=30, seed=20261022, out=tmp_path / "b", inject_anomalies=False)
    assert va["row_counts"] == vb["row_counts"]
    for name in a:
        assert a[name].to_csv(index=False) == b[name].to_csv(index=False)

def test_structural_integrity_without_anomalies(tmp_path):
    tables, summary = generate(scale=50, seed=20261022, out=tmp_path / "clean", inject_anomalies=False)
    assert summary["passed_structural_checks"], summary["structural_issues"]
    assert tables["Customer"].customer_id.is_unique
    assert tables["Subscription"].customer_id.isin(tables["Customer"].customer_id).all()

def test_anomalies_are_labelled(tmp_path):
    tables, summary = generate(scale=10, seed=20261022, out=tmp_path / "edge", inject_anomalies=True)
    assert len(pd_truth := __import__("pandas").read_csv(tmp_path / "edge" / "ground_truth.csv")) == 4
    assert set(pd_truth.issue_type) == {
        "INELIGIBLE_OFFER_SENT", "TREATMENT_CONTROL_LEAKAGE",
        "MULTIPLE_OFFER_ATTRIBUTION", "CHURN_BEFORE_PREDICTION_DATE"
    }

def test_all_required_anomalies_are_detected(tmp_path):
    tables, summary = generate(
        scale=100,
        seed=20261022,
        out=tmp_path / "anomaly_test",
        inject_anomalies=True
    )

    detected = summary["detected_business_rule_violations"]

    required = [
        "INELIGIBLE_OFFER_SENT",
        "TREATMENT_CONTROL_LEAKAGE",
        "CHURN_BEFORE_PREDICTION_DATE",
        "MULTIPLE_OFFER_ATTRIBUTION",
    ]

    for anomaly in required:
        assert detected[anomaly] >= 1, (
            f"Required anomaly was not detected: {anomaly}"
        )


def test_retention_metrics_are_present(tmp_path):
    tables, summary = generate(
        scale=100,
        seed=20261022,
        out=tmp_path / "metrics_test",
        inject_anomalies=True
    )

    assert "retention_metrics" in summary

    metrics = summary["retention_metrics"]

    assert "assigned_customers" in metrics
    assert "missing_retention_outcomes" in metrics
    assert "outcome_completeness_rate" in metrics
    assert "incremental_retention_lift" in metrics
    assert "cost_per_additional_retained_customer" in metrics
