-- Full refresh, not incremental. One month of hourly weather is ~720 rows —
-- small enough that incremental adds complexity without meaningful benefit.
-- See dbt_weather/README.md for the rationale.

select
    station_id,
    station_name,
    observation_hour,
    temperature_f,
    relative_humidity_pct,
    wind_speed_mph,
    precipitation_in,
    sky_conditions,
    weather_type

from {{ ref('stg_weather__hourly_lga') }}
