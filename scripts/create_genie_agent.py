"""Update the Kaapi Bricks Genie Space to replace Knowledge Assistant + Supervisor Agent.

Patches the existing space (01f12a63ec1011e0acbb09158eda7634) with:
- All 21 silver + gold tables
- Store-operations instructions
- 5 benchmark example queries

Usage:
    python create_genie_agent.py
    python create_genie_agent.py --profile DEFAULT --warehouse-id e755eae9d758fdf7
"""
import argparse
import json
import subprocess
import sys

from databricks.sdk import WorkspaceClient

SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"
CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"
DEFAULT_WAREHOUSE = "e755eae9d758fdf7"

SILVER_TABLES = [
    "stores", "products", "toppings", "ingredients", "suppliers",
    "promotions", "customers", "orders", "order_items",
    "order_item_toppings", "purchase_orders", "inventory_transactions",
    "promotion_redemptions", "po_line_items",
]

GOLD_TABLES = [
    "gold_store_daily_kpis", "gold_inventory_position",
    "gold_open_purchase_orders", "gold_delivery_exceptions",
    "gold_product_demand", "gold_supplier_performance", "gold_waste_summary",
]

INSTRUCTIONS = """You are the Kaapi Bricks store operations assistant. Answer questions about sales, inventory, purchase orders, supplier performance, and waste for the 37 Kaapi Bricks filter coffee stores.

Key facts:
- 37 stores across India and 7 international locations (Dubai, Singapore, London, San Francisco, KL, Sydney, Toronto)
- Products: filter coffee, specialty coffee, traditional beverages, seasonal drinks
- Suppliers: 8 core suppliers (dairy, coffee beans, spices, packaging, alt milks)
- Data range: 2026-02-01 to 2026-07-31

For inventory questions: use gold_inventory_position (current stock, below_reorder flag, days_cover).
For purchase order questions: use gold_open_purchase_orders (pending POs) and gold_delivery_exceptions (late/cancelled).
For sales and demand: use gold_store_daily_kpis and gold_product_demand.
For supplier performance: use gold_supplier_performance (fill_rate, on_time_rate).
For waste: use gold_waste_summary.
For detailed order analysis: use orders, order_items joined to products.

When a store name is mentioned (e.g., "Koramangala"), map it to the store_id by joining to the stores table.
Always include store name in results when showing multi-store data.
State the date range of the data when relevant.
For recipe and product preparation questions: answer from your knowledge of the menu (products table has all 28 drinks with categories and bases)."""

EXAMPLE_QUERIES = [
    {
        "question": "Which ingredients are below reorder threshold at Koramangala?",
        "query": (
            "SELECT ip.ingredient_name, ip.unit, ROUND(ip.current_stock, 2) AS current_stock, "
            "ip.reorder_threshold, ROUND(ip.days_cover, 1) AS days_cover "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_inventory_position ip "
            "JOIN fevm_cme_conde_catalog.kaapi_bricks.stores s ON ip.store_id = s.store_id "
            "WHERE s.neighborhood = 'Koramangala' AND ip.below_reorder = true "
            "ORDER BY ip.days_cover ASC"
        ),
    },
    {
        "question": "What are our top 5 selling products this month?",
        "query": (
            "SELECT product_name, category, "
            "SUM(units) AS total_units, ROUND(SUM(revenue), 2) AS total_revenue "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_product_demand "
            "WHERE order_date >= DATE_TRUNC('month', MAX(order_date) OVER ()) "
            "GROUP BY product_name, category "
            "ORDER BY total_units DESC LIMIT 5"
        ),
    },
    {
        "question": "Show me overdue purchase orders",
        "query": (
            "SELECT po_id, supplier_name, store_id, order_date, "
            "expected_delivery_date, days_overdue, ROUND(total_amount, 2) AS total_amount "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_open_purchase_orders "
            "WHERE is_overdue = true "
            "ORDER BY days_overdue DESC"
        ),
    },
    {
        "question": "Which suppliers have the worst on-time delivery rate?",
        "query": (
            "SELECT supplier_name, category, total_pos, "
            "ROUND(fill_rate * 100, 1) AS fill_rate_pct, "
            "ROUND(on_time_rate * 100, 1) AS on_time_rate_pct, "
            "ROUND(avg_days_late, 1) AS avg_days_late "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_supplier_performance "
            "ORDER BY on_time_rate ASC"
        ),
    },
    {
        "question": "What is the daily revenue trend for all stores this week?",
        "query": (
            "SELECT order_date, SUM(revenue) AS total_revenue, "
            "SUM(orders) AS total_orders, ROUND(AVG(avg_order_value), 2) AS avg_order_value "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis "
            "WHERE order_date >= (SELECT MAX(order_date) - INTERVAL 7 DAYS "
            "FROM fevm_cme_conde_catalog.kaapi_bricks.gold_store_daily_kpis) "
            "GROUP BY order_date ORDER BY order_date"
        ),
    },
]


