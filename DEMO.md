# Kaapi Bricks — Demo Script (15 minutes)

**Audience:** a business stakeholder (the executive who funds it) and a technical stakeholder
(the architect who must run it).
**Story:** one day in the life of Priya, store manager at Kaapi Bricks Koramangala. Today she runs
the store from five or six disconnected tools. In the demo she runs it from one app:
**Ask · See · Act · Plan**.
**Structure:** every scene is Tell → Show → Tell. Each scene ends with its **business impact** and
the **Databricks technology** behind it. Prepared answers are in `ROLEPLAY_PREP.md`.

---

## Before you start (5 min)

Open these tabs:
1. **Kaapi Bricks app**: main chat, store set to Koramangala, Bangalore.
2. **Kaapi Bricks app**: 📊 Live Dashboard, store Koramangala (STR-001).
3. **Kaapi Bricks app**: Delivery & Invoice tab.
4. **Invoice PDF**: `sample-invoices/invoice_mysore_po01057.pdf` (matches open PO-01057).
5. **MLflow experiment**: the evaluation runs (run IDs in `evidence/09`).
6. **Unity Catalog**: lineage of `gold_inventory_position`, plus the gateway services.
7. Optional backup: `deck/FE_BAR_DECK.md`.

Warm the answer cache: `python apps/main-chat-app/prewarm_cache.py <app URL>`. Uncached
document answers take ~20–25 s; the cache makes them instant on stage.

The demo invoice is reusable only if PO-01057 is still open. After a rehearsal approval, delete the
test rows and re-sync Lakebase (see `evidence/12`, "Test clean-up").

---

## Opening — frame before you show (1 min, no screen)

> "Kaapi Bricks runs 37 filter-coffee stores. Every morning each manager makes the same decisions:
> how much to prepare, what to reorder, whether a delivery is right, how to answer a new barista.
> The information for those decisions is spread across a sales dashboard, a stock spreadsheet,
> supplier emails, paper invoices and six SOP PDFs. Managers spend their time finding information
> instead of running the store.
>
> I'll show you one app that replaces that with four things: **ask** any question, **see** the
> store live, **act** on a delivery in seconds, and **plan** the day. Then I'll show how we know the
> AI is right, what it's worth, and how we'd prove it in a pilot."

---

## Scene 1 — ASK: morning questions (3 min)

**TELL:** "It's 7am. Priya has questions about her numbers and about how to run the shift. Today
that means four tools and a phone call. Watch her ask in plain English."

**SHOW:** main chat
1. "Which ingredients are below reorder threshold? Show store and days of cover."
   → SQL over `gold_inventory_position`: 27 positions below threshold, the most urgent at under 2
   days of cover (evidence/05). Expand the SQL.
2. "How long can prepared decoction be kept before discarding?"
   → "Maximum of 4 hours …", from the drink-recipes SOP PDF, with the source cited (evidence/07).
3. "Which supplier is late most often?"
   → Organic Alternatives India, 80.5% on time (evidence/05).

**TELL (impact):** "Answers in seconds instead of opening four tools, so decisions are made on data
rather than memory. New baristas look up recipes and allergen rules themselves, so procedures stay
the same in all 37 stores."

**TELL (technology, one line):** "That's **Genie Agent mode** writing SQL over **Unity Catalog**
tables and reading the SOP PDFs in a governed Volume. Repeat questions come from a semantic cache in
**Lakebase** in about a second."

---

## Scene 2 — SEE: the live store dashboard (2 min)

**TELL:** "Today Priya finds out she's low on stock when she counts it, and that a delivery is late
when the shelf is empty."

**SHOW:** 📊 Live Dashboard, Koramangala
1. Top tiles: items below reorder, **8 overdue POs worth ₹31,065**, late deliveries, units sold.
2. Stock cover by ingredient: ⛔ below reorder · ⚠ under 21 days · ✓ OK.
3. The overdue-PO table, with days late computed live.
4. The status card: LIVE, "updated a few seconds ago", Lakebase query time of a few tens of
   milliseconds.

**TELL (impact):** "She sees the problem days before it hits the counter and chases the supplier
before the morning-rush stockout. The money tied up in late orders is on screen."

**TELL (technology):** "**Lakeflow** builds the gold stock, order and delivery views with 45
data-quality checks. **Lakebase** serves them per store in 23–37 milliseconds and refreshes every
10 seconds, which an analytics warehouse isn't built for. Keep this tab open: in the next scene it
changes."

---

## Scene 3 — ACT: the delivery (4 min) ⭐

**TELL:** "It's 9am. A truck from Mysore Sweet Works arrives with a paper invoice. Today that's 25
to 30 minutes of line-by-line checking. That's our assumption, to confirm in the pilot."

**SHOW:** Delivery & Invoice tab
1. Upload `invoice_mysore_po01057.pdf` and click **Parse Invoice** (~18 s).
2. The app extracts the lines, finds PO-01057 and compares each line against `po_line_items`.
3. Walk the flagged lines (measured, evidence/11):
   - Rose Syrup: price +₹30.
   - Jaggery: quantity +1.3 kg.
   - Sugar: not on the PO.
   - Palm Jaggery: missing from the delivery.
   - Badam Paste: matches (the control line).
