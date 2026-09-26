# Kaapi Bricks — Architecture & Integrated Journey

> **Living document.** Updated as the build progresses. Legend:
> ✅ built & verified · 🟡 exists, needs rework · 🔴 to build · ⬜ planned

_Last updated: 2026-09-26 — repo flattened so the project is the repo root; scaffold dirs created._

## Repository layout (submission root)

```
FEbar_copy_bricks/            ← git root = the submission
  ARCHITECTURE.md             ← this file (living diagram)
  febar.md                    ← working plan + gap checklist
  README.md  DEMO.md  DEMO_SCRIPT.md
  databricks.yml              🔴 bundle root (to create)
  resources/                  🔴 pipeline + job definitions
  src/pipeline/               🔴 bronze / silver / gold declarative code
  scripts/                    ✅ generate_data.py, create_agents.py, evals …
  apps/                       ✅ main-chat-app, growth-advisor-agent, promo-agent, mcp-server
  sample-invoices/            ✅ PDFs for the doc-AI demo
  evidence/                   🔴 committed text execution evidence
  deck/                       🔴 business presentation
```

---

## The one-line story

A store manager for **Kaapi Bricks** (fictional 37-store South-Indian filter-coffee chain)
asks one governed assistant to prep daily demand, catch supplier-invoice discrepancies, and
avoid stockouts — replacing a ~30-minute manual cross-check with a few seconds.

---

## Integrated journey (target state)

```
                          KAAPI BRICKS — END-TO-END DATA JOURNEY

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  SYNTHETIC DATA GENERATION                                            ✅       │
  │  scripts/generate_data.py  (Faker, seed=42)                                   │
  │  37 stores · 28 products · 15k customers · 200k orders · 2k POs · inventory   │
  └───────────────────────────────────────┬───────────────────────────────────────┘
                                           │  writes raw Parquet (one dir per entity)
                                           ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  UNITY CATALOG VOLUME  (raw landing zone)                            🟡→🔴     │
  │  /Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/<entity>/*.parquet     │
  └───────────────────────────────────────┬───────────────────────────────────────┘
                                           │  Auto Loader (cloudFiles)
                                           ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  LAKEFLOW  ·  Spark Declarative Pipeline (serverless)               🔴 BUILD  │
  │                                                                               │
  │   BRONZE  (streaming tables, raw + ingest metadata)                           │
  │     bronze_stores  bronze_products  bronze_customers  bronze_orders  …(13)    │
  │            │  expectations: type-cast, not-null keys, valid ranges            │
  │            ▼                                                                   │
  │   SILVER  (conformed, deduped, referential-integrity checks)                  │
  │     stores  products  customers  orders  order_items  purchase_orders  …(13)  │
  │            │  aggregate + business logic                                      │
  │            ▼                                                                   │
  │   GOLD  (operational + KPI tables)                                            │
  │     gold_store_daily_kpis      gold_inventory_position                        │
  │     gold_open_purchase_orders  gold_delivery_exceptions                       │
  │     gold_product_demand        gold_supplier_performance  gold_waste_summary  │
  └───────────────────────────────────────┬───────────────────────────────────────┘
                                           │
        ┌──────────────────────────────────┼───────────────────────────────────┐
        ▼                                  ▼                                     ▼
  ┌───────────────┐            ┌──────────────────────┐            ┌────────────────────┐
  │ UNITY CATALOG │            │ LAKEBASE (Postgres)  │            │  ML / GenAI         │
  │ governance ✅ │            │ operational serving  │            │                     │
  │ • comments    │            │ 🟡 memory→🔴 ops     │            │ • Knowledge Asst ✅ │
  │ • grants      │            │ synced gold tables:  │            │ • Multi-Agent Sup ✅│
  │ • lineage 🔴  │            │  inventory_position  │            │ • ai_parse_document │
  │  (bronze→gold)│            │  open_pos            │            │   invoice parse  ✅ │
  └───────┬───────┘            │  delivery_exceptions │            │ • MLflow eval    🟡 │
          │                    │  product_demand      │            │   (needs outputs)   │
          │                    └──────────┬───────────┘            └─────────┬──────────┘
          ▼                               │                                  │
  ┌───────────────┐                       │                                  │
  │ GENIE SPACE ✅│                       │                                  │
  │ NL analytics  │                       │                                  │
  │ over silver + │                       │                                  │
  │ gold tables   │                       │                                  │
  └───────┬───────┘                       │                                  │
          │                               │                                  │
          └───────────────┬───────────────┴──────────────────┬───────────────┘
                          ▼                                   ▼
              ┌───────────────────────────────────────────────────────────┐
              │  DATABRICKS APP — Store Manager Console          ✅         │
              │  apps/main-chat-app  (+ growth-advisor, promo, mcp-server)  │
              │  • reads operational views from Lakebase (OLTP latency)     │
              │  • routes questions to MAS → KA / Genie / Ops Advisor       │
              │  • invoice upload → ai_parse_document → PO discrepancy check │
              └───────────────────────────────────────────────────────────┘
```

---

## Layer status (FE Bar mandatory 6)

| # | Layer | Status | Where (paths are repo-root relative) |
|---|-------|--------|--------------------------------------|
| 1 | **Lakeflow** | 🔴 to build | `databricks.yml`, `resources/kaapi_pipeline.pipeline.yml`, `src/pipeline/0{1,2,3}_*.py` (see `LAKEFLOW_PLAN.md`) |
| 2 | **Unity Catalog** | ✅ / 🔴 lineage | `scripts/generate_data.py`; pipeline adds layered lineage + comments |
| 3 | **Lakebase** | 🟡 → 🔴 | today: chat memory/cache in `apps/main-chat-app/app.py`. Add: `scripts/sync_gold_to_lakebase.py` + app reads gold |
| 4 | **ML / GenAI** | ✅ | KA + MAS + `ai_parse_document` + `scripts/run_{ka,mas}_evaluation.ipynb` |
| 5 | **Genie** | ✅ | `scripts/create_agents.py`; repoint at silver+gold |
| 6 | **Databricks App** | ✅ | `apps/main-chat-app` + 3 more |

---

## Key design decisions (rationale for the roleplay)

- **Silver tables keep the plain business names** (`orders`, `customers`, …) that the Genie
  Space, MAS, and app already query — so the medallion slots in underneath with zero
  downstream rewrites. Bronze is prefixed `bronze_`, gold is prefixed `gold_`.
- **Lakebase vs Delta for serving:** aggregated *gold* operational tables (small, hot,
  point-lookups by store) are synced to Lakebase for OLTP-latency app reads; heavy
  analytical scans stay on Delta/Genie. (This is a rehearsable trade-off.)
- **Deterministic gold + LLM on top:** inventory position, open POs, and delivery
  exceptions are deterministic SQL in gold (auditable); the LLM layer *explains and
  recommends*, it doesn't compute the numbers.
- **`inference_logs`** stays app-managed (observability), outside the medallion.

---

## Open items feeding this diagram
- [ ] Confirm target catalog/schema stays `fevm_cme_conde_catalog.kaapi_bricks` (or a public-safe rename before push)
- [ ] Decide Lakebase sync mechanism (synced tables vs scheduled write) — see `LAKEFLOW_PLAN.md`
- [ ] Wire lineage evidence capture (`evidence/02_uc_tables_and_lineage.md`)
