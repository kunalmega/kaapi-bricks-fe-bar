# Databricks notebook source
# Creates KA, Genie Space, and MAS Supervisor for Kaapi Bricks demo
# Run this AFTER generate_data and generate_ka_documents have completed

# MAGIC %pip install databricks-sdk>=0.38.0
# MAGIC %restart_python

CATALOG = "fe_india_gcc_catalog"
SCHEMA = "kaapi_bricks"
WAREHOUSE_ID = "13a6b534c35ffbcb"

from databricks.sdk import WorkspaceClient
import json, time

w = WorkspaceClient()
host = w.config.host.rstrip("/")
headers = w.config.authenticate()
headers["Content-Type"] = "application/json"

import requests

# ============================================================
# 1. Create Genie Space
# ============================================================
print("Creating Genie Space...")

tables = [
    f"{CATALOG}.{SCHEMA}.stores",
    f"{CATALOG}.{SCHEMA}.products",
    f"{CATALOG}.{SCHEMA}.orders",
    f"{CATALOG}.{SCHEMA}.order_items",
    f"{CATALOG}.{SCHEMA}.customers",
    f"{CATALOG}.{SCHEMA}.ingredients",
    f"{CATALOG}.{SCHEMA}.suppliers",
    f"{CATALOG}.{SCHEMA}.promotions",
    f"{CATALOG}.{SCHEMA}.inventory_transactions",
    f"{CATALOG}.{SCHEMA}.purchase_orders",
    f"{CATALOG}.{SCHEMA}.toppings",
    f"{CATALOG}.{SCHEMA}.order_item_toppings",
    f"{CATALOG}.{SCHEMA}.promotion_redemptions",
    f"{CATALOG}.{SCHEMA}.po_line_items",
]

genie_payload = {
    "display_name": "Kaapi Bricks Analytics",
    "description": "Sales analytics for Kaapi Bricks coffee chain — 37 stores, 28 products, 200K+ orders. Ask about sales, revenue, inventory, customers, promotions.",
    "warehouse_id": WAREHOUSE_ID,
    "table_identifiers": tables,
    "sample_questions": [
        "What are the top 5 selling drinks this month?",
        "Show me revenue for the Koramangala store",
        "Which ingredients are running low in inventory?",
        "How did the Morning Rush Hour promotion perform?",
        "Compare sales between Koramangala and Indiranagar",
    ],
}

# Create Genie via the API
resp = requests.post(f"{host}/api/2.0/genie/spaces", headers=headers, json=genie_payload)
if resp.status_code == 200:
    genie_data = resp.json()
    genie_space_id = genie_data.get("space_id", genie_data.get("id", ""))
    print(f"  Genie Space created: {genie_space_id}")
else:
    print(f"  Genie creation failed: {resp.status_code} — {resp.text[:200]}")
    print("  Trying alternative format...")
    # Try with serialized_space format
    genie_payload2 = {
        "serialized_space": json.dumps({
            "display_name": "Kaapi Bricks Analytics",
            "description": "Sales analytics for Kaapi Bricks",
            "warehouse_id": WAREHOUSE_ID,
            "table_identifiers": tables,
        })
    }
    resp2 = requests.post(f"{host}/api/2.0/genie/spaces", headers=headers, json=genie_payload2)
    if resp2.status_code == 200:
        genie_data = resp2.json()
        genie_space_id = genie_data.get("space_id", genie_data.get("id", ""))
        print(f"  Genie Space created (v2): {genie_space_id}")
    else:
        genie_space_id = "MANUAL_CREATION_NEEDED"
        print(f"  Still failed: {resp2.status_code} — {resp2.text[:200]}")
        print("  Please create Genie Space manually in the UI.")

# ============================================================
# 2. Create Knowledge Assistant
# ============================================================
print("\nCreating Knowledge Assistant...")

ka_volume = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data/ka_documents"

