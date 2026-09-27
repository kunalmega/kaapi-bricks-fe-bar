# Kaapi Bricks — Architecture & Integrated Journey

> **Living document.** Updated as the build progresses. Legend:
> ✅ built & verified · 🟡 exists, needs rework · 🔴 to build · ⬜ planned

_Last updated: 2026-09-27 — all code complete. Blockers resolved: po_line_items added,
write-path conflict fixed (app_inventory_receipts / app_po_approvals), Lakebase sync script
created, evidence skeleton (01–10) and deck written. Awaiting: `databricks auth login` →
pipeline deploy + run → fill evidence files → push to GitHub._

## Repository layout (submission root)

```
FEbar_copy_bricks/            ← git root = the submission
  ARCHITECTURE.md             ← this file (living diagram)
  febar.md                    ← working plan + gap checklist
  README.md  DEMO.md  DEMO_SCRIPT.md
  databricks.yml              ✅ bundle root (catalog/schema vars, dev target)
  resources/                  ✅ kaapi_pipeline.pipeline.yml (serverless LDP)
  src/pipeline/               ✅ 01_bronze.sql · 02_silver.sql · 03_gold.sql (deploy pending)
  scripts/                    ✅ generate_data.py · drop_legacy_tables.sql · init_app_tables.sql
                                 sync_gold_to_lakebase.py · evals
  evidence/                   🟡 01–10 skeleton files (fill after pipeline runs)
  deck/                       ✅ FE_BAR_DECK.md (outcome-led, 10 sections, KPI math)
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
  │  UNITY CATALOG VOLUME  (raw landing zone)                            🟡 ready  │
  │  /Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/<entity>/*.parquet     │
  └───────────────────────────────────────┬───────────────────────────────────────┘
                                           │  Auto Loader (cloudFiles)
                                           ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  LAKEFLOW  ·  Spark Declarative Pipeline (serverless)          🟡 CODE READY  │
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
| 1 | **Lakeflow** | 🟡 code ✅, deploy pending | 14 bronze (Auto Loader) + 14 silver (expectations) + 7 gold; `po_line_items` added; `databricks.yml` + bundle resource |
| 2 | **Unity Catalog** | ✅ / 🟡 lineage after run | catalog `fevm_cme_conde_catalog`, schema `kaapi_bricks`, comments on all tables; lineage visible after pipeline runs |
| 3 | **Lakebase** | ✅ code complete | `scripts/sync_gold_to_lakebase.py` syncs 4 gold tables; `GET /api/lakebase/inventory/{store_id}` reads `lb_inventory_position`; chat memory + QA cache also live |
| 4 | **ML / GenAI** | ✅ | KA + MAS + `ai_parse_document` + MLflow eval notebooks (outputs needed after run) |
| 5 | **Genie** | ✅ | `scripts/create_agents.py`; pointed at silver + gold |
| 6 | **Databricks App** | ✅ | `apps/main-chat-app` + 3 more; write-path conflict resolved |

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
