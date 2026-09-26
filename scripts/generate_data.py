"""Generate synthetic data for Kaapi Bricks South Indian filter coffee chain.

Writes Delta tables to Databricks Unity Catalog via the Databricks SDK.
Requires: pip install -r requirements.txt
Uses the default Databricks CLI profile from ~/.databrickscfg.
"""
import io
import time
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
try:
    import holidays
except ImportError:
    holidays = None
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout, StatementState

# =============================================================================
# CONFIGURATION
# =============================================================================
CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

N_CUSTOMERS = 15000
N_ORDERS = 200000

END_DATE = datetime(2026, 7, 31)
START_DATE = END_DATE - timedelta(days=180)

# Monsoon kaapi promo - ~3 months ago
MONSOON_PROMO_START = END_DATE - timedelta(days=120)
MONSOON_PROMO_END = END_DATE - timedelta(days=90)

# Newest store opening spike - ~6 weeks ago
NEW_STORE_OPEN = END_DATE - timedelta(days=42)

if holidays:
    COUNTRY_HOLIDAYS = {
        "India": holidays.IN(years=[START_DATE.year, END_DATE.year]),
        "UAE": holidays.AE(years=[START_DATE.year, END_DATE.year]),
        "Singapore": holidays.SG(years=[START_DATE.year, END_DATE.year]),
        "UK": holidays.GB(years=[START_DATE.year, END_DATE.year]),
        "USA": holidays.US(years=[START_DATE.year, END_DATE.year]),
        "Australia": holidays.AU(years=[START_DATE.year, END_DATE.year]),
        "Canada": holidays.CA(years=[START_DATE.year, END_DATE.year]),
        "Malaysia": holidays.MY(years=[START_DATE.year, END_DATE.year]),
    }
else:
    from datetime import date
    _years = [START_DATE.year, END_DATE.year]
    _hols_india = {date(y, 1, 26) for y in _years} | {date(y, 8, 15) for y in _years} | {date(y, 10, 2) for y in _years} | {date(y, 11, 1) for y in _years}
    _hols_uae = {date(y, 12, 2) for y in _years} | {date(y, 1, 1) for y in _years}
    _hols_sg = {date(y, 8, 9) for y in _years} | {date(y, 1, 1) for y in _years}
    _hols_uk = {date(y, 12, 25) for y in _years} | {date(y, 1, 1) for y in _years}
    _hols_us = {date(y, 7, 4) for y in _years} | {date(y, 12, 25) for y in _years} | {date(y, 1, 1) for y in _years}
    _hols_au = {date(y, 1, 26) for y in _years} | {date(y, 12, 25) for y in _years}
    _hols_ca = {date(y, 7, 1) for y in _years} | {date(y, 12, 25) for y in _years}
    _hols_my = {date(y, 8, 31) for y in _years} | {date(y, 1, 1) for y in _years}
    COUNTRY_HOLIDAYS = {
        "India": _hols_india, "UAE": _hols_uae, "Singapore": _hols_sg,
        "UK": _hols_uk, "USA": _hols_us, "Australia": _hols_au,
        "Canada": _hols_ca, "Malaysia": _hols_my,
    }
SEED = 42

# =============================================================================
# SETUP
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker("en_IN")

# --- Databricks SDK connection ---
# Works both locally (with CLI profile) and on Databricks clusters (auto-auth)
_is_databricks = False
try:
    # On Databricks cluster, spark session is already available
    spark  # noqa: F821 — injected by Databricks runtime
    _is_databricks = True
except NameError:
    pass

if _is_databricks:
    # Running on a Databricks cluster — no argparse, no profile needed
    print("Running on Databricks cluster...")
    w = WorkspaceClient()
    warehouse_id = None
else:
    # Running locally — use argparse for CLI options
    parser = argparse.ArgumentParser(description="Generate Kaapi Bricks synthetic data")
    parser.add_argument("--warehouse-id", default=None, help="SQL warehouse ID (auto-discovered if omitted)")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile name (uses default if omitted)")
    args, _ = parser.parse_known_args()
    print("Connecting to Databricks workspace...")
    w = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
    warehouse_id = args.warehouse_id

print(f"  Host: {w.config.host}")

if not warehouse_id:
    print("  Discovering SQL warehouse...")
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found. Provide --warehouse-id or create a warehouse.")
    running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    warehouse_id = chosen.id
    print(f"  Using warehouse: {chosen.name} ({warehouse_id})")


def run_sql(statement, catalog=None, schema=None):
    """Execute SQL via Statement Execution API and wait for completion."""
    resp = w.statement_execution.execute_statement(
        statement=statement,
        warehouse_id=warehouse_id,
        catalog=catalog if catalog is not None else CATALOG,
        schema=schema if schema is not None else SCHEMA,
        wait_timeout="50s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
    )
    while resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state == StatementState.FAILED:
        raise RuntimeError(f"SQL failed: {resp.status.error}\nStatement: {statement[:200]}")
    return resp


def land_raw_files(table_name, df):
    """Land a pandas DataFrame as Parquet into a per-entity folder in the raw Volume.

    One folder per entity (raw_data/<table>/<table>.parquet) so the Lakeflow
    medallion pipeline can ingest each source with Auto Loader. Delta table
    creation is owned by the Lakeflow pipeline, NOT this script.
    """
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data/{table_name}/{table_name}.parquet"
    w.files.upload(volume_path, parquet_buffer, overwrite=True)
    print(f"    Landed raw_data/{table_name}/{table_name}.parquet ({len(df):,} rows)")

# =============================================================================
# CREATE INFRASTRUCTURE
# =============================================================================
print("Setting up catalog/schema/volume...")
run_sql(f"USE CATALOG {CATALOG}", catalog=CATALOG, schema="default")
print(f"  Catalog {CATALOG} ready")
run_sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}", catalog=CATALOG, schema="default")
run_sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")
print(f"  Volume ready at {VOLUME_PATH}")

# =============================================================================
# 1. STORES
# =============================================================================
print("Generating stores...")

STORE_META = {
    # Bangalore (10 stores)
    "STR-001": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-002": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-003": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-004": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-005": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-006": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-007": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-008": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-009": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-010": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    # Other South India (10 stores)
    "STR-011": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-012": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-013": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-014": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-015": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-016": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-017": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-018": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-019": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-020": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    # Rest of India (10 stores)
    "STR-021": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-022": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-023": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-024": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-025": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-026": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-027": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-028": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-029": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    "STR-030": {"country": "India", "tax_rate": 0.05, "hemisphere": "N", "holiday_key": "India"},
    # International (7 stores)
    "STR-031": {"country": "UAE",       "tax_rate": 0.00,   "hemisphere": "N", "holiday_key": "UAE"},
    "STR-032": {"country": "Singapore", "tax_rate": 0.09,   "hemisphere": "N", "holiday_key": "Singapore"},
    "STR-033": {"country": "UK",        "tax_rate": 0.20,   "hemisphere": "N", "holiday_key": "UK"},
    "STR-034": {"country": "USA",       "tax_rate": 0.0875, "hemisphere": "N", "holiday_key": "USA"},
    "STR-035": {"country": "Malaysia",  "tax_rate": 0.06,   "hemisphere": "N", "holiday_key": "Malaysia"},
    "STR-036": {"country": "Australia", "tax_rate": 0.10,   "hemisphere": "S", "holiday_key": "Australia"},
    "STR-037": {"country": "Canada",    "tax_rate": 0.13,   "hemisphere": "N", "holiday_key": "Canada"},
}

