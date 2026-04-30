# dbt_trips

**Domain owner**: Data Platform  
**Data product**: NYC TLC Yellow Taxi trip analytics  
**Raw source**: `raw_db.trips.yellow_taxi` (Snowpipe, append-only)  
**Published marts**: `analytics_db.trips_marts.*`

---

## Model Lineage

```
raw_db.trips.yellow_taxi  (source, via Snowpipe)
    │
    ▼
stg_trips__yellow_taxi    (view, analytics_db.trips_staging)
    │
    ├──► fct_trips                     (incremental table, analytics_db.trips_marts)
    │
    ├──► dim_pickup_zones              (table, analytics_db.trips_staging → trips_marts)
    │      ▲
    │      └── seeds/taxi_zones.csv
    │
    └──► agg_daily_revenue_by_zone    (table, analytics_db.trips_marts)
```

### Models

| Model | Materialization | Schema | Description |
|-------|----------------|--------|-------------|
| `stg_trips__yellow_taxi` | view | `trips_staging` | Light cleaning + column renames. 1:1 with raw. |
| `fct_trips` | incremental (merge) | `trips_marts` | One row per trip. Keyed on `trip_id`. The showpiece incremental model. |
| `dim_pickup_zones` | table | `trips_marts` | TLC zone reference from seed. ~265 rows. |
| `agg_daily_revenue_by_zone` | table | `trips_marts` | Daily trip volume + revenue by pickup zone. |

---

## Running in Snowflake

**Full run:**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'run';
```

**Selective run (new data only, downstream of source):**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'run --select source:raw_trips+';
```

**Tests:**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'test';
```

**Source freshness:**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'source freshness';
```

**Seeds (run once, or after updating taxi_zones.csv):**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'seed';
```

---

## Tests

| Model | Test | Type |
|-------|------|------|
| `fct_trips` | `trip_id` unique + not_null | Generic |
| `fct_trips` | `payment_type` accepted_values (1–6) | Generic |
| `fct_trips` | `fare_amount >= 0` | dbt_utils.expression_is_true |
| `fct_trips` | `pickup_location_id` → `dim_pickup_zones.zone_id` | Relationship |

---

## Adding a New Model

1. Add the SQL file in `models/staging/` (view) or `models/marts/` (table).
2. Add a description + tests to the corresponding `schema.yml`.
3. If the model is consumed by `dbt_derived`, update `dbt_derived/models/sources.yml` if needed.
4. `ALTER GIT REPOSITORY ... FETCH` in Snowflake to pull the new file.
5. Re-run the project.

---

## Published Contract Surface

The following marts are consumed by `dbt_derived`. Column renames or type changes here are breaking changes:

| Table | Consumer | Key columns |
|-------|----------|-------------|
| `analytics_db.trips_marts.fct_trips` | `dbt_derived` | `trip_id`, `pickup_datetime`, `pickup_location_id`, `fare_amount`, `total_amount` |
| `analytics_db.trips_marts.agg_daily_revenue_by_zone` | `dbt_derived` | `trip_date`, `zone_id`, `trip_count`, `total_revenue`, `avg_fare` |

---

## Incremental Model Notes

`fct_trips` uses merge strategy keyed on `trip_id`. When new Parquet chunks land via Snowpipe:

- The staging view (`stg_trips__yellow_taxi`) sees all rows in `raw_db.trips.yellow_taxi`.
- The incremental filter `pickup_datetime > max(pickup_datetime)` in `fct_trips` selects only new rows.
- Duplicate rows (same vendor + pickup + dropoff timestamp) produce the same surrogate key and are merged (updated) rather than inserted.

To force a full refresh:
```sql
EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'run --full-refresh --select fct_trips';
```
