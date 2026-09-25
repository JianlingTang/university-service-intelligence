# Stakeholder Brief and Iteration Contract

## Decision owners

| Stakeholder | Decision this product supports |
|---|---|
| Executive sponsor, Operations | Which service friction should be prioritised and funded? |
| Student Operations lead | Where should routing, process or peak staffing change? |
| ICT service owner | Which digital journeys create repeat demand? |
| Campus Infrastructure lead | Which contractor/service hotspots require remediation? |
| Faculty operations partner | Which cohorts and lifecycle stages experience disproportionate friction? |
| Data steward | Which data-health issues undermine published metrics? |

## Agreed questions

1. Which service/category combinations create the largest avoidable staff effort and negative experience?
2. At which process stage does elapsed time accumulate?
3. When will forecast demand exceed productive capacity?
4. Are raw case volumes misleading after adjusting for population and lifecycle stage?
5. Which actions have an accountable owner, measurable target and review date?
6. What data-quality condition could invalidate a published conclusion?

## MVP acceptance criteria

- Every executive recommendation has at least two supporting metrics, a sample size, an owner and a success measure.
- Filters for date, service, campus, cohort, requester type and lifecycle stage behave consistently.
- Metric definitions are visible and reconcile to curated CSV/SQLite results.
- Synthetic and partial-period status are visible on every page.
- AI-generated results are not shown or implied in v1.

## Agile iteration backlog

| Priority | Increment | Hypothesis |
|---|---|---|
| P0 | Executive, bottleneck, experience and action pages | A four-page decision chain is sufficient for first stakeholder validation |
| P0 | Data health and reconciliation | Trust increases when metric defects and exclusions are visible |
| P1 | Demand forecast and scenario console | Capacity decisions improve when demand uncertainty is explicit |
| P1 | Drill-through to service/category | Owners need evidence without crowding the executive page |
| P2 | AI theme/summary/routing integration | Human-reviewed AI can reduce triage effort and surface emerging issues |
| P2 | Azure/Snowflake deployment | Shared governed refresh is required before institutional use |

