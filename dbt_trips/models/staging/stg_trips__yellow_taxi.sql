with source as (
    select * from {{ source('raw_trips', 'yellow_taxi') }}
),

renamed as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'vendorid',
            'tpep_pickup_datetime',
            'tpep_dropoff_datetime'
        ]) }}                               as trip_id,

        vendorid                            as vendor_id,
        TO_TIMESTAMP_NTZ(tpep_pickup_datetime::NUMBER, 6)  as pickup_datetime,
        TO_TIMESTAMP_NTZ(tpep_dropoff_datetime::NUMBER, 6) as dropoff_datetime,
        passenger_count,
        trip_distance,
        ratecodeid                          as rate_code_id,
        store_and_fwd_flag,
        pulocationid                        as pickup_location_id,
        dolocationid                        as dropoff_location_id,
        payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        airport_fee,
        cbd_congestion_fee,
        _load_timestamp

    from source
    where tpep_pickup_datetime is not null
      and tpep_dropoff_datetime is not null
      and tpep_dropoff_datetime::NUMBER > tpep_pickup_datetime::NUMBER
)

select * from renamed
