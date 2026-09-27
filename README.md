# Kaapi Bricks — Intelligent Store Operations

**FE Bar submission** · Industry: Multi-location food-service and specialty retail

---

## Business Problem

Kaapi Bricks operates **37 stores** across India and internationally selling South Indian filter
coffee. Each store manager currently reconciles supplier deliveries, checks inventory, reviews
demand, and looks up operating guidance across separate systems — a process that takes roughly
**30 minutes per delivery, per store, every day**.

This solution replaces that manual workflow with a single governed assistant that answers
operational questions in seconds: catching invoice discrepancies, flagging stockout risk before
it happens, and recommending preparation quantities based on weather and local demand patterns.

**Measured outcome:** Supplier-invoice cross-check reduced from ~30 minutes to seconds.
Full KPI math in `evidence/10_business_kpi_calculations.md`.

---

## Integrated Data Journey

```
Synthetic raw retail + supplier data   (scripts/generate_data.py — 37 stores, 200k orders)
  → Unity Catalog Volume               (raw_data/<entity>/*.parquet)
  → Lakeflow bronze streaming tables   (Auto Loader, 14 entities)
  → Lakeflow silver tables             (conformed + data-quality expectations, 14 entities)
  → Lakeflow gold operational tables   (7 KPI + operational tables)
  → Lakebase operational serving       (4 hot tables at OLTP latency)
  → ML / GenAI                         (Knowledge Assistant, Multi-Agent Supervisor, document AI, MLflow)
  → Genie Agent                        (governed NL analytics over silver + gold)
  → Databricks App                     (store-manager console — main-chat-app)
```

The same entity keys (store_id, ingredient_id, po_id) flow from raw Parquet through every layer
to the app response — one integrated journey, not separate demos.

---

## FE Bar Layer Map

| Layer | Implementation | File |
|---|---|---|
| **Lakeflow** | Serverless declarative pipeline: 14 bronze (Auto Loader) + 14 silver (expectations) + 7 gold | `databricks.yml`, `resources/`, `src/pipeline/` |
| **Unity Catalog** | Catalog `fevm_cme_conde_catalog`, schema `kaapi_bricks`, comments, grants, lineage | `scripts/generate_data.py`, pipeline |
| **Lakebase** | 4 operational gold tables synced for OLTP reads; app memory + QA cache | `scripts/sync_gold_to_lakebase.py`, `apps/main-chat-app/app.py` |
| **ML / GenAI** | Knowledge Assistant (RAG), Multi-Agent Supervisor, `ai_parse_document` (invoice), MLflow eval | `scripts/run_ka_evaluation.ipynb`, `run_mas_evaluation.ipynb` |
| **Genie Agent** | NL analytics space wired to silver + gold tables | `scripts/create_agents.py` |
| **Databricks App** | Store-manager chat console + MCP ops-advisor + growth + promo agents | `apps/` |

---

## Repository Layout

```
README.md                ← you are here
DEMO.md                  ← 15-min demo script (tell-show-tell per scene)
DEMO_SCRIPT.md           ← extended talking points
ARCHITECTURE.md          ← living integrated-journey diagram
febar.md                 ← working plan + submission checklist
LAKEFLOW_PLAN.md         ← medallion pipeline design doc

databricks.yml           ← DAB bundle root
resources/               ← kaapi_pipeline.pipeline.yml (serverless LDP)
src/pipeline/            ← 01_bronze.sql · 02_silver.sql · 03_gold.sql
scripts/                 ← generate_data.py · sync_gold_to_lakebase.py · create_agents.py · evals
apps/                    ← main-chat-app · growth-advisor-agent · promo-agent · mcp-server
sample-invoices/         ← PDF invoices for the doc-AI demo
evidence/                ← committed text execution evidence (01–10)
deck/                    ← FE_BAR_DECK.md (business presentation)
```

---

## Deploy

**Prerequisites:** Databricks CLI authenticated, Unity Catalog access, SQL warehouse, Lakebase
instance named `kaapi-bricks`.

```bash
# 1. Land raw data in the UC Volume
python scripts/generate_data.py --profile DEFAULT

# 2. Drop legacy generator-created tables (one-time migration)
databricks sql execute --profile DEFAULT --file scripts/drop_legacy_tables.sql

# 3. Deploy and run the Lakeflow medallion pipeline
databricks bundle deploy -t dev --profile DEFAULT
databricks bundle run kaapi_bricks_medallion -t dev --profile DEFAULT

# 4. Create app-write tables (outside the pipeline)
databricks sql execute --profile DEFAULT --file scripts/init_app_tables.sql

# 5. Sync gold operational data to Lakebase
python scripts/sync_gold_to_lakebase.py --profile DEFAULT

# 6. Create KA + MAS + Genie agents
python scripts/create_agents.py --profile DEFAULT

# 7. Deploy apps
./deploy.sh DEFAULT fevm_cme_conde_catalog <warehouse_id>
```

**Catalog and warehouse:** change `fevm_cme_conde_catalog` → your catalog in `databricks.yml`
variables and `apps/main-chat-app/app.py` (`CATALOG_SCHEMA`).

---

## Data

Fully synthetic — no real customer identity. Generated with Faker (seed=42):
37 stores · 28 products · 22 ingredients · 8 suppliers · 15,000 customers ·
~200,000 orders · 2,000 purchase orders · inventory transactions · po_line_items

See `evidence/` for committed text-readable execution results after deployment.
