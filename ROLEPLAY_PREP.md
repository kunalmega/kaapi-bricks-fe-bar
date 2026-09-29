# Roleplay Prep — Kaapi Bricks

Two personas in one session:
- **Business stakeholder** (the executive who funds it): cares about value, cost, risk, time to value.
- **Technical stakeholder** (the architect or data lead who must run it): cares about architecture,
  data quality, security, integration, and failure handling.

Rule of thumb: answer the business persona in one or two sentences with a number and a decision;
answer the technical persona with the mechanism, the trade-off, and what you'd change in production.
When a question spans both, give the business line first, then "for the platform team: …".

Be explicit about what is **measured** (from `evidence/`) and what is an **assumption**
(from `evidence/10`).

---

## Opening (60–90 seconds, before any screen)

> "Kaapi Bricks runs 37 filter-coffee stores. Every store gets about two supplier deliveries a day,
> and the manager checks each paper invoice against the PO by hand. We estimate 25 to 30 minutes
> each. That's an assumption we'd confirm in a pilot, and it's where invoice overcharges slip
> through.
>
> In the next 12 minutes I'll show three things: a manager getting answers from both her data and
> her company's SOPs in one place; an invoice check that flags every discrepancy for her to approve;
> and how we measure whether the AI is right, including where it isn't yet.
>
> I'll close with the value model: roughly ₹2.2 crore a year, projected from assumptions I'll show
> you, and a five-store pilot to turn those assumptions into measurements."

---

## Tell–show–tell by scene

| Scene | Tell (what you'll see) | Show | Tell (what it means) |
|---|---|---|---|
| 1. Morning questions | "Priya asks about her numbers and her procedures in plain English." | Below-reorder items (SQL on gold) → decoction hold time (SOP PDF, cited) → top drinks | "Data and SOPs in one governed assistant: fewer escalations, faster barista onboarding." |
| 2. Delivery | "A supplier invoice arrives on paper." | Upload → governed parse through the Unity AI Gateway (`kaapi_llm`) → PO match → 4 flagged lines + 1 clean match → Lakebase inventory → approve | "The system compares; the manager decides. Every discrepancy is recorded. This is the leakage and labor line of the business case." |
| 2b. Preparation | "How should Priya prepare for today?" | Same-weekday baseline (SQL) + Lakebase stock → gateway MCP service (live weather, holidays) → plan | "Her own history sets the numbers; today's weather adjusts them. Every AI call went through the governed gateway." |
| 3. Evaluation | "How do we know it's right?" | MLflow: 0.00 → 0.50 → 0.70 Correctness (app end to end), Relevance 1.00, Safety 1.00; a failed case with the judge's reason | "We found the root cause and fixed it. We're below our 0.80 target and we know why. This becomes your quality gate." |
| 4. Architecture | "One journey, not six demos." | UC lineage, PO-00006 trace raw → app, gateway services + payload log | "Governed in one place, serverless, deployed from code." |
| 5. Close | "What it's worth and how to prove it." | Value table with assumptions | "Next step is a six-week, five-store pilot with a timed baseline." |

---

## Prepared answers

### Data freshness and Lakebase sync timing
- **Business:** "Inventory and delivery data is as fresh as the last pipeline run, today a
  triggered run that takes about a minute. In a pilot we'd run it on a schedule, for example every
  15 minutes during store hours, and managers see updates within that window."
- **Technical:** "Raw files land in a Unity Catalog volume; Lakeflow Auto Loader ingests them into
  bronze; silver and gold are materialized views. The full run took ~61 s serverless (evidence/01).
  Lakebase is loaded by a truncate-and-reload script after each run. That's a snapshot, so
  freshness equals pipeline cadence plus sync. For production I'd make the sync a job task that
  runs right after the pipeline, or move to Lakebase synced tables so there is no custom sync code."

### Invoice human approval and the write path
- **Business:** "Nothing is posted without the manager clicking approve. The AI prepares the
  comparison; accountability stays with a person."
- **Technical:** "Silver and gold tables are owned by the pipeline and read-only to the app. An
  approval writes to two separate Delta tables, `app_inventory_receipts` and `app_po_approvals`.
  Gold unions them in, so stock and open-PO numbers reflect the approval after the next refresh.
  That separation means a pipeline full-refresh can never erase an approval, and the app can never
  corrupt pipeline tables. Parsing is one governed call: the PDF goes to `kaapi_llm` through the
  Unity AI Gateway, which returns the structured fields (18.4 s server time, all 4 planted
  discrepancies caught, evidence/11). The PO comparison itself is deterministic code, not the model."

### "Your correctness is only 0.70"
- **Business:** "Yes, and I'm showing you on purpose. It was 0.00 on the first run; we found the
  cause, fixed it, and it's now 0.70 measured through the deployed app. Safety is 1.00: when it doesn't know, it says
  so instead of guessing. We won't roll out below the 0.80 target; the pilot includes getting there."
- **Technical:** "Baseline 0.00: we called Genie through the Chat-mode API, which only queries
  tables, so all SOP questions were declined. We switched to the Agent mode API, which reads the
  attached PDF volume; Correctness went to 0.50, Relevance 1.00. Most misses were facts the model left out, like menu
  prices. A prompt change didn't fix that, so we moved prices to a deterministic lookup against the
  governed `products` table. Measured end to end through the app, Correctness is 0.70. Of the three
  remaining failures, one is a judge error and two missed one secondary fact each. With 10 questions,
  run-to-run variation is about ±0.1–0.2, so the next step is a 30+ question set and a
  must-have/nice-to-have rubric.
  Latest numbers are in evidence/09. We dropped the groundedness scorer because Agent mode doesn't
  return the retrieved chunks, so a groundedness score would have been meaningless."

### Agent mode latency (~23 s) and the cache
- **Business:** "Answers from documents take about 20 seconds today; answers from data are
  faster. The common questions (recipes, hold times, cleaning) are cached, so the second person to
  ask gets it instantly."
- **Technical:** "Agent mode reasons over several steps and reads files, so we measured 22.9 s
  end-to-end through the app. The app checks a Lakebase semantic cache first: exact match, then
  embedding similarity ≥ 0.95, 48-hour TTL, filtered by store. SOP content changes rarely, so hit
  rates should be high. If latency matters more than breadth, we can route pure table questions to
  the faster Chat-mode API and keep Agent mode for documents."

### ROI is based on assumptions
- **Business:** "Correct. Every number in the value model is an assumption, written down with its
  source. The ₹2.2 crore figure is the reason to run a pilot, not the result of one. The pilot's
  first week is a stopwatch baseline on ten invoices per store; week six re-times them."
- **Technical:** "Payback is implementation cost divided by annual net benefit: $70k ÷ ($264.5k −
  $50k) × 12 = 3.9 months. Three-year net ROI is (3 × $264.5k − $220k) ÷ $220k = 2.6×. The biggest
  sensitivities are minutes saved per delivery and the invoice exception rate. Halve both and the
  case still pays back inside a year."

