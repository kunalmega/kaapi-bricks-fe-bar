# End-to-End Record Trace — Kaapi Bricks

This document traces a single delivery event from raw data through every layer to the app.

**Entity traced:** Purchase Order `PO-01234` (Coorg Coffee Estates → Kaapi Bricks Koramangala)  
**Ingredient:** `ING-001` (Coorg Arabica Beans)

---

## Layer 0 — Raw Parquet (Volume)

**File:** `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/purchase_orders/purchase_orders.parquet`

**Row (as read by `read_files()`):**
```
po_id        | supplier_id | store_id | order_date  | expected_delivery_date | actual_delivery_date | total_amount | status
PO-01234     | SUP-001     | STR-001  | 2026-09-15  | 2026-09-22             | 2026-09-25           | 45230.0      | delivered
```

**PO line item file:** `/Volumes/.../raw_data/po_line_items/po_line_items.parquet`
```
line_id    | po_id   | ingredient_id | ingredient_name     | quantity | unit | unit_price | line_total
PLI-001234 | PO-01234 | ING-001      | Coorg Arabica Beans | 25.0     | kg   | 1200.0     | 30000.0
```

[FILL: use `SELECT * FROM read_files('/Volumes/.../raw_data/purchase_orders/', format=>'parquet') WHERE po_id='PO-01234'` after generate_data.py runs]

---

## Layer 1 — Bronze (Auto Loader streaming table)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders`

```sql
SELECT po_id, supplier_id, store_id, order_date, expected_delivery_date,
       actual_delivery_date, total_amount, status, _source_file, _ingested_at
FROM fevm_cme_conde_catalog.kaapi_bricks.bronze_purchase_orders
WHERE po_id = 'PO-01234'
```

Result:
```
po_id   | supplier_id | store_id | order_date | expected_delivery_date | actual_delivery_date | total_amount | status    | _source_file                          | _ingested_at
PO-01234 | SUP-001    | STR-001  | 2026-09-15 | 2026-09-22             | 2026-09-25           | 45230.0      | delivered | /Volumes/.../purchase_orders.parquet  | [FILL]
```

[FILL: paste actual row after pipeline runs]

---

## Layer 2 — Silver (Materialized View, conformed + typed)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.purchase_orders`

```sql
SELECT po_id, supplier_id, store_id,
       CAST(order_date AS DATE) AS order_date,
       CAST(expected_delivery_date AS DATE) AS expected_delivery_date,
       CAST(actual_delivery_date AS DATE) AS actual_delivery_date,
       CAST(total_amount AS DOUBLE) AS total_amount, status
FROM fevm_cme_conde_catalog.kaapi_bricks.purchase_orders
WHERE po_id = 'PO-01234'
```

Result:
```
po_id   | supplier_id | store_id | order_date | expected_delivery | actual_delivery | total_amount | status
PO-01234 | SUP-001    | STR-001  | 2026-09-15 | 2026-09-22        | 2026-09-25      | 45230.0      | delivered
```

Note: `actual_delivery_date (2026-09-25) > expected_delivery_date (2026-09-22)` → 3 days late

[FILL: paste actual row after pipeline runs]

---

## Layer 3 — Gold (gold_delivery_exceptions)

**Table:** `fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions`

```sql
SELECT po_id, supplier_name, store_id, expected_delivery_date,
       actual_delivery_date, exception_type, days_late, total_amount
FROM fevm_cme_conde_catalog.kaapi_bricks.gold_delivery_exceptions
WHERE po_id = 'PO-01234'
```

Result:
```
po_id   | supplier_name        | store_id | expected_delivery | actual_delivery | exception_type | days_late | total_amount
PO-01234 | Coorg Coffee Estates | STR-001 | 2026-09-22        | 2026-09-25      | late           | 3         | 45230.0
```

[FILL: paste actual row after pipeline runs]

---

## Layer 4 — Lakebase (lb_delivery_exceptions, synced from gold)

```sql
SELECT po_id, supplier_name, store_id, expected_delivery_date,
       actual_delivery_date, exception_type, days_late
FROM lb_delivery_exceptions
WHERE po_id = 'PO-01234';
```

Result: [FILL — should match gold layer above]

---

## Layer 5 — App (Genie / MAS response)

**Question asked in app:** "Are there any overdue deliveries for Koramangala this week?"

**App routing:** MAS → Genie Space (SQL over gold_delivery_exceptions)

**App response excerpt:**
```
Yes — I found 2 overdue deliveries for Koramangala (STR-001) this week:

1. PO-01234 from Coorg Coffee Estates — arrived 3 days late (25 Sep vs expected 22 Sep).
   Total value: ₹45,230. Status: now delivered.

2. PO-01567 from Kerala Spice Traders — still pending, 5 days overdue (expected 22 Sep).
   Total value: ₹18,750. Recommend following up with the supplier today.
```

[FILL: paste actual app response; note the MLflow trace ID for this question]

MLflow trace ID: [FILL]

---

## Lineage Summary

```
raw_data/purchase_orders/purchase_orders.parquet  (PO-01234 row)
  → bronze_purchase_orders                         (+ _source_file, _ingested_at)
  → purchase_orders [silver]                       (dates cast, deduped, expectations checked)
  → gold_delivery_exceptions                       (filter: late/cancelled, join suppliers, compute days_late)
  → lb_delivery_exceptions [Lakebase]              (synced by sync_gold_to_lakebase.py)
  → App response: "2 overdue deliveries for Koramangala"
```
