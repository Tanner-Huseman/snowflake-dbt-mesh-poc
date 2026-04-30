# Architecture

## 1. Data Flow and Component Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│  SOURCE LAYER                                                     │
│  NYC TLC Yellow Taxi (Parquet)   NOAA LCD LaGuardia (CSV)        │
│  Manual chunk drops → S3         Manual chunk drops → S3         │
└───────────────────┬─────────────────────────┬───────────────────┘
                    │ S3 event → SQS           │ S3 event → SQS
                    ▼                          ▼
┌───────────────────────────────────────────────────────────────────┐
│  INGEST LAYER (Snowpipe AUTO_INGEST)                               │
│  raw_db.trips.yellow_taxi        raw_db.weather.hourly_lga        │
│  Append-only. No transforms.     Append-only. No transforms.      │
└───────────────────┬─────────────────────────┬─────────────────────┘
                    │ Airflow sensor           │ Airflow sensor
                    │ (COPY_HISTORY poll)      │ (COPY_HISTORY poll)
                    ▼                          ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  dbt_trips project        │    │  dbt_weather project              │
│  (EXECUTE DBT PROJECT)    │    │  (EXECUTE DBT PROJECT)            │
│                           │    │                                    │
│  staging/                 │    │  staging/                          │
│   stg_trips__yellow_taxi  │    │   stg_weather__hourly_lga          │
│                           │    │                                    │
│  marts/                   │    │  marts/                            │
│   fct_trips (incremental) │    │   fct_weather_hourly               │
│   dim_pickup_zones        │    │   dim_weather_stations             │
│   agg_daily_revenue_…     │    │   agg_daily_weather                │
│                           │    │                                    │
│  → analytics_db           │    │  → analytics_db                    │
│    .trips_staging         │    │    .weather_staging                │
│    .trips_marts           │    │    .weather_marts                  │
└──────────┬───────────────┘    └────────────────┬───────────────────┘
           │ Airflow fan-in (TriggerRule.ALL_DONE) │
           └────────────────────┬──────────────────┘
                                ▼
           ┌─────────────────────────────────────────┐
           │  dbt_derived project                      │
           │  (EXECUTE DBT PROJECT)                    │
           │                                           │
           │  Sources: analytics_db.trips_marts        │
           │           analytics_db.weather_marts      │
           │                                           │
           │  marts/                                   │
           │   mart_trip_demand_weather                │
           │   mart_hourly_demand_vs_temperature       │
           │                                           │
           │  → analytics_db.derived                  │
           └──────────────────────┬────────────────────┘
                                  ▼
           ┌─────────────────────────────────────────┐
           │  Streamlit in Snowflake                   │
           │  Tabs: Trips | Weather | Combined         │
           └─────────────────────────────────────────┘
