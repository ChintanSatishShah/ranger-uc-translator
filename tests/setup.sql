-- ==============================================================================
-- OPTIONAL SETUP: Audit Tables for Ranger to UC Migration
-- ==============================================================================
-- This script is OPTIONAL and creates audit/tracking tables for enterprise use.
-- The translation engine works WITHOUT these tables.
-- 
-- PURPOSE:
--   - Track translation history and applied policies
--   - Maintain audit trail for compliance
--   - Store custom resource/principal mappings
--
-- USAGE:
--   1. Ensure you have a Unity Catalog (replace 'main' with your catalog name)
--   2. Review and adjust catalog/schema names below
--   3. Run each section separately (not all at once)
--   4. Update GRANT statements for your workspace groups
--
-- NOTE: The app and translator work fine without running this setup!
-- ==============================================================================

-- STEP 1: Create schema (assumes 'main' catalog exists)
-- If 'main' catalog doesn't exist, replace with your catalog name
CREATE SCHEMA IF NOT EXISTS main.ranger_migration;

-- ==============================================================================
-- STEP 2: Create Tables
-- ==============================================================================

-- TABLE 1: Raw Ranger Policies (Source of Truth)
-- Stores original Ranger policy JSON files for reference and re-translation
CREATE TABLE IF NOT EXISTS main.ranger_migration.ranger_policies_raw (
  timestamp TIMESTAMP,
  policies_json STRING,
  upload_source STRING,
  file_name STRING
)
USING DELTA
COMMENT 'Raw Ranger policy JSON files uploaded for migration';

-- TABLE 2: Translation Log (Activity Tracking)
-- Tracks each translation attempt with success/failure metrics
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

-- TABLE 3: UC Policies Applied (Execution Audit Trail)
-- Records which policies were actually applied to Unity Catalog
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

-- TABLE 4: Mapping Configuration (Custom Overrides)
-- Stores user-defined mappings for resources, principals, and privileges
CREATE TABLE IF NOT EXISTS main.ranger_migration.mapping_config (
  mapping_type STRING,  -- resource, principal, privilege
  ranger_value STRING,
  uc_value STRING,
  created_at TIMESTAMP,
  created_by STRING
)
USING DELTA
COMMENT 'Custom mappings from Ranger to Unity Catalog';

-- ==============================================================================
-- STEP 3: Create Views (run after tables are created)
-- ==============================================================================

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

-- ==============================================================================
-- STEP 4: Set Permissions (Adjust for Your Workspace)
-- ==============================================================================
-- Uncomment and modify these for your workspace groups:
-- GRANT ALL PRIVILEGES ON SCHEMA main.ranger_migration TO `admin_group`;
-- GRANT SELECT ON SCHEMA main.ranger_migration TO `viewer_group`;

-- Verification query
SELECT 'Setup completed successfully! Audit tables and views created in main.ranger_migration schema.' as status;
