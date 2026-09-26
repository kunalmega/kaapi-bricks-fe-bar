-- =============================================================================
-- GOLD — operational + KPI tables for the store-manager app, Lakebase, and Genie.
-- Deterministic SQL (auditable); the LLM layer explains these numbers, it does
-- not compute them. Business dimensions (store, product, supplier, day) preserved.
-- =============================================================================

-- 1. Per-store daily operational KPIs.
CREATE OR REFRESH MATERIALIZED VIEW gold_store_daily_kpis
COMMENT 'Per-store daily KPIs: orders, revenue, discount, refunds, units, AOV.'
AS
WITH item_units AS (
  SELECT o.store_id, o.order_date, COUNT(oi.order_item_id) AS units_sold
  FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
  GROUP BY o.store_id, o.order_date
)
SELECT
  o.store_id,
  o.order_date,
  COUNT(DISTINCT o.order_id)                                             AS orders,
  ROUND(SUM(o.order_total), 2)                                          AS revenue,
  ROUND(SUM(o.subtotal), 2)                                            AS gross_subtotal,
  ROUND(SUM(o.discount), 2)                                            AS discount_total,
  ROUND(SUM(o.tax), 2)                                                 AS tax_total,
  SUM(CASE WHEN o.status = 'refunded' THEN 1 ELSE 0 END)               AS refunds,
  ROUND(SUM(CASE WHEN o.status = 'refunded' THEN 1 ELSE 0 END)
        / COUNT(DISTINCT o.order_id), 4)                               AS refund_rate,
  ROUND(SUM(o.order_total) / COUNT(DISTINCT o.order_id), 2)            AS avg_order_value,
  SUM(CASE WHEN o.promotion_id IS NOT NULL THEN 1 ELSE 0 END)          AS promo_orders,
  MAX(u.units_sold)                                                    AS units_sold
FROM orders o
LEFT JOIN item_units u ON o.store_id = u.store_id AND o.order_date = u.order_date
GROUP BY o.store_id, o.order_date;

-- 2. Current inventory position per store x ingredient (⭐ served via Lakebase).
CREATE OR REFRESH MATERIALIZED VIEW gold_inventory_position
COMMENT 'Current stock per store x ingredient with below-reorder flag and days of cover.'
AS
WITH pos AS (
  SELECT store_id, ingredient_id,
         SUM(quantity)                                                          AS current_stock,
         SUM(CASE WHEN transaction_type = 'usage' THEN -quantity ELSE 0 END)    AS total_usage,
         COUNT(DISTINCT CASE WHEN transaction_type = 'usage' THEN transaction_date END) AS usage_days,
         MAX(transaction_date)                                                  AS last_txn_date
  FROM inventory_transactions
  GROUP BY store_id, ingredient_id
)
SELECT
  p.store_id, p.ingredient_id, i.name AS ingredient_name, i.unit,
  ROUND(p.current_stock, 2)                                              AS current_stock,
  i.reorder_threshold,
  (p.current_stock < i.reorder_threshold)                               AS below_reorder,
  ROUND(p.total_usage / NULLIF(p.usage_days, 0), 3)                     AS avg_daily_usage,
  ROUND(p.current_stock / NULLIF(p.total_usage / NULLIF(p.usage_days, 0), 0), 1) AS days_cover,
  p.last_txn_date
FROM pos p
JOIN ingredients i ON p.ingredient_id = i.ingredient_id;

-- 3. Open (pending) purchase orders with overdue flag (⭐ Lakebase).
CREATE OR REFRESH MATERIALIZED VIEW gold_open_purchase_orders
COMMENT 'Pending supplier POs with overdue flag and days overdue.'
AS
SELECT
  po.po_id, po.supplier_id, s.name AS supplier_name, po.store_id,
  po.order_date, po.expected_delivery_date, po.total_amount, s.lead_time_days,
  (po.expected_delivery_date < current_date())                          AS is_overdue,
  GREATEST(datediff(current_date(), po.expected_delivery_date), 0)      AS days_overdue
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.supplier_id
WHERE po.status = 'pending';

-- 4. Delivery exceptions: late or cancelled POs (⭐ Lakebase).
CREATE OR REFRESH MATERIALIZED VIEW gold_delivery_exceptions
COMMENT 'Late or cancelled supplier deliveries with days late.'
AS
SELECT
  po.po_id, po.supplier_id, s.name AS supplier_name, po.store_id,
  po.order_date, po.expected_delivery_date, po.actual_delivery_date, po.status,
  po.total_amount,
  CASE WHEN po.status = 'cancelled' THEN 'cancelled' ELSE 'late' END    AS exception_type,
  datediff(po.actual_delivery_date, po.expected_delivery_date)          AS days_late
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.supplier_id
WHERE po.status = 'cancelled'
   OR po.actual_delivery_date > po.expected_delivery_date;

-- 5. Daily product demand per store with 28-day rolling average (⭐ Lakebase subset).
CREATE OR REFRESH MATERIALIZED VIEW gold_product_demand
COMMENT 'Daily units/revenue per store x product with 28-day rolling average demand.'
AS
WITH daily AS (
  SELECT o.store_id, oi.product_id, o.order_date,
         COUNT(oi.order_item_id) AS units,
         ROUND(SUM(oi.item_price), 2) AS revenue
  FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
  WHERE o.status = 'completed'
  GROUP BY o.store_id, oi.product_id, o.order_date
)
SELECT d.store_id, d.product_id, p.name AS product_name, p.category,
       d.order_date, d.units, d.revenue,
       ROUND(AVG(d.units) OVER (
         PARTITION BY d.store_id, d.product_id ORDER BY d.order_date
         ROWS BETWEEN 27 PRECEDING AND CURRENT ROW), 2) AS units_28d_avg
FROM daily d
JOIN products p ON d.product_id = p.product_id;

-- 6. Supplier performance: fill rate, on-time rate, avg days late.
CREATE OR REFRESH MATERIALIZED VIEW gold_supplier_performance
COMMENT 'Supplier scorecard: fill rate, on-time rate, avg days late.'
AS
SELECT
  s.supplier_id, s.name AS supplier_name, s.category, s.reliability_score,
  COUNT(*)                                                                    AS total_pos,
  SUM(CASE WHEN po.status = 'delivered' THEN 1 ELSE 0 END)                    AS delivered_pos,
  ROUND(SUM(CASE WHEN po.status = 'delivered' THEN 1 ELSE 0 END) / COUNT(*), 4) AS fill_rate,
  ROUND(SUM(CASE WHEN po.actual_delivery_date <= po.expected_delivery_date THEN 1 ELSE 0 END)
        / COUNT(*), 4)                                                       AS on_time_rate,
  ROUND(AVG(GREATEST(datediff(po.actual_delivery_date, po.expected_delivery_date), 0)), 2) AS avg_days_late
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.name, s.category, s.reliability_score;

-- 7. Ingredient waste summary per store.
CREATE OR REFRESH MATERIALIZED VIEW gold_waste_summary
COMMENT 'Ingredient waste quantity and cost per store.'
AS
SELECT
  it.store_id, it.ingredient_id, i.name AS ingredient_name,
  ROUND(SUM(-it.quantity), 2)                 AS waste_qty,
  ROUND(SUM(-it.quantity * it.unit_cost), 2)  AS waste_cost
FROM inventory_transactions it
JOIN ingredients i ON it.ingredient_id = i.ingredient_id
WHERE it.transaction_type = 'waste'
GROUP BY it.store_id, it.ingredient_id, i.name;