stores_data = [
    # Bangalore (10)
    {"store_id": "STR-001", "name": "Kaapi Bricks Koramangala",       "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Koramangala",       "sq_footage": 450,  "seating_capacity": 14, "opened_date": "2022-06-01"},
    {"store_id": "STR-002", "name": "Kaapi Bricks Indiranagar",       "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Indiranagar",       "sq_footage": 420,  "seating_capacity": 12, "opened_date": "2022-09-15"},
    {"store_id": "STR-003", "name": "Kaapi Bricks Jayanagar",         "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Jayanagar 4th Block","sq_footage": 380, "seating_capacity": 10, "opened_date": "2023-01-10"},
    {"store_id": "STR-004", "name": "Kaapi Bricks Whitefield",        "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Whitefield",        "sq_footage": 500,  "seating_capacity": 16, "opened_date": "2023-04-20"},
    {"store_id": "STR-005", "name": "Kaapi Bricks MG Road",           "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "MG Road",           "sq_footage": 400,  "seating_capacity": 12, "opened_date": "2023-06-01"},
    {"store_id": "STR-006", "name": "Kaapi Bricks HSR Layout",        "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "HSR Layout",        "sq_footage": 380,  "seating_capacity": 10, "opened_date": "2023-08-15"},
    {"store_id": "STR-007", "name": "Kaapi Bricks Malleshwaram",      "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Malleshwaram",      "sq_footage": 350,  "seating_capacity": 10, "opened_date": "2023-11-01"},
    {"store_id": "STR-008", "name": "Kaapi Bricks Basavanagudi",      "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Basavanagudi",      "sq_footage": 320,  "seating_capacity": 8,  "opened_date": "2024-02-01"},
    {"store_id": "STR-009", "name": "Kaapi Bricks Electronic City",   "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "Electronic City",   "sq_footage": 480,  "seating_capacity": 14, "opened_date": NEW_STORE_OPEN.strftime("%Y-%m-%d")},
    {"store_id": "STR-010", "name": "Kaapi Bricks JP Nagar",          "city": "Bangalore",     "state": "Karnataka",      "neighborhood": "JP Nagar",          "sq_footage": 360,  "seating_capacity": 10, "opened_date": "2024-06-15"},
    # Other South India (10)
    {"store_id": "STR-011", "name": "Kaapi Bricks Chennai T. Nagar",  "city": "Chennai",       "state": "Tamil Nadu",     "neighborhood": "T. Nagar",          "sq_footage": 400,  "seating_capacity": 12, "opened_date": "2023-03-01"},
    {"store_id": "STR-012", "name": "Kaapi Bricks Chennai Adyar",     "city": "Chennai",       "state": "Tamil Nadu",     "neighborhood": "Adyar",             "sq_footage": 380,  "seating_capacity": 10, "opened_date": "2024-01-15"},
    {"store_id": "STR-013", "name": "Kaapi Bricks Mysuru",            "city": "Mysuru",        "state": "Karnataka",      "neighborhood": "Saraswathipuram",   "sq_footage": 350,  "seating_capacity": 10, "opened_date": "2023-09-01"},
    {"store_id": "STR-014", "name": "Kaapi Bricks Hyderabad Banjara", "city": "Hyderabad",     "state": "Telangana",      "neighborhood": "Banjara Hills",     "sq_footage": 420,  "seating_capacity": 12, "opened_date": "2023-07-01"},
    {"store_id": "STR-015", "name": "Kaapi Bricks Hyderabad Jubilee", "city": "Hyderabad",     "state": "Telangana",      "neighborhood": "Jubilee Hills",     "sq_footage": 400,  "seating_capacity": 12, "opened_date": "2024-03-15"},
    {"store_id": "STR-016", "name": "Kaapi Bricks Coimbatore",        "city": "Coimbatore",    "state": "Tamil Nadu",     "neighborhood": "RS Puram",          "sq_footage": 340,  "seating_capacity": 10, "opened_date": "2024-05-01"},
    {"store_id": "STR-017", "name": "Kaapi Bricks Kochi",             "city": "Kochi",         "state": "Kerala",         "neighborhood": "Fort Kochi",        "sq_footage": 360,  "seating_capacity": 10, "opened_date": "2024-06-01"},
    {"store_id": "STR-018", "name": "Kaapi Bricks Madurai",           "city": "Madurai",       "state": "Tamil Nadu",     "neighborhood": "Anna Nagar",        "sq_footage": 320,  "seating_capacity": 8,  "opened_date": "2024-08-15"},
    {"store_id": "STR-019", "name": "Kaapi Bricks Pondicherry",       "city": "Pondicherry",   "state": "Puducherry",     "neighborhood": "White Town",        "sq_footage": 300,  "seating_capacity": 8,  "opened_date": "2024-09-01"},
    {"store_id": "STR-020", "name": "Kaapi Bricks Vizag",             "city": "Visakhapatnam", "state": "Andhra Pradesh", "neighborhood": "Beach Road",        "sq_footage": 350,  "seating_capacity": 10, "opened_date": "2024-10-01"},
    # Rest of India (10)
    {"store_id": "STR-021", "name": "Kaapi Bricks Mumbai Bandra",     "city": "Mumbai",        "state": "Maharashtra",    "neighborhood": "Bandra West",       "sq_footage": 380,  "seating_capacity": 10, "opened_date": "2023-05-15"},
    {"store_id": "STR-022", "name": "Kaapi Bricks Mumbai Andheri",    "city": "Mumbai",        "state": "Maharashtra",    "neighborhood": "Andheri West",      "sq_footage": 400,  "seating_capacity": 12, "opened_date": "2024-02-15"},
    {"store_id": "STR-023", "name": "Kaapi Bricks Delhi CP",          "city": "New Delhi",     "state": "Delhi",          "neighborhood": "Connaught Place",   "sq_footage": 420,  "seating_capacity": 12, "opened_date": "2023-08-01"},
    {"store_id": "STR-024", "name": "Kaapi Bricks Delhi Hauz Khas",   "city": "New Delhi",     "state": "Delhi",          "neighborhood": "Hauz Khas Village", "sq_footage": 350,  "seating_capacity": 10, "opened_date": "2024-04-01"},
    {"store_id": "STR-025", "name": "Kaapi Bricks Pune",              "city": "Pune",          "state": "Maharashtra",    "neighborhood": "Koregaon Park",     "sq_footage": 380,  "seating_capacity": 10, "opened_date": "2024-01-01"},
    {"store_id": "STR-026", "name": "Kaapi Bricks Kolkata",           "city": "Kolkata",       "state": "West Bengal",    "neighborhood": "Park Street",       "sq_footage": 360,  "seating_capacity": 10, "opened_date": "2024-05-15"},
    {"store_id": "STR-027", "name": "Kaapi Bricks Ahmedabad",         "city": "Ahmedabad",     "state": "Gujarat",        "neighborhood": "SG Highway",        "sq_footage": 400,  "seating_capacity": 12, "opened_date": "2024-07-01"},
    {"store_id": "STR-028", "name": "Kaapi Bricks Jaipur",            "city": "Jaipur",        "state": "Rajasthan",      "neighborhood": "C-Scheme",          "sq_footage": 380,  "seating_capacity": 10, "opened_date": "2024-08-01"},
    {"store_id": "STR-029", "name": "Kaapi Bricks Chandigarh",        "city": "Chandigarh",    "state": "Chandigarh",     "neighborhood": "Sector 17",         "sq_footage": 350,  "seating_capacity": 10, "opened_date": "2024-09-15"},
    {"store_id": "STR-030", "name": "Kaapi Bricks Goa",               "city": "Panaji",        "state": "Goa",            "neighborhood": "Fontainhas",        "sq_footage": 320,  "seating_capacity": 8,  "opened_date": "2024-11-01"},
    # International (7)
    {"store_id": "STR-031", "name": "Kaapi Bricks Dubai",             "city": "Dubai",         "state": "UAE",            "neighborhood": "Downtown Dubai",    "sq_footage": 700,  "seating_capacity": 20, "opened_date": "2024-02-01"},
    {"store_id": "STR-032", "name": "Kaapi Bricks Singapore",         "city": "Singapore",     "state": "Singapore",      "neighborhood": "Little India",      "sq_footage": 600,  "seating_capacity": 16, "opened_date": "2024-04-15"},
    {"store_id": "STR-033", "name": "Kaapi Bricks London",            "city": "London",        "state": "UK",             "neighborhood": "Tooting",           "sq_footage": 650,  "seating_capacity": 16, "opened_date": "2024-06-01"},
    {"store_id": "STR-034", "name": "Kaapi Bricks San Francisco",     "city": "San Francisco", "state": "CA",             "neighborhood": "Mission District",  "sq_footage": 680,  "seating_capacity": 18, "opened_date": "2024-07-15"},
    {"store_id": "STR-035", "name": "Kaapi Bricks Kuala Lumpur",      "city": "Kuala Lumpur",  "state": "Malaysia",       "neighborhood": "Brickfields",       "sq_footage": 620,  "seating_capacity": 14, "opened_date": "2024-08-01"},
    {"store_id": "STR-036", "name": "Kaapi Bricks Sydney",            "city": "Sydney",        "state": "Australia",      "neighborhood": "Harris Park",       "sq_footage": 640,  "seating_capacity": 14, "opened_date": "2024-09-01"},
    {"store_id": "STR-037", "name": "Kaapi Bricks Toronto",           "city": "Toronto",       "state": "Canada",         "neighborhood": "Scarborough",       "sq_footage": 620,  "seating_capacity": 14, "opened_date": "2024-10-15"},
]

stores_pdf = pd.DataFrame(stores_data)
store_ids = stores_pdf["store_id"].tolist()
print(f"  Created {len(stores_pdf)} stores")

# =============================================================================
# 2. PRODUCTS (Drinks Menu)
# =============================================================================
print("Generating products...")

products_data = [
    # Filter Coffee (8)
    {"product_id": "PRD-001", "name": "Classic Filter Coffee",         "category": "Filter Coffee",     "base_price": 60,   "cost": 15, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-002", "name": "Strong Decoction",              "category": "Filter Coffee",     "base_price": 70,   "cost": 18, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-003", "name": "Bella Kaapi (Jaggery)",         "category": "Filter Coffee",     "base_price": 65,   "cost": 16, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-004", "name": "Sukku Kaapi (Dry Ginger)",      "category": "Filter Coffee",     "base_price": 65,   "cost": 17, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-005", "name": "Degree Coffee",                 "category": "Filter Coffee",     "base_price": 60,   "cost": 15, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-006", "name": "Mysore Filter Coffee",          "category": "Filter Coffee",     "base_price": 70,   "cost": 18, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-007", "name": "Kumbakonam Degree Coffee",      "category": "Filter Coffee",     "base_price": 75,   "cost": 20, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-008", "name": "Chicory Blend",                 "category": "Filter Coffee",     "base_price": 55,   "cost": 14, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    # Specialty Coffee (6)
    {"product_id": "PRD-009", "name": "Cold Coffee",                   "category": "Specialty Coffee",  "base_price": 100,  "cost": 28, "is_seasonal": False, "beverage_base": "Espresso"},
    {"product_id": "PRD-010", "name": "Kaapi Frappe",                  "category": "Specialty Coffee",  "base_price": 120,  "cost": 32, "is_seasonal": False, "beverage_base": "Espresso"},
    {"product_id": "PRD-011", "name": "Caramel Kaapi",                 "category": "Specialty Coffee",  "base_price": 130,  "cost": 35, "is_seasonal": False, "beverage_base": "Espresso"},
    {"product_id": "PRD-012", "name": "Hazelnut Kaapi",                "category": "Specialty Coffee",  "base_price": 140,  "cost": 38, "is_seasonal": False, "beverage_base": "Espresso"},
    {"product_id": "PRD-013", "name": "Mocha Kaapi",                   "category": "Specialty Coffee",  "base_price": 150,  "cost": 40, "is_seasonal": False, "beverage_base": "Espresso"},
    {"product_id": "PRD-014", "name": "Espresso Shot",                 "category": "Specialty Coffee",  "base_price": 80,   "cost": 22, "is_seasonal": False, "beverage_base": "Espresso"},
    # Traditional Beverages (8)
    {"product_id": "PRD-015", "name": "Masala Chai",                   "category": "Traditional",       "base_price": 50,   "cost": 12, "is_seasonal": False, "beverage_base": "Tea"},
    {"product_id": "PRD-016", "name": "Irani Chai",                    "category": "Traditional",       "base_price": 55,   "cost": 14, "is_seasonal": False, "beverage_base": "Tea"},
    {"product_id": "PRD-017", "name": "Ginger Tea",                    "category": "Traditional",       "base_price": 45,   "cost": 11, "is_seasonal": False, "beverage_base": "Tea"},
    {"product_id": "PRD-018", "name": "Cardamom Tea",                  "category": "Traditional",       "base_price": 50,   "cost": 13, "is_seasonal": False, "beverage_base": "Tea"},
    {"product_id": "PRD-019", "name": "Rose Milk",                     "category": "Traditional",       "base_price": 60,   "cost": 15, "is_seasonal": False, "beverage_base": "Milk-based"},
    {"product_id": "PRD-020", "name": "Badam Milk",                    "category": "Traditional",       "base_price": 70,   "cost": 20, "is_seasonal": False, "beverage_base": "Milk-based"},
    {"product_id": "PRD-021", "name": "Paneer Soda",                   "category": "Traditional",       "base_price": 40,   "cost": 10, "is_seasonal": False, "beverage_base": "Sherbet"},
    {"product_id": "PRD-022", "name": "Nannari Sherbet",               "category": "Traditional",       "base_price": 45,   "cost": 12, "is_seasonal": False, "beverage_base": "Sherbet"},
    # Seasonal / Special (6)
    {"product_id": "PRD-023", "name": "Mango Lassi",                   "category": "Seasonal",          "base_price": 80,   "cost": 22, "is_seasonal": True,  "beverage_base": "Milk-based"},
    {"product_id": "PRD-024", "name": "Buttermilk (Majjige)",          "category": "Seasonal",          "base_price": 35,   "cost": 8,  "is_seasonal": False, "beverage_base": "Milk-based"},
    {"product_id": "PRD-025", "name": "Filter Coffee Ice Cream Float", "category": "Seasonal",          "base_price": 120,  "cost": 35, "is_seasonal": True,  "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-026", "name": "Pista Kaapi",                   "category": "Seasonal",          "base_price": 110,  "cost": 30, "is_seasonal": False, "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-027", "name": "Jaggery Cold Brew",             "category": "Seasonal",          "base_price": 100,  "cost": 28, "is_seasonal": True,  "beverage_base": "Filter Coffee"},
    {"product_id": "PRD-028", "name": "Monsoon Malabar Pour-Over",     "category": "Seasonal",          "base_price": 90,   "cost": 25, "is_seasonal": True,  "beverage_base": "Filter Coffee"},
]

products_pdf = pd.DataFrame(products_data)
product_ids = products_pdf["product_id"].tolist()

# Popularity weights - Classic Filter Coffee is the top seller
product_popularity = {
    "PRD-001": 0.14, "PRD-002": 0.10, "PRD-003": 0.06, "PRD-004": 0.04, "PRD-005": 0.08,
    "PRD-006": 0.05, "PRD-007": 0.04, "PRD-008": 0.03, "PRD-009": 0.05, "PRD-010": 0.03,
    "PRD-011": 0.03, "PRD-012": 0.02, "PRD-013": 0.02, "PRD-014": 0.02, "PRD-015": 0.09,
    "PRD-016": 0.03, "PRD-017": 0.03, "PRD-018": 0.02, "PRD-019": 0.02, "PRD-020": 0.02,
    "PRD-021": 0.01, "PRD-022": 0.01, "PRD-023": 0.02, "PRD-024": 0.02, "PRD-025": 0.01,
    "PRD-026": 0.01, "PRD-027": 0.01, "PRD-028": 0.01,
}
product_weights = np.array([product_popularity[p] for p in product_ids])
product_weights = (product_weights / product_weights.sum()).tolist()
print(f"  Created {len(products_pdf)} products")

# =============================================================================
# 3. ADD-ONS (Toppings)
# =============================================================================
print("Generating add-ons...")

toppings_data = [
    {"topping_id": "TOP-001", "name": "Extra Decoction Shot",  "price": 20,  "cost": 5,  "is_available": True},
    {"topping_id": "TOP-002", "name": "Jaggery Sweetener",     "price": 15,  "cost": 3,  "is_available": True},
    {"topping_id": "TOP-003", "name": "Chicory Boost",         "price": 15,  "cost": 4,  "is_available": True},
    {"topping_id": "TOP-004", "name": "Cardamom",              "price": 10,  "cost": 2,  "is_available": True},
    {"topping_id": "TOP-005", "name": "Ice Cream Float",       "price": 30,  "cost": 8,  "is_available": True},
    {"topping_id": "TOP-006", "name": "Whipped Cream",         "price": 25,  "cost": 6,  "is_available": True},
    {"topping_id": "TOP-007", "name": "Chocolate Drizzle",     "price": 20,  "cost": 5,  "is_available": True},
    {"topping_id": "TOP-008", "name": "Vanilla Shot",          "price": 20,  "cost": 5,  "is_available": True},
    {"topping_id": "TOP-009", "name": "Hazelnut Shot",         "price": 25,  "cost": 7,  "is_available": True},
    {"topping_id": "TOP-010", "name": "Cinnamon",              "price": 10,  "cost": 2,  "is_available": True},
    {"topping_id": "TOP-011", "name": "Nutmeg",                "price": 10,  "cost": 2,  "is_available": True},
    {"topping_id": "TOP-012", "name": "Palm Jaggery",          "price": 15,  "cost": 4,  "is_available": True},
]

toppings_pdf = pd.DataFrame(toppings_data)
topping_ids = toppings_pdf["topping_id"].tolist()

# Extra decoction shot dominates add-on orders
topping_weights = np.array([0.30, 0.12, 0.08, 0.10, 0.06, 0.05, 0.05, 0.05, 0.04, 0.06, 0.04, 0.05])
topping_weights = (topping_weights / topping_weights.sum()).tolist()
print(f"  Created {len(toppings_pdf)} add-ons")

# =============================================================================
# 4. SUPPLIERS
# =============================================================================
print("Generating suppliers...")

suppliers_data = [
    {"supplier_id": "SUP-001", "name": "Coorg Coffee Estates",        "country": "India (Karnataka)",       "category": "Arabica Beans",         "lead_time_days": 7,  "reliability_score": 4.8},
    {"supplier_id": "SUP-002", "name": "Chikmagalur Plantations",     "country": "India (Karnataka)",       "category": "Robusta & Chicory",     "lead_time_days": 5,  "reliability_score": 4.6},
    {"supplier_id": "SUP-003", "name": "Araku Valley Organics",       "country": "India (Andhra Pradesh)",  "category": "Specialty Blends",      "lead_time_days": 10, "reliability_score": 4.7},
    {"supplier_id": "SUP-004", "name": "Nandini Dairy",               "country": "India (Karnataka)",       "category": "Dairy & Milks",         "lead_time_days": 1,  "reliability_score": 4.9},
    {"supplier_id": "SUP-005", "name": "Kerala Spice Traders",        "country": "India (Kerala)",          "category": "Spices & Flavors",      "lead_time_days": 5,  "reliability_score": 4.5},
    {"supplier_id": "SUP-006", "name": "Mysore Sweet Works",          "country": "India (Karnataka)",       "category": "Syrups & Sweeteners",   "lead_time_days": 3,  "reliability_score": 4.6},
    {"supplier_id": "SUP-007", "name": "Chennai Packaging Co.",       "country": "India (Tamil Nadu)",      "category": "Cups & Packaging",      "lead_time_days": 7,  "reliability_score": 4.4},
    {"supplier_id": "SUP-008", "name": "Organic Alternatives India",  "country": "India (Karnataka)",       "category": "Alt Milks",             "lead_time_days": 3,  "reliability_score": 4.7},
]

suppliers_pdf = pd.DataFrame(suppliers_data)
supplier_ids = suppliers_pdf["supplier_id"].tolist()
print(f"  Created {len(suppliers_pdf)} suppliers")

# =============================================================================
# 5. INGREDIENTS
# =============================================================================
print("Generating ingredients...")

ingredients_data = [
    {"ingredient_id": "ING-001", "name": "Coorg Arabica Beans",       "unit": "kg",    "unit_cost": 1200.00, "supplier_id": "SUP-001", "reorder_threshold": 10.0},
    {"ingredient_id": "ING-002", "name": "Chikmagalur Robusta Beans", "unit": "kg",    "unit_cost": 800.00,  "supplier_id": "SUP-002", "reorder_threshold": 15.0},
    {"ingredient_id": "ING-003", "name": "Araku Valley Blend",        "unit": "kg",    "unit_cost": 1500.00, "supplier_id": "SUP-003", "reorder_threshold": 5.0},
    {"ingredient_id": "ING-004", "name": "Chicory",                   "unit": "kg",    "unit_cost": 400.00,  "supplier_id": "SUP-002", "reorder_threshold": 8.0},
    {"ingredient_id": "ING-005", "name": "Jaggery",                   "unit": "kg",    "unit_cost": 80.00,   "supplier_id": "SUP-006", "reorder_threshold": 20.0},
    {"ingredient_id": "ING-006", "name": "Cardamom",                  "unit": "kg",    "unit_cost": 3000.00, "supplier_id": "SUP-005", "reorder_threshold": 2.0},
    {"ingredient_id": "ING-007", "name": "Dry Ginger (Sukku)",        "unit": "kg",    "unit_cost": 600.00,  "supplier_id": "SUP-005", "reorder_threshold": 3.0},
    {"ingredient_id": "ING-008", "name": "Full Cream Milk",           "unit": "liter", "unit_cost": 55.00,   "supplier_id": "SUP-004", "reorder_threshold": 50.0},
    {"ingredient_id": "ING-009", "name": "Toned Milk",                "unit": "liter", "unit_cost": 45.00,   "supplier_id": "SUP-004", "reorder_threshold": 40.0},
    {"ingredient_id": "ING-010", "name": "Oat Milk",                  "unit": "liter", "unit_cost": 250.00,  "supplier_id": "SUP-008", "reorder_threshold": 20.0},
    {"ingredient_id": "ING-011", "name": "Almond Milk",               "unit": "liter", "unit_cost": 280.00,  "supplier_id": "SUP-008", "reorder_threshold": 15.0},
    {"ingredient_id": "ING-012", "name": "Coconut Milk",              "unit": "liter", "unit_cost": 120.00,  "supplier_id": "SUP-004", "reorder_threshold": 15.0},
    {"ingredient_id": "ING-013", "name": "Rose Syrup",                "unit": "liter", "unit_cost": 200.00,  "supplier_id": "SUP-006", "reorder_threshold": 8.0},
    {"ingredient_id": "ING-014", "name": "Badam Paste",               "unit": "kg",    "unit_cost": 800.00,  "supplier_id": "SUP-006", "reorder_threshold": 5.0},
    {"ingredient_id": "ING-015", "name": "Nannari Syrup",             "unit": "liter", "unit_cost": 350.00,  "supplier_id": "SUP-005", "reorder_threshold": 6.0},
    {"ingredient_id": "ING-016", "name": "Masala Chai Spice Mix",     "unit": "kg",    "unit_cost": 1500.00, "supplier_id": "SUP-005", "reorder_threshold": 3.0},
    {"ingredient_id": "ING-017", "name": "Sugar",                     "unit": "kg",    "unit_cost": 45.00,   "supplier_id": "SUP-006", "reorder_threshold": 25.0},
    {"ingredient_id": "ING-018", "name": "Palm Jaggery",              "unit": "kg",    "unit_cost": 150.00,  "supplier_id": "SUP-006", "reorder_threshold": 10.0},
    {"ingredient_id": "ING-019", "name": "Cocoa Powder",              "unit": "kg",    "unit_cost": 500.00,  "supplier_id": "SUP-003", "reorder_threshold": 4.0},
    {"ingredient_id": "ING-020", "name": "Vanilla Extract",           "unit": "liter", "unit_cost": 2000.00, "supplier_id": "SUP-005", "reorder_threshold": 2.0},
    {"ingredient_id": "ING-021", "name": "Paper Cups (200ml)",        "unit": "case",  "unit_cost": 800.00,  "supplier_id": "SUP-007", "reorder_threshold": 5.0},
    {"ingredient_id": "ING-022", "name": "Stirrer Sticks",            "unit": "case",  "unit_cost": 300.00,  "supplier_id": "SUP-007", "reorder_threshold": 5.0},
]

ingredients_pdf = pd.DataFrame(ingredients_data)
ingredient_ids = ingredients_pdf["ingredient_id"].tolist()
print(f"  Created {len(ingredients_pdf)} ingredients")

# =============================================================================
# 6. PROMOTIONS
# =============================================================================
print("Generating promotions...")

promotions_data = [
    {"promotion_id": "PRM-001", "name": "Grand Opening - Electronic City",  "type": "BOGO",           "discount_pct": 50.0, "min_order": 0,    "start_date": NEW_STORE_OPEN.strftime("%Y-%m-%d"),                          "end_date": (NEW_STORE_OPEN + timedelta(days=14)).strftime("%Y-%m-%d"), "store_id": "STR-009"},
    {"promotion_id": "PRM-002", "name": "Monsoon Kaapi Special",            "type": "DISCOUNT",        "discount_pct": 15.0, "min_order": 0,    "start_date": MONSOON_PROMO_START.strftime("%Y-%m-%d"),                     "end_date": MONSOON_PROMO_END.strftime("%Y-%m-%d"),                     "store_id": None},
    {"promotion_id": "PRM-003", "name": "Morning Rush Hour (7-9am)",        "type": "HAPPY_HOUR",      "discount_pct": 20.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-004", "name": "Loyalty Double Points",            "type": "LOYALTY",         "discount_pct": 0.0,  "min_order": 200,  "start_date": (START_DATE + timedelta(days=30)).strftime("%Y-%m-%d"),      "end_date": (START_DATE + timedelta(days=44)).strftime("%Y-%m-%d"),    "store_id": None},
    {"promotion_id": "PRM-005", "name": "Free Add-on Friday",               "type": "FREE_ITEM",       "discount_pct": 0.0,  "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-006", "name": "Student Discount",                 "type": "DISCOUNT",        "discount_pct": 10.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-007", "name": "Birthday Month Special",           "type": "BIRTHDAY",        "discount_pct": 25.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-008", "name": "Referral Reward",                  "type": "REFERRAL",        "discount_pct": 15.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-009", "name": "New Member Welcome",               "type": "DISCOUNT",        "discount_pct": 20.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-010", "name": "Sankranti Special",                "type": "SEASONAL",        "discount_pct": 10.0, "min_order": 0,    "start_date": (END_DATE - timedelta(days=60)).strftime("%Y-%m-%d"),        "end_date": (END_DATE - timedelta(days=30)).strftime("%Y-%m-%d"),      "store_id": None},
    {"promotion_id": "PRM-011", "name": "Filter Coffee Monday",             "type": "DAY_OF_WEEK",     "discount_pct": 15.0, "min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-012", "name": "Buy 5 Get 1 Free",                 "type": "LOYALTY_PUNCH",   "discount_pct": 100.0,"min_order": 0,    "start_date": START_DATE.strftime("%Y-%m-%d"),                              "end_date": END_DATE.strftime("%Y-%m-%d"),                              "store_id": None},
    {"promotion_id": "PRM-013", "name": "Oat Milk Upgrade Free",            "type": "FREE_UPGRADE",    "discount_pct": 0.0,  "min_order": 0,    "start_date": (START_DATE + timedelta(days=60)).strftime("%Y-%m-%d"),      "end_date": (START_DATE + timedelta(days=74)).strftime("%Y-%m-%d"),    "store_id": None},
    {"promotion_id": "PRM-014", "name": "Diwali Special",                   "type": "HOLIDAY",         "discount_pct": 15.0, "min_order": 300,  "start_date": (START_DATE + timedelta(days=45)).strftime("%Y-%m-%d"),      "end_date": (START_DATE + timedelta(days=47)).strftime("%Y-%m-%d"),    "store_id": None},
    {"promotion_id": "PRM-015", "name": "App Launch Promo",                 "type": "APP_EXCLUSIVE",   "discount_pct": 25.0, "min_order": 0,    "start_date": (START_DATE + timedelta(days=10)).strftime("%Y-%m-%d"),      "end_date": (START_DATE + timedelta(days=24)).strftime("%Y-%m-%d"),    "store_id": None},
]

promotions_pdf = pd.DataFrame(promotions_data)
promotion_ids = promotions_pdf["promotion_id"].tolist()
print(f"  Created {len(promotions_pdf)} promotions")

# =============================================================================
# 7. CUSTOMERS
# =============================================================================
print("Generating customers...")

loyalty_tiers = np.random.choice(["Bronze", "Silver", "Gold", "Platinum Tumbler"], N_CUSTOMERS, p=[0.55, 0.28, 0.12, 0.05])
preferred_milk = np.random.choice(["Full Cream Milk", "Toned Milk", "Oat Milk", "Almond Milk", "Coconut Milk"], N_CUSTOMERS, p=[0.50, 0.25, 0.12, 0.08, 0.05])
# Weight home_store by store age (older stores have more established customer bases)
_store_age_days = [(END_DATE - datetime.strptime(s["opened_date"], "%Y-%m-%d")).days for s in stores_data]
_home_store_weights = np.array([max(d, 30) for d in _store_age_days], dtype=float)
_home_store_weights /= _home_store_weights.sum()
home_store = np.random.choice(store_ids, N_CUSTOMERS, p=_home_store_weights)

# Loyalty points correlate with tier
tier_points_map = {"Bronze": (50, 200), "Silver": (200, 800), "Gold": (800, 2500), "Platinum Tumbler": (2500, 8000)}
loyalty_points = [int(np.random.uniform(*tier_points_map[t])) for t in loyalty_tiers]

customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "first_name": [fake.first_name() for _ in range(N_CUSTOMERS)],
    "last_name": [fake.last_name() for _ in range(N_CUSTOMERS)],
    "email": [fake.email() for _ in range(N_CUSTOMERS)],
    "loyalty_tier": loyalty_tiers,
    "loyalty_points": loyalty_points,
    "preferred_milk": preferred_milk,
    "home_store_id": home_store,
    "joined_date": [fake.date_between(start_date="-3y", end_date=START_DATE) for _ in range(N_CUSTOMERS)],
    "birth_month": np.random.randint(1, 13, N_CUSTOMERS),
    "is_student": np.random.choice([True, False], N_CUSTOMERS, p=[0.22, 0.78]),
    "app_user": np.random.choice([True, False], N_CUSTOMERS, p=[0.60, 0.40]),
})

# Convert date objects to strings for clean Parquet serialization
customers_pdf["joined_date"] = customers_pdf["joined_date"].astype(str)

customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["loyalty_tier"]))
customer_store_map = dict(zip(customers_pdf["customer_id"], customers_pdf["home_store_id"]))

# Higher tier customers order more frequently
tier_visit_weight = customers_pdf["loyalty_tier"].map({"Platinum Tumbler": 6.0, "Gold": 3.5, "Silver": 2.0, "Bronze": 1.0})
customer_weights = (tier_visit_weight / tier_visit_weight.sum()).tolist()

print(f"  Created {len(customers_pdf):,} customers")

# =============================================================================
# 8. ORDERS + ORDER ITEMS + ORDER ITEM TOPPINGS
# =============================================================================
print("Generating orders, order_items, order_item_toppings...")

sizes = ["Small (Tumbler)", "Regular", "Large"]
size_weights = [0.20, 0.55, 0.25]
size_price_add = {"Small (Tumbler)": -15, "Regular": 0, "Large": 20}

sweetness_levels = ["No Sugar", "Less Sugar", "Regular", "Extra Sweet"]
sweetness_weights = [0.10, 0.25, 0.45, 0.20]

temperature_levels = ["Hot", "Warm", "Cold"]
temperature_weights = [0.50, 0.20, 0.30]

milk_alts = ["Full Cream Milk", "Toned Milk", "Oat Milk", "Almond Milk", "Coconut Milk"]
milk_weights = [0.50, 0.25, 0.12, 0.08, 0.05]
milk_upcharge = {"Full Cream Milk": 0, "Toned Milk": 0, "Oat Milk": 30, "Almond Milk": 30, "Coconut Milk": 20}

channels = ["In-Store", "Mobile App", "Online"]
channel_weights = [0.55, 0.35, 0.10]

# Build a lookup from store_id -> opened_date for new-store logic
_store_opened = {s["store_id"]: datetime.strptime(s["opened_date"], "%Y-%m-%d") for s in stores_data}


# Volume multiplier per day
def get_daily_multiplier(date, store_id):
    meta = STORE_META[store_id]
    m = 1.0

    # Weekend boost for coffee shops
    if date.weekday() >= 5:
        m *= 1.35

    # Holiday drop - use country-specific holidays
    holiday_key = meta["holiday_key"]
    country_hols = COUNTRY_HOLIDAYS.get(holiday_key)
    if country_hols and date in country_hols:
        m *= 0.50

    # Seasonal adjustment (hemisphere-aware)
    month = date.month
    if meta["hemisphere"] == "S":
        # Southern hemisphere: warm months are Dec-Feb, cool months are Jun-Aug
        if month in [12, 1, 2]:
            m *= 1.20
        elif month in [6, 7, 8]:
            m *= 0.85
    else:
        # Northern hemisphere: warm months are Jun-Aug, cool months are Dec-Feb
        if month in [6, 7, 8]:
            m *= 1.20
        elif month in [12, 1, 2]:
            m *= 0.85

    # New store opening spike - works for any store that opened within the data window
    opened = _store_opened[store_id]
    days_open = (date - opened).days
    if days_open < 0:
        return 0.0
    elif days_open < 14:
        m *= 2.5
    elif days_open < 30:
        m *= 1.5

    # Monsoon promo lift
    if MONSOON_PROMO_START <= date <= MONSOON_PROMO_END:
        m *= 1.15

    return max(0.1, m * np.random.normal(1, 0.12))

orders_data = []
order_items_data = []
order_item_toppings_data = []

order_idx = 0
item_idx = 0
topping_idx = 0

# Generate orders distributed across dates and stores
# Derive base volume from store age: flagships (2+ yr) get 45-60, newer get less
store_base_volume = {}
for s in stores_data:
    opened = datetime.strptime(s["opened_date"], "%Y-%m-%d")
    age_days = (END_DATE - opened).days
    if age_days > 730:        # 2+ years: flagship
        base = int(45 + (age_days - 730) / 365 * 10)
        base = min(base, 60)
    elif age_days > 365:      # 1-2 years: established
        base = int(30 + (age_days - 365) / 365 * 15)
    elif age_days > 180:      # 6-12 months: growing
        base = int(20 + (age_days - 180) / 185 * 10)
    elif age_days > 60:       # 2-6 months: ramping
        base = int(12 + (age_days - 60) / 120 * 8)
    else:                      # <2 months: new
        base = 10
    store_base_volume[s["store_id"]] = base

for day in pd.date_range(START_DATE, END_DATE):
    day_dt = day.to_pydatetime()
    day_str = day.strftime("%Y-%m-%d")
    is_weekend = day_dt.weekday() >= 5

    for store_id in store_ids:
        base = store_base_volume[store_id]
        multiplier = get_daily_multiplier(day_dt, store_id)
        n_orders_today = int(base * multiplier)

        for _ in range(n_orders_today):
            if order_idx >= N_ORDERS:
                break

            cid = np.random.choice(customer_ids, p=customer_weights)
            tier = customer_tier_map[cid]
            channel = np.random.choice(channels, p=channel_weights)

            # Order time - peaks at morning and after work
            # Hours 0-5 are low traffic, 6-9 morning rush, 10-16 steady, 17-20 evening
            hour_probs = [0.01]*6 + [0.06, 0.10, 0.12, 0.08, 0.05, 0.06, 0.05, 0.04, 0.04, 0.05, 0.06, 0.08, 0.06, 0.04, 0.02, 0.01, 0.01, 0.01]
            hour_probs = [p/sum(hour_probs) for p in hour_probs]
            hour = np.random.choice(range(24), p=hour_probs)
            minute = np.random.randint(0, 60)
            order_time = f"{hour:02d}:{minute:02d}"

            # Number of items in order
            n_items = np.random.choice([1, 2, 3, 4], p=[0.55, 0.30, 0.12, 0.03])

            order_subtotal = 0.0
            order_item_ids = []

            for j in range(n_items):
                product_id = np.random.choice(product_ids, p=product_weights)
                product = products_pdf[products_pdf["product_id"] == product_id].iloc[0]

                size = np.random.choice(sizes, p=size_weights)
                sweetness = np.random.choice(sweetness_levels, p=sweetness_weights)
                temperature = np.random.choice(temperature_levels, p=temperature_weights)
                milk = np.random.choice(milk_alts, p=milk_weights)

                item_price = round(product["base_price"] + size_price_add[size] + milk_upcharge[milk], 2)
                order_subtotal += item_price

                item_id = f"ITM-{item_idx:07d}"
                order_item_ids.append(item_id)

                order_items_data.append({
                    "order_item_id": item_id,
                    "order_id": f"ORD-{order_idx:07d}",
                    "product_id": product_id,
                    "size": size,
                    "sweetness_level": sweetness,
                    "temperature": temperature,
                    "milk_type": milk,
                    "item_price": item_price,
                })
                item_idx += 1

                # Add-ons - ~55% chance of at least one add-on
                n_toppings = np.random.choice([0, 1, 2, 3], p=[0.45, 0.35, 0.15, 0.05])
                selected_toppings = np.random.choice(topping_ids, size=min(n_toppings, len(topping_ids)), replace=False, p=topping_weights) if n_toppings > 0 else []

                for top_id in selected_toppings:
                    top_price = toppings_pdf[toppings_pdf["topping_id"] == top_id]["price"].values[0]
                    order_subtotal += top_price
                    order_item_toppings_data.append({
                        "order_item_topping_id": f"OIT-{topping_idx:07d}",
                        "order_item_id": item_id,
                        "topping_id": top_id,
                        "price": top_price,
                    })
                    topping_idx += 1

            # Apply promotion discount
            promo_id = None
            discount = 0.0
            active_promos = [
                p for p in promotions_data
                if p["start_date"] <= day_str <= p["end_date"]
                and (p["store_id"] is None or p["store_id"] == store_id)
                and order_subtotal >= p["min_order"]
            ]
            if active_promos and np.random.random() < 0.18:
                promo = np.random.choice(active_promos)
                promo_id = promo["promotion_id"]
                if promo["discount_pct"] > 0:
                    discount = round(order_subtotal * promo["discount_pct"] / 100, 2)

            order_total = round(max(0, order_subtotal - discount), 2)
            tax = round(order_total * STORE_META[store_id]["tax_rate"], 2)

            orders_data.append({
                "order_id": f"ORD-{order_idx:07d}",
                "customer_id": cid,
                "store_id": store_id,
                "order_date": day_str,
                "order_time": order_time,
                "channel": channel,
                "subtotal": round(order_subtotal, 2),
                "discount": discount,
                "order_total": order_total,
                "tax": tax,
                "promotion_id": promo_id,
                "status": np.random.choice(["completed", "completed", "completed", "refunded"], p=[0.97, 0.01, 0.01, 0.01]),
            })
            order_idx += 1

        if order_idx >= N_ORDERS:
            break
    if order_idx >= N_ORDERS:
        break

orders_pdf = pd.DataFrame(orders_data)
order_items_pdf = pd.DataFrame(order_items_data)
order_item_toppings_pdf = pd.DataFrame(order_item_toppings_data)

print(f"  Created {len(orders_pdf):,} orders")
print(f"  Created {len(order_items_pdf):,} order items")
print(f"  Created {len(order_item_toppings_pdf):,} order item toppings")

# =============================================================================
# 9. PURCHASE ORDERS (Supplier Orders)
# =============================================================================
print("Generating purchase orders...")

po_data = []
for i in range(2000):
    supplier_id = np.random.choice(supplier_ids)
    supplier = suppliers_pdf[suppliers_pdf["supplier_id"] == supplier_id].iloc[0]
    store_id = np.random.choice(store_ids)
    order_date = fake.date_between(start_date=START_DATE, end_date=END_DATE)
    lead_time = int(supplier["lead_time_days"] * np.random.normal(1, 0.15))
    delivery_date = order_date + timedelta(days=max(1, lead_time))
    amount = round(np.random.lognormal(8.5, 0.6), 2)  # INR amounts (~5000-10000)

    po_data.append({
        "po_id": f"PO-{i:05d}",
        "supplier_id": supplier_id,
        "store_id": store_id,
        "order_date": order_date.strftime("%Y-%m-%d"),
        "expected_delivery_date": delivery_date.strftime("%Y-%m-%d"),
        "actual_delivery_date": (delivery_date + timedelta(days=int(np.random.choice([0, 0, 0, 1, 2, -1], p=[0.55, 0.15, 0.10, 0.10, 0.05, 0.05])))).strftime("%Y-%m-%d"),
        "total_amount": amount,
        "status": np.random.choice(["delivered", "delivered", "delivered", "pending", "cancelled"], p=[0.82, 0.05, 0.05, 0.07, 0.01]),
    })

purchase_orders_pdf = pd.DataFrame(po_data)
print(f"  Created {len(purchase_orders_pdf):,} purchase orders")

# =============================================================================
# 10. INVENTORY TRANSACTIONS (realistic: initial stock + daily usage + weekly restocking)
# =============================================================================
print("Generating inventory transactions...")

# Daily usage rates per ingredient (kg or liters per day per store, based on ~64 orders/day avg)
INGREDIENT_DAILY_USAGE = {
    "ING-001": 3.0,   # Coorg Arabica Beans — ~3kg/day for filter coffee
    "ING-002": 4.0,   # Chikmagalur Robusta — most used bean
    "ING-003": 1.5,   # Araku Valley Blend
    "ING-004": 1.5,   # Chicory — blended with robusta
    "ING-005": 1.0,   # Jaggery
    "ING-006": 0.15,  # Cardamom — small amounts
    "ING-007": 0.2,   # Dry Ginger
    "ING-008": 25.0,  # Full Cream Milk — highest volume (liters)
    "ING-009": 10.0,  # Toned Milk
    "ING-010": 3.0,   # Oat Milk
    "ING-011": 2.5,   # Almond Milk
    "ING-012": 2.0,   # Coconut Milk
    "ING-013": 0.5,   # Rose Syrup
    "ING-014": 0.3,   # Badam Paste
    "ING-015": 0.3,   # Nannari Syrup
    "ING-016": 0.5,   # Masala Chai Spice Mix
    "ING-017": 5.0,   # Sugar — heavy usage
    "ING-018": 0.5,   # Palm Jaggery
    "ING-019": 0.2,   # Cocoa Powder
    "ING-020": 0.05,  # Vanilla Extract
    "ING-021": 2.0,   # Paper Cups (cases)
    "ING-022": 1.0,   # Stirrer Sticks (cases)
}

# Initial stock = ~14 days of supply (comfortable buffer)
INITIAL_STOCK_DAYS = 14
# Restock every 7 days with ~10 days of supply
RESTOCK_INTERVAL_DAYS = 7
RESTOCK_DAYS_SUPPLY = 10

inv_data = []
txn_id = 0

for store_id in store_ids:
    # Store-level volume multiplier (some stores busier than others)
    store_volume = np.random.uniform(0.6, 1.4)

    for ingredient_id in ingredient_ids:
        base_daily_usage = INGREDIENT_DAILY_USAGE.get(ingredient_id, 1.0) * store_volume
        unit_cost = ingredients_pdf[ingredients_pdf["ingredient_id"] == ingredient_id]["unit_cost"].values[0]

        # 1. Initial stock on START_DATE
        initial_qty = round(base_daily_usage * INITIAL_STOCK_DAYS * np.random.uniform(0.9, 1.1), 2)
        inv_data.append({
            "transaction_id": f"INV-{txn_id:06d}",
            "store_id": store_id, "ingredient_id": ingredient_id,
            "transaction_date": START_DATE.strftime("%Y-%m-%d"),
            "transaction_type": "purchase", "quantity": initial_qty, "unit_cost": unit_cost,
        })
        txn_id += 1

        current_stock = initial_qty
        current_date = START_DATE

        while current_date <= END_DATE:
            # Daily usage (with some randomness)
            day_of_week = current_date.weekday()
            weekend_mult = 1.3 if day_of_week >= 5 else 1.0
            daily_usage = round(base_daily_usage * weekend_mult * np.random.uniform(0.7, 1.3), 2)

            inv_data.append({
                "transaction_id": f"INV-{txn_id:06d}",
                "store_id": store_id, "ingredient_id": ingredient_id,
                "transaction_date": current_date.strftime("%Y-%m-%d"),
                "transaction_type": "usage", "quantity": -daily_usage, "unit_cost": unit_cost,
            })
            txn_id += 1
            current_stock -= daily_usage

            # Occasional waste (~3% chance per day)
            if np.random.random() < 0.03:
                waste = round(base_daily_usage * np.random.uniform(0.1, 0.5), 2)
                inv_data.append({
                    "transaction_id": f"INV-{txn_id:06d}",
                    "store_id": store_id, "ingredient_id": ingredient_id,
                    "transaction_date": current_date.strftime("%Y-%m-%d"),
                    "transaction_type": "waste", "quantity": -waste, "unit_cost": unit_cost,
                })
                txn_id += 1
                current_stock -= waste

            # Weekly restock (every RESTOCK_INTERVAL_DAYS or when stock gets low)
            days_elapsed = (current_date - START_DATE).days
            needs_restock = (days_elapsed > 0 and days_elapsed % RESTOCK_INTERVAL_DAYS == 0) or current_stock < base_daily_usage * 2
            if needs_restock and current_date < END_DATE:
                restock_qty = round(base_daily_usage * RESTOCK_DAYS_SUPPLY * np.random.uniform(0.85, 1.15), 2)
                # Simulate occasional delayed delivery (~10% chance)
                if np.random.random() < 0.9:
                    inv_data.append({
                        "transaction_id": f"INV-{txn_id:06d}",
                        "store_id": store_id, "ingredient_id": ingredient_id,
                        "transaction_date": current_date.strftime("%Y-%m-%d"),
                        "transaction_type": "purchase", "quantity": restock_qty, "unit_cost": unit_cost,
                    })
                    txn_id += 1
                    current_stock += restock_qty

            current_date += timedelta(days=1)

inventory_transactions_pdf = pd.DataFrame(inv_data)
print(f"  Created {len(inventory_transactions_pdf):,} inventory transactions")

# =============================================================================
# 11. PROMOTION REDEMPTIONS
# =============================================================================
print("Generating promotion redemptions...")

# Extract orders that had a promotion applied
promo_orders = orders_pdf[orders_pdf["promotion_id"].notna()][["order_id", "customer_id", "store_id", "order_date", "promotion_id", "discount"]]

redemptions_data = []
for i, row in enumerate(promo_orders.itertuples()):
    redemptions_data.append({
        "redemption_id": f"RDM-{i:06d}",
        "promotion_id": row.promotion_id,
        "order_id": row.order_id,
        "customer_id": row.customer_id,
        "store_id": row.store_id,
        "redemption_date": row.order_date,
        "discount_applied": row.discount,
    })

promotion_redemptions_pdf = pd.DataFrame(redemptions_data)
print(f"  Created {len(promotion_redemptions_pdf):,} promotion redemptions")

# =============================================================================
# 12. INFERENCE LOGS (empty table for observability)
# =============================================================================
print("Creating inference_logs table schema...")

inference_logs_pdf = pd.DataFrame({
    "trace_id": pd.Series(dtype="str"),
    "request_id": pd.Series(dtype="str"),
    "timestamp": pd.Series(dtype="str"),
    "conversation_id": pd.Series(dtype="str"),
    "store_location": pd.Series(dtype="str"),
    "query": pd.Series(dtype="str"),
    "response_summary": pd.Series(dtype="str"),
    "latency_ms": pd.Series(dtype="float"),
    "agent_name": pd.Series(dtype="str"),
    "endpoint_name": pd.Series(dtype="str"),
    "input_tokens": pd.Series(dtype="int"),
    "output_tokens": pd.Series(dtype="int"),
    "error": pd.Series(dtype="str"),
})

# =============================================================================
# 13. UPLOAD & CREATE DELTA TABLES
# =============================================================================
print(f"\nLanding raw Parquet into the Volume (tables are built by the Lakeflow pipeline)...")

tables = {
    "stores": stores_pdf,
    "products": products_pdf,
    "toppings": toppings_pdf,
    "ingredients": ingredients_pdf,
    "suppliers": suppliers_pdf,
    "promotions": promotions_pdf,
    "customers": customers_pdf,
    "orders": orders_pdf,
    "order_items": order_items_pdf,
    "order_item_toppings": order_item_toppings_pdf,
    "purchase_orders": purchase_orders_pdf,
    "inventory_transactions": inventory_transactions_pdf,
    "promotion_redemptions": promotion_redemptions_pdf,
}

for table_name, df in tables.items():
    land_raw_files(table_name, df)
    print(f"  Landed {table_name}: {len(df):,} rows")

# Create inference_logs table via SQL (empty schema)
run_sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.inference_logs (
    trace_id STRING,
    request_id STRING,
    timestamp TIMESTAMP,
    conversation_id STRING,
    store_location STRING,
    query STRING,
    response_summary STRING,
    latency_ms DOUBLE,
    agent_name STRING,
    endpoint_name STRING,
    input_tokens INT,
    output_tokens INT,
    error STRING
)
""")
print(f"  Created table {CATALOG}.{SCHEMA}.inference_logs (empty)")

# =============================================================================
# 14. VALIDATION SUMMARY
# =============================================================================
print("\n=== VALIDATION SUMMARY ===")
print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print(f"Total orders: {len(orders_pdf):,}")
print(f"Total revenue: \u20b9{orders_pdf['order_total'].sum():,.2f}")
print(f"Avg order value: \u20b9{orders_pdf['order_total'].mean():.2f}")
print(f"Orders by channel:\n{orders_pdf['channel'].value_counts().to_string()}")
print(f"Orders by store:\n{orders_pdf['store_id'].value_counts().to_string()}")
print(f"Loyalty tier distribution:\n{customers_pdf['loyalty_tier'].value_counts().to_string()}")
promo_rate = orders_pdf["promotion_id"].notna().mean() * 100
print(f"Promotion redemption rate: {promo_rate:.1f}%")

# Remote verification — confirm raw files landed (Delta tables are built by the Lakeflow pipeline)
print("\n=== REMOTE VERIFICATION (raw landing zone) ===")
for table_name in tables.keys():
    resp = run_sql(
        f"SELECT COUNT(*) AS cnt FROM read_files("
        f"'/Volumes/{CATALOG}/{SCHEMA}/raw_data/{table_name}/', format => 'parquet')"
    )
    count = resp.result.data_array[0][0] if resp.result and resp.result.data_array else "?"
    print(f"  raw_data/{table_name}: {count} rows landed")
print("\nNext: run the Lakeflow pipeline to build bronze -> silver -> gold:")
print("  databricks bundle deploy -t dev --profile DEFAULT")
print("  databricks bundle run kaapi_bricks_medallion -t dev --profile DEFAULT")
