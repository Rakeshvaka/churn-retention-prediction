from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_SEED = 20261022
PREDICTION_DATE = pd.Timestamp("2026-01-01")
OBSERVATION_MONTHS = pd.date_range("2024-07-01", periods=18, freq="MS")
CHURN_HORIZON_DAYS = 90

def make_id(prefix, n, width=6):
    return f"{prefix}-{n:0{width}d}"

def generate(scale=20000, seed=DEFAULT_SEED, out="data/generated", inject_anomalies=True):
    rng = np.random.default_rng(seed)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)

    n = int(scale)
    customer_num = np.arange(1, n + 1)
    customer_ids = [make_id("CUS", i) for i in customer_num]
    regions = rng.choice(["NORTH", "SOUTH", "EAST", "WEST"], n)
    segments = rng.choice(["BASIC", "STANDARD", "PREMIUM"], n, p=[.45, .38, .17])
    acquisition = pd.to_datetime(rng.integers(pd.Timestamp("2022-01-01").value//10**9,
                                             pd.Timestamp("2025-07-01").value//10**9, n), unit="s").normalize()
    customers = pd.DataFrame({
        "customer_id": customer_ids, "signup_date": acquisition.date.astype(str),
        "region": regions, "segment": segments,
        "customer_status": rng.choice(["ACTIVE", "SUSPENDED"], n, p=[.96, .04]),
        "issue_type": ""
    })

    plan_map = {"BASIC": ("Basic", 20.0), "STANDARD": ("Standard", 40.0), "PREMIUM": ("Premium", 70.0)}
    subs = []
    for i, cid in enumerate(customer_ids):
        seg = segments[i]
        plan, price = plan_map[seg]
        start = pd.Timestamp(acquisition[i]).to_period("M").to_timestamp()
        subs.append({
            "subscription_id": f"SUB-{cid}-01", "customer_id": cid, "product_cohort": seg,
            "plan_name": plan, "monthly_price": price, "start_date": str(start.date()),
            "end_date": "", "subscription_status": "ACTIVE", "issue_type": ""
        })
    subscriptions = pd.DataFrame(subs)
    subscription_ids = subscriptions.subscription_id.tolist()

    # A latent risk score creates related behavior and labels rather than independent churn labels.
    latent_risk = rng.beta(2, 5, n)
    seasonal = rng.random(n) < .12
    involuntary_propensity = rng.random(n)
    base_usage = np.where(segments == "BASIC", 35, np.where(segments == "STANDARD", 70, 120))
    snapshots, billing, support = [], [], []
    churn_month_idx = np.full(n, -1, dtype=int)
    churn_type = np.array([""] * n, dtype=object)

    for i in range(n):
        # Monthly churn hazard is driven by latent risk, payment friction, and later usage decline.
        risk = latent_risk[i]
        usage_prev = float(base_usage[i] * rng.uniform(.75, 1.25))
        failed_streak = 0
        for mi, month in enumerate(OBSERVATION_MONTHS):
            month_index = mi + 1
            seasonal_factor = 0.58 if seasonal[i] and month.month in (1, 2, 7, 8) else 1.0
            trend_factor = max(.25, 1 - max(0, mi - 7) * (0.008 + risk * .045))
            usage = max(0.0, usage_prev * trend_factor * seasonal_factor * rng.normal(1, .12))
            if rng.random() < (0.025 + risk * .12):
                usage *= rng.uniform(.15, .55)
            usage = round(float(usage), 2)
            snap_id = f"SNAP-{subscription_ids[i]}-{month.strftime('%Y-%m')}"
            snapshots.append({
                "snapshot_id": snap_id, "subscription_id": subscription_ids[i],
                "snapshot_month": str(month.date()), "usage_units": usage,
                "active_days": int(np.clip(round(30 * min(1, usage / max(base_usage[i], 1))), 0, 30)),
                "sessions": int(max(0, round(usage * rng.uniform(.5, 1.5)))),
                "issue_type": ""
            })
            failed = rng.random() < (.025 + risk * .16)
            failed_streak = failed_streak + 1 if failed else 0
            amount = float(subscriptions.monthly_price.iloc[i])
            paid = not failed
            billing.append({
                "billing_event_id": f"BILL-{subscription_ids[i]}-{month.strftime('%Y-%m')}",
                "subscription_id": subscription_ids[i], "event_date": str((month + pd.offsets.Day(1)).date()),
                "event_type": "INVOICE", "amount": round(amount, 2),
                "payment_status": "FAILED" if failed else "PAID",
                "balance_after_event": round(amount if failed else 0.0, 2),
                "issue_type": ""
            })
            if rng.random() < (.035 + risk * .10):
                opened = month + pd.offsets.Day(int(rng.integers(1, 26)))
                support.append({
                    "support_case_id": f"CASE-{subscription_ids[i]}-{month.strftime('%Y-%m')}",
                    "customer_id": customer_ids[i], "subscription_id": subscription_ids[i],
                    "opened_date": str(opened.date()), "case_category": rng.choice(["BILLING", "TECHNICAL", "CANCELLATION", "GENERAL"]),
                    "severity": rng.choice(["LOW", "MEDIUM", "HIGH"], p=[.55, .35, .10]),
                    "case_status": rng.choice(["CLOSED", "OPEN"], p=[.88, .12]),
                    "issue_type": ""
                })
            # churn propensity responds to risk, failed payments and low usage.
            hazard = min(.10, .006 + risk * .045 + (0.025 if failed_streak >= 2 else 0) +
                         (0.018 if usage < base_usage[i] * .35 else 0))
            if churn_month_idx[i] < 0 and rng.random() < hazard:
                churn_month_idx[i] = mi
                churn_type[i] = "INVOLUNTARY" if (failed_streak >= 2 and involuntary_propensity[i] < .72) else "VOLUNTARY"
            usage_prev = max(usage, 1.0)

    usage_df = pd.DataFrame(snapshots)
    billing_df = pd.DataFrame(billing)
    support_df = pd.DataFrame(support)

    # Churn outcomes are derived from the latent behavioral process. Churn dates are after the observation period
    # for labels used by the prediction-date dataset; historical churn is represented in lifecycle state.
    outcomes = []
    for i, cid in enumerate(customer_ids):
        # Keep prediction date at end of observation window; a future 90-day outcome is generated from pre-date risk.
        # Labels are generated from documented rules with seeded random draws, not assigned independently.
        recent = usage_df[(usage_df.subscription_id == subscription_ids[i])].tail(3).usage_units.to_numpy()
        earlier = usage_df[(usage_df.subscription_id == subscription_ids[i])].tail(6).head(3).usage_units.to_numpy()
        decline = (float(np.mean(earlier)) - float(np.mean(recent))) / max(float(np.mean(earlier)), 1)
        failed_count = int((billing_df[billing_df.subscription_id == subscription_ids[i]].tail(3).payment_status == "FAILED").sum())
        case_count = int((support_df[(support_df.subscription_id == subscription_ids[i]) &
                                     (pd.to_datetime(support_df.opened_date) >= PREDICTION_DATE - pd.Timedelta(days=90))]).shape[0]) if len(support_df) else 0
        risk_score = float(np.clip(.18 + latent_risk[i] * .55 + max(0, decline) * .18 +
                                   failed_count * .055 + case_count * .025, 0, .99))
        churn_probability = float(np.clip(risk_score * .20, .01, .19))
        churned = bool(rng.random() < churn_probability)
        churn_date = (PREDICTION_DATE + pd.Timedelta(days=int(rng.integers(1, CHURN_HORIZON_DAYS + 1)))).date().isoformat() if churned else ""
        outcomes.append({
            "churn_outcome_id": f"CHURN-{cid}-2026", "customer_id": cid,
            "prediction_date": str(PREDICTION_DATE.date()), "horizon_days": CHURN_HORIZON_DAYS,
            "churned_within_horizon": int(churned), "churn_date": churn_date,
            "churn_type": (churn_type[i] if churned and churn_type[i] else ("INVOLUNTARY" if failed_count >= 2 else "VOLUNTARY")) if churned else "",
            "risk_score": round(risk_score, 4), "issue_type": ""
        })
    churn_outcomes = pd.DataFrame(outcomes)

    offers = pd.DataFrame([
        {"offer_id": "OFF-2026-000001", "offer_name": "10pct_3months", "discount_pct": 10.0, "duration_months": 3, "unit_cost": 12.0, "min_margin_pct": 35.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "status": "ACTIVE"},
        {"offer_id": "OFF-2026-000002", "offer_name": "service_credit", "discount_pct": 0.0, "duration_months": 1, "unit_cost": 8.0, "min_margin_pct": 30.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "status": "ACTIVE"},
        {"offer_id": "OFF-2026-000003", "offer_name": "premium_upgrade", "discount_pct": 5.0, "duration_months": 2, "unit_cost": 15.0, "min_margin_pct": 40.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "status": "ACTIVE"}
    ])
    eligibility = pd.DataFrame([
        {"eligibility_rule_id": "RULE-0001", "offer_id": "OFF-2026-000001", "min_risk_score": .45, "allowed_segments": "BASIC;STANDARD;PREMIUM", "max_discount_pct": 15.0, "min_margin_pct": 35.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "is_active": True},
        {"eligibility_rule_id": "RULE-0002", "offer_id": "OFF-2026-000002", "min_risk_score": .35, "allowed_segments": "BASIC;STANDARD;PREMIUM", "max_discount_pct": 0.0, "min_margin_pct": 30.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "is_active": True},
        {"eligibility_rule_id": "RULE-0003", "offer_id": "OFF-2026-000003", "min_risk_score": .60, "allowed_segments": "STANDARD;PREMIUM", "max_discount_pct": 10.0, "min_margin_pct": 40.0, "effective_from": "2026-01-01", "effective_to": "2026-12-31", "is_active": True}
    ])

    # Eligibility and offer assignment: one campaign decision per customer, randomized treatment/control among eligible.
    campaign = []
    retentions = []
    customer_lookup = customers.set_index("customer_id")
    sub_lookup = subscriptions.set_index("customer_id")
    for i, row in churn_outcomes.iterrows():
        cid = row.customer_id
        seg = customer_lookup.loc[cid, "segment"]
        price = float(sub_lookup.loc[cid, "monthly_price"])
        risk = float(row.risk_score)
        possible = []
        for _, rule in eligibility.iterrows():
            offer = offers.loc[offers.offer_id == rule.offer_id].iloc[0]
            allowed = rule.allowed_segments.split(";")
            margin_pct = 100 * (price - price * offer.discount_pct / 100) / max(price, 1)
            ok = (bool(rule.is_active) and risk >= float(rule.min_risk_score) and seg in allowed and
                  float(offer.discount_pct) <= float(rule.max_discount_pct) and
                  margin_pct >= max(float(rule.min_margin_pct), float(offer.min_margin_pct)))
            if ok:
                possible.append((offer, rule))
        if not possible:
            campaign.append({"campaign_contact_id": f"CONTACT-{cid}-2026-01", "customer_id": cid,
                "offer_id": "", "eligibility_rule_id": "", "contact_date": "2026-01-05",
                "eligibility_status": "INELIGIBLE", "exception_reason": "NO_RULE_MATCH",
                "experiment_group": "NOT_ASSIGNED", "contact_status": "NOT_SENT", "assignment_seed": seed,
                "issue_type": ""})
            continue
        # Select one offer deterministically among eligible offers; then randomize group.
        offer, rule = possible[int(rng.integers(0, len(possible)))]
        treatment = bool(rng.random() < .5)
        group = "TREATMENT" if treatment else "CONTROL"
        # Contact only treatment. Control is an experiment assignment, not a contact.
        sent = treatment
        contact_status = "SENT" if sent else "HOLDOUT"
        campaign.append({"campaign_contact_id": f"CONTACT-{cid}-2026-01", "customer_id": cid,
            "offer_id": offer.offer_id, "eligibility_rule_id": rule.eligibility_rule_id,
            "contact_date": "2026-01-05", "eligibility_status": "ELIGIBLE", "exception_reason": "",
            "experiment_group": group, "contact_status": contact_status, "assignment_seed": seed,
            "issue_type": ""})
        # Outcome depends on risk and treatment, creating measurable but not guaranteed lift.
        base_retention_prob = max(.35, min(.96, .92 - risk * .45))
        offer_effect = .10 if treatment else 0.0
        retained = bool(rng.random() < min(.99, base_retention_prob + offer_effect))
        retentions.append({"retention_outcome_id": f"RET-{cid}-2026-01", "campaign_contact_id": f"CONTACT-{cid}-2026-01",
            "customer_id": cid, "offer_id": offer.offer_id, "measurement_date": "2026-04-05",
            "retained_90d": int(retained), "offer_cost": round(float(offer.unit_cost) if treatment else 0.0, 2),
            "estimated_margin_after_offer": round(price * (1 - float(offer.discount_pct)/100) - (float(offer.unit_cost) if treatment else 0), 2),
            "issue_type": ""})

    campaign_df = pd.DataFrame(campaign)
    retention_df = pd.DataFrame(retentions)

    ground_truth = []
    if inject_anomalies and n >= 4:
        # Labelled edge cases are injected only into designated records; anomaly IDs are preserved in truth file.
        campaign_df.loc[0, ["eligibility_status", "exception_reason", "contact_status", "issue_type"]] = ["INELIGIBLE", "FORCED_INELIGIBLE_SEND", "SENT", "INELIGIBLE_OFFER_SENT"]
        ground_truth.append({"anomaly_id": "ANOM-0001", "entity": "CampaignContact", "record_id": campaign_df.loc[0, "campaign_contact_id"], "issue_type": "INELIGIBLE_OFFER_SENT", "expected_detection": "A contact marked SENT must not be INELIGIBLE", "severity": "HIGH"})
        campaign_df.loc[1, ["experiment_group", "contact_status", "issue_type"]] = ["CONTROL", "SENT", "TREATMENT_CONTROL_LEAKAGE"]
        ground_truth.append({"anomaly_id": "ANOM-0002", "entity": "CampaignContact", "record_id": campaign_df.loc[1, "campaign_contact_id"], "issue_type": "TREATMENT_CONTROL_LEAKAGE", "expected_detection": "Control group must not receive the retention offer", "severity": "HIGH"})
        if len(retention_df) > 0:
            # Duplicate attribution is explicitly labelled, not hidden.
            r = retention_df.iloc[0].copy()
            r["retention_outcome_id"] = "RET-ANOM-0003"
            r["issue_type"] = "MULTIPLE_OFFER_ATTRIBUTION"
            r["campaign_contact_id"] = retention_df.iloc[0]["campaign_contact_id"]
            retention_df = pd.concat([retention_df, pd.DataFrame([r])], ignore_index=True)
            ground_truth.append({"anomaly_id": "ANOM-0003", "entity": "RetentionOutcome", "record_id": "RET-ANOM-0003", "issue_type": "MULTIPLE_OFFER_ATTRIBUTION", "expected_detection": "A customer should have at most one attributed retention outcome in this single-offer experiment", "severity": "MEDIUM"})
        # Churn label before prediction date
        churn_outcomes.loc[2, ["churned_within_horizon", "churn_date", "issue_type"]] = [1, "2025-12-15", "CHURN_BEFORE_PREDICTION_DATE"]
        ground_truth.append({"anomaly_id": "ANOM-0004", "entity": "ChurnOutcome", "record_id": churn_outcomes.loc[2, "churn_outcome_id"], "issue_type": "CHURN_BEFORE_PREDICTION_DATE", "expected_detection": "A forward-horizon churn date must be after prediction_date and within horizon", "severity": "HIGH"})

    tables = {
        "Customer": customers, "Subscription": subscriptions, "UsageSnapshot": usage_df,
        "BillingEvent": billing_df, "SupportCase": support_df, "Offer": offers,
        "EligibilityRule": eligibility, "CampaignContact": campaign_df,
        "ChurnOutcome": churn_outcomes, "RetentionOutcome": retention_df
    }
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
        df.to_json(out / f"{name}.json", orient="records", indent=2, date_format="iso")
    pd.DataFrame(ground_truth, columns=["anomaly_id","entity","record_id","issue_type","expected_detection","severity"]).to_csv(out / "ground_truth.csv", index=False)

    # Simple schema/data manifest and checksums for reproducibility.
    manifest = {"seed": int(seed), "scale": n, "prediction_date": str(PREDICTION_DATE.date()),
                "churn_horizon_days": CHURN_HORIZON_DAYS, "tables": {}}
    for name, df in tables.items():
        csv_path = out / f"{name}.csv"
        manifest["tables"][name] = {"rows": int(len(df)), "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest()}
        (out / "source_manifest.json").write_text(json.dumps(manifest, indent=2))
    validation = validate_tables(tables)
    validation["retention_metrics"] = calculate_retention_metrics(tables)
    (out / "validation_summary.json").write_text(json.dumps(validation, indent=2))
    return tables, validation

def calculate_retention_metrics(tables):
    contacts = tables["CampaignContact"]
    outcomes = tables["RetentionOutcome"]

    experiment = outcomes.merge(
        contacts[
            ["campaign_contact_id", "experiment_group"]
        ],
        on="campaign_contact_id",
        how="left",
        validate="many_to_one"
    )

    results = {}

    for group in ["TREATMENT", "CONTROL"]:
        subset = experiment[
            experiment["experiment_group"] == group
        ]

        results[group] = {
            "customers": int(len(subset)),
            "retention_rate": (
                float(subset["retained_90d"].mean())
                if len(subset) > 0 else None
            ),
            "total_offer_cost": float(subset["offer_cost"].sum())
        }

    treatment_rate = results["TREATMENT"]["retention_rate"]
    control_rate = results["CONTROL"]["retention_rate"]

    if treatment_rate is not None and control_rate is not None:
        lift = treatment_rate - control_rate

        results["incremental_retention_lift"] = float(lift)

        additional_retained = (
            lift * results["TREATMENT"]["customers"]
        )

        treatment_cost = results["TREATMENT"]["total_offer_cost"]

        results["cost_per_additional_retained_customer"] = (
            float(treatment_cost / additional_retained)
            if additional_retained > 0 else None
        )
    else:
        results["incremental_retention_lift"] = None
        results["cost_per_additional_retained_customer"] = None

    return results

def validate_tables(t):
    issues = []
    def duplicate(df, key, name):
        if df[key].duplicated().any(): issues.append(f"{name}: duplicate primary key {key}")
    duplicate(t["Customer"], "customer_id", "Customer")
    duplicate(t["Subscription"], "subscription_id", "Subscription")
    duplicate(t["UsageSnapshot"], "snapshot_id", "UsageSnapshot")
    duplicate(t["BillingEvent"], "billing_event_id", "BillingEvent")
    duplicate(t["SupportCase"], "support_case_id", "SupportCase")
    duplicate(t["Offer"], "offer_id", "Offer")
    duplicate(t["EligibilityRule"], "eligibility_rule_id", "EligibilityRule")
    duplicate(t["CampaignContact"], "campaign_contact_id", "CampaignContact")
    duplicate(t["ChurnOutcome"], "churn_outcome_id", "ChurnOutcome")
    # Duplicate retention ID is invalid; duplicate attribution intentionally detected separately.
    duplicate(t["RetentionOutcome"], "retention_outcome_id", "RetentionOutcome")
    customers = set(t["Customer"].customer_id)
    subs = set(t["Subscription"].subscription_id)
    offers = set(t["Offer"].offer_id)
    contacts = set(t["CampaignContact"].campaign_contact_id)
    if not set(t["Subscription"].customer_id) <= customers: issues.append("Subscription: orphan customer_id")
    if not set(t["UsageSnapshot"].subscription_id) <= subs: issues.append("UsageSnapshot: orphan subscription_id")
    if not set(t["BillingEvent"].subscription_id) <= subs: issues.append("BillingEvent: orphan subscription_id")
    if not set(t["SupportCase"].customer_id) <= customers: issues.append("SupportCase: orphan customer_id")
    if not set(t["SupportCase"].subscription_id) <= subs: issues.append("SupportCase: orphan subscription_id")
    if not set(t["EligibilityRule"].offer_id) <= offers: issues.append("EligibilityRule: orphan offer_id")
    c = t["CampaignContact"]
    nonblank_offer = set(c.loc[c.offer_id.fillna("") != "", "offer_id"])
    if not nonblank_offer <= offers: issues.append("CampaignContact: orphan offer_id")
    if not set(t["RetentionOutcome"].campaign_contact_id) <= contacts: issues.append("RetentionOutcome: orphan campaign_contact_id")
    if not set(t["RetentionOutcome"].customer_id) <= customers: issues.append("RetentionOutcome: orphan customer_id")
    if (t["UsageSnapshot"].usage_units < 0).any(): issues.append("UsageSnapshot: negative usage")
    if not set(t["BillingEvent"].payment_status) <= {"PAID","FAILED"}: issues.append("BillingEvent: invalid payment_status")
    if not set(c.experiment_group) <= {"TREATMENT","CONTROL","NOT_ASSIGNED"}: issues.append("CampaignContact: invalid experiment_group")
    
    # Independently detect business-rule violations.
    campaign = t["CampaignContact"]
    churn = t["ChurnOutcome"]
    retention = t["RetentionOutcome"]

    detected = {}

    # 1. Ineligible customer must not receive an offer.
    detected["INELIGIBLE_OFFER_SENT"] = int((
        (campaign["eligibility_status"] == "INELIGIBLE") &
        (campaign["contact_status"] == "SENT")
    ).sum())

    # 2. Control customers must not receive the offer.
    detected["TREATMENT_CONTROL_LEAKAGE"] = int((
        (campaign["experiment_group"] == "CONTROL") &
        (campaign["contact_status"] == "SENT")
    ).sum())

    # 3. Positive churn labels must have valid dates.
    prediction = pd.to_datetime(churn["prediction_date"], errors="coerce")
    churn_date = pd.to_datetime(churn["churn_date"], errors="coerce")
    horizon_end = prediction + pd.to_timedelta(
        pd.to_numeric(churn["horizon_days"], errors="coerce"), unit="D"
    )
    positive = churn["churned_within_horizon"].eq(1)

    invalid_churn = positive & (
        churn_date.isna() |
        (churn_date <= prediction) |
        (churn_date > horizon_end)
    )
    detected["CHURN_BEFORE_PREDICTION_DATE"] = int(invalid_churn.sum())

    # 4. A customer must not have multiple attributed outcomes
    # in this single-offer campaign.
    duplicate_attribution = retention["customer_id"].duplicated(keep=False)
    detected["MULTIPLE_OFFER_ATTRIBUTION"] = int(
        duplicate_attribution.sum()
    )

    # Expected anomalies are reported separately and must not make base referential integrity fail.
    expected_anomalies = {
        "INELIGIBLE_OFFER_SENT": int((c.issue_type == "INELIGIBLE_OFFER_SENT").sum()),
        "TREATMENT_CONTROL_LEAKAGE": int((c.issue_type == "TREATMENT_CONTROL_LEAKAGE").sum()),
        "CHURN_BEFORE_PREDICTION_DATE": int((t["ChurnOutcome"].issue_type == "CHURN_BEFORE_PREDICTION_DATE").sum()),
        "MULTIPLE_OFFER_ATTRIBUTION": int((t["RetentionOutcome"].issue_type == "MULTIPLE_OFFER_ATTRIBUTION").sum())
    }
    
    return {
        "passed_structural_checks": len(issues) == 0,
        "structural_issues": issues,
        "expected_anomalies_detected_by_label": expected_anomalies,
        "detected_business_rule_violations": detected,
        "row_counts": {k: int(len(v)) for k, v in t.items()}
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scale", type=int, default=20000)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", default="data/generated")
    p.add_argument("--no-anomalies", action="store_true")
    args = p.parse_args()
    tables, summary = generate(args.scale, args.seed, args.out, not args.no_anomalies)
    print(json.dumps(summary, indent=2))
