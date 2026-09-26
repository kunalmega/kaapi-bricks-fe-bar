-- =============================================================================
-- BRONZE — raw ingestion from the Unity Catalog Volume via Auto Loader.
-- One streaming table per source entity. Keeps raw fidelity (no drops);
-- adds ingest metadata (_source_file, _ingested_at). Source path comes from the
-- pipeline `source_volume` configuration = /Volumes/<catalog>/<schema>/raw_data.
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_stores
COMMENT 'Raw store master landed from the UC Volume (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/stores/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_products
COMMENT 'Raw product/menu data (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/products/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_toppings
COMMENT 'Raw add-on/topping catalog (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/toppings/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_ingredients
COMMENT 'Raw ingredient master (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/ingredients/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_suppliers
COMMENT 'Raw supplier master (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/suppliers/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_promotions
COMMENT 'Raw promotions catalog (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/promotions/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_customers
COMMENT 'Raw customer master (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/customers/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_orders
COMMENT 'Raw order headers (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/orders/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_order_items
COMMENT 'Raw order line items (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/order_items/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_order_item_toppings
COMMENT 'Raw order-item topping lines (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/order_item_toppings/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_purchase_orders
COMMENT 'Raw supplier purchase orders (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/purchase_orders/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_inventory_transactions
COMMENT 'Raw inventory movements: purchase/usage/waste (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/inventory_transactions/', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_promotion_redemptions
COMMENT 'Raw promotion redemptions (Auto Loader).'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${source_volume}/promotion_redemptions/', format => 'parquet');
