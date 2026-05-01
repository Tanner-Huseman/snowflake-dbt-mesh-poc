"""
Streamlit in Snowflake — dbt Mesh POC (simplified)
Combined trip demand vs. weather statistics only.
Deploy the same way as app.py: paste into the SiS editor and click Run.
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="Trip Demand vs. Weather", layout="wide")

session = get_active_session()


def query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


st.title("NYC Trip Demand vs. Weather — dbt Mesh POC")

df = query("""
    SELECT
        trip_date,
        SUM(trip_count)      AS total_trips,
        SUM(total_revenue)   AS total_revenue,
        AVG(avg_temp_f)      AS avg_temp_f,
        SUM(total_precip_in) AS total_precip_in,
        MAX(weather_category) AS weather_category
    FROM analytics_db.dbt.mart_trip_demand_weather
    GROUP BY 1
    ORDER BY 1
""")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trips",    f"{df['TOTAL_TRIPS'].sum():,.0f}")
col2.metric("Total Revenue",  f"${df['TOTAL_REVENUE'].sum():,.0f}")
col3.metric("Avg Temp (°F)",  f"{df['AVG_TEMP_F'].mean():.1f}°")
col4.metric("Total Precip",   f"{df['TOTAL_PRECIP_IN'].sum():.2f}\"")

st.subheader("Trips vs. Temperature (daily scatter)")
st.scatter_chart(
    df[["AVG_TEMP_F", "TOTAL_TRIPS"]].rename(
        columns={"AVG_TEMP_F": "Temperature (°F)", "TOTAL_TRIPS": "Trip Count"}
    ),
    x="Temperature (°F)",
    y="Trip Count",
)

st.subheader("Trips by Temperature Range (5° buckets)")
bucket_low = (df["AVG_TEMP_F"] // 5 * 5).astype(int)
bucket_df = df.copy()
bucket_df["temp_range"] = bucket_low.astype(str) + "–" + (bucket_low + 5).astype(str) + "°F"
bucket_df["_sort_key"] = bucket_low
bucket_summary = (
    bucket_df.groupby(["temp_range", "_sort_key"])["TOTAL_TRIPS"]
    .sum()
    .reset_index()
    .sort_values("_sort_key")
    .set_index("temp_range")["TOTAL_TRIPS"]
)
st.bar_chart(bucket_summary)

st.subheader("Demand: Rainy vs. Dry Days")
rain_df = df.copy()
rain_df["condition"] = rain_df["TOTAL_PRECIP_IN"].apply(lambda x: "Rainy" if x > 0 else "Dry")
rain_summary = (
    rain_df.groupby("condition")["TOTAL_TRIPS"]
    .agg(avg_daily_trips="mean", day_count="count")
    .reset_index()
)
col_a, col_b = st.columns(2)
with col_a:
    st.caption("Avg daily trips")
    st.bar_chart(rain_summary.set_index("condition")["avg_daily_trips"])
with col_b:
    st.caption("Number of days")
    st.bar_chart(rain_summary.set_index("condition")["day_count"])

st.subheader("Precipitation Amount vs. Trip Count")
st.caption("Each point is one day. Shows whether heavier rain compounds the effect.")
st.scatter_chart(
    df[["TOTAL_PRECIP_IN", "TOTAL_TRIPS"]].rename(
        columns={"TOTAL_PRECIP_IN": "Precipitation (in)", "TOTAL_TRIPS": "Trip Count"}
    ),
    x="Precipitation (in)",
    y="Trip Count",
)

st.subheader("Daily Trips by Weather Category")
cat_df = (
    df.groupby("WEATHER_CATEGORY")["TOTAL_TRIPS"]
    .sum()
    .reset_index()
    .sort_values("TOTAL_TRIPS", ascending=False)
)
st.bar_chart(cat_df.set_index("WEATHER_CATEGORY")["TOTAL_TRIPS"])

st.subheader("Daily Trip Count")
st.line_chart(df.set_index("TRIP_DATE")["TOTAL_TRIPS"])

# ── Hourly visuals ────────────────────────────────────────────────────────────

hourly_df = query("""
    SELECT
        HOUR(trip_hour)  AS hour_of_day,
        AVG(trip_count)  AS avg_trips
    FROM analytics_db.dbt.mart_hourly_demand_vs_temperature
    GROUP BY 1
    ORDER BY 1
