# Lakeflow Pipeline — Detailed Design (Kaapi Bricks)

Design for the #1 FE Bar gap: replace the one-time `read_files()` batch load with a real
**Lakeflow Spark Declarative Pipeline** (bronze → silver → gold) on serverless compute.

Status: **PLAN ONLY** — no code written yet. Awaiting go-ahead to scaffold.
See `ARCHITECTURE.md` for the whole-journey diagram.

---

## 1. What changes vs. today

| | Today | After |
|---|---|---|
| Raw landing | `generate_data.py` uploads 1 parquet per table to `raw_data/<t>.parquet`, then `CREATE OR REPLACE TABLE AS SELECT read_files(...)` | `generate_data.py` **only lands** raw parquet into `raw_data/<t>/` subdirs — no table creation |
| Ingestion | one-time batch CTAS | **Auto Loader** streaming tables (bronze) |
| Validation | none | **expectations** at silver (drop/quarantine bad rows) |
| Serving tables | flat 13 tables | bronze_/silver_ + **7 gold operational/KPI tables** |
| Lineage | none | full bronze→silver→gold lineage in UC |

**One-time migration:** drop the 13 existing generator-created tables so the pipeline can own
them (`inference_logs` stays app-managed, untouched).

---

## 2. Source entities (13) → bronze

Raw parquet lands at `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/<entity>/`.
One `bronze_<entity>` streaming table each, via Auto Loader (`format=parquet`), adding
`_ingested_at` and `_source_file`. Bronze keeps everything (no drops) — raw fidelity.

`stores, products, toppings, ingredients, suppliers, promotions, customers, orders,
order_items, order_item_toppings, purchase_orders, inventory_transactions, promotion_redemptions`

---

## 3. Silver — conformed + expectations (plain business names)

Silver tables **keep the current names** (`orders`, `customers`, …) so Genie/MAS/app work
unchanged. Type-cast dates/timestamps, dedupe on PK, enforce keys. Expectation policy:
`expect_or_drop` for row-level validity (bad rows quarantined out), `expect` (warn) for soft signals.

| Silver table | Key expectations (`expect_or_drop` unless noted) |
|---|---|
| `stores` | `store_id` not null & unique; `sq_footage`>0; `opened_date` parseable |
| `products` | `product_id` not null; `base_price`>0; `cost`>=0; `cost`<=`base_price` (warn) |
| `toppings` | `topping_id` not null; `price`>=0 |
| `ingredients` | `ingredient_id` not null; `unit_cost`>=0; `supplier_id` not null |
| `suppliers` | `supplier_id` not null; `reliability_score` between 0 and 5 |
| `promotions` | `promotion_id` not null; `discount_pct` between 0 and 100; `end_date`>=`start_date` |
| `customers` | `customer_id` not null & unique; `home_store_id` not null; `loyalty_tier` in set |
| `orders` | `order_id` not null & unique; `order_total`>=0; `subtotal`>=0; `store_id`/`customer_id` not null; `status` in (completed,refunded); derive `order_ts` = `order_date`+`order_time` |
| `order_items` | `order_item_id` not null; `order_id` not null; `product_id` not null; `item_price`>0 |
| `order_item_toppings` | `order_item_id` not null; `topping_id` not null; `price`>=0 |
| `purchase_orders` | `po_id` not null; `total_amount`>0; `expected_delivery_date`>=`order_date`; `status` in set |
| `inventory_transactions` | `transaction_id` not null; `transaction_type` in (purchase,usage,waste); `unit_cost`>=0 |
| `promotion_redemptions` | `redemption_id` not null; `order_id`/`promotion_id` not null; `discount_applied`>=0 |

Referential-integrity (warn-level) checks join to dims (e.g. `orders.store_id` ∈ `stores`).

---

## 4. Gold — operational + KPI tables (7)

These map directly to the store-manager demo. Deterministic SQL (auditable); LLM explains them.

