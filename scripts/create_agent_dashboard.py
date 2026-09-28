import os
"""Create a Lakeview dashboard for Kaapi Bricks Agent Monitoring.

Combines:
- system.serving.endpoint_usage (foundation model token usage — filterable)
- fevm_cme_conde_catalog.kaapi_bricks.inference_logs (app-level agent logs)
- Lakebase kaapi_app tables via SQL warehouse (chat stats, cache)
"""

import json
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip("/")
headers = w.config.authenticate()
headers["Content-Type"] = "application/json"
me = w.current_user.me().user_name
warehouse_id = "e755eae9d758fdf7"

# ── CONFIGURABLE ENDPOINT FILTER ──
# Change this list to monitor different endpoints
ENDPOINTS = [
    "databricks-bge-large-en",
    "databricks-meta-llama-3-3-70b-instruct",
    "databricks-claude-sonnet-4-6",
    "databricks-gpt-5-2",
    "databricks-llama-4-maverick",
]
endpoint_sql = ",".join(f"'{e}'" for e in ENDPOINTS)

# ── DATASETS ──

datasets = [
    # --- Foundation Model metrics (filterable) ---
    {
        "name": "fm_summary",
        "displayName": "FM Summary",
        "queryLines": [
            f"SELECT COUNT(*) as total_requests, COALESCE(SUM(eu.input_token_count + eu.output_token_count), 0) as total_tokens, COALESCE(SUM(eu.input_token_count), 0) as input_tokens, COALESCE(SUM(eu.output_token_count), 0) as output_tokens, COUNT(DISTINCT se.endpoint_name) as active_endpoints, SUM(CASE WHEN eu.status_code != 200 THEN 1 ELSE 0 END) as errors FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS"
        ],
    },
    {
        "name": "fm_by_endpoint",
        "displayName": "FM by Endpoint",
        "queryLines": [
            f"SELECT se.endpoint_name as endpoint, COUNT(*) as requests, COALESCE(SUM(eu.input_token_count), 0) as input_tokens, COALESCE(SUM(eu.output_token_count), 0) as output_tokens, COALESCE(SUM(eu.input_token_count + eu.output_token_count), 0) as total_tokens, SUM(CASE WHEN eu.status_code != 200 THEN 1 ELSE 0 END) as errors, ROUND(SUM(CASE WHEN eu.status_code = 200 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as success_pct FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS GROUP BY 1 ORDER BY 5 DESC"
        ],
    },
    {
        "name": "fm_hourly",
        "displayName": "FM Hourly",
        "queryLines": [
            f"SELECT se.endpoint_name as endpoint, DATE_TRUNC('hour', eu.request_time) as hour, COUNT(*) as requests, COALESCE(SUM(eu.input_token_count + eu.output_token_count), 0) as tokens FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.status_code = 200 AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 24 HOURS GROUP BY 1, 2 ORDER BY 2, 1"
        ],
    },
    {
        "name": "fm_daily",
        "displayName": "FM Daily",
        "queryLines": [
            f"SELECT se.endpoint_name as endpoint, DATE(eu.request_time) as day, COALESCE(SUM(eu.input_token_count + eu.output_token_count), 0) as total_tokens, COUNT(*) as requests FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.status_code = 200 AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS GROUP BY 1, 2 ORDER BY 2, 1"
        ],
    },
    {
        "name": "fm_errors",
        "displayName": "FM Errors",
        "queryLines": [
            f"SELECT se.endpoint_name as endpoint, CAST(eu.status_code AS STRING) as status_code, COUNT(*) as error_count FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.status_code != 200 AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS GROUP BY 1, 2 ORDER BY 3 DESC"
        ],
    },
    {
        "name": "fm_distribution",
        "displayName": "FM Distribution",
        "queryLines": [
            f"SELECT se.endpoint_name as endpoint, COALESCE(SUM(eu.input_token_count + eu.output_token_count), 0) as total_tokens FROM system.serving.endpoint_usage eu JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id WHERE se.endpoint_name IN ({endpoint_sql}) AND eu.status_code = 200 AND eu.request_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS GROUP BY 1 ORDER BY 2 DESC"
        ],
    },
    # --- Kaapi Bricks Agent Logs ---
    {
        "name": "kaapi_summary",
        "displayName": "Kaapi Summary",
        "queryLines": [
            "SELECT COUNT(*) as total_queries, ROUND(AVG(latency_ms) / 1000, 1) as avg_latency_sec, COUNT(CASE WHEN error IS NOT NULL AND error != '' THEN 1 END) as errors FROM fevm_cme_conde_catalog.kaapi_bricks.inference_logs WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS"
        ],
    },
    {
        "name": "kaapi_logs",
        "displayName": "Kaapi Logs",
        "queryLines": [
            "SELECT store_location as store, query as question, LEFT(response_summary, 120) as response, ROUND(latency_ms / 1000, 1) as latency_sec, agent_name as agent, endpoint_name as endpoint, input_tokens as in_tokens, output_tokens as out_tokens, timestamp FROM fevm_cme_conde_catalog.kaapi_bricks.inference_logs ORDER BY timestamp DESC LIMIT 30"
        ],
    },
    {
        "name": "kaapi_latency",
        "displayName": "Kaapi Latency",
        "queryLines": [
            "SELECT DATE_TRUNC('hour', timestamp) as hour, COUNT(*) as queries, ROUND(AVG(latency_ms) / 1000, 1) as avg_sec, ROUND(MIN(latency_ms) / 1000, 1) as min_sec, ROUND(MAX(latency_ms) / 1000, 1) as max_sec FROM fevm_cme_conde_catalog.kaapi_bricks.inference_logs WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 24 HOURS GROUP BY 1 ORDER BY 1"
        ],
    },
    {
        "name": "kaapi_stores",
        "displayName": "Kaapi Stores",
        "queryLines": [
            "SELECT store_location as store, COUNT(*) as queries, ROUND(AVG(latency_ms) / 1000, 1) as avg_latency_sec FROM fevm_cme_conde_catalog.kaapi_bricks.inference_logs WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
        ],
    },
]

