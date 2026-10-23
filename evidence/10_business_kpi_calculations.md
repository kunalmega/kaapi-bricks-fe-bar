# Business KPI Calculations — Kaapi Bricks Intelligent Store Operations

**Status: projection, not a measured outcome.** Every value below is derived from inputs marked
`[ASSUMPTION: ...]`. No timed baseline trial of manual vs. assisted reconciliation has been run, and
Kaapi Bricks is a fictional company with synthetic data. Replace each assumption with the customer's
own operational data before using these numbers in a real business case. The only measured timings
in this repository are system latencies (see `evidence/06` for invoice parse time and `evidence/09`
for Genie Agent latency).

---

## KPI 1: Supplier Invoice Reconciliation — Labor Savings

**Current state:** Each store manager manually cross-checks a supplier delivery invoice against the purchase order. This involves looking up the PO in one system, comparing line items by hand, and noting discrepancies.

**Calculation:**
```
Stores                          :  37
Deliveries per store per day    :   2  [ASSUMPTION: 2 deliveries/day avg across 37 stores]
Manual reconciliation time      :  25 min/delivery  [ASSUMPTION: based on 8-line invoice]
---------------------------------------------------------------------------
Manager time saved per day      :  37 × 2 × 25 = 1,850 minutes = 30.8 hours/day

Working days per year           : 365
Annual hours saved              : 30.8 × 365 = 11,242 hours/year

Loaded hourly cost (manager)    : ₹800/hr  [ASSUMPTION: ₹12–16 LPA fully loaded]
---------------------------------------------------------------------------
Annual labor value              : 11,242 × ₹800 = ₹8,993,600 (~₹90 lakhs/year)
USD equivalent at ₹84/USD       : ~$107,000/year
```

---

## KPI 2: Invoice Leakage Prevention

**Current state:** Without automated matching, overcharged line items, unauthorized items, and quantity discrepancies go unnoticed until month-end reconciliation (if at all).

**Calculation:**
```
Deliveries per year             : 37 × 2 × 365 = 27,010 deliveries
Average invoice value           : ₹35,000  [ASSUMPTION: avg across 8 suppliers]
Invoices with discrepancies     :  12%  [ASSUMPTION: industry-typical rate; not measured from the synthetic data]
Average discrepancy per invoice : ₹2,800  [ASSUMPTION: ~8% of invoice value slips through]
---------------------------------------------------------------------------
Annual leakage prevented        : 27,010 × 12% × ₹2,800 = ₹9,075,360 (~₹91 lakhs/year)
USD equivalent                  : ~$108,000/year
```

---

## KPI 3: Stockout Reduction

**Current state:** Without real-time inventory visibility and demand forecasting, stores occasionally run out of high-demand ingredients (Coorg Arabica, Full Cream Milk) during peak hours.

**Calculation:**
```
Current stockout rate           :  3.5%  [ASSUMPTION: % of store-days with ≥1 critical stockout]
Store-days per year             : 37 × 365 = 13,505
Stockout events per year        : 13,505 × 3.5% = 473
Revenue lost per stockout event : ₹4,200  [ASSUMPTION: 2hr peak window × 35 orders × ₹60 avg]
---------------------------------------------------------------------------
Current annual stockout loss    : 473 × ₹4,200 = ₹1,986,600 (~₹20 lakhs)

Expected stockout reduction     :  60%  [ASSUMPTION: proactive alerts + demand-aware prep cuts stockouts by 60%]
Annual value recovered          : ₹1,986,600 × 60% = ₹1,191,960 (~₹12 lakhs/year)
USD equivalent                  : ~$14,200/year
```

---

## KPI 4: Waste Reduction

**Current state:** Perishable ingredients (milk, fresh coconut, cardamom) are over-ordered based on intuition rather than demand forecasts, leading to spoilage.

**Calculation:**
```
Estimated annual waste (milk + perishables) : ₹28,000/store/year  [ASSUMPTION]
Total waste across 37 stores               : 37 × ₹28,000 = ₹1,036,000
Expected waste reduction                   : 25%  [ASSUMPTION: demand-aware prep; weather/event signals]
---------------------------------------------------------------------------
Annual waste savings                       : ₹1,036,000 × 25% = ₹259,000 (~₹2.6 lakhs/year)
USD equivalent                             : ~$3,100/year
```

---

## KPI 5: Manager Time Redeemed (Non-Invoice)

**Calculation:**
```
Time saved per day per store (Genie questions vs manual report pulling): 15 min
Stores: 37
---------------------------------------------------------------------------
Annual manager hours redeemed   : 37 × 15 min × 365 / 60 = 3,384 hours/year
Annual value at ₹800/hr         : ₹2,707,200 (~₹27 lakhs/year)
```

---

## Total Annual Value Summary

