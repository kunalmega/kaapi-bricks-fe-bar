# Kaapi Bricks Intelligent Store Operations
## Powered by Databricks

*FE Bar Submission Deck — Kaapi Bricks (fictional 37-store South Indian filter-coffee chain)*
*Industry: Multi-location food service and specialty retail*

> **How to read the numbers in this deck.** Business value figures (₹ / $, time saved, payback, ROI)
> are **projections built from labeled assumptions**. No timed baseline trial has been run.
> System measurements (pipeline run, data quality, Lakebase rows, invoice parse time, AI evaluation
> scores, latency) are **measured** and come from the `evidence/` folder.

---

## Slide 1: The Outcome in One Sentence

**Today:** A store manager spends an estimated 25–30 minutes per delivery cross-checking a supplier invoice against the purchase order. Across 37 stores and ~74 deliveries a day, that is a projected 30+ manager-hours a day. *[assumption]*

**With the solution:** The manager uploads the invoice. The app parses it, matches it to the PO, flags every quantity and price discrepancy, and the manager approves or rejects. Parse-and-match is measured in seconds of system time (see `evidence/06`); the target end-to-end manager time is under 2 minutes per delivery.

**Projected annual value: ~₹2.2 crore (~$264,500) across 37 stores** *(assumption-based; see Slide 9)*

---

## Slide 2: Customer and Industry Context

**Kaapi Bricks** operates 37 stores: 30 in India and 7 international (Dubai, Singapore, London, San Francisco, Kuala Lumpur, Sydney, Toronto). The brand specializes in South Indian filter coffee, from tumbler-davara Degree Coffee to cold brews.

**Why this industry is hard:**

- **Perishable ingredients**: full cream milk, cardamom, coconut milk. Over-order and you waste; under-order and you lose the morning rush.
- **8 active suppliers**, each with its own lead time, pricing, and reliability. Measured on-time delivery ranges from **80.5% to 86.4%** across the 8 suppliers (`gold_supplier_performance`, evidence/05).
- **Weather and festivals matter**: holidays, rain, and local events shift demand between hot and cold drinks.
- **37 stores × ~2 deliveries/day**: ~74 invoices a day, arriving as paper or PDFs in different layouts.

**The store manager is the most information-dense role in the company**, and today they work from paper, spreadsheets, and memory.

---

## Slide 3: The Specific Problem — Three Pain Points

### Pain Point 1: Invoice Reconciliation
Priya, the Koramangala store manager, receives a paper invoice from Coorg Coffee Estates. She must:
1. Find the matching PO.
2. Compare each line item by hand: quantities, units, prices, GST codes.
3. Note discrepancies (price increase? item not on the PO?).
4. Chase accounts payable for approval, then file.

**Estimated at 25–30 minutes per delivery** *[assumption]*. Across 37 stores: a projected **1,850 manager-minutes a day**.

### Pain Point 2: Inventory Blindness
Priya doesn't know her current stock of Coorg Arabica until she counts it. By then, the 7-day reorder lead time from Coorg means she will run short. In the synthetic data, **27 store×ingredient positions are below reorder threshold right now** (evidence/05). The stockout cost model assumes 3.5% of store-days have a critical stockout *[assumption]*.

### Pain Point 3: Operating Knowledge Is Locked in PDFs
Recipes, decoction timing, allergen handling, and equipment cleaning live in six SOP and training PDFs. New baristas ask the manager; the manager looks it up or answers from memory.

---

## Slide 4: Proposed Business Outcomes and KPI Targets

| KPI | Current Baseline | 12-Month Target | Baseline source |
|---|---|---|---|
| Invoice reconciliation time | 25–30 min/delivery | < 2 min/delivery | assumption |
| Invoice exception rate (missed discrepancies) | ~12% | < 3% | assumption |
| Stockout rate (% of store-days) | 3.5% | < 1.5% | assumption |
| Ingredient waste rate | ~4% of cost | < 3% | assumption |
| Supplier on-time delivery rate | 80.5–86.4% | > 92% | **measured** (synthetic data) |
| Manager time on data gathering | ~45 min/day | < 5 min/day | assumption |
| Answer latency, table/cached questions | manual | < 5 s | target |
| Answer latency, SOP document questions | manual | ~23 s measured today; < 10 s target | **measured** (evidence/09) |

**Projected annual value: ₹2.2 crore (~$264,500/year)** *(assumption-based)*

