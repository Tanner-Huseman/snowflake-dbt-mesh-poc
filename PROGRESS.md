# POC Progress

**Legend:** `[ ]` not started · `[~]` scaffolded / needs Snowflake validation · `[x]` validated in Snowflake

---

## Phase 1 — Infrastructure Setup (Days 1–2)

### Snowflake Object Setup
- [ ] Create `raw_db` and `analytics_db` databases (Snowflake UI or `CREATE DATABASE`)
- [~] `infra/snowflake/warehouses.sql` — `wh_poc_xs`, 60s auto-suspend
- [~] `infra/snowflake/resource_monitor.sql` — account-level hard suspend at $200
- [~] `infra/snowflake/rbac.sql` — `poc_role`, all needed grants
- [~] `infra/snowflake/storage_integration.sql` — S3 storage integration
- [ ] Run `DESC INTEGRATION poc_s3_integration` → copy IAM ARN + external ID into AWS role trust policy
- [~] `infra/snowflake/file_formats.sql` — Parquet (TLC) + CSV (NOAA)
- [~] `infra/snowflake/stages.sql` — `trips_stage` and `weather_stage` external stages
- [~] `infra/snowflake/raw_tables.sql` — `raw_db.trips.yellow_taxi` + `raw_db.weather.hourly_lga`
- [~] `infra/snowflake/pipes.sql` — Snowpipe with `AUTO_INGEST = TRUE`
- [ ] Configure S3 event notifications to point at each pipe's SQS queue ARN (`SHOW PIPES`)
- [ ] **Validate:** drop a file into S3 → confirm row lands in `raw_db`

### Data Loader
- [~] `infra/sample_data_loader/load_chunks.py` — chunk + upload script
- [ ] Download TLC Yellow Taxi January 2024 Parquet from NYC.gov
- [ ] Download NOAA LCD January 2024 CSV (LaGuardia, station `USW00014732`)
- [ ] Run loader to drop first chunk into S3

---

## Phase 2 — dbt Projects (Days 3–4)

### Snowflake Git + dbt Object Setup
- [~] `infra/snowflake/git_repository.sql` — API integration + Git repository object
- [~] `infra/snowflake/dbt_projects.sql` — `CREATE DBT PROJECT` for all three projects
- [ ] Create GitHub PAT, store as `poc_git_credentials` secret in Snowflake
- [ ] `ALTER GIT REPOSITORY poc_git_stage FETCH` — pull latest commits
- [ ] **Validate:** `EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'debug'`

### dbt_trips
- [~] `dbt_trips/dbt_project.yml`
- [~] `dbt_trips/packages.yml`
- [~] `dbt_trips/macros/generate_schema_name.sql`
- [~] `dbt_trips/seeds/taxi_zones.csv` — TLC zone lookup (~265 rows; download full CSV from TLC)
- [~] `dbt_trips/models/staging/stg_trips__yellow_taxi.sql`
- [~] `dbt_trips/models/staging/schema.yml` — source declaration + freshness + staging tests
- [~] `dbt_trips/models/marts/fct_trips.sql` — incremental, `unique_key = trip_id`
- [~] `dbt_trips/models/marts/dim_pickup_zones.sql`
- [~] `dbt_trips/models/marts/agg_daily_revenue_by_zone.sql`
- [~] `dbt_trips/models/marts/schema.yml` — all 4 required tests
- [ ] **Validate:** `EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'run'`

### dbt_weather
- [~] `dbt_weather/dbt_project.yml`
- [~] `dbt_weather/packages.yml`
- [~] `dbt_weather/macros/generate_schema_name.sql`
- [~] `dbt_weather/models/staging/stg_weather__hourly_lga.sql`
- [~] `dbt_weather/models/staging/schema.yml` — source + freshness + staging tests
- [~] `dbt_weather/models/marts/fct_weather_hourly.sql`
- [~] `dbt_weather/models/marts/dim_weather_stations.sql`
- [~] `dbt_weather/models/marts/agg_daily_weather.sql`
- [~] `dbt_weather/models/marts/schema.yml` — all 3 required tests
- [ ] **Validate:** `EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'run'`

### dbt_derived
- [~] `dbt_derived/dbt_project.yml`
- [~] `dbt_derived/packages.yml`
- [~] `dbt_derived/macros/generate_schema_name.sql`
- [~] `dbt_derived/models/sources.yml` — upstream mart declarations
- [~] `dbt_derived/models/marts/mart_trip_demand_weather.sql`
- [~] `dbt_derived/models/marts/mart_hourly_demand_vs_temperature.sql`
- [~] `dbt_derived/models/marts/schema.yml` — not_null tests
- [~] `dbt_derived/tests/assert_derived_mart_has_daily_rows.sql` — row-count sanity
- [ ] **Validate:** `EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'run'`

---

## Phase 3 — Testing & Incremental Validation (Day 5)

- [ ] `EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'test'` — all pass
- [ ] `EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'test'` — all pass
- [ ] `EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'test'` — all pass
- [ ] Run source freshness check on both domain projects
- [ ] Drop second TLC chunk → confirm `fct_trips` incremental merge adds only new rows
- [ ] Verify test counts: ≥4 trips tests, ≥3 weather tests, ≥2 derived tests

---

## Phase 4 — Airflow Orchestration (Days 6–7)

- [~] `infra/airflow/docker-compose.yml` — local Airflow + Snowflake provider
- [~] `infra/airflow/dags/poc_pipeline.py` — sensors + parallel dbt runs + fan-in
- [~] `infra/airflow/connections.md` — Snowflake connection setup notes
- [ ] `docker compose up` in `infra/airflow/` — confirm Airflow UI at `localhost:8080`
- [ ] Configure `snowflake_default` connection in Airflow UI (see `connections.md`)
- [ ] Trigger DAG manually — confirm sensors pass and all dbt runs complete
- [ ] Drop file into S3 → confirm end-to-end DAG fires automatically
- [ ] (Optional) Switch to `SnowflakeSqlApiOperator` deferrable mode for long dbt runs

---

## Phase 5 — Streamlit in Snowflake (Days 8–9)

- [~] `streamlit_app/app.py` — three tabs (Trips, Weather, Combined Insights)
- [ ] Deploy to Streamlit in Snowflake (Snowflake UI → Streamlit → New App)
- [ ] Confirm Trips tab renders daily revenue trend + zone charts
- [ ] Confirm Weather tab renders temp range + precipitation charts
- [ ] Confirm Combined Insights tab renders cross-domain mart charts
- [ ] (Stretch) Add data freshness status panel (COPY_HISTORY + dbt run timestamps)

---

## Phase 6 — Documentation & Polish (Day 10)

- [~] `README.md` (top-level)
- [~] `ARCHITECTURE.md`
- [~] `infra/README.md`
- [~] `dbt_trips/README.md`
- [~] `dbt_weather/README.md`
- [~] `dbt_derived/README.md`
- [~] `streamlit_app/README.md`
- [ ] End-to-end demo run: fresh file drop → all transforms → Streamlit reflects new data
- [ ] Verify total credit consumption < $200
- [ ] Review ARCHITECTURE.md Phase 2 deferred list is complete

---

## Known Blockers / Issues

_Add blockers here as they come up during validation._
