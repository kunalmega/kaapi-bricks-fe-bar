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

## Industry KPI Targets (post-deployment)

| KPI | Current (baseline) | Target (12 months) |
|---|---|---|
| Invoice exception rate | 12% | < 3% |
| Stockout rate (store-days) | 3.5% | < 1.5% |
| Waste rate (% of ingredient cost) | ~4% | < 3% |
| Supplier on-time rate | 80–86% (range across 8 suppliers, per gold_supplier_performance) | > 92% |
| Manager minutes per delivery reconciliation | 25 min | < 2 min |
| Genie answer latency | N/A (manual) | < 5 sec for cached / table questions; document (SOP) questions measured at ~23 s in Agent mode (see evidence/09) |
| Forecast error (MAPE) | no forecast | < 15% |

---

*All figures are projections from labeled assumptions. They are not measured customer outcomes and must be validated against real operational data (ideally a timed pilot baseline in 5 stores) before a production business case.*
