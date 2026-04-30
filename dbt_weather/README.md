# dbt_weather

**Domain owner**: Data Platform  
**Data product**: NOAA LaGuardia hourly weather analytics  
**Raw source**: `raw_db.weather.hourly_lga` (Snowpipe, append-only)  
**Published marts**: `analytics_db.weather_marts.*`

---

## Model Lineage

```
raw_db.weather.hourly_lga  (source, via Snowpipe)
    │
    ▼
stg_weather__hourly_lga    (view, analytics_db.weather_staging)
    │
    ├──► fct_weather_hourly        (table, analytics_db.weather_marts)
    │       │
    │       └──► agg_daily_weather (table, analytics_db.weather_marts)
    │
    └──► dim_weather_stations      (table, analytics_db.weather_marts)
```

### Models

| Model | Materialization | Schema | Description |
|-------|----------------|--------|-------------|
| `stg_weather__hourly_lga` | view | `weather_staging` | NOAA parsing + type casting. Handles 'T' trace precipitation. |
| `fct_weather_hourly` | table | `weather_marts` | One row per (station, hour). ~720 rows for one month. |
| `dim_weather_stations` | table | `weather_marts` | Station reference (LaGuardia). One row for the POC. |
| `agg_daily_weather` | table | `weather_marts` | Daily temp range, precipitation, humidity, wind. |

---

## Running in Snowflake

**Full run:**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'run';
```

**Selective run (new data only):**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'run --select source:raw_weather+';
```

**Tests:**
```sql
EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'test';
```

---

## Tests

| Model | Test | Type |
|-------|------|------|
| `fct_weather_hourly` | `(station_id, observation_hour)` unique combination | dbt_utils.unique_combination_of_columns |
| `fct_weather_hourly` | `temperature_f` not_null | Generic |
| `fct_weather_hourly` | `temperature_f` between -30 and 120°F | dbt_utils.accepted_range |

---

## Why `fct_weather_hourly` is Full-Refresh, Not Incremental

One month of hourly weather data is ~720 rows (~50KB). The cost of a full table
rebuild is negligible compared to the added complexity of tracking an incremental
watermark and handling re-delivered observations. If the data volume ever exceeds
~100K rows (e.g., multiple years or multiple stations), an incremental model
becomes worth the complexity.

---

## NOAA CSV Quirks

- **`M`** (missing): handled by the file format `NULL_IF` clause → becomes `NULL`.
- **`T`** (trace precipitation): not a number; handled in the staging model → `0.001` inches.
- **`s`** suffix on precipitation values (e.g., `0.12s`): indicates a "suspected" value; the staging model strips it with `replace(hourlyprecipitation, 's', '')`.
- Station filter: the staging model filters to `station = 'USW00014732'` (LaGuardia). If the raw CSV includes other stations, they are excluded.

---

## Published Contract Surface

| Table | Consumer | Key columns |
|-------|----------|-------------|
| `analytics_db.weather_marts.fct_weather_hourly` | `dbt_derived` | `station_id`, `observation_hour`, `temperature_f`, `precipitation_in` |
| `analytics_db.weather_marts.agg_daily_weather` | `dbt_derived` | `weather_date`, `station_id`, `avg_temp_f`, `total_precip_in` |
