# Kaapi Bricks: One Place to Run Every Store
## Store operations on the Databricks Data Intelligence Platform

*FE Bar submission deck · Kaapi Bricks, a fictional 37-store South Indian filter-coffee chain ·
Retail & Consumer Goods (restaurants / quick-service)*

> **How to read this deck.**
> - Each slide title is the message; the body is the proof.
> - **Slides 1–5 are for the executive** (outcome, problem, solution, value, plan).
> - **Slides 6–10 are for the technical architect** (architecture, governance, AI quality, trade-offs, risks).
> - Every system number is **measured** and links to a file in `evidence/`.
> - Every business number is a **projection from a labelled assumption** *[assumption]*.

---

## Slide 1 · Store managers spend their day finding information. We give them one place to run the store.

**The situation.** Each of Kaapi Bricks' 37 store managers makes the same decisions every day:
how much to prepare, what to reorder, whether a delivery is right, and how to answer a barista's
question. The information for those decisions is spread across five or six disconnected tools.

**What we built.** One store-operations app on one governed copy of the data. The manager can:

| | Instead of | Now | Business impact |
|---|---|---|---|
| **Ask** | opening dashboards, spreadsheets and PDFs | asking in plain language about sales, stock, suppliers or recipes | answers in seconds; decisions on data, not memory |
| **See** | counting stock and chasing suppliers | a live store dashboard of stock cover, overdue orders and late deliveries | problems spotted days earlier; fewer stockouts |
| **Act** | checking invoices line by line on paper | uploading the invoice and approving the discrepancies the app flags; stock updates instantly | 25–30 min → under 2 min per delivery; leakage stopped |
| **Plan** | gut feel and a weather app | a daily preparation plan from the store's own history plus today's weather and holidays | less waste; ready for the rush |

**The ask.** A 6-week pilot in 5 stores to replace our assumptions with measured baselines.

**Projected value:** ~$264,500 (₹2.2 crore) a year, **3.9-month payback** *[assumption-based, Slide 4]*.

> **Say:** "This isn't an invoice tool or a chatbot. It's the operating system for the store
> manager: ask, see, act and plan in one place, on data HQ also trusts."

---

## Slide 2 · The problem isn't one task. It's that every decision needs five systems.

**A manager's morning today**

| Question | Where they look | What goes wrong |
|---|---|---|
| "What sold last Tuesday? What will sell today?" | Sales dashboard / POS reports | Separate tool, not connected to stock or weather |
| "What's running low?" | Spreadsheet or a physical count | Found too late: **27 store-ingredient positions are below reorder level right now** (evidence/05) |
| "Where's my delivery?" | Supplier emails, PO system, phone | Suppliers deliver on time only **80.5–86.4%** of the time (measured, evidence/05) |
| "Is this invoice right?" | Paper invoice next to the PO | 25–30 min per delivery; errors get paid *[assumption]* |
| "How long can decoction be kept? Allergen rule?" | Six SOP and training PDFs | New staff interrupt the manager |

**Why it's hard in this business**
- **Perishables:** milk, cardamom and coconut milk. Over-order and you waste; under-order and you miss the morning rush.
- **Demand moves:** weather and festivals shift hot vs cold drinks.
- **Scale:** 37 stores in 8 countries, 8 suppliers and ~74 deliveries a day, each store working its own way.

**The cost of fragmentation**
- ~45 min per manager per day spent gathering data *[assumption]*.
- Invoice leakage, stockouts and waste.
- HQ has no consistent view of how stores are run.

> **Say:** "Your managers are the most information-dense role in the company, and they're working
> from paper, spreadsheets and memory."

---

## Slide 3 · Four capabilities, each removing a different cost from the business

*All four run on one platform: Lakeflow builds the data, Unity Catalog governs it, Lakebase
serves it, Genie and the Unity AI Gateway put AI on it, and MLflow measures it.*

### 1 · ASK: any store question answered in seconds, in plain language

