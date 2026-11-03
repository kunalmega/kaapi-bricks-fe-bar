# Yoodli Demo Roleplay Script, v2 — Kaapi Bricks (30 minutes)

> ## ▶ SAY THIS FIRST: the bot's three set-up questions
>
> **1. "What are you going to show, and what's the use case?"**
> "I'm demoing **Kaapi Bricks Store Operations**, built on the Databricks Data Intelligence
> Platform. Kaapi Bricks is a 37-store filter-coffee chain. Today each store manager pieces the
> day together from five or six tools: a sales dashboard, a stock spreadsheet, supplier emails,
> paper invoices and SOP PDFs. The use case is **one app where the manager can ask, see, act and
> plan**: questions answered from governed data and SOPs, a live store dashboard, supplier
> invoices checked in seconds, and a prep plan from an ML forecast. We project about
> **$264,000 a year**, and I'll show how we'd prove it in a pilot."
>
> **2. "What's the industry?"**
> "**Retail and consumer goods**: specifically quick-service restaurants, a multi-store coffee chain."
>
> **3. "Which personas should we play?"**
> "Alex, please be the **VP of Store Operations**: you own all 37 stores, you're measured on
> stockouts, waste and consistency across stores, and you carry the savings target to the board.
> Shreya, please be the **Head of Data Platform**: you'd run this in production, so governance,
> deployment, reliability and integration are yours."

**Personas:** Alex Morgan (business) · Shreya (technical)
**What's scored** (last run's score in brackets):

| Rubric item | Last run | What earns the 5 in this script |
|---|---|---|
| Solution framing | 4/5 | Tell-show-tell in **every** segment, ending on a business line for Alex; **one** value figure (**$264,000**) everywhere |
| Production readiness and deployability | 2/5 | A new 3-minute **path to production** segment: deploy from code, dev → staging → prod, tests, rollback, bad data, identity, network |
| Blocker handling and judgment | 3/5 | Every objection gets **Acknowledge → Clarify → Answer with a trade-off → Next step**; dates come with their dependencies and the account team |
| Professionalism and delivery | 4/5 | Prepared, confident answers; no "I hope it works"; fewer fillers; clear pronunciation |

**The one rule for this run:** say only what is true. Where something isn't built yet, say
*"Today… In the pilot…"*. That counts as judgment, not weakness.

---

## Before the call (15 minutes earlier)

- [ ] **App tabs**, store set to *Koramangala, Bangalore*:
  1. Chat
  2. 📊 Live Dashboard
  3. Delivery & Invoice
  4. 🧭 Architecture
- [ ] **Invoice file:** have `invoice_mysore_po01057.pdf` open in Finder, ready to drag.
  - Last time you lost 35 seconds searching for a file on screen.
  - PO-01057 must still be open. If you approved it in a rehearsal, clean up first (`evidence/12`).
- [ ] **Warm the cache:** `python prewarm_cache.py <app URL>`.
- [ ] **Workspace tabs, for Shreya:**
  - Jobs → `kaapi_daily_ops`, run history
  - Catalog → `demand_forecaster` model, its versions and `@champion` alias
  - GitHub → `databricks.yml` and `resources/`
- [ ] **Read today's dashboard numbers before you start.** The 05:30 job rewrites the brief and the forecast every day.
- [ ] **Know your fixed numbers:**
  - $264,000 a year (~₹2.2 crore); 3.9-month payback
  - 81% of the value from invoices; the invoice line alone pays back in ~5 months
  - Food cost 23.1% of sales
  - Waste ₹4,572 per store per month, with a 3× spread between stores
  - Supplier on-time rate 83.8%; ₹8.9 lakh tied up in 147 overdue POs
  - Forecast 9.3% more accurate than the same-weekday baseline
  - 45 data-quality checks

---

## 0:00 – 2:30 · The bot's set-up questions (answer crisply, about 20 seconds each)

