-- Setup script for Ranger to Unity Catalog migration audit tables
-- Run this script before using the translation engine

-- Create catalog and schema for audit tables
CREATE CATALOG IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS main.ranger_migration;

-- Table 1: Raw Ranger policies (source of truth)
CREATE TABLE IF NOT EXISTS main.ranger_migration.ranger_policies_raw (
  timestamp TIMESTAMP,
  policies_json STRING,
  upload_source STRING,
  file_name STRING
)
USING DELTA
COMMENT 'Raw Ranger policy JSON files uploaded for migration';

-- Table 2: Translation log (tracks translation attempts)
CREATE TABLE IF NOT EXISTS main.ranger_migration.translation_log (
  timestamp TIMESTAMP,
  activity STRING,
  ranger_policy_count INT,
  uc_policy_count INT,
  error_count INT,
  errors STRING,
  metadata STRING
)
USING DELTA
COMMENT 'Log of policy translation activities';

-- Table 3: UC policies applied (execution audit trail)
CREATE TABLE IF NOT EXISTS main.ranger_migration.uc_policies_applied (
  timestamp TIMESTAMP,
  policy_id STRING,
  policy_type STRING,
  status STRING,
  message STRING,
  executed_count INT,
  total_statements INT,
  error_details STRING,
  applied_by STRING
)
USING DELTA
COMMENT 'Audit trail of Unity Catalog policies applied';

-- Table 4: Mapping configuration (user-defined mappings)
CREATE TABLE IF NOT EXISTS main.ranger_migration.mapping_config (
  mapping_type STRING,  -- resource, principal, privilege
  ranger_value STRING,
  uc_value STRING,
  created_at TIMESTAMP,
  created_by STRING
)
USING DELTA
COMMENT 'Custom mappings from Ranger to Unity Catalog';

-- Create views for reporting

-- View: Translation summary by date
CREATE OR REPLACE VIEW main.ranger_migration.v_translation_summary AS
SELECT 
  DATE(timestamp) as translation_date,
  COUNT(*) as translation_count,
  SUM(ranger_policy_count) as total_ranger_policies,
  SUM(uc_policy_count) as total_uc_policies,
  SUM(error_count) as total_errors
FROM main.ranger_migration.translation_log
GROUP BY DATE(timestamp)
ORDER BY translation_date DESC;

-- View: Policy application summary
CREATE OR REPLACE VIEW main.ranger_migration.v_application_summary AS
SELECT 
  DATE(timestamp) as application_date,
  policy_type,
  status,
  COUNT(*) as policy_count,
  SUM(executed_count) as statements_executed,
  SUM(total_statements) as total_statements
FROM main.ranger_migration.uc_policies_applied
GROUP BY DATE(timestamp), policy_type, status
ORDER BY application_date DESC, policy_type;

-- View: Recent errors
CREATE OR REPLACE VIEW main.ranger_migration.v_recent_errors AS
SELECT 
  timestamp,
  policy_id,
  policy_type,
  status,
  message,
  error_details
FROM main.ranger_migration.uc_policies_applied
WHERE status IN ('error', 'partial')
ORDER BY timestamp DESC
LIMIT 100;

-- Grant permissions (adjust as needed for your workspace)
-- GRANT ALL PRIVILEGES ON SCHEMA main.ranger_migration TO `your_admin_group`;
-- GRANT SELECT ON SCHEMA main.ranger_migration TO `your_viewer_group`;

SELECT 'Setup completed successfully! Audit tables and views created.' as status;