| | |
|---|---|
| **Before** | Open the sales dashboard, the stock sheet, supplier emails and the SOP PDFs, or call HQ. It takes minutes to hours, so it's often skipped and decided from memory |
| **After** | *"Which ingredients are below reorder at my store?" · "Which supplier is late most often?" · "How long can decoction be kept?"* One chat answers from 21 governed business tables **and** 6 SOP documents |
| **Business impact** | Decisions made on data, not memory. ~15 min a day back per manager *[assumption]*. New baristas look up recipes and allergen rules themselves, so procedures stay consistent across 37 stores |
| **Measured** | 27 below-reorder positions answered with SQL (evidence/05). SOP answer with a cited source (evidence/07). Repeat questions in **1.1 s** (evidence/11) |
| **Databricks behind it** | **Genie Agent mode** writes SQL over **Unity Catalog** tables and reads the SOP PDFs in a UC Volume. **Lakebase** stores chat history and a semantic answer cache. Cache embeddings go through **Unity AI Gateway** |

### 2 · SEE: a live dashboard for each store

| | |
|---|---|
| **Before** | Stock is known only after a physical count. An overdue order is noticed when the shelf is empty. HQ reports are a day old |
| **After** | One screen per store, refreshed every 10 s: items below reorder, days of stock cover per ingredient, overdue POs with days late and value, late deliveries, units sold, and a live activity feed |
| **Business impact** | Problems are visible days before they hit the counter. The manager chases the supplier **before** the morning-rush stockout (target 3.5% → < 1.5% of store-days). Money tied up in late orders is visible: Koramangala showed **8 overdue POs worth ₹31,065** (evidence/12) |
| **Measured** | Whole dashboard in **23–37 ms**. Stock changes on screen within one refresh after an invoice is approved (evidence/12) |
| **Databricks behind it** | **Lakeflow** builds the gold inventory, PO and delivery views, with 45 data-quality checks. **Lakebase** serves them per store in milliseconds and takes live writes. **Databricks Apps** hosts the screen, with no extra infrastructure |

### 3 · ACT: invoice checked in seconds, the manager approves

| | |
|---|---|
| **Before** | Compare the paper invoice line by line against the PO: 25–30 min per delivery, ~74 deliveries a day, with ~12% of discrepancies paid anyway *[assumption]* |
| **After** | Upload the invoice. The app extracts the lines, matches them to the PO, and flags price changes, wrong quantities, extra items and missing deliveries. The manager approves, and stock and the PO update at once |
| **Business impact** | The largest cash line: manager time ($107k) plus leakage stopped ($108k) *[assumption]*. Suppliers are held to the PO price. Every decision is on record for audit |
| **Measured** | **All 4** planted discrepancies caught and the control line matched, in **18.4 s** (evidence/11) |
| **Databricks behind it** | **Claude through Unity AI Gateway** reads the PDF: permissioned, rate-limited and logged. Matching is deterministic code. The approval is written to **Delta** (system of record) and through to **Lakebase**, so the dashboard updates. The invoice is stored in a **UC Volume** |

### 4 · PLAN: a preparation plan for today, not gut feel

| | |
|---|---|
| **Before** | Prep is based on experience and a weather app. Over-prepare and milk is thrown away; under-prepare and the rush runs out |
| **After** | *"How should I prepare for today?"* returns a per-drink plan. It uses the store's own same-weekday history, current stock and overdue POs, live weather and upcoming holidays |
| **Business impact** | Less perishable waste and fewer stockouts on busy days. New managers plan as well as experienced ones |
| **Measured** | Captured plan: *Tuesday, thunderstorm, 21 mm. Filter Coffee typical 12.1 → forecast 14–15; Cold Coffee 3.6 → 2–3*. The baseline matches an independent SQL check (evidence/11, 06) |
| **Databricks behind it** | Demand history from **gold Delta** tables (SQL). Stock and POs from **Lakebase**. Weather and holidays from an **MCP service on Unity AI Gateway**. The plan is written by Claude through the gateway, and **MLflow** traces every step |

### Together: one source of truth

The manager stops switching between tools. HQ and every store see the same numbers. Every AI
answer is governed and measured.

**Two rules the business can rely on**
1. **Numbers come from data, words come from AI.** Stock, prices and baselines are computed in SQL; the AI explains them and adds context.
2. **The manager decides.** The app flags and recommends; approvals are always a human action, and every one is recorded.

> **Say:** "Ask, see, act, plan. Each one removes a different cost: time, stockouts, invoice
> leakage, waste. And all four sit on one pipeline, one catalog and one set of permissions."

---

## Slide 4 · ~$264k a year across all four capabilities, 3.9-month payback, every assumption visible