**Q1: "What product, and what use case?"**
> "Thanks, Alex and Shreya. I'm demoing **Kaapi Bricks Store Operations**, built on the
> Databricks Data Intelligence Platform. Kaapi Bricks is a 37-store filter-coffee chain. Today
> each store manager pieces the day together from five or six tools. This gives them **one app
> to ask, see, act and plan**: questions answered from governed data and SOPs, a live store
> dashboard, invoices checked in seconds, and a forecast-based prep plan. We project about
> **$264,000 a year**, and I'll show how we'd prove it."

**Q2: "What industry?"**
> "Retail and consumer goods: specifically quick-service restaurants, a multi-store coffee chain."

**Q3: "Which personas should we take?"**
> "Alex, please be the **VP of Store Operations**. You own all 37 stores and you're measured on
> stockouts, waste and consistency across the stores. You also carry the savings target to the
> board. Shreya, please be the **Head of Data Platform**: you'd run this in production, so
> governance, deployment, reliability and integration are yours."

---

## 2:30 – 4:30 · Frame the demo *(Solution framing)*

**Time and agenda (20 s)**
> "We have 30 minutes. I'll take about 20 for the demo and keep the rest for your questions and
> next steps. Does that still work?"

**Discovery: ask, listen, then repeat it back (40 s)**
> "Alex, before I show anything: your priorities, as I understand them, are fewer stockouts,
> less waste, stopping invoice overbilling, and getting managers' time back. Which **one number**
> do you most need to move this year?"

*(Whatever Alex names, repeat it:* "Got it: [number]. I'll come back to exactly that at the end.")*

> "Shreya, I expect your questions are: does it run on our platform, how is it governed, how do
> we know the AI is right, and **how does it get to production safely**. I'll cover all four,
> including a short path-to-production section for you near the end."

**Situation and what to watch for (60 s)**
> "Here's the situation. Every morning each of the 37 managers makes the same four decisions:
> how much to prepare, what to reorder, whether a delivery is correct, and how to answer a new
> barista. The information is spread across a sales dashboard, a stock spreadsheet, supplier
> emails, paper invoices and six SOP PDFs. So managers spend their mornings finding information
> instead of running the store.
>
> I'll follow Priya, the Koramangala manager, through one day, in four steps: **ask, see, act,
> plan**. Alex, watch for three numbers: **stockouts, invoice leakage and manager time**.
> Shreya, watch for one idea: **every number comes from governed data, and the AI only puts it
> into words**.
>
> One note: Kaapi Bricks is fictional and the data is synthetic, but the platform is real and
> deployed. I'll say each time whether a number is measured or assumed."

---

## 4:30 – 7:00 · ASK *(tell → show → tell)*

**TELL: the pain (15 s)**
> "It's 7am. Priya has two kinds of questions: about her numbers, and about how to do the job.
> Today that means four tools and a call to HQ."

**SHOW (90 s)**
1. **"Which ingredients are below reorder threshold? Show store and days of cover."**
   > "On screen: the items below reorder, with days of cover. Shreya, here's the SQL it ran,
   > against the same governed gold table HQ uses."
2. **"How do I make a Classic Filter Coffee?"** (cached)
   > "And a procedure question, answered from the recipe SOP, in about a second, because
   > repeated questions are cached. That also saves AI cost."

**TELL: business, then one technical line (30 s)**
> "Alex, for you: answers in seconds instead of four tools, and every store follows the same
> recipe and allergen procedure. That's your consistency number.
> Shreya: this is **Genie in Agent mode**, writing SQL over Unity Catalog tables and reading the
> SOP PDFs in a governed volume. The cache lives in **Lakebase**."

**Check-in (10 s)**
> "Alex, is that the kind of question managers call HQ about today?"

---

## 7:00 – 9:00 · SEE *(tell → show → tell)*

**TELL (15 s)**
> "Today Priya finds out she's low when she counts the shelf, and that a delivery is late when
> it doesn't arrive."

**SHOW (75 s).** Live Dashboard tab.
> "One screen for her store, refreshed every 10 seconds. Top tiles: **[read the overdue count
> and value]** purchase orders are past their delivery date. These are **deliveries we're still
> waiting for, not unpaid bills**.
>
> The table lists every open order; the ones marked ⛔ are past their date.
>
> Here's **today's action plan**, written at 5:30 this morning. Note '[x] of [x] numbers
> verified': the AI wrote the words, and code checked every number against the data.
>
> And **today's demand forecast**, from an ML model registered in Unity Catalog."

