# Lakeflow Pipeline Plan — Kaapi Bricks

Design for the one missing mandatory layer. **Plan only — no pipeline code written yet.**
Derived from the real schema in `scripts/generate_data.py` (13 populated tables + `inference_logs`).

---

## 1. What has to change in the current flow

**Today** (`scripts/generate_data.py`):
```
pandas DataFrame → Parquet → /Volumes/…/raw_data/<table>.parquet
                           → CREATE OR REPLACE TABLE … AS SELECT * FROM read_files(…)
```
One-shot batch. No declarative pipeline, no expectations, no medallion, no layered lineage.

**Target:**
```
pandas DataFrame → Parquet → /Volumes/…/raw_data/<entity>/<entity>_<ts>.parquet
                           → Lakeflow pipeline: bronze → silver → gold
```

Two concrete edits to `generate_data.py`:
- `upload_and_create_table()` (lines 133–151) → **`upload_raw_only()`**: write to a
  per-entity *directory* (`raw_data/orders/orders_20260926.parquet`) and **delete the
  `CREATE OR REPLACE TABLE … read_files()` block**. Auto Loader needs a directory per
  entity to watch, and table creation becomes the pipeline's job.
- Keep the volume/schema creation (lines 156–161) and the `inference_logs` DDL (898–915) —
  `inference_logs` is app-managed observability and stays **outside** the medallion.

> **Naming decision:** silver keeps the plain business names the Genie Space, MAS and app
> already query (`orders`, `customers`, …) so the medallion slots in underneath with **zero
> downstream rewrites**. Bronze is `bronze_*`, gold is `gold_*`.

---

## 2. Bronze — raw ingest (13 streaming tables)

One Auto Loader streaming table per entity, schema inferred from Parquet, plus ingest metadata
(`_ingest_file`, `_ingest_ts`). Bronze stays faithful to the source: **no filtering, no casting**.

| Bronze table | Source dir | Approx rows |
|---|---|---|
| `bronze_stores` | `raw_data/stores/` | 37 |
| `bronze_products` | `raw_data/products/` | 28 |
| `bronze_toppings` | `raw_data/toppings/` | 12 |
| `bronze_ingredients` | `raw_data/ingredients/` | 22 |
| `bronze_suppliers` | `raw_data/suppliers/` | 8 |
| `bronze_promotions` | `raw_data/promotions/` | 15 |
| `bronze_customers` | `raw_data/customers/` | 15,000 |
| `bronze_orders` | `raw_data/orders/` | ~200,000 |
| `bronze_order_items` | `raw_data/order_items/` | ~330,000 |
| `bronze_order_item_toppings` | `raw_data/order_item_toppings/` | ~270,000 |
| `bronze_purchase_orders` | `raw_data/purchase_orders/` | 2,000 |
| `bronze_inventory_transactions` | `raw_data/inventory_transactions/` | ~1.6M |
| `bronze_promotion_redemptions` | `raw_data/promotion_redemptions/` | ~36,000 |

---

## 3. Silver — conformed + validated

Type-cast (dates are strings in the Parquet), dedupe on primary key, and enforce expectations.
Quarantine strategy: **`EXPECT` (warn) for business-rule softness, `EXPECT … DROP ROW` for
broken keys** — so data-quality metrics are non-zero and demonstrable in evidence.

| Silver table | Key expectations |
|---|---|
| `stores` | `store_id` not null & unique; `sq_footage > 0`; `opened_date` parses |
| `products` | `product_id` unique; `base_price > 0`; `cost > 0`; `cost < base_price` (margin sanity) |
| `toppings` / `ingredients` / `suppliers` | id not null & unique; `unit_cost > 0`; `reliability_score` in 0–5 |
| `promotions` | `promotion_id` unique; `discount_pct` 0–100; `start_date <= end_date` |
| `customers` | `customer_id` unique; `loyalty_points >= 0`; `birth_month` 1–12; FK → `stores` |
| `orders` | `order_id` unique; `order_total >= 0`; `discount <= subtotal`; `tax >= 0`; FK → `customers`, `stores`; `status` in (completed, refunded) |
| `order_items` | `order_item_id` unique; `item_price > 0`; FK → `orders`, `products` |
| `order_item_toppings` | FK → `order_items`, `toppings`; `price >= 0` |
| `purchase_orders` | `po_id` unique; `total_amount > 0`; `expected_delivery_date >= order_date`; FK → `suppliers`, `stores` |
| `inventory_transactions` | `transaction_id` unique; `transaction_type` in (purchase, usage, waste); **sign rule:** purchase `> 0`, usage/waste `< 0`; FK → `stores`, `ingredients` |
| `promotion_redemptions` | FK → `promotions`, `orders`; `discount_applied >= 0` |

