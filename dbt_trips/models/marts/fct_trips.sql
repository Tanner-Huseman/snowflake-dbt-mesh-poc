{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='trip_id',
        on_schema_change='fail'
    )
}}

with stg as (
    select * from {{ ref('stg_trips__yellow_taxi') }}

    {% if is_incremental() %}
    -- Only process rows newer than the latest pickup in the current table.
    -- Using pickup_datetime (not _load_timestamp) keeps the filter stable
    -- across re-runs with the same data.
    where pickup_datetime > (
        select coalesce(max(pickup_datetime), '1900-01-01'::timestamp_ntz)
        from {{ this }}
    )
    {% endif %}
)

select
    trip_id,
    vendor_id,
    pickup_datetime,
    dropoff_datetime,
    datediff('minute', pickup_datetime, dropoff_datetime)  as trip_duration_minutes,
    passenger_count,
    trip_distance,
    rate_code_id,
    store_and_fwd_flag,
    pickup_location_id,
    dropoff_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    airport_fee,
    total_amount,
    _load_timestamp

from stg