**Simple payback: 3.9 months**
= one-time implementation cost ÷ annual net benefit × 12
= $70,000 ÷ ($264,500 − $50,000) × 12

---

## Slide 5: The Solution Journey (Live Demo Flow)

*Tell → Show → Tell for every scene. Full script in `DEMO.md`.*

### Scene 1 — Morning Questions
**TELL:** *"Priya opens the store at 7am. She has questions about her data and about how to do the job. She asks both in plain English, in one place."*

**SHOW:** Main chat app (Genie Agent mode) →
- "Which ingredients are below reorder threshold?" → SQL over `gold_inventory_position`; 27 positions below threshold across stores (evidence/05).
- "How long can prepared decoction be kept before discarding?" → answered from `drink_recipes_sop.pdf`: maximum 4 hours (evidence/07).

**TELL:** *"One assistant, governed data plus company SOPs. The numbers come from SQL she can inspect; the procedures come from cited documents."*

### Scene 2 — The Delivery
**TELL:** *"A truck arrives from Coorg Coffee Estates with a paper invoice."*

**SHOW:** Upload the invoice PDF → the PDF is parsed and structured in one governed call through the **Unity AI Gateway** (`kaapi_llm`) → matched to the open PO → discrepancies flagged line by line → Priya approves → receipt written to `app_inventory_receipts`; the inventory panel (served from Lakebase) reflects it after the next pipeline refresh and sync. Measured through the gateway: all 4 planted discrepancies detected, the clean control line matched, 18.4 s server time (`evidence/11`).

**TELL:** *"The machine does the comparison; the manager still makes the decision. Every discrepancy is on record."*

### Scene 2b — Today's Preparation Plan
**TELL:** *"Before the rush, Priya asks how to prepare for today."*

**SHOW:** "How should I prepare for today?" → the app takes the same-weekday demand from gold (SQL) and stock plus overdue POs from Lakebase, then calls the operations advisor through the Unity AI Gateway MCP service. It pulls live weather and the holiday calendar and writes the plan through `kaapi_llm`. Captured: *Tuesday, thunderstorm 21 mm; Classic Filter Coffee typical 12.1 → forecast 14–15; Cold Coffee 3.6 → 2–3* (`evidence/11`, trace tr-aaeed488…).

**TELL:** *"The numbers come from her own history for this weekday; the model only adjusts for today's weather and writes it up."*

### Scene 3 — How We Know It Works
**TELL:** *"How do we know the answers are right?"*

**SHOW:** MLflow experiment → evaluation runs on 10 store-manager questions. Baseline (Chat mode, no document access): Correctness 0.00. After switching to Genie Agent mode with the SOP volume: Correctness 0.50. With governed menu-price lookup, measured end to end through the deployed app: **Correctness 0.70, Relevance 1.00, Safety 1.00** (10/10 questions scored). Failed-case analysis: `evidence/09`.

**TELL:** *"We measure it, we publish the failures, and we fix the root cause, not the score."*

---

## Slide 6: Architecture and Integrated Data Flow

```
SYNTHETIC RETAIL DATA (scripts/generate_data.py, Faker seed=42)
  37 stores · 28 products · 15k customers · 200k orders · 2k POs · 3.5k PO lines · 171k inventory txns
    │
    ▼ Parquet, one folder per entity
UNITY CATALOG VOLUME  raw_data/<entity>/
    │
    ▼ Auto Loader (STREAM read_files)
LAKEFLOW PIPELINE  kaapi_bricks_medallion  [serverless, declarative]
  ├── Bronze  14 streaming tables — raw + ingest metadata
  ├── Silver  14 materialized views — typed, deduped, 45 expectations
  └── Gold     7 materialized views — inventory position, open POs, delivery
               exceptions, product demand, supplier performance, waste, store KPIs
    │
    ├─► UNITY CATALOG — governed tables, comments, lineage, least-privilege grants
    │
    ├─► LAKEBASE (Postgres) — 4 gold operational tables synced
    │     lb_inventory_position · lb_open_purchase_orders ·
    │     lb_delivery_exceptions · lb_product_demand
    │
    ├─► GENIE AGENT (Agent mode) — 21 silver + gold tables + 6 SOP PDFs in a volume
    │
    ├─► UNITY AI GATEWAY — every non-Genie AI call, EXECUTE-granted, rate-limited, logged
    │     kaapi_llm (Sonnet 4.6 → Haiku 4.5) — invoice document parsing, preparation plan
    │     kaapi_embed (BGE) — semantic-cache embeddings
    │     MCP service kaapi_ops_advisor — live weather + holiday calendar
    │
    └─► Evaluation — MLflow mlflow.genai.evaluate: Correctness, Relevance, Safety
    │
    ▼
DATABRICKS APP — Store Manager Console (main-chat-app)
  chat → Genie Agent mode · prep plan → SQL + Lakebase + gateway MCP · inventory panel → Lakebase
  invoice upload → gateway kaapi_llm
```