---

## 4. Gold — operational + KPI tables

These are the **deterministic, auditable** numbers. The LLM layer explains and recommends on
top of them; it never computes them.

| Gold table | Grain | Business question it answers | Feeds |
|---|---|---|---|
| `gold_inventory_position` | store × ingredient | "What do I have on hand, and am I below reorder threshold?" — running sum of signed qty vs `reorder_threshold` | **Lakebase**, app, Genie |
| `gold_open_purchase_orders` | po | "What's inbound and when?" — status `pending` + not yet delivered | **Lakebase**, app |
| `gold_delivery_exceptions` | po | "Which deliveries were late or short?" — `actual > expected` delivery date, w/ days-late | **Lakebase**, app, KPI |
| `gold_product_demand_daily` | store × product × date | "How much do I prep tomorrow?" — units/revenue, weekend & holiday flags | **Lakebase**, ML, Genie |
| `gold_store_daily_kpis` | store × date | Revenue, orders, AOV, discount %, waste cost, stockout count | Genie, dashboard |
| `gold_supplier_performance` | supplier | On-time %, fill rate, avg days late, exception rate | Genie, deck |
| `gold_waste_summary` | store × ingredient × month | Waste qty × unit_cost = ₹ waste | KPI math, deck |

**Industry KPIs the FE Bar checklist asks for** map onto these directly:
stockout rate & waste rate ← `gold_inventory_position` + `gold_waste_summary`;
invoice exception rate & supplier fill rate ← `gold_delivery_exceptions` + `gold_supplier_performance`;
labor minutes per delivery ← measured in the demo (30 min → seconds).

---

## 5. Files to create

```
databricks.yml                          bundle root: catalog/schema vars, targets (dev/prod)
resources/kaapi_pipeline.pipeline.yml   serverless LDP, UC-enabled, target schema
src/pipeline/01_bronze.py               13 Auto Loader streaming tables
src/pipeline/02_silver.py               13 conformed tables + expectations
src/pipeline/03_gold.py                 7 operational/KPI tables
```

Edit: `scripts/generate_data.py` (raw-only landing, per above).

---

## 6. Lakebase serving decision

Gold operational tables are small, hot, and queried by point-lookup on `store_id` — a good fit
for OLTP. Heavy analytical scans stay on Delta via Genie.

- **Option A — Synced tables (preferred):** declare a UC→Lakebase synced table for
  `gold_inventory_position`, `gold_open_purchase_orders`, `gold_delivery_exceptions`,
  `gold_product_demand_daily`. Managed, incremental, and it *demonstrates* the product.
- **Option B — Scheduled write:** `scripts/sync_gold_to_lakebase.py` upserts via psycopg into
  existing Lakebase (`kaapi-bricks` / `databricks_postgres`). More control, more code.

Then make **at least one app workflow read business data from Lakebase** — the natural one is
the store-manager "morning prep" view in `apps/main-chat-app/app.py`, which currently only uses
Lakebase for chat memory and QA cache.

---

## 7. Trade-offs to rehearse (roleplay will probe these)

| Choice | Why | Alternative rejected |
|---|---|---|
| Lakebase for gold serving | point-lookup latency for per-store app reads | Delta direct — fine for analytics, slower for OLTP-style reads |
| Genie for NL analytics | governed, no SQL to maintain per question | custom SQL tools — more control, far more upkeep |
| Deterministic gold + LLM on top | numbers are auditable; LLM only explains | LLM computes totals — unauditable, hallucination risk |
| Auto Loader streaming tables | incremental, handles new files, gives DQ metrics | batch CTAS — what we have today, no lineage/DQ |
| Semantic cache in Lakebase | cuts cost/latency on repeat questions | always-fresh — higher cost; note staleness trade-off |

---

## 8. Execution order

1. Edit `generate_data.py` → raw-only, per-entity dirs; re-run to land raw files
2. Create `databricks.yml` + `resources/kaapi_pipeline.pipeline.yml`
3. Write `01_bronze.py` → run → capture row counts
4. Write `02_silver.py` → run → capture expectation pass/fail
5. Write `03_gold.py` → run → capture gold row counts
6. Sync gold → Lakebase; point one app workflow at it
7. Repoint Genie Space at silver + gold
8. Capture all output into `evidence/01`–`04`
9. End-to-end trace: one PO from raw file → bronze → silver → `gold_delivery_exceptions` → app (`evidence/08`)

**Open questions:** catalog/schema stays `fevm_cme_conde_catalog.kaapi_bricks` or rename for a
public repo? Synced tables (A) or scheduled write (B)?
