"""Sync gold operational tables from Unity Catalog into Lakebase (Postgres).

Run this after every Lakeflow pipeline update so the app can serve
inventory, open POs, delivery exceptions, and product demand at OLTP latency
instead of scanning Delta on every request.

Usage:
    python sync_gold_to_lakebase.py
    python sync_gold_to_lakebase.py --warehouse-id <id> --profile <profile>
"""
import argparse
import time
import uuid
from datetime import datetime

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout, StatementState

try:
    import psycopg
except ImportError:
    import psycopg2 as psycopg

CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"
LAKEBASE_INSTANCE_NAME = "kaapi-bricks"
LAKEBASE_DATABASE_NAME = "databricks_postgres"

# Gold tables to sync → Lakebase target table name
SYNC_TARGETS = [
    ("gold_inventory_position",    "lb_inventory_position"),
    ("gold_open_purchase_orders",  "lb_open_purchase_orders"),
    ("gold_delivery_exceptions",   "lb_delivery_exceptions"),
    ("gold_product_demand_7d",     "lb_product_demand"),
]

# -------------------------------------------------------------------------
# Databricks connection
# -------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--warehouse-id", default=None)
parser.add_argument("--profile", default=None)
args, _ = parser.parse_known_args()

print("Connecting to Databricks workspace...")
w = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
print(f"  Host: {w.config.host}")

warehouse_id = args.warehouse_id
if not warehouse_id:
    warehouses = list(w.warehouses.list())
    running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    warehouse_id = chosen.id
    print(f"  Warehouse: {chosen.name} ({warehouse_id})")


def run_sql(statement, catalog=CATALOG, schema=SCHEMA):
    resp = w.statement_execution.execute_statement(
        statement=statement,
        warehouse_id=warehouse_id,
        catalog=catalog,
        schema=schema,
        wait_timeout="120s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
    )
    while resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state == StatementState.FAILED:
        raise RuntimeError(f"SQL failed: {resp.status.error}\nStatement: {statement[:200]}")
    cols = [c.name for c in (resp.manifest.schema.columns if resp.manifest and resp.manifest.schema else [])]
    rows = resp.result.data_array if resp.result and resp.result.data_array else []
    return cols, rows


# -------------------------------------------------------------------------
# Lakebase connection
# -------------------------------------------------------------------------
print("Connecting to Lakebase...")
cred = w.database.generate_database_credential(
    instance_names=[LAKEBASE_INSTANCE_NAME],
    request_id=str(uuid.uuid4()),
)
instance = w.database.get_database_instance(LAKEBASE_INSTANCE_NAME)
lb_host = instance.read_write_dns
user = w.current_user.me().user_name

conn = psycopg.connect(
    host=lb_host, port=5432, dbname=LAKEBASE_DATABASE_NAME,
    user=user, password=cred.token, sslmode="require", autocommit=True,
)
cur = conn.cursor()
print(f"  Connected to {lb_host}/{LAKEBASE_DATABASE_NAME}")


def lb_exec(sql, params=None):
    cur.execute(sql, params)


# -------------------------------------------------------------------------
# Create Lakebase tables (idempotent)
# -------------------------------------------------------------------------
print("Creating Lakebase tables if not exists...")

lb_exec("""CREATE TABLE IF NOT EXISTS lb_inventory_position (
  store_id TEXT, ingredient_id TEXT, ingredient_name TEXT, unit TEXT,
  current_stock DOUBLE PRECISION, reorder_threshold DOUBLE PRECISION,
  below_reorder BOOLEAN, avg_daily_usage DOUBLE PRECISION,
  days_cover DOUBLE PRECISION, last_txn_date DATE,
  synced_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (store_id, ingredient_id)
)""")

lb_exec("""CREATE TABLE IF NOT EXISTS lb_open_purchase_orders (
  po_id TEXT PRIMARY KEY, supplier_id TEXT, supplier_name TEXT, store_id TEXT,
  order_date DATE, expected_delivery_date DATE, total_amount DOUBLE PRECISION,
  lead_time_days INTEGER, is_overdue BOOLEAN, days_overdue INTEGER,
  synced_at TIMESTAMP DEFAULT NOW()
)""")

lb_exec("""CREATE TABLE IF NOT EXISTS lb_delivery_exceptions (
  po_id TEXT PRIMARY KEY, supplier_id TEXT, supplier_name TEXT, store_id TEXT,
  order_date DATE, expected_delivery_date DATE, actual_delivery_date DATE,
  status TEXT, total_amount DOUBLE PRECISION,
  exception_type TEXT, days_late INTEGER,
  synced_at TIMESTAMP DEFAULT NOW()
)""")

lb_exec("""CREATE TABLE IF NOT EXISTS lb_product_demand (
  store_id TEXT, product_id TEXT, product_name TEXT, category TEXT,
  order_date DATE, units INTEGER, revenue DOUBLE PRECISION, units_28d_avg DOUBLE PRECISION,
  synced_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (store_id, product_id, order_date)
)""")
print("  Tables ready.")


# -------------------------------------------------------------------------
# Sync each gold table
# -------------------------------------------------------------------------
def sync_table(gold_table, lb_table, extra_where=""):
    print(f"\nSyncing {gold_table} → {lb_table} ...")
    sql = f"SELECT * FROM {CATALOG}.{SCHEMA}.{gold_table}{(' WHERE ' + extra_where) if extra_where else ''}"
    cols, rows = run_sql(sql)
    if not cols:
        print(f"  WARNING: {gold_table} returned no columns — pipeline may not have run yet.")
        return 0

    lb_exec(f"TRUNCATE {lb_table}")

    col_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    insert_sql = f"INSERT INTO {lb_table} ({col_list}) VALUES ({placeholders})"

    batch = []
    for row in rows:
        # Cast booleans: Databricks returns 'true'/'false' strings
        processed = []
        for val in row:
            if isinstance(val, str) and val.lower() in ("true", "false"):
                processed.append(val.lower() == "true")
            else:
                processed.append(val if val != "" else None)
        batch.append(tuple(processed))

    if batch:
        cur.executemany(insert_sql, batch)
    print(f"  Synced {len(batch):,} rows.")
    return len(batch)


# gold_product_demand is large — limit to last 7 days for OLTP serving
sync_table("gold_inventory_position",   "lb_inventory_position")
sync_table("gold_open_purchase_orders", "lb_open_purchase_orders")
sync_table("gold_delivery_exceptions",  "lb_delivery_exceptions")
sync_table(
    "gold_product_demand", "lb_product_demand",
    extra_where="order_date >= CURRENT_DATE() - INTERVAL 7 DAYS",
)

print(f"\nSync complete at {datetime.utcnow().isoformat()}Z")
print("Next: run the app and verify /api/lakebase/inventory/<store_id> responds.")
conn.close()