*Projections from stated assumptions. No measured customer outcome yet; the pilot replaces them.*

| Capability | Value driver | Annual ($) | Key assumption |
|---|---|---:|---|
| **Ask + See** | Manager time gathering data: 15 min saved per day | $32,200 | 37 managers, ₹800/hr loaded cost |
| **See + Plan** | Fewer stockouts | $14,200 | 60% fewer, on a 3.5% store-day baseline |
| **Plan** | Less perishable waste | $3,100 | 25% less, on ₹28k/store/year |
| **Act** | Invoice-check time: 25 min saved per delivery | $107,000 | 2 deliveries/store/day, ₹800/hr |
| **Act** | Invoice leakage stopped | $108,000 | 12% exception rate, ₹2,800 average slip-through |
| | **Total** | **~$264,500 (₹2.2 crore)** | |

| | |
|---|---|
| Platform cost | $50,000 / year (serverless pipeline, Lakebase, model APIs, app) |
| Implementation | $70,000 one-time (8 weeks, including training) |
| **Simple payback** | $70,000 ÷ ($264,500 − $50,000) × 12 = **3.9 months** |
| **3-year net ROI** | ($793,500 − $220,000) ÷ $220,000 = **2.6×** |

**KPI targets (12 months)**

| KPI | Capability | Today | Target |
|---|---|---|---|
| Manager time gathering data | Ask + See | ~45 min/day | < 5 min/day |
| Stockouts (% of store-days) | See + Plan | 3.5% | < 1.5% |
| Perishable waste (% of cost) | Plan | ~4% | < 3% |
| Invoice check time | Act | 25–30 min | < 2 min |
| Missed invoice errors | Act | ~12% | < 3% |
| Supplier on-time delivery | See (supplier scorecard) | 80.5–86.4% (measured) | > 92% |

**What's not in the number**
- Consistent recipes and allergen handling across 37 stores.
- HQ visibility into every store.
- A supplier scorecard to negotiate with.
- New use cases at low marginal cost, because they reuse the same platform.

> **Say:** "Invoices are the biggest cash line, but the daily habit is Ask and See: that's what
> managers open every morning. The platform is shared, so each new workflow costs a fraction of
> the first." Full calculation: `evidence/10_business_kpi_calculations.md`.

---

## Slide 5 · Prove it in 5 stores in 6 weeks, with go/no-go decided by measured results

| Weeks | Activity | Output |
|---|---|---|
| **1–2 · Baseline** | Time 10 manual invoice checks and log data-gathering time per pilot store. Connect real POS, PO and inventory exports (the pipeline and quality checks stay the same) | Measured baseline replaces assumptions |
| **3–4 · Live** | App live in 5 stores; managers trained (~1 hour); sync scheduled after every pipeline run | Real usage |
| **5–6 · Measure** | Re-time invoice checks; re-run the AI evaluation on the customer's own SOP questions; count stockouts | Pilot scorecard |

**Go / no-go**
- ≥ 50% less time on invoice checks and data gathering (measured).
- AI correctness ≥ 0.80, with safety at 1.00.
- No increase in stockouts.
- Managers using the app on most store days.

**Next steps**
1. Agree on the 5 pilot stores and the baseline method.
2. Share one month of masked invoices, POs, sales and SOP documents.
3. Week-2 review of the pipeline and evaluation on the customer's own data.

> **Say:** "We're not asking you to believe the ₹2.2 crore. We're asking for 6 weeks to measure it."

---
---

# Technical deep dive (for the architect)

---

## Slide 6 · Architecture: Delta computes, Lakebase serves, Genie answers, the AI Gateway governs