# ── WIDGET BUILDERS ──

def counter(name, dataset, field, title):
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [{"name": field, "expression": f"`{field}`"}], "disaggregated": True}}], "spec": {"version": 2, "widgetType": "counter", "encodings": {"value": {"fieldName": field, "displayName": title}}, "frame": {"showTitle": True, "title": title}}}}

def bar(name, dataset, x, y, title, color=None, x_type="categorical"):
    fields = [{"name": x, "expression": f"`{x}`"}, {"name": y, "expression": f"`{y}`"}]
    enc = {"x": {"fieldName": x, "scale": {"type": x_type}, "displayName": x}, "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": y}}
    if color:
        fields.append({"name": color, "expression": f"`{color}`"})
        enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}, "displayName": color}
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}], "spec": {"version": 3, "widgetType": "bar", "encodings": enc, "frame": {"showTitle": True, "title": title}}}}

def line(name, dataset, x, y, title, color=None):
    fields = [{"name": x, "expression": f"`{x}`"}, {"name": y, "expression": f"`{y}`"}]
    enc = {"x": {"fieldName": x, "scale": {"type": "temporal"}, "displayName": x}, "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": y}}
    if color:
        fields.append({"name": color, "expression": f"`{color}`"})
        enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}, "displayName": color}
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}], "spec": {"version": 3, "widgetType": "line", "encodings": enc, "frame": {"showTitle": True, "title": title}}}}

def table(name, dataset, title, columns):
    fields = [{"name": c[0], "expression": f"`{c[0]}`"} for c in columns]
    col_enc = [{"fieldName": c[0], "displayName": c[1]} for c in columns]
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": True}}], "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": col_enc}, "frame": {"showTitle": True, "title": title}}}}

def text(name, lines):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}}}

# ── LAYOUT ──

