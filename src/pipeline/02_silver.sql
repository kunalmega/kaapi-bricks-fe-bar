-- =============================================================================
-- SILVER — conformed, type-cast, de-duplicated, with data-quality expectations.
-- Materialized views read bronze as batch. Tables keep their PLAIN business names
-- (orders, customers, ...) so the existing Genie Space / MAS / app work unchanged.
-- expect_or_drop = row-level validity (bad rows quarantined out); expect = warn.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW stores (
  CONSTRAINT valid_store_id EXPECT (store_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_sqft  EXPECT (sq_footage > 0)
)
COMMENT 'Conformed store master (silver).'
AS SELECT store_id, name, city, state, neighborhood,
          CAST(sq_footage AS INT)       AS sq_footage,
          CAST(seating_capacity AS INT) AS seating_capacity,
          CAST(opened_date AS DATE)     AS opened_date
FROM bronze_stores
QUALIFY ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW products (
  CONSTRAINT valid_product_id EXPECT (product_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_price   EXPECT (base_price > 0) ON VIOLATION DROP ROW,
  CONSTRAINT cost_le_price    EXPECT (cost <= base_price)
)
COMMENT 'Conformed product/menu (silver).'
AS SELECT product_id, name, category,
          CAST(base_price AS DOUBLE) AS base_price,
          CAST(cost AS DOUBLE)       AS cost,
          CAST(is_seasonal AS BOOLEAN) AS is_seasonal,
          beverage_base
FROM bronze_products
QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW toppings (
  CONSTRAINT valid_topping_id EXPECT (topping_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_price EXPECT (price >= 0)
)
COMMENT 'Conformed add-on/topping catalog (silver).'
AS SELECT topping_id, name, CAST(price AS DOUBLE) AS price,
          CAST(cost AS DOUBLE) AS cost, CAST(is_available AS BOOLEAN) AS is_available
FROM bronze_toppings
QUALIFY ROW_NUMBER() OVER (PARTITION BY topping_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ingredients (
  CONSTRAINT valid_ingredient_id EXPECT (ingredient_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT has_supplier        EXPECT (supplier_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_cost   EXPECT (unit_cost >= 0)
)
COMMENT 'Conformed ingredient master (silver).'
AS SELECT ingredient_id, name, unit,
          CAST(unit_cost AS DOUBLE) AS unit_cost, supplier_id,
          CAST(reorder_threshold AS DOUBLE) AS reorder_threshold
FROM bronze_ingredients
QUALIFY ROW_NUMBER() OVER (PARTITION BY ingredient_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW suppliers (
  CONSTRAINT valid_supplier_id EXPECT (supplier_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_reliability EXPECT (reliability_score BETWEEN 0 AND 5)
)
COMMENT 'Conformed supplier master (silver).'
AS SELECT supplier_id, name, country, category,
          CAST(lead_time_days AS INT) AS lead_time_days,
          CAST(reliability_score AS DOUBLE) AS reliability_score
FROM bronze_suppliers
QUALIFY ROW_NUMBER() OVER (PARTITION BY supplier_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW promotions (
  CONSTRAINT valid_promotion_id EXPECT (promotion_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_discount     EXPECT (discount_pct BETWEEN 0 AND 100) ON VIOLATION DROP ROW,
  CONSTRAINT valid_window       EXPECT (end_date >= start_date)
)
COMMENT 'Conformed promotions (silver).'
AS SELECT promotion_id, name, type,
          CAST(discount_pct AS DOUBLE) AS discount_pct,
          CAST(min_order AS DOUBLE)    AS min_order,
          CAST(start_date AS DATE)     AS start_date,
          CAST(end_date AS DATE)       AS end_date,
          store_id
FROM bronze_promotions
QUALIFY ROW_NUMBER() OVER (PARTITION BY promotion_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW customers (
  CONSTRAINT valid_customer_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT has_home_store    EXPECT (home_store_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_tier        EXPECT (loyalty_tier IN ('Bronze','Silver','Gold','Platinum Tumbler'))
)
COMMENT 'Conformed customer master (silver).'
AS SELECT customer_id, first_name, last_name, email, loyalty_tier,
          CAST(loyalty_points AS INT) AS loyalty_points,
          preferred_milk, home_store_id,
          CAST(joined_date AS DATE) AS joined_date,
          CAST(birth_month AS INT)  AS birth_month,
          CAST(is_student AS BOOLEAN) AS is_student,
          CAST(app_user AS BOOLEAN)   AS app_user
FROM bronze_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW orders (
  CONSTRAINT valid_order_id  EXPECT (order_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_keys      EXPECT (store_id IS NOT NULL AND customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_neg_total   EXPECT (order_total >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT non_neg_subtotal EXPECT (subtotal >= 0),
  CONSTRAINT valid_status    EXPECT (status IN ('completed','refunded'))
)
COMMENT 'Conformed order headers (silver); adds order_ts timestamp.'
AS SELECT order_id, customer_id, store_id,
          CAST(order_date AS DATE) AS order_date,
          order_time,
          to_timestamp(concat(order_date, ' ', order_time), 'yyyy-MM-dd HH:mm') AS order_ts,
          channel,
          CAST(subtotal AS DOUBLE)    AS subtotal,
          CAST(discount AS DOUBLE)    AS discount,
          CAST(order_total AS DOUBLE) AS order_total,
          CAST(tax AS DOUBLE)         AS tax,
          promotion_id, status
FROM bronze_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW order_items (
  CONSTRAINT valid_item_id EXPECT (order_item_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_order   EXPECT (order_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_product EXPECT (product_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_price EXPECT (item_price > 0)
)
COMMENT 'Conformed order line items (silver).'
AS SELECT order_item_id, order_id, product_id, size, sweetness_level,
          temperature, milk_type, CAST(item_price AS DOUBLE) AS item_price
FROM bronze_order_items
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_item_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW order_item_toppings (
  CONSTRAINT valid_oit_id EXPECT (order_item_topping_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_item   EXPECT (order_item_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_topping EXPECT (topping_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_neg_price EXPECT (price >= 0)
)
COMMENT 'Conformed order-item topping lines (silver).'
AS SELECT order_item_topping_id, order_item_id, topping_id, CAST(price AS DOUBLE) AS price
FROM bronze_order_item_toppings
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_item_topping_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW purchase_orders (
  CONSTRAINT valid_po_id     EXPECT (po_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount EXPECT (total_amount > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_delivery  EXPECT (expected_delivery_date >= order_date),
  CONSTRAINT valid_status    EXPECT (status IN ('delivered','pending','cancelled'))
)
COMMENT 'Conformed supplier purchase orders (silver).'
AS SELECT po_id, supplier_id, store_id,
          CAST(order_date AS DATE)              AS order_date,
          CAST(expected_delivery_date AS DATE)  AS expected_delivery_date,
          CAST(actual_delivery_date AS DATE)    AS actual_delivery_date,
          CAST(total_amount AS DOUBLE)          AS total_amount,
          status
FROM bronze_purchase_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY po_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW inventory_transactions (
  CONSTRAINT valid_txn_id EXPECT (transaction_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_type   EXPECT (transaction_type IN ('purchase','usage','waste')) ON VIOLATION DROP ROW,
  CONSTRAINT non_neg_cost EXPECT (unit_cost >= 0)
)
COMMENT 'Conformed inventory movements (silver); quantity is signed.'
AS SELECT transaction_id, store_id, ingredient_id,
          CAST(transaction_date AS DATE) AS transaction_date,
          transaction_type,
          CAST(quantity AS DOUBLE)  AS quantity,
          CAST(unit_cost AS DOUBLE) AS unit_cost
FROM bronze_inventory_transactions
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW promotion_redemptions (
  CONSTRAINT valid_redemption_id EXPECT (redemption_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_refs EXPECT (order_id IS NOT NULL AND promotion_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_neg_discount EXPECT (discount_applied >= 0)
)
COMMENT 'Conformed promotion redemptions (silver).'
AS SELECT redemption_id, promotion_id, order_id, customer_id, store_id,
          CAST(redemption_date AS DATE) AS redemption_date,
          CAST(discount_applied AS DOUBLE) AS discount_applied
FROM bronze_promotion_redemptions
QUALIFY ROW_NUMBER() OVER (PARTITION BY redemption_id ORDER BY _ingested_at DESC) = 1;
