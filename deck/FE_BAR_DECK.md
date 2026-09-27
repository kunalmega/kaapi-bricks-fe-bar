# Kaapi Bricks Intelligent Store Operations
## Powered by Databricks

*FE Bar Submission Deck — Kaapi Bricks (fictional 37-store South Indian filter-coffee chain)*  
*Industry: Multi-location food service and specialty retail*

---

## Slide 1: The Outcome in One Sentence

**Before Databricks:** A store manager spends 30 minutes per delivery cross-checking a supplier invoice against a purchase order — across 37 stores, that is 30+ manager-hours lost every single day.

**After Databricks:** The same reconciliation takes seconds. Every discrepancy is flagged. Every inventory record is updated. The manager approves with one click.

**Annual value: ~₹2.2 crore (~$264,000) across 37 stores.**

---

## Slide 2: Customer and Industry Context

**Kaapi Bricks** operates 37 stores across India, Dubai, Singapore, London, San Francisco, and Sydney. The brand specializes in South Indian filter coffee — from classic tumbler-davara Degree Coffee to specialty cold brews.

**Why this industry is hard:**

- **Perishable ingredients** — full cream milk (25 litres/day/store), cardamom, fresh coconut. Over-order and you waste. Under-order and you lose the morning rush.
- **8 active suppliers**, each with their own lead times, pricing schedules, and delivery reliability.
- **Weather and festivals matter** — a Navratri long weekend in Bangalore drives 20% more footfall. A rainy morning shifts orders from cold brew to hot filter coffee.
- **37 stores, 2 deliveries/day each** — 74 invoices per day arriving on paper or as PDFs. No two invoices look the same.

**The store manager is the most information-dense role in the company** — and today they operate with no real-time data, no AI assistance, and no time.

---

## Slide 3: The Specific Problem — Three Pain Points

### Pain Point 1: Invoice Reconciliation (30 min × 74 invoices/day)
Priya, the Koramangala store manager, receives a paper invoice from Coorg Coffee Estates. She must:
1. Open the PO system and find PO-01288.
2. Compare 8 line items manually — quantities, units, prices, GST codes.
3. Note any discrepancies (price increase? extra items not in PO?).
4. Call accounts payable. Wait. Get approval. File.

**Today this takes 25–30 minutes per delivery.** Across 37 stores: **1,850 manager-minutes lost every day.**

### Pain Point 2: Inventory Blindness
Priya doesn't know her current stock of Coorg Arabica until she physically counts it. By the time she realizes she's low, the reorder lead time (7 days from Coorg) means she'll run short. **3.5% of store-days have a critical stockout** — that's ₹20 lakhs/year in lost revenue.

### Pain Point 3: No Contextual Demand Preparation
Tomorrow is a holiday. There's a corporate campus nearby. Rain is forecast. None of this context reaches Priya's preparation plan — she uses last week's numbers and her intuition.

---

## Slide 4: Proposed Business Outcomes and KPI Targets

| KPI | Current Baseline | 12-Month Target |
|---|---|---|
| Invoice reconciliation time | 25–30 min/delivery | < 2 min/delivery |
| Invoice exception rate (missed discrepancies) | ~12% | < 3% |
| Stockout rate (% of store-days) | 3.5% | < 1.5% |
| Ingredient waste rate | ~4% of cost | < 3% |
| Supplier on-time delivery rate | ~78% | > 92% |
| Manager time on data gathering | ~45 min/day | < 5 min/day |
| Genie answer latency | N/A (manual) | < 5 seconds |

**Projected annual value: ₹2.2 crore (~$264,500/year)**  
**Payback period: ~3.6 months**

---

## Slide 5: The Solution Journey (Live Demo Flow)

*Tell → Show → Tell structure*

### Scene 1 — Morning Questions (TELL)
*"Priya opens the store at 7am. She has three questions. She asks them in plain English."*

**SHOW:** Main chat app → "What's our best-selling drink this month?" → Classic Filter Coffee, 1,483 units. "How do I make a Classic Filter Coffee?" → barista recipe from the training manual. "How should I prepare for tomorrow?" → weather + holiday + demand context from three different agents.

*"Three questions. Three different AI systems answered. Priya didn't know which one. She just asked."*

### Scene 2 — The Delivery (TELL)
*"A truck pulls up from Coorg Coffee Estates. Priya has a paper invoice. Eight line items. GST breakups. Batch numbers."*

**SHOW:** Upload invoice PDF → `ai_parse_document` extracts every line item → matches PO-01288 → flags 3 discrepancies (overdelivery on Arabica, price increase on Chicory, 3 unauthorized items) → Priya clicks "Approve" → inventory updated, PO marked delivered.

