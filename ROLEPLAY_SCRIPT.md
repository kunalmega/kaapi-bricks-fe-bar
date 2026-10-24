# PitchPerfect Roleplay Script — Kaapi Bricks (30 minutes)

**Audience:** Alex Morgan (business persona) · Shreya (technical persona)
**Scored on:**
- Demo set-up
- Tell-show-tell
- Value communication
- Professionalism and delivery
- Audience focus and personalization
- Time management
- Actionable next steps

**Plan:** about 22 minutes presenting, 6 minutes of questions, 2 minutes to close. Stop by 29:00.

> **The daily job rewrites the brief and forecast every morning at 05:30.** The figures in this
> script are from 23 Oct 2026, a Friday. On the day, say the numbers that are on your screen,
> including the weekday. The fixed facts stay the same: 27 below reorder, the invoice's four
> problems, 9.3%, 0.90–1.00, 6,606 vs 200,000, and $264k / 3.9 months.

---

## Before the call (10 minutes earlier)

- [ ] App open on **Koramangala, Bangalore** in three tabs:
  - **Chat**
  - **📊 Live Dashboard**
  - **Delivery & Invoice**
- [ ] `sample-invoices/invoice_mysore_po01057.pdf` ready to upload.
  - PO-01057 must still be open. If you approved it in a rehearsal, clean up first (see `evidence/12`).
- [ ] Warm the cache: `python prewarm_cache.py <app URL>`
- [ ] Also open, as backups:
  - `notebooks/07_evaluation_over_time.ipynb` (eval history)
  - `notebooks/02_row_level_security.ipynb` (HQ vs store manager)
  - the deck, at Slide 4 (value)
- [ ] A timer is visible to you. Water nearby. Camera at eye level.
- [ ] **If the AI judge can't see your screen, narrate what's on it.** Say "On screen you can see…" every time.

**Delivery rules for the whole call**
1. Use their names: Alex for business questions, Shreya for technical ones.
2. Signpost every move: "First…", "Now…", "So what that means for you is…".
3. Tell-show-tell in every scene, out loud: "What I'll show you" → show it → "What that means for you".
4. Pause for two seconds after each key number.
5. Say "measured" or "assumed" every time you quote a number.
6. Check in after each scene with one short question. Then move on.
7. Never read the screen word for word. Point to one thing and explain it.

---

## 0:00 – 2:30 · Opening and demo set-up *(rubric: Demo Set Up, Personalization)*

**Greeting (15 s)**
> "Hi Alex, hi Shreya, thanks for making the time. I'm Kunal, a field engineer at Databricks. We
> have 30 minutes, and I'd like to keep the last eight for your questions and next steps. Does that
> still work for both of you?"

*(Wait for a yes.)*

**Confirm their goals (45 s). This is discovery, so ask and listen.**
> "Before I show anything, I want to make sure I focus on what matters to you. Alex, from our
> earlier conversation, your priorities are cutting stockouts and waste in the stores, and
> stopping invoice overbilling. Is that still right, and is there one number you're measured on
> that you'd most like to move this year?"

*(Whatever Alex says, repeat it back and tie it in:* "Great, I'll come back to [stockout days /
food cost / invoice leakage] specifically.")*

> "Shreya, for you I expect the questions are: does this run on our platform, how is it governed,
> and how do we know the AI is right? Anything to add?"

*(Repeat it back:* "I'll make sure we cover [governance / data freshness / AI quality].")*

**Situation (45 s)**
> "Here's the situation as I understand it. Kaapi Bricks runs 37 filter-coffee stores in eight
> countries. Every morning each store manager makes the same four decisions: how much to prepare,
> what to reorder, whether a delivery is correct, and how to answer a new barista's question. The
> information for those decisions is spread across five or six tools: a sales dashboard, a stock
> spreadsheet, supplier emails, paper invoices and six SOP PDFs. So managers spend their mornings
> finding information instead of running the store."

