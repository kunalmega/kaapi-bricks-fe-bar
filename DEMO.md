# Kaapi Bricks — AI Days Finale Demo

**Duration:** 15-18 minutes
**Audience:** CIOs, VPs, Architects, Developers
**Story:** A day in the life of a Kaapi Bricks store manager — from morning questions to supplier deliveries — powered entirely by Databricks AI.

---

## Before Going On Stage (3 min)

Open these tabs in order:
1. **Kaapi Bricks App** — Main Chat (Koramangala selected)
2. **MLflow Experiment** — traces page (empty, ready for new traces)
3. **Databricks UI** — MAS Supervisor Agent (show 3 agents)
4. **MCP Server App** — Settings tab (show model config)
5. **MCP Server App** — Compare tab (ready for A/B test)
6. **Kaapi Bricks App** — Delivery & Invoice tab (ready for upload)
7. **Sample invoice PDF** — `invoice_complex_coorg.pdf` ready on desktop

Clear chat history. Confirm MAS is warm (ask one quick question from the UI first).

---

## THE STORY

You're telling the story of **Priya**, a store manager at Kaapi Bricks Koramangala, Bangalore. It's 7am. She's opening the store. She has questions, she has deliveries coming in, and she needs to plan for tomorrow. She doesn't want dashboards. She wants answers.

---

## SCENE 1 — Morning Questions (3 min)

*Tab: Main Chat app*

> "Meet Priya. She manages our Koramangala store — one of 37 across India, Dubai, Singapore, London. It's 7am. She's opening the store and she has three questions before the first customer walks in."

**[Click:]** "What's our best-selling drink this month?"

*Answer appears — Classic Filter Coffee 1,483 units, Strong Decoction 1,071...*

> "Real data. 200,000 orders across 37 stores. She didn't open a dashboard. She asked a question."

**[Click:]** "How do I make a Classic Filter Coffee?"

*Recipe appears — tumbler-davara technique, 92-96°C, 12-15 min drip.*

> "Same chat. Different answer. This one came from our barista training manual — a PDF. She didn't search a document library. She just asked."

**[Click:]** "How should I prepare for tomorrow?"

*Answer appears — weather forecast, holiday calendar, product recommendations.*

> "Now this one is interesting. Priya asked about tomorrow. The system checked the live weather forecast for Bangalore, looked at the Indian holiday calendar, and generated a preparation plan."

**[Pause 3 seconds. Let the audience read.]**

> "Three questions. Three different AI agents answered. One pulled from a database. One searched internal documents. One checked the weather and the festival calendar. Priya didn't know which agent answered. She just asked."

---

## SCENE 2 — Under the Hood (2 min)

*Tab: MLflow Experiment — click the latest trace*

> "Let me show you what actually happened."

