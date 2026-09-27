# Unity Catalog Tables and Lineage — Kaapi Bricks

Catalog: `fevm_cme_conde_catalog`  Schema: `kaapi_bricks`

## Complete Table Inventory

| Full Table Name | Layer | Description | Row Count |
|---|---|---|---|
| fevm_cme_conde_catalog.kaapi_bricks.raw_data (volume) | RAW | Parquet landing zone | — |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_stores | BRONZE | Raw stores, Auto Loader | 37 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_products | BRONZE | Raw products | 28 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_toppings | BRONZE | Raw toppings | 12 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_ingredients | BRONZE | Raw ingredients | 22 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_suppliers | BRONZE | Raw suppliers | 8 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_promotions | BRONZE | Raw promotions | 15 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_customers | BRONZE | Raw customers | 15,000 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_orders | BRONZE | Raw orders | 200,000 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_order_items | BRONZE | Raw order line items | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_order_item_toppings | BRONZE | Raw topping lines | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders | BRONZE | Raw supplier POs | 2,000 |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_inventory_transactions | BRONZE | Raw inventory movements | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_promotion_redemptions | BRONZE | Raw promo redemptions | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.bronze_po_line_items | BRONZE | Raw PO line items | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.stores | SILVER | Conformed store master | 37 |
| fevm_cme_conde_catalog.kaapi_bricks.products | SILVER | Conformed products | 28 |
| fevm_cme_conde_catalog.kaapi_bricks.toppings | SILVER | Conformed toppings | 12 |
| fevm_cme_conde_catalog.kaapi_bricks.ingredients | SILVER | Conformed ingredients | 22 |
| fevm_cme_conde_catalog.kaapi_bricks.suppliers | SILVER | Conformed suppliers | 8 |
| fevm_cme_conde_catalog.kaapi_bricks.promotions | SILVER | Conformed promotions | 15 |
| fevm_cme_conde_catalog.kaapi_bricks.customers | SILVER | Conformed customers | 15,000 |
| fevm_cme_conde_catalog.kaapi_bricks.orders | SILVER | Conformed orders + order_ts | 200,000 |
| fevm_cme_conde_catalog.kaapi_bricks.order_items | SILVER | Conformed order lines | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.order_item_toppings | SILVER | Conformed topping lines | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.purchase_orders | SILVER | Conformed POs | 2,000 |
| fevm_cme_conde_catalog.kaapi_bricks.inventory_transactions | SILVER | Conformed inventory movements | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.promotion_redemptions | SILVER | Conformed redemptions | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.po_line_items | SILVER | Conformed PO line items | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis | GOLD | Store × day KPIs | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.gold_inventory_position | GOLD | Current stock per store × ingredient | 814 |
| fevm_cme_conde_catalog.kaapi_bricks.gold_open_purchase_orders | GOLD | Pending POs with overdue flag | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions | GOLD | Late/cancelled deliveries | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.gold_product_demand | GOLD | Daily demand + 28d rolling avg | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.gold_supplier_performance | GOLD | Supplier fill rate, on-time % | 8 |
| fevm_cme_conde_catalog.kaapi_bricks.gold_waste_summary | GOLD | Waste qty + cost per store | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.app_inventory_receipts | APP | Invoice-approved receipts (app writes) | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.app_po_approvals | APP | PO approval events (app writes) | [FILL] |
| fevm_cme_conde_catalog.kaapi_bricks.inference_logs | APP | MLflow/app observability | [FILL] |

## Lineage Trace: Orders Entity (raw → bronze → silver → gold)

```
/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/orders/orders.parquet
  │  (Auto Loader — STREAM read_files, format=parquet)
  ▼
fevm_cme_conde_catalog.kaapi_bricks.bronze_orders
  │  columns: order_id, customer_id, store_id, order_date, order_time, channel,
  │           subtotal, discount, order_total, tax, promotion_id, status,
  │           _source_file, _ingested_at
  │  (MATERIALIZED VIEW — ROW_NUMBER dedup on order_id, type casting, derive order_ts)
  ▼
fevm_cme_conde_catalog.kaapi_bricks.orders    [silver]
  │  columns: order_id, customer_id, store_id, order_date, order_time, order_ts,
  │           channel, subtotal, discount, order_total, tax, promotion_id, status
  │  expectations enforced: valid_order_id (DROP), valid_keys (DROP),
  │                          non_neg_total (DROP), valid_status (WARN)
  │
  ├─► fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis
  │     (aggregated: store_id × order_date → orders, revenue, AOV, refund_rate, promo_orders)
  │
  └─► fevm_cme_conde_catalog.kaapi_bricks.gold_product_demand
        (joined with order_items → store_id × product_id × order_date → units, revenue, 28d avg)
```

## Lineage Trace: Inventory Entity (raw → bronze → silver → gold)

```
/Volumes/.../raw_data/inventory_transactions/inventory_transactions.parquet
  ▼  Auto Loader
fevm_cme_conde_catalog.kaapi_bricks.bronze_inventory_transactions
  ▼  MV + expectations (valid_txn_id, valid_type DROP, non_neg_cost WARN)
fevm_cme_conde_catalog.kaapi_bricks.inventory_transactions    [silver]
  ▼  + UNION fevm_cme_conde_catalog.kaapi_bricks.app_inventory_receipts (app writes)
fevm_cme_conde_catalog.kaapi_bricks.gold_inventory_position
  ▼  synced to Lakebase table: lb_inventory_position
  ▼  read by app endpoint: GET /api/lakebase/inventory/{store_id}
```

## Verification Queries (run after pipeline completes)

```sql
-- Confirm lineage registered in system tables
SELECT source_table_full_name, target_table_full_name, created_by
FROM system.access.table_lineage
WHERE source_table_full_name LIKE 'fevm_cme_conde_catalog.kaapi_bricks.%'
  AND created_by LIKE '%pipeline%'
ORDER BY source_table_full_name;

-- Row count snapshot across layers
SELECT table_name,
       CASE
         WHEN table_name LIKE 'bronze_%' THEN '1_bronze'
         WHEN table_name LIKE 'gold_%'   THEN '3_gold'
         WHEN table_name LIKE 'app_%'    THEN '4_app'
         ELSE '2_silver'
       END AS layer
FROM information_schema.tables
WHERE table_catalog = 'fevm_cme_conde_catalog'
  AND table_schema  = 'kaapi_bricks'
ORDER BY layer, table_name;
```

[FILL: Paste the query results above after the pipeline runs and commit this file.]