The same keys (store_id, ingredient_id, po_id) flow raw → bronze → silver → gold → Lakebase → app. `evidence/08` traces one real delivery (PO-00006) through every layer.

---

## Slide 7: Governance, Security, and Data Quality

### Unity Catalog Governance
- All tables in one governed `kaapi_bricks` schema, with table comments.
- App service principal grants: `USE CATALOG`, `USE SCHEMA`, `SELECT` and `MODIFY` on the `kaapi_bricks` schema (the app only writes to the two app-write tables), `READ VOLUME` on raw data, read/write on the invoices volume, and `SELECT` on the Lakebase serving tables. Tightening `MODIFY` to the two tables is a production hardening step.
- Lineage: raw volume → bronze → silver → gold, visible in Unity Catalog.

### Data Quality (45 expectations in Silver, measured)
- **DROP ROW** on primary keys, required foreign keys, non-negative totals.
- **WARN** on business rules (e.g. `cost ≤ base_price`, delivery date ≥ order date).
- Pipeline run 065d6a70: **45 of 45 constraints passed, 0 rows failed** (read from the pipeline event log, evidence/03). The data is synthetic and clean by construction; the constraints protect future real ingest.

### App-Write Separation
- Silver and gold are pipeline-owned (read-only to the app).
- Invoice approvals write to separate `app_inventory_receipts` and `app_po_approvals` Delta tables.
- Gold views UNION both sources. The calculation is deterministic SQL; the LLM only explains results.

### AI Governance: Unity AI Gateway
- Every AI call except Genie goes through Unity Catalog services: `kaapi_llm`, `kaapi_embed`, MCP service `kaapi_ops_advisor`.
- Access is a UC grant (`EXECUTE` to the app service principals). Nothing else can call them.
- Rate limits per service (300 / 600 / 120 per minute). Tested: at 1/min the gateway returned **HTTP 429** on the second call.
- Every model call lands in a payload-log table with requester, status and latency. The logs show both identities: the main app (invoice parsing, embeddings) and the MCP app (plan writing).
- No ungoverned fallback: if the gateway refuses, the app shows the error. The only fallback (Sonnet → Haiku) is inside the gateway.
- Evidence: `evidence/11`.

### Security
- 100% synthetic data, fictional company.
- No credentials in the codebase; commits pass a secret-scanning hook. Lakebase uses short-lived OAuth credentials.
- The app runs as its own service principal; user access goes through Databricks App OAuth.

---

## Slide 8: AI Grounding, Evaluation, and Human Controls

### How the AI is Grounded
- **Genie Agent, structured questions:** generates SQL over governed silver/gold tables. The SQL is visible and runs against real data.
- **Genie Agent, procedural questions:** reads the six SOP/training PDFs in a Unity Catalog volume and cites the source file.
- **Invoice parsing:** the PDF goes to `kaapi_llm` through the Unity AI Gateway, which parses and structures it in one governed call; matching against the PO is deterministic code.
- **Preparation plan:** demand and stock come from SQL and Lakebase; the model (through the gateway) only adjusts for live weather and holidays and writes the plan.

### Evaluation Loop (MLflow, measured)
```
10 store-manager questions with 32 expected facts
  → mlflow.genai.evaluate()  (scripts/run_genie_evaluation.py, serverless job)
  → Scorers: Correctness, RelevanceToQuery, Safety
  → Baseline:   Correctness 0.00  (Chat mode API cannot read documents)
  → Fix:        switch to Genie Agent mode API
  → Re-test:    Correctness 0.50 · Relevance 1.00 · Safety 1.00
  → App end-to-end (+ governed price lookup): Correctness 0.70 · Relevance 1.00 · Safety 1.00
  → Latest iteration + failed-case analysis: evidence/09
```

### Where Humans Stay in the Loop
- **Invoice approval** is always a human action. The app flags discrepancies; the manager decides.
- **No silent answers:** when a source is missing, the agent says so instead of guessing (Safety 1.00 in both runs).
- **MLflow traces** log every question and response for audit.

