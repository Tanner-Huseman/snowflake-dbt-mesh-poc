-- Static station reference. Even with a single station this establishes
-- the pattern for adding more stations in a future iteration.

select distinct
    station_id,
    station_name,
    'LaGuardia Airport'     as common_name,
    'LGA'                   as iata_code,
    40.7769                 as latitude,
    -73.8740                as longitude,
    'Queens, New York'      as city

from {{ ref('stg_weather__hourly_lga') }}
