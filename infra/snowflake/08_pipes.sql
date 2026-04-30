-- Snowpipe definitions with AUTO_INGEST = TRUE.
-- After creation, run SHOW PIPES to get the notification_channel SQS ARN for each pipe.
-- Configure S3 event notifications to send ObjectCreated events to those SQS queues.
-- See infra/README.md for setup details.

USE ROLE poc_role;

-- ─── Trips pipe ───────────────────────────────────────────────────────────────

CREATE OR REPLACE PIPE raw_db.trips.trips_pipe
    AUTO_INGEST = TRUE
    ERROR_INTEGRATION = null
    COMMENT = 'Auto-ingest TLC Yellow Taxi Parquet from S3 trips/ prefix'
AS
COPY INTO raw_db.trips.yellow_taxi (
    vendorid, tpep_pickup_datetime, tpep_dropoff_datetime,
    passenger_count, trip_distance, ratecodeid, store_and_fwd_flag,
    pulocationid, dolocationid, payment_type, fare_amount, extra,
    mta_tax, tip_amount, tolls_amount, improvement_surcharge,
    total_amount, congestion_surcharge, airport_fee
)
FROM (
    SELECT
        $1:VendorID::NUMBER,
        $1:tpep_pickup_datetime::TIMESTAMP_NTZ,
        $1:tpep_dropoff_datetime::TIMESTAMP_NTZ,
        $1:passenger_count::NUMBER,
        $1:trip_distance::FLOAT,
        $1:RatecodeID::NUMBER,
        $1:store_and_fwd_flag::VARCHAR,
        $1:PULocationID::NUMBER,
        $1:DOLocationID::NUMBER,
        $1:payment_type::NUMBER,
        $1:fare_amount::FLOAT,
        $1:extra::FLOAT,
        $1:mta_tax::FLOAT,
        $1:tip_amount::FLOAT,
        $1:tolls_amount::FLOAT,
        $1:improvement_surcharge::FLOAT,
        $1:total_amount::FLOAT,
        $1:congestion_surcharge::FLOAT,
        $1:Airport_fee::FLOAT
    FROM @raw_db.public.trips_stage
)
FILE_FORMAT = (FORMAT_NAME = 'raw_db.public.parquet_trips')
ON_ERROR = CONTINUE;

-- ─── Weather pipe ─────────────────────────────────────────────────────────────

CREATE OR REPLACE PIPE raw_db.weather.weather_pipe
    AUTO_INGEST = TRUE
    COMMENT = 'Auto-ingest NOAA LCD CSV from S3 weather/ prefix'
AS
COPY INTO raw_db.weather.hourly_lga (
    station, name, date,
    hourlydrybulbtemperature, hourlyrelativehumidity, hourlywindspeed,
    hourlyprecipitation, hourlyskyconditions, hourlypresentweathertype
)
FROM @raw_db.public.weather_stage
FILE_FORMAT = (FORMAT_NAME = 'raw_db.public.csv_weather')
ON_ERROR = CONTINUE;

-- ─── Post-creation validation ─────────────────────────────────────────────────
-- Run after pipes are created and S3 event notifications are configured.
--
-- SHOW PIPES IN DATABASE raw_db;
--
-- Check recent load history (replace TABLE_NAME as needed):
-- SELECT * FROM TABLE(raw_db.information_schema.copy_history(
--     TABLE_NAME => 'YELLOW_TAXI',
--     START_TIME => DATEADD('hour', -1, CURRENT_TIMESTAMP())
-- ));
