-- App-write tables: live outside the medallion pipeline so the app can INSERT/UPDATE.
-- Run once after the Lakeflow pipeline first deploys. Gold views union these in.
USE CATALOG fevm_cme_conde_catalog;
USE SCHEMA kaapi_bricks;

CREATE TABLE IF NOT EXISTS app_inventory_receipts (
  receipt_id      STRING NOT NULL,
  store_id        STRING NOT NULL,
  ingredient_id   STRING NOT NULL,
  receipt_date    DATE   NOT NULL,
  quantity        DOUBLE NOT NULL,
  unit_cost       DOUBLE,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) USING DELTA
COMMENT 'Invoice-approved inventory receipts written by the app (outside the pipeline).';

CREATE TABLE IF NOT EXISTS app_po_approvals (
  approval_id     STRING NOT NULL,
  po_id           STRING NOT NULL,
  approved_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  actual_delivery DATE
) USING DELTA
COMMENT 'PO approval events written by the app (outside the pipeline).';
