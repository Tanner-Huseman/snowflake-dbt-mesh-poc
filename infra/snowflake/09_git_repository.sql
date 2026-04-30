-- Git repository object for dbt Projects on Snowflake.
-- Snowflake fetches dbt project code directly from this repo via the API integration.
-- Replace <your-org> and <your-repo> with your actual GitHub org and repo name.

USE ROLE accountadmin;
USE DATABASE analytics_db;
CREATE SCHEMA integrations;
USE SCHEMA integrations;

-- API integration authenticates Snowflake to GitHub over HTTPS.
CREATE OR REPLACE API INTEGRATION poc_github_integration
    API_PROVIDER = git_https_api
    API_ALLOWED_PREFIXES = ('https://github.com/<your-org>/')
    ENABLED = TRUE
    COMMENT = 'HTTPS API integration for GitHub — used by poc_git_stage';

-- Store GitHub credentials (PAT) as a Snowflake secret.
-- Create the PAT in GitHub with repo read scope, then run this manually
-- (do not commit the PAT value to this file).
--
-- CREATE SECRET analytics_db.integrations.poc_git_credentials
--     TYPE = PASSWORD
--     USERNAME = '<your-github-username>'
--     PASSWORD = '<your-github-pat>';

-- Git repository object — points at the monorepo root.
-- dbt projects are deployed by referencing subdirectory paths within this stage.
CREATE OR REPLACE GIT REPOSITORY analytics_db.integrations.poc_git_stage
    API_INTEGRATION = poc_github_integration
    GIT_CREDENTIALS = analytics_db.integrations.poc_git_credentials
    ORIGIN = 'https://github.com/<your-org>/snowflake-dbt-mesh-poc.git'
    COMMENT = 'Monorepo containing dbt_trips, dbt_weather, and dbt_derived projects';

-- Pull the latest commits. Re-run this whenever new commits should be deployed.
ALTER GIT REPOSITORY analytics_db.integrations.poc_git_stage FETCH;

-- Validate: list the root of the main branch
-- LIST @analytics_db.integrations.poc_git_stage/branches/main/;
