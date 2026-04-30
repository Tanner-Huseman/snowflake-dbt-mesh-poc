-- DBT PROJECT objects for all three domain projects.
-- Each project is deployed independently from the monorepo Git stage,
-- pointing at its own subdirectory.
-- Run git_repository.sql and FETCH before running this file.

USE ROLE accountadmin;

-- Grant EXECUTE DBT PROJECT to poc_role
GRANT EXECUTE DBT PROJECT ON ACCOUNT TO ROLE poc_role;

USE ROLE poc_role;
USE DATABASE analytics_db;

-- ─── Trips domain project ─────────────────────────────────────────────────────

CREATE OR REPLACE DBT PROJECT analytics_db.dbt.trips_project
    FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_trips'
    DBT_VERSION = '1.10.15'
    DEFAULT_TARGET = 'prod'
    WAREHOUSE = wh_poc_xs
    COMMENT = 'Trips domain: raw_db.trips → analytics_db.trips_*';

-- ─── Weather domain project ───────────────────────────────────────────────────

CREATE OR REPLACE DBT PROJECT analytics_db.dbt.weather_project
    FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_weather'
    DBT_VERSION = '1.10.15'
    DEFAULT_TARGET = 'prod'
    WAREHOUSE = wh_poc_xs
    COMMENT = 'Weather domain: raw_db.weather → analytics_db.weather_*';

-- ─── Cross-domain derived project ────────────────────────────────────────────

CREATE OR REPLACE DBT PROJECT analytics_db.dbt.derived_project
    FROM '@analytics_db.integrations.poc_git_stage/branches/main/dbt_derived'
    DBT_VERSION = '1.10.15'
    DEFAULT_TARGET = 'prod'
    WAREHOUSE = wh_poc_xs
    COMMENT = 'Cross-domain: composes trips + weather marts into derived analytics';

-- ─── Validation commands ──────────────────────────────────────────────────────
-- Run these in a worksheet after creation to verify each project is wired up:
--
-- EXECUTE DBT PROJECT analytics_db.dbt.trips_project ARGS = 'debug';
-- EXECUTE DBT PROJECT analytics_db.dbt.weather_project ARGS = 'debug';
-- EXECUTE DBT PROJECT analytics_db.dbt.derived_project ARGS = 'debug';
