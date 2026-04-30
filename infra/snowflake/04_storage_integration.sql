-- S3 storage integration for Snowpipe auto-ingest.
-- After running, execute DESC INTEGRATION poc_s3_integration and copy
-- STORAGE_AWS_IAM_USER_ARN + STORAGE_AWS_EXTERNAL_ID into your AWS IAM role trust policy.
-- See infra/README.md for the exact trust policy JSON snippet.

USE ROLE accountadmin;

CREATE OR REPLACE STORAGE INTEGRATION poc_s3_integration
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = '<your-iam-role-arn>'
    STORAGE_ALLOWED_LOCATIONS = (
        's3://<your-bucket>/trips/',
        's3://<your-bucket>/weather/'
    )
    COMMENT = 'POC: S3 access for Snowpipe auto-ingest (trips + weather)';

-- Run this after creation to retrieve IAM values for the trust policy.
DESC INTEGRATION poc_s3_integration;
