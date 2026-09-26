"""Generate synthetic KA PDF documents for Kaapi Bricks and upload to Databricks Volume.

Creates 6 realistic PDF documents for RAG ingestion by the Knowledge Assistant.
Requires: pip install -r requirements.txt
Uses the default Databricks CLI profile from ~/.databrickscfg.
"""
import io
import os
import sys
from fpdf import FPDF
from databricks.sdk import WorkspaceClient

# =============================================================================
# CONFIGURATION
# =============================================================================
CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data/ka_documents"

# =============================================================================
# DATABRICKS SDK CONNECTION
# =============================================================================
_profile = os.environ.get("DATABRICKS_PROFILE")
if not _profile and len(sys.argv) > 1 and sys.argv[1].startswith("--profile"):
    _profile = sys.argv[1].split("=", 1)[1] if "=" in sys.argv[1] else (sys.argv[2] if len(sys.argv) > 2 else None)

print("Connecting to Databricks workspace...")
w = WorkspaceClient(profile=_profile) if _profile else WorkspaceClient()
print(f"  Host: {w.config.host}")


# =============================================================================
# PDF HELPER
# =============================================================================
class KaapiBricksPDF(FPDF):
    """Custom PDF with Kaapi Bricks branding."""

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 50, 20)
        self.cell(0, 8, "Kaapi Bricks  |  Internal Document", align="R")
        self.ln(4)
        self.set_draw_color(80, 50, 20)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Kaapi Bricks Confidential  -  Page {self.page_no()}/{{nb}}", align="C")


def create_pdf(title, sections):
    """Create a styled PDF from a title and list of (heading, body) sections.

    Returns the PDF as bytes.
    """
    pdf = KaapiBricksPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title page content
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(80, 40, 10)
    pdf.ln(30)
    pdf.multi_cell(0, 12, title, align="C")
    pdf.set_x(pdf.l_margin)
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 8, "Kaapi Bricks Pvt. Ltd.  |  Effective 2025", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.ln(4)
    pdf.multi_cell(0, 8, "CONFIDENTIAL - For Internal Use Only", align="C")
    pdf.set_x(pdf.l_margin)

    for heading, body in sections:
        pdf.add_page()
        # Section heading
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(80, 40, 10)
        pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_draw_color(80, 50, 20)
        pdf.line(10, pdf.get_y(), 120, pdf.get_y())
        pdf.ln(6)

        # Body text
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(40, 40, 40)
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped:
                pdf.ln(4)
            elif stripped.startswith("## "):
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(80, 40, 10)
                pdf.multi_cell(0, 8, stripped[3:])
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(40, 40, 40)
            elif stripped.startswith("- "):
                pdf.multi_cell(0, 6, "  - " + stripped[2:])
                pdf.set_x(pdf.l_margin)
            else:
                pdf.multi_cell(0, 6, stripped)
                pdf.set_x(pdf.l_margin)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# DOCUMENT CONTENT
# =============================================================================

