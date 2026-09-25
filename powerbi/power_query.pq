// Power Query (M) for building the semantic model in the Power BI service.
// Each block is one query: in Power Query, create a Blank query, rename it to the "Query name",
// open Advanced editor and paste the block's body. BUILD_GUIDE.md section 2 has the click path.
// Column types are explicit so every key matches its dimension and no numeric column loads as text.

// Query name: BaseUrl   (parameter; points at the public repository that serves data/curated)
"https://raw.githubusercontent.com/JianlingTang/university-service-intelligence/main/data/curated/" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]

// Query name: LoadCsv   (function; not loaded to the model)
// Web.Contents keeps BaseUrl static and passes the file as RelativePath, so scheduled refresh works in the service.
(fileName as text, columnTypes as list) as table =>
let
    Source = Csv.Document(
        Web.Contents(BaseUrl, [RelativePath = fileName & ".csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    BlanksToNull = Table.TransformColumns(Promoted, {}, each if _ = "" then null else _),
    Typed = Table.TransformColumnTypes(BlanksToNull, columnTypes, "en-US")
in
    Typed

// Query name: DimDate
LoadCsv("dim_date", {
    {"date_key", Int64.Type},
    {"date", type datetime},
    {"month_start", type datetime},
    {"year", Int64.Type},
    {"month_number", Int64.Type},
    {"month_name", type text},
    {"year_month", type text},
    {"quarter", type text},
    {"weekday", type text},
    {"is_weekend", Int64.Type},
    {"is_working_day", Int64.Type},
    {"academic_phase", type text},
    {"is_partial_period", Int64.Type},
    {"is_future", Int64.Type}
})

// Query name: DimService
LoadCsv("dim_service", {
    {"service_key", Int64.Type},
    {"service_name", type text},
    {"executive_owner", type text},
    {"is_student_facing", Int64.Type}
})

// Query name: DimTeam
LoadCsv("dim_team", {
    {"team_key", Int64.Type},
    {"team_name", type text},
    {"service_key", Int64.Type}
})

// Query name: DimCampus
LoadCsv("dim_campus", {
    {"campus_key", Int64.Type},
    {"campus_name", type text}
})

// Query name: DimCohort
LoadCsv("dim_cohort", {
    {"cohort_key", Int64.Type},
    {"cohort_name", type text},
    {"requester_type", type text},
    {"domestic_international", type text}
})

// Query name: DimChannel
LoadCsv("dim_channel", {
    {"channel_key", Int64.Type},
    {"channel_name", type text}
})

// Query name: DimLifecycleStage
LoadCsv("dim_lifecycle_stage", {
    {"lifecycle_stage_key", Int64.Type},
    {"lifecycle_stage", type text}
})

// Query name: DimSLA
LoadCsv("dim_sla", {
    {"priority", type text},
    {"first_response_target_business_hours", Int64.Type},
    {"resolution_target_business_hours", Int64.Type},
    {"sla_description", type text}
})

// Query name: FactCase
LoadCsv("fact_case", {
    {"case_id", type text},
    {"submitted_datetime", type datetime},
    {"submitted_date_key", Int64.Type},
    {"closed_datetime", type datetime},
    {"service_key", Int64.Type},
    {"team_key", Int64.Type},
    {"campus_key", Int64.Type},
    {"cohort_key", Int64.Type},
    {"lifecycle_stage_key", Int64.Type},
    {"channel_key", Int64.Type},
    {"requester_type", type text},
    {"case_type", type text},
    {"category", type text},
    {"priority", type text},
    {"current_status", type text},
    {"first_response_business_hours", type number},
    {"triage_business_hours", type number},
    {"assignment_business_hours", type number},
    {"resolution_business_hours", type number},
    {"first_response_sla_breached", Int64.Type},
    {"resolution_sla_breached", Int64.Type},
    {"handoff_count", Int64.Type},
    {"reopened_flag", Int64.Type},
    {"repeat_contact_14d", Int64.Type},
    {"first_contact_resolution_flag", Int64.Type},
    {"complexity_weight", type number},
    {"staff_handle_hours", type number},
    {"estimated_cost_aud", type number},
    {"case_summary", type text},
    {"synthetic_label", type text},
    {"ai_theme", type text},
    {"ai_summary", type text},
    {"ai_recommended_owner", type text},
    {"ai_confidence", type text},
    {"ai_review_status", type text},
    {"source_extract_ts", type datetime},
    {"dq_missing_owner_flag", Int64.Type},
    {"dq_repaired_datetime_flag", Int64.Type},
    {"closed_date_key", Int64.Type},
    {"eligible_resolution_flag", Int64.Type},
    {"backlog_eligible_flag", Int64.Type},
    {"sla_breach_eligible_flag", Int64.Type},
    {"resolution_time_band", type text}
})

// Query name: FactFeedback
LoadCsv("fact_feedback", {
    {"feedback_id", type text},
    {"feedback_date", type datetime},
    {"related_case_id", type text},
    {"related_work_order_id", type text},
    {"respondent_type", type text},
    {"service_key", Int64.Type},
    {"campus_key", Int64.Type},
    {"cohort_key", Int64.Type},
    {"feedback_type", type text},
    {"csat_score", Int64.Type},
    {"ces_score", Int64.Type},
    {"feedback_theme", type text},
    {"comment_text", type text},
    {"response_valid", Int64.Type},
    {"synthetic_label", type text},
    {"feedback_date_key", Int64.Type},
    {"csat_positive_flag", Int64.Type}
})

// Query name: FactCapacityWeekly
LoadCsv("fact_capacity_weekly", {
    {"week_start", type datetime},
    {"week_date_key", Int64.Type},
    {"team_key", Int64.Type},
    {"service_key", Int64.Type},
    {"fte_available", type number},
    {"absence_rate", type number},
    {"staffed_hours", type number},
    {"cases_received", Int64.Type},
    {"required_handle_hours", type number},
    {"forecast_handle_hours", type number},
    {"capacity_gap_hours", type number},
    {"capacity_gap_pct", type number},
    {"synthetic_label", type text}
})

// Query name: FactDemandForecast
LoadCsv("fact_demand_forecast", {
    {"week_start", type datetime},
    {"week_date_key", Int64.Type},
    {"service_key", Int64.Type},
    {"actual_cases", type number},
    {"predicted_cases", type number},
    {"lower_95_cases", type number},
    {"upper_95_cases", type number},
    {"predicted_handle_hours", type number},
    {"typical_capacity_hours", type number},
    {"predicted_capacity_gap_hours", type number},
    {"record_type", type text},
    {"model_version", type text},
    {"forecast_generated_date", type datetime},
    {"synthetic_label", type text}
})

// Query name: FactDigitalJourneyDaily
LoadCsv("fact_digital_journey_daily", {
    {"date", type datetime},
    {"date_key", Int64.Type},
    {"service_key", Int64.Type},
    {"self_service_sessions", Int64.Type},
    {"successful_completions", Int64.Type},
    {"abandonments", Int64.Type},
    {"estimated_cases_deflected", Int64.Type},
    {"completion_rate", type number},
    {"synthetic_label", type text}
})

// Query name: FactPopulationMonthly
LoadCsv("fact_population_monthly", {
    {"month_start", type datetime},
    {"month_date_key", Int64.Type},
    {"campus_key", Int64.Type},
    {"cohort_key", Int64.Type},
    {"lifecycle_stage_key", Int64.Type},
    {"active_users", Int64.Type},
    {"synthetic_label", type text}
})

// Query name: FactWorkOrder
LoadCsv("fact_work_order", {
    {"work_order_id", type text},
    {"case_id", type text},
    {"created_datetime", type datetime},
    {"completed_datetime", type datetime},
    {"campus_key", Int64.Type},
    {"team_key", Int64.Type},
    {"category", type text},
    {"contractor_name", type text},
    {"response_business_hours", type number},
    {"completion_business_hours", type number},
    {"on_time_flag", Int64.Type},
    {"rework_flag", Int64.Type},
    {"contractor_cost_aud", type number},
    {"synthetic_label", type text}
})

// Query name: FactActionInsight
LoadCsv("fact_action_insight", {
    {"action_id", type text},
    {"insight_date", type datetime},
    {"service_key", Int64.Type},
    {"campus_key", Int64.Type},
    {"cohort_key", Int64.Type},
    {"issue", type text},
    {"evidence_1_name", type text},
    {"evidence_1_value", type number},
    {"evidence_2_name", type text},
    {"evidence_2_value", type number},
    {"sample_size", Int64.Type},
    {"recommended_action", type text},
    {"suggested_owner_team_key", Int64.Type},
    {"success_measure", type text},
    {"baseline_value", type number},
    {"target_value", type number},
    {"actual_value", type number},
    {"unit", type text},
    {"action_status", type text},
    {"priority", type text},
    {"next_review_date", type datetime},
    {"estimated_avoidable_staff_hours", type number},
    {"negative_experience_rate", type number},
    {"users_affected", Int64.Type},
    {"sla_breach_rate", type number},
    {"synthetic_label", type text}
})

// Query name: ForecastModelEvaluation
LoadCsv("forecast_model_evaluation", {
    {"model_version", type text},
    {"service_key", Int64.Type},
    {"training_end_week", type datetime},
    {"holdout_weeks", Int64.Type},
    {"mae_cases", type number},
    {"rmse_cases", type number},
    {"wape", type number},
    {"forecast_bias", type number},
    {"synthetic_label", type text}
})

// Query name: DataQualityIssues
LoadCsv("data_quality_issues", {
    {"issue_type", type text},
    {"record_id", type text},
    {"source_table", type text},
    {"resolution", type text}
})

