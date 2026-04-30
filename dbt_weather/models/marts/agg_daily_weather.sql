select
    date_trunc('day', observation_hour)         as weather_date,
    station_id,

    avg(temperature_f)                          as avg_temp_f,
    min(temperature_f)                          as min_temp_f,
    max(temperature_f)                          as max_temp_f,

    sum(coalesce(precipitation_in, 0))          as total_precip_in,

    avg(relative_humidity_pct)                  as avg_humidity_pct,
    avg(wind_speed_mph)                         as avg_wind_mph,

    -- Dominant condition: most common non-null sky condition for the day
    mode(sky_conditions)                        as dominant_sky_condition

from {{ ref('fct_weather_hourly') }}
group by 1, 2