barista_training_manual = (
    "Barista Training Manual",
    [
        ("1. Welcome to Kaapi Bricks", """
Welcome to Kaapi Bricks! We are a premium South Indian filter coffee chain operating 37 locations across India and select international cities. Our mission is to deliver authentic, high-quality South Indian filter coffee experiences with consistent service at every store.

## Our Brand Values
- Quality First: We source Arabica beans from Coorg Coffee Estates, Robusta from Chikmagalur Plantations, and specialty blends from Araku Valley Organics. Our dairy comes fresh from Nandini Dairy.
- Tradition Meets Innovation: Authentic tumbler-davara service alongside modern specialty coffees.
- Consistency: Every drink must be prepared following our standard operating procedures, regardless of location.
- Customer Experience: Friendly, efficient service with an average target order time of 3-4 minutes.

## Store Locations (37 across India and worldwide)
- Bangalore (Flagship City, 10 stores): Koramangala (STR-001), Indiranagar (STR-002), Jayanagar (STR-003), Whitefield (STR-004), MG Road (STR-005), HSR Layout (STR-006), Malleshwaram (STR-007), Basavanagudi (STR-008), Electronic City (STR-009), JP Nagar (STR-010)
- Other South India (10 stores): Chennai T. Nagar (STR-011), Chennai Adyar (STR-012), Mysuru (STR-013), Hyderabad Banjara Hills (STR-014), Hyderabad Jubilee Hills (STR-015), Coimbatore (STR-016), Kochi (STR-017), Madurai (STR-018), Pondicherry (STR-019), Vizag (STR-020)
- Rest of India (10 stores): Mumbai Bandra (STR-021), Mumbai Andheri (STR-022), Delhi CP (STR-023), Delhi Hauz Khas (STR-024), Pune (STR-025), Kolkata (STR-026), Ahmedabad (STR-027), Jaipur (STR-028), Chandigarh (STR-029), Goa (STR-030)
- International (7 stores): Dubai (STR-031), Singapore (STR-032), London (STR-033), San Francisco (STR-034), Kuala Lumpur (STR-035), Sydney (STR-036), Toronto (STR-037)
"""),
        ("2. Station Setup & Opening Procedures", """
Every shift begins with a thorough station setup. Complete the following checklist before the store opens.

## Morning Opening (30 minutes before open)
- Prepare fresh coffee decoction: Use the South Indian brass filter. Add 2 heaped tablespoons (approx 20g) of Kaapi Bricks house blend (70% Chikmagalur Robusta, 30% Chicory) per 150ml of boiling water (92-96 degrees C). Allow to drip for 12-15 minutes.
- Prepare 4 batches of decoction for the morning rush. Each batch yields approximately 30 servings.
- Boil milk: Heat 5 liters of full cream milk (Nandini Dairy, SUP-004) and 3 liters of toned milk. Keep warm at 70 degrees C in the milk warmer.
- Set up spice station: Ground cardamom, dry ginger powder (sukku), jaggery blocks, palm jaggery.
- Prepare chai masala: Heat water with masala chai spice mix (Kerala Spice Traders, SUP-005), ginger, and cardamom for the chai base.
- Verify ice machine is full for cold coffee orders.
- Clean and polish all stainless steel tumblers and davaras.
- Power on POS system and verify connection to mobile app ordering platform.

## Station Layout
- Station 1 (Order Taking): POS terminal, tumbler staging area.
- Station 2 (Coffee Prep): Filter coffee makers (brass and steel), decoction dispensers, milk warmers.
- Station 3 (Specialty & Chai): Espresso machine, chai kettle, blender for frappes.
- Station 4 (Handoff): Tumbler-davara staging, order display screen, pickup counter.
"""),
        ("3. Drink Preparation Standards", """
All drinks must follow the standard recipe with precise measurements. Customizations are allowed within our defined options.

## Size Standards
- Small (Tumbler): Standard 150ml tumbler-davara serving. Base price minus Rs.15 from regular.
- Regular: Standard 200ml serving. Standard base price.
- Large: 300ml serving in a large tumbler or glass. Base price plus Rs.20.

## Sweetness Levels
Customers can choose from 4 sweetness levels:
- No Sugar: No sugar added. Popular with health-conscious customers and diabetics (~10% of orders).
- Less Sugar: Half the standard sugar amount (~25% of orders).
- Regular: Standard sugar amount, our default (~45% of orders).
- Extra Sweet: 150% sugar. Common for cold coffees and special drinks (~20% of orders).

## Temperature Options
- Hot: Standard serving temperature, 65-70 degrees C (~50% of orders).
- Warm: Slightly cooled, 45-50 degrees C (~20% of orders).
- Cold: Chilled or iced, for cold coffee variants (~30% of orders).

## Milk Alternatives and Upcharges
- Full Cream Milk (Nandini Dairy): Default, no upcharge (50% of orders)
- Toned Milk: No upcharge, lighter option (25% of orders)
- Oat Milk (Organic Alternatives India): +Rs.30 upcharge (12% of orders)
- Almond Milk: +Rs.30 upcharge (8% of orders)
- Coconut Milk: +Rs.20 upcharge (5% of orders)

## Tumbler-Davara Pouring Technique (Filter Coffee)
This is the signature Kaapi Bricks experience. It aerates the coffee and creates the perfect froth:
- Hold the davara (saucer) at waist height and the tumbler at shoulder height.
- Pour the coffee in a steady stream from tumbler to davara, extending the distance to 2-3 feet.
- Repeat 3-4 times to create a rich, frothy top layer.
- The final pour should leave a visible foam layer on the coffee.
- Serve immediately in the tumbler placed inside the davara.
"""),
        ("4. Customer Service Standards", """
Kaapi Bricks aims for a best-in-class customer experience. Follow these guidelines for every interaction.

## Greeting & Order Taking
- Greet every customer within 5 seconds of approaching the counter: "Namaskara! Welcome to Kaapi Bricks!" (or "Vanakkam!" in Tamil Nadu stores).
- For new customers, briefly explain our menu categories: Filter Coffee, Specialty Coffee, Traditional Beverages, and Seasonal Specials.
- Suggest popular items if asked: Classic Filter Coffee (our #1 seller), Strong Decoction, and Masala Chai.
- Always confirm customizations: size, sweetness, temperature, milk preference, and add-ons.
- Repeat the full order back to the customer before processing payment.

## Order Channels
We receive orders through three channels:
- In-Store (55% of orders): Standard face-to-face ordering at POS.
- Mobile App (35% of orders): Orders appear on the prep screen. Prepare and stage for customer pickup.
- Online (10% of orders): Delivery partner orders (Swiggy/Zomato). Package in insulated cups with secure lids.

## Handling Complaints
- Listen actively without interrupting.
- Apologize sincerely and offer to remake the drink immediately.
- If the issue is a wrong order, remake at no charge and let the customer keep the original.
- For quality complaints, offer a free drink coupon for their next visit.
- Log all complaints in the shift report for management review.

## Loyalty Program
- Bronze tier: 50-200 points
- Silver tier: 200-800 points
- Gold tier: 800-2,500 points
- Platinum Tumbler tier: 2,500-8,000 points
- Customers earn 1 point per Rs.10 spent. Higher tiers unlock free add-ons, birthday specials, and exclusive promotions.
- Always ask if the customer has a loyalty account and remind them to scan their app.
"""),
        ("5. Closing Procedures", """
Closing procedures ensure the store is clean, safe, and ready for the next day.

## End-of-Day Checklist
- Discard all remaining prepared decoction. Never store decoction for more than 4 hours as it turns bitter and loses aroma.
- Clean all filter coffee makers thoroughly with hot water. Remove coffee grounds and rinse the upper and lower chambers.
- Discard remaining boiled milk. Fresh milk must be prepared each morning.
- Clean all tumblers, davaras, chai kettles, and blenders with hot soapy water and sanitize.
- Wipe down all counters, prep surfaces, and the spice station with food-safe sanitizer.
- Empty and clean the drip trays under all coffee dispensers.
- Run the cleaning cycle on the espresso machine.
- Sweep and mop all floor areas, including behind the counter.
- Restock cups, stirrers, napkins, and sugar sachets for the morning shift.
- Count the register and complete the daily cash reconciliation in the POS system.
- Set the alarm system and lock all doors.

## Inventory Notes for Closing
- Check that milk supplies are sufficient for the morning. If full cream milk is below 10 liters, call Nandini Dairy for early morning delivery (lead time: 1 day).
- Check coffee bean stock. If Chikmagalur Robusta is below 5 kg, submit a reorder request to Chikmagalur Plantations (lead time: 5 days).
- Log any equipment issues in the maintenance log for the manager.
"""),
    ],
)