```
Synthetic source data (37 stores · 28 products · 200k orders · 2k POs · 171k inventory txns)
   │  Parquet per entity → Unity Catalog Volume raw_data/
   ▼  Auto Loader (read_files, streaming)
LAKEFLOW SPARK DECLARATIVE PIPELINE (serverless, SQL)
   Bronze 14 streaming tables → Silver 14 MVs (45 expectations) → Gold 7 MVs
   inventory position · open POs · delivery exceptions · product demand ·
   supplier performance · waste · store KPIs
   │
   ├──► LAKEBASE (Postgres)  operational serving + app state
   │      4 gold copies: lb_inventory_position · lb_open_purchase_orders ·
   │                     lb_delivery_exceptions · lb_product_demand
   │      app state: conversations · messages · feedback · qa_cache (semantic) · activity_log
   │
   ├──► GENIE AGENT MODE  21 silver/gold tables + SOP PDF volume (config as code)
   │
   ├──► UNITY AI GATEWAY  every non-Genie AI call
   │      kaapi_llm   Claude Sonnet 4.6 → Haiku 4.5 fallback · 300 rpm · payload log
   │      kaapi_embed BGE-large · 600 rpm · payload log
   │      kaapi_ops_advisor MCP service → ops-advisor app (weather, holidays) · 120 rpm
   │
   └──► MLFLOW 3  tracing on every request · mlflow.genai.evaluate
   ▼
DATABRICKS APP (FastAPI + React)   Ask → Genie · See → Lakebase · Act → Gateway + Delta + Lakebase
                                   Plan → SQL + Lakebase + Gateway MCP
```

**The write path (how "Act" stays consistent)**
1. Approval writes to Delta `app_inventory_receipts` / `app_po_approvals`. Delta is the system of record, and pipeline tables stay read-only.
2. In the same request, it writes through to Lakebase: stock updated, PO closed, activity logged, so the dashboard updates within one 10 s refresh.
3. The next pipeline run unions the app tables into gold, and the sync reconciles Lakebase.

**Why each component**

| Need | Component | Why this, not the alternative |
|---|---|---|
| Many sources, repeatable, with quality checks | Lakeflow Declarative Pipelines | Declarative SQL, built-in expectations, serverless; no orchestration code |
| Per-store reads in milliseconds, plus row-level writes | Lakebase | A SQL warehouse is built for scans, not 37 stores polling every 10 s; Delta single-row updates rewrite files |
| Questions over tables **and** documents | Genie Agent mode | One governed assistant; Chat mode can't read PDFs; Knowledge Assistant / Supervisor Agent are deprecated |
| Controlled, auditable model use | Unity AI Gateway | Permissions in UC, rate limits, fallback and payload logs in one place |
| Proof of AI quality | MLflow 3 | Traces per request; repeatable scored evaluation |

One record (PO-00006) is traced through every layer, raw → bronze → silver → gold → Lakebase → app: `evidence/08`.

---

## Slide 7 · Governance: one permission model for data, documents, AI and the app

**Data (Unity Catalog)**
- One governed schema with table comments, lineage from raw volume → bronze → silver → gold, and the SOP documents in a governed Volume.
- The app runs as its own service principal (SP), with grants scoped to what it uses:
  - read on the pipeline tables;
  - write only to the two `app_*` tables (narrowing schema-wide `MODIFY` to those tables is a listed hardening step);
  - in Lakebase, `SELECT` on serving tables, plus `UPDATE`/`DELETE` only on the two tables that approvals write through.

**Data quality (measured)**
- 45 expectations in silver:
  - `DROP ROW` on keys and totals;
  - `WARN` on business rules (e.g. delivery date ≥ order date).
- Run 065d6a70: **45 of 45 passed, 0 rows failed**, from the pipeline event log (evidence/03).

**AI (Unity AI Gateway)**
- Every AI call except Genie goes through UC-registered services; access is `EXECUTE` granted to the app SPs only.
- Rate limits are enforced. At 1 request/min, the second call returned **HTTP 429** (evidence/11).
- Payload log tables record the requester, status, latency and body of each model call.
- **No ungoverned fallback.** If the gateway refuses, the app shows the error. The only fallback (Sonnet → Haiku) is inside the gateway.

**Security**
- 100% synthetic data and a fictional company.
- No credentials in code, and commits pass a secret-scanning hook.
- Lakebase uses short-lived OAuth tokens; users sign in through Databricks Apps OAuth.

---

## Slide 8 · AI quality is measured, published with its failures, and improved at the root cause

**Grounding by workflow**

| Workflow | Where facts come from | What the AI does |
|---|---|---|
| Ask | Genie-generated SQL over governed tables (visible); cited SOP PDFs | Interprets the question, writes the answer |
| Act | The PO and price tables; matching in deterministic code | Reads the PDF into structured lines |
| Plan | Same-weekday demand (SQL), stock and POs (Lakebase), weather and holidays (MCP tool) | Adjusts for context, writes the plan |

**Evaluation history** (10 store-manager questions, 32 expected facts; `mlflow.genai.evaluate`)