```

### Component responsibilities

| Component | Responsibility | Owns |
|-----------|---------------|------|
| S3 + Snowpipe | Event-driven file ingestion | `raw_db` tables |
| `dbt_trips` | Trips domain transforms, published data products | `analytics_db.trips_*` |
| `dbt_weather` | Weather domain transforms, published data products | `analytics_db.weather_*` |
| `dbt_derived` | Cross-domain composition, downstream analytics | `analytics_db.derived` |
| Airflow DAG | Orchestration, sensors, dependency management | — |
| Streamlit app | Data product consumption, visualization | — |

---

## 2. Mesh-Aligned Domain Split Rationale

The two domain projects (`dbt_trips`, `dbt_weather`) are **independent owners** of their respective data products. Each project:

- Reads from its own `raw_db` schema
- Publishes marts to its own `analytics_db` schema
- Runs independently — a weather failure does not block trips transforms
- Has its own `EXECUTE DBT PROJECT` object in Snowflake, enabling independent scheduling and versioning

`dbt_derived` is a **consumer**, not an owner. It has no raw sources. It reads only from the published marts of the domain projects, modeling the downstream analytics use case (how does weather affect trip demand?).

This is the core mesh pattern at the POC scale: **domain projects publish; derived projects compose.** At production scale, the domain projects would be owned by separate teams with formal data product contracts (schema contracts, SLA agreements). The derived project would be owned by the analytics or data science team consuming those products.

### Why a monorepo?

At two-team scale, a monorepo reduces friction without sacrificing deployment independence:

- One Git remote, one CI surface, one place to navigate
- Atomic PRs spanning multiple projects (e.g., adding a column to a trips mart and updating its consumer in `dbt_derived`)
- Each project is still deployed as an independent `DBT PROJECT` object in Snowflake

As the platform grows and team boundaries harden, individual projects can split into separate repos without rearchitecting Snowflake deployments.

---

## 3. Snowflake Object Conventions

### Databases and Schemas

| Database | Schema | Owner Project | Purpose |
|----------|--------|---------------|---------|
| `raw_db` | `trips` | Snowpipe | Append-only TLC Parquet ingest target |
| `raw_db` | `weather` | Snowpipe | Append-only NOAA CSV ingest target |
| `analytics_db` | `trips_staging` | `dbt_trips` | 1:1 staging models (views, light cleaning) |
| `analytics_db` | `trips_marts` | `dbt_trips` | Published trips data products |
| `analytics_db` | `weather_staging` | `dbt_weather` | 1:1 staging models (views) |
| `analytics_db` | `weather_marts` | `dbt_weather` | Published weather data products |
| `analytics_db` | `derived` | `dbt_derived` | Cross-domain marts |
| `analytics_db` | `integrations` | Infra | Git repository + API integration objects |
| `analytics_db` | `dbt` | Infra | DBT PROJECT objects |

### Warehouses

POC uses a single `wh_poc_xs` (X-Small) warehouse with 60-second auto-suspend.

**Production note:** A production version of this platform should split compute into at minimum three warehouses for cost attribution and isolation:
- `wh_ingest` — Snowpipe-driven loads
- `wh_transform` — dbt project runs
- `wh_bi` — Streamlit queries and interactive workloads

### Naming conventions

- Databases: `snake_case` with a functional suffix (`_db`)
- Schemas: `snake_case` with a functional suffix (`_staging`, `_marts`, `_raw`)
- Tables/views: `snake_case`; marts prefixed by type (`fct_`, `dim_`, `agg_`, `mart_`)
- dbt projects: `dbt_<domain>` (e.g., `dbt_trips`)
- Snowflake DBT PROJECT objects: `<domain>_project` (e.g., `trips_project`)
- Snowpipe objects: `<domain>_pipe` (e.g., `trips_pipe`)

---

## 4. Cross-Project Source Dependency Pattern

### Current (Option A — direct source references)

`dbt_derived` declares `analytics_db.trips_marts` and `analytics_db.weather_marts` as `{{ source() }}` in `models/sources.yml`. There is no enforced contract — dbt_derived trusts that the upstream marts exist and have the expected columns.

This is the correct pattern for a POC where the domain and derived projects are maintained by the same small team.

### Production target (Option B — explicit data product contracts)

At production scale, each domain project should publish a formal contract:

1. A versioned `schema.yml` for each published mart, specifying column names, types, and `not_null` / `unique` constraints
2. The derived project pins to a specific contract version, failing loudly if the upstream schema changes in a breaking way
3. Ownership metadata (team, SLA, contact) is embedded in the schema YAML

This pattern maps directly to the [dbt contracts](https://docs.getdbt.com/docs/collaborate/govern/model-contracts) feature (dbt 1.5+) and enables the "published data product" framing at scale.

---

## 5. Deferred — Phase 2 Candidates

The following are explicitly out of scope for this POC. Document as future work when this platform is productionized:

- **Snapshots / SCD Type 2** — Track slowly changing dimensions (e.g., zone borough reassignments)
- **Tagging, masking policies, governance** — Column-level PII tagging, dynamic data masking
- **CI/CD with GitHub Actions** — Automated `dbt test` on PR, automated `CREATE DBT PROJECT` on merge
- **Cost observability dashboards** — Per-query credit attribution, warehouse utilization trends
- **Formal data product contracts** — Schema contracts with versioning (Option B above)
- **Multiple warehouses for compute isolation** — Separate ingest, transform, and BI warehouses
- **Snowpipe Streaming / true real-time** — Sub-minute latency ingestion
- **Cortex / LLM features** — Natural language querying over trip and weather data
- **External tables / Iceberg** — Open table format for the raw layer
- **Replication / failover** — Cross-region replication for HA

---

## 6. Operational Notes

### Resource monitor

An account-level resource monitor (`poc_resource_monitor`) is set with a **hard suspend at $200** of credit consumption. This is non-negotiable on a trial account. All warehouses are assigned to this monitor.

The monitor will `SUSPEND_IMMEDIATE` the warehouse, which will terminate running queries. Plan demos accordingly.

### Auto-suspend

`wh_poc_xs` is configured with `AUTO_SUSPEND = 60` (seconds). The warehouse starts on first query and suspends after 60 seconds of inactivity. On a trial account, this is the most important lever for controlling credit spend.

### Trial account clock

The Snowflake trial expires 30 days after account creation. The 2-week build plan + 10-day demo window fits within that window — but only if the build starts promptly. If the trial expires before the demo, create a new trial account and re-run the infra SQL scripts.

### Snowpipe IAM trust policy

After creating the storage integration, run:

```sql
DESC INTEGRATION poc_s3_integration;
```

Copy the values for `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` from the output. These must be placed in the AWS IAM role's trust policy before Snowpipe can access S3. This is the single most common setup failure for Snowpipe.

### dbt Projects on Snowflake — known rough edges

- **Log visibility**: Execution logs are less immediately accessible than `dbt Core` stdout. Check `INFORMATION_SCHEMA.QUERY_HISTORY` or Snowflake's Query Profile UI for dbt run details.
- **Selective model runs**: The `--select` syntax in `EXECUTE DBT PROJECT ARGS = 'run --select ...'` works but has less tooling support than dbt Core CLI. Test selectors manually in a worksheet before using them in the Airflow DAG.
- **Package installation**: `packages.yml` is resolved at project creation/update time in Snowflake. After updating `packages.yml`, re-create or update the DBT PROJECT object.
- **Budget 2x time for debugging** dbt failures compared to local dbt Core development.
