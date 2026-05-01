-- Cross-domain showpiece mart: trip demand + weather context per (date, zone).
-- Joins the trips domain's daily revenue aggregation with the weather domain's
-- daily aggregation. This is what a mesh consumer looks like: no raw sources,
-- only domain-published data products.

select
    t.trip_date,
    t.zone_id,
    t.zone_name,
    t.borough,
    t.service_zone,
    t.trip_count,
    t.total_revenue,
    t.avg_fare,
    t.avg_tip,
    t.avg_distance_miles,
    t.avg_duration_minutes,

    w.avg_temp_f,
    w.min_temp_f,
    w.max_temp_f,
    w.total_precip_in,
    w.avg_humidity_pct,
    w.avg_wind_mph,
    w.dominant_sky_condition,

    case
        when w.total_precip_in > 0.1                    then 'rainy'
        when w.max_temp_f < 32                          then 'freezing'
        when w.max_temp_f < 50                          then 'cold'
        when w.max_temp_f >= 85                         then 'hot'
        else                                                 'mild'
    end                                                 as weather_category

from {{ source('trips_marts', 'agg_daily_revenue_by_zone') }} t
inner join {{ source('weather_marts', 'agg_daily_weather') }} w
    on t.trip_date = w.weather_date