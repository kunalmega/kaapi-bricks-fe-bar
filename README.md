# Kaapi Bricks — Intelligent Store Operations

**FE Bar submission** · Retail & Consumer Goods (quick-service coffee chain) · Fictional company,
100% synthetic data · Deck: `deck/FE_BAR_DECK.md` · Demo: `DEMO.md` · Roleplay: `ROLEPLAY_PREP.md`

Kaapi Bricks' 37 store managers run their stores from five or six disconnected tools: a sales
dashboard, a stock spreadsheet, supplier emails, paper invoices and six SOP PDFs. This build gives
them **one app on one governed copy of the data**, where they can **Ask** questions, **See** the store
live, **Act** on deliveries, and **Plan** the day.

---

## Proof it runs: executed notebooks (outputs committed)

Every notebook in [`notebooks/`](notebooks/) was **executed against the live workspace on
2026-10-23/24 and committed with its outputs**. Open any of them on GitHub to read what actually ran.
For text-only review, the same output cells are collected in
[`evidence/13_executed_notebook_outputs.txt`](evidence/13_executed_notebook_outputs.txt).

| Notebook | What it shows (real output) |
|---|---|
| [`01_pipeline_and_data_quality`](notebooks/01_pipeline_and_data_quality.ipynb) | Lakeflow update timeline from the event log; **14 bronze / 14 silver / 7 gold** tables with row counts; **45 of 45** expectations passed, 0 failed rows |
| [`02_row_level_security`](notebooks/02_row_level_security.ipynb) | Same SQL as HQ (**all stores, 200,000 orders**) vs the Koramangala manager (**1 store, 6,606 orders**); the same Genie question answered for 36 stores vs only STR-001 |
| [`03_genie_agent`](notebooks/03_genie_agent.ipynb) | Live Genie Agent answers with the **generated SQL** (`execute_sql`) for data questions and **SOP-document search** (`search_context_files`) for procedures |
| [`04_app_lakebase_and_ai_workflows`](notebooks/04_app_lakebase_and_ai_workflows.ipynb) | The deployed app: Live Dashboard from **Lakebase in ~33 ms** (median of 5); the invoice check catching **match / price / quantity / extra / missing** lines in ~7 s via **Unity AI Gateway**; the preparation plan using the **ML forecast + live weather** (MCP), with its trace ID |
| [`05_demand_forecast_model`](notebooks/05_demand_forecast_model.ipynb) | UC model `demand_forecaster@champion`: **MAE 1.42 vs 1.57** for the same-weekday baseline (**9.3% better**) on a 14-day holdout; next-7-day forecast for 37 stores × 28 drinks |
| [`06_store_briefs_and_ai_gateway`](notebooks/06_store_briefs_and_ai_gateway.ipynb) | 37 morning action plans; **882 of 884 numbers verified** against the SQL facts; the facts the LLM was given; gateway payload-log rows by caller |
| [`07_evaluation_over_time`](notebooks/07_evaluation_over_time.ipynb) | A live `mlflow.genai.evaluate` run of the deployed app, the **`eval_history`** time series (scheduled + manual runs), and per-question judge scores |

Earlier point-in-time captures (pipeline run, invoice tests, write-through test, gateway 429,
evaluation history from 0.00 to 0.70) are in [`evidence/`](evidence/) 01–12.

### Measured results at a glance

| | Result | Source |
|---|---|---|
| Pipeline | 14 → 14 → 7 tables, serverless, 45 / 45 data-quality expectations passed | nb 01 |
| Row-level security | Store manager sees only their own store, in SQL and in Genie | nb 02 |
| Lakebase serving | Whole store dashboard in ~33 ms median (30–38 ms); approvals update stock and POs instantly | nb 04, evidence/12 |
| Invoice check | 5 of 5 line outcomes correct (1 match, 4 planted discrepancies) in ~7 s server time | nb 04 |
| Demand forecast | 9.3% lower MAE than the same-weekday baseline; registered `@champion` in UC | nb 05 |
| Morning briefs | 37 stores; 882 / 884 numbers grounded; failed checks rewritten automatically | nb 06 |
| AI quality (app end to end) | Correctness **0.90 → 1.00 → 1.00** across today's 3 runs; Relevance 1.00; Safety 1.00 | nb 07, `eval_history` |

