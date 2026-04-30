# Airflow Snowflake Connection Setup

The `poc_pipeline` DAG uses connection ID `snowflake_default`. Configure it in
the Airflow UI after running `docker compose up -d`.

## Via the Airflow UI

1. Open **http://localhost:8080** and log in (admin / admin).
2. Go to **Admin → Connections → Add a new record**.
3. Fill in:

| Field | Value |
|-------|-------|
| Connection Id | `snowflake_default` |
| Connection Type | `Snowflake` |
| Account | `<your-account-identifier>` (e.g., `abc123.us-east-1`) |
| Login | `<your-snowflake-username>` |
| Password | `<your-snowflake-password>` |
| Schema | `trips` _(default schema; overridden per query)_ |
| Extra | See JSON below |

Extra JSON:

```json
{
  "database": "analytics_db",
  "warehouse": "wh_poc_xs",
  "role": "poc_role"
}
```

4. Click **Save** and test the connection.

## Via environment variable

Add to `docker-compose.yml` under the `airflow-common` environment block:

```yaml
AIRFLOW_CONN_SNOWFLAKE_DEFAULT: >-
  snowflake://<username>:<password>@<account>/analytics_db/trips?
  warehouse=wh_poc_xs&role=poc_role
```

URL-encode any special characters in the password.

## Finding your account identifier

In a Snowflake worksheet:

```sql
SELECT CURRENT_ACCOUNT();
-- Returns e.g. ABC12345

SELECT SYSTEM$ALLOWLIST();
-- Includes the full account identifier with region
```

For Snowflake accounts in AWS US East 1, the identifier is typically
`<org>-<account>` or `<account>.us-east-1`. Check the URL of your Snowflake
UI — it will be in the format `https://<account-identifier>.snowflakecomputing.com`.
