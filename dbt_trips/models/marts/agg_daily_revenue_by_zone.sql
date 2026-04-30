select
    date_trunc('day', t.pickup_datetime)    as trip_date,
    t.pickup_location_id                    as zone_id,
    z.zone                                  as zone_name,
    z.borough,
    z.service_zone,
    count(*)                                as trip_count,
    sum(t.total_amount)                     as total_revenue,
    avg(t.fare_amount)                      as avg_fare,
    avg(t.tip_amount)                       as avg_tip,
    avg(t.trip_distance)                    as avg_distance_miles,
    avg(t.trip_duration_minutes)            as avg_duration_minutes

from {{ ref('fct_trips') }} t
left join {{ ref('dim_pickup_zones') }} z
    on t.pickup_location_id = z.zone_id

group by 1, 2, 3, 4, 5
