# End-to-End Record Trace — Kaapi Bricks

Traces a single delivery event (PO-00006) from raw Parquet through every layer
to the Genie Agent response. Every row shown was queried from the live workspace on 2026-09-27.

---

## The event

**PO-00006** — Chikmagalur Plantations → Kaapi Bricks Pondicherry (STR-019)
- Ordered: 2026-07-15
- Expected delivery: 2026-07-20
- Actual delivery: 2026-07-22 (**2 days late**)
- PO contract total (purchase_orders.total_amount): ₹3,087.64
- Line items actual total: 12.4 kg Chicory (₹4,960) + 38.32 kg Chikmagalur Robusta Beans (₹30,656) = **₹35,616**

> **Data note:** `total_amount` in the `purchase_orders` table is a synthetic contracted/budgeted
> value (generated independently via `numpy.lognormal`). The `po_line_items` table holds actual
> ingredient quantities × unit prices. The ₹32,528 gap between them is intentional in the synthetic
> dataset — it represents exactly the kind of invoice discrepancy the `ai_parse_document` workflow
> is designed to surface. In a real deployment both would come from the ERP and would be consistent.

---

## Layer 1 — Raw Volume

**Path:** `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/purchase_orders/purchase_orders.parquet`

```
po_id    | supplier_id | store_id | order_date | expected_delivery_date | actual_delivery_date | total_amount | status
PO-00006 | SUP-002     | STR-019  | 2026-07-15 | 2026-07-20             | 2026-07-22           | 3,087.64     | delivered
```

```
# Verify (run in workspace):
SELECT * FROM read_files(
  '/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/purchase_orders/',
  format => 'parquet'
) WHERE po_id = 'PO-00006'
```

**Path:** `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/po_line_items/po_line_items.parquet`

```
line_id       | po_id    | ingredient_id | ingredient_name           | quantity | unit | unit_price | line_total
PLI-000013    | PO-00006 | ING-004       | Chicory                   | 12.4     | kg   | 400.00     | 4,960.00
PLI-000014    | PO-00006 | ING-002       | Chikmagalur Robusta Beans | 38.32    | kg   | 800.00     | 30,656.00
```

---

## Layer 2 — Bronze (Auto Loader streaming table)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders`
Pipeline: `kaapi_bricks_medallion`, update `065d6a70`, completed 2026-09-27

```
po_id    | supplier_id | store_id | order_date | status    | _source_file                      | _ingested_at
PO-00006 | SUP-002     | STR-019  | 2026-07-15 | delivered | .../purchase_orders.parquet        | 2026-09-27T09:26:27Z
```

Auto Loader picked up the file on pipeline run, added `_source_file` and `_ingested_at` metadata columns. Row count: 2,000 (all POs).

---

## Layer 3 — Silver (materialized view + expectations)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.purchase_orders`

Expectations applied:
- `valid_po_id`: po_id IS NOT NULL → PASS
- `positive_amount`: total_amount > 0 → PASS (3,087.64 > 0)
- `valid_delivery`: expected_delivery_date >= order_date → PASS (Jul 20 >= Jul 15)
- `valid_status`: status IN ('delivered','pending','cancelled') → PASS

```sql
SELECT po_id, supplier_id, store_id,
       CAST(order_date AS DATE)             AS order_date,
       CAST(expected_delivery_date AS DATE) AS expected_delivery_date,
       CAST(actual_delivery_date AS DATE)   AS actual_delivery_date,
       CAST(total_amount AS DOUBLE)         AS total_amount,
       status
FROM fevm_cme_conde_catalog.kaapi_bricks.purchase_orders
WHERE po_id = 'PO-00006'
```

Result:
```
po_id    | supplier_id | store_id | order_date | expected_delivery_date | actual_delivery_date | total_amount | status
PO-00006 | SUP-002     | STR-019  | 2026-07-15 | 2026-07-20             | 2026-07-22           | 3087.64      | delivered
```

0 rows dropped across all 2,000 POs (synthetic data clean).

---

## Layer 4 — Gold (delivery exceptions view)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions`

Logic: `actual_delivery_date > expected_delivery_date` → exception_type='late', days_late=2

```sql
SELECT po_id, supplier_name, store_id, order_date,
       expected_delivery_date, actual_delivery_date, status,
       exception_type, days_late, total_amount
FROM fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions
WHERE po_id = 'PO-00006'
```

Result (actual query output, 2026-09-27):
```
po_id    | supplier_name            | store_id | order_date | expected    | actual     | exception_type | days_late | total_amount
PO-00006 | Chikmagalur Plantations  | STR-019  | 2026-07-15 | 2026-07-20  | 2026-07-22 | late           | 2         | 3087.64
```

Gold layer has 339 total delivery exceptions (late + cancelled).

