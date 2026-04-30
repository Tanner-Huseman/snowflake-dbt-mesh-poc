# Snowflake dbt Mesh POC

A 2-week proof of concept demonstrating a full ELT pipeline in Snowflake using **dbt Projects on Snowflake**, **Snowpipe** auto-ingest, **Apache Airflow** orchestration, and **Streamlit in Snowflake** for consumption.

The goal is to learn and document patterns for a future production platform built around domain-aligned dbt projects, mesh-style data products, and event-driven orchestration.

## Architecture

```
S3 (NOAA weather drops)        S3 (TLC trip data drops)
    │                              │
    │ S3 Event → SQS               │ S3 Event → SQS
    ▼                              ▼
Snowpipe (auto-ingest)        Snowpipe (auto-ingest)
    │                              │
    ▼                              ▼
raw_db.weather                raw_db.trips
    │                              │
    │ ── Airflow sensors (COPY_HISTORY) ──────────┐
    │                                              │
    ▼                                              ▼
EXECUTE DBT PROJECT (weather)    EXECUTE DBT PROJECT (trips)
    │                                              │
    ▼                                              ▼
analytics_db.weather_marts       analytics_db.trips_marts
                       │
                       │ Airflow fan-in
                       ▼
           EXECUTE DBT PROJECT (derived)
                       │
                       ▼
       analytics_db.derived.mart_trip_demand_weather
                       │
                       ▼
           Streamlit in Snowflake app
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full design documentation.

## Repository Structure

```
snowflake-dbt-mesh-poc/
├── PROGRESS.md                     # Build checklist ([ ] / [~] / [x])
├── ARCHITECTURE.md
├── infra/
│   ├── README.md
│   ├── snowflake/                  # DDL: storage integration, stages, pipes, RBAC
│   ├── airflow/                    # Docker Compose + DAG
│   └── sample_data_loader/         # Script to chunk and drop source files into S3
├── dbt_trips/                      # Trips domain dbt project
├── dbt_weather/                    # Weather domain dbt project
├── dbt_derived/                    # Cross-domain derived dbt project
└── streamlit_app/                  # Streamlit in Snowflake app
```

## Data Sources

| Source | Format | Volume | Description |
|--------|--------|--------|-------------|
| NYC TLC Yellow Taxi (Jan 2024) | Parquet | ~3M rows / ~50MB | One month of trip records, split into 4–5 weekly chunks |
| NOAA LCD LaGuardia (Jan 2024) | CSV | ~720 rows | Hourly weather observations, station `USW00014732` |

## Quick Start

### 1. Snowflake Infrastructure

Run the SQL files in `infra/snowflake/` in this order:

```
1. warehouses.sql
2. resource_monitor.sql
3. rbac.sql
4. storage_integration.sql    ← then update AWS IAM trust policy
5. file_formats.sql
6. stages.sql
7. raw_tables.sql
8. pipes.sql                  ← then configure S3 event notifications
9. git_repository.sql         ← then fetch and set up credentials
10. dbt_projects.sql
```

See `infra/README.md` for step-by-step setup instructions.

### 2. Drop Data into S3

```bash
cd infra/sample_data_loader
pip install -r requirements.txt
python load_chunks.py --source trips --file yellow_tripdata_2024-01.parquet --chunks 4
python load_chunks.py --source weather --file lcd_lga_2024_01.csv --chunks 4
```

### 3. Run dbt Projects (manual validation)

In a Snowflake worksheet:

```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'run';
EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'run';
EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'run';
```

### 4. Start Airflow

```bash
cd infra/airflow
docker compose up -d
# UI: http://localhost:8080 (admin/admin)
```

Configure the `snowflake_default` connection (see `infra/airflow/connections.md`), then trigger the `poc_pipeline` DAG.

### 5. Open the Streamlit App

Deploy `streamlit_app/app.py` to Streamlit in Snowflake. See `streamlit_app/README.md`.

## Success Criteria

- [ ] A file dropped in S3 cascades through Snowpipe → both domain dbt projects → derived project → visible in Streamlit, without manual intervention
- [ ] The team can articulate the mesh pattern: "domain projects publish marts; derived projects compose them"
- [ ] Documentation is sufficient for an engineer not on the build team to replicate the setup
- [ ] Total credit consumption under $200

## Progress

See [PROGRESS.md](PROGRESS.md) for the live build checklist.
