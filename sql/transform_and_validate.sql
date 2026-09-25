PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS fact_case;
CREATE TABLE fact_case AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY case_id
            ORDER BY source_extract_ts DESC, rowid DESC
        ) AS source_rank
    FROM raw_case
), canonical AS (
    SELECT
        case_id,
        submitted_datetime,
        submitted_date_key,
        CASE
            WHEN closed_datetime IS NOT NULL AND closed_datetime < submitted_datetime
                THEN datetime(submitted_datetime, '+' || CAST(ROUND(COALESCE(resolution_business_hours, 8) * 1.55) AS INTEGER) || ' hours')
            ELSE closed_datetime
        END AS closed_datetime,
        service_key,
        CAST(COALESCE(team_key, 0) AS INTEGER) AS team_key,
        campus_key,
        cohort_key,
        lifecycle_stage_key,
        channel_key,
        requester_type,
        case_type,
        CASE category
            WHEN 'Enrollment Changes' THEN 'Enrolment changes'
            WHEN 'Timetable & Class Allocation' THEN 'Timetable and class allocation'
            WHEN 'Wifi / Network' THEN 'Wi-Fi and network'
            WHEN 'HVAC/Temperature' THEN 'HVAC and temperature'
            ELSE category
        END AS category,
        priority,
        current_status,
        first_response_business_hours,
        triage_business_hours,
        assignment_business_hours,
        resolution_business_hours,
        first_response_sla_breached,
        resolution_sla_breached,
        handoff_count,
        reopened_flag,
        repeat_contact_14d,
        first_contact_resolution_flag,
        complexity_weight,
        staff_handle_hours,
        estimated_cost_aud,
        case_summary,
        synthetic_label,
        ai_theme,
        ai_summary,
        ai_recommended_owner,
        ai_confidence,
        ai_review_status,
        source_extract_ts,
        CASE WHEN team_key IS NULL THEN 1 ELSE 0 END AS dq_missing_owner_flag,
        CASE WHEN closed_datetime IS NOT NULL AND closed_datetime < submitted_datetime THEN 1 ELSE 0 END AS dq_repaired_datetime_flag
    FROM ranked
    WHERE source_rank = 1
)
SELECT
    *,
    CAST(strftime('%Y%m%d', closed_datetime) AS INTEGER) AS closed_date_key,
    CASE WHEN current_status = 'Resolved' THEN 1 ELSE 0 END AS eligible_resolution_flag,
    CASE WHEN current_status NOT IN ('Resolved','Merged Duplicate','Withdrawn','Cancelled') THEN 1 ELSE 0 END AS backlog_eligible_flag,
    CASE WHEN current_status = 'Resolved' AND resolution_sla_breached = 1 THEN 1 ELSE 0 END AS sla_breach_eligible_flag,
    CASE
        WHEN current_status = 'Resolved' AND resolution_business_hours <= 8 THEN '0–8h'
        WHEN current_status = 'Resolved' AND resolution_business_hours <= 24 THEN '9–24h'
        WHEN current_status = 'Resolved' AND resolution_business_hours <= 80 THEN '25–80h'
        WHEN current_status = 'Resolved' THEN '80h+'
        ELSE 'Open/Excluded'
    END AS resolution_time_band
FROM canonical;

DROP TABLE IF EXISTS fact_case_event;
CREATE TABLE fact_case_event AS SELECT * FROM raw_case_event;

DROP TABLE IF EXISTS fact_interaction;
CREATE TABLE fact_interaction AS SELECT * FROM raw_interaction;

DROP TABLE IF EXISTS fact_feedback;
CREATE TABLE fact_feedback AS
SELECT
    *,
    CAST(strftime('%Y%m%d', feedback_date) AS INTEGER) AS feedback_date_key,
    CASE WHEN csat_score >= 4 THEN 1 ELSE 0 END AS csat_positive_flag
FROM raw_feedback;

DROP TABLE IF EXISTS fact_capacity_weekly;
CREATE TABLE fact_capacity_weekly AS SELECT * FROM raw_capacity_weekly;

DROP TABLE IF EXISTS fact_work_order;
CREATE TABLE fact_work_order AS SELECT * FROM raw_work_order;

DROP TABLE IF EXISTS fact_digital_journey_daily;
CREATE TABLE fact_digital_journey_daily AS SELECT * FROM raw_digital_journey_daily;

DROP TABLE IF EXISTS fact_population_monthly;
CREATE TABLE fact_population_monthly AS SELECT * FROM raw_population_monthly;

DROP TABLE IF EXISTS fact_action_insight;
CREATE TABLE fact_action_insight AS SELECT * FROM raw_action_insight;

DROP TABLE IF EXISTS fact_demand_forecast;
CREATE TABLE fact_demand_forecast AS SELECT * FROM raw_demand_forecast;

DROP TABLE IF EXISTS forecast_model_evaluation;
CREATE TABLE forecast_model_evaluation AS SELECT * FROM raw_forecast_model_evaluation;

DROP TABLE IF EXISTS dim_date_curated;
CREATE TABLE dim_date_curated AS SELECT * FROM dim_date;

DROP TABLE IF EXISTS dim_service_curated;
CREATE TABLE dim_service_curated AS SELECT * FROM dim_service;

DROP TABLE IF EXISTS dim_team_curated;
CREATE TABLE dim_team_curated AS SELECT * FROM dim_team;

DROP TABLE IF EXISTS dim_campus_curated;
CREATE TABLE dim_campus_curated AS SELECT * FROM dim_campus;

DROP TABLE IF EXISTS dim_cohort_curated;
CREATE TABLE dim_cohort_curated AS SELECT * FROM dim_cohort;

DROP TABLE IF EXISTS dim_channel_curated;
CREATE TABLE dim_channel_curated AS SELECT * FROM dim_channel;

DROP TABLE IF EXISTS dim_sla_curated;
CREATE TABLE dim_sla_curated AS SELECT * FROM dim_sla;

DROP TABLE IF EXISTS dim_lifecycle_stage_curated;
CREATE TABLE dim_lifecycle_stage_curated AS SELECT * FROM dim_lifecycle_stage;

DROP TABLE IF EXISTS data_quality_issues;
CREATE TABLE data_quality_issues AS
SELECT
    'Duplicate source row' AS issue_type,
    case_id AS record_id,
    'raw_case' AS source_table,
    'Lower-ranked duplicate retained only in raw layer' AS resolution
FROM (
    SELECT case_id, COUNT(*) AS duplicate_count
    FROM raw_case
    GROUP BY case_id
    HAVING COUNT(*) > 1
)
UNION ALL
SELECT
    'Missing owner',
    case_id,
    'raw_case',
    'Mapped to Unknown team key 0'
FROM fact_case
WHERE dq_missing_owner_flag = 1
UNION ALL
SELECT
    'Invalid close timestamp',
    case_id,
    'raw_case',
    'Repaired from submitted timestamp and resolution duration'
FROM fact_case
WHERE dq_repaired_datetime_flag = 1;

CREATE INDEX IF NOT EXISTS idx_fact_case_submitted ON fact_case(submitted_datetime);
CREATE INDEX IF NOT EXISTS idx_fact_case_service ON fact_case(service_key);
CREATE INDEX IF NOT EXISTS idx_fact_event_case ON fact_case_event(case_id);
CREATE INDEX IF NOT EXISTS idx_fact_interaction_case ON fact_interaction(case_id);
