# Unity Catalog Tables and Lineage

Catalog: `fevm_cme_conde_catalog`  Schema: `kaapi_bricks`
Pipeline: `kaapi_bricks_medallion` (update 065d6a70, 2026-09-27)

## Table Inventory

| Layer | Full Table Name | Rows | Type |
|---|---|---:|---|
| Raw Volume | raw_data/stores/ | 37 | Parquet file |
| Raw Volume | raw_data/orders/ | 200,000 | Parquet file |
| Raw Volume | raw_data/inventory_transactions/ | 171,163 | Parquet file |
| Raw Volume | raw_data/purchase_orders/ | 2,000 | Parquet file |
| Raw Volume | raw_data/po_line_items/ | 3,493 | Parquet file |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_stores | 37 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_products | 28 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_toppings | 12 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_ingredients | 22 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_suppliers | 8 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_promotions | 15 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_customers | 15,000 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_orders | 200,000 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_order_items | 325,765 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_order_item_toppings | 261,124 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders | 2,000 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_inventory_transactions | 171,163 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_promotion_redemptions | 35,969 | Streaming Table |
| Bronze | fevm_cme_conde_catalog.kaapi_bricks.bronze_po_line_items | 3,493 | Streaming Table |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.stores | 37 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.products | 28 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.toppings | 12 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.ingredients | 22 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.suppliers | 8 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.promotions | 15 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.customers | 15,000 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.orders | 200,000 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.order_items | 325,765 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.order_item_toppings | 261,124 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.purchase_orders | 2,000 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.inventory_transactions | 171,163 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.promotion_redemptions | 35,969 | Materialized View |
| Silver | fevm_cme_conde_catalog.kaapi_bricks.po_line_items | 3,493 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis | 3,693 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_inventory_position | 814 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_open_purchase_orders | 147 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions | 339 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_product_demand | 85,710 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_supplier_performance | 8 | Materialized View |
| Gold | fevm_cme_conde_catalog.kaapi_bricks.gold_waste_summary | 810 | Materialized View |
| App write | fevm_cme_conde_catalog.kaapi_bricks.app_inventory_receipts | 0 | Delta Table |
| App write | fevm_cme_conde_catalog.kaapi_bricks.app_po_approvals | 0 | Delta Table |

## Lineage Traces

### Orders end-to-end

```
raw_data/orders/orders.parquet
  → fevm_cme_conde_catalog.kaapi_bricks.bronze_orders          (Auto Loader, 200,000 rows)
  → fevm_cme_conde_catalog.kaapi_bricks.orders                 (silver MV, 200,000 rows — QUALIFY dedup)
  → fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis  (gold MV, 3,693 rows — grouped by store×day)
  → fevm_cme_conde_catalog.kaapi_bricks.gold_product_demand    (gold MV, 85,710 rows — grouped by store×product×day)
```

### Inventory / delivery end-to-end

```
raw_data/inventory_transactions/inventory_transactions.parquet
  → fevm_cme_conde_catalog.kaapi_bricks.bronze_inventory_transactions   (171,163 rows)
  → fevm_cme_conde_catalog.kaapi_bricks.inventory_transactions          (171,163 rows)
  → fevm_cme_conde_catalog.kaapi_bricks.gold_inventory_position         (814 rows — current stock per store×ingredient)
  → lb_inventory_position (Lakebase)                                    (814 rows — OLTP serving)
  → GET /api/lakebase/inventory/{store_id}                              (app response)

raw_data/purchase_orders/purchase_orders.parquet
  → fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders
  → fevm_cme_conde_catalog.kaapi_bricks.purchase_orders
  → fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions        (339 rows — late/cancelled)
  → fevm_cme_conde_catalog.kaapi_bricks.gold_open_purchase_orders       (147 rows — pending, not approved)
```