**TELL (30 s)**
> "Alex, that's your stockout number: Priya sees the problem days before it hits the counter,
> and chases the supplier before the morning rush. Across the chain, ₹8.9 lakh sits in 147
> overdue orders today, measured. Your procurement head gets a live supplier scorecard.
> Shreya: **Lakeflow** builds the gold tables, and **Lakebase** serves this page in about 30
> milliseconds. Keep this tab in mind: it's about to change."

---

## 9:00 – 12:30 · ACT ⭐ *(tell → show → tell, plus the objection you'll get)*

**TELL (20 s)**
> "It's 9am, and a delivery from Mysore Sweet Works arrives with a paper invoice. Today Priya
> checks it line by line against the purchase order: about 25 to 30 minutes, across about 74
> deliveries a day. Both are assumptions we'll time in the pilot."

**SHOW (2 min)**
1. Drag in `invoice_mysore_po01057.pdf` and click **Parse Invoice** (say *"parse"*, /pɑːrs/).
   > "It's reading the PDF through our governed AI gateway; this takes about ten seconds."
2. Walk the lines; point at each one, don't read the whole table.
   > "It found PO-01057 by itself. Five lines:
   > - Badam Paste matches;
   > - Rose Syrup is billed at ₹230 against a contract price of ₹200;
   > - Jaggery: 14 kg billed against 12.69 ordered;
   > - Sugar was never ordered;
   > - Palm Jaggery was ordered but never delivered.
   >
   > That's four problems a busy manager can miss."
3. Click **Approve**, then **switch to the Live Dashboard**. (Last time you skipped this.)
   > "Shreya, you asked last time whether there's a lag. Look: stock for those items has gone up,
   > the overdue count dropped by one, and the activity feed shows the approval. It's written to
   > Delta as the system of record, and to Lakebase at the same moment. No batch, no lag."

**TELL (40 s)**
> "Alex, this is the biggest line in the business case: about 30 minutes becomes under two, and
> the overcharge doesn't get paid. With food cost at 23% of sales, every rupee of leakage comes
> straight off margin. This line alone pays back in about five months.
> Shreya: Claude reads the PDF through **Unity AI Gateway**, so it's permissioned, rate-limited
> and logged. The matching is plain code against the PO, not the model. And a person approves
> every invoice."

**Expect this objection.** Alex asked it last time: *"Can it tell a negotiated price change from an overcharge?"*

1. **Acknowledge:** "That's exactly the right question; a false flag wastes Priya's time."
2. **Clarify:** "Where do negotiated prices live today: on the PO itself, or in a separate supplier contract or price list?"
3. **Answer, with the trade-off:**
   > "The check is rule-based: it compares against the price on the PO in your governed tables.
   > If renegotiated prices are on the PO, or in a contract price table we can ingest, the line
   > matches. If they only live in email, the line gets flagged. That's the safe failure, because
   > Priya still decides. The trade-off is a few more flags in the first week, until the contract
   > feed is connected."
4. **Next step:**
   > "In the pilot we'll measure the false-flag rate and the missed-overcharge rate on your real
   > invoices, against a target your finance team signs off."

---

## 12:30 – 14:30 · PLAN *(tell → show → tell; business first and last)*

**TELL: the pain (20 s)**
> "Before the lunch rush, Priya decides how much to prepare. Today that's memory and a weather
> app. Over-prepare and milk is thrown away; under-prepare and the rush runs out. Waste averages
> ₹4,572 per store a month, and it varies **3× between your best and worst stores**. That's
> measured."

**SHOW (60 s).** Chat: **"How should I prepare for today?"** It takes about 30 seconds; keep the narration short.
> "While it runs: it takes the store's ML forecast, current stock, and live weather and holidays.
> On screen: a target for each drink. Hot drinks go up because it's drizzling, cold drinks go
> down, and the stock alerts are at the bottom."