drink_recipes_sop = (
    "Drink Recipes & Standard Operating Procedures",
    [
        ("1. Filter Coffee", """
Our filter coffee line is Kaapi Bricks' core offering, representing the majority of sales. All filter coffees use our house-blend decoction and fresh Nandini Dairy milk.

## Classic Filter Coffee (PRD-001) - Rs.60
Our best-selling drink and the foundation of the Kaapi Bricks experience.
- Decoction: 30ml freshly dripped decoction (Kaapi Bricks house blend: 70% Chikmagalur Robusta + 30% Chicory, brewed at 92-96 degrees C, dripped 12-15 minutes)
- Milk: 120ml hot full cream milk (or customer's preferred alternative)
- Sweetener: 10g sugar (adjust per sweetness level)
- Serve in traditional tumbler-davara with the signature pour technique (3-4 pours for froth)
- Prep time: 2 minutes
- Recommended add-ons: Extra Decoction Shot, Jaggery Sweetener

## Strong Decoction (PRD-002) - Rs.70
For customers who prefer a bold, intense coffee experience.
- Decoction: 50ml concentrated decoction (double the standard amount)
- Milk: 100ml hot full cream milk
- Sweetener: 8g sugar
- Higher decoction-to-milk ratio creates a more intense flavor
- Prep time: 2 minutes
- Recommended add-on: Chicory Boost

## Bella Kaapi - Jaggery (PRD-003) - Rs.65
Traditional South Indian coffee sweetened with jaggery instead of sugar.
- Decoction: 30ml standard decoction
- Milk: 120ml hot full cream milk
- Sweetener: 15g crushed jaggery (Mysore Sweet Works, SUP-006), dissolved in decoction while hot
- The jaggery adds a caramel-like sweetness and earthy depth
- Prep time: 3 minutes (jaggery dissolving step)

## Sukku Kaapi - Dry Ginger (PRD-004) - Rs.65
A traditional medicinal coffee with dry ginger, popular in South India.
- Decoction: 30ml standard decoction
- Dry ginger powder (sukku): 2g (Kerala Spice Traders, SUP-005)
- Milk: 100ml hot full cream milk
- Sweetener: 10g palm jaggery
- Note: Sukku kaapi is traditionally consumed for its digestive benefits
- Prep time: 3 minutes

## Degree Coffee (PRD-005) - Rs.60
Named after the traditional "degree" purity standard for milk.
- Decoction: 30ml standard decoction
- Milk: 130ml hot full cream milk (must be unadulterated "degree" quality)
- Sweetener: 10g sugar
- The higher milk ratio creates a milder, creamier profile
- Prep time: 2 minutes

## Mysore Filter Coffee (PRD-006) - Rs.70
A regional variant using a higher chicory blend.
- Decoction: 35ml decoction from Mysore-style blend (60% Robusta, 40% Chicory)
- Milk: 120ml hot full cream milk
- Sweetener: 10g sugar
- The extra chicory creates a distinctive nutty, slightly bitter flavor
- Prep time: 2 minutes

## Kumbakonam Degree Coffee (PRD-007) - Rs.75
Premium filter coffee inspired by the famous Kumbakonam style from Tamil Nadu.
- Decoction: 40ml concentrated decoction using Araku Valley Blend (SUP-003)
- Milk: 110ml hot full cream milk (boiled with a pinch of cardamom)
- Sweetener: 12g sugar
- Must use premium Araku Valley beans. Cost per serving is higher at Rs.1500/kg for beans.
- Prep time: 3 minutes

## Chicory Blend (PRD-008) - Rs.55
Our most affordable option, with a higher chicory ratio for a unique flavor.
- Decoction: 25ml decoction from chicory-forward blend (50% Robusta, 50% Chicory)
- Milk: 130ml hot toned milk
- Sweetener: 8g sugar
- Popular with budget-conscious customers and chicory lovers
- Prep time: 2 minutes
"""),
        ("2. Specialty Coffee", """
Modern coffee preparations that blend South Indian traditions with international coffee culture.

## Cold Coffee (PRD-009) - Rs.100
- Coffee: 40ml chilled decoction
- Milk: 150ml cold full cream milk
- Sugar: 15g (dissolved in decoction first)
- Ice: 200g
- Blend for 20 seconds until frothy
- Prep time: 2 minutes

## Kaapi Frappe (PRD-010) - Rs.120
- Espresso: Double shot (60ml) from espresso machine
- Milk: 120ml cold full cream milk
- Sugar: 15g
- Ice: 250g
- Blend for 30 seconds until smooth and icy
- Top with whipped cream (optional add-on)
- Prep time: 3 minutes

## Caramel Kaapi (PRD-011) - Rs.130
- Espresso: Double shot
- Caramel syrup: 25ml (Mysore Sweet Works)
- Milk: 150ml steamed milk
- Drizzle caramel on top
- Prep time: 3 minutes

## Hazelnut Kaapi (PRD-012) - Rs.140
- Espresso: Double shot
- Hazelnut syrup: 25ml
- Milk: 150ml steamed milk
- Prep time: 3 minutes

## Mocha Kaapi (PRD-013) - Rs.150
- Espresso: Double shot
- Cocoa powder: 10g (Araku Valley Organics)
- Milk: 150ml steamed milk
- Sugar: 12g
- Top with chocolate drizzle
- Prep time: 4 minutes

## Espresso Shot (PRD-014) - Rs.80
- Single or double shot (30ml/60ml) from espresso machine
- Served in a small cup
- Use Coorg Arabica beans (SUP-001) for espresso
- Prep time: 1 minute
"""),
        ("3. Traditional Beverages", """
## Masala Chai (PRD-015) - Rs.50
Our second most popular drink after filter coffee.
- Water: 120ml
- Masala chai spice mix: 3g (Kerala Spice Traders blend of ginger, cardamom, cinnamon, cloves, black pepper)
- Tea leaves: 5g CTC tea
- Milk: 80ml full cream milk
- Sugar: 10g
- Boil water with spices for 3 minutes, add tea leaves, simmer 2 minutes, add milk, bring to boil
- Strain and serve hot
- Prep time: 5 minutes

## Irani Chai (PRD-016) - Rs.55
- Water: 100ml
- Tea leaves: 6g CTC tea (strong brew)
- Milk: 100ml full cream milk (reduced/thickened)
- Sugar: 12g
- The signature is the thick, sweet, milky preparation
- Prep time: 6 minutes

## Ginger Tea (PRD-017) - Rs.45
- Water: 150ml
- Fresh ginger: 5g crushed
- Tea leaves: 4g CTC tea
- Milk: 50ml (optional)
- Sugar: 8g
- Prep time: 4 minutes

## Cardamom Tea (PRD-018) - Rs.50
- Water: 150ml
- Cardamom: 2 pods, crushed (Kerala Spice Traders)
- Tea leaves: 4g CTC tea
- Milk: 60ml
- Sugar: 8g
- Prep time: 4 minutes

## Rose Milk (PRD-019) - Rs.60
- Cold milk: 200ml full cream milk
- Rose syrup: 25ml (Mysore Sweet Works)
- Serve chilled with ice
- Garnish with crushed pistachios (optional)
- Prep time: 1 minute

## Badam Milk (PRD-020) - Rs.70
- Hot/cold milk: 200ml full cream milk
- Badam paste: 20g (Mysore Sweet Works)
- Sugar: 10g
- Saffron strands: 2-3 for garnish
- Prep time: 2 minutes

## Paneer Soda (PRD-021) - Rs.40
A classic South Indian carbonated drink (not related to paneer cheese).
- Soda water: 200ml chilled
- Lemon juice: 15ml
- Sugar syrup: 20ml
- Salt: pinch
- Serve ice cold
- Prep time: 1 minute

## Nannari Sherbet (PRD-022) - Rs.45
- Water: 200ml chilled
- Nannari syrup: 30ml (Kerala Spice Traders)
- Lemon juice: 10ml
- Ice: 100g
- Prep time: 1 minute
"""),
        ("4. Seasonal & Special Drinks", """
## Mango Lassi (PRD-023) - Rs.80 (Seasonal - Summer)
- Fresh mango pulp: 80ml
- Yogurt: 100ml
- Sugar: 10g
- Cardamom powder: 1g
- Ice: 100g
- Blend until smooth
- Prep time: 2 minutes
- Available April through August only

## Buttermilk / Majjige (PRD-024) - Rs.35
- Yogurt: 80ml
- Water: 150ml
- Salt, curry leaves, green chili, ginger
- Blend and serve chilled
- Prep time: 2 minutes

## Filter Coffee Ice Cream Float (PRD-025) - Rs.120 (Seasonal)
- Chilled decoction: 40ml
- Cold milk: 100ml
- Vanilla ice cream: 1 scoop
- Sugar: 10g
- Serve in a tall glass
- Prep time: 2 minutes

## Pista Kaapi (PRD-026) - Rs.110
- Decoction: 30ml
- Milk: 120ml hot
- Pistachio paste: 15g
- Sugar: 10g
- Garnish with crushed pistachios
- Prep time: 3 minutes

## Jaggery Cold Brew (PRD-027) - Rs.100 (Seasonal)
- Cold brew concentrate: 60ml (Coorg Arabica beans, steeped 18 hours)
- Jaggery syrup: 20ml
- Cold milk: 100ml
- Ice: 150g
- Prep time: 2 minutes (requires advance cold brew preparation)

## Monsoon Malabar Pour-Over (PRD-028) - Rs.90 (Seasonal)
- Monsoon Malabar beans (Araku Valley Organics): 15g freshly ground
- Pour-over method: 200ml water at 92 degrees C, slow pour over 3 minutes
- Served black with optional milk and sugar on the side
- Premium single-origin experience
- Prep time: 5 minutes
"""),
        ("5. Add-ons Reference", """
All add-ons are available with any drink. Prices listed are customer-facing prices; cost to Kaapi Bricks is shown in parentheses.

## Add-on Options
- TOP-001: Extra Decoction Shot - Rs.20 (cost Rs.5) - Most popular add-on, ~30% of add-on orders
- TOP-002: Jaggery Sweetener - Rs.15 (cost Rs.3) - Replaces sugar with traditional jaggery
- TOP-003: Chicory Boost - Rs.15 (cost Rs.4) - Adds extra chicory for nutty depth
- TOP-004: Cardamom - Rs.10 (cost Rs.2) - Fresh ground cardamom sprinkle
- TOP-005: Ice Cream Float - Rs.30 (cost Rs.8) - Vanilla ice cream scoop added
- TOP-006: Whipped Cream - Rs.25 (cost Rs.6) - For specialty and cold coffees
- TOP-007: Chocolate Drizzle - Rs.20 (cost Rs.5) - Cocoa drizzle topping
- TOP-008: Vanilla Shot - Rs.20 (cost Rs.5) - Vanilla flavor enhancement
- TOP-009: Hazelnut Shot - Rs.25 (cost Rs.7) - Hazelnut syrup shot
- TOP-010: Cinnamon - Rs.10 (cost Rs.2) - Ground cinnamon sprinkle
- TOP-011: Nutmeg - Rs.10 (cost Rs.2) - Freshly grated nutmeg
- TOP-012: Palm Jaggery - Rs.15 (cost Rs.4) - Premium sweetener alternative

## Add-on Guidelines
- Extra Decoction Shot should only be added to filter coffee drinks, not tea or milk-based beverages.
- Jaggery and Palm Jaggery should be dissolved in hot liquid; do not add directly to cold drinks.
- Ice Cream Float is not recommended for hot beverages; suggest cold coffee or frappe instead.
"""),
        ("6. Customization Rules & Quality Standards", """
## Temperature Standards
- Hot drinks: Serve at 65-70 degrees C. Never exceed 75 degrees C (burn risk).
- Warm drinks: Serve at 45-50 degrees C.
- Cold drinks: Serve at 4-8 degrees C with adequate ice.

## Decoction Quality Checks
- Fresh decoction must drip for 12-15 minutes for proper extraction. Rushing creates weak, watery coffee.
- Maximum decoction hold time: 4 hours. After this, discard and prepare fresh.
- Decoction should be dark brown with a rich aroma. Pale decoction indicates insufficient coffee or improper grind.
- The Robusta-Chicory ratio must be maintained at 70:30 for house blend. Mysore variant uses 60:40.

## Milk Standards
- Always use Nandini Dairy milk for consistency. Full cream milk is the default.
- Milk must be boiled before use (Indian dairy safety requirement).
- Do not re-boil milk more than once; it affects taste and texture.
- Alternative milks (oat, almond, coconut) do not need boiling but should be heated to serving temperature.

## Service Quality
- Every filter coffee must be served with the tumbler-davara pour technique. This is our signature.
- Specialty coffees served in branded cups with the Kaapi Bricks logo visible.
- Traditional beverages (chai, rose milk, badam milk) served in glass tumblers.
- All drinks must be served within 4 minutes of order placement.
"""),
    ],
)

