-- Single poc_role for the entire POC.
-- Production note: split into poc_ingest_role, poc_transform_role, poc_consume_role
-- for proper least-privilege isolation.

USE ROLE accountadmin;

CREATE ROLE IF NOT EXISTS poc_role;

-- Warehouse
GRANT USAGE, OPERATE ON WAREHOUSE wh_poc_xs TO ROLE poc_role;

-- Databases
GRANT USAGE ON DATABASE raw_db TO ROLE poc_role;
GRANT USAGE ON DATABASE analytics_db TO ROLE poc_role;

-- raw_db schemas + objects
GRANT USAGE ON ALL SCHEMAS IN DATABASE raw_db TO ROLE poc_role;
GRANT CREATE SCHEMA ON DATABASE raw_db TO ROLE poc_role;
GRANT SELECT, INSERT ON ALL TABLES IN DATABASE raw_db TO ROLE poc_role;
GRANT SELECT, INSERT ON FUTURE TABLES IN DATABASE raw_db TO ROLE poc_role;
GRANT USAGE ON ALL STAGES IN DATABASE raw_db TO ROLE poc_role;
GRANT READ ON ALL STAGES IN DATABASE raw_db TO ROLE poc_role;
GRANT USAGE ON FUTURE STAGES IN DATABASE raw_db TO ROLE poc_role;
GRANT READ ON FUTURE STAGES IN DATABASE raw_db TO ROLE poc_role;
GRANT MONITOR, OPERATE ON ALL PIPES IN DATABASE raw_db TO ROLE poc_role;
GRANT MONITOR, OPERATE ON FUTURE PIPES IN DATABASE raw_db TO ROLE poc_role;
GRANT USAGE ON ALL FILE FORMATS IN DATABASE raw_db TO ROLE poc_role;
GRANT USAGE ON FUTURE FILE FORMATS IN DATABASE raw_db TO ROLE poc_role;

-- analytics_db schemas + objects
GRANT USAGE ON ALL SCHEMAS IN DATABASE analytics_db TO ROLE poc_role;
GRANT CREATE SCHEMA ON DATABASE analytics_db TO ROLE poc_role;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN DATABASE analytics_db TO ROLE poc_role;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON FUTURE TABLES IN DATABASE analytics_db TO ROLE poc_role;
GRANT CREATE TABLE ON ALL SCHEMAS IN DATABASE analytics_db TO ROLE poc_role;
GRANT CREATE VIEW ON ALL SCHEMAS IN DATABASE analytics_db TO ROLE poc_role;
GRANT USAGE ON ALL INTEGRATIONS TO ROLE poc_role;

-- Storage integration (needed for stage creation)
GRANT USAGE ON INTEGRATION poc_s3_integration TO ROLE poc_role;

-- Git repository and dbt project objects
GRANT USAGE ON ALL GIT REPOSITORIES IN SCHEMA analytics_db.integrations TO ROLE poc_role;
GRANT USAGE ON FUTURE GIT REPOSITORIES IN SCHEMA analytics_db.integrations TO ROLE poc_role;

-- Assign poc_role to the user running the POC
-- Replace <your-snowflake-username> with your actual username.
GRANT ROLE poc_role TO USER <your-snowflake-username>;

-- Grant poc_role to sysadmin for warehouse management
GRANT ROLE poc_role TO ROLE sysadmin;