""")

st.subheader("Avg Trip Demand by Hour of Day")
st.line_chart(hourly_df.set_index("HOUR_OF_DAY")["AVG_TRIPS"])

rainy_hourly_df = query("""
    SELECT
        HOUR(t.trip_hour)                                                         AS hour_of_day,
        CASE WHEN w.precipitation_in > 0 THEN 'Raining' ELSE 'Not Raining' END   AS rain_status,
        AVG(t.trip_count)                                                         AS avg_trips
    FROM analytics_db.dbt.mart_hourly_demand_vs_temperature t
    JOIN analytics_db.dbt.fct_weather_hourly w
        ON DATE_TRUNC('hour', t.trip_hour) = w.observation_hour
    WHERE DATE_TRUNC('day', t.trip_hour)::DATE IN (
        SELECT DISTINCT trip_date
        FROM analytics_db.dbt.mart_trip_demand_weather
        WHERE total_precip_in > 0
    )
    GROUP BY 1, 2
    ORDER BY 1, 2
""")

st.subheader("Hourly Demand: Raining vs. Not Raining (on days with precipitation)")
st.caption("Only days that had any precipitation. Shows whether the rainy hour itself suppresses demand.")
pivot = rainy_hourly_df.pivot(
    index="HOUR_OF_DAY", columns="RAIN_STATUS", values="AVG_TRIPS"
)
st.line_chart(pivot)

st.subheader("Hourly Rain vs. Cab Demand — Day Drill-Down")
st.caption("Pick a day to see how precipitation intensity tracks with trip demand hour by hour.")

rainy_days_df = query("""
    SELECT DISTINCT DATE_TRUNC('day', t.trip_hour)::DATE AS trip_date
    FROM analytics_db.dbt.mart_hourly_demand_vs_temperature t
    JOIN analytics_db.dbt.fct_weather_hourly w
        ON DATE_TRUNC('hour', t.trip_hour) = w.observation_hour
    WHERE w.precipitation_in > 0
    ORDER BY 1
""")

selected_day = st.selectbox(
    "Select a rainy day",
    options=rainy_days_df["TRIP_DATE"].tolist(),
    format_func=str,
)

if selected_day:
    day_df = query(f"""
        SELECT
            HOUR(t.trip_hour)       AS hour_of_day,
            SUM(t.trip_count)       AS trip_count,
            MAX(w.precipitation_in) AS precipitation_in
        FROM analytics_db.dbt.mart_hourly_demand_vs_temperature t
        JOIN analytics_db.dbt.fct_weather_hourly w
            ON DATE_TRUNC('hour', t.trip_hour) = w.observation_hour
        WHERE DATE_TRUNC('day', t.trip_hour)::DATE = '{selected_day}'
        GROUP BY 1
        ORDER BY 1
    """)

    base = alt.Chart(day_df).encode(
        x=alt.X("HOUR_OF_DAY:O", title="Hour of Day", axis=alt.Axis(labelAngle=0))
    )
    bars = base.mark_bar(color="#4a90d9", opacity=0.6).encode(
        y=alt.Y("PRECIPITATION_IN:Q", title="Precipitation (in)",
                axis=alt.Axis(titleColor="#4a90d9")),
        tooltip=["HOUR_OF_DAY", "PRECIPITATION_IN"],
    )
    line = base.mark_line(color="#e05252", point=True, strokeWidth=2).encode(
        y=alt.Y("TRIP_COUNT:Q", title="Trip Count",
                axis=alt.Axis(titleColor="#e05252")),
        tooltip=["HOUR_OF_DAY", "TRIP_COUNT"],
    )
    st.altair_chart(
        alt.layer(bars, line).resolve_scale(y="independent").properties(height=300),
        use_container_width=True,
    )

# ── Tier 1: Hour × Day-of-Week demand heatmap ────────────────────────────────

heatmap_df = query("""
    SELECT
        HOUR(trip_hour)         AS hour_of_day,
        DAYOFWEEKISO(trip_hour) AS day_of_week,
        AVG(trip_count)         AS avg_trips
    FROM analytics_db.dbt.mart_hourly_demand_vs_temperature
    GROUP BY 1, 2
    ORDER BY 1, 2