**Agenda and the "watch for" (30 s)**
> "In the next 20 minutes I'll follow Priya, the Koramangala store manager, through one morning,
> in four steps:
> - she'll **ask** questions in plain English;
> - she'll **see** her store live;
> - she'll **act** on a supplier delivery;
> - she'll **plan** the day.
>
> Then I'll show Shreya how we know it's correct and governed, and Alex what it's worth.
>
> Alex, as we go, watch for three numbers: stockout days, invoice leakage and manager time.
> Shreya, watch for one idea: every number comes from governed data, and the AI only puts it
> into words. One note before we start: Kaapi Bricks is fictional and all the data is synthetic,
> so I'll tell you each time whether a number is measured or assumed."

**Transition:**
> "Let's start at 7am."

---

## 2:30 – 6:00 · Scene 1 — ASK *(Tell-Show-Tell)*

**TELL (20 s)**
> "What I'll show you: Priya asks one assistant about her numbers **and** her company's
> procedures. Today that means four tools and probably a call to HQ."

**SHOW (2 min 30 s).** Chat tab.

1. Type: **"Which ingredients are below reorder threshold? Show store and days of cover."**
   > "On screen you can see a table: 27 store-ingredient positions below reorder right now, the
   > most urgent with under two days of cover. That's measured from the data. And Shreya, here's
   > the SQL it ran, against the same governed table HQ uses. Nothing is a black box."
2. Type: **"How long can prepared decoction be kept before discarding?"** (cached)
   > "Now a procedure question. It answers from the drink-recipes SOP document: four hours
   > maximum, then it's discarded. That came back in about a second, because common questions are
   > cached."
