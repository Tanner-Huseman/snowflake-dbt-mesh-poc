-- File formats for TLC Parquet and NOAA CSV.
-- Stored in raw_db.public so stages in both raw_db schemas can reference them.

USE ROLE poc_role;
USE DATABASE raw_db;
USE SCHEMA public;

CREATE OR REPLACE FILE FORMAT parquet_trips
    TYPE = 'PARQUET'
    SNAPPY_COMPRESSION = TRUE
    COMMENT = 'TLC Yellow Taxi Parquet files';

-- NOAA LCD CSV quirks:
--   - Header row present
--   - Empty fields and literal "M" (missing) should be NULL
--   - "T" (trace precipitation) is handled in the staging model, not here
CREATE OR REPLACE FILE FORMAT csv_weather
    TYPE = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null', 'M')
    EMPTY_FIELD_AS_NULL = TRUE
    COMMENT = 'NOAA LCD hourly CSV files';
