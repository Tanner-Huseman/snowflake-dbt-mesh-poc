-- Raw ingest tables. Append-only. No transforms happen here.
-- Snowpipe COPYs directly into these tables.

USE ROLE poc_role;

-- ─── TLC Yellow Taxi ──────────────────────────────────────────────────────────
-- Schema matches the 2026 TLC Yellow Taxi Parquet schema.
-- cbd_congestion_fee added in 2026 (NYC CBD congestion pricing surcharge).
CREATE SCHEMA IF NOT EXISTS raw_db.trips;

CREATE TABLE IF NOT EXISTS raw_db.trips.yellow_taxi (
    vendorid              NUMBER,
    tpep_pickup_datetime  TIMESTAMP_NTZ,
    tpep_dropoff_datetime TIMESTAMP_NTZ,
    passenger_count       NUMBER,
    trip_distance         FLOAT,
    ratecodeid            NUMBER,
    store_and_fwd_flag    VARCHAR(1),
    pulocationid          NUMBER,
    dolocationid          NUMBER,
    payment_type          NUMBER,
    fare_amount           FLOAT,
    extra                 FLOAT,
    mta_tax               FLOAT,
    tip_amount            FLOAT,
    tolls_amount          FLOAT,
    improvement_surcharge FLOAT,
    total_amount          FLOAT,
    congestion_surcharge  FLOAT,
    airport_fee           FLOAT,
    cbd_congestion_fee    FLOAT,
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ─── NOAA GHCNh Hourly (LaGuardia) ──────────────────────────────────────────
-- Source: GHCNh_USW00014732_2026.psv (~200 pipe-delimited columns).
-- Only the columns used by the weather domain models are captured here;
-- the pipe maps them by positional reference ($N) from the PSV.
-- All values stored as VARCHAR; unit conversions happen in the staging model.
CREATE SCHEMA IF NOT EXISTS raw_db.weather;

CREATE TABLE IF NOT EXISTS raw_db.weather.hourly_lga (
    station           VARCHAR,
    station_name      VARCHAR,
    date              VARCHAR,        -- ISO timestamp string; parsed to TIMESTAMP in staging
    temperature       VARCHAR,        -- °C ($12); converted to °F in staging
    wind_speed        VARCHAR,        -- m/s ($42); converted to mph in staging
    wind_gust         VARCHAR,        -- m/s ($48); converted to mph in staging
    precipitation     VARCHAR,        -- mm ($54); converted to inches in staging
    relative_humidity VARCHAR,        -- % ($60)
    snow_depth        VARCHAR,        -- mm ($126); converted to inches in staging
    sky_condition     VARCHAR,        -- ($150)
    pres_wx_mw1       VARCHAR,        -- present weather code ($72)
    _load_timestamp   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);