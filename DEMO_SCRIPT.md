# Kaapi Bricks — Demo Cue Card

One-page version of `DEMO.md` to keep open while presenting. Prepared answers: `ROLEPLAY_PREP.md`.

**Story in one line:** store managers run the store from five or six disconnected tools. One app
lets them **Ask · See · Act · Plan** on one governed copy of the data.

## Setup
- [ ] App open, store = Koramangala, Bangalore; 📊 Live Dashboard open in a second tab
- [ ] `python apps/main-chat-app/prewarm_cache.py <app URL>` run (document answers take ~20–25 s uncached)
- [ ] `sample-invoices/invoice_mysore_po01057.pdf` ready, and PO-01057 still open
- [ ] MLflow experiment with the evaluation runs open
- [ ] Unity Catalog lineage for `gold_inventory_position` and the gateway services open

## Flow
| # | Tell | Show | Business impact | Databricks behind it |
|---|---|---|---|---|
| 0 | 37 stores; decisions need 5–6 tools | — | "Ask, see, act, plan in one place" | — |
| 1 · Ask | Priya's 7am questions | Below-reorder (SQL) → decoction hold time (SOP PDF) → late supplier | Seconds not tools; consistent procedures | Genie Agent · Unity Catalog · Lakebase cache |
| 2 · See | "She finds out when the shelf is empty" | Live Dashboard: 8 overdue POs ₹31,065, stock cover | Problems seen days earlier; fewer stockouts | Lakeflow gold · Lakebase 23–37 ms · Apps |
| 3 · Act | Mysore Sweet Works delivery | Upload → 4 flagged + 1 match → approve → **dashboard moves** | 30 min → < 2 min; leakage stopped | Claude via Unity AI Gateway · Delta · Lakebase write-through |
| 4 · Plan | "How should I prepare for today?" | Weekday baseline + stock → gateway MCP (weather) → plan | Less waste; ready for the rush | Gold Delta · Lakebase · gateway MCP · MLflow traces |
| 5 | "How do we know it's right?" | Eval 0.00 → 0.50 → 0.70, Relevance 1.00, Safety 1.00; a failed case | Measured, honest about the gap to 0.80 | MLflow 3 evaluation |
| 6 | "One journey, not six demos" | Lineage · PO-00006 trace · gateway services and payload log | Governed, deployed from code | Unity Catalog · AI Gateway |
| 7 | Value | ₹2.2 cr/yr projected across all four, 3.9-month payback | Next step: 6-week, 5-store pilot | — |

## Numbers you may quote
- **Measured:**
  - Pipeline: 14 / 14 / 7 tables; 45 / 45 quality checks passed.
  - Lakebase: 814 inventory positions; 27 below reorder; dashboard in 23–37 ms.
  - Suppliers: on-time 80.5–86.4%.
  - Ask: repeat questions in 1.1 s (cache); Agent mode document answers ~23 s.
  - Act: invoice parse 18.4 s, 4 / 4 discrepancies plus the control line matched; stock updated
    on approval.
  - AI quality: Correctness 0.00 → 0.50 → 0.70.
  - Gateway: rate limit 300 / min, with a real 429 in testing.
- **Assumed (say so):** 25–30 min per manual check; ~45 min a day gathering data; 12% invoice
  exception rate; 3.5% stockout days; ₹2.2 crore / year; 3.9-month payback; 2.6× 3-year ROI.