3. *(Optional, if you're ahead of time)* **"Which supplier is late most often?"**
   > "Organic Alternatives India: 80.5% on time, measured."

**TELL: so what (30 s)**
> "So what that means for you, Alex: managers get answers in seconds, not by opening four tools,
> and decisions are made on data, not memory. New baristas look up recipes and allergen rules
> themselves, so all 37 stores follow the same procedure."
>
> "Shreya, technically that's **Genie in Agent mode**. It writes SQL over Unity Catalog tables and
> reads the SOP PDFs in a governed volume. The answer cache lives in **Lakebase**."

**Check-in (10 s)**
> "Alex, is that the kind of question your managers call HQ about today?"

---

## 6:00 – 8:30 · Scene 2 — SEE *(Tell-Show-Tell)*

**TELL (15 s)**
> "Today Priya finds out she's low when she counts the shelf, and finds out a delivery is late
> when it doesn't arrive. What I'll show you is her store, live, on one screen."

**SHOW (1 min 45 s).** Live Dashboard tab.
> "On screen, top left: **8 overdue purchase orders worth ₹31,065** for this one store, measured.
>
> Below that, **today's action plan**, written at 5:30 this morning:
> - priority one: chase PO-00816 with Mysore Sweet Works;
> - priority four: prepare extra Classic Filter Coffee and Masala Chai.
>
> Look at this line: '23 of 23 numbers verified'. The AI wrote the wording, but code checked that
> every number matches the data before Priya sees it.
>
> Next to it, **today's demand forecast** from our ML model: Classic Filter Coffee 14.1 against
> a usual Friday of 12.3. And the status card: live, refreshed every 10 seconds, served in about
> 33 milliseconds."

**TELL: so what (30 s)**
> "Alex, that's your stockout number. Priya sees the problem days before it hits the counter and
> chases the supplier before the morning rush. Across the chain there's ₹8.9 lakh sitting in 147
> overdue orders today; your procurement head gets a live supplier scorecard instead of anecdotes."
>
> "Shreya: **Lakeflow** builds the gold tables, **Lakebase** serves them in milliseconds, and the
> brief goes through **Unity AI Gateway**. Keep this tab in mind: it's about to change."

---

## 8:30 – 12:30 · Scene 3 — ACT, the delivery ⭐ *(Tell-Show-Tell)*

**TELL (25 s)**
> "It's 9am, and a truck from Mysore Sweet Works arrives with a paper invoice. Today Priya checks
> it line by line against the purchase order. We estimate 25 to 30 minutes per delivery, and about
> 74 deliveries a day across the chain. Both are assumptions we'd measure in a pilot. What I'll
> show you: the same check in seconds, with Priya still making the decision."

**SHOW (2 min 30 s).** Delivery & Invoice tab.

1. Upload the invoice and click **Parse Invoice**.
   > "It's reading the PDF now, through our governed AI gateway. This takes about seven seconds…"
2. Walk through the flagged lines. Point at each one; don't read the whole table.
   > "It found PO-01057 automatically. Five lines:
   > - Badam Paste matches;
   > - Rose Syrup is invoiced at ₹230 against a contract price of ₹200, so ₹30 a litre too much;
   > - Jaggery: 14 kg invoiced against 12.69 ordered;
   > - Sugar isn't on the purchase order at all;
   > - Palm Jaggery was ordered but never delivered.
   >
   > That's four problems, every one of which a tired manager can miss."
3. Click **Approve**, then switch to the **Live Dashboard**.
   > "Priya approves the lines that were on the order. Back on the dashboard: stock for those
   > items has gone up, overdue POs went from 8 to 7, and the activity feed shows the approval.
   > There was no overnight batch."

**TELL: so what (45 s)**
> "Alex, this is the biggest line in the business case. Half an hour becomes under two minutes,
> and the overcharge doesn't get paid. With food cost at 23% of sales, every rupee of leakage
> comes straight off margin. For your CFO, this line alone pays back in about five months."
>
> "Shreya: the PDF is read by Claude through **Unity AI Gateway**, which means permissioned,
> rate-limited and logged. The matching is plain code, not the model. The approval goes to Delta
> as the system of record and writes through to Lakebase, which is why the screen moved."

**Check-in (10 s)**
> "Alex, how are invoice disputes handled today: by the store, or by finance?"

*(Listen. Use the answer later in next steps.)*

---

## 12:30 – 15:00 · Scene 4 — PLAN *(Tell-Show-Tell)*

**TELL (20 s)**
> "Before the lunch rush, Priya wants to know how much to prepare. Today that's gut feel and a
> weather app. What I'll show you: a plan built on a forecasting model, adjusted for today's
> weather."

**SHOW (1 min 45 s).** Chat tab: **"How should I prepare for today?"** It takes about 30 seconds, so narrate while it runs:
> "While it works, here's what's happening. It takes the ML forecast for this store and this day,
> current stock and overdue orders from Lakebase, and live weather and holidays through a governed
> tool.
>
> On screen: the forecast basis says 'ML model plus weather adjustment'. It's drizzling, so hot
> drinks go up and cold drinks go down. Each drink has a prep target, and the stock alerts are at
> the bottom."

**TELL: so what (35 s)**
> "Alex, that's your waste number. Less milk in the bin on slow days, no running out on busy ones,
> and a new manager plans as well as an experienced one. Measured, the model is 9.3% more accurate
> than the 'average of past Fridays' rule managers use today."
>
> "Shreya: the model is trained on gold, tracked in **MLflow** and registered in **Unity Catalog**.
> It's only promoted to champion if it beats that baseline, and it's rescored every morning by
> a scheduled job."

---

## 15:00 – 18:00 · Trust: correct and governed *(for Shreya)*

**TELL (15 s)**
> "Shreya, you can't put AI in front of 37 store managers on trust. What I'll show you is how we
> measure it, and how we stop one store from seeing another's data."

**SHOW (2 min)**
1. **AI quality.** Open notebook 07, or MLflow.
   > "Every morning a scheduled job asks the live app the same 10 store-manager questions, and
   > MLflow judges score the answers. In September we started at zero: the API couldn't read
   > documents. We fixed one root cause at a time, 0.50, then 0.70. Yesterday's three runs scored
   > 0.90, 1.00 and 1.00, with safety at 1.00. To be honest about it, 10 questions is a small set,
   > so the next step is 30-plus from your real questions."
2. **Row-level security.** Open notebook 02.
   > "Same query, two identities. HQ sees all 200,000 orders. The Koramangala manager sees only
   > their store: 6,606 orders. Genie respects the same rule. It's enforced in Unity Catalog, so it
   > holds in any tool, not just in our app."

**TELL: so what (30 s)**
> "So for you, Shreya: quality is a daily number, not a one-off claim; access is one permission
> model; and every AI call except Genie goes through the gateway, which is rate-limited and logged,
> with no ungoverned fallback. A regression shows up the next morning, not at the next audit."

---

## 18:00 – 19:30 · Under the hood, one picture *(for Shreya)*

> "One sentence for the architecture: **Delta computes, Lakebase serves, Genie answers, the
> gateway governs, and Unity Catalog controls all of it.**
>
> It's one pipeline, bronze to silver to gold, with 45 data-quality checks, all passing. And one
> daily job, deployed from code: pipeline, retrain, forecast, briefs, sync, evaluation. Nothing in
> this demo is a separate tool you'd have to integrate."

**Check-in:**
> "Shreya, anything there you'd want to see in more depth after the call?"

---

## 19:30 – 22:00 · Value and next step *(rubric: Value Communication, Next Steps)*

**TELL (2 min)**
> "Alex, let me bring it back to what you said matters: **[repeat Alex's metric]**.
>
> We project about $264,000 a year, roughly ₹2.2 crore, across the four capabilities:
> - $215,000 of it, 81%, is the invoice line: manager time plus leakage;
> - the rest is manager time on data, stockouts and waste.
>
> Against $50,000 a year of platform cost and $70,000 to implement, payback is about four months.
>
> To be straight with you: those are projections from assumptions, and every one is written down.
> The waste line is conservative: the data shows about ₹55,000 of waste per store a year, double
> what we assumed.
>
> So I'm not asking you to believe the ₹2.2 crore. I'm asking for six weeks to measure it."

**The ask: specific, owned, dated**
> "Here's what I'd propose:
> - **Weeks 1–2:** we time ten real invoice checks per store in five pilot stores, and connect
>   your POS, PO and inventory exports. The pipeline doesn't change.
> - **Weeks 3–4:** the app goes live, each manager sees only their own store, and training takes
>   about an hour.
> - **Weeks 5–6:** we re-time the checks, run the AI evaluation on your own SOPs, and count stockouts.
>
> Go or no-go is on measured numbers: at least 50% less manager time, AI correctness of 0.80 or
> more, and no increase in stockouts.
>
> Three next steps:
> 1. Alex, could you nominate the five stores, ideally the ones with the most stockout days?
> 2. Shreya, could your team share one month of masked invoices, POs and SOP documents?
> 3. I'll send a pilot plan and a calendar invite for a week-2 review by Friday.
>
> Does that work for both of you?"

*(Stop talking. Wait.)*

---

## 22:00 – 28:00 · Questions (prepared answers)

Answer Alex in one or two sentences, with a number and a decision. Answer Shreya with how it
works, the trade-off, and what you'd change in production. Bridge back to value at the end.

| If they ask… | Say |
|---|---|
| **Alex:** "Are these savings real?" | "The system results are measured; the business numbers are assumptions, all labelled. That's why the first two weeks of the pilot are a stopwatch baseline. If only the invoice line works, payback is still about five months." |
| **Alex:** "What does it cost per store?" | "At the assumed $50,000 a year, about $113 per store per month, plus $70,000 one-time. We'd confirm it with a sizing on your real volumes." |
| **Alex:** "Will managers use it?" | "It replaces five tools with one, it's chat-first, and training is about an hour. Adoption is a go/no-go criterion, so we'll know by week six." |
| **Alex:** "What if the AI gets an invoice wrong?" | "Nothing is posted without the manager approving it. The AI reads the PDF; the comparison is plain code; every decision is logged." |
| **Alex:** "How fast to all 37 stores?" | "After a successful pilot, about 8 weeks. Everything deploys from code, so a new store is new data, not a new system." |
| **Shreya:** "How fresh is the data?" | "Anything done in the app, like approvals, shows within seconds through write-through. Source data is as fresh as the pipeline, which runs daily now and takes about a minute. In production I'd schedule it more often during store hours and move to Lakebase synced tables." |
| **Shreya:** "Why Lakebase, not just Delta?" | "Delta computes, Lakebase serves. 37 stores refreshing every 10 seconds is point lookups and row-level writes, which is what Postgres is for: about 33 ms for the whole dashboard. Delta stays the system of record." |
| **Shreya:** "Why are document answers slow?" | "Agent mode reads the PDFs and takes 15–25 seconds the first time. Repeat questions come from the cache in about a second, and SOPs rarely change." |
| **Shreya:** "Is 1.00 too good to be true?" | "On 10 questions, one answer moves the score by 0.10, so I don't read it as perfect. What matters is that it runs every day and is stored as history. Next is 30-plus questions from your real traces." |
| **Shreya:** "Does the app enforce row-level security?" | "Unity Catalog enforces it for Genie and SQL users, as you saw. The app currently calls Genie as its own service principal and scopes by the selected store. The production step is to call Genie on behalf of the signed-in user." |
| **Shreya:** "What if the model provider is down?" | "The gateway falls back from Sonnet to Haiku automatically. If the gateway itself refuses, the app shows an error; there's no ungoverned fallback." |
| **Shreya:** "Can the brief make up numbers?" | "Code checks every number against the facts and forces a rewrite if one doesn't match: 882 of 884 verified, and the two left are flagged, not hidden." |
| **Anyone:** a question you can't answer | "Good question. I don't want to guess. I'll confirm it and include it in Friday's follow-up." *(Write it down where they can see you doing it.)* |

**Objection pattern:** acknowledge, answer, bridge back.
> "That's a fair concern. [Answer.] And that's exactly what the pilot measures in weeks five and six."

---

## 28:00 – 30:00 · Close *(rubric: Actionable Next Steps, Time Management)*

> "We're at time, so let me wrap up. Today you saw Priya:
> - **ask** about her numbers and procedures in one place;
> - **see** her store live, with a morning plan she can trust;
> - **act** on a delivery in seconds, with four problems caught;
> - **plan** her day from a forecast instead of gut feel.
>
> All of it runs on one governed platform and is measured every day.
>
> Alex, for you that's stockout days, waste and invoice leakage. Shreya, for you it's one
> permission model and AI quality you can track.
>
> Next steps as agreed:
> - Alex nominates five stores;
> - Shreya's team shares a month of masked data;
> - I'll send the pilot plan and the week-2 review invite by Friday.
>
> Thank you both. I really appreciate the time and the questions."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| A document answer is slow | Narrate: "It's reading our SOP documents and citing them." Then ask a cached question. |
| Chat errors | Ask a table question (inventory, suppliers). If that fails, show `notebooks/03_genie_agent.ipynb`. |
| Dashboard shows OFFLINE | Show `notebooks/04` (dashboard output) and `evidence/12`. Say: "Here's the same screen from this morning's run." |
| PO-01057 already approved | Show the before/after in `evidence/12`. Clean up after the call. |
| Invoice parse fails | Show the invoice table in `notebooks/04`. Explain the four flags from there. |
| Preparation plan errors | Show the plan in `notebooks/04` (section 3). |
| Running over time | Skip the optional supplier question, cut "Under the hood" to one sentence, and **never cut the next steps**. |

## Timing card (keep it visible)

| Clock | You should be at |
|---|---|
| 2:30 | Finished the agenda; starting Ask |
| 6:00 | Starting See |
| 8:30 | Starting Act ⭐ |
| 12:30 | Starting Plan |
| 15:00 | Trust (Shreya) |
| 19:30 | Value and next steps |
| 22:00 | Questions |
| 28:00 | Close, whatever happens |

## Self-check before you hang up
- [ ] Used Alex's and Shreya's names, and tied back to the metric Alex named.
- [ ] Said "what I'll show you" and "so what that means for you" in every scene.
- [ ] Labelled every number as measured or assumed.
- [ ] Gave three next steps, each with an owner and a date.
- [ ] Finished before 30:00.
