# Business KPI Calculations — Kaapi Bricks Intelligent Store Operations

All inputs marked `[ASSUMPTION: ...]` are estimates. Replace with actual data from Kaapi Bricks operations before a real customer presentation.

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
Invoices with discrepancies     :  12%  [ASSUMPTION: based on demo data — ~12% of POs have qty/price issues]
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

## Payback Estimate

```
Databricks platform cost (est.) : $60,000/year  [ASSUMPTION: serverless + apps + FMAPI at demo scale]
Implementation cost (one-time)  : $40,000  [ASSUMPTION: 4-week pilot + data eng + app setup]
---------------------------------------------------------------------------
Year-1 net benefit              : $264,500 - $60,000 - $40,000 = $164,500
Year-2+ net benefit/year        : $264,500 - $60,000 = $204,500
Payback period                  : ~3.6 months
3-year ROI                      : ($164,500 + $204,500 × 2) / $100,000 total investment = 5.7×
```

---

## Industry KPI Targets (post-deployment)

| KPI | Current (baseline) | Target (12 months) |
|---|---|---|
| Invoice exception rate | 12% | < 3% |
| Stockout rate (store-days) | 3.5% | < 1.5% |
| Waste rate (% of ingredient cost) | ~4% | < 3% |
| Supplier on-time rate | [FILL from gold_supplier_performance] | > 92% |
| Manager minutes per delivery reconciliation | 25 min | < 2 min |
| Genie answer latency | N/A (manual) | < 5 sec |
| Forecast error (MAPE) | no forecast | < 15% |

---

*All assumptions labeled above should be validated against actual Kaapi Bricks operational data before a production business case. These numbers are for demo and illustrative purposes using the synthetic dataset.*
