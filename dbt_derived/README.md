# dbt_derived

**Role**: Cross-domain derived project (mesh consumer)  
**Upstream contracts**: `analytics_db.trips_marts.*`, `analytics_db.weather_marts.*`  
**Published marts**: `analytics_db.derived.*`  
**Downstream consumer**: Streamlit in Snowflake app

---

## The Derived Pattern

This project demonstrates what a mesh consumer looks like at production scale:

- **No raw sources.** `dbt_derived` never touches `raw_db`. It reads only from domain-published marts.
- **Cross-domain composition.** Joining trips and weather is a derived concern — it belongs to neither the trips nor the weather domain team. Putting it in a separate project maintains clean domain ownership.
- **Independent failure domain.** A failure in `dbt_derived` does not affect the domain projects or their published data products.

In a production mesh architecture, this project would be owned by the analytics or data science team. The domain teams (`dbt_trips`, `dbt_weather`) are responsible for the quality and availability of their published marts; `dbt_derived` is responsible for the derived analytics built on top of them.

---

## Model Lineage

```
analytics_db.trips_marts.fct_trips
analytics_db.trips_marts.agg_daily_revenue_by_zone  ──┐
                                                       ├──► mart_trip_demand_weather
analytics_db.weather_marts.agg_daily_weather        ──┘
analytics_db.weather_marts.fct_weather_hourly       ──► mart_hourly_demand_vs_temperature
```

### Models

| Model | Materialization | Description |
|-------|----------------|-------------|
| `mart_trip_demand_weather` | table | (date, zone) × weather context. Primary analytical mart. |
| `mart_hourly_demand_vs_temperature` | table | Hourly trip volume vs. temperature for scatter charts. |

---

## Running in Snowflake

```sql
-- Full run (after both domain projects have completed)
EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'run';

-- Tests (includes the singular row-count test)
EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'test';
```

---

## Tests

| Model | Test | Type |
|-------|------|------|
| `mart_trip_demand_weather` | `trip_date` not_null | Generic |
| `mart_trip_demand_weather` | `zone_id` not_null | Generic |
| `mart_hourly_demand_vs_temperature` | `trip_hour` unique + not_null | Generic |
| `mart_trip_demand_weather` | At least one row per day in loaded range | Singular (`tests/`) |

---

## Upstream Contracts

If either upstream domain project changes a column name or type in the tables below, this project will break. Treat these as the **contract surface**:

| Upstream Table | Used by | Columns relied on |
|---------------|---------|-------------------|
| `trips_marts.fct_trips` | `mart_hourly_demand_vs_temperature` | `pickup_datetime`, `fare_amount`, `trip_distance` |
| `trips_marts.agg_daily_revenue_by_zone` | `mart_trip_demand_weather` | `trip_date`, `zone_id`, `zone_name`, `borough`, `trip_count`, `total_revenue`, `avg_fare` |
| `weather_marts.fct_weather_hourly` | `mart_hourly_demand_vs_temperature` | `observation_hour`, `temperature_f`, `precipitation_in`, `sky_conditions` |
| `weather_marts.agg_daily_weather` | `mart_trip_demand_weather` | `weather_date`, `avg_temp_f`, `min_temp_f`, `max_temp_f`, `total_precip_in` |

---

## Why This Is a Separate Project

Alternatives considered:

1. **Add to `dbt_trips`**: Breaks domain ownership — weather data is not the trips team's concern.
2. **Add to `dbt_weather`**: Same problem in reverse.
3. **Single monolithic dbt project**: Loses the mesh boundary and independent deployment/failure isolation that the POC is meant to demonstrate.

A separate project with explicit source declarations makes the dependency graph explicit, keeps team ownership clean, and mirrors how a production mesh platform would be structured.