*"30 minutes. Now seconds. And every discrepancy is on record."*

### Scene 3 — Under the Hood (TELL)
*"How do we know it's correct?"*

**SHOW:** MLflow trace → every agent call, every tool invocation, every token. Evaluation dashboard → Correctness, Safety, RelevanceToQuery, RetrievalGroundedness. One failed case: wrong decoction ratio caught by the evaluator.

*"We measure it. When something fails, our baristas review it, label it, and the agent gets better."*

---

## Slide 6: Architecture and Integrated Data Flow

```
SYNTHETIC RETAIL DATA (generate_data.py)
  37 stores · 28 products · 15k customers · 200k orders · 2k POs
    │
    ▼ Parquet per entity
UNITY CATALOG VOLUME  /Volumes/.../kaapi_bricks/raw_data/<entity>/
    │
    ▼ Auto Loader (STREAM read_files)
LAKEFLOW PIPELINE  kaapi_bricks_medallion  [serverless, declarative]
  ├── Bronze (13 streaming tables) — raw + ingest metadata
  ├── Silver (14 MV) — conformed, typed, expectations, deduped
  └── Gold (7 MV) — operational KPIs, inventory position, open POs,
                    delivery exceptions, product demand, supplier performance
    │
    ├─► UNITY CATALOG — governed tables, column comments, lineage, grants
    │
    ├─► LAKEBASE (Postgres) — 4 operational gold tables synced
    │     lb_inventory_position, lb_open_purchase_orders,
    │     lb_delivery_exceptions, lb_product_demand
    │
    ├─► GENIE SPACE — natural-language analytics over silver + gold
    │
    └─► ML / GenAI
          Knowledge Assistant (KA) — RAG over barista/ops documents
          Multi-Agent Supervisor (MAS) — routes KA / Genie / Ops Advisor
          ai_parse_document — native SQL invoice parsing
          MLflow evaluation — Correctness, Safety, Groundedness, Relevance
    │
    ▼
DATABRICKS APP — Kaapi Bricks Store Manager Console
  main-chat-app · growth-advisor · promo-agent · mcp-server
```

Every entity key (store_id, ingredient_id, po_id) flows from raw → bronze → silver → gold → app without transformation breaks. The same `po_id = 'PO-01234'` can be traced through every layer.

---

## Slide 7: Governance, Security, and Data Quality

### Unity Catalog Governance
- All tables in `fevm_cme_conde_catalog.kaapi_bricks` with column-level comments.
- Service principal access via least-privilege grants (`USE CATALOG`, `SELECT` on specific tables).
- Full lineage registered: raw Parquet → bronze streaming table → silver MV → gold MV.
- Lineage visible in UC UI: "Who reads `gold_inventory_position`?" — the app and Genie.

### Data Quality (44 Expectations in Silver)
- **DROP ROW** constraints on primary keys, required foreign keys, non-negative totals.
- **WARN** constraints on referential integrity and business rules (e.g. `cost ≤ base_price`).
- Clean synthetic data: 0 rows expected to drop on first run. Constraints protect against future dirty ingest.

### App-Write Separation
- Silver materialized views are pipeline-managed (read-only).
- Invoice approvals write to separate `app_inventory_receipts` and `app_po_approvals` Delta tables.
- Gold views UNION both sources — deterministic calculation, LLM only explains the result.

### Security
- No real customer data. 100% synthetic (Faker, seed=42).
- No hardcoded credentials in codebase. Lakebase uses OAuth token rotation.
- Databricks App identity / user_api_scopes controls what users can query.

---

## Slide 8: AI Grounding, Evaluation, and Human Controls

### How the AI is Grounded
- **Knowledge Assistant:** retrieves from PDF training documents (barista manual, food safety policy, supplier SOPs). Answers are grounded in retrieved chunks, not model memory.
- **Genie Space:** generates SQL over certified gold/silver tables. SQL is visible, auditable, and executed against real data — not inferred.
- **Operations Advisor:** uses deterministic data (gold inventory position, weather API) as inputs; model only synthesizes the narrative.

### Evaluation Loop (MLflow)
```
Test dataset (10 KA queries + 5 MAS routing tests)
  → mlflow.genai.evaluate()
  → Scorers: Correctness, Safety, RelevanceToQuery, RetrievalGroundedness
  → Failed cases flagged → SME labelling session → evaluation dataset improved
  → Re-evaluate → scores trend upward
```

### Where Humans Stay in the Loop
- **Invoice approval** is always a human action — the app flags discrepancies, Priya decides.
- **Model promotion** requires running an evaluation set and comparing scores — not auto-promoted.
- **Guardrails:** off-topic questions (e.g. financial forecasts) are deflected to the appropriate channel.
- **MLflow traces** — every question, every agent decision, every API call logged. Auditable in production.

