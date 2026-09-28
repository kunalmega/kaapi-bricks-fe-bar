# Kaapi Bricks — Architecture and Design Decisions

Current, deployed architecture. Every status below is backed by a file in `evidence/`.

## The one-line story

A Kaapi Bricks store manager (fictional 37-store filter-coffee chain) uses one governed assistant
to check supplier invoices against POs, see current inventory and late deliveries, and get answers
from both company data and company SOPs.

## End-to-end journey

```
  SYNTHETIC DATA  scripts/generate_data.py (Faker, seed=42)
  37 stores · 200k orders · 2k POs · 3.5k PO lines · 171k inventory txns · 6 SOP PDFs
        │  Parquet, one folder per entity
        ▼
  UNITY CATALOG VOLUME  raw_data/<entity>/            (+ raw_data/ka_documents/*.pdf)
        │  Auto Loader: STREAM read_files
        ▼
  LAKEFLOW  kaapi_bricks_medallion  (serverless, triggered)          evidence/01, 03
    BRONZE  14 streaming tables       raw + _source_file + _ingested_at
    SILVER  14 materialized views     typed, deduped, 45 expectations (45/45 passed)
    GOLD     7 materialized views     inventory position · open POs · delivery exceptions ·
                                      product demand · supplier performance · waste · store KPIs
        │
        ├──► UNITY CATALOG governance: comments, lineage, app SP grants    evidence/02
        │
        ├──► LAKEBASE (Postgres)  scripts/sync_gold_to_lakebase.py         evidence/04
        │      lb_inventory_position (814) · lb_open_purchase_orders (147)
        │      lb_delivery_exceptions (339) · lb_product_demand (6,324, last 7 days)
        │      + kaapi_mcp.* chat history, feedback, semantic answer cache
        │
        └──► GENIE AGENT  resources/genie_space.json                       evidence/05, 09
               21 silver + gold tables  +  SOP/recipe PDF volume
               called via Agent mode: POST /api/2.0/genie/agents/{id}/responses (SSE)
        │
        ▼
  DATABRICKS APP  apps/main-chat-app  (FastAPI + React)                    evidence/07
    chat panel       → semantic cache (Lakebase) → Genie Agent mode
    inventory panel  → GET /api/lakebase/inventory/{store} → Lakebase
    invoice upload   → ai_parse_document + LLM extraction → PO + po_line_items match
                     → human approval → app_inventory_receipts / app_po_approvals (Delta)
        │
        ▼
  MLFLOW  scripts/run_genie_evaluation.py → mlflow.genai.evaluate           evidence/09
    Correctness · RelevanceToQuery · Safety on 10 store-manager questions
```

## Layer status

| # | Layer | Status | Evidence |
|---|---|---|---|
| 1 | Lakeflow | ✅ Ran: update 065d6a70, 14 + 14 + 7 datasets, ~61 s serverless | 01, 03 |
| 2 | Unity Catalog | ✅ Governed schema, volumes, comments, lineage, SP grants | 02 |
| 3 | Lakebase | ✅ 4 serving tables synced; app inventory panel reads Lakebase (HTTP 200, `source: lakebase`) | 04, 07 |
| 4 | ML / GenAI | ✅ Invoice parsing; ✅ MLflow evaluation measured (latest scores in 09) | 06, 09 |
| 5 | Genie Agent | ✅ Agent mode, tables + documents | 05, 09 |
| 6 | Databricks App | ✅ Deployed and ACTIVE | 07 |

## Design decisions (and the trade-offs to defend)

- **One Genie Agent instead of Knowledge Assistant + Supervisor Agent.** KA and SA are being
  deprecated in favour of Genie Agents. One agent now answers table questions (SQL) and document
  questions (PDF volume). This removed a routing layer and two endpoints.
- **Agent mode API, not Chat mode.** The Chat-mode conversation API only queries tables. Our
  first evaluation scored Correctness 0.00 because every SOP question was declined. Agent mode
  reads the attached volume and cites the file. Cost: ~23 s per document answer versus a few
  seconds, because Agent mode reasons over several steps.
- **Semantic answer cache in Lakebase.** Repeat questions (SOPs change rarely) are answered from
  `kaapi_mcp.qa_cache` by exact match, then embedding similarity ≥ 0.95, with a 48-hour TTL.
  This hides Agent mode latency for common questions.
- **Silver keeps plain business names** (`orders`, `purchase_orders`, …), so Genie and the app
  query the pipeline-owned tables with no renaming. Bronze is prefixed `bronze_`, gold `gold_`.
- **Deterministic gold, LLM on top.** Inventory position, open POs, and delivery exceptions are
  SQL in gold. The LLM explains and summarizes; it does not compute the numbers.
- **App writes are separate from pipeline tables.** Silver and gold are pipeline-owned and
  read-only. Invoice approvals write to `app_inventory_receipts` and `app_po_approvals`; gold
  unions them in, so an approval shows up after the next pipeline refresh.
- **Lakebase vs Delta for serving.** Small per-store point lookups go to Lakebase; multi-store
  analytics stays on Delta through Genie.
- **Lakebase sync is a snapshot script.** `sync_gold_to_lakebase.py` truncates and reloads after
  each pipeline run. Simple and correct for a demo. In production: schedule it as a job task after
  the pipeline, or use Lakebase synced tables.

## Known limits (stated, not hidden)

- Lakebase data is only as fresh as the last pipeline run + sync. An approved invoice is not
  visible in the inventory panel until then.
- Agent mode latency (~23 s) on uncached document questions.
- Evaluation Correctness is below target (see `evidence/09` for the latest iteration and the
  failure analysis).
- `MODIFY` is granted at schema level to the app service principal; production should narrow it
  to the two app-write tables.
- The operations-advisor MCP server (`apps/mcp-server`) is deployed but not called by the
  current chat flow; its previous caller was the retired Supervisor Agent.
