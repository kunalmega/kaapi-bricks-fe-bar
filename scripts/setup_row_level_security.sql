-- Row-level security: a store manager only ever sees their own store's rows,
-- in Genie, in SQL, and in any tool that reads these tables through Unity Catalog.
-- HQ principals (and the pipeline / app service principals) get '*'.
-- Run once BEFORE the pipeline update that attaches the filter (src/pipeline/02_silver.sql,
-- 03_gold.sql use WITH ROW FILTER ... ON (store_id)).
USE CATALOG fevm_cme_conde_catalog;
USE SCHEMA kaapi_bricks;

-- Who may see which store. principal = current_user() (a user email, or a
-- service principal's application ID). store_id '*' = every store (HQ).
CREATE TABLE IF NOT EXISTS store_access (
  principal   STRING NOT NULL,
  store_id    STRING NOT NULL,
  role        STRING,
  granted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Row-level security mapping: principal -> store_id (or * for HQ). Read by store_row_filter.';

-- The filter runs with the function owner's rights, so readers need no access to store_access.
CREATE OR REPLACE FUNCTION store_row_filter(row_store_id STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: TRUE when the current principal is HQ (*) or mapped to this store.'
RETURN EXISTS (
  SELECT 1 FROM store_access a
  WHERE a.principal = current_user()
    AND (a.store_id = '*' OR a.store_id = row_store_id)
);

-- Mapping rows are inserted by scripts/apply_store_access.py (it resolves the app and
-- pipeline service principals' application IDs in the target workspace), e.g.:
--   INSERT INTO store_access (principal, store_id, role) VALUES ('<owner email>', '*', 'hq');
--   INSERT INTO store_access (principal, store_id, role) VALUES ('<store SP app id>', 'STR-001', 'store_manager');