food_safety_policy = (
    "Food Safety Policy",
    [
        ("1. General Food Safety Principles", """
Kaapi Bricks is committed to the highest standards of food safety across all 37 locations. We comply with FSSAI (Food Safety and Standards Authority of India) regulations and maintain FSSAI licenses at every store.

## Regulatory Compliance
- All stores must maintain a valid FSSAI license (14-digit registration number displayed prominently).
- International stores must comply with local food safety regulations in addition to Kaapi Bricks standards.
- Annual third-party food safety audits are mandatory. Target score: 90+ out of 100.
- All staff must complete FSSAI-approved food handler training before their first shift.

## Key Principles
- First In, First Out (FIFO): Always use oldest stock first. Date-label all containers.
- Temperature Control: Maintain cold chain for dairy (below 4 degrees C) and hot holding for prepared beverages (above 63 degrees C).
- Personal Hygiene: Handwashing every 30 minutes, before handling food, after breaks, and after handling cash.
- Cross-Contamination Prevention: Use separate equipment for allergen-containing items.
"""),
        ("2. Ingredient Handling & Storage", """
## Coffee Beans & Chicory
- Store in airtight containers in a cool, dry area (18-22 degrees C, below 60% humidity).
- Shelf life: Whole beans 6 months, ground coffee 2 weeks after opening.
- Coorg Arabica Beans (SUP-001): Store separately from Robusta to prevent flavor cross-contamination.
- Chikmagalur Robusta (SUP-002): Keep sealed until ready for grinding.
- Chicory (SUP-002): Hygroscopic; seal immediately after use to prevent moisture absorption.
- Araku Valley Blend (SUP-003): Premium beans; store in dedicated container with date label.

## Dairy Products
- Full Cream Milk (Nandini Dairy, SUP-004): Refrigerate at 2-4 degrees C. Use within 2 days of delivery.
- Toned Milk: Same storage as full cream.
- Oat Milk and Almond Milk (Organic Alternatives India, SUP-008): Store at room temperature until opened, then refrigerate and use within 5 days.
- Coconut Milk: Refrigerate after opening, use within 3 days.
- Always boil dairy milk before use. This is a mandatory FSSAI requirement for non-pasteurized milk.

## Spices & Flavoring
- Cardamom, dry ginger, chai spice mix (Kerala Spice Traders, SUP-005): Store in airtight jars away from moisture. Shelf life: 6 months.
- Jaggery, palm jaggery (Mysore Sweet Works, SUP-006): Store in dry area. Absorbs moisture quickly; keep sealed. Shelf life: 12 months if dry.
- Rose syrup, nannari syrup: Refrigerate after opening. Shelf life: 3 months.

## Packaging Materials
- Paper cups and stirrer sticks (Chennai Packaging Co., SUP-007): Store in dry, pest-free area.
- Tumblers and davaras: Wash and sanitize daily. Polish with dry cloth before service.
"""),
        ("3. Allergen Management", """
## Common Allergens in Our Products
Kaapi Bricks products may contain the following allergens. Staff must be trained to identify and communicate allergen risks:

- Dairy (Milk): Present in virtually all our drinks. Non-dairy alternatives available.
- Tree Nuts: Almond milk, badam milk (PRD-020), pistachio in Pista Kaapi (PRD-026), hazelnut syrup.
- Soy: Some flavoring syrups may contain soy lecithin.
- Gluten: Not commonly present, but some flavoring syrups may contain traces.
- Coconut: Coconut milk alternative.

## Allergen Communication Protocol
- Menu boards must clearly mark drinks containing common allergens.
- When a customer reports an allergy, the barista must:
  1. Confirm the specific allergen.
  2. Check all ingredients including syrups and add-ons.
  3. Use freshly cleaned equipment to prevent cross-contact.
  4. If unsure, consult the manager before preparing the drink.
- Almond milk and coconut milk must be stored and dispensed separately from dairy milk.
- The blender must be cleaned between orders when switching between nut-based and dairy milks.

## Allergen Incident Protocol
- If a customer reports an allergic reaction, call emergency services immediately.
- Document the incident fully: what was ordered, what was served, ingredients used.
- Notify the store manager and regional manager within 1 hour.
"""),
        ("4. Prepared Product Shelf Life", """
These are maximum hold times for prepared items. Discard after the time limit regardless of appearance.

## Beverages
- Prepared decoction (filter coffee): Maximum 4 hours. After this, the coffee oxidizes and tastes stale.
- Boiled milk: Maximum 4 hours at hot holding temperature (above 63 degrees C). Discard if temperature drops below 63 degrees C for more than 30 minutes.
- Brewed chai: Maximum 2 hours. Chai loses flavor rapidly.
- Cold coffee (prepared): Serve immediately. Do not hold for more than 15 minutes.
- Cold brew concentrate: Maximum 48 hours refrigerated.

## Prepared Ingredients
- Dissolved jaggery syrup: Maximum 8 hours at room temperature.
- Badam paste (prepared): Maximum 3 days refrigerated.
- Rose milk mixture: Maximum 24 hours refrigerated.
- Nannari sherbet mixture: Maximum 24 hours refrigerated.
- Mango pulp (opened): Maximum 24 hours refrigerated.

## Daily Discard Log
- At closing, log all discarded items in the waste log.
- Calculate waste percentage weekly. Target: below 5% of total ingredient cost.
- High waste items should be reviewed for order quantity adjustment.
"""),
        ("5. Health Inspection Preparation", """
## FSSAI Inspection Readiness
Kaapi Bricks maintains inspection-ready status at all times. The following must always be in order:

## Documentation Checklist
- FSSAI license displayed prominently near the entrance.
- Staff food handler certificates on file (updated annually).
- Temperature logs for refrigerators and milk warmers (recorded 3 times daily).
- Pest control records (monthly treatment by licensed operator).
- Supplier invoices and quality certificates for all ingredients.
- Cleaning schedule with sign-off sheets.
- Waste disposal records.

## Physical Standards
- All surfaces must be clean and sanitized at all times.
- No personal belongings in the food preparation area.
- Staff must wear clean uniforms, hair nets/caps, and no jewelry while preparing food.
- Handwashing stations must be stocked with soap, paper towels, and sanitizer.
- Refrigerator temperatures must be below 4 degrees C; verified with calibrated thermometer.
- Pest-free environment: No evidence of rodents, insects, or other pests.
- Proper waste segregation: Wet waste, dry waste, and recyclables in labeled bins.

## Common Deficiencies to Avoid
- Unlabeled containers in storage areas.
- Expired ingredients on shelves (check FIFO compliance daily).
- Temperature logs not up to date.
- Missing or expired staff health certificates.
- Cleaning supplies stored near food items.
"""),
    ],
)