1. **`gold_store_daily_kpis`** — grain: store × day. orders, revenue, units, avg order value,
   discount total, refund rate, promo redemption count. ← `orders`(+`order_items`).
2. **`gold_inventory_position`** ⭐ — grain: store × ingredient. current stock =
   `SUM(quantity)` over `inventory_transactions`; join `reorder_threshold`; `below_reorder` flag,
   `days_cover` estimate. **→ synced to Lakebase.**
3. **`gold_open_purchase_orders`** ⭐ — POs where `status='pending'`; join supplier lead time;
   `is_overdue` = `expected_delivery_date < current_date`. **→ Lakebase.**
4. **`gold_delivery_exceptions`** ⭐ — POs where `actual_delivery_date > expected_delivery_date`
   or `status='cancelled'`; `days_late`. **→ Lakebase.**
5. **`gold_product_demand`** — grain: store × product × day + rolling 7/28-day units, for prep
   recommendations. **→ Lakebase (subset).**
6. **`gold_supplier_performance`** — supplier fill rate, on-time %, avg days late, reliability.
7. **`gold_waste_summary`** — store × ingredient waste qty & cost (`transaction_type='waste'`).

⭐ = the four operational tables that satisfy FE Bar gap #2 (Lakebase operational serving).

---

## 5. Files to create (scaffold — not yet written)

Repo was flattened on 2026-09-26 — `kaapi_bricks_DEMO` is now the repo root
(`FEbar_copy_bricks/`). Scaffolding folders (`src/pipeline/`, `resources/`, `evidence/`,
`deck/`) already exist as empty placeholders. Paths below are repo-root-relative:

```
FEbar_copy_bricks/                       # = repo root (was kaapi_bricks_DEMO)
├── databricks.yml                       # (edit) add pipeline + variables
├── resources/
│   └── kaapi_pipeline.pipeline.yml      # 🔴 LDP resource, serverless, target=kaapi_bricks
├── src/pipeline/                        # (folder exists, empty)
│   ├── 01_bronze.py                     # 🔴 Auto Loader → bronze_* (13)
│   ├── 02_silver.py                     # 🔴 expectations → business tables (13)
│   └── 03_gold.py                       # 🔴 7 gold operational/KPI tables
└── scripts/generate_data.py             # (edit) land raw to per-entity dirs; stop creating tables
```

Modern LDP patterns (Python `@dlt.table` / `@dlt.expect_or_drop`, Auto Loader
`spark.readStream.format("cloudFiles")`) — exact syntax pulled from the
`databricks-pipelines` skill at code time.

---

## 6. Lakebase serving (gap #2)

Sync the 4 ⭐ gold tables to Lakebase (synced tables from UC, snapshot/scheduled). App's store
console reads `gold_inventory_position`, `gold_open_purchase_orders`, `gold_delivery_exceptions`
from Lakebase at OLTP latency instead of scanning Delta. Mechanism (synced table vs scheduled
write job) to confirm against the `databricks-lakebase` skill.

---

## 7. How this closes FE Bar checklist items

- ✅ Lakeflow pipeline resource in the bundle · bronze streaming from Volume · silver with
  expectations · gold operational + KPI tables · lineage across layers (Product checklist §1–8)
- ✅ Lakebase serves operational gold; app reads it (Product §9–10, gap #2)
- Feeds evidence files `01_lakeflow_run.txt`, `02_uc_tables_and_lineage.md`,
  `03_data_quality_results.txt`, `08_end_to_end_record_trace.md`

---

## 8. Open decisions before coding
1. **Catalog/schema:** keep `fevm_cme_conde_catalog.kaapi_bricks`, or rename to a public-safe
   catalog before the GitHub push? (affects app/Genie config)
2. **Bronze trigger:** `availableNow` (batch-like, cheap for demo) vs continuous. Recommend `availableNow`.
3. **Lakebase sync:** synced tables vs scheduled write job.
4. **Migration:** OK to drop the 13 existing tables so the pipeline owns them? (data is regenerable)
