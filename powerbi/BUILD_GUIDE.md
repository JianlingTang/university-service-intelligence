# Power BI Service Build Guide

Build the semantic model and report entirely in the browser at [app.powerbi.com](https://app.powerbi.com), then publish the report to the web. You do not need Windows or Power BI Desktop.

Files used:

- `powerbi/power_query.pq`: one typed query per table. It loads the CSVs from `data/curated` on GitHub.
- `powerbi/measures.dax`: all measures in one DAX query. It also returns a reconciliation row you can check.
- `powerbi/theme.json`: the report theme.
- `mockups/*.png`: the target layout for each page.

The model deliberately leaves out `fact_case_event` and `fact_interaction`. No page uses them, and loading them would add fact-to-fact paths that make filters ambiguous.

## 0. Prerequisites

1. **Account.** Power BI only accepts work or school accounts. Publish to web also needs the tenant setting *Publish to web* to be enabled (step 7). If you use a university tenant, its admin has probably disabled this setting. In that case, use a tenant where you are the admin (for example, one created by a Microsoft 365 Business trial). Then sign in to Power BI with that account.
2. **Stay in *My workspace*.** Publish to web from My workspace needs only a free Power BI license. Other workspaces need Pro.
3. **Public CSVs.** The CSVs are served from the public repository (the data is synthetic). This URL must download a file:
   `https://raw.githubusercontent.com/JianlingTang/university-service-intelligence/main/data/curated/dim_campus.csv`

## 1. Create the queries

1. In Power BI, open **Create** → **Get data** → **Blank query**.
2. Create each query in `power_query.pq`, in order. For each one: **New query → Blank query**, rename it to the `Query name` in the comment, open **Advanced editor**, and paste the body.
   - Create `BaseUrl` first. It points at this repository; change it only if you fork the repository.
   - Create `LoadCsv` next. It is a function, so it does not load a table.
   - Then create the 18 table queries (`DimDate` … `DataQualityIssues`).
3. When the first query asks for a connection, choose **Anonymous** authentication and privacy level **Public**.
4. Check that no column header shows an error icon. The column types are already set explicitly; do not let Power Query change them.
5. Choose **Create a semantic model only** and name it `University Service Intelligence`.

## 2. Model setup (semantic model → Editing mode)

1. **Calculated tables** (Home → New table):

   ```dax
   _Measures = { BLANK () }
   ```

   ```dax
   AgeingBand =
   DATATABLE (
       "band", STRING, "sort_order", INTEGER, "min_days", INTEGER, "max_days", INTEGER,
       { { "0–7 days", 1, 0, 7 }, { "8–14 days", 2, 8, 14 }, { "15–30 days", 3, 15, 30 }, { "30+ days", 4, 31, 100000 } }
   )
   ```

   Hide `_Measures[Value]`. `AgeingBand` stays disconnected.

2. **Calculated columns** on `FactFeedback` (New column). These link each survey to its case's resolution time band without a fact-to-fact relationship:

   ```dax
   resolution_time_band =
   LOOKUPVALUE ( FactCase[resolution_time_band], FactCase[case_id], FactFeedback[related_case_id] )
   ```

   ```dax
   resolution_band_order =
   SWITCH ( FactFeedback[resolution_time_band], "0–8h", 1, "9–24h", 2, "25–80h", 3, "80h+", 4, "Open/Excluded", 5 )
   ```

3. **Date table.** Right-click `DimDate` → **Mark as date table**, and choose `date`.
4. **Sort by column** (Properties pane):
   - `DimDate[month_name]` by `month_number`
   - `DimLifecycleStage[lifecycle_stage]` by `lifecycle_stage_key`
   - `AgeingBand[band]` by `sort_order`
   - `FactFeedback[resolution_time_band]` by `resolution_band_order`

## 3. Relationships

Open **Manage relationships** and first **delete any relationships that were auto-detected**, especially anything between two fact tables (for example `FactCase[case_id]` ↔ `FactWorkOrder[case_id]`). Then create the relationships below. Every one is many-to-one (the dimension is the "one" side) with a **single** cross-filter direction.

| From (many) | To (one) | Active |
|---|---|---|
| `FactCase[submitted_date_key]` | `DimDate[date_key]` | Yes |
| `FactCase[closed_date_key]` | `DimDate[date_key]` | **No** (used by `Cases Closed`) |
| `FactFeedback[feedback_date_key]` | `DimDate[date_key]` | Yes |
| `FactCapacityWeekly[week_date_key]` | `DimDate[date_key]` | Yes |
| `FactDemandForecast[week_date_key]` | `DimDate[date_key]` | Yes |
| `FactDigitalJourneyDaily[date_key]` | `DimDate[date_key]` | Yes |
| `FactPopulationMonthly[month_date_key]` | `DimDate[date_key]` | Yes |
| `FactCase`, `FactFeedback`, `FactCapacityWeekly`, `FactDemandForecast`, `FactDigitalJourneyDaily`, `FactActionInsight`, `ForecastModelEvaluation` `[service_key]` | `DimService[service_key]` | Yes |
| `FactCase`, `FactCapacityWeekly`, `FactWorkOrder` `[team_key]` | `DimTeam[team_key]` | Yes |
| `FactActionInsight[suggested_owner_team_key]` | `DimTeam[team_key]` | Yes |
| `FactCase`, `FactFeedback`, `FactWorkOrder`, `FactPopulationMonthly` `[campus_key]` | `DimCampus[campus_key]` | Yes |
| `FactCase`, `FactFeedback`, `FactPopulationMonthly` `[cohort_key]` | `DimCohort[cohort_key]` | Yes |
| `FactCase`, `FactPopulationMonthly` `[lifecycle_stage_key]` | `DimLifecycleStage[lifecycle_stage_key]` | Yes |
| `FactCase[channel_key]` | `DimChannel[channel_key]` | Yes |
| `FactCase[priority]` | `DimSLA[priority]` | Yes |

Do not relate `DimTeam` to `DimService`. `DimTeam[service_key]` is only a descriptive attribute.

Hide every `*_key` column and every `synthetic_label` column.

## 4. Measures

1. On the semantic model, choose **Write DAX queries**. If the option is greyed out, turn on *Users can edit data models in the Power BI service* in the workspace settings.
2. Paste all of `measures.dax` and select **Run**. The result is one row; compare it with section 5.
3. Select **Update model with changes**. This saves all 45 measures, with their descriptions, to `_Measures`.
4. Set format strings in the Properties pane. Ctrl-click to select several measures at once.
   - Counts: `#,##0`
   - Rates and WAPE: `0.0%`
   - Hours: `0.0`
   - AUD: `$#,##0`

## 5. Reconciliation

The **Run** in step 4 must return these values. They are computed independently from `data/curated` with the same logic.

| Measure | Expected |
|---|---|
| Cases Received | 18,000 |
| Cases Closed | 16,566 |
| Open Backlog As Of | 182 (matches `validation_summary.csv`) |
| Aged Backlog 7D As Of | 44 |
| SLA Compliance % | 64.0% |
| Median Resolution Business Hours | 29.15 |
| CSAT Positive % | 53.4% (n = 5,400) |
| Forecast Cases Next 12W | 2,070 |
| Forecast Capacity Gap Hours | −157.4 (a surplus) |
| Forecast WAPE | 13.3% |
| Data Quality Issues | 255 |

For the backlog ageing bands at the last actual date, expect 0–7 days = 138, 8–14 days = 44, and 0 in the older bands.

## 6. Report

Open the semantic model → **New report**. Then set up the report:

- **Theme.** View → Themes → Browse for themes → `theme.json`.
- **Canvas.** Use 16:9 on every page.
- **Top filter bar.** Put slicers for `DimService[service_name]` and `DimCampus[campus_name]` on every page, and link them with View → Sync slicers.
- **Synthetic-data badge.** Add a text box on every page: *Synthetic demonstration data — not actual University of Sydney results.*
- **Future-date filter.** DimDate runs 12 weeks past the data so the forecast has dates. On every visual with a date axis, **except the forecast chart**, add the visual filter `DimDate[is_future] = 0`.

Use `mockups/` for layout. Each bullet below is one visual.

### Page 1 · Executive Operational Health

- **KPI cards:** `Cases Received`, `Open Backlog As Of`, `SLA Compliance %`, `Median Resolution Business Hours`, `Display CSAT %`, `Forecast Capacity Gap Hours`.
- **Line chart:** axis `DimDate[month_start]`; values `Cases Received`, `Cases Closed`.
- **Scatter (bubble) chart** from `FactActionInsight`:
  - Values: `issue`
  - X: Sum `estimated_avoidable_staff_hours`
  - Y: Average `negative_experience_rate`
  - Size: Sum `users_affected`
  - Legend: `priority`
- **Table:** `issue`, `evidence_1_name`, `evidence_1_value`, `DimTeam[team_name]`, `recommended_action`, `next_review_date`.

### Page 2 · Bottlenecks & Capacity

- **Clustered bar:** `Median Triage Business Hours`, `Median Assignment Business Hours`, `Median Resolution Business Hours`. Add `DimService[service_name]` on the axis.
- **Column chart:** axis `AgeingBand[band]`; value `Open Backlog by Age Band`.
- **Forecast line chart:**
  - Axis: `FactDemandForecast[week_start]`
  - Values: Sum `actual_cases`, Sum `predicted_cases`
  - Error bars on predicted: lower `lower_95_cases`, upper `upper_95_cases`
  - **No** `is_future` filter on this visual.
- **Line and clustered column chart:**
  - Axis: `FactCapacityWeekly[week_start]`
  - Columns: Sum `required_handle_hours`, Sum `staffed_hours`
  - Line: `Capacity Gap Hours`
- **Matrix (Facilities drill-down):** rows `DimCampus[campus_name]` → `FactWorkOrder[category]`; values `Contractor On Time %`, `Contractor Rework %`.

### Page 3 · Experience & Equity

- **Line and clustered column chart:** axis `DimDate[month_start]`; columns `Valid Post Case Responses`; lines `Display CSAT %`, `Average Customer Effort`.
- **Matrix:** rows `DimCohort[cohort_name]`; columns `DimLifecycleStage[lifecycle_stage]`; value `Display Cases per 1,000`.
- **Column chart:** axis `FactFeedback[resolution_time_band]`; value `CSAT Positive %`. Filter out blank and `Open/Excluded`.
- **Bar chart:** axis `FactFeedback[feedback_theme]`; legend `respondent_type`; value Count of `feedback_id`, sorted descending.
- **Line chart:** axis `DimDate[month_start]`; values `Self Service Completion %`, `Repeat Contact 14D %`.

### Page 4 · Actions & Benefits

- **Table (action register):** `action_id`, `issue`, `DimTeam[team_name]`, `action_status`, `priority`, `next_review_date`. Use conditional-format **icons** on `priority` and `action_status`, not colour alone.
- **Table:** `action_id`, `success_measure`, `baseline_value`, `target_value`, `actual_value`, `unit`, with data bars on the three values. The units differ between actions, so one shared axis would mislead.
- **Clustered bar:** axis `issue`; values Sum `estimated_avoidable_staff_hours`, Sum `users_affected`.
- **Data-health cards:** `Data Quality Issues`, `Cases with Repaired Data %`, `Forecast WAPE`.

### Accessibility and QA

- Add alt text to every visual (Format → General → Alt text).
- Add tooltips for metric definitions. The measure descriptions from `///` show in the Data pane.
- Show `Valid Post Case Responses` next to CSAT. Use the `CSAT Wilson 95%` bounds only where n ≥ 30; the measures already return blank below that.
- Click through each page with a service slicer selected and confirm the cards change.

## 7. Publish to web

1. **Enable the tenant setting** (tenant admin only): Settings (gear) → **Admin portal** → **Tenant settings** → *Export and sharing settings* → **Publish to web** → Enabled → Apply. It can take a few minutes to take effect.
2. **Stop refresh.** On the semantic model settings, turn scheduled refresh **off**. The data is static.
3. **Create the embed code.** Open the report → **File → Embed report → Publish to web (public)** → Create embed code → Publish. Choose **Page 1** as the default page, and add a placeholder image (a screenshot of Page 1). The placeholder is shown during heavy usage.
4. **Share it.**
   - Copy the **link** for your resume and LinkedIn.
   - Copy the **iframe** for a portfolio site. At 16:9, `960 × 596` avoids letterboxing.
5. **Test it.** Open the link in a private browser window and check that all four pages and the slicers work without signing in.

Anyone with the link can see all the data in the model, not only what the visuals show. That is acceptable here only because the data is synthetic. You can manage or delete the link under Settings → **Manage embed codes**.
