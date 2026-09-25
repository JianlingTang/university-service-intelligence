# Metric Catalog

| Metric | Definition | Decision supported |
|---|---|---|
| Cases received | Distinct valid cases submitted in filter context | Demand volume |
| Cases closed | Distinct cases with final status `Resolved` | Throughput |
| Open backlog as of | Submitted by selected date and not resolved/excluded by that date | Operational workload |
| Aged backlog 30+ days | Backlog open for more than 30 calendar days at as-of date | Escalation priority |
| Cases per 1,000 active users | Cases / average monthly active population x 1,000 | Fair cross-cohort comparison |
| Median resolution hours | Median business resolution time for eligible cases | Typical experience |
| P90 resolution hours | 90th percentile business resolution time | Tail risk |
| SLA compliance | 1 - eligible resolution breaches / eligible resolved cases | Service performance |
| First-contact resolution | Resolved without requester repeat, handoff or reopen / eligible resolved | Quality and avoidable demand |
| Repeat contact 14d | Cases with requester-initiated repeat within 14 days / cases | Failure demand |
| Handoff rate | Cases transferred at least once / eligible cases | Ownership clarity |
| Reopen rate | Resolved cases reopened / eligible resolved | Outcome quality |
| Cost per resolved case | Estimated operational cost / eligible resolved cases | Resource efficiency |
| Capacity gap | Required handle hours - staffed productive hours | Workforce planning |
| Self-service completion | Successful completions / self-service sessions | Digital experience |
| Contractor on-time | Work orders completed within target / completed work orders | Vendor performance |
| Contractor rework | Work orders requiring repeat work / work orders | Quality leakage |
| CSAT positive | Valid post-case responses scoring 4 or 5 / valid responses | Service satisfaction |
| Customer effort | Average valid CES score, 1 difficult to 5 easy | Friction |
| Forecast WAPE | Sum absolute forecast errors / sum actual holdout cases | Forecast reliability |

## Statistical presentation

- Show sample size beside every experience rate.
- Use Wilson 95% confidence intervals for CSAT positive rate when `n >= 30`.
- Use median and P90 together for skewed time distributions.
- Show percentage-point change for rates; do not use relative percent change without the baseline.
- Display forecast WAPE and model version on the capacity page.

