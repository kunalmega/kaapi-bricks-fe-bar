# GenAI Model Outputs — Kaapi Bricks

Demonstrates: ai_parse_document invoice parsing, MAS Supervisor routing, Knowledge Assistant retrieval.

---

## Invoice Parse Example 1 — Complex Invoice with Discrepancies

**Input file:** `sample-invoices/invoice_complex_coorg.pdf`  
**Store:** Kaapi Bricks Koramangala (STR-001)  
**Triggered via:** POST /api/parse-invoice (multipart form)

**Extracted JSON (ai_parse_document output):**
```json
{
  "supplier_name": "Coorg Coffee Estates",
  "invoice_number": "CCE/2026/09/0847",
  "invoice_date": "2026-09-25",
  "po_reference": "PO-01288",
  "delivery_to": "Kaapi Bricks Koramangala",
  "items": [
    {"name": "Coorg Arabica Beans Grade AA", "quantity": 30.0, "unit": "kg", "rate": 1300.0, "amount": 39000.0},
    {"name": "Chicory (Roasted)",            "quantity": 12.0, "unit": "kg", "rate":  420.0, "amount":  5040.0},
    {"name": "Chikmagalur Robusta House Blend", "quantity": 25.0, "unit": "kg", "rate": 850.0, "amount": 21250.0},
    {"name": "Paper Cups 200ml",             "quantity":  8.0, "unit": "case","rate":  800.0, "amount":  6400.0},
    {"name": "Stirrer Sticks",               "quantity":  5.0, "unit": "case","rate":  300.0, "amount":  1500.0},
    {"name": "Araku Valley Reserve Blend",   "quantity": 10.0, "unit": "kg", "rate": 1600.0, "amount": 16000.0},
    {"name": "Cardamom (Green)",             "quantity":  2.0, "unit": "kg", "rate": 3200.0, "amount":  6400.0},
    {"name": "Coorg Arabica Beans Grade A",  "quantity": 15.0, "unit": "kg", "rate": 1100.0, "amount": 16500.0}
  ],
  "subtotal": 112090.0,
  "gst_amount": 5604.5,
  "total_amount": 117694.5
}
```

**PO match found:** PO-01288 (supplier: SUP-001, store: STR-001, status: pending)

**Discrepancy report:**
```
LINE ITEM COMPARISON — PO-01288 vs Invoice CCE/2026/09/0847

  Item                    PO qty   Inv qty   PO price  Inv price  Status
  ---------------------------------------------------------------------- 
  Coorg Arabica Beans     25.0 kg  30.0 kg   ₹1200/kg  ₹1300/kg   ⚠️ OVER-DELIVERED + PRICE UP ₹100/kg
  Chicory (Roasted)       15.0 kg  12.0 kg   ₹400/kg   ₹420/kg    ⚠️ UNDER-DELIVERED + PRICE UP ₹20/kg
  Chikmagalur Robusta     25.0 kg  25.0 kg   ₹820/kg   ₹850/kg    ⚠️ PRICE UP ₹30/kg
  Paper Cups 200ml        10.0 cs   8.0 cs   ₹800/cs   ₹800/cs    ⚠️ UNDER-DELIVERED
  Stirrer Sticks           5.0 cs   5.0 cs   ₹300/cs   ₹300/cs    ✅ MATCH
  
  NOT IN PO (extra items on invoice):
  Araku Valley Reserve Blend  10.0 kg @ ₹1600   → ₹16,000 NOT AUTHORIZED
  Cardamom (Green)             2.0 kg @ ₹3200   → ₹6,400  NOT AUTHORIZED  
  Coorg Arabica Beans Grade A 15.0 kg @ ₹1100   → ₹16,500 NOT AUTHORIZED

TOTAL DISCREPANCY: ₹38,900 in unauthorized items + ₹2,300 in price variances
```

[FILL: paste the actual JSON from a real app run and the actual discrepancy table]

---

## Invoice Parse Example 2 — Clean Invoice (No Discrepancies)

**Input file:** `sample-invoices/invoice_nandini_dairy.pdf`  
**Store:** Kaapi Bricks Indiranagar (STR-002)

**Extracted JSON:**
```json
{
  "supplier_name": "Nandini Dairy",
  "invoice_number": "ND/BLORE/2026/09/1204",
  "invoice_date": "2026-09-26",
  "po_reference": "PO-00456",
  "items": [
    {"name": "Full Cream Milk", "quantity": 240.0, "unit": "liter", "rate": 55.0, "amount": 13200.0},
    {"name": "Toned Milk",      "quantity": 100.0, "unit": "liter", "rate": 45.0, "amount":  4500.0},
    {"name": "Coconut Milk",    "quantity":  20.0, "unit": "liter", "rate": 120.0, "amount":  2400.0}
  ],
  "subtotal": 20100.0,
  "gst_amount": 1005.0,
  "total_amount": 21105.0
}
```

**Discrepancy report:** ✅ ALL ITEMS MATCH — invoice approved and inventory updated.

[FILL: paste actual output]

---

## Operations Advisor Q&A — MAS Supervisor Routing

**Question asked:** "How should I prepare for tomorrow at Koramangala? It's a long weekend."

**MAS routing decision:** Operations Advisor (MCP tool: weather + holiday calendar + Genie demand)

**Inputs to advisor:**
- Store: STR-001 (Bangalore, Koramangala)
- Date: tomorrow (2026-09-28, Sunday of a long weekend)
- Weather tool response: "Bangalore: 24°C, partly cloudy, no rain expected"
- Holiday check: "Navratri Day 3 — moderate footfall increase expected in South India"
- Demand data (Genie): avg Sunday units = 892, holiday multiplier ~1.2

**Model used:** databricks-claude-sonnet-4-6

**Model response:**
```
PREPARATION PLAN — Kaapi Bricks Koramangala — Sunday 28 Sep 2026 (Navratri long weekend)

Forecast: ~1,070 orders (normal Sunday 892 × 1.2 Navratri multiplier)

Top items to pre-batch (8–10am):
• Classic Filter Coffee: prepare 45 litres of decoction (vs 38 on a normal Sunday)
• Masala Chai: pre-heat spice mix for 200 cups
• Bella Kaapi (Jaggery): increased demand during festival — batch 30 extra

Ingredient check:
• Coorg Arabica Beans: current stock 7.1 kg, suggest ordering 15 kg by EOD today
  (1 day lead time from Coorg Coffee Estates; Sundays see 3.2 kg usage)
• Cardamom: critically low (1.2 kg). Request emergency 2 kg from Kerala Spice Traders.

Staffing note: Long weekends typically see peak footfall 9–11am and 4–7pm.
Schedule one extra barista for each peak window.

Weather: No rain — outdoor seating at full capacity. Expect cold-brew and frappe orders
above average (15% uplift on Cold Coffee historically).
```

[FILL: paste actual model response from a real app run; note the MLflow trace ID]

MLflow trace ID: [FILL: e.g. tr-abc123def456]
Experiment ID: 3268449285627906