""")

dow_labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
heatmap_df["day_label"] = heatmap_df["DAY_OF_WEEK"].map(dow_labels)

st.subheader("Demand Heatmap: Hour of Day × Day of Week")
st.caption("Avg trip count per cell. Shows commute peaks, late-night weekends, Sunday brunch dip.")
heatmap_chart = (
    alt.Chart(heatmap_df)
    .mark_rect()
    .encode(
        x=alt.X("HOUR_OF_DAY:O", title="Hour of Day"),
        y=alt.Y("day_label:O", title=None,
                sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
        color=alt.Color("avg_trips:Q", scale=alt.Scale(scheme="orangered"), title="Avg Trips"),
        tooltip=["day_label", "HOUR_OF_DAY", alt.Tooltip("avg_trips:Q", format=".0f")],
    )
    .properties(height=220)
)
st.altair_chart(heatmap_chart, use_container_width=True)

# ── Tier 1: Borough weather sensitivity ──────────────────────────────────────

borough_df = query("""
    SELECT
        borough,
        CASE WHEN total_precip_in > 0 THEN 'Rainy' ELSE 'Dry' END AS condition,
        AVG(trip_count) AS avg_trips
    FROM analytics_db.dbt.mart_trip_demand_weather
    GROUP BY 1, 2
""")

st.subheader("Weather Sensitivity by Borough")
st.caption("Avg daily trips per zone on rainy vs. dry days. Outer boroughs are more discretionary; airports should be flat.")
borough_pivot = borough_df.pivot(index="BOROUGH", columns="CONDITION", values="AVG_TRIPS").fillna(0)
borough_pivot["delta_pct"] = ((borough_pivot.get("Rainy", 0) - borough_pivot.get("Dry", 0))
                               / borough_pivot.get("Dry", 1) * 100)
borough_pivot = borough_pivot.sort_values("delta_pct")
st.bar_chart(borough_pivot[["Dry", "Rainy"]])

# ── Tier 1: Tip rate by weather ───────────────────────────────────────────────

tip_df = query("""
    SELECT
        weather_category,
        AVG(avg_tip)                                                    AS avg_tip,
        AVG(CASE WHEN avg_fare > 0 THEN avg_tip / avg_fare ELSE NULL END) AS avg_tip_rate
    FROM analytics_db.dbt.mart_trip_demand_weather
    GROUP BY 1
    ORDER BY 3 DESC
""")

st.subheader("Tip Rate by Weather Category")
st.caption("Do people tip more in bad weather? Guilt, urgency, and gratitude all push tips up on rainy/freezing days.")
col_t1, col_t2 = st.columns(2)
with col_t1:
    st.caption("Avg tip amount ($)")
    st.bar_chart(tip_df.set_index("WEATHER_CATEGORY")["AVG_TIP"])
with col_t2:
    st.caption("Avg tip rate (tip / fare)")
    st.bar_chart(tip_df.set_index("WEATHER_CATEGORY")["AVG_TIP_RATE"])

# ── Tier 1: Trip duration × weather ──────────────────────────────────────────

duration_df = query("""
    SELECT
        weather_category,
        AVG(avg_duration_minutes) AS avg_duration_minutes,
        AVG(avg_fare)             AS avg_fare
    FROM analytics_db.dbt.mart_trip_demand_weather
    GROUP BY 1
    ORDER BY 2 DESC
