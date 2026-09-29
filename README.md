# Kaapi Bricks — Intelligent Store Operations

**FE Bar submission** · Industry: multi-location food service and specialty retail ·
Fictional company, 100% synthetic data

---

## Business problem

Kaapi Bricks runs **37 filter-coffee stores** (30 in India, 7 international). Each store gets about
two supplier deliveries a day. Today the store manager checks every paper invoice against its
purchase order by hand, looks up stock levels by counting, and answers staff questions about
recipes and food safety from memory or a binder of PDFs.

This solution gives the manager one governed assistant:

- **Invoice check:** upload an invoice → it is parsed, matched to the PO, and every quantity and
  price discrepancy is flagged → the manager approves.
- **Inventory:** current stock, below-reorder items, open and late POs, served from Lakebase.
- **Questions in plain English:** sales, suppliers, and inventory from governed tables; recipes,
  SOPs, and food safety from the company's own documents, with citations.

**Projected value: ~₹2.2 crore (~$264,500) a year, simple payback 3.9 months.** These are
projections from labeled assumptions, not measured outcomes. No timed baseline trial has been run.
See `evidence/10_business_kpi_calculations.md`.

---

## Integrated data journey (as built and run)

```
scripts/generate_data.py          synthetic POS, supplier, PO, inventory data (Faker, seed=42)
  → Unity Catalog volume          raw_data/<entity>/*.parquet
  → Lakeflow bronze               14 streaming tables (Auto Loader)
  → Lakeflow silver               14 materialized views, 45 data-quality expectations
  → Lakeflow gold                 7 operational + KPI views
  → Lakebase                      4 gold tables synced for the app's point lookups
  → Genie Agent (Agent mode)      21 silver + gold tables + 6 SOP/recipe PDFs
  → Unity AI Gateway              every non-Genie AI call: invoice document parsing (kaapi_llm),
                                  cache embeddings (kaapi_embed), weather/holiday advice (MCP service
                                  kaapi_ops_advisor); human approval writes app tables
  → MLflow evaluation             Correctness / Relevance / Safety on 10 store-manager questions
  → Databricks App                store manager console (main-chat-app)
```

The same keys (store_id, ingredient_id, po_id) flow through every layer. `evidence/08` traces one
real purchase order from raw file to app response.

---

## FE Bar layer map

| Layer | What is built | Where | Evidence |
|---|---|---|---|
| **Lakeflow** | Serverless declarative pipeline `kaapi_bricks_medallion`: 14 bronze + 14 silver + 7 gold. Run 065d6a70 completed | `databricks.yml`, `resources/kaapi_pipeline.pipeline.yml`, `src/pipeline/` | 01, 03 |
| **Unity Catalog** | `kaapi_bricks` schema, raw/invoice volumes, table comments, lineage, app service-principal grants | pipeline, `scripts/generate_data.py` | 02 |
| **Lakebase** | `lb_inventory_position`, `lb_open_purchase_orders`, `lb_delivery_exceptions`, `lb_product_demand`; the inventory panel reads `/api/lakebase/inventory/{store}`. Also chat history + answer cache | `scripts/sync_gold_to_lakebase.py`, `apps/main-chat-app/` | 04, 07 |
| **ML / GenAI** | Invoice document parsing + extraction through Unity AI Gateway (`kaapi_llm`); daily preparation plan (SQL + Lakebase + MCP weather/holiday advisor); MLflow `genai.evaluate` with Correctness, Relevance, Safety | `apps/main-chat-app/app.py`, `scripts/run_app_evaluation.py` | 06, 09, 11 |
| **Genie Agent** | One space: 21 tables + SOP PDF volume, called through the **Agent mode** API so it can read documents | `resources/genie_space.json`, `scripts/create_genie_agent.py` | 05, 09 |
| **Databricks App** | Store manager console: chat, preparation plan, inventory panel, invoice upload and approval | `apps/main-chat-app/` | 07, 11 |
| **Unity AI Gateway** | Every AI call except Genie goes through governed UC services: `kaapi_llm`, `kaapi_embed`, MCP service `kaapi_ops_advisor`. `EXECUTE` grants, service-wide rate limits (a real 429 captured), payload logs, no ungoverned fallback | UC services in `kaapi_bricks`; `app.yaml` `GW_*` | 11 |

**Replaced:** Knowledge Assistant and Supervisor Agent (being deprecated). One Genie Agent now covers
structured data and documents.

---

## Evidence index (text, committed)

| File | Contents |
|---|---|
| `evidence/01_lakeflow_run.txt` | Pipeline update ID, status, duration, row counts for all 35 datasets |
| `evidence/02_uc_tables_and_lineage.md` | Unity Catalog table inventory and raw → gold lineage traces |
| `evidence/03_data_quality_results.txt` | 45 expectations with passed/failed counts, read from the pipeline event log |
| `evidence/04_lakebase_queries.txt` | Lakebase tables, synced row counts, operational queries |
| `evidence/05_genie_questions_and_answers.md` | Genie questions, generated SQL, returned results |
| `evidence/06_genai_model_outputs.md` | Invoice parse and match output from `/api/parse-invoice` |
| `evidence/07_app_health_and_api_tests.txt` | App status and authenticated API responses (Lakebase inventory, chat) |
| `evidence/08_end_to_end_record_trace.md` | PO-00006 traced raw → bronze → silver → gold → Lakebase → app |
| `evidence/09_mlflow_evaluation_results.md` | MLflow run IDs, scores per iteration, per-question traces, failure analysis |
| `evidence/10_business_kpi_calculations.md` | Value model: every assumption labeled, payback and ROI formulas |
| `evidence/11_unity_ai_gateway.md` | Gateway services, grants, invoice / preparation plan / cache through the gateway, payload-log rows, a real HTTP 429 |