4. Click **Approve**. The 3 lines that are on the PO are received, and PO-01057 is closed.
5. **Switch to the Live Dashboard tab:**
   - Badam Paste, Rose Syrup and Jaggery stock go up.
   - Overdue POs drop from 8 to 7.
   - The activity feed shows "PO-01057 … invoice approved and closed" (evidence/12).

**TELL (impact):** "The system compares; Priya decides. The check goes from half an hour to under
two minutes, the overcharge doesn't get paid, and every decision is on record. That's the biggest
cash line in the business case."

**TELL (technology):** "The invoice is read by Claude through **Unity AI Gateway**, which means
permissioned, rate-limited and logged. The matching is plain code, not the model. The approval goes
to **Delta**, the system of record, and is written straight through to **Lakebase**, which is why
the dashboard moved without waiting for a pipeline run."

---

## Scene 4 — PLAN: today's preparation (2 min)

**TELL:** "Before the lunch rush, Priya wants to know how much to prepare, and it's raining. Today
that's gut feel and a weather app."

**SHOW:** main chat → "How should I prepare for today?"
- The same-weekday baseline comes from gold; stock and overdue POs come from Lakebase.
- Live weather and holidays come from the operations advisor, through the **gateway MCP service**.
- Captured on a Tuesday (evidence/11): thunderstorm, 21 mm → Filter Coffee 12.1 → 14–15, Cold
  Coffee 3.6 → 2–3. Point at the "Store data used" block.
- About 35 s. Plans are never cached, because the weather changes.

**TELL (impact):** "Less milk thrown away on slow days, and no running out on busy ones. A new
manager plans like an experienced one."

**TELL (technology):** "Her own history from **gold Delta** sets the numbers; **Lakebase** adds
current stock; the weather comes through an **MCP service on the gateway**. **MLflow** traces
every step."

---

## Scene 5 — How we know it's correct (2 min)

**TELL:** "You can't put AI in front of 37 store managers on trust. You have to measure it."

**SHOW:** MLflow experiment
1. The test set: 10 store-manager questions, 32 expected facts.
2. Run 1: Correctness 0.00. The Chat-mode API can't read documents, so it declined; it didn't make
   anything up (Safety 1.00).
3. After the switch to Genie Agent mode: 0.50. End to end through the app, with prices from the
   governed products table: **0.70**, Relevance 1.00, Safety 1.00.
4. Open one failed case and read the judge's reason (evidence/09).

**TELL:** "We found the root cause, fixed it and measured again. We're below our 0.80 target and
we know why. In a pilot, this test set becomes your quality gate before any change ships."

---

## Scene 6 — Under the hood (1 min, for the architect)

**TELL:** "One integrated journey, not six demos."

**SHOW:** the Unity Catalog lineage on `gold_inventory_position`, then the gateway services.
- The flow: raw volume → Lakeflow bronze / silver / gold (45 checks passed) → Lakebase serving
  → Genie Agent over the same tables plus SOPs → the app.
- Gateway services: `kaapi_llm`, `kaapi_embed` and `kaapi_ops_advisor`, with their `EXECUTE`
  grants and rate limits.
- `kaapi_llm_payload`: rows from both apps.
- Mention `evidence/08`: PO-00006 traced through every layer.

**TELL:** "Delta computes, Lakebase serves, Genie answers, the gateway governs, and Unity Catalog
controls all of it. Everything is deployed from code."

---

## Close — value and next step (1 min)

> "Each capability removes a different cost: Ask and See give managers their time back and prevent
> stockouts, Act stops invoice leakage, Plan cuts waste. Together we project about ₹2.2 crore a
> year, a payback of about four months. Those are assumptions and every one is written down. So the
> next step is a six-week pilot in five stores, measured before and after, and you decide on
> the numbers."

---

## Timing

| Part | Minutes |
|---|---|
| Opening | 1 |
| Scene 1 — Ask | 3 |
| Scene 2 — See | 2 |
| Scene 3 — Act | 4 |
| Scene 4 — Plan | 2 |
| Scene 5 — Evaluation | 2 |
| Scene 6 — Under the hood | 1 |
| Close | 1 |
| **Total** | **~16**, leaving time for questions |

## If something goes wrong

| Problem | Recovery |
|---|---|
| A document answer is slow (~20–25 s) | Narrate: "It's reading our SOP documents and citing them." Use a pre-warmed question next. |
| Chat returns an error | Ask a table question (inventory, suppliers); those are fast. Show `evidence/05`. |
| Dashboard shows OFFLINE | Lakebase permissions or the instance; show `evidence/12` and its screenshot. |
| PO-01057 already approved | Show the before/after table in `evidence/12`; clean up after the session. |
| Invoice parse is slow or fails | Narrate the steps (governed read, PO match); walk through `evidence/11` §4.1. |
| Preparation plan errors | Show the captured plan in `evidence/11` §4.2. |
| Gateway returns 429 | That's the rate limit working. Wait a minute, and use it as a governance talking point. |

## Rules

1. Lead with Priya and the outcome, not the technology.
2. End every scene with the business impact first, then one line of technology.
3. Pause after each answer so people can read it.
4. Say which numbers are measured and which are assumptions.
5. Answer at the altitude of the person who asked.
