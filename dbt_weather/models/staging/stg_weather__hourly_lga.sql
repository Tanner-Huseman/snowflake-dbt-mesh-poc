with source as (
    select * from {{ source('raw_weather', 'hourly_lga') }}
),

cleaned as (
    select
        station                                                             as station_id,
        station_name,

        -- GHCNh DATE format: '2026-01-01T00:00:00'
        try_to_timestamp(date, 'YYYY-MM-DDTHH24:MI:SS')                    as observation_timestamp,
        date_trunc('hour',
            try_to_timestamp(date, 'YYYY-MM-DDTHH24:MI:SS'))               as observation_hour,

        -- GHCNh temperature is in °C; convert to °F
        (try_to_double(temperature) * 9.0 / 5.0) + 32                      as temperature_f,

        try_to_double(relative_humidity)                                    as relative_humidity_pct,

        -- GHCNh wind values are in m/s; convert to mph
        try_to_double(wind_speed) * 2.23694                                 as wind_speed_mph,
        try_to_double(wind_gust)  * 2.23694                                 as wind_gust_mph,

        -- GHCNh precipitation is in mm; convert to inches.
        -- ⚠️ Verify scale factor against a known precipitation day —
        --    GHCNh may store values in tenths of mm (divide by 254 instead of 25.4).
        -- 'T' sentinel does not appear in GHCNh but guard is kept for safety.
        case
            when precipitation = 'T' then 0.001
            else try_to_double(precipitation) / 25.4
        end                                                                 as precipitation_in,

        -- GHCNh snow_depth is in mm; convert to inches
        try_to_double(snow_depth) / 25.4                                    as snow_depth_in,

        sky_condition                                                       as sky_conditions,
        pres_wx_mw1                                                         as weather_type,

        _load_timestamp

    from source
    where station = '{{ var("lga_station_id") }}'
      and date is not null
)

select * from cleaned
where observation_hour is not null