---

## Repository layout

```
README.md                ← you are here
deck/FE_BAR_DECK.md      ← business presentation (outcome first, 10 sections)
DEMO.md                  ← 15-minute demo script, tell-show-tell per scene
ROLEPLAY_PREP.md         ← opening, scene script, prepared answers for both personas
ARCHITECTURE.md          ← architecture and design decisions
febar.md                 ← submission checklist
LAKEFLOW_PLAN.md         ← pipeline design notes

databricks.yml           ← bundle root
resources/               ← kaapi_pipeline.pipeline.yml · genie_space.json
src/pipeline/            ← 01_bronze.sql · 02_silver.sql · 03_gold.sql
scripts/                 ← data generation, migration, Lakebase sync, Genie config, evaluation
apps/main-chat-app/      ← the store manager console (deployed)
apps/mcp-server/         ← operations-advisor MCP server, called through the Unity AI Gateway MCP service
sample-invoices/         ← invoice PDFs for the demo
evidence/                ← execution evidence 01–11
```

Legacy files kept for history, not part of the current flow: `scripts/create_agents.py`,
`scripts/run_ka_evaluation*.ipynb`, `scripts/run_mas_evaluation*.ipynb` (Knowledge Assistant /
Supervisor Agent), `apps/growth-advisor-agent/`, `apps/promo-agent/`.

---

## Deploy

Prerequisites: Databricks CLI authenticated, a Unity Catalog catalog, a SQL warehouse, and a
Lakebase instance named `kaapi-bricks`. Set your catalog in `databricks.yml` and in
`apps/main-chat-app/app.py` (`CATALOG_SCHEMA`).

```bash
# 1. Generate synthetic data and land raw Parquet in the volume
python scripts/generate_data.py --profile DEFAULT --warehouse-id <warehouse_id>

# 2. One-time migration: drop tables the pipeline will own
#    run scripts/drop_legacy_tables.sql in a SQL editor or via the statements API

# 3. Deploy and run the Lakeflow pipeline
databricks bundle deploy -t dev --profile DEFAULT
databricks bundle run kaapi_bricks_medallion -t dev --profile DEFAULT

# 4. Create the app-write tables (outside the pipeline)
#    run scripts/init_app_tables.sql

# 5. Sync gold operational tables to Lakebase (repeat after every pipeline update)
python scripts/sync_gold_to_lakebase.py --profile DEFAULT --warehouse-id <warehouse_id>
#    then, in Lakebase: GRANT SELECT ON lb_inventory_position, lb_open_purchase_orders,
#    lb_delivery_exceptions, lb_product_demand TO "<app service principal>";

# 6. Configure the Genie Agent from resources/genie_space.json
python scripts/create_genie_agent.py --profile DEFAULT            # update existing space
python scripts/create_genie_agent.py --create --catalog <catalog> # or create a new one

# 7. Deploy the apps and grant the app service principal access
./deploy.sh DEFAULT <catalog> <warehouse_id>

# 7b. Unity AI Gateway (exact JSON in evidence/11): create the governed services…
databricks ai-gateway create-model-service schemas/<catalog>.kaapi_bricks kaapi_llm   --json '…'  # Sonnet 4.6 → Haiku 4.5 fallback
databricks ai-gateway create-model-service schemas/<catalog>.kaapi_bricks kaapi_embed --json '…'  # BGE-large-en
databricks ai-gateway create-mcp-service   schemas/<catalog>.kaapi_bricks kaapi_ops_advisor \
  --json '{"config":{"source_connection":{"name":"connections/kaapi_ops_mcp"}}}'
#     …add rate limits and payload logs…
databricks ai-gateway update-model-service model-services/<catalog>.kaapi_bricks.kaapi_llm config.rate_limits \
  --json '{"config":{"rate_limits":[{"key":"RATE_LIMIT_KEY_SERVICE","renewal_period":"RATE_LIMIT_RENEWAL_PERIOD_MINUTE","requests":300}]}}'
databricks ai-gateway update-model-service model-services/<catalog>.kaapi_bricks.kaapi_llm config.inference_table \
  --json '{"config":{"inference_table":{"parent":"schemas/<catalog>.kaapi_bricks","table_name_prefix":"kaapi_llm"}}}'
#     …grant EXECUTE to the app service principals (main app: all three; MCP app: kaapi_llm)…
databricks grants update model_service <catalog>.kaapi_bricks.kaapi_llm \
  --json '{"changes":[{"principal":"<app-sp-client-id>","add":["EXECUTE"]}]}'
#     …and give both apps the ai-gateway scope, then redeploy them
databricks apps update <app> --json '{"user_api_scopes":["serving.serving-endpoints","ai-gateway","sql","dashboards.genie"], …}'

# 8. Evaluate (results land in MLflow)
python scripts/run_app_evaluation.py --app-url <app-url>   # the deployed app, end to end
#    scripts/run_genie_evaluation.py evaluates Genie directly (serverless notebook job)
```

---

## Data

Fully synthetic, fictional company (Faker, seed=42): 37 stores · 28 products · 22 ingredients ·
8 suppliers · 15,000 customers · 200,000 orders · 2,000 purchase orders · 3,493 PO line items ·
171,163 inventory transactions · 6 SOP/training PDFs.

Date coverage: orders 2026-02-01 → 2026-05-14 (the 200,000-order cap is reached in mid-May);
purchase orders and inventory 2026-02-01 → 2026-07-31.