franchise_operations_guide = (
    "Franchise Operations Guide",
    [
        ("1. Kaapi Bricks Franchise Overview", """
Kaapi Bricks is expanding through a franchise model across India and select international markets. This guide covers everything a prospective franchisee needs to know.

## Brand History
Kaapi Bricks was founded with the mission of making authentic South Indian filter coffee accessible to everyone. Starting with our flagship store in Koramangala, Bangalore, we have grown to 37 company-owned locations across India and internationally.

## Business Model
- 37 company-owned stores as of 2025, with franchise expansion planned.
- Average store revenue varies by city tier and location. Bangalore flagships perform highest.
- Mobile app users account for 60% of our customer base with 35% of orders placed through the app.
- Loyalty program with 4 tiers (Bronze, Silver, Gold, Platinum Tumbler) drives repeat purchases.
- Product mix: ~55% filter coffee, ~20% traditional beverages, ~15% specialty coffee, ~10% seasonal.

## Why Franchise With Kaapi Bricks?
- Proven model across 37 stores in diverse markets (metro cities, tier-2 cities, international).
- Strong brand recognition in the South Indian coffee segment.
- Comprehensive training program and ongoing operational support.
- Centralized supply chain with quality-vetted suppliers.
- Technology platform: POS, mobile app, loyalty program, inventory management.
"""),
        ("2. Financial Requirements", """
## Investment Breakdown (Indian Market)
- Franchise fee: Rs.25,00,000 (one-time, non-refundable)
- Store build-out: Rs.15,00,000 - Rs.25,00,000 (depending on city and location)
- Equipment package: Rs.8,00,000 - Rs.12,00,000 (filter coffee makers, espresso machine, chai kettles, refrigeration, POS)
- Initial inventory: Rs.2,00,000 - Rs.3,00,000
- Working capital (first 3 months): Rs.5,00,000 - Rs.8,00,000
- Total estimated investment: Rs.55,00,000 - Rs.73,00,000

## Ongoing Fees
- Royalty: 6% of gross monthly revenue
- Marketing fund contribution: 2% of gross monthly revenue
- Technology fee: Rs.5,000/month (POS, app, loyalty platform)

## Revenue Expectations
- Typical break-even: 12-18 months depending on location.
- Average daily orders for a mature store: 150-300 (varies significantly by location).
- Average order value: Rs.80-120.
- Gross margin target: 65-70% (coffee and beverages have high margins).
"""),
        ("3. Site Selection & Build-Out", """
## Location Criteria
- Minimum 300 sq ft carpet area for Indian stores; 600 sq ft for international.
- High foot traffic: Near colleges, IT parks, commercial areas, or busy residential neighborhoods.
- Seating capacity: 8-16 for Indian stores, 14-24 for international.
- Visibility: Ground floor with street-facing frontage preferred.
- Proximity: Minimum 2 km radius from existing Kaapi Bricks stores.
- Parking: While not mandatory, available parking increases walk-in traffic by 15-20%.

## Store Layout (Standard Indian Format - 400 sq ft)
- Counter and POS area: 60 sq ft
- Coffee preparation area: 80 sq ft (includes filter coffee station, espresso machine, chai station)
- Storage and refrigeration: 40 sq ft
- Customer seating: 180 sq ft (10-12 seats)
- Restroom: 40 sq ft
- All stores follow the Kaapi Bricks design template: warm wood tones, brass accents, traditional South Indian motifs, and our signature coffee filter wall art.

## Build-Out Process
- Kaapi Bricks provides the store design template and approved vendor list.
- Build-out timeline: 45-60 days from lease signing to store opening.
- All equipment must be from Kaapi Bricks-approved suppliers to ensure consistency.
- FSSAI license application should begin immediately upon lease signing (processing time: 30-45 days).
"""),
        ("4. Training & Launch", """
## Franchisee Training Program
- Duration: 2 weeks at the Kaapi Bricks Training Center (Koramangala flagship, STR-001)
- Week 1: Coffee knowledge, decoction preparation, tumbler-davara technique, recipe mastery for all 28 drinks.
- Week 2: Operations management, inventory systems, POS training, customer service, FSSAI compliance.
- Final exam: Must demonstrate proficiency in preparing all 28 drinks and pass the operations quiz (80% minimum).

## Staff Training
- Each store requires a minimum of 4 trained baristas and 1 shift supervisor.
- Kaapi Bricks provides a 1-week on-site training program for all initial staff.
- Ongoing training: Monthly video modules on new recipes, seasonal specials, and operational updates.
- Regional managers conduct quarterly store visits for quality assurance.

## Grand Opening Playbook
- Standard Grand Opening promotion: Buy One Get One 50% off for the first 2 weeks (PRM-001 template).
- Local marketing: Flyers, social media posts (content provided by Kaapi Bricks marketing team).
- Sampling: Free small filter coffees for the first 100 customers on opening day.
- Media outreach: Local food bloggers and influencers invited for a pre-opening tasting.
- Target: 200+ customers on opening day.
"""),
    ],
)

