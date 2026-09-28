# Kaapi Bricks — Demo Script (12–15 minutes)

**Audience:** a business stakeholder (the executive who funds it) and a technical stakeholder
(the architect who must run it).
**Story:** one morning in the life of Priya, store manager at Kaapi Bricks Koramangala.
**Structure:** every scene is Tell → Show → Tell. Prepared answers to likely questions are in
`ROLEPLAY_PREP.md`.

---

## Before you start (5 min)

Open these tabs:
1. **Kaapi Bricks app** — main chat, store set to Koramangala, Bangalore
2. **Kaapi Bricks app** — Delivery & Invoice tab
3. **Invoice PDF** — `sample-invoices/invoice_complex_coorg.pdf`
4. **MLflow experiment** — the evaluation runs (see `evidence/09` for run IDs)
5. **Unity Catalog** — lineage view of `gold_inventory_position`
6. Optional backup: `deck/FE_BAR_DECK.md`

Warm the answer cache so the first answers are instant: `python prewarm_cache.py <app URL>`.
Document questions in Agent mode take ~20–25 s when not cached; the cache avoids waiting on stage.

---

## Opening — frame before you show (1 min)

> "Kaapi Bricks runs 37 filter-coffee stores. Each manager receives about two supplier deliveries a
> day, and today checks every invoice against its purchase order by hand. We estimate 25 to 30
> minutes per delivery. That is an assumption we'd confirm with a timed baseline in a pilot.
>
> I'll show you three things: how Priya gets answers from her data and her company's SOPs in one
> place, how an invoice check goes from a manual cross-check to a reviewed result, and how we know
> the AI's answers are correct. Then I'll show you the value model and what a pilot looks like."

---

## Scene 1 — Morning questions (3 min)

**TELL:** "It's 7am. Priya has questions about her numbers and about how to run the shift. She asks
both in plain English."

**SHOW:** main chat
1. "Which ingredients are below reorder threshold? Show store and days of cover."
   → SQL over `gold_inventory_position`; 27 positions below threshold across stores, the most urgent
   at under 2 days of cover (evidence/05).
2. "How long can prepared decoction be kept before discarding?"
   → "Maximum of 4 hours … after 4 hours the coffee oxidizes and tastes stale", from the drink
   recipes SOP PDF (evidence/07).
3. "What were our top-selling drinks from February to May?"
   → Classic Filter Coffee first with 44,375 units (evidence/05).

**TELL:** "One assistant. The numbers come from governed tables through SQL she can inspect. The
procedures come from her company's own documents, with the source cited. For the business, that
means fewer calls to the area manager and faster onboarding for new baristas."

---

## Scene 2 — The delivery (4 min) ⭐

**TELL:** "It's 9am. A truck from Coorg Coffee Estates arrives with a paper invoice."

**SHOW:** Delivery & Invoice tab
1. Upload `invoice_complex_coorg.pdf` and click **Parse Invoice**.
2. `ai_parse_document` reads the PDF; an LLM structures the line items, rates, and GST.
3. The app finds the matching purchase order and compares each line with `po_line_items`.
4. Walk through the flagged lines on screen: matches, quantity differences, price differences,
   and items not on the PO. **Read the actual figures from the screen**; the captured output and
   timing for this invoice are in `evidence/06`.
5. Click **View Current Inventory**. The panel is served from Lakebase.
6. Click **Approve**. The receipt is written to `app_inventory_receipts` and the PO approval to
   `app_po_approvals`.

**TELL:** "The system does the comparison; Priya still makes the decision. Every discrepancy is on
record, which is where invoice leakage stops. One thing to be precise about: the approved receipt
flows into the inventory numbers after the next pipeline refresh and Lakebase sync, not instantly."

---

## Scene 3 — How we know it's correct (3 min)

**TELL:** "You can't put an AI assistant in front of 37 store managers on trust. You have to measure it."

**SHOW:** MLflow experiment
1. The test set: 10 real store-manager questions, 32 expected facts.
2. Run 1 (baseline): Correctness 0.00. The agent was called through the Chat-mode API, which
   cannot read documents, so it declined every SOP question. It didn't make anything up:
   Safety 1.00.
3. Run 2 (after switching to Genie Agent mode): Correctness 0.50, Relevance 1.00, Safety 1.00.
4. Open one failed case and read the judge's reason (e.g. the recipe was right but the price was
   missing). The latest iteration is in `evidence/09`.

**TELL:** "We found the root cause, fixed it, and measured again. We're not at our 0.80 target yet,
and I'd rather show you that than a perfect score we can't defend. In a pilot, this same test set
becomes your team's quality gate before any change ships."

---

## Scene 4 — Under the hood (2 min, for the architect)

**TELL:** "Here's how the pieces connect. It's one integrated journey, not six demos."

**SHOW:** Unity Catalog lineage on `gold_inventory_position`, then the architecture in `ARCHITECTURE.md`:
raw volume → Lakeflow bronze/silver/gold (45 quality checks, all passed) → Lakebase for the app →
Genie Agent over the same governed tables plus the SOP volume → the app.
Mention `evidence/08`: one purchase order, PO-00006, traced through every layer.

**TELL:** "Everything is governed in one place, runs serverless, and the pipeline, the Genie
configuration, and the app are all deployed from code."

---

## Close — value and next step (1 min)

> "We projected about ₹2.2 crore a year across 37 stores, with a payback of about four months. Those
> are assumptions, and every one is written down. So the next step isn't a rollout. It's a
> six-week pilot in five stores: time ten invoice checks per store before and after, run this
> evaluation on your own SOPs, and decide on measured numbers."

---

## Timing

| Part | Minutes |
|---|---|
| Opening | 1 |
| Scene 1 — Morning questions | 3 |
| Scene 2 — The delivery | 4 |
| Scene 3 — Evaluation | 3 |
| Scene 4 — Under the hood | 2 |
| Close | 1 |
| **Total** | **~14**, leaving time for questions |

## If something goes wrong

| Problem | Recovery |
|---|---|
| A document answer is slow (~20–25 s) | Narrate: "It's reading our SOP documents and citing them." Use a pre-warmed question next. |
| Chat returns an error | Ask a table question (inventory, suppliers); those are fast. Show the answer in `evidence/05`. |
| Invoice parse is slow | Narrate the steps (parse, structure, match). If it fails, walk through `evidence/06`. |
| Inventory panel is empty | Lakebase permissions or sync; fall back to `evidence/07` and explain the sync step. |

## Rules

1. Lead with Priya and the outcome, not the technology.
2. Pause after each answer so people can read it.
3. Say which numbers are measured and which are assumptions.
4. Answer at the altitude of the person who asked.