### Cost per store
- **Business:** "At the assumed $50,000 a year for the platform, that's about $1,350 per store per
  year, roughly $113 a month, plus a one-time $70,000 implementation, about $1,900 per store.
  We'd confirm the platform number with a sizing exercise on your real volumes."
- **Technical:** "Cost drivers are serverless pipeline runs (~1 minute each today), the SQL
  warehouse for Genie queries, Lakebase capacity, model calls for parsing and Agent mode, and the
  app's compute. Serverless and caching keep idle cost low; the Lakebase cache also reduces model
  calls for repeat questions."

### KA / Supervisor Agent deprecation and the migration
- **Business:** "Databricks is consolidating its agent products into Genie Agents. We already
  migrated, so what you see is on the current product line, with one component instead of three."
- **Technical:** "We removed the Knowledge Assistant and the Supervisor Agent. One Genie Agent now
  covers the 21 governed tables and the SOP PDF volume. The app calls the Agent mode responses
  API. The space configuration is exported as code in `resources/genie_space.json` and applied with
  `scripts/create_genie_agent.py`, so it is reproducible in another workspace."

### Security and identity
- **Business:** "No real customer data. Access is controlled in one place, and the app can only
  see what it has been granted."
- **Technical:** "Users sign in through Databricks App OAuth. The app runs as its own service
  principal with Unity Catalog grants: use catalog and schema, select, modify for the two
  app-write tables, volume access for raw data and invoices, and select on the Lakebase serving
  tables. Lakebase uses short-lived OAuth credentials, no stored passwords. There are no secrets in
  the repo, and every commit passes a secret-scanning hook. Hardening item: narrow modify from the
  schema to the two app-write tables."

