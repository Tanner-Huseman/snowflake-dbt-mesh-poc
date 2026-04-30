# infra/

All non-dbt, non-Streamlit infrastructure: Snowflake DDL, S3 wiring, Airflow, and the sample data loader.

## Setup Order

Run the Snowflake SQL files in this exact order. Each file is idempotent (`CREATE OR REPLACE`) so re-runs are safe.

```
1.  snowflake/warehouses.sql          # wh_poc_xs, auto-suspend
2.  snowflake/resource_monitor.sql    # $200 hard suspend — run this first
3.  snowflake/rbac.sql                # poc_role, all grants
4.  snowflake/storage_integration.sql # S3 integration object
    → DESC INTEGRATION poc_s3_integration
    → copy STORAGE_AWS_IAM_USER_ARN + STORAGE_AWS_EXTERNAL_ID into AWS role trust policy
5.  snowflake/file_formats.sql        # Parquet (TLC) + CSV (NOAA)
6.  snowflake/stages.sql              # trips_stage + weather_stage
7.  snowflake/raw_tables.sql          # raw_db.trips.yellow_taxi + raw_db.weather.hourly_lga
8.  snowflake/pipes.sql               # Snowpipe AUTO_INGEST
    → SHOW PIPES → copy notification_channel ARN into S3 event notifications
9.  snowflake/git_repository.sql      # API integration + Git repository object
    → create GitHub PAT → store as Snowflake secret → FETCH
10. snowflake/dbt_projects.sql        # CREATE DBT PROJECT for all three
```

### Manual prerequisites before step 1

- Create `raw_db` and `analytics_db` databases:
  ```sql
  USE ROLE accountadmin;
  CREATE DATABASE IF NOT EXISTS raw_db;
  CREATE DATABASE IF NOT EXISTS analytics_db;
  ```

- Create the required schemas:
  ```sql
  CREATE SCHEMA IF NOT EXISTS raw_db.trips;
  CREATE SCHEMA IF NOT EXISTS raw_db.weather;
  CREATE SCHEMA IF NOT EXISTS analytics_db.integrations;
  CREATE SCHEMA IF NOT EXISTS analytics_db.dbt;
  ```

### Snowpipe IAM trust policy (step 4 follow-up)

After running `storage_integration.sql`, run:

```sql
DESC INTEGRATION poc_s3_integration;
```

Find the `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` values. Update the trust policy of your S3-access IAM role:

```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "<STORAGE_AWS_IAM_USER_ARN>"
  },
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {
      "sts:ExternalId": "<STORAGE_AWS_EXTERNAL_ID>"
    }
  }
}
```

### S3 event notification setup (step 8 follow-up)

After running `pipes.sql`, run:

```sql
SHOW PIPES IN DATABASE raw_db;
```

For each pipe, copy the `notification_channel` value (an SQS queue ARN). In the AWS S3 console, configure event notifications on your bucket:

- Prefix `trips/` → event type `s3:ObjectCreated:*` → SQS queue from `trips_pipe`
- Prefix `weather/` → event type `s3:ObjectCreated:*` → SQS queue from `weather_pipe`

### Git credentials setup (step 9 follow-up)

Create a GitHub Personal Access Token (PAT) with `repo` read scope. Store it in Snowflake:

```sql
USE ROLE accountadmin;
CREATE SECRET analytics_db.integrations.poc_git_credentials
  TYPE = PASSWORD
  USERNAME = '<your-github-username>'
  PASSWORD = '<your-github-pat>';
```

Then fetch the repo:

```sql
ALTER GIT REPOSITORY analytics_db.integrations.poc_git_stage FETCH;
```

## Validate End-to-End Ingest

Drop a small test file into S3:

```bash
aws s3 cp sample.parquet s3://<your-bucket>/trips/sample.parquet
```

Wait ~30–60 seconds, then check:

```sql
SELECT COUNT(*), MAX(_load_timestamp)
FROM raw_db.trips.yellow_taxi;
```

## Airflow

See `airflow/` for the Docker Compose setup and the `poc_pipeline` DAG.

Start locally:

```bash
cd airflow
docker compose up -d
# UI: http://localhost:8080  (admin / admin)
```

See `airflow/connections.md` for Snowflake connection setup.

## Sample Data Loader

See `sample_data_loader/load_chunks.py`. Run it manually to chunk source files and drop them into S3.

```bash
cd sample_data_loader
pip install -r requirements.txt
python load_chunks.py --help
```
