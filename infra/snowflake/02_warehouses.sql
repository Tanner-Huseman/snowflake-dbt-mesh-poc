-- Single X-Small warehouse for the entire POC.
-- Production note: split into wh_ingest, wh_transform, wh_bi for cost attribution.

USE ROLE sysadmin;

CREATE WAREHOUSE IF NOT EXISTS wh_poc_xs
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Shared POC warehouse. Auto-suspends after 60s idle.';

-- Resource monitor is set at the account level (resource_monitor.sql) and covers all warehouses.
-- No per-warehouse attachment needed.
