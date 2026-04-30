-- File formats for TLC Parquet and NOAA CSV.
-- Stored in raw_db.public so stages in both raw_db schemas can reference them.

USE ROLE poc_role;
USE DATABASE raw_db;
USE SCHEMA public;

CREATE OR REPLACE FILE FORMAT parquet_trips
    TYPE = 'PARQUET'
    SNAPPY_COMPRESSION = TRUE
    COMMENT = 'TLC Yellow Taxi Parquet files';

-- NOAA GHCNh PSV quirks:
--   - Pipe-delimited (~200 columns; COPY INTO maps only the subset we need by position)
--   - Header row present
--   - Empty fields and literal "M" (missing) should be NULL
--   - "T" (trace precipitation) does not appear in GHCNh; handled defensively in staging
CREATE OR REPLACE FILE FORMAT csv_weather
    TYPE = 'CSV'
    FIELD_DELIMITER = '|'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null', 'M')
    EMPTY_FIELD_AS_NULL = TRUE
    COMMENT = 'NOAA GHCNh hourly PSV files (pipe-delimited)';