**TELL (30 s)**
> "Alex, this is your waste and consistency number: every manager plans like your best manager,
> every morning. The model is 9.3% more accurate than the 'average of past Tuesdays' rule
> managers use today; that's measured. The waste reduction, 25%, is an assumption we'll measure
> store by store in the pilot.
> Shreya: one line. The forecast is trained on gold, registered in Unity Catalog, and only
> promoted if it beats that baseline."

---

## 14:30 – 16:30 · Trust: how we know it's right, and what happens when it isn't *(for Shreya)*

**TELL (10 s)**
> "Shreya, you asked how we know the AI is right. Here are the specific checks, and what happens
> when one fails."

**SHOW + TELL (110 s).** Point at the four layers one at a time:

| Layer | Check that runs | What happens when it fails |
|---|---|---|
| **Data** | 45 Lakeflow expectations on every run, all passing today | Bad rows are dropped and counted in the pipeline's event log; business-rule breaks are flagged as warnings |
| **Forecast** | Every retrain is scored on a 14-day holdout against the same-weekday baseline | It doesn't become `@champion`, so the previous version keeps serving. Rollback is automatic |
| **Answers** | Every morning a job asks the live app 10 store-manager questions; MLflow judges score them into a history table. Latest: 1.00 correctness and safety | A drop shows up the next morning, not at the next audit. **Below 0.80 is our go/no-go line** |
| **Morning brief** | Code checks every number the AI writes against the SQL facts, and forces a rewrite if one doesn't match | Anything still unmatched is flagged, not hidden |

> "And for everything that touches money, **a person decides**: invoice approval is always
> manual. If the AI is unavailable, Priya still has the dashboard and the manual check."

---

## 16:30 – 20:00 · Path to production *(new; Production readiness)*

**TELL (15 s)**
> "Shreya, here's how this gets to production safely, and how we roll back. I'll be clear about
> what's in place today and what the pilot adds."

**SHOW (2 min 45 s).** Show the Architecture tab first, then GitHub `databricks.yml`, then the Jobs run history.

1. **Deploy from code**
   > "Today, the pipeline and the daily job are defined in one **Declarative Automation Bundle**
   > (Databricks Asset Bundles) in Git, and deployed with a single command. The two apps deploy
   > from the same repo. Nothing is hand-built in the UI."
2. **Environments and promotion**
   > "Today there's one dev target. In pilot week one we add **staging and prod targets** to the
   > same bundle, each with its own catalog and its own service principal. Prod is deployed by a
   > CI service principal, never by a person."
3. **Testing**
   > "On every pull request, CI validates the bundle, unit-tests the invoice matcher and the
   > number check, deploys to staging, and runs the evaluation there. Prod deploys only when it's
   > green. The evaluation and the proof notebooks already exist; the pilot wires them into CI."
4. **Rollback**
   > - "Code: redeploy the previous Git tag.
   > - App: redeploy the previous deployment.
   > - Model: point `@champion` back at the previous version. That's one command, no redeploy.
   > - Data: Delta time travel to restore a table, or a pipeline full refresh from bronze."
5. **Bad data and schema drift**
   > "Auto Loader brings new supplier columns into bronze without breaking anything. Silver
   > selects and casts named columns, so gold changes only when we decide. A type change fails
   > an expectation and shows up in the event log, not on Priya's screen."
6. **Security and identity**
   > - "Today: row filters keep each store manager to their own store (proven with a real
   >   store-manager identity). Secrets live in a secret scope, and every commit runs secret
   >   scanning.
   > - Pilot: column masks on customer PII; single sign-on through your identity provider; SCIM
   >   groups driving the store-access mapping; private connectivity and IP access lists set up
   >   with your cloud team and our account team."
7. **Integration**
   > "Your POS, PO and inventory exports land in one governed volume, or come in through Lakeflow
   > Connect where there's a connector. Everything downstream stays the same, so there are no
   > big changes to your current setup."
8. **A real incident, which shows the monitoring works and where the gap was** (30 s)
   > "A real example from last week: a model routing change on the gateway made some AI calls
   > fail. The gateway's request log showed the exact reason, and we fixed and rolled back the
   > routing in under an hour. But the daily job had already failed for a few mornings before
   > anyone looked. So in pilot week one, the job **alerts on failure**. I'd rather tell you that
   > now than have you find it."