ep_list = ", ".join(ENDPOINTS[:3]) + "..."
layout = [
    # Title
    {**text("title", [f"# Kaapi Bricks — Agent Monitor"]), "position": {"x": 0, "y": 0, "width": 6, "height": 1}},
    {**text("subtitle", [f"Foundation Models: {ep_list} | Agent Logs: MAS Supervisor + KA + Genie"]), "position": {"x": 0, "y": 1, "width": 6, "height": 1}},

    # ── SECTION 1: Foundation Model Metrics ──
    {**text("h-fm", ["## Foundation Model Usage"]), "position": {"x": 0, "y": 2, "width": 6, "height": 1}},

    # Counters
    {**counter("c-req", "fm_summary", "total_requests", "Requests (7d)"), "position": {"x": 0, "y": 3, "width": 2, "height": 3}},
    {**counter("c-tok", "fm_summary", "total_tokens", "Tokens (7d)"), "position": {"x": 2, "y": 3, "width": 2, "height": 3}},
    {**counter("c-err", "fm_summary", "errors", "Errors (7d)"), "position": {"x": 4, "y": 3, "width": 2, "height": 3}},

    # Token breakdown table
    {**table("tbl-fm", "fm_by_endpoint", "Token Usage by Endpoint", [
        ("endpoint", "Endpoint"), ("requests", "Requests"), ("input_tokens", "Input Tokens"),
        ("output_tokens", "Output Tokens"), ("total_tokens", "Total Tokens"),
        ("errors", "Errors"), ("success_pct", "Success %"),
    ]), "position": {"x": 0, "y": 6, "width": 6, "height": 5}},

    # Hourly charts
    {**text("h-hourly", ["### Hourly Trends (24h)"]), "position": {"x": 0, "y": 11, "width": 6, "height": 1}},
    {**bar("bar-req-h", "fm_hourly", "hour", "requests", "Requests per Hour", "endpoint", "temporal"), "position": {"x": 0, "y": 12, "width": 3, "height": 5}},
    {**bar("bar-tok-h", "fm_hourly", "hour", "tokens", "Tokens per Hour", "endpoint", "temporal"), "position": {"x": 3, "y": 12, "width": 3, "height": 5}},

    # Daily trend + distribution
    {**text("h-daily", ["### Daily Trend & Distribution (7d)"]), "position": {"x": 0, "y": 17, "width": 6, "height": 1}},
    {**line("line-daily", "fm_daily", "day", "total_tokens", "Daily Token Volume", "endpoint"), "position": {"x": 0, "y": 18, "width": 3, "height": 5}},
    {**bar("bar-dist", "fm_distribution", "endpoint", "total_tokens", "Token Distribution by Endpoint"), "position": {"x": 3, "y": 18, "width": 3, "height": 5}},

    # Errors
    {**bar("bar-err", "fm_errors", "endpoint", "error_count", "Errors by Endpoint & Status", "status_code"), "position": {"x": 0, "y": 23, "width": 6, "height": 4}},

    # ── SECTION 2: Kaapi Bricks Agent Logs ──
    {**text("h-kaapi", ["## Kaapi Bricks — Agent Performance"]), "position": {"x": 0, "y": 27, "width": 6, "height": 1}},

    # Kaapi counters
    {**counter("c-kq", "kaapi_summary", "total_queries", "Agent Queries (7d)"), "position": {"x": 0, "y": 28, "width": 2, "height": 3}},
    {**counter("c-klat", "kaapi_summary", "avg_latency_sec", "Avg Latency (sec)"), "position": {"x": 2, "y": 28, "width": 2, "height": 3}},
    {**counter("c-kerr", "kaapi_summary", "errors", "Agent Errors"), "position": {"x": 4, "y": 28, "width": 2, "height": 3}},

    # Latency trend + store breakdown
    {**line("line-lat", "kaapi_latency", "hour", "avg_sec", "Avg Latency Over Time (sec)"), "position": {"x": 0, "y": 31, "width": 3, "height": 5}},
    {**bar("bar-stores", "kaapi_stores", "store", "queries", "Queries by Store Location"), "position": {"x": 3, "y": 31, "width": 3, "height": 5}},

    # Inference logs table
    {**text("h-logs", ["### Recent Inference Logs"]), "position": {"x": 0, "y": 36, "width": 6, "height": 1}},
    {**table("tbl-logs", "kaapi_logs", "Kaapi Bricks — Chat Logs", [
        ("store", "Store"), ("question", "Question"), ("response", "Response"),
        ("latency_sec", "Latency (s)"), ("agent", "Agent"), ("in_tokens", "In"), ("out_tokens", "Out"), ("timestamp", "Time"),
    ]), "position": {"x": 0, "y": 37, "width": 6, "height": 6}},

    # Links
    {**text("h-links", [
        "### Quick Links",
        f"- [MAS Traces (MLflow)]({host}/ml/experiments/982411422225143) — Full trace spans for every MAS request",
        f"- [KA Traces (MLflow)]({host}/ml/experiments/982411422225142) — Knowledge Assistant traces",
        f"- [Kaapi Bricks App]({os.environ.get('KAAPI_APP_URL', '<app-url>')}) — Live chat app",
    ]), "position": {"x": 0, "y": 43, "width": 6, "height": 2}},
]

dashboard_def = {
    "datasets": datasets,
    "pages": [{"name": "main", "displayName": "Agent Monitor", "layout": layout, "pageType": "PAGE_TYPE_CANVAS"}],
}

# ── CREATE ──

print("Creating dashboard...")
resp = requests.post(f"{host}/api/2.0/lakeview/dashboards", headers=headers, json={
    "display_name": "Kaapi Bricks — Agent Monitor",
    "warehouse_id": warehouse_id,
    "parent_path": f"/Workspace/Users/{me}",
    "serialized_dashboard": json.dumps(dashboard_def),
})

if resp.ok:
    dash_id = resp.json()["dashboard_id"]
    print(f"  Created: {dash_id}")
    print(f"  URL: {host}/sql/dashboardsv3/{dash_id}")

    pub = requests.post(f"{host}/api/2.0/lakeview/dashboards/{dash_id}/published",
        headers=headers, json={"embed_credentials": True, "warehouse_id": warehouse_id})
    if pub.ok:
        print(f"  Published: {host}/sql/dashboardsv3/{dash_id}/published")
    else:
        print(f"  Publish: {pub.status_code} {pub.text[:200]}")

    print(f"\n  Endpoints monitored: {', '.join(ENDPOINTS)}")
    print(f"  To change endpoints, edit ENDPOINTS list in this script and re-run.")
else:
    print(f"Error: {resp.status_code}\n{resp.text[:500]}")
