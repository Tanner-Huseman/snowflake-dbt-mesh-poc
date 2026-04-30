-- Single X-Small warehouse for the entire POC.
-- Production note: split into wh_ingest, wh_transform, wh_bi for cost attribution.

USE ROLE sysadmin;

CREATE WAREHOUSE IF NOT EXISTS wh_poc_xs
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Shared POC warehouse. Auto-suspends after 60s idle.';

-- Assign to the resource monitor created in resource_monitor.sql.
ALTER WAREHOUSE wh_poc_xs SET RESOURCE_MONITOR = poc_resource_monitor;