**TELL (20 s)**
> "So for you, Shreya: the same tested code moves from dev to prod, every release can be rolled
> back, bad data is stopped before gold, and access is one permission model."

---

## 20:00 – 22:30 · Value and next steps *(one number; dependencies; account team)*

> "Alex, back to the number you named: **[repeat it]**.
>
> We project about **$264,000 a year** across the four capabilities:
> - **81% of it, about $215,000, is invoices**: manager time plus leakage;
> - the rest is data-gathering time, stockouts and waste.
>
> Against $50,000 a year of platform cost and $70,000 to implement, payback is about **four
> months**. These are projections from written-down assumptions. The waste line is
> conservative: the data shows about ₹55,000 of waste per store a year, double our assumption.
> So I'm **not** asking you to believe the $264,000. I'm asking for six weeks to measure it."

**The pilot**
> "Five stores, six weeks:
> - **Weeks 1–2:** time ten real invoice checks per store; connect your exports; add staging and
>   prod and the failure alerts.
> - **Weeks 3–4:** live in the five stores; each manager sees only their store; about an hour of
>   training.
> - **Weeks 5–6:** re-time the checks, run the evaluation on your own SOPs, and compare
>   stockouts and waste with each store's own baseline.
>
> **Go/no-go:** at least 50% less manager time, AI correctness of 0.80 or more, **no increase**
> in stockouts, and a false-flag rate on invoices that your finance team accepts."

**Dependencies before any date** *(last time you committed to a date alone)*
> "We can start about two weeks after three things are in place:
> 1. workspace access and the masked exports;
> 2. the five stores named;
> 3. a contact for identity and network.
>
> Before I lock a date, I'll confirm scope and resourcing with our account team this week. You'll
> have that with the plan on Friday."

**Three next steps, each with an owner**
> 1. "Alex, could you name the five stores, ideally those with the most stockout days, by Thursday?
> 2. Shreya, could your team share one month of masked invoices, POs and SOPs, and name an identity and network contact?
> 3. I'll send the pilot plan, the confirmed timeline from our account team, and an invite for the week-2 review by Friday.
>
> Does that work for both of you?"

*(Stop talking. Wait.)*

---

## 22:30 – 28:30 · Questions: use the A-C-A-N pattern every time

**A**cknowledge → **C**larify with one question → **A**nswer with specifics and a trade-off → **N**ext step.

