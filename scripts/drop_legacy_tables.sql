-- One-time migration: drop the generator-created tables so the Lakeflow medallion
-- pipeline can own them (silver publishes these same plain names).
-- Data is fully synthetic and regenerable via scripts/generate_data.py.
-- Keeps `inference_logs` (app-managed observability, outside the medallion).
-- Run against fevm_cme_conde_catalog.kaapi_bricks (adjust catalog if renamed).

DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.stores;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.products;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.toppings;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.ingredients;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.suppliers;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.promotions;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.customers;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.orders;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.order_items;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.order_item_toppings;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.purchase_orders;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.inventory_transactions;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.promotion_redemptions;
DROP TABLE IF EXISTS fevm_cme_conde_catalog.kaapi_bricks.po_line_items;