The eval set is 10 questions, so one question moves Correctness by 0.10. The September runs scored
0.00 → 0.50 → 0.70 while the root causes were being fixed (evidence/09). The daily job keeps
adding data points.

---

## Integrated data journey

```
scripts/generate_data.py        synthetic POS, supplier, PO, inventory data (Faker, seed=42)
  → UC Volume raw_data/          Parquet per entity + 6 SOP PDFs
  → Lakeflow (serverless SDP)    bronze 14 streaming tables → silver 14 MVs (45 expectations)
                                 → gold 7 MVs; store-keyed tables carry a UC ROW FILTER
  → Unity Catalog                one governance plane: tables, volumes, row filters, models,
                                 AI Gateway services, grants, lineage
  → ML                           demand_forecaster (UC model, @champion) → ml_demand_forecast
  → GenAI                        morning briefs + invoice reading + prep plan via Unity AI Gateway
  → Lakebase (Postgres)          lb_* serving copies of gold, forecast and briefs; app state;
                                 invoice approvals write through
  → Genie Agent (Agent mode)     21 governed tables + SOP PDFs, respects row-level security
  → Databricks App               Ask · See · Act · Plan for the store manager
  → MLflow                       traces on every request; evaluation tracked in eval_history

Daily job kaapi_daily_ops (05:30 IST, from code):
  pipeline → train forecaster → score 7 days → write 37 briefs → sync Lakebase → evaluate the app
```

---

## FE Bar layer map

| Layer | What is built | Where | Proof |
|---|---|---|---|
| **Lakeflow** | Serverless declarative pipeline: 14 bronze + 14 silver + 7 gold, 45 expectations; runs as the first task of the daily job | `src/pipeline/`, `resources/kaapi_pipeline.pipeline.yml` | nb 01 |
| **Unity Catalog** | One schema for tables, volumes, the forecast model, gateway services; **row-level security** (`store_row_filter` on 10 tables, `store_access` mapping); least-privilege grants per service principal | `scripts/setup_row_level_security.sql`, `scripts/apply_store_access.py` | nb 02, evidence/02 |
| **Lakebase** | `lb_inventory_position`, `lb_open_purchase_orders`, `lb_delivery_exceptions`, `lb_product_demand`, `lb_demand_forecast`, `lb_store_daily_brief`; chat history, cache, activity feed; write-through on approval | `scripts/sync_gold_to_lakebase.py`, `apps/main-chat-app/` | nb 04, evidence/04, 12 |
| **ML** | Gradient-boosted demand forecaster, holdout-tested against two baselines, registered in UC, champion-gated, scored daily | `src/jobs/train_demand_forecast.py`, `score_demand_forecast.py` | nb 05 |
| **GenAI** | Invoice reading, morning briefs (with deterministic number check + retry) and prep plan through `kaapi_llm`; embeddings through `kaapi_embed`; weather tool through MCP service `kaapi_ops_advisor` | `apps/`, `src/jobs/store_daily_briefs.py` | nb 04, 06, evidence/11 |
| **Genie Agent** | One space, Agent mode, 21 tables + SOP PDF volume, config as code | `resources/genie_space.json`, `scripts/create_genie_agent.py` | nb 02, 03 |
| **Databricks App** | Store manager console: chat, Live Dashboard (brief + forecast), invoice check and approval, prep plan | `apps/main-chat-app/` | nb 04 |
| **Evaluation** | `mlflow.genai.evaluate` against the deployed app, scheduled daily as SP `kaapi-eval-runner`, appended to `eval_history` | `src/jobs/evaluate_app.py` | nb 07 |

Knowledge Assistant and Supervisor Agent (being deprecated) were replaced by one Genie Agent; the
legacy agents and notebooks were removed from the tree (they remain in git history).

---

## Repository layout

