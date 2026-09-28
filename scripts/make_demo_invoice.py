"""Generate sample-invoices/invoice_mysore_po01057.pdf against a REAL purchase order.

PO-01057 (Mysore Sweet Works -> Koramangala STR-001, pending, 4 lines) exists in the
current synthetic dataset. The invoice plants known discrepancies so the invoice
workflow's output can be checked against an expected answer:
  - Badam Paste   : matches PO (2.15 kg @ Rs.800)
  - Rose Syrup    : price overcharge (Rs.230 vs contract Rs.200)
  - Jaggery Blocks: quantity over-bill (14.0 kg vs 12.69 kg ordered)
  - Palm Jaggery  : on the PO, missing from invoice (short delivery)
  - Sugar         : extra item not on the PO
"""
from fpdf import FPDF

LINES = [  # name, hsn, qty, unit, rate
    ("Badam Paste", "2008", 2.15, "kg", 800.0),
    ("Rose Syrup", "2106", 6.39, "liter", 230.0),
    ("Jaggery Blocks", "1701", 14.0, "kg", 80.0),
    ("Sugar", "1701", 5.0, "kg", 45.0),
]
GST = 0.05

pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(True, 15)
pdf.set_font("Helvetica", "B", 18); pdf.cell(0, 10, "MYSORE SWEET WORKS", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
for t in ["Syrups & Sweeteners  |  Mysuru, Karnataka", "GSTIN: 29ABCDE1234F1Z5 (synthetic)"]:
    pdf.cell(0, 6, t, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4); pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 8, "TAX INVOICE", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
for t in ["Invoice No: MSW-INV-2026-0729", "Invoice Date: 2026-07-29", "PO Reference: PO-01057",
          "Deliver To: Kaapi Bricks Koramangala, Bangalore (STR-001)"]:
    pdf.cell(0, 6, t, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
widths = [70, 22, 22, 18, 25, 33]
pdf.set_font("Helvetica", "B", 10)
for w_, h_ in zip(widths, ["Item", "HSN", "Qty", "Unit", "Rate (Rs.)", "Amount (Rs.)"]):
    pdf.cell(w_, 8, h_, border=1)
pdf.ln(); pdf.set_font("Helvetica", "", 10)
subtotal = 0.0
for name, hsn, qty, unit, rate in LINES:
    amt = round(qty * rate, 2); subtotal += amt
    for w_, v in zip(widths, [name, hsn, f"{qty:.2f}", unit, f"{rate:,.2f}", f"{amt:,.2f}"]):
        pdf.cell(w_, 8, v, border=1)
    pdf.ln()
gst = round(subtotal * GST, 2); total = round(subtotal + gst, 2)
pdf.ln(2)
for label, v in [("Subtotal", subtotal), ("GST @ 5%", gst), ("Total Amount", total)]:
    pdf.cell(157, 7, label, align="R"); pdf.cell(33, 7, f"{v:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
pdf.ln(6); pdf.set_font("Helvetica", "I", 8)
pdf.multi_cell(0, 5, "Synthetic invoice for the Kaapi Bricks demo (fictional company). Payment terms: Net 15.")
out = "sample-invoices/invoice_mysore_po01057.pdf"
pdf.output(out)
print(f"wrote {out}: subtotal {subtotal:.2f}, GST {gst:.2f}, total {total:.2f}")
