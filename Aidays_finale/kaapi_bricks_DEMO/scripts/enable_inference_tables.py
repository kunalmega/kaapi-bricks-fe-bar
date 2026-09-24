"""Enable inference tables (AI Gateway payload logging) on Agent Bricks endpoints.

This captures full request/response payloads in Delta tables, which is the only
way to get token usage data from MAS/KA endpoints (they don't expose usage in
the API response or system.serving tables).

Usage:
    python enable_inference_tables.py
"""

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"

endpoints = [
    ("mas-3c936239-endpoint", "mas_payload"),
    ("ka-06ac94eb-endpoint", "ka_payload"),
]

for ep_name, prefix in endpoints:
    print(f"Enabling inference tables on {ep_name}...")
    try:
        w.serving_endpoints.put_ai_gateway(
            name=ep_name,
            ai_gateway={
                "inference_table_config": {
                    "catalog_name": CATALOG,
                    "schema_name": SCHEMA,
                    "table_name_prefix": prefix,
                    "enabled": True,
                }
            },
        )
        print(f"  Done — payloads will be logged to {CATALOG}.{SCHEMA}.{prefix}_request_response")
    except Exception as e:
        print(f"  Error: {e}")

print("\nAfter sending a few requests, query the tables:")
print(f"  SELECT * FROM {CATALOG}.{SCHEMA}.mas_payload_request_response LIMIT 5;")
print(f"  SELECT * FROM {CATALOG}.{SCHEMA}.ka_payload_request_response LIMIT 5;")
