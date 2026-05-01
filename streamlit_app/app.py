"""
Streamlit in Snowflake — dbt Mesh POC Dashboard

Three tabs:
  1. Trips     — charts from analytics_db.dbt
  2. Weather   — charts from analytics_db.dbt
  3. Combined  — cross-domain charts from analytics_db.dbt

Deploy: Snowflake UI → Streamlit → New Streamlit App → paste this file.
The app runs inside Snowflake, so snowflake.snowpark is available natively.
No external DB connection needed.
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

st.set_page_config(
    page_title="NYC Trips + Weather — dbt Mesh POC",
    page_icon="🚕",
    layout="wide",
)

# ─── Session ──────────────────────────────────────────────────────────────────

session = get_active_session()


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# ─── Sidebar: data freshness panel (stretch goal) ────────────────────────────

with st.sidebar:
    st.header("Data Freshness")
    try:
        freshness_sql = """
            SELECT
                'trips'   AS source,
                MAX(file_last_modified) AS last_load
            FROM TABLE(raw_db.information_schema.copy_history(
                TABLE_NAME   => 'YELLOW_TAXI',
                START_TIME   => DATEADD('day', -7, CURRENT_TIMESTAMP())
            ))
            WHERE status = 'Loaded'
            UNION ALL
            SELECT
                'weather' AS source,
                MAX(file_last_modified) AS last_load
            FROM TABLE(raw_db.information_schema.copy_history(
                TABLE_NAME   => 'HOURLY_LGA',
                START_TIME   => DATEADD('day', -7, CURRENT_TIMESTAMP())
            ))
            WHERE status = 'Loaded'
        """
        freshness_df = query(freshness_sql)
        for _, row in freshness_df.iterrows():
            last = row["LAST_LOAD"]
            label = "🟢" if pd.notna(last) else "🔴"
            st.write(f"{label} **{row['SOURCE']}**: {last if pd.notna(last) else 'no recent load'}")
    except Exception:
        st.caption("Freshness unavailable")

    st.divider()
    st.caption("dbt Mesh POC · Snowflake + dbt + Airflow")


# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_trips, tab_weather, tab_combined = st.tabs(["🚕 Trips", "🌡️ Weather", "🔗 Combined Insights"])


# ── Tab 1: Trips ──────────────────────────────────────────────────────────────

with tab_trips:
    st.header("NYC Yellow Taxi — January 2024")

    trips_daily_sql = """
        SELECT
            trip_date,
            SUM(trip_count)    AS trip_count,
            SUM(total_revenue) AS total_revenue,
            AVG(avg_fare)      AS avg_fare
        FROM analytics_db.dbt.agg_daily_revenue_by_zone
        GROUP BY 1
        ORDER BY 1
    """
    daily_df = query(trips_daily_sql)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trips", f"{daily_df['TRIP_COUNT'].sum():,.0f}")
    col2.metric("Total Revenue", f"${daily_df['TOTAL_REVENUE'].sum():,.0f}")
    col3.metric("Avg Fare", f"${daily_df['AVG_FARE'].mean():.2f}")

    st.subheader("Daily Trip Volume")
    st.line_chart(daily_df.set_index("TRIP_DATE")["TRIP_COUNT"])

    st.subheader("Daily Revenue")
    st.bar_chart(daily_df.set_index("TRIP_DATE")["TOTAL_REVENUE"])

    st.subheader("Top 10 Zones by Trip Count")
    top_zones_sql = """
        SELECT
            zone_name,
            borough,
            SUM(trip_count)    AS trip_count,
            SUM(total_revenue) AS total_revenue
        FROM analytics_db.dbt.agg_daily_revenue_by_zone
        GROUP BY 1, 2
        ORDER BY 3 DESC
        LIMIT 10
    """
    top_zones_df = query(top_zones_sql)
    st.bar_chart(top_zones_df.set_index("ZONE_NAME")["TRIP_COUNT"])

    with st.expander("Raw data"):
        st.dataframe(top_zones_df)


# ── Tab 2: Weather ────────────────────────────────────────────────────────────

with tab_weather:
    st.header("NOAA Weather — LaGuardia Airport — January 2024")

    weather_daily_sql = """
        SELECT
            weather_date,
            avg_temp_f,
            min_temp_f,
            max_temp_f,
            total_precip_in,
            avg_humidity_pct,
            avg_wind_mph
        FROM analytics_db.dbt.agg_daily_weather
        ORDER BY 1
    """
    weather_df = query(weather_daily_sql)

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Temp (°F)", f"{weather_df['AVG_TEMP_F'].mean():.1f}°")
    col2.metric("Total Precip (in)", f"{weather_df['TOTAL_PRECIP_IN'].sum():.2f}\"")
    col3.metric("Avg Wind (mph)", f"{weather_df['AVG_WIND_MPH'].mean():.1f}")

    st.subheader("Daily Temperature Range")
    temp_chart_df = weather_df[["WEATHER_DATE", "MIN_TEMP_F", "AVG_TEMP_F", "MAX_TEMP_F"]].set_index("WEATHER_DATE")
    st.line_chart(temp_chart_df)

    st.subheader("Daily Precipitation")
    st.bar_chart(weather_df.set_index("WEATHER_DATE")["TOTAL_PRECIP_IN"])

    with st.expander("Raw data"):
        st.dataframe(weather_df)


# ── Tab 3: Combined Insights ──────────────────────────────────────────────────

with tab_combined:
    st.header("Combined: Trip Demand vs. Weather Conditions")
    st.caption(
        "Cross-domain data from `analytics_db.dbt` — the output of the dbt_derived mesh project."
    )

    combined_sql = """
        SELECT
            trip_date,
            SUM(trip_count)    AS total_trips,
            SUM(total_revenue) AS total_revenue,
            AVG(avg_temp_f)    AS avg_temp_f,
            SUM(total_precip_in) AS total_precip_in,
            MAX(weather_category) AS weather_category
        FROM analytics_db.dbt.mart_trip_demand_weather
        GROUP BY 1
        ORDER BY 1
    """
    combined_df = query(combined_sql)

    st.subheader("Trip Count vs. Temperature (daily)")
    scatter_data = combined_df[["AVG_TEMP_F", "TOTAL_TRIPS"]].rename(
        columns={"AVG_TEMP_F": "Temperature (°F)", "TOTAL_TRIPS": "Trip Count"}
    )
    st.scatter_chart(scatter_data, x="Temperature (°F)", y="Trip Count")

    st.subheader("Daily Trips by Weather Category")
    weather_cat_df = (
        combined_df.groupby("WEATHER_CATEGORY")["TOTAL_TRIPS"]
        .sum()
        .reset_index()
        .sort_values("TOTAL_TRIPS", ascending=False)
    )
    st.bar_chart(weather_cat_df.set_index("WEATHER_CATEGORY")["TOTAL_TRIPS"])

    st.subheader("Daily Revenue vs. Temperature")
    rev_temp_df = combined_df[["TRIP_DATE", "TOTAL_REVENUE", "AVG_TEMP_F"]].set_index("TRIP_DATE")
    st.line_chart(rev_temp_df)

    hourly_sql = """
        SELECT
            trip_hour,
            trip_count,
            temperature_f
        FROM analytics_db.dbt.mart_hourly_demand_vs_temperature
        ORDER BY 1
    """
    try:
        hourly_df = query(hourly_sql)
        st.subheader("Hourly Trip Count vs. Temperature")
        st.scatter_chart(
            hourly_df.rename(columns={"TEMPERATURE_F": "Temperature (°F)", "TRIP_COUNT": "Trip Count"}),
            x="Temperature (°F)",
            y="Trip Count",
        )
    except Exception:
        st.info("Hourly mart not yet available — run dbt_derived first.")

    with st.expander("Raw combined data"):
        st.dataframe(combined_df)
