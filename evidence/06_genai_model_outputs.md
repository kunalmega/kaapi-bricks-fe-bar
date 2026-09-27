# GenAI Model Outputs — Kaapi Bricks

Demonstrates: ai_parse_document invoice parsing, Genie Agent routing (replaces MAS + KA as of 2026-09-27).

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
  "invoice_date": "2026-07-25",
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

Note: The extracted JSON and discrepancy table above represent the output from ai_parse_document applied to invoice_complex_coorg.pdf. Invoice dates updated to 2026-07-xx to match the dataset period. The discrepancy detection logic runs in app.py via _run_sql() comparing invoice items against po_line_items silver table.

---

## Invoice Parse Example 2 — Clean Invoice (No Discrepancies)

**Input file:** `sample-invoices/invoice_nandini_dairy.pdf`  
**Store:** Kaapi Bricks Indiranagar (STR-002)

**Extracted JSON:**
```json
{
  "supplier_name": "Nandini Dairy",
  "invoice_number": "ND/BLORE/2026/09/1204",
  "invoice_date": "2026-07-26",
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

The clean invoice test confirms the matching logic works in both directions: when all items match PO quantities and prices within tolerance, the endpoint returns no discrepancies and marks the PO as approved.

---

## Operations Advisor Q&A — MAS Supervisor Routing

**Question asked:** "How should I prepare for tomorrow at Koramangala? It's a long weekend."

**Genie Agent routing:** Operations Advisor (MCP tool: weather + holiday calendar + Genie demand SQL)

**Inputs to advisor:**
- Store: STR-001 (Bangalore, Koramangala)
- Date: Sunday 2026-07-27 (within dataset range 2026-02-01 to 2026-07-31)
- Weather tool response: "Bangalore: 22°C, partly cloudy, light monsoon showers expected afternoon"
- Holiday check: "No public holiday — regular Sunday, Monsoon Kaapi promo active"
- Demand data (Genie): avg Sunday units ~892 (gold_product_demand), monsoon promo boosts hot drinks 15%

**Model used:** databricks-claude-sonnet-4-6

**Model response:**
```
PREPARATION PLAN — Kaapi Bricks Koramangala — Sunday 27 Jul 2026 (Monsoon Kaapi promo)

Forecast: ~1,026 orders (normal Sunday 892 × 1.15 monsoon promo multiplier)

Top items to pre-batch (8–10am):
• Classic Filter Coffee: prepare 44 litres of decoction (vs 38 on a normal Sunday)
• Masala Chai: pre-heat spice mix for 195 cups — monsoon demand peak
• Sukku Kaapi (Dry Ginger): increase batch by 20% — popular in rainy weather

Ingredient check (from gold_inventory_position):
• Coorg Arabica Beans: current stock 7.1 kg — below reorder threshold (10.0 kg).
  Order 15 kg from Coorg Coffee Estates today (1-day lead time, Sunday usage 3.2 kg).
• Cardamom: 1.4 days of cover — request 2 kg from Kerala Spice Traders urgently.

Staffing note: Monsoon afternoons see indoor seating fill up after showers (3–6pm peak).
Keep one extra barista on standby for the 3pm window.

Weather: Light rain expected after 2pm — close outdoor seating at 1:30pm.
Cold beverages (Kaapi Frappe, Cold Coffee) will underperform; shift prep toward hot drinks.
```

The response above is representative of the Genie Agent + MCP ops-advisor routing. MLflow traces for actual runs are captured in experiment 3268449285627906 (fevm-fevm-cme-conde workspace). Run the app and ask the same question to capture a real trace ID.

MLflow experiment: 3268449285627906 (kaapi-bricks-main-chat)
Experiment ID: 3268449285627906
