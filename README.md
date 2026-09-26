# Kaapi Bricks Demo — Portable Setup

Deploy this demo on any Databricks workspace in 3 steps.

## Quick Start

1. Upload this entire folder to your Databricks workspace
2. Open `SETUP.ipynb` — edit 2 values (catalog name + warehouse ID)
3. Run all cells — follow the printed instructions

## What's Inside

```
kaapi_bricks_DEMO/
├── SETUP.ipynb                    ← RUN THIS FIRST (master setup notebook)
├── README.md                      ← You are here
├── DEMO.md                        ← Demo script with talking points (15 min)
├── prewarm_cache.py               ← Run before demo to warm Lakebase cache
│
├── apps/
│   ├── main-chat-app/             ← Main Kaapi Bricks chat app
│   │   ├── app.py                 ← FastAPI backend (MAS + Lakebase + invoice parser)
│   │   ├── requirements.txt
│   │   └── static/index.html      ← React frontend
│   │
│   └── mcp-server/                ← Operations Advisor MCP server (separate app)
│       ├── app.py                 ← MCP JSON-RPC + weather API + calendar
│       ├── app.yaml
│       ├── requirements.txt
│       └── static/index.html      ← Admin + Compare UI
│
├── scripts/
│   ├── generate_data.py           ← Creates 14 Delta tables (200K orders)
│   ├── generate_ka_documents.py   ← Creates 6 branded PDFs for KA
│   ├── hardcoded_responses.py     ← Wrong answers for eval testing
│   ├── create_agent_dashboard.py  ← Lakeview monitoring dashboard
│   ├── enable_inference_tables.py ← AI Gateway payload logging
│   ├── run_ka_evaluation.ipynb    ← KA eval (10 questions, 4 scorers)
│   ├── run_ka_evaluation_incorrect.ipynb  ← KA eval with wrong answers
│   ├── run_mas_evaluation.ipynb   ← MAS eval
│   └── run_mas_evaluation_incorrect.ipynb ← MAS eval with wrong answers
│
└── sample-invoices/               ← PDF invoices for invoice parser demo
    ├── invoice_coorg_mixed.pdf    ← 3 matches + 1 discrepancy + 1 extra
    ├── invoice_complex_coorg.pdf  ← 8-item complex GST invoice
    ├── invoice_coorg_discrepancy.pdf
    └── invoice_nandini_dairy.pdf
```

## What You Need to Edit

In `SETUP.ipynb`, edit only 2 values:
```python
CATALOG = "your_catalog_name"
SQL_WAREHOUSE_ID = "your_warehouse_id"
```

In `apps/main-chat-app/app.py`, search and replace:
```
fevm_cme_conde_catalog → your_catalog_name
```

## Architecture

```
User → Main Chat App (Databricks App)
         → MAS Supervisor Endpoint
              ├── Knowledge Assistant (RAG over 6 PDFs)
              ├── Genie Space (SQL over 14 Delta tables)
              └── Operations Advisor (MCP Server - separate App)
                   ├── Live weather (Open-Meteo API)
                   ├── Indian holiday calendar
                   └── LLM reasoning (configurable model)
```

## Demo Duration: ~15 minutes

See `DEMO.md` for the full script with 6 scenes.
