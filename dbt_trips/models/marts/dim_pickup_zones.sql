select
    locationid  as zone_id,
    borough,
    zone,
    service_zone

from {{ ref('taxi_zones') }}