| Run | Change | Correctness | Relevance | Safety |
|---|---|---:|---:|---:|
| 1 | Genie Chat mode (can't read documents) | 0.00 | 0.30 | 1.00 |
| 2–3 | Genie **Agent mode** + SOP volume | 0.50 | 1.00 | 1.00 |
| 5 | End to end through the app, with governed price lookup | **0.70** | **1.00** | **1.00** |

- Run 4 was void (one question unscored after an auth refresh) and was re-run, not reported as a pass.
- Gap to the 0.80 target:
  - supplier terms from a table;
  - a must-have / nice-to-have rubric;
  - a 30+ question set.
- Failed-case analysis is in `evidence/09`.

**Humans in the loop.** Approvals are always manual. When a source is missing, the assistant says
so rather than guessing (Safety 1.00). Every request has an MLflow trace for audit.

---

## Slide 9 · The trade-offs we chose, and how each one is mitigated

| Decision | What it costs | Mitigation |
|---|---|---|
| **Genie Agent mode** for tables and PDFs | ~23 s on document questions vs a few seconds in Chat mode | Lakebase semantic cache: repeat questions 25.3 s → **1.1 s** |
| **Lakebase as a serving copy** of gold | Freshness depends on the sync | Write-through on approval; production uses **Lakebase synced tables** or a sync task after the pipeline |
| **All non-Genie AI through the gateway**, no direct fallback | A gateway outage stops "Act" and "Plan" | Model fallback inside the gateway; a failed call errors loudly instead of escaping governance |
| **SQL computes, AI writes** | Less free-form flexibility | Correctness rose once prices came from tables; numbers are auditable |
| **One gateway document call** for invoices | Depends on the model's PDF reading | 22.7 s → 18.4 s vs `ai_parse_document` + a second call; human approval on every result |
| **Synthetic data** | Business value is assumed | Labelled assumptions; the pilot measures real baselines first |

---

## Slide 10 · Risks and what happens next

| Risk | Likelihood | Mitigation |
|---|---|---|
| Unusual invoice layouts parse badly | Medium | Human approval on every invoice; deterministic line checks; every parse logged |
| AI correctness below target on long procedures | Medium | Measured at 0.70 today; target ≥ 0.80 is a pilot go/no-go criterion |
| Document-answer latency (~23 s) | Medium | Semantic cache; SOPs change rarely |
| Lakebase snapshot drifts from gold | Medium | Write-through now; synced tables or a sync task after the pipeline in production |
| Model provider outage | Low | Sonnet → Haiku fallback inside the gateway |
| Managers don't adopt it | Low | One app instead of five; chat-first; ~1-hour training |

**Production hardening backlog**
- Narrow `MODIFY` to the two app tables.
- Attach gateway guardrail policies (jailbreak, unsafe content).
- Cost per store from system tables.
- Lakebase synced tables.

---

## Appendix · Evidence index

| # | Evidence | File |
|---|---|---|
| 01 | Lakeflow pipeline run (14 / 14 / 7) | `evidence/01_lakeflow_run.txt` |
| 02 | Unity Catalog tables, lineage, grants | `evidence/02_uc_tables_and_lineage.md` |
| 03 | Data quality: 45 / 45 expectations | `evidence/03_data_quality_results.txt` |
| 04 | Lakebase serving tables and queries | `evidence/04_lakebase_queries.txt` |
| 05 | Genie questions and answers | `evidence/05_genie_questions_and_answers.md` |
| 06 | Invoice and preparation-plan outputs | `evidence/06_genai_model_outputs.md` |
| 07 | App health and API tests | `evidence/07_app_health_and_api_tests.txt` |
| 08 | One record traced end to end | `evidence/08_end_to_end_record_trace.md` |
| 09 | MLflow evaluation runs | `evidence/09_mlflow_evaluation_results.md` |
| 10 | Business KPI calculations | `evidence/10_business_kpi_calculations.md` |
| 11 | Unity AI Gateway | `evidence/11_unity_ai_gateway.md` |
| 12 | Live store dashboard and write-through | `evidence/12_live_store_dashboard.md` |

*Kaapi Bricks is a fictional company. All data is synthetic (Faker, seed=42). No real customer
data or credentials. Live demo script: `DEMO.md`. Roleplay prep: `ROLEPLAY_PREP.md`.*
