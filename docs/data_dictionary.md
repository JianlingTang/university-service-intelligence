# University Service Intelligence - Data Dictionary

> **Synthetic demonstration data. These records are not University of Sydney data or results.**

## Grain and purpose

| Table | Grain | Purpose |
|---|---|---|
| `FactCase` | One curated service case | Demand, resolution, SLA, cost, ownership and student-lifecycle analysis |
| `FactCaseEvent` | One workflow event per case | Historical case flow, stage time and as-of backlog reconstruction |
| `FactInteraction` | One contact per case | Repeat contact, channel and first-contact-resolution analysis |
| `FactFeedback` | One valid survey or pulse response | Student, staff and contractor experience metrics |
| `FactCapacityWeekly` | One team-week | Demand, workload, staffed capacity and capacity gap |
| `FactWorkOrder` | One contractor work order | Facilities SLA, rework, cost and vendor performance |
| `FactDigitalJourneyDaily` | One service-day | Self-service sessions, completion, abandonment and estimated deflection |
| `FactPopulationMonthly` | One month-campus-cohort-lifecycle combination | Denominator for cases per 1,000 active users |
| `FactActionInsight` | One evidence-backed recommendation | Issue, evidence, owner, baseline, target, outcome and review date |
| `FactDemandForecast` | One service-week-model version | Historical fit and 12-week demand/capacity forecast with 95% interval |
| `ForecastModelEvaluation` | One service-model evaluation | Holdout MAE, RMSE, WAPE and forecast bias |

## Dimensions

| Table | Key | Notes |
|---|---|---|
| `DimDate` | `date_key` | Daily calendar from the first data week to the end of the 12-week forecast; working-day, academic-phase, partial-period and `is_future` flags |
| `DimService` | `service_key` | Student Administration, IT Support and Facilities |
| `DimTeam` | `team_key` | Operational owner; key `0` is `Unknown` after data-quality remediation |
| `DimCampus` | `campus_key` | Synthetic campus segmentation |
| `DimCohort` | `cohort_key` | Student and staff requester groups |
| `DimLifecycleStage` | `lifecycle_stage_key` | Pre-enrolment, Commencing, Continuing, Completing or Staff service |
| `DimChannel` | `channel_key` | Portal, email, phone, chat or walk-in |
| `DimSLA` | `priority` | P1-P4 response and resolution targets in business hours |

## Important FactCase definitions

| Field | Definition |
|---|---|
| `eligible_resolution_flag` | 1 only for resolved cases; duplicate, withdrawn and cancelled cases are excluded |
| `backlog_eligible_flag` | 1 for cases still requiring operational action |
| `closed_date_key` | `yyyymmdd` of `closed_datetime`; blank while open. Inactive relationship to `DimDate` for close-date measures |
| `resolution_sla_breached` | Resolved case exceeded its priority-specific resolution target |
| `repeat_contact_14d` | Requester initiated at least one additional contact within 14 days |
| `first_contact_resolution_flag` | Resolved without requester repeat contact, handoff or reopen |
| `assignment_business_hours` | Business time between triage and assignment; primary routing bottleneck measure |
| `staff_handle_hours` | Synthetic productive effort, distinct from elapsed resolution time |
| `dq_missing_owner_flag` | Source owner was missing and mapped to the Unknown team |
| `dq_repaired_datetime_flag` | Invalid source close time was repaired in the curated layer |
| `ai_*` | Reserved integration fields; AI is not run in version 1 |

## Exclusions and guardrails

- Duplicate, withdrawn and cancelled cases are excluded from SLA and resolution denominators.
- Open backlog is reconstructed at the selected as-of date from submitted and closed dates; it is not a simple current-status count.
- Current partial month is visibly flagged and excluded from complete month-on-month comparisons.
- Group results with `n < 10` are suppressed; confidence intervals require `n >= 30`.
- Pre/post results are descriptive and must not be described as causal without an experimental or quasi-experimental design.
- Rates use active-user denominators and must not be compared using raw case volumes alone.