### Trade-off: Genie vs Custom SQL Tools
- **Chose Genie:** Faster to build, governed table access, natural-language SQL is transparent to users.
- **Trade-off:** Genie occasionally generates suboptimal SQL for complex aggregations. Mitigated with certified metric views and Genie instructions.
- **Alternative considered:** Custom LangGraph agent with pre-built SQL tools — more controllable, 2× build time.

### Trade-off: Lakebase vs Delta for Serving
- **Delta (warehouse):** great for heavy analytical scans, ~500ms–2s cold start.
- **Lakebase (Postgres):** OLTP latency (~10–50ms), suitable for point-lookups in the app (current inventory for one store).
- **Decision:** Gold aggregates (inventory position, open POs) synced to Lakebase for the app. Heavy queries (trend analysis, multi-store revenue) stay on Delta/Genie.

---

## Slide 9: Expected Value and Assumptions

| Value driver | Annual (₹) | Annual ($) | Key assumption |
|---|---|---|---|
| Invoice reconciliation labor | ₹89,93,600 | $107,000 | 25 min saved/delivery, ₹800/hr loaded cost |
| Invoice leakage prevention | ₹90,75,360 | $108,000 | 12% exception rate, ₹2,800 avg slip-through |
| Stockout reduction | ₹11,91,960 | $14,200 | 60% reduction in 3.5% baseline stockout rate |
| Waste reduction | ₹2,59,000 | $3,100 | 25% reduction in ₹28k/store/year waste |
| Manager time (Genie queries) | ₹27,07,200 | $32,200 | 15 min/day saved × 37 stores |
| **Total annual value** | **₹2,22,27,120** | **~$264,500** | |
| Platform cost (est.) | — | $60,000/year | Serverless + apps + FMAPI at demo scale |
| Payback period | — | ~3.6 months | |
| 3-year ROI | — | 5.7× | Net of platform cost |

*All assumptions labeled. Replace with actual Kaapi Bricks operational data before a live business case.*

---

## Slide 10: Pilot Plan, Risks, and Next Steps

### Recommended Pilot (5 stores, 6 weeks)

**Week 1–2 — Data foundation**
- Deploy pipeline, land synthetic data, validate bronze/silver/gold row counts.
- Connect Genie Space; confirm 5 demo questions return correct answers.

**Week 3–4 — App + Lakebase live**
- Deploy main-chat-app to 5 pilot stores.
- Sync gold tables to Lakebase; confirm latency < 50ms.
- Train 5 store managers on invoice upload and approval workflow.

**Week 5–6 — Measure and evaluate**
- Run KA + MAS evaluation; target Correctness ≥ 0.80.
- Measure invoice reconciliation time (stopwatch, 10 deliveries per store).
- Capture actual stockout events vs baseline.
- Collect manager NPS.

**Go/no-go criteria:** ≥ 50% time reduction on invoice reconciliation; ≥ 0 critical stockouts from proactive reorder alerts; KA Correctness ≥ 0.80.

### Key Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Lakeflow pipeline fails on first run (auth, volume path) | Medium | Tested locally via `bundle validate`; run `generate_data.py` first to land raw files |
| ai_parse_document accuracy on non-standard invoices | Medium | Fallback LLM vision parsing already coded; flag low-confidence parses for human review |
| Genie generates wrong SQL for complex aggregations | Low-medium | Certified metric views + Genie instructions constrain query scope |
| Store managers resist new workflow | Low | App is chat-first, not dashboard; invoice upload takes < 60 seconds |
| Lakebase Postgres latency spikes | Low | Connection pooling + token refresh logic already in app; fallback to Delta SQL warehouse |

### Next Steps
1. `databricks auth login --profile DEFAULT`
2. `python scripts/generate_data.py --profile DEFAULT`
3. `databricks bundle deploy -t dev --profile DEFAULT`
4. `databricks bundle run kaapi_bricks_medallion -t dev --profile DEFAULT`
5. Fill in `evidence/01_lakeflow_run.txt` with real pipeline output.
6. `python scripts/sync_gold_to_lakebase.py --profile DEFAULT`
7. Deploy app; run `evidence/07_app_health_and_api_tests.txt` curls.
8. Run eval notebooks; fill in `evidence/09_mlflow_evaluation_results.md`.
9. Push to public GitHub repo.
10. Submit via the FE Bar form.

---

*Kaapi Bricks is a fictional company. All data is synthetic (Faker library, seed=42). No real customer data, no real product names, no hardcoded credentials.*
