# Snowflake dbt Mesh POC: Snowpipe + dbt Projects + Airflow + Streamlit

A 2-week proof of concept demonstrating a full ELT pipeline in Snowflake leveraging dbt Projects on Snowflake, with Airflow orchestration and Streamlit in Snowflake (SiS) for consumption. The goal is to learn and document the patterns for a future production platform built around domain-aligned dbt projects, mesh-style data products, and event-driven orchestration.

## Project Goal

Build an end-to-end ELT platform demonstration that ingests data from S3 via Snowpipe, transforms it through two domain-aligned dbt projects plus a cross-domain derived project, orchestrates the flow via Airflow, and surfaces results in a Streamlit in Snowflake app.

This is a **sandbox for the team to learn patterns**, not a production-grade showcase. Prioritize pattern clarity and documentation over polish, scale, or feature breadth.

## Success Criteria

- A new file dropped in S3 cascades through Snowpipe, both domain dbt projects, the derived dbt project, and is visible in the Streamlit app — without manual intervention beyond the file drop.
- The team can articulate the mesh-aligned pattern of "domain projects publish marts, derived projects compose them."
- Documentation (README + ARCHITECTURE) is sufficient for an engineer not on the build team to stand up a similar setup.
- Total credit consumption stays under $200 on the trial account.

## Out of Scope (Phase 2 candidates)

These are explicitly deferred. Mention in ARCHITECTURE.md as future work:

- Snapshots / SCD Type 2
- Tagging, masking policies, governance
- CI/CD with GitHub Actions
- Cost observability dashboards
- Formal data product contracts
- Multiple warehouses for compute isolation
- Snowpipe Streaming / true real-time
- Cortex / LLM features
- External tables / Iceberg
- Replication / failover

## Architecture Overview

```
S3 (NOAA weather drops)        S3 (TLC trip data drops)
    │                              │
    │ S3 Event                     │ S3 Event
    ▼                              ▼
Snowpipe (auto-ingest)        Snowpipe (auto-ingest)
    │                              │
    ▼                              ▼
raw_db.weather                raw_db.trips
    │                              │
    │ ────── Airflow DAG (sensors on COPY_HISTORY) ──────┐
    │                                                     │
    ▼                                                     ▼
EXECUTE DBT PROJECT (weather)                EXECUTE DBT PROJECT (trips)
    │                                                     │
    ▼                                                     ▼
analytics_db.weather_marts                   analytics_db.trips_marts
                          │
                          │ Airflow waits for both
                          ▼
              EXECUTE DBT PROJECT (derived)
                          │
                          ▼
              analytics_db.derived.mart_trip_demand_weather
                          │
                          ▼
                  Streamlit in Snowflake app
```

## Tech Stack

- **Cloud Storage**: AWS S3 (existing trial-account-connected bucket)
- **Data Warehouse**: Snowflake (trial account)
- **Ingestion**: Snowpipe with auto-ingest via SQS
- **Transformation**: dbt Projects on Snowflake (dbt Core executed natively in Snowflake via `EXECUTE DBT PROJECT`)
- **Orchestration**: Apache Airflow (local Docker for the POC)
- **Visualization**: Streamlit in Snowflake
- **Data Sources**:
  - NYC TLC Yellow Taxi trip data (one month, e.g., January 2024)
  - NOAA NYC hourly weather data (one month, LaGuardia station)

## Datasets

### TLC Yellow Taxi
- Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Format: Parquet
- Volume: ~3M rows / ~50MB for one month of yellow taxi data
- Strategy: Download one month, split into 4-5 weekly chunks. Drop chunks into S3 on a manual or scripted schedule to demonstrate ongoing ingestion.

### NOAA NYC Weather
- Source: https://www.ncei.noaa.gov/cdo-web/
- Station: LaGuardia (LGA)
- Format: CSV
- Volume: ~720 hourly records for one month
- Strategy: Same chunked-drop pattern as TLC.

## Repository Structure