**[Point at the trace spans — don't click into every one, just point:]**

> "The MAS Supervisor received the question. It read the descriptions of three agents and decided this was an operational planning question. It called our MCP server — that's a separate Databricks App — which checked the weather API, checked the holiday calendar, and called a foundation model to generate the plan."

> "Every step is traced. Every API call, every tool invocation, every token. If this agent starts giving bad answers at 3am, I open the trace and I know exactly where it went wrong."

**[Switch to Databricks UI — MAS Supervisor]**

> "Here's the architecture. Three agents under one supervisor."

**Point quickly at each:**
> "Knowledge Assistant — our training documents. Genie Space — our transaction data. Operations Advisor — an MCP server connecting to the outside world. The supervisor routes. I don't write routing code."

---

## SCENE 3 — Model Flexibility (2 min)

*Tab: MCP Server App — Settings*

> "Now the question every CIO asks: are we locked into one model?"

**[Show the Settings page]**

> "This is our MCP server's admin. The Operations Advisor currently uses Llama 70B. I can change it to Claude, GPT, Gemini — one dropdown."

**[Switch to Compare tab. Select Llama vs Claude. Ask: "How should I prepare for tomorrow?"]**

> "But I wouldn't change blindly. Same question, same weather, same calendar — two different models."

*Both results appear side by side.*

> "Claude structured it as a checklist. Llama gave more narrative detail. I pick the winner, go back to Settings, save. Done."

> "Test in the sandbox. Promote to production. CI/CD for AI."

---

## SCENE 4 — The Delivery (4 min) ⭐ Star of the demo

*Tab: Kaapi Bricks App — Delivery & Invoice*

> "It's now 9am. A truck pulls up from Coorg Coffee Estates. They hand Priya a paper invoice."

**[Hold up the PDF or show it on screen for 3 seconds]**

> "Eight line items. Arabica beans, chicory, house blend, cardamom, paper cups. HSN codes, batch numbers, GST breakup, quality certifications. A real Indian GST invoice."

**[Upload the PDF. Click "Parse Invoice".]**

> "Watch."

*Loading... "Parsing invoice with ai_parse_document..."*

*Results appear — extracted supplier, items, totals.*

> "Databricks just read that PDF. ai_parse_document — a native SQL AI function — extracted every line item, every rate, every GST number. No OCR library. No third-party service. One SQL function."

**[Point at the PO Match card]**

> "It found the matching purchase order — PO-01288. And look at the line items."

**[Point at the comparison table]**

> "Green means match. Yellow means warning. Red means discrepancy."

**[Point at specific discrepancies:]**

> "Arabica beans — we ordered 25 kilos at twelve hundred rupees. The invoice says 30 kilos at thirteen hundred. That's a quantity overdelivery AND a price increase. The system caught both."

> "Chicory — price went up by 20 rupees per kilo. House blend — up by 30. And there are three extra items not in our purchase order at all — Araku Valley Reserve, Cardamom, and a second grade of Arabica."

**[Pause — let them absorb]**

> "A store manager looking at this paper invoice would take 30 minutes to cross-check against the PO. The system did it in seconds."

**[Click "View Current Inventory"]**

> "Here's our current stock. Some items are green, some are low, some are critical."

**[Click "Approve & Update Inventory"]**

*Success message. Inventory refreshes.*

> "One click. The delivery is now in our inventory system. The purchase order is marked as delivered. And if Priya goes back to the main chat and asks 'What's our current stock of Arabica?' — she'll see the new quantity."

---

## SCENE 5 — Evaluation & Quality (3 min)

*Tab: MLflow Experiment — Evaluation tab*

> "Everything I showed you looks great. But how do I KNOW it's correct? How do I know the agent isn't hallucinating? In production, you can't just trust the output — you have to measure it."

**[Show the evaluation dashboard / labelling session]**

> "We built custom LLM judges that run on every agent output. Four judges, each checking a different dimension."

**[Point at each scorer:]**

> "**Correctness** — does the answer match expected guidelines? If someone asks about our food safety policy, does the agent return the actual FSSAI policy, or did it make something up?"

> "**Retrieval Groundedness** — is the answer grounded in the documents it retrieved? We check: did the agent cite real content from our training manual, or did it hallucinate a recipe that doesn't exist?"

> "**Safety** — does the response contain anything inappropriate, harmful, or off-brand for Kaapi Bricks?"

> "**Custom Guidelines** — domain-specific checks. Does it mention prices in INR? Does it reference the right store? Does it follow our brand voice?"

**[Show a failed evaluation — a row marked red]**

> "Here's one that failed. The agent gave a recipe with the wrong decoction ratio — 1 tablespoon per 200ml instead of 2 tablespoons per 150ml. The Correctness judge caught it."

> "When something fails, it goes into a **labelling session**. Our subject matter experts — the baristas, the operations team — review the flagged outputs and label them: correct or incorrect, with notes. That labelled data goes back into improving the evaluation dataset."

**[Show evaluation comparison — if available]**

> "And we can compare evaluations. We ran evaluation set A with Llama, and evaluation set B with Claude. Side by side — which model scored higher on correctness? Which one had better retrieval grounding? The data tells us which model to promote. Not opinions — evidence."

**[Pause]**

> "This is what separates a demo from production. Evaluation, labelling, continuous improvement. The agents get better because we measure them."

---

## SCENE 6 — The Big Picture (2 min)

> "Let me step back and show you what we just built."

**Count on fingers:**

> "One — a multi-agent supervisor. Three specialists, one router. Documents, data, and the outside world. The store manager doesn't know or care which agent answered."

> "Two — an MCP server. A separate app that connects our AI system to live weather, holiday calendars, and anything else we want. It plugs into the supervisor via a standard protocol. Tomorrow I could add a CRM connector, an ERP system, a logistics tracker — same pattern."

> "Three — document intelligence. A supplier invoice — a complex, real-world PDF with GST breakups and batch numbers — parsed by a native SQL function, matched against purchase orders, discrepancies flagged, inventory updated. End to end."

> "Four — model flexibility. Ten foundation models, side-by-side comparison, one-click switch. We're not locked into any vendor."

> "Five — continuous evaluation. Custom LLM judges — correctness, retrieval grounding, safety — running on every output. When something fails, SMEs label it, the evaluation dataset improves, the agents get better."

> "Six — full traceability. Every question, every agent decision, every tool call — traced in MLflow. Production-ready observability."

---

## CLOSING (30 seconds)

> "We started at 7am with Priya opening her store. She asked about her best sellers, learned a recipe, planned for tomorrow's weather. Then a delivery truck arrived, she scanned an invoice, caught three discrepancies, and updated her inventory — all without leaving one app."

> "That's not a chatbot. That's an enterprise AI platform. And it runs on Databricks."

**[END]**

---

## Timing Summary

| Scene | Duration | What Happens |
|-------|----------|-------------|
| 1. Morning Questions | 3 min | 3 chat questions → 3 agents |
| 2. Under the Hood | 2 min | MLflow trace + MAS architecture |
| 3. Model Flexibility | 2 min | MCP Settings + Compare side-by-side |
| 4. The Delivery | 4 min | Invoice upload → parse → PO match → discrepancies → approve → inventory |
| 5. Evaluation & Quality | 3 min | Custom LLM judges, failed eval, labelling, eval comparison |
| 6. Big Picture | 2 min | Six pillars recap |
| Close | 0.5 min | Back to Priya's story |
| **Total** | **~17 min** | Buffer: 1-2 min for audience reactions |

---

## If Things Go Wrong

| Problem | Recovery |
|---------|----------|
| MAS slow on first question | Click a cached example first to warm it up. Say "Real agents, real data" while waiting. |
| MCP tool approval hangs | The auto-approval code handles this. If it still fails, ask a KA or Genie question instead. |
| Invoice parsing slow | Say "ai_parse_document is reading 8 line items, HSN codes, GST breakups..." — narrate while waiting. |
| Network error on chat | Switch to the cached question. Second try always works. |
| Compare page slow | Say "Two models running the same question — real computation, not a mock." |

---

## Golden Rules

1. **Lead with Priya, not the technology.** The audience remembers the store manager, not the API call.
2. **Pause after each answer.** The magic only works if they have time to read it.
3. **Don't explain MCP protocol** unless asked. Say "an open standard for connecting AI to external systems" and move on.
4. **Don't show code.** Everything is UI-driven. That IS the point.
5. **The invoice is your closer.** It's the most visual, most tangible, most "I need this" moment. Spend time here.
6. **Name the products.** "Classic Filter Coffee, Coorg Arabica, tumbler-davara" — specifics make it real.
7. **End with the platform, not the features.** "That's not a chatbot. That's an enterprise AI platform."