### Failure handling
- **Business:** "If the AI can't answer, it says so. If a component is down, the manager can still
  check stock and invoices; nothing is posted without approval."
- **Technical:**
  - **Bad data:** 45 expectations in silver drop invalid rows or warn; results are in the event log
    (evidence/03 shows 45/45 passed, 0 failed).
  - **Model or Genie unavailable:** the app returns a clear "couldn't get an answer" message and
    logs the error to `inference_logs`; cached answers still serve.
  - **Invoice parse fails:** the gateway retries on the fallback model (Haiku 4.5) if Sonnet is
    unavailable; if the gateway itself refuses, the app shows the error. There is no ungoverned
    fallback. Any parse still needs human approval.
  - **Lakebase unavailable:** the Delta-backed `/api/inventory` endpoint returns the same gold
    data, only slower. The UI does not fail over to it automatically today; that is a small
    production change.
  - **Observability:** every chat request is traced in MLflow and logged with latency.

### "How do you govern AI calls?"
- **Business:** "Every AI call except the Genie assistant goes through one governed gateway.
  Only this app is allowed to call it, there's a spending brake (a rate limit), and every request
  is logged. If someone asks 'what did the AI see on that invoice?', we can show them."
- **Technical:** "Unity AI Gateway services in the same Unity Catalog schema as the data:
  `kaapi_llm` (Sonnet 4.6 → Haiku 4.5), `kaapi_embed` (BGE) and the MCP service
  `kaapi_ops_advisor`. The app service principals get `EXECUTE`, nothing else. Service-wide limits
  are 300, 600 and 120 per minute; at 1/min in testing the gateway returned HTTP 429 on the
  second call. Every model call lands in `kaapi_llm_payload` / `kaapi_embed_payload` with the
  requester, so you can see the main app parsing invoices and the MCP app writing plans. The app
  has no direct serving-endpoint path, so a gateway error surfaces instead of bypassing governance.
  Guardrail policies are attached in the UI; that's the next hardening step." (evidence/11)

### "What if the model provider is down?"
- **Business:** "There's a backup model behind the same gateway, so the manager doesn't notice."
- **Technical:** "`kaapi_llm` routes to Claude Sonnet 4.6 with Claude Haiku 4.5 as the gateway
  fallback destination. The fallback is configured in the service, not in app code, so it's
  governed and logged the same way."

### "Why is Genie not behind the gateway?"
- **Business:** "Genie is already governed: it only sees the tables and documents we gave it, with
  the same Unity Catalog permissions."
- **Technical:** "Genie Agent is its own governed product. Its access is the Genie space plus
  Unity Catalog grants, and its model calls are managed inside Genie. We chose not to add a guard
  step in front of it because it would add latency to every question. If question-level policies
  are needed, the design has a strict-lane `kaapi_guard` service ready to add (ARCHITECTURE §9.6)."

### "What about the weather API?"
- **Business:** "The weather feed is used only to adjust the preparation plan, and the call to it is governed."
- **Technical:** "The app calls the operations advisor through the gateway MCP service, which is
  `EXECUTE`-granted and rate-limited at 120/min. The MCP server then calls Open-Meteo itself, so the
  gateway governs the tool call, not that HTTP request. If that mattered, the next step is a UC
  HTTP connection for Open-Meteo."

### Other likely questions
- **"How fast can we pilot in five stores?"** Six weeks: two for baseline and data connection, two
  live, two to measure. The pipeline, Genie config, and app deploy from code.
- **"What if a recommendation is wrong?"** Numbers come from deterministic SQL the user can
  inspect; procedural answers cite the source document; invoice results always need approval.
- **"Why Databricks?"** Ingestion, governance, operational serving, document AI, the agent, and
  evaluation run on one platform with one permission model. No data copies to a separate vector
  store or app database vendor.
- **"How does it fit our systems?"** In a pilot the synthetic generator is replaced by POS, PO,
  and inventory exports landing in the same volume; the pipeline and everything downstream stay
  the same.

---

## Rehearsal checklist
- [ ] Opening delivered in under 90 seconds, no screen
- [ ] Each scene ends with a business "so what", not a feature
- [ ] Say "projected" or "assumed" every time you quote the value model
- [ ] Practice the 0.70 answer out loud until it sounds confident, not defensive
- [ ] Practice switching altitude mid-answer ("for the platform team: …")
- [ ] Full run under 15 minutes with pre-warmed cache
