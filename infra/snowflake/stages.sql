-- External stages pointing at S3 prefixes for each domain.
-- Replace <your-bucket> with your actual S3 bucket name.

USE ROLE poc_role;
USE DATABASE raw_db;
USE SCHEMA public;

CREATE OR REPLACE STAGE trips_stage
    URL = 's3://<your-bucket>/trips/'
    STORAGE_INTEGRATION = poc_s3_integration
    FILE_FORMAT = parquet_trips
    COMMENT = 'External stage for TLC Yellow Taxi Parquet drops';

CREATE OR REPLACE STAGE weather_stage
    URL = 's3://<your-bucket>/weather/'
    STORAGE_INTEGRATION = poc_s3_integration
    FILE_FORMAT = csv_weather
    COMMENT = 'External stage for NOAA LCD CSV drops';

-- Validate after S3 files are present:
-- LIST @trips_stage;
-- LIST @weather_stage;
