CREATE TABLE Customer (
  customer_id VARCHAR(20) PRIMARY KEY,
  signup_date DATE NOT NULL,
  region VARCHAR(10) NOT NULL CHECK (region IN ('NORTH','SOUTH','EAST','WEST')),
  segment VARCHAR(10) NOT NULL CHECK (segment IN ('BASIC','STANDARD','PREMIUM')),
  customer_status VARCHAR(12) NOT NULL,
  issue_type VARCHAR(64) NULL
);
CREATE TABLE Subscription (
  subscription_id VARCHAR(40) PRIMARY KEY,
  customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id),
  product_cohort VARCHAR(10) NOT NULL,
  plan_name VARCHAR(20) NOT NULL,
  monthly_price DECIMAL(12,2) NOT NULL CHECK (monthly_price >= 0),
  start_date DATE NOT NULL,
  end_date DATE NULL,
  subscription_status VARCHAR(12) NOT NULL,
  issue_type VARCHAR(64) NULL
);
CREATE TABLE Offer (
  offer_id VARCHAR(30) PRIMARY KEY,
  offer_name VARCHAR(80) NOT NULL,
  discount_pct DECIMAL(5,2) NOT NULL CHECK (discount_pct BETWEEN 0 AND 100),
  duration_months INT NOT NULL CHECK (duration_months > 0),
  unit_cost DECIMAL(12,2) NOT NULL CHECK (unit_cost >= 0),
  min_margin_pct DECIMAL(5,2) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  status VARCHAR(10) NOT NULL
);
-- Remaining tables follow the CSV data dictionary; preserve declared foreign keys.
-- Incremental lift should be measured as treatment retention rate minus control retention rate.
SELECT experiment_group,
       COUNT(*) AS assigned_customers,
       AVG(CAST(retained_90d AS DECIMAL(10,4))) AS retention_rate,
       SUM(offer_cost) AS total_offer_cost,
       AVG(estimated_margin_after_offer) AS avg_estimated_margin
FROM RetentionOutcome ro
JOIN CampaignContact cc ON cc.campaign_contact_id = ro.campaign_contact_id
GROUP BY experiment_group;

-- Data-quality check: control group must never receive an offer.
SELECT campaign_contact_id, customer_id, issue_type
FROM CampaignContact
WHERE experiment_group = 'CONTROL' AND contact_status = 'SENT';

-- Temporal label check: a valid positive label must occur after prediction date and within horizon.
SELECT churn_outcome_id, customer_id, issue_type
FROM ChurnOutcome
WHERE churned_within_horizon = 1
  AND (churn_date <= prediction_date
       OR churn_date > DATEADD(day, horizon_days, prediction_date));
