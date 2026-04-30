"""
poc_pipeline — End-to-end orchestration DAG for the Snowflake dbt Mesh POC.

Flow:
    sensor_trips_loaded  ──► run_dbt_trips  ──┐
                                               ├──► run_dbt_derived
    sensor_weather_loaded ──► run_dbt_weather ─┘

Sensors poll COPY_HISTORY to detect new Snowpipe loads. Domain dbt runs are
fanned out in parallel. The derived run fans in, executing only after both
domain runs succeed.

Execution model: SQLExecuteQueryOperator submits EXECUTE DBT PROJECT as a
plain SQL statement via the Snowflake connection. For longer dbt runs, swap to
SnowflakeSqlApiOperator in deferrable mode to avoid holding Airflow worker slots.

There is intentionally no Cosmos here. Cosmos runs dbt-core from the Airflow
worker, which defeats the purpose of dbt Projects on Snowflake (Snowflake's
managed runtime). Use plain SQL operators instead.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.snowflake.sensors.snowflake import SnowflakeSensor
from airflow.utils.trigger_rule import TriggerRule

SNOWFLAKE_CONN_ID = "snowflake_default"

# ─── Sensor SQL ───────────────────────────────────────────────────────────────
# Returns True (non-empty result set) when at least one successful Snowpipe load
# exists in the last 6 hours. Adjust START_TIME window as needed.

_TRIPS_SENSOR_SQL = """
SELECT 1
FROM TABLE(raw_db.information_schema.copy_history(
    TABLE_NAME   => 'YELLOW_TAXI',
    START_TIME   => DATEADD('hour', -6, CURRENT_TIMESTAMP())
))
WHERE status = 'Loaded'
LIMIT 1
"""

_WEATHER_SENSOR_SQL = """
SELECT 1
FROM TABLE(raw_db.information_schema.copy_history(
    TABLE_NAME   => 'HOURLY_LGA',
    START_TIME   => DATEADD('hour', -6, CURRENT_TIMESTAMP())
))
WHERE status = 'Loaded'
LIMIT 1
"""

# ─── DAG ──────────────────────────────────────────────────────────────────────

default_args = {
    "owner": "data-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="poc_pipeline",
    description="Snowpipe → dbt_trips + dbt_weather → dbt_derived",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # triggered manually or by future S3 → SNS → Lambda webhook
    catchup=False,
    default_args=default_args,
    tags=["poc", "dbt", "snowflake"],
) as dag:

    # ── Sensors ────────────────────────────────────────────────────────────────

    sensor_trips_loaded = SnowflakeSensor(
        task_id="sensor_trips_loaded",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=_TRIPS_SENSOR_SQL,
        poke_interval=60,     # seconds between polls
        timeout=3600,         # fail if not loaded within 1 hour
        mode="poke",
    )

    sensor_weather_loaded = SnowflakeSensor(
        task_id="sensor_weather_loaded",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=_WEATHER_SENSOR_SQL,
        poke_interval=60,
        timeout=3600,
        mode="poke",
    )

    # ── Domain dbt runs ────────────────────────────────────────────────────────
    # Runs the full project. Adjust --select to be more targeted if needed.

    run_dbt_trips = SQLExecuteQueryOperator(
        task_id="run_dbt_trips",
        conn_id=SNOWFLAKE_CONN_ID,
        sql="""
            EXECUTE DBT PROJECT analytics_db.dbt.trips_project
            ARGS = 'run --select source:raw_trips+'
        """,
    )

    run_dbt_weather = SQLExecuteQueryOperator(
        task_id="run_dbt_weather",
        conn_id=SNOWFLAKE_CONN_ID,
        sql="""
            EXECUTE DBT PROJECT analytics_db.dbt.weather_project
            ARGS = 'run --select source:raw_weather+'
        """,
    )

    # ── Derived dbt run ────────────────────────────────────────────────────────
    # Waits for both domain runs via TriggerRule.ALL_SUCCESS (default).

    run_dbt_derived = SQLExecuteQueryOperator(
        task_id="run_dbt_derived",
        conn_id=SNOWFLAKE_CONN_ID,
        sql="""
            EXECUTE DBT PROJECT analytics_db.dbt.derived_project
            ARGS = 'run'
        """,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    # ── Dependencies ───────────────────────────────────────────────────────────
    # Fan-out: sensors → domain runs in parallel
    # Fan-in:  both domain runs must succeed before derived runs

    sensor_trips_loaded >> run_dbt_trips
    sensor_weather_loaded >> run_dbt_weather
    [run_dbt_trips, run_dbt_weather] >> run_dbt_derived