equipment_maintenance_guide = (
    "Equipment Maintenance Guide",
    [
        ("1. Equipment Overview", """
Every Kaapi Bricks store uses standardized equipment to ensure consistency. Proper maintenance extends equipment life and ensures beverage quality.

## Core Equipment List
- South Indian Filter Coffee Maker (Brass/Stainless Steel): 4-6 per store, used for decoction preparation
- Espresso Machine (Semi-automatic): 1 per store, for specialty coffee drinks
- Chai Kettle (5L Stainless Steel): 2 per store, for masala chai and tea preparation
- Milk Warmer (Electric, 5L): 2 per store, maintains milk at serving temperature
- Commercial Blender: 1 per store, for frappes, cold coffees, and blended drinks
- Refrigerator (Double-door Commercial): 1 per store, for dairy and perishable storage
- Ice Machine: 1 per store, 50 kg/day capacity
- Coffee Grinder (Burr): 1 per store, for grinding beans fresh
- POS Terminal: 1-2 per store, integrated with mobile app orders
"""),
        ("2. Daily Cleaning Procedures", """
## South Indian Filter Coffee Maker
- After each batch: Discard used coffee grounds, rinse both chambers with hot water.
- End of day: Disassemble upper and lower chambers. Wash with warm soapy water. Rinse thoroughly. Air dry upside down.
- Weekly: Soak in a solution of warm water and baking soda (1 tbsp per liter) for 30 minutes to remove coffee oil buildup.
- For brass filters: Polish with lemon and salt weekly to maintain shine and prevent tarnishing.
- Never use abrasive scrubbers on brass filters.

## Espresso Machine
- After each shot: Purge the group head with a blank shot of water.
- Every 2 hours: Wipe the steam wand with a damp cloth and purge steam.
- End of day: Backflush the group head with espresso machine cleaner (follow manufacturer instructions).
- Weekly: Remove and soak the portafilter basket in espresso cleaner solution for 30 minutes.
- Monthly: Descale the machine using the approved descaling solution. Run 2 liters of descaling solution followed by 4 liters of clean water rinse.
- Record all maintenance in the equipment log.

## Chai Kettle
- After each batch: Rinse with hot water to prevent spice buildup.
- End of day: Wash with hot soapy water. Scrub interior with a soft brush to remove tea stains and spice residue.
- Weekly: Boil water with lemon juice (50ml per liter) for 15 minutes to remove mineral deposits.
- Check the heating element monthly for scale buildup.

## Milk Warmer
- Every 2 hours: Check temperature is between 68-72 degrees C. Adjust thermostat if needed.
- End of day: Drain remaining milk. Wash interior with warm soapy water. Rinse and sanitize.
- Weekly: Deep clean by filling with hot water and food-safe descaler. Run for 15 minutes, drain, rinse twice.
- Never leave milk in the warmer overnight.
"""),
        ("3. Periodic Maintenance Schedule", """
## Commercial Blender
- After each use: Blend warm water with a drop of dish soap for 10 seconds, then rinse.
- End of day: Remove blade assembly, wash all parts, sanitize.
- Monthly: Inspect blade sharpness. Replace blades every 6 months or if visibly dull.
- Check gasket seal monthly; replace if cracked or worn.

## Refrigerator
- Daily: Check temperature reads below 4 degrees C. Log reading 3 times per day.
- Weekly: Clean interior shelves with food-safe sanitizer. Check door gaskets for proper seal.
- Monthly: Clean condenser coils (usually at the back or underneath). Dust buildup reduces cooling efficiency.
- Quarterly: Professional maintenance check including refrigerant levels.

## Ice Machine
- Daily: Check ice level and quality. Ice should be clear and odorless.
- Weekly: Clean the ice bin with warm water and food-safe sanitizer.
- Monthly: Run the machine's built-in cleaning cycle. Use manufacturer-approved ice machine cleaner.
- Quarterly: Professional descaling and inspection.
- If ice has off-flavor or cloudiness, run cleaning cycle immediately and check water filter.

## Coffee Grinder
- After each use: Brush out retained grounds from the burrs and chute.
- Daily: Run 10g of grinder cleaning pellets (rice-based) to absorb oils.
- Weekly: Remove the hopper, wash with warm soapy water, dry completely before reattaching.
- Every 3 months: Professional burr calibration and alignment check.
- Replace burrs every 12 months or after 500 kg of beans ground (whichever comes first).

## POS Terminal
- Daily: Wipe screen with microfiber cloth and electronics-safe cleaner.
- Weekly: Check receipt printer paper stock. Clean print head with manufacturer's cleaning card.
- Check network connectivity daily. If app orders are not appearing, restart the device and check WiFi.
"""),
        ("4. Troubleshooting Common Issues", """
## Filter Coffee Maker
- Weak decoction: Check grind size (should be medium-fine, not coarse). Ensure 20g per 150ml water ratio. Verify water temperature is 92-96 degrees C.
- Slow drip time (>20 minutes): Grind is too fine, or filter is clogged with oils. Clean filter with baking soda soak.
- Fast drip time (<8 minutes): Grind is too coarse. Adjust grinder to finer setting.
- Metallic taste: Brass filter needs polishing. Soak in lemon-salt solution.

## Espresso Machine
- No crema on shot: Check bean freshness (should be within 2 weeks of roasting). Adjust grind finer. Check extraction time (target: 25-30 seconds for double shot).
- Machine not heating: Check power connection. Verify thermostat setting. If persistent, call authorized service technician.
- Steam wand not producing steam: Likely blocked. Remove tip and soak in hot water. Clear with a pin.

## Chai Kettle
- Tea tastes burnt: Temperature too high. Chai should simmer, not boil vigorously.
- Spice residue in tea: Improve straining. Use a finer mesh strainer.

## General
- For any equipment failure during service hours, switch to backup equipment (all stores have backup filter coffee makers).
- Log all equipment issues in the maintenance tracker app.
- For warranty claims, contact the Kaapi Bricks Equipment Support team with the equipment serial number and photo of the issue.
"""),
    ],
)