# KA uses the AI Bricks API — try different endpoints
ka_payload = {
    "name": "Kaapi Bricks Operations Knowledge",
    "description": "Answers questions about Kaapi Bricks recipes, barista training, food safety, equipment maintenance, franchise operations, and supplier agreements.",
    "instructions": "Be helpful and always cite the specific document when answering. Use INR for all prices. If unsure, say so.",
    "volume_path": ka_volume,
}

# Try the tile creation API
for api_path in ["/api/2.0/ai/bricks/ka/tiles", "/api/2.0/agent-bricks/ka", "/api/2.0/serving-endpoints"]:
    resp = requests.post(f"{host}{api_path}", headers=headers, json=ka_payload)
    if resp.status_code == 200:
        ka_data = resp.json()
        ka_tile_id = ka_data.get("tile_id", ka_data.get("id", ""))
        ka_endpoint = ka_data.get("endpoint_name", "")
        print(f"  KA created via {api_path}: tile={ka_tile_id} endpoint={ka_endpoint}")
        break
else:
    ka_tile_id = "MANUAL_CREATION_NEEDED"
    ka_endpoint = "MANUAL_CREATION_NEEDED"
    print(f"  KA API not available. Please create KA manually in Agent Bricks UI.")
    print(f"  Volume: {ka_volume}")

# ============================================================
# 3. Create MAS Supervisor
# ============================================================
print("\nCreating MAS Supervisor...")

if ka_tile_id != "MANUAL_CREATION_NEEDED" and genie_space_id != "MANUAL_CREATION_NEEDED":
    mas_payload = {
        "name": "Kaapi Bricks HQ",
        "description": "Routes store queries to specialized agents: document knowledge, data analytics, and operational planning",
        "instructions": "Route recipes/policies/training to knowledge_assistant. Route sales/inventory/revenue to analytics. Route planning/weather/staffing to operations_advisor.",
        "agents": [
            {
                "name": "knowledge_assistant",
                "ka_tile_id": ka_tile_id,
                "description": "Answers questions about recipes, barista training, food safety policies, equipment maintenance, franchise operations, and supplier agreements from Kaapi Bricks internal documents"
            },
            {
                "name": "analytics",
                "genie_space_id": genie_space_id,
                "description": "Answers data questions about sales, revenue, inventory, customers, orders, promotions, and suppliers using SQL on 14 Delta tables. All financial data in INR."
            },
        ],
    }

    for api_path in ["/api/2.0/ai/bricks/mas/tiles", "/api/2.0/agent-bricks/mas"]:
        resp = requests.post(f"{host}{api_path}", headers=headers, json=mas_payload)
        if resp.status_code == 200:
            mas_data = resp.json()
            mas_endpoint = mas_data.get("endpoint_name", "")
            print(f"  MAS created: endpoint={mas_endpoint}")
            break
    else:
        mas_endpoint = "MANUAL_CREATION_NEEDED"
        print(f"  MAS API not available. Please create MAS manually in Agent Bricks UI.")
else:
    mas_endpoint = "MANUAL_CREATION_NEEDED"
    print("  Skipping MAS — KA or Genie not created via API.")

# ============================================================
# 4. Print Summary
# ============================================================
print(f"""
╔═══════════════════════════════════════════════════════╗
║              AGENT CREATION SUMMARY                   ║
╠═══════════════════════════════════════════════════════╣
║  Genie Space ID: {genie_space_id:<35} ║
║  KA Tile ID:     {ka_tile_id:<35} ║
║  KA Endpoint:    {ka_endpoint:<35} ║
║  MAS Endpoint:   {mas_endpoint:<35} ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  If any show MANUAL_CREATION_NEEDED, create them      ║
║  in the Databricks UI (Agent Bricks / SQL).           ║
║                                                       ║
║  Then update the main app resources:                  ║
║  databricks apps update kaapi-bricks-finale \\         ║
║    --profile fevm-india-gcc --json '{{                 ║
║      "resources": [                                   ║
║        {{"name":"mas-endpoint","serving_endpoint":     ║
║          {{"name":"{mas_endpoint}",                    ║
║           "permission":"CAN_QUERY"}}}},...             ║
║      ]                                                ║
║    }}'                                                ║
╚═══════════════════════════════════════════════════════╝
""")