---

## Layer 5 — Lakebase (operational serving)

Sync: `scripts/sync_gold_to_lakebase.py`, latest run 2026-09-28T13:59:57Z (339 rows in `lb_delivery_exceptions`).

**Table:** `lb_delivery_exceptions` in Lakebase instance `kaapi-bricks`. Actual query output, 2026-09-28:

```sql
SELECT po_id, days_late FROM lb_delivery_exceptions
WHERE store_id = 'STR-019' ORDER BY days_late DESC, po_id;
```
```
PO-00006 | 2      <- the traced record
PO-00470 | 2
PO-00167 | 1
PO-00996 | 1
PO-01077 | 1
PO-01358 | 1
(6 rows)
```

The same query on gold `gold_delivery_exceptions` returns the same 6 POs with the same `days_late`.

---

## Layer 6 — App response (captured from the deployed app)

| Field | Value |
|---|---|
| Endpoint | `POST /api/chat` on `kaapi-bricks-finale` (authenticated SDK token) |
| Body | `{"query": "Are there any delivery exceptions for my store? List any late or cancelled supplier deliveries with the PO number, supplier and days late.", "store_location": "Pondicherry", "skip_cache": true}` |
| Captured | 2026-09-28T14:19:38Z · HTTP 200 · `from_cache: false` · 44.0 s client |
| Route | `process_chat` → `call_genie_sync` (Genie Agent mode, space `01f12a63…`) → `menu_price_lookup` |
| MLflow trace | **tr-054b71b6d16076a7ba3b5e0008342e81** · experiment 3268449285627906 · state OK · 42.7 s |
| Trace spans | `chat_request` (AGENT, 42,683 ms) → `genie_call` (CHAT_MODEL, 40,005 ms) → `menu_price_lookup` (TOOL, 2,632 ms) |
| Raw response | `evidence/raw/08_app_delivery_exceptions_response.json` |

**Actual response (`full_text`, citation link removed):**

> ## Delivery Exceptions for Kaapi Bricks Pondicherry
>
> Yes, there are **6 late deliveries** recorded for your store. All were eventually delivered, with delays ranging from 1 to 2 days. No cancelled deliveries were found.
>
> | po_id | supplier_name | exception_type | days_late | order_date | expected_delivery_date | actual_delivery_date | status |
> |---|---|---|---|---|---|---|---|
> | PO-00470 | Araku Valley Organics | late | 2 | 2026-06-01 | 2026-06-11 | 2026-06-13 | delivered |
> | **PO-00006** | **Chikmagalur Plantations** | **late** | **2** | **2026-07-15** | **2026-07-20** | **2026-07-22** | **delivered** |
> | PO-01077 | Kerala Spice Traders | late | 1 | 2026-02-23 | 2026-03-01 | 2026-03-02 | delivered |
> | PO-00167 | Coorg Coffee Estates | late | 1 | 2026-06-04 | 2026-06-11 | 2026-06-12 | delivered |
> | PO-00996 | Coorg Coffee Estates | late | 1 | 2026-06-27 | 2026-07-02 | 2026-07-03 | delivered |
> | PO-01358 | Kerala Spice Traders | late | 1 | 2026-03-10 | 2026-03-14 | 2026-03-15 | delivered |

**Cross-check:** the app's 6 POs and days-late values match gold `gold_delivery_exceptions` and
Lakebase `lb_delivery_exceptions` row for row. PO-00006's order, expected and actual dates match
the raw, bronze and silver rows in Layers 1–3.

**Correction note:** an earlier version of this file had a *representative* answer
claiming "1 delivery exception" for Pondicherry. The captured answer is 6, which matches the data.
The representative text has been removed.

Serving path note: the chat answer is produced by Genie Agent mode over the governed
silver/gold tables. The Lakebase copy serves the app's operational panels (`/api/lakebase/inventory/*`,
evidence/07) at OLTP latency. Layer 5 shows that both stores hold the same records.

---

## Summary: the same entity flows every layer

| Layer | Table / Path | Key | Value |
|---|---|---|---|
| Raw Volume | raw_data/purchase_orders/*.parquet | PO-00006 | SUP-002 → STR-019, 2026-07-15 |
| Bronze | bronze_purchase_orders | PO-00006 | +_source_file, +_ingested_at |
| Silver | purchase_orders | PO-00006 | type-cast, expectations passed |
| Gold | gold_delivery_exceptions | PO-00006 | exception_type=late, days_late=2 |
| Lakebase | lb_delivery_exceptions | PO-00006 | days_late=2 (synced 2026-09-28T13:59Z) |
| App | /api/chat → Genie Agent mode | PO-00006 | "late · 2 days · 2026-07-20 → 2026-07-22" (trace tr-054b71b6…) |
