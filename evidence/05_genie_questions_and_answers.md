# Genie Space Q&A — Kaapi Bricks

Genie Space ID: `01f12a63ec1011e0acbb09158eda7634`  
Tables: silver + gold operational tables in `fevm_cme_conde_catalog.kaapi_bricks`

---

## Question 1: Best-selling drinks this month

**Question asked:** What are the top 5 best-selling drinks this month by units sold?

**Generated SQL:**
```sql
SELECT p.name, p.category, SUM(oi.item_price) AS revenue, COUNT(oi.order_item_id) AS units_sold
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= DATE_TRUNC('month', CURRENT_DATE())
  AND o.status = 'completed'
GROUP BY p.name, p.category
ORDER BY units_sold DESC
LIMIT 5
```

**Result:**
| name | category | revenue (₹) | units_sold |
|---|---|---|---|
| Classic Filter Coffee | Filter Coffee | [FILL] | [FILL] |
| Strong Decoction | Filter Coffee | [FILL] | [FILL] |
| Masala Chai | Traditional | [FILL] | [FILL] |
| Bella Kaapi (Jaggery) | Filter Coffee | [FILL] | [FILL] |
| Cold Coffee | Specialty Coffee | [FILL] | [FILL] |

[FILL: paste actual Genie results after running]

---

## Question 2: Inventory alert across all stores

**Question asked:** Which stores have ingredients below reorder level right now?

**Generated SQL:**
```sql
SELECT g.store_id, s.name AS store_name, g.ingredient_name, g.unit,
       ROUND(g.current_stock, 2) AS current_stock,
       g.reorder_threshold,
       ROUND(g.days_cover, 1) AS days_cover
FROM gold_inventory_position g
JOIN stores s ON g.store_id = s.store_id
WHERE g.below_reorder = TRUE
ORDER BY g.days_cover ASC
LIMIT 20
```

**Result:**
| store_id | store_name | ingredient_name | current_stock | reorder_threshold | days_cover |
|---|---|---|---|---|---|
| STR-001 | Kaapi Bricks Koramangala | Cardamom | 1.2 kg | 2.0 kg | 0.8 |
| STR-009 | Kaapi Bricks Electronic City | Coorg Arabica Beans | 5.1 kg | 10.0 kg | 1.7 |
[FILL: paste actual rows]

---

## Question 3: Overdue supplier deliveries

**Question asked:** Show me all overdue supplier purchase orders.

**Generated SQL:**
```sql
SELECT po_id, supplier_name, store_id, order_date,
       expected_delivery_date, total_amount,
       DATEDIFF(CURRENT_DATE(), expected_delivery_date) AS days_overdue
FROM gold_open_purchase_orders
WHERE is_overdue = TRUE
ORDER BY days_overdue DESC
```

**Result:**
| po_id | supplier_name | store_id | expected_delivery | total_amount (₹) | days_overdue |
|---|---|---|---|---|---|
| PO-01234 | Coorg Coffee Estates | STR-001 | 2026-09-20 | 45,230 | 7 |
| PO-00891 | Kerala Spice Traders | STR-014 | 2026-09-22 | 18,750 | 5 |
[FILL: paste actual rows]

---

## Question 4: Revenue comparison by store, last 30 days

**Question asked:** Compare total revenue across all stores in the last 30 days, sorted highest to lowest.

**Generated SQL:**
```sql
SELECT store_id, SUM(revenue) AS total_revenue_30d,
       SUM(orders) AS total_orders,
       ROUND(AVG(avg_order_value), 2) AS avg_order_value
FROM gold_store_daily_kpis
WHERE order_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY store_id
ORDER BY total_revenue_30d DESC
```

**Result:**
| store_id | total_revenue_30d (₹) | total_orders | avg_order_value (₹) |
|---|---|---|---|
| STR-031 | [FILL] | [FILL] | [FILL] |
| STR-001 | [FILL] | [FILL] | [FILL] |
[FILL: paste actual rows — expected: Dubai (STR-031) and London (STR-033) to rank high due to premium pricing]

---

## Question 5: Supplier performance scorecard

**Question asked:** Which supplier has the lowest on-time delivery rate?

**Generated SQL:**
```sql
SELECT supplier_name, category, total_pos, delivered_pos,
       ROUND(fill_rate * 100, 1) AS fill_rate_pct,
       ROUND(on_time_rate * 100, 1) AS on_time_rate_pct,
       avg_days_late
FROM gold_supplier_performance
ORDER BY on_time_rate ASC
```

**Result:**
| supplier_name | category | total_pos | fill_rate % | on_time_rate % | avg_days_late |
|---|---|---|---|---|---|
| Chennai Packaging Co. | Cups & Packaging | [FILL] | [FILL]% | [FILL]% | [FILL] |
| Kerala Spice Traders | Spices & Flavors | [FILL] | [FILL]% | [FILL]% | [FILL] |
[FILL: paste actual rows]

---

[FILL: Run each question in the Genie Space UI, capture the generated SQL and result table, paste above, then commit this file.]
