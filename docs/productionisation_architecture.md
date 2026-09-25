# Productionisation Architecture

The repository implements a local, reproducible reference pipeline. The following is a target production design, not a claim of deployment.

```mermaid
flowchart LR
    A[Service management exports] --> B[Azure Data Lake raw zone]
    C[Survey and feedback] --> B
    D[Workforce and contractor systems] --> B
    E[Digital journey events] --> B
    B --> F[Snowflake staging]
    F --> G[SQL quality rules and conformed dimensions]
    G --> H[Snowflake curated analytics schema]
    H --> I[Power BI semantic model]
    H --> J[Analytics Action Console API]
    H --> K[Forecast and future AI services]
    L[Purview/catalogue and access policy] -. governance .-> B
    L -. governance .-> H
    M[Monitoring and data-quality alerts] -. assurance .-> G
```

## Production controls

- Managed identity/service principal rather than embedded credentials.
- Row-level security by faculty or service owner where required.
- Development, test and production workspaces with deployment pipelines.
- Incremental refresh for case events and interactions.
- Source-to-target reconciliation, schema-drift alerts and failed-row quarantine.
- Model/version metadata for forecasts and future AI outputs.
- Human review, confidence thresholds and audit trail before AI-derived fields are published.

