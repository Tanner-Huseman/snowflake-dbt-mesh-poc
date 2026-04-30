# streamlit_app/

Streamlit in Snowflake (SiS) app surfacing the dbt Mesh POC data products.

Three tabs:
1. **Trips** — Daily trip volume, revenue trends, and top pickup zones from `analytics_db.trips_marts`
2. **Weather** — Daily temperature range and precipitation from `analytics_db.weather_marts`
3. **Combined Insights** — Cross-domain scatter charts and category breakdowns from `analytics_db.derived`

The sidebar shows a **data freshness panel** querying `COPY_HISTORY` for the last successful Snowpipe load per source.

---

## Deploying to Streamlit in Snowflake

1. In the Snowflake UI, navigate to **Projects → Streamlit**.
2. Click **+ Streamlit App**.
3. Set:
   - **App name**: `poc_dashboard`
   - **Warehouse**: `wh_poc_xs`
   - **App location**: `analytics_db` / `derived` (or any schema with the needed grants)
4. In the editor, replace the default code with the contents of `app.py`.
5. Click **Run**.

The app runs inside Snowflake's managed runtime, so `snowflake.snowpark` is available without installation.

---

## Packages

The app uses only:
- `streamlit` (built-in to SiS)
- `snowflake.snowpark` (built-in to SiS)
- `pandas` (built-in to SiS)

No additional packages are needed.

If adding charts beyond `st.line_chart` / `st.bar_chart` / `st.scatter_chart`, check the [Snowflake Streamlit package whitelist](https://docs.snowflake.com/en/developer-guide/streamlit/additional-libraries) before importing. `altair` and `plotly` are available; `bokeh` and `matplotlib` are not.

---

## Data Products Consumed

| Tab | Source | Table |
|-----|--------|-------|
| Trips | `analytics_db.trips_marts` | `agg_daily_revenue_by_zone` |
| Weather | `analytics_db.weather_marts` | `agg_daily_weather` |
| Combined | `analytics_db.derived` | `mart_trip_demand_weather` |
| Combined | `analytics_db.derived` | `mart_hourly_demand_vs_temperature` |
| Sidebar | `raw_db.information_schema` | `copy_history()` (table function) |

---

## Local Development

Streamlit in Snowflake does not support a local dev loop out of the box — the
`snowflake.snowpark.context.get_active_session()` call requires running inside
Snowflake's runtime.

Workaround for local testing: replace `get_active_session()` with a standard
`snowflake.connector` connection, or use the
[Snowflake Streamlit local runner](https://docs.snowflake.com/en/developer-guide/streamlit/testing-locally).

For the POC, the SiS deployment is the dev loop. Edit in the Snowflake UI editor,
click Run, iterate.

---

## Adding a New Tab

1. Add a new tab in the `st.tabs([...])` call.
2. Query the relevant mart via `session.sql(...).to_pandas()`.
3. Use `@st.cache_data(ttl=300)` to avoid re-querying on every interaction.
4. Update this README with the new data product reference.