supplier_agreements_summary = (
    "Supplier Agreements Summary",
    [
        ("1. Supplier Directory (SUP-001 to SUP-004)", """
## SUP-001: Coorg Coffee Estates
- Location: Coorg (Kodagu), Karnataka, India
- Category: Arabica Beans
- Products supplied: Coorg Arabica Beans (ING-001)
- Lead time: 7 days
- Reliability score: 4.8/5.0
- Payment terms: Net 30 days
- Minimum order: 50 kg
- Pricing: Rs.1,200/kg (contracted rate, reviewed annually)
- Delivery: Weekly shipment to Bangalore central warehouse, redistribution to stores
- Quality: Single-origin Arabica, shade-grown, hand-picked. Certificate of origin provided with each shipment.
- Contact: Procurement desk at coorg-estates@example.com

## SUP-002: Chikmagalur Plantations
- Location: Chikmagalur, Karnataka, India
- Category: Robusta & Chicory
- Products supplied: Chikmagalur Robusta Beans (ING-002), Chicory (ING-004)
- Lead time: 5 days
- Reliability score: 4.6/5.0
- Payment terms: Net 15 days
- Minimum order: 30 kg (Robusta), 20 kg (Chicory)
- Pricing: Robusta Rs.800/kg, Chicory Rs.400/kg
- Delivery: Bi-weekly to Bangalore warehouse
- Quality: Robusta beans are medium-roasted for optimal flavor in filter coffee blends. Chicory is sourced from dedicated chicory farms in the Chikmagalur region.

## SUP-003: Araku Valley Organics
- Location: Araku Valley, Andhra Pradesh, India
- Category: Specialty Blends
- Products supplied: Araku Valley Blend (ING-003), Cocoa Powder (ING-019)
- Lead time: 10 days
- Reliability score: 4.7/5.0
- Payment terms: Net 30 days
- Minimum order: 20 kg
- Pricing: Araku Blend Rs.1,500/kg, Cocoa Powder Rs.500/kg
- Delivery: Bi-weekly shipment
- Quality: Organic certified, tribal cooperative sourced. GI-tagged Araku coffee. Premium pricing reflects single-origin quality.

## SUP-004: Nandini Dairy
- Location: Karnataka Milk Federation, Bangalore, Karnataka
- Category: Dairy & Milks
- Products supplied: Full Cream Milk (ING-008), Toned Milk (ING-009), Coconut Milk (ING-012)
- Lead time: 1 day (daily delivery)
- Reliability score: 4.9/5.0
- Payment terms: Net 7 days
- Minimum order: 20 liters per delivery
- Pricing: Full Cream Rs.55/liter, Toned Rs.45/liter, Coconut Milk Rs.120/liter
- Delivery: Daily morning delivery (5:00 AM) to each store
- Quality: Government cooperative, pasteurized. Consistent quality and reliable daily supply.
"""),
        ("2. Supplier Directory (SUP-005 to SUP-008)", """
## SUP-005: Kerala Spice Traders
- Location: Idukki, Kerala, India
- Category: Spices & Flavors
- Products supplied: Cardamom (ING-006), Dry Ginger/Sukku (ING-007), Nannari Syrup (ING-015), Masala Chai Spice Mix (ING-016), Vanilla Extract (ING-020)
- Lead time: 5 days
- Reliability score: 4.5/5.0
- Payment terms: Net 15 days
- Minimum order: Varies by product (2 kg cardamom, 5 kg ginger, 5 liters syrup)
- Pricing: Cardamom Rs.3,000/kg, Dry Ginger Rs.600/kg, Nannari Syrup Rs.350/liter, Chai Mix Rs.1,500/kg, Vanilla Rs.2,000/liter
- Delivery: Weekly to Bangalore warehouse
- Quality: Direct from Kerala spice gardens. Cardamom is Alleppey Green variety. Spice mix is Kaapi Bricks proprietary blend.

## SUP-006: Mysore Sweet Works
- Location: Mysuru, Karnataka, India
- Category: Syrups & Sweeteners
- Products supplied: Jaggery (ING-005), Rose Syrup (ING-013), Badam Paste (ING-014), Sugar (ING-017), Palm Jaggery (ING-018)
- Lead time: 3 days
- Reliability score: 4.6/5.0
- Payment terms: Net 15 days
- Minimum order: 20 kg (jaggery), 10 liters (syrups)
- Pricing: Jaggery Rs.80/kg, Rose Syrup Rs.200/liter, Badam Paste Rs.800/kg, Sugar Rs.45/kg, Palm Jaggery Rs.150/kg
- Delivery: Weekly to Bangalore warehouse
- Quality: Traditional Mysore-style preparation. Jaggery is chemical-free and sourced from sugarcane farms in Mandya district.

## SUP-007: Chennai Packaging Co.
- Location: Chennai, Tamil Nadu, India
- Category: Cups & Packaging
- Products supplied: Paper Cups 200ml (ING-021), Stirrer Sticks (ING-022)
- Lead time: 7 days
- Reliability score: 4.4/5.0
- Payment terms: Net 30 days
- Minimum order: 10 cases
- Pricing: Paper Cups Rs.800/case (500 cups), Stirrer Sticks Rs.300/case (1000 sticks)
- Delivery: Bi-weekly to Bangalore warehouse
- Quality: Food-grade, BIS-certified. Cups are eco-friendly (recyclable paper with plant-based lining). Custom Kaapi Bricks branding.

## SUP-008: Organic Alternatives India
- Location: Bangalore, Karnataka, India
- Category: Alt Milks
- Products supplied: Oat Milk (ING-010), Almond Milk (ING-011)
- Lead time: 3 days
- Reliability score: 4.7/5.0
- Payment terms: Net 15 days
- Minimum order: 20 liters per variety
- Pricing: Oat Milk Rs.250/liter, Almond Milk Rs.280/liter
- Delivery: Weekly to Bangalore warehouse, bi-weekly to other cities
- Quality: Locally produced in Bangalore. No added sugar versions stocked. Barista-grade formulation for steaming and frothing.
"""),
        ("3. Reorder Policies & Inventory Thresholds", """
## Automated Reorder Triggers
When inventory drops below the reorder threshold, the inventory management system generates a purchase order automatically. Store managers must review and approve within 24 hours.

## Coffee & Chicory
- Coorg Arabica Beans (ING-001): Reorder at 10 kg. Typical weekly usage per store: 5-8 kg. Lead time: 7 days.
- Chikmagalur Robusta Beans (ING-002): Reorder at 15 kg. Typical weekly usage: 8-12 kg. Lead time: 5 days.
- Araku Valley Blend (ING-003): Reorder at 5 kg. Used only for premium drinks. Lead time: 10 days.
- Chicory (ING-004): Reorder at 8 kg. Typical weekly usage: 3-5 kg. Lead time: 5 days.

## Dairy
- Full Cream Milk (ING-008): Daily delivery. Emergency reorder if below 10 liters before evening rush.
- Toned Milk (ING-009): Daily delivery included with full cream order.
- Oat Milk (ING-010): Reorder at 20 liters. Lead time: 3 days.
- Almond Milk (ING-011): Reorder at 15 liters. Lead time: 3 days.
- Coconut Milk (ING-012): Reorder at 15 liters. Lead time: 1 day (included with Nandini delivery).

## Spices & Sweeteners
- Cardamom (ING-006): Reorder at 2 kg. Premium ingredient, Rs.3,000/kg. Lead time: 5 days.
- Jaggery (ING-005): Reorder at 20 kg. High usage in Bella Kaapi and traditional drinks.
- Sugar (ING-017): Reorder at 25 kg. Bulk usage across all sweetened drinks.
- Palm Jaggery (ING-018): Reorder at 10 kg.

## Packaging
- Paper Cups (ING-021): Reorder at 5 cases. Each case has 500 cups. Lead time: 7 days.
- Stirrer Sticks (ING-022): Reorder at 5 cases. Each case has 1000 sticks. Lead time: 7 days.

## Emergency Reorder Process
For urgent needs (same-day), contact the supplier directly by phone. Nandini Dairy (SUP-004) offers same-day emergency delivery. Other suppliers require minimum 24-hour notice.
"""),
        ("4. Contract Terms & Performance Monitoring", """
## Standard Contract Terms
- All supplier contracts are annual, reviewed in Q1 each year.
- Pricing is locked for the contract year. Mid-year price adjustments require 60-day written notice and mutual agreement.
- Quality standards are defined in the supplier quality agreement (SQA) appendix.
- Kaapi Bricks reserves the right to conduct unannounced quality inspections at supplier facilities.
- Suppliers must maintain relevant certifications: FSSAI license, organic certification (where applicable), ISO 22000 (preferred).

## Performance Metrics
Each supplier is evaluated quarterly on:
- On-time delivery rate: Target 95%+
- Quality acceptance rate: Target 98%+ (incoming quality checks)
- Responsiveness: Time to respond to urgent orders or quality issues
- Documentation: Accurate invoices, certificates of analysis, and delivery notes

## Current Supplier Scores (Last Quarter)
- SUP-001 (Coorg Coffee Estates): 4.8/5.0 - Excellent. Consistent quality, rarely late.
- SUP-002 (Chikmagalur Plantations): 4.6/5.0 - Very good. Occasional 1-day delays during monsoon season.
- SUP-003 (Araku Valley Organics): 4.7/5.0 - Very good. Premium quality but longer lead times due to remote location.
- SUP-004 (Nandini Dairy): 4.9/5.0 - Excellent. Daily delivery, rarely misses.
- SUP-005 (Kerala Spice Traders): 4.5/5.0 - Good. Cardamom pricing fluctuates with market.
- SUP-006 (Mysore Sweet Works): 4.6/5.0 - Very good. Reliable for all sweetener products.
- SUP-007 (Chennai Packaging Co.): 4.4/5.0 - Good. Occasional print quality variations on branded cups.
- SUP-008 (Organic Alternatives India): 4.7/5.0 - Very good. Local Bangalore supplier enables fast delivery.

## Dispute Resolution
- Quality issues: Document with photos and report to supplier within 48 hours. Credit or replacement shipment expected within the supplier's standard lead time.
- Pricing disputes: Escalate to Kaapi Bricks Procurement Manager. All pricing is per contracted rates.
- Repeated performance failures: After 2 consecutive quarters below target metrics, Kaapi Bricks initiates supplier review and may source alternatives.
"""),
    ],
)

