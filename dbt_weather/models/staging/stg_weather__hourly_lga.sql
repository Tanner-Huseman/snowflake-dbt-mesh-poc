with source as (
    select * from {{ source('raw_weather', 'hourly_lga') }}
),

cleaned as (
    select
        station                                                             as station_id,
        name                                                                as station_name,

        -- NOAA DATE format: '2024-01-15T14:53:00'
        try_to_timestamp(date, 'YYYY-MM-DDTHH24:MI:SS')                    as observation_timestamp,
        date_trunc('hour',
            try_to_timestamp(date, 'YYYY-MM-DDTHH24:MI:SS'))               as observation_hour,

        try_to_number(hourlydrybulbtemperature)                             as temperature_f,
        try_to_number(hourlyrelativehumidity)                               as relative_humidity_pct,
        try_to_number(hourlywindspeed)                                      as wind_speed_mph,

        -- 'T' = trace precipitation (treat as 0.001 inches); 'M' / NULL already handled
        -- by the file format NULL_IF, but 'T' requires explicit handling here.
        case
            when hourlyprecipitation = 'T' then 0.001
            else try_to_number(replace(hourlyprecipitation, 's', ''))
        end                                                                 as precipitation_in,

        hourlyskyconditions                                                 as sky_conditions,
        hourlypresentweathertype                                            as weather_type,

        _load_timestamp

    from source
    where station = '{{ var("lga_station_id") }}'
      and date is not null
)

select * from cleaned
where observation_hour is not null