The project is organized as a **monorepo** containing multiple dbt projects alongside infra and Streamlit code. dbt Projects on Snowflake supports this pattern: a single Git repository can hold multiple dbt projects, each in its own subdirectory with its own `dbt_project.yml`. Each subdirectory is deployed as a separate `DBT PROJECT` object in Snowflake by pointing `CREATE DBT PROJECT ... FROM` at the appropriate subdirectory of the Git stage.

Why monorepo for the POC:

- One Git remote to clone, one CI surface, one place for the team to navigate
- Atomic PRs that touch multiple projects (e.g., adding a column to a trips mart and updating its consumer in `dbt_derived`) stay in a single review
- Cross-project navigation is easier in editors
- Deployment is still cleanly separated — three independent `DBT PROJECT` objects with independent versioning, execution, and failure domains
- Pattern extends naturally as the platform grows: domains can split into separate repos later when team boundaries justify it, without rearchitecting how Snowflake deploys the projects

```
snowflake-dbt-mesh-poc/
├── README.md                       # Top-level project README
├── ARCHITECTURE.md                 # Top-level architecture document
├── infra/                          # Snowflake DDL, S3 setup, Airflow
│   ├── README.md
│   ├── snowflake/                  # Storage integration, stages, pipes, warehouses, RBAC
│   ├── airflow/                    # DAG definitions, Docker setup
│   └── sample_data_loader/         # Script to chunk and drop data into S3
├── dbt_trips/                      # Trips domain dbt project
│   ├── dbt_project.yml
│   ├── README.md
│   └── ... standard dbt structure
├── dbt_weather/                    # Weather domain dbt project
│   ├── dbt_project.yml
│   ├── README.md
│   └── ... standard dbt structure
├── dbt_derived/                    # Cross-domain derived dbt project
│   ├── dbt_project.yml
│   ├── README.md
│   └── ... standard dbt structure
└── streamlit_app/                  # SiS app code
    ├── README.md
    └── ... Streamlit code
```

### Deploying Multiple dbt Projects from a Monorepo

Each dbt project is deployed as its own `DBT PROJECT` object in Snowflake, pointing at its subdirectory in the Git stage. Example:

```sql
CREATE OR REPLACE DBT PROJECT analytics_db.dbt.trips_project
  FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_trips'
  DBT_VERSION = '1.10.15'
  DEFAULT_TARGET = 'prod';

CREATE OR REPLACE DBT PROJECT analytics_db.dbt.weather_project
  FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_weather'
  DBT_VERSION = '1.10.15'
  DEFAULT_TARGET = 'prod';

CREATE OR REPLACE DBT PROJECT analytics_db.dbt.derived_project
  FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_derived'
  DBT_VERSION = '1.10.15'
  DEFAULT_TARGET = 'prod';
```

These `DBT PROJECT` object definitions belong in `infra/snowflake/` as a separate `.sql` file (e.g., `dbt_projects.sql`) and run after the underlying databases, schemas, and warehouse exist.

## Snowflake Object Conventions

Set these conventions explicitly in `infra/snowflake/` and document them in ARCHITECTURE.md.

### Databases and Schemas