```
README.md                ← you are here
notebooks/               ← executed proof notebooks 01–07 (outputs committed) + proof_helpers.py
deck/FE_BAR_DECK.md      ← business presentation (10 slides: executive 1–5, architect 6–10)
DEMO.md · DEMO_SCRIPT.md ← demo script and one-page cue card
ROLEPLAY_PREP.md         ← opening, scene script, prepared answers for both personas
ARCHITECTURE.md          ← architecture and design decisions
febar.md                 ← submission checklist

databricks.yml           ← bundle root
resources/               ← pipeline, daily ops job, Genie space config
src/pipeline/            ← 01_bronze.sql · 02_silver.sql · 03_gold.sql
src/jobs/                ← forecaster train/score, store briefs, scheduled app evaluation
scripts/                 ← data + SOP generation, RLS setup, Lakebase sync, Genie config, eval set
apps/main-chat-app/      ← the store manager console (deployed)
apps/mcp-server/         ← operations-advisor MCP server behind the gateway MCP service
sample-invoices/         ← invoice PDFs for the demo
evidence/                ← point-in-time execution captures 01–12
```

---

## Deploy

Prerequisites: Databricks CLI authenticated, a Unity Catalog catalog, a SQL warehouse, and a
Lakebase instance named `kaapi-bricks`. Set your catalog in `databricks.yml` and in
`apps/main-chat-app/app.py` (`CATALOG_SCHEMA`).

```bash
# 1. Synthetic data + SOP PDFs into the raw volume
python scripts/generate_data.py --profile DEFAULT --warehouse-id <warehouse_id>

# 2. One-time: drop tables the pipeline will own; create app-write tables and row-level security
#    run scripts/drop_legacy_tables.sql, scripts/init_app_tables.sql, scripts/setup_row_level_security.sql
python scripts/apply_store_access.py --profile DEFAULT     # HQ (*) + store-manager mappings

# 3. Deploy the bundle (pipeline + daily ops job) and run the pipeline
databricks bundle deploy -t dev --profile DEFAULT
databricks bundle run kaapi_bricks_medallion -t dev --profile DEFAULT

# 4. Genie Agent from resources/genie_space.json
python scripts/create_genie_agent.py --profile DEFAULT

# 5. Apps, app service-principal grants, Lakebase roles
./deploy.sh DEFAULT <catalog> <warehouse_id>

# 6. Unity AI Gateway services, rate limits, payload logs, EXECUTE grants (exact JSON in evidence/11)
databricks ai-gateway create-model-service schemas/<catalog>.kaapi_bricks kaapi_llm   --json '…'  # Sonnet 4.6 → Haiku 4.5
databricks ai-gateway create-model-service schemas/<catalog>.kaapi_bricks kaapi_embed --json '…'  # BGE-large-en
databricks ai-gateway create-mcp-service   schemas/<catalog>.kaapi_bricks kaapi_ops_advisor \
  --json '{"config":{"source_connection":{"name":"connections/kaapi_ops_mcp"}}}'

# 7. Service principals for the store-manager demo and the scheduled evaluation:
#    kaapi-store-manager-str001, kaapi-eval-runner; OAuth secrets in secret scope `kaapi`
#    (keys store_mgr_client_id/secret, eval_client_id/secret); eval runner gets CAN_USE on the app.

# 8. Run the daily job once (forecast, briefs, Lakebase sync, evaluation); it then runs at 05:30 IST
databricks bundle run kaapi_daily_ops -t dev --profile DEFAULT

# 9. Re-execute the proof notebooks
jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb
```

---

## Business value (projected)

~₹2.2 crore (~$264,500) a year across the four capabilities, 3.9-month payback, 2.6× three-year ROI.
These are projections from labelled assumptions (`evidence/10`), not measured outcomes; the
recommended next step is a 6-week, 5-store pilot that measures them.

## Data

Fully synthetic, fictional company (Faker, seed=42): 37 stores · 28 products · 22 ingredients ·
8 suppliers · 15,000 customers · 200,000 orders · 2,000 purchase orders · 3,493 PO line items ·
171,163 inventory transactions · 6 SOP/training PDFs. Orders cover 2026-02-01 → 2026-05-14;
purchase orders and inventory 2026-02-01 → 2026-07-31.
