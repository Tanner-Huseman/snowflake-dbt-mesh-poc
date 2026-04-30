-- Account-level resource monitor with a hard suspend at $200.
-- Run this before creating the warehouse. Non-negotiable on a trial account.

USE ROLE accountadmin;

CREATE OR REPLACE RESOURCE MONITOR poc_resource_monitor
    WITH
        CREDIT_QUOTA = 200
        FREQUENCY = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 75 PERCENT DO NOTIFY
            ON 90 PERCENT DO NOTIFY
            ON 100 PERCENT DO SUSPEND_IMMEDIATE;

-- Apply to account so all warehouses are covered by default.
ALTER ACCOUNT SET RESOURCE_MONITOR = poc_resource_monitor;
