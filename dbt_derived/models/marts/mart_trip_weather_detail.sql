{{
    config(
        materialized='table',
        on_schema_change='fail'
    )
}}

-- Trip-level join with hourly weather at pickup time.
-- Enables: payment type × weather, tip distributions, per-trip weather analysis.
-- ~3M rows for Q1 2026. Full refresh — no incremental complexity needed at this scale.

with trips as (
    select * from {{ source('trips_marts', 'fct_trips') }}
),

weather as (
    select * from {{ source('weather_marts', 'fct_weather_hourly') }}
)

select
    t.trip_id,
    t.pickup_datetime,
    date_trunc('day', t.pickup_datetime)::date  as trip_date,
    hour(t.pickup_datetime)                     as pickup_hour,
    dayofweekiso(t.pickup_datetime)             as day_of_week,  -- 1=Mon, 7=Sun
    t.pickup_location_id,
    t.payment_type,
    t.fare_amount,
    t.tip_amount,
    case
        when t.fare_amount > 0 then t.tip_amount / t.fare_amount
    end                                         as tip_rate,
    t.trip_distance,
    t.trip_duration_minutes,
    t.total_amount,
    w.temperature_f,
    w.precipitation_in,
    w.wind_speed_mph,
    w.relative_humidity_pct,
    case
        when w.precipitation_in > 0  then 'rainy'
        when w.temperature_f    < 32 then 'freezing'
        when w.temperature_f    < 45 then 'cold'
        when w.temperature_f    > 75 then 'hot'
        else 'mild'
    end                                         as weather_category

from trips t
left join weather w
    on date_trunc('hour', t.pickup_datetime) = w.observation_hour