| Value driver | Annual saving (₹) | Annual saving ($) |
|---|---|---|
| Invoice reconciliation labor | ₹89,93,600 | $107,000 |
| Invoice leakage prevention | ₹90,75,360 | $108,000 |
| Stockout reduction | ₹11,91,960 | $14,200 |
| Waste reduction | ₹2,59,000 | $3,100 |
| Manager time (non-invoice) | ₹27,07,200 | $32,200 |
| **TOTAL** | **₹2,22,27,120 (~₹2.2 crore)** | **~$264,500/year** |

---

## Payback and ROI (projection)

```
Annual gross value (projected)  : $264,500/year   (sum of KPIs 1–5 above, all assumption-based)
Databricks platform cost        : $50,000/year    [ASSUMPTION: serverless pipelines + Lakebase + FMAPI + apps at 37-store scale]
Implementation cost (one-time)  : $70,000         [ASSUMPTION: 8-week implementation — data eng, app setup, training, change management]
---------------------------------------------------------------------------
Annual net benefit              : $264,500 − $50,000 = $214,500

Simple payback (months)         = one-time implementation cost ÷ annual net benefit × 12
                                = $70,000 ÷ $214,500 × 12
                                = 3.9 months

3-year gross value              : 3 × $264,500 = $793,500
3-year total cost               : 3 × $50,000 + $70,000 = $220,000
3-year net ROI                  = (3-year gross value − 3-year total cost) ÷ 3-year total cost
                                = ($793,500 − $220,000) ÷ $220,000
                                = $573,500 ÷ $220,000
                                = 2.6×
```

These two formulas are the only payback and ROI definitions used in this repository (deck included).

---

## Industry KPI Targets (post-deployment), with the executive who owns each

| KPI | Owner | Current (baseline) | Target (12 months) |
|---|---|---|---|
| Invoice exception rate | CFO | 12% *[assumption]* | < 3% |
| Food cost % of sales | CFO | 23.1% *(measured, synthetic)* | held while volume grows |
| Stockout rate (store-days) | COO | 3.5% *[assumption]* | < 1.5% |
| Ingredient waste per store | COO | ₹4,572/month, 0.66% of purchases *(measured, synthetic)* | −25% |
| Manager minutes per delivery reconciliation | VP Store Operations | 25 min *[assumption]* | < 2 min |
| Supplier on-time rate | Head of Procurement | 83.8% chain, 80.5–86.4% by supplier *(measured)* | > 92% |
| Value in POs past expected date | Head of Procurement | ₹8,91,514 in 147 POs *(measured)* | halved |
| Forecast error, store × drink × day | COO | WAPE 0.47 model vs 0.52 same-weekday heuristic *(measured, notebook 05)* | beat the heuristic on every retrain (champion gate) |
| Genie answer latency | CIO | N/A (manual) | < 5 s cached / table questions; SOP questions ~15–25 s in Agent mode (notebook 03) |
| AI correctness, app end to end | CIO | 0.90–1.00 on 10 questions *(measured daily, notebook 07)* | ≥ 0.80 on the customer's own 30+ questions |

Earlier versions of this table listed waste as "~4% of ingredient cost" and a forecast target of
"MAPE < 15%". Both were replaced with measured values: daily store × drink demand is small and
noisy (a few units), so a per-cell percentage error is the wrong yardstick; the honest bar is
"better than the heuristic managers use today".

## Measured cross-checks of the value model (gold tables, 2026-10-23)

| Metric | Value | SQL (schema `kaapi_bricks`) |
|---|---|---|
| Food cost % of sales | 23.1% | `SUM(products.cost) / SUM(order_items.item_price)` |
| Average order value | ₹147.9 | `SUM(revenue) / SUM(orders)` on `gold_store_daily_kpis` |
| Revenue per store-day | ₹8,009 (~₹10.8 crore/year for 37 stores) | `AVG(revenue)` on `gold_store_daily_kpis` |
| Ingredient waste | ₹10,07,123 total; ₹4,572 per store per month; 0.66% of purchase value | `inventory_transactions` where `transaction_type = 'waste'` |
| Supplier on-time / fill rate (chain, PO-weighted) | 83.8% / 91.7% | `gold_supplier_performance` |
| Late / cancelled deliveries | 321 / 18 of 2,000 POs | `gold_delivery_exceptions` |
| Open POs past expected date | 147, ₹8,91,514 | `gold_open_purchase_orders` |

**What this changes:** the waste value line assumes ₹28k per store per year; the data shows ~₹55k,
so the $3,100 waste line is conservative. The total ($264,500) is left unchanged so that the payback
and ROI formulas above stay the single source.

---

*All figures are projections from labeled assumptions. They are not measured customer outcomes and must be validated against real operational data (ideally a timed pilot baseline in 5 stores) before a production business case.*
