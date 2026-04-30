-- Raw ingest tables. Append-only. No transforms happen here.
-- Snowpipe COPYs directly into these tables.

USE ROLE poc_role;

-- ─── TLC Yellow Taxi ──────────────────────────────────────────────────────────
-- Schema matches the 2024 TLC Yellow Taxi Parquet schema.
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
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ─── NOAA LCD Hourly (LaGuardia) ─────────────────────────────────────────────
-- Schema covers the key LCD columns. The full NOAA LCD export has 100+ columns;
-- this table captures the fields needed for the weather domain models.
CREATE SCHEMA IF NOT EXISTS raw_db.weather;

CREATE TABLE IF NOT EXISTS raw_db.weather.hourly_lga (
    station                     VARCHAR,
    name                        VARCHAR,
    date                        VARCHAR,      -- raw string; parsed to TIMESTAMP in staging
    hourlydrybulbtemperature    VARCHAR,      -- degrees F; may be empty/M
    hourlyrelativehumidity      VARCHAR,      -- %; may be empty/M
    hourlywindspeed             VARCHAR,      -- mph; may be empty/M
    hourlyprecipitation         VARCHAR,      -- inches; "T" for trace; may be empty/M
    hourlyskyconditions         VARCHAR,
    hourlypresentweathertype    VARCHAR,
    _load_timestamp             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);