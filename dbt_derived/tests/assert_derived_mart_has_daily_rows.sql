-- Sanity check: the derived mart must have at least one row per day
-- in the loaded date range. Fails if any day has zero trips joined with weather.
-- Returns rows that fail (dates where no zones had trips + weather data).

with daily_counts as (
    select
        trip_date,
        count(*) as zone_count
    from {{ ref('mart_trip_demand_weather') }}
    group by 1
),

date_range as (
    select
        min(trip_date) as first_date,
        max(trip_date) as last_date
    from {{ ref('mart_trip_demand_weather') }}
),

all_dates as (
    select
        dateadd('day', seq4(), first_date) as expected_date
    from table(generator(rowcount => 366))
    cross join date_range
    where dateadd('day', seq4(), first_date) <= last_date
)

select
    d.expected_date as missing_date
from all_dates d
left join daily_counts c
    on d.expected_date = c.trip_date
where c.trip_date is null
