-- Hourly trip volume vs. temperature — powers the "weather effect" chart in Streamlit.

with hourly_trips as (
    select
        date_trunc('hour', pickup_datetime)     as trip_hour,
        count(*)                                as trip_count,
        avg(fare_amount)                        as avg_fare,
        avg(trip_distance)                      as avg_distance_miles
    from {{ source('trips_marts', 'fct_trips') }}
    group by 1
)

select
    t.trip_hour,
    t.trip_count,
    t.avg_fare,
    t.avg_distance_miles,

    w.temperature_f,
    w.precipitation_in,
    w.relative_humidity_pct,
    w.wind_speed_mph,
    w.sky_conditions

from hourly_trips t
inner join {{ source('weather_marts', 'fct_weather_hourly') }} w
    on t.trip_hour = w.observation_hour