""")

st.subheader("Trip Duration & Fare by Weather")
st.caption("Bad weather = traffic = longer trips = higher fares. Duration and fare should move together.")
col_d1, col_d2 = st.columns(2)
with col_d1:
    st.caption("Avg duration (minutes)")
    st.bar_chart(duration_df.set_index("WEATHER_CATEGORY")["AVG_DURATION_MINUTES"])
with col_d2:
    st.caption("Avg fare ($)")
    st.bar_chart(duration_df.set_index("WEATHER_CATEGORY")["AVG_FARE"])

# ── Tier 2: Precipitation intensity buckets ───────────────────────────────────

precip_bucket_df = query("""
    SELECT
        CASE
            WHEN precipitation_in = 0     THEN '0 (dry)'
            WHEN precipitation_in <= 0.1  THEN '0–0.1"'
            WHEN precipitation_in <= 0.25 THEN '0.1–0.25"'
            WHEN precipitation_in <= 0.5  THEN '0.25–0.5"'
            ELSE '>0.5"'
        END AS precip_bucket,
        AVG(trip_count) AS avg_trips,
        MIN(CASE
            WHEN precipitation_in = 0     THEN 0
            WHEN precipitation_in <= 0.1  THEN 1
            WHEN precipitation_in <= 0.25 THEN 2
            WHEN precipitation_in <= 0.5  THEN 3
            ELSE 4
        END) AS sort_key
    FROM analytics_db.dbt.mart_hourly_demand_vs_temperature
    GROUP BY 1
    ORDER BY 3
""")

st.subheader("Precipitation Intensity vs. Demand")
st.caption("Light rain → demand spike (people avoid walking). Heavy rain → demand drops (can't get a cab). Look for the sweet spot.")
st.bar_chart(precip_bucket_df.set_index("PRECIP_BUCKET")["AVG_TRIPS"])

# ── Tier 3: Airport vs. Yellow Zone vs. Boro Zone sensitivity ────────────────

zone_sensitivity_df = query("""
    SELECT
        service_zone,
        weather_category,
        AVG(trip_count) AS avg_trips
    FROM analytics_db.dbt.mart_trip_demand_weather
    WHERE service_zone IN ('EWR', 'Yellow Zone', 'Boro Zone')
    GROUP BY 1, 2
    ORDER BY 1, 2
""")

st.subheader("Weather Sensitivity by Service Zone")
st.caption("Airport (EWR) pickups should be weather-immune — travelers have flights. Yellow Zone (Manhattan) and Boro Zone show different sensitivity.")
zone_pivot = zone_sensitivity_df.pivot(
    index="WEATHER_CATEGORY", columns="SERVICE_ZONE", values="AVG_TRIPS"
).fillna(0)
st.line_chart(zone_pivot)

# ── Tier 3: Payment type × weather (requires mart_trip_weather_detail) ────────

pay_df = query("""
    SELECT
        weather_category,
        COUNT_IF(payment_type = 1) * 100.0 / COUNT(*) AS credit_card_pct,
        COUNT_IF(payment_type = 2) * 100.0 / COUNT(*) AS cash_pct
    FROM analytics_db.dbt.mart_trip_weather_detail
    GROUP BY 1
    ORDER BY 2 DESC
""")

st.subheader("Payment Type by Weather")
st.caption("In bad weather, do cash payments drop? People rushing in the rain tap card and go.")
st.bar_chart(pay_df.set_index("WEATHER_CATEGORY")[["CREDIT_CARD_PCT", "CASH_PCT"]])

# ── Tier 2: Wind chill vs. demand ─────────────────────────────────────────────

wind_df = query("""
    SELECT
        AVG(avg_wind_mph)  AS avg_wind_mph,
        AVG(avg_temp_f)    AS avg_temp_f,
        SUM(trip_count)    AS total_trips
    FROM analytics_db.dbt.mart_trip_demand_weather
    GROUP BY trip_date
""")

def wind_chill(t, v):
    if t <= 50 and v > 3:
        return 35.74 + 0.6215 * t - 35.75 * (v ** 0.16) + 0.4275 * t * (v ** 0.16)
    return t

wind_df["feels_like_f"] = wind_df.apply(
    lambda r: wind_chill(r["AVG_TEMP_F"], r["AVG_WIND_MPH"]), axis=1
)

st.subheader("Feels-Like Temperature (Wind Chill) vs. Demand")
st.caption("Wind chill captures 'how bad it is to be outside' better than raw temperature. Compare the cluster tightness to the raw temp scatter above.")
st.scatter_chart(
    wind_df[["feels_like_f", "TOTAL_TRIPS"]].rename(
        columns={"feels_like_f": "Feels-Like Temp (°F)", "TOTAL_TRIPS": "Total Trips"}
    ),
    x="Feels-Like Temp (°F)",
    y="Total Trips",
)

with st.expander("Raw data"):
    st.dataframe(df)
