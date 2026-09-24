# Kaapi Bricks — AI Days Finale Demo Script

**Duration:** 12-15 minutes
**Audience:** CIOs, VPs, Architects

---

## Setup (before going on stage)

- [ ] MAS endpoint running (with Operations Advisor registered as sub-agent)
- [ ] Operations Advisor endpoint running
- [ ] SQL warehouse `kun` running
- [ ] Lakebase `kaapi-bricks` running
- [ ] App deployed and open in browser (Koramangala, Bangalore selected)
- [ ] Run `python prewarm_cache.py <APP_URL>` — all 6 questions cached
- [ ] MLflow experiments page open in a tab
- [ ] Lakeview dashboard open in a tab
- [ ] Eval notebooks open in tabs (with prior results visible)
- [ ] Serving Endpoints page open in a tab

---

## Act 1 — The Magic (3 min)

*App is open. Koramangala store selected.*

**Say:** "Kaapi Bricks is a South Indian filter coffee chain — 37 stores across India, Dubai, Singapore, London, San Francisco. Like any real business, store managers need answers every day. Let me show you what they see."

1. **Click:** "What's our best-selling drink this month?"
   - Instant table appears — Classic Filter Coffee at #1, 14% share
   - *Let it land for 2 seconds*

2. **Click:** "How do I make a Classic Filter Coffee?"
   - Rich recipe with tumbler-davara pour technique
   - **Say:** "That came from our barista training manual — a PDF indexed by our Knowledge Assistant."

3. **Type:** "What was our revenue in Bangalore last quarter?"
   - Brewing animation plays, then a data-driven SQL answer
   - **Say:** "That answer came from 200,000 transaction records across 14 tables — our Genie agent wrote SQL on the fly."

4. **Type:** "What should I prepare for tomorrow?"
   - Brewing animation, then a detailed prep plan with weather, calendar, product forecasts
   - **Say:** "This one checked tomorrow's live weather forecast, the Indian festival calendar, and 6 months of this store's sales patterns — then gave the manager an actionable plan with product-level numbers."

**Key line:** "One question went to training documents. One went to sales data. One checked the weather and festival calendar. Three different agents, three different data sources — invisible to the store manager. They just ask a question."

---

## Act 2 — Multi-Agent Routing (2-3 min)

*Switch to MLflow Experiments tab*

**Say:** "Let me show you what happened behind the scenes."

1. **Open** the trace for the recipe question
   - Show span waterfall: `chat_request` → `cache_lookup` → `mas_call`
   - Point at `mas_call`: "The Supervisor received this question and routed it to our Knowledge Assistant — which did vector search over our training PDFs."

2. **Open** the trace for the revenue question
   - Show: MAS routed to Genie → SQL generated and executed
   - "Same supervisor, different agent. This time it wrote SQL against 14 Delta tables."

3. **Open** the trace for "What should I prepare for tomorrow?"
   - Show 3 tool call spans: `get_weather_forecast`, `check_calendar`, `query_store_patterns`
   - **Say:** "This went to our custom Operations Advisor. Three tool calls — a live weather API, a holiday calendar check, and a historical sales query. Then the LLM reasoned across all three and generated the prep plan."

**Key line:** "Three agents, three completely different data sources — documents, Delta tables, and external APIs. Every tool call, every API response, every reasoning step — traced. You can see exactly how the agent arrived at 'prepare 105 cups of filter coffee.'"

---

## Act 3 — Evaluation Framework (2-3 min)

*Switch to eval notebooks tab*

**Say:** "How do you know the agent is actually correct? You can't ship AI without evaluation."

1. **Show** `run_mas_evaluation.ipynb` results
   - 5-question test dataset with expected answers
   - Scorers: Safety, RelevanceToQuery, Correctness
   - All green — high scores
   - "These are LLM judges. They compare the agent's answer against your ground truth."

2. **Switch to** `run_mas_evaluation_incorrect.ipynb`
   - Show the hardcoded wrong answers: "Wrong ratio — 1 tablespoon per 200ml instead of the correct 2 tablespoons per 150ml"
   - Show Correctness scorer catching it — red flag
   - **Say:** "We deliberately gave the agent wrong answers. The Correctness scorer caught every mistake."

**Key line:** "This is your test suite for AI. Every prompt change, every document update, every model swap — you run eval before shipping. Just like unit tests for code."

---

## Act 4 — Monitoring & Observability (2 min)

*Switch to Lakeview dashboard tab*

**Say:** "Evaluation tells you if the agent is correct. Monitoring tells you if it's healthy."

1. **Point to** FM Usage section
   - Token consumption across endpoints
   - Request counts, error rates

2. **Point to** Kaapi Bricks Agent section
   - Latency trend line — "If this spikes at 3am, you see it"
   - Queries by store — "Koramangala asks the most questions"
   - Recent inference logs — "Every question, every answer, every latency, logged"

3. **Point to** the timing breakdown
   - "If my agent starts responding slowly, I can see exactly which component is the bottleneck. Is it the weather API? The SQL query? The model? I don't guess — I measure."

**Key line:** "Every agent in your organization — visible in one place. Nothing is silently failing."

---

## Act 5 — CI/CD for AI (2-3 min)

*Switch to Serving Endpoints tab*

**Say:** "Now the most important question. A new model drops next week. What do you do? Today, most companies rebuild everything from scratch. Let me show you a better way."

1. **Show** the Operations Advisor endpoint
   - Current config: 100% traffic to Llama
   - "This is our custom agent. We own this endpoint."

2. **Run** `python act5_traffic_split.py split` (or show the concept)
   - 90% stays on Llama, 10% routes to Claude
   - "Both models now serve real store managers. Real questions, real answers."

3. **Explain the feedback loop:**
   - "The monitoring dashboard shows me latency and error rates for both models."
   - "The evaluation framework scores correctness for both."
   - "When the challenger wins — I promote it to 100%. If it fails — I rollback. Zero downtime."

4. **Show** rollback: `python act5_traffic_split.py rollback`
   - "One command. Back to the original model. No one noticed."

**Key line:** "A new model comes out? I don't rebuild anything. I route 10% of traffic, watch the metrics, and promote or rollback. CI/CD for AI — the same pipeline you use for microservices, applied to AI agents."

---

## Close (30 seconds)

**Say:** "Let me recap. Three agents — one reads your company documents, one queries your data, one checks the weather and festivals and gives you a prep plan. Behind the scenes: automated evaluation with LLM judges, production monitoring with latency and error tracking, and CI/CD with traffic splitting for safe model upgrades. All on one platform. All integrated. That's Kaapi Bricks on Databricks."

---

## Backup Plans

| Risk | Mitigation |
|------|------------|
| MAS endpoint slow/cold | 5 pre-cached answers bypass MAS entirely. Click examples, don't type. |
| Operations Advisor API fails | Weather fallback built in — uses seasonal estimates if API is down |
| Lakebase connection fails | App still works, just no persistence. Chat is unaffected. |
| Novel question takes too long | Brewing animation buys time. Have a backup question ready. |
| Eval notebook slow to run | Don't re-run live. Show pre-computed results. |
| Dashboard shows no data | Fire 10+ questions through app 1 hour before. |