# =============================================================================
# GENERATE AND UPLOAD
# =============================================================================

documents = [
    barista_training_manual,
    drink_recipes_sop,
    food_safety_policy,
    franchise_operations_guide,
    equipment_maintenance_guide,
    supplier_agreements_summary,
]

file_names = [
    "barista_training_manual.pdf",
    "drink_recipes_sop.pdf",
    "food_safety_policy.pdf",
    "franchise_operations_guide.pdf",
    "equipment_maintenance_guide.pdf",
    "supplier_agreements_summary.pdf",
]

print(f"\nGenerating {len(documents)} PDF documents...")

for fname, (title, sections) in zip(file_names, documents):
    pdf_bytes = create_pdf(title, sections)
    upload_path = f"{VOLUME_PATH}/{fname}"
    w.files.upload(upload_path, io.BytesIO(pdf_bytes), overwrite=True)
    size_kb = len(pdf_bytes) / 1024
    print(f"  Uploaded {fname} ({size_kb:.1f} KB)")

# =============================================================================
# VERIFICATION
# =============================================================================
print(f"\nVerifying uploaded files in {VOLUME_PATH}/...")
from databricks.sdk.service.files import ListDirectoryResponse

listed = list(w.files.list_directory_contents(VOLUME_PATH))
for f in listed:
    print(f"  {f.path} ({f.file_size:,} bytes)" if f.file_size else f"  {f.path}")

print(f"\nDone! {len(documents)} KA documents uploaded to {VOLUME_PATH}/")