| Likely question | Clarify with | Answer |
|---|---|---|
| **"How will you validate invoice-parsing accuracy across suppliers and formats?"** *(Yoodli's follow-up)* | "Which formats do you see most: supplier PDFs, scanned paper, or handwritten?" | "We build a hand-checked test set in weeks 1–2: about 50 real invoices across all 8 suppliers and every format. We measure two things: how accurately fields are pulled (supplier, PO, quantities, prices), and how often discrepancies are flagged correctly, both caught and false. Finance signs off the target before go-live. When the app can't match a PO, or the PO belongs to another supplier, it already warns instead of guessing. Every parse is logged in the gateway, so any result can be audited." |
| "What about handwritten or very messy invoices?" | "Roughly what share of your invoices are handwritten?" | "Those are the hardest. We measure them separately. If they fall below target, they go to manual review in the pilot; the manager still approves either way. The trade-off is less time saved on those suppliers." |
| "Who can approve an invoice?" | — | "**Today**, anyone with access to the app; every approval is recorded with a timestamp. **In the pilot**, we add a role check so only that store's manager can approve, mapped from your identity groups." |
| "How fast to all 37 stores?" | "Is there a busy season we should avoid?" | "Six-week pilot, then about eight weeks in waves of roughly ten stores. It deploys from code, so a new store is new data, not a new system." |
| "What does it cost per store?" | — | "At the assumed $50,000 a year, about $113 per store per month, plus $70,000 one-time. We'd confirm it with a sizing on your real volumes." |
| "What if the model provider is down?" | — | "The gateway falls back from Sonnet to Haiku automatically. If the gateway itself refuses, the app shows an error; it never goes around governance. Priya keeps the dashboard and the manual check." |
| "Is 1.00 correctness too good to be true?" | — | "On 10 questions, one answer moves the score by 0.10, so I don't read it as perfect. What matters is that it runs daily and the history is stored. Next is 30 or more questions from your real traces." |
| "Why Lakebase and not just Delta?" | — | "Delta computes, Lakebase serves. 37 stores refreshing every 10 seconds means point lookups and row-level writes, which is what Postgres is for: about 30 ms for the whole page. Delta stays the system of record." |
| "Do store managers really only see their own store?" | — | "In Genie and SQL, yes: Unity Catalog row filters, proven with a real store-manager identity. The app currently calls Genie as its own service principal and scopes by store; the production step is to call Genie as the signed-in user." |
| A question you can't answer | — | "I don't want to guess. I'll confirm it with our product team and include it in Friday's follow-up." *(Write it down where they can see you doing it.)* |

---

## 28:30 – 30:00 · Close *(always do this; last time you said "Okay, done")*

> "Let me wrap up. Today you saw Priya:
> - **ask** about her numbers and procedures in one place;
> - **see** her store live, with a morning plan she can trust;
> - **act** on a delivery in seconds, with four problems caught and stock updated straight away;
> - **plan** her day from a forecast, not memory.
>
> All of it is on one governed platform, deployable from code and measured every day.
>
> Alex, for you that's stockouts, waste and invoice leakage: about $264,000 a year to prove in
> six weeks. Shreya, for you it's one permission model, a safe path to production, and AI quality
> you can track.
>
> Next steps: Alex names the five stores; Shreya's team shares the masked data and an identity
> contact; I send the plan and the confirmed timeline by Friday. Thank you both."

---

## Delivery card (keep it next to the screen)

**Pronunciation**
- **parse / parsing**: /pɑːrs/, with the R. Not "pass".
- **invoice, delivery, volume, every**: a real /v/, with your top teeth on your lower lip.
- **discrepancy**: stress on the second syllable, dis-**CREP**-an-cy.
- **Kaapi** (*Kaa-pee*) Bricks · **Lakeflow** · **Lakebase** · **Unity Catalog**: slowly and clearly.

**Swap the fillers**

| Instead of | Say |
|---|---|
| "you know", "like" | *(pause)* |
| "okay?", "correct?", "does it make sense?" | a specific question: "Alex, is that how it works in your stores today?" |
| "I hope it works", "I believe it should" | "Here's how we'll measure it in the pilot: [specific]." |

**Never say these (they were wrong last time)**

| Don't say | Say |
|---|---|
| "240k" | **$264,000** |
| "overdue payments" | **overdue deliveries** |
| "only store managers can approve" | Use the "today / in the pilot" answer above |
| "I'm asking you to believe" | **"I'm not asking you to believe"** |
| "increase the stockouts" | **"no increase in stockouts"** |
| "TTL is time to delivery" | **"time to live"** |

## Timing card

| Clock | You should be at |
|---|---|
| 2:30 | Set-up questions done; framing |
| 4:30 | Ask |
| 7:00 | See |
| 9:00 | Act ⭐ |
| 12:30 | Plan |
| 14:30 | Trust |
| 16:30 | Path to production |
| 20:00 | Value and next steps |
| 22:30 | Questions |
| 28:30 | **Close, whatever happens** |

**If you're running late:**
- cut the second Ask question;
- shorten Plan to 60 seconds;
- in path to production, keep only deploy, promotion, rollback and the incident.

**Never cut** the dependencies or the close.

## Recovery

| Problem | What to do |
|---|---|
| A document answer is slow | "It's reading our SOP documents and citing them." Then ask a cached question. |
| Dashboard shows OFFLINE | Show the dashboard output in `notebooks/04` and `evidence/12`. |
| PO-01057 is already approved | Show the before/after table in `evidence/12`. |
| Parse or plan fails | Show `notebooks/04`. Then say: "This is exactly why the pilot adds failure alerts." |