- `raw_db.trips` — Snowpipe target for TLC data (no transformations, append-only)
- `raw_db.weather` — Snowpipe target for NOAA data (no transformations, append-only)
- `analytics_db.trips_staging` — Trips staging models (1:1 with raw, light cleaning)
- `analytics_db.trips_marts` — Trips published marts (the domain's data products)
- `analytics_db.weather_staging` — Weather staging models
- `analytics_db.weather_marts` — Weather published marts
- `analytics_db.derived` — Cross-domain marts that join trips + weather

### Warehouses

For the POC, a single `wh_poc_xs` (X-Small) warehouse with 60-second auto-suspend is sufficient. Document in ARCHITECTURE.md that a production version of this platform would split this into ingest, transform, and BI warehouses for compute isolation and cost attribution.

### Resource Monitor

Set an account-level resource monitor with a hard suspend at $200 of credit consumption. This is non-negotiable on a trial account.

## Cross-Project Source Dependencies

The `dbt_derived` project consumes the published marts of `dbt_trips` and `dbt_weather` via `{{ source() }}` declarations pointing at `analytics_db.trips_marts` and `analytics_db.weather_marts`.

This is the simpler "Option A" pattern. The "Option B" mesh-proper pattern (explicit published-mart schemas with formal contracts) is documented in ARCHITECTURE.md as the production-platform target.

## Build Plan: 2-Week Breakdown

### Week 1: Ingest + Transform

- **Days 1–2**: S3 setup, Snowflake storage integration, stages, file formats, Snowpipes for both domains. Validate auto-ingest by dropping a file and watching it land in `raw_db`.
- **Days 3–4**: Stand up the three dbt projects. Get a basic raw → staging → mart flow working manually via `EXECUTE DBT PROJECT` in a worksheet.
- **Day 5**: Add `dbt test` calls (3-4 meaningful tests per project), source freshness, one incremental model (`fct_trips`).

### Week 2: Orchestrate + Visualize

- **Days 6–7**: Airflow DAG with `SnowflakeSqlSensor`s on `COPY_HISTORY`, fan-out to domain dbt runs, fan-in to derived dbt run. Validate end-to-end with a fresh file drop.
- **Days 8–9**: Streamlit in Snowflake app — three tabs (Trips, Weather, Combined Insights).
- **Day 10**: Buffer for breakage and documentation polish.

## Known Risks and Gotchas

- **dbt Projects on Snowflake is newer than dbt Core**. Logging access, error visibility, and selective model runs have rougher edges. Budget 2x time for debugging dbt failures.
- **Snowpipe IAM trust policy** is the most common setup failure. After creating the storage integration, run `DESC INTEGRATION ...` and copy the generated `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` into the AWS role's trust relationship.
- **Streamlit in Snowflake package whitelist** is restricted. Verify libraries before reaching for them.
- **30-day trial clock**: build + buffer = 2 weeks, leaving ~10 days of demo/iteration time. Plan accordingly.

## Documentation Requirements

Every directory listed in the repo structure has a `README.md`. The top-level `ARCHITECTURE.md` covers:

1. The overall data flow and component responsibilities
2. The mesh-aligned domain split rationale
3. Snowflake object conventions (databases, schemas, warehouses)
4. Cross-project source dependency pattern (current state and production target)
5. The deferred Phase 2 list
6. Operational notes (resource monitor, auto-suspend, trial-account caveats)

---

# Per-Project Specs

## `infra/`

### Scope

All non-dbt, non-Streamlit infrastructure: Snowflake DDL, S3 wiring, Airflow.

### Deliverables

- `snowflake/storage_integration.sql` — `CREATE STORAGE INTEGRATION` for the S3 bucket
- `snowflake/file_formats.sql` — Parquet format for TLC, CSV format for NOAA
- `snowflake/stages.sql` — External stages for trips and weather, scoped to subprefixes within the bucket
- `snowflake/raw_tables.sql` — `raw_db.trips.yellow_taxi`, `raw_db.weather.hourly_lga` table definitions
- `snowflake/pipes.sql` — Snowpipe definitions with `AUTO_INGEST = TRUE` and `PATTERN` filters
- `snowflake/warehouses.sql` — `wh_poc_xs` definition with auto-suspend
- `snowflake/resource_monitor.sql` — Account-level monitor with hard suspend at $200
- `snowflake/rbac.sql` — Single POC role with grants on all needed databases/schemas/warehouses. Document in ARCHITECTURE.md that a production version would split this into ingest, transform, and consume roles.
- `snowflake/git_repository.sql` — Git repository object pointing at the monorepo, used as the source for dbt project deployments
- `snowflake/dbt_projects.sql` — `CREATE DBT PROJECT` statements for `trips_project`, `weather_project`, and `derived_project`, each pointing at the corresponding subdirectory of the Git stage
- `airflow/docker-compose.yml` — Local Airflow setup (the Airflow runtime for this POC)
- `airflow/dags/poc_pipeline.py` — The orchestration DAG
- `airflow/connections.md` — Notes on the Snowflake connection setup in local Airflow (using Airflow connections UI or environment variables)
- `sample_data_loader/load_chunks.py` — Script that takes downloaded source files, splits them into chunks, and uploads to S3. Invoked manually during exploration and demo (no scheduling).

### Airflow DAG Pattern

```
              ┌─────────────────────────┐
              │ sensor_trips_loaded     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │ run_dbt_trips           │
              └────────────┬────────────┘
                           │
              ┌─────────────────────────┐
              │ sensor_weather_loaded   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │ run_dbt_weather         │
              └────────────┬────────────┘
                           │
                  (fan-in via TriggerRule)
                           │
              ┌────────────▼────────────┐
              │ run_dbt_derived         │
              └─────────────────────────┘
```

Sensors should poll `INFORMATION_SCHEMA.COPY_HISTORY` for recent successful loads on the corresponding raw table. The dbt run tasks call `EXECUTE DBT PROJECT` as a plain SQL statement via the Common SQL provider's `SQLExecuteQueryOperator` (the modern replacement for the deprecated `SnowflakeOperator`). For longer-running dbt projects, use `SnowflakeSqlApiOperator` in deferrable mode to release the Airflow worker slot while Snowflake executes.

There is intentionally **no Cosmos** in this architecture. Cosmos parses a local dbt project and runs `dbt-core` from the Airflow worker, which would defeat the entire point of dbt Projects on Snowflake (dbt runs natively inside Snowflake's managed runtime). Cosmos is the right answer for "Airflow + dbt Core somewhere"; the wrong answer for "Airflow + dbt Projects on Snowflake."

Example task definition:

```python
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

run_dbt_trips = SQLExecuteQueryOperator(
    task_id="run_dbt_trips",
    conn_id="snowflake_default",
    sql="""
        EXECUTE DBT PROJECT analytics_db.dbt.trips_project
        ARGS = 'run --select source:raw_trips+'
    """,
)
```

### README contents

- Setup steps (in order): bucket prep, storage integration, stages, pipes, IAM trust policy, validation
- How to manually run the data loader script to drop a chunk into S3
- How to start Airflow locally via Docker Compose
- Validation checklist (drop a file manually, watch it land, watch the DAG fire)

---

## `dbt_trips/`

### Scope

The trips domain dbt project. Owns the transformation from `raw_db.trips.yellow_taxi` into published trips marts in `analytics_db.trips_marts`.

### Models

**Staging** (`models/staging/`):
- `stg_trips__yellow_taxi.sql` — Light cleaning, type casting, column renaming. Materialized as a view.

**Marts** (`models/marts/`):
- `fct_trips.sql` — One row per trip. **Incremental**, keyed on a load timestamp or pickup datetime. The showpiece incremental model.
- `dim_pickup_zones.sql` — Pickup zone reference (from the TLC zone lookup table — bundle this as a seed).
- `agg_daily_revenue_by_zone.sql` — Daily aggregation of revenue, trip count, average fare by pickup zone.

**Seeds** (`seeds/`):
- `taxi_zones.csv` — TLC zone lookup, ~265 rows. Static reference data.

### Tests

At least 4 meaningful tests across `schema.yml` files:
- `unique` and `not_null` on `fct_trips.trip_id`
- `accepted_values` on `fct_trips.payment_type`
- `relationships` test from `fct_trips.pickup_zone_id` to `dim_pickup_zones.zone_id`
- A custom test or `dbt_utils.expression_is_true` checking that `fare_amount >= 0`

### Sources

Declare `raw_db.trips.yellow_taxi` as a source with a freshness check (`warn_after: { count: 6, period: hour }`).

### README contents

- Domain ownership statement (this is the Trips data product)
- Model lineage (staging → marts) with a brief description of each
- How to run locally (`EXECUTE DBT PROJECT ...` syntax)
- How to add a new model
- The published marts that `dbt_derived` depends on (contract surface)

---

## `dbt_weather/`

### Scope

The weather domain dbt project. Owns the transformation from `raw_db.weather.hourly_lga` into published weather marts in `analytics_db.weather_marts`.

### Models

**Staging** (`models/staging/`):
- `stg_weather__hourly_lga.sql` — Light cleaning, type casting, unit normalization (Fahrenheit to consistent units). Materialized as a view.

**Marts** (`models/marts/`):
- `fct_weather_hourly.sql` — One row per hour per station. Materialized as a table (volume is small enough that incremental adds complexity without benefit).
- `dim_weather_stations.sql` — Station reference, even if just one row for LGA. Establishes the pattern.
- `agg_daily_weather.sql` — Daily aggregation: avg/min/max temp, total precipitation, dominant condition.

### Tests

At least 3 meaningful tests:
- `unique` on `fct_weather_hourly` composite key (station_id, observation_hour)
- `not_null` on `fct_weather_hourly.temperature_f`
- A range test on temperature (`dbt_utils.accepted_range` between -30 and 120)

### Sources

Declare `raw_db.weather.hourly_lga` as a source with a freshness check.

### README contents

- Domain ownership statement (this is the Weather data product)
- Model lineage with descriptions
- How to run locally
- The published marts that `dbt_derived` depends on
- Note on why `fct_weather_hourly` is full-refresh, not incremental (volume rationale)

---

## `dbt_derived/`

### Scope

The cross-domain derived project. Joins trips and weather marts to produce derived data products. Demonstrates the mesh pattern of "downstream projects compose domain products."

### Models

**Staging** (`models/staging/`):
- None — consumes upstream marts directly via sources. The staging layer in this project is conceptually the upstream domains' marts.

**Marts** (`models/marts/`):
- `mart_trip_demand_weather.sql` — Joins `agg_daily_revenue_by_zone` with `agg_daily_weather`. One row per (date, zone) with weather context. The cross-domain showpiece.
- `mart_hourly_demand_vs_temperature.sql` — Hourly trip volume vs. hourly temperature, useful for the Streamlit "weather effect" chart.

### Sources

Declare upstream marts from `analytics_db.trips_marts` and `analytics_db.weather_marts` as sources. Document explicitly in `schema.yml` that these are domain data products being consumed by the derived project.

### Tests

At least 2 tests:
- `not_null` on the date/key columns of the joined marts
- A row-count sanity test (the derived mart should have at least one row per day in the loaded range)

### README contents

- The derived pattern explanation (this is what mesh consumers look like at production scale)
- Why this is a separate project rather than additional models in `dbt_trips` or `dbt_weather`
- The upstream contracts being consumed
- The downstream consumers (Streamlit app)

---

## `streamlit_app/`

### Scope

The Streamlit in Snowflake app surfacing the derived marts. Three tabs.

### Tabs

1. **Trips** — Charts and tables from `analytics_db.trips_marts`. Daily revenue trend, top zones by trip count, average fare distribution.
2. **Weather** — Charts from `analytics_db.weather_marts`. Daily temperature range, precipitation totals.
3. **Combined Insights** — The cross-domain payoff. Charts from `analytics_db.derived.mart_trip_demand_weather` showing relationships between weather conditions and ride demand.

### Stretch Goal (if time allows)

A header status panel showing:
- Last successful Snowpipe load time per source (from `COPY_HISTORY`)
- Last successful dbt run time per project (from event table or task history)
- "Data freshness" indicator (green/yellow/red based on staleness)

This demonstrates that the platform is aware of its own state and naturally extends into SLA conversations.

### README contents

- How to deploy to SiS
- How to develop locally (or note that SiS deployment is the dev loop)
- The data products being consumed (with database/schema/table references)
- How to add a new tab or chart

---

## Resolved Decisions

- **Airflow**: Runs locally on Docker. No durable instance for the POC.
- **Snowflake roles**: A single role for the POC. Role separation (ingest, transform, consume) is deferred and noted in ARCHITECTURE.md as future work.
- **Data loader**: Triggered manually during exploration and demo. No cron scheduling.
- **Demo date**: None. The 2-week breakdown is a working estimate, not a deadline.