def build_serialized_space(warehouse_id: str) -> dict:
    all_tables = SILVER_TABLES + GOLD_TABLES
    tables = sorted(
        [{"identifier": f"{CATALOG}.{SCHEMA}.{t}"} for t in all_tables],
        key=lambda x: x["identifier"],
    )

    snippets = [
        {
            "title": eq["question"],
            "query": eq["query"],
        }
        for eq in EXAMPLE_QUERIES
    ]

    return {
        "version": 2,
        "display_name": "Kaapi Bricks Store Operations",
        "description": "Governed analytics and operational Q&A for Kaapi Bricks store managers — 37 stores, South Indian filter coffee.",
        "instructions": INSTRUCTIONS,
        "data_sources": {
            "tables": tables,
        },
        "sql_snippets": snippets,
    }


def patch_space(space_id: str, serialized_space: dict, warehouse_id: str, profile: str, host: str) -> dict:
    payload = {
        "title": "Kaapi Bricks Store Operations",
        "description": "Governed analytics and operational Q&A for Kaapi Bricks store managers — 37 stores, South Indian filter coffee.",
        "warehouse_id": warehouse_id,
        "serialized_space": serialized_space,
    }

    payload_path = "/tmp/kaapi_genie_patch.json"
    with open(payload_path, "w") as f:
        json.dump(payload, f)

    result = subprocess.run(
        [
            "databricks", "api", "patch",
            f"/api/2.0/genie/spaces/{space_id}",
            "--profile", profile,
            "--json", f"@{payload_path}",
        ],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"  PATCH stderr: {result.stderr[:400]}")
        raise RuntimeError(f"PATCH failed (exit {result.returncode}): {result.stdout[:400]}")

    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Update Kaapi Bricks Genie Space")
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE)
    args = parser.parse_args()

    print("Connecting to Databricks workspace...")
    w = WorkspaceClient(profile=args.profile)
    host = w.config.host.rstrip("/")
    print(f"  Host: {host}")
    print(f"  Warehouse: {args.warehouse_id}")
    print(f"  Space ID: {SPACE_ID}")

    print("\nBuilding serialized_space payload...")
    serialized = build_serialized_space(args.warehouse_id)
    tables_count = len(serialized["data_sources"]["tables"])
    snippets_count = len(serialized["sql_snippets"])
    print(f"  Tables: {tables_count} ({len(SILVER_TABLES)} silver + {len(GOLD_TABLES)} gold)")
    print(f"  Example queries: {snippets_count}")

    print("\nPatching Genie Space via CLI...")
    patch_space(SPACE_ID, serialized, args.warehouse_id, args.profile, host)
    print("  Space updated.")

    space_url = f"{host}/genie/rooms/{SPACE_ID}"
    print(f"\nGenie Space URL: {space_url}")
    print(f"Space ID:        {SPACE_ID}")

    print(f"""
NOTE: To add Content Search over documents (replaces Knowledge Assistant):
  1. Open the Genie Space in the UI: {space_url}
  2. Click Settings → Content Search → Add Volume
  3. Add: /Volumes/{CATALOG}/{SCHEMA}/raw_data/ka_documents
  4. This indexes: barista_training_manual.pdf, drink_recipes_sop.pdf,
     food_safety_policy.pdf, franchise_operations_guide.pdf,
     equipment_maintenance_guide.pdf, supplier_agreements_summary.pdf

After adding Content Search, update GENIE_SPACE_ID in app.yaml if needed
and redeploy: databricks bundle deploy -t dev --profile {args.profile}
""")


if __name__ == "__main__":
    main()