### Trade-off: Genie Agent vs a Custom Agent
- **Chose Genie Agent:** governed table access, transparent SQL, native document reading, and it replaces the deprecated Knowledge Assistant + Supervisor Agent with one product.
- **Cost of that choice:** Agent mode answers SOP questions in ~23 s versus a few seconds for table-only Chat mode. Mitigated with the Lakebase semantic answer cache for repeat questions.
- **Alternative considered:** a custom agent on Databricks Apps with our own retrieval. More control, more code to own.

### Trade-off: Lakebase vs Delta for Serving
- **Delta via SQL warehouse:** best for large analytical scans.
- **Lakebase (Postgres):** OLTP point lookups for one store's current inventory.
- **Decision:** gold operational tables are synced to Lakebase for the app's inventory panel; trend and multi-store analysis stays on Delta through Genie.

---

## Slide 9: Expected Value and Assumptions

*Every row is a projection from the stated assumption. None is a measured customer outcome.*

| Value driver | Annual (₹) | Annual ($) | Key assumption |
|---|---|---|---|
| Invoice reconciliation labor | ₹89,93,600 | $107,000 | 25 min saved/delivery, 2 deliveries/store/day, ₹800/hr loaded cost |
| Invoice leakage prevention | ₹90,75,360 | $108,000 | 12% exception rate, ₹2,800 average slip-through |
| Stockout reduction | ₹11,91,960 | $14,200 | 60% reduction on a 3.5% store-day stockout baseline |
| Waste reduction | ₹2,59,000 | $3,100 | 25% reduction on ₹28k/store/year perishable waste |
| Manager time (data questions) | ₹27,07,200 | $32,200 | 15 min/day saved × 37 stores |
| **Total annual value** | **₹2,22,27,120** | **~$264,500** | |
| Platform cost | — | $50,000/year | serverless pipeline + Lakebase + model APIs + app at 37 stores |
| Implementation (one-time) | — | $70,000 | 8-week implementation and training |

**Simple payback = one-time implementation ÷ annual net benefit × 12 = $70,000 ÷ $214,500 × 12 = 3.9 months**

**3-year net ROI = (3-year gross value − 3-year cost) ÷ 3-year cost = ($793,500 − $220,000) ÷ $220,000 = 2.6×**

Full calculation: `evidence/10_business_kpi_calculations.md`. The first thing a pilot should do is replace these assumptions with a timed baseline.

---

## Slide 10: Pilot Plan, Risks, and Next Steps

### Recommended Pilot (5 stores, 6 weeks)

**Week 1–2: Baseline and data foundation**
- Stopwatch baseline: time 10 manual invoice reconciliations per pilot store before go-live.
- Connect the customer's POS, PO, and inventory exports in place of the synthetic generator; the pipeline and expectations stay the same.

**Week 3–4: App live in 5 stores**
- Deploy the store manager console; train 5 managers on invoice upload and approval.
- Schedule the Lakebase sync right after each pipeline refresh.

**Week 5–6: Measure**
- Re-time 10 reconciliations per store with the app; compare with the Week 1 baseline.
- Re-run the MLflow evaluation on the customer's own SOP questions; target Correctness ≥ 0.80.
- Count stockout events against the baseline; collect manager feedback.

**Go/no-go:** ≥ 50% reduction in measured reconciliation time; Correctness ≥ 0.80 with Safety 1.00; no increase in stockouts.

### Key Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Document-parsing accuracy on unusual invoice layouts | Medium | Every result needs human approval; line-level checks are deterministic code; the gateway logs every parse for audit |
| Model provider outage | Low | Fallback Sonnet 4.6 → Haiku 4.5 inside the gateway |
| Genie Agent correctness on long procedures | Medium | Measured today: 0.70 end to end (target 0.80, see evidence/09); improve instructions and eval rubric before rollout |
| Agent mode latency (~23 s on SOP questions) | Medium | Semantic answer cache in Lakebase; SOP content changes rarely |
| Lakebase data is a snapshot | Medium | Sync runs after each pipeline update; move to a scheduled job or synced tables in production |
| Store managers resist the new workflow | Low | Chat-first UI; invoice upload is a single step |

### Next Steps
1. Agree the 5 pilot stores and the baseline timing method.
2. Share one month of real (masked) invoices, POs, and SOP documents for a fit test.
3. Re-run the pipeline and the evaluation on customer data; review results together in week 2.

---

*Kaapi Bricks is a fictional company. All data is synthetic (Faker, seed=42). No real customer data or credentials.*
