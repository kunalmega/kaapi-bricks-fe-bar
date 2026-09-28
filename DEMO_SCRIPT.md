# Kaapi Bricks — Demo Cue Card

One-page version of `DEMO.md` to keep open while presenting. Prepared answers: `ROLEPLAY_PREP.md`.

> An earlier version of this file described the retired Knowledge Assistant + Supervisor Agent demo
> (multi-agent routing, endpoint traffic splitting). That architecture was replaced by a single
> Genie Agent; this card matches what is deployed.

## Setup
- [ ] App open, store = Koramangala, Bangalore
- [ ] `python prewarm_cache.py <app URL>` run (document answers take ~20–25 s uncached)
- [ ] `sample-invoices/invoice_complex_coorg.pdf` ready
- [ ] MLflow experiment with both evaluation runs open
- [ ] Unity Catalog lineage for `gold_inventory_position` open

## Flow
| # | Tell | Show | Tell (so what) |
|---|---|---|---|
| 0 | 37 stores, ~74 invoices/day, manual checks (estimated 25–30 min each) | — | "Three things: answers, invoice check, proof it's correct" |
| 1 | Priya's 7am questions | Below-reorder items (SQL) → decoction hold time (SOP PDF) → top drinks | Data and SOPs in one governed assistant |
| 2 | Coorg delivery arrives | Upload → parse → PO match → flagged lines → Lakebase inventory → approve | Machine compares, human decides; leakage on record |
| 3 | "How do we know it's right?" | Eval: 0.00 → 0.50 Correctness, Relevance 1.00, Safety 1.00; one failed case | Root cause found and fixed; honest about the gap to 0.80 |
| 4 | "One journey, not six demos" | Lineage + PO-00006 trace | Governed, serverless, deployed from code |
| 5 | Value | ₹2.2 cr/yr projected, 3.9-month payback, assumptions listed | Next step: 6-week, 5-store pilot with a timed baseline |

## Numbers you may quote
- Measured: 14/14/7 pipeline tables; 45/45 quality checks passed; 814 inventory positions in
  Lakebase; 27 below reorder; supplier on-time 80.5–86.4%; Correctness 0.00 → 0.50; ~23 s Agent
  mode document answers.
- Assumed (say so): 25–30 min per manual check; 12% invoice exception rate; ₹2.2 crore/year;
  3.9-month payback; 2.6× 3-year ROI.
