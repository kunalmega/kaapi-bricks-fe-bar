# Passing an AI Demo Roleplay: a Reusable Playbook

**For:** anyone preparing for an AI-scored product-demo roleplay, such as the Yoodli "Demo Bot":
30 minutes, an AI business persona and an AI technical persona, scored against a rubric.

**How this was written:** from two real attempts at the same scenario, with the AI judge's full
feedback each time. The first attempt didn't pass; the second did.

| Rubric item | Attempt 1 | Attempt 2 | What moved the score |
|---|---:|---:|---|
| Solution framing | 4 | 4 | Tell-show-tell kept it at 4. To reach 5, the close must lead with the persona's own number |
| Production readiness and deployability | **2** | **3** | Adding a "path to production" segment. To reach 5, the security and integration detail must match the CI/CD detail |
| Blocker handling and judgment | 3 | 4 | Naming dependencies and the account team before any date. To reach 5, offer options with trade-offs, never "it's configurable" |
| Professionalism and delivery | 4 | 4 | Organised and honest. To reach 5, answer pressure questions with numbers, not reassurance |

Each section below says what the judge rewards, what it penalises, and the exact wording that
works. Fill in your own product, numbers and personas.

---

## 1. Understand what's being scored

The judge listens for **behaviours**, not product knowledge. Four rubric items, and what a 5 looks like:

| Rubric item | What a 5 sounds like |
|---|---|
| **Solution framing** | Every segment is tell → show → tell. Each one ends with a business outcome in the persona's terms ("Alex, this is your waste number"). The close is anchored on the **one number the persona chose** |
| **Production readiness** | You explain how it ships and runs safely: deploy from code, environments, tests, rollback, bad data and schema drift, security controls, identity, network, integration, monitoring. All of it concrete and honest about "today vs pilot" |
| **Blocker handling and judgment** | You acknowledge, ask a clarifying question, then answer with **options and trade-offs**. You state dependencies before dates, and bring in the account team |
| **Professionalism and delivery** | A clear agenda, controlled timing, confident answers under pressure, few fillers, a strong close with one next step per person |

**The judge is a transcript reader.** It hears words, not your screen. Say what's on screen,
say the business point out loud, and say every number clearly.

---

## 2. Prepare (the day before and 15 minutes before)

**Content you must have ready**
- [ ] **One value number** and its currency. Use the same figure every time (in attempt 1, saying "240k" when the deck said $264k cost a point).
- [ ] A **downside scenario** for that number: what happens if your weakest assumption only half works?
- [ ] For each persona: **the metric they're measured on**, today's value, and the target.
- [ ] Every number labelled as **measured** or **assumed**.
- [ ] A one-line answer for each likely follow-up (see section 9).
- [ ] An honest list of **what's built today** vs **what the pilot adds**.

**Screen set-up**
- [ ] Every demo tab open, logged in, and warmed up (cached questions, sample data loaded).
- [ ] The file you'll upload **open in the file picker already**. Searching for a file cost 35 seconds in attempt 1.
- [ ] A backup for each live step (a screenshot or saved output) in case something fails.
- [ ] A visible timer.

**Sanity check:** run the live flow once in the morning. A real demo broke between our two attempts because of an upstream configuration change.

---

## 3. Answer the bot's set-up questions crisply (about 20 seconds each)

The bot always starts by asking three questions. Prepare them word for word.

| Bot asks | Template | Example |
|---|---|---|
| "What are you demoing, and what's the use case?" | *[Product] on [platform]. [Customer] has [pain]. The use case is [one-line capability]. We project [one number], and I'll show how we'd prove it.* | "Kaapi Bricks Store Operations on Databricks. Store managers piece the day together from six tools. One app lets them ask, see, act and plan. About $264,000 a year, and I'll show how we'd prove it in a pilot." |
| "What industry?" | *[Industry]: specifically [segment].* | "Retail and consumer goods, specifically quick-service restaurants." |
| "Which personas should we play?" | Give each persona a **title, what they own, and the metric they're measured on.** | "Alex, VP of Store Operations: you own all 37 stores and you're measured on stockouts, waste and consistency. Shreya, Head of Data Platform: you'd run this in production." |

**Don't:**
- call it "a chatbot" if it's more than that;
- give a number you can't defend;
- leave the personas vague ("a business person").

---

## 4. Open with a hook, then frame (first 2–3 minutes)

The judge penalised going "from set-up straight into a savings figure and a long list of
capabilities". Use this order:

1. **Time and agenda (15 s):**
   > "We have 30 minutes. I'll take about 20 for the demo and keep the rest for your questions and next steps. Does that work?"
2. **Discovery (40 s):** ask the business persona for **their one number**, and repeat it back.
   > "Before I show anything: which one number do you most need to move this year?"
   > "Got it: waste. I'll show the waste impact in the Plan section, and the cost in the close."

   Say *where* you'll deliver it, then deliver it there.
3. **Technical persona's questions (20 s):**
   > "Shreya, I expect your questions are: does it run on our platform, how is it governed, how do we know the AI is right, and how does it get to production safely. I'll cover all four."
4. **A hook: a short story, not a feature list (30 s):**
   > "Here's Priya's Monday. By 9am she's opened six tools, counted a shelf by hand, and still doesn't know a delivery is late. That's 37 managers, every morning."
5. **Roadmap (20 s):** name the steps you'll show, and say them again in the close.
   > "Four steps: ask, see, act, plan."
6. **What to watch for (15 s), one line per persona:**
   > "Alex, watch for three numbers. Shreya, watch for one idea: every number comes from governed data."
7. **Honesty disclaimer (10 s):**
   > "The company is fictional and the data is synthetic, but the platform is real. I'll say whether each number is measured or assumed."

---

## 5. Run every segment as tell → show → tell

Both attempts lost points where a segment "started mid-action" or "drifted into technical
inputs". Use this template for **every** segment:

| Part | Length | What to say |
|---|---|---|
| **Tell: the pain** | 15–20 s | The situation today, in the persona's terms. "Today Priya guesses prep from memory, so milk gets thrown away." |
| **Tell: what you'll show** | 5–10 s | "What I'll show you is the same decision made from a forecast." |
| **Show** | 60–120 s | Point at **one thing at a time**. Say what's on screen. **Don't narrate clicks** ("now I click here, then I go there"). |
| **Tell: the business benefit** | 15–20 s | "Alex, this is your **waste** number: every manager plans like your best manager." |
| **One technical line** | 10 s | "Shreya: the model is registered in Unity Catalog and only promoted if it beats the baseline." |
| **Transition** | 5 s | "That's how Priya plans. Next, how she handles a delivery." |

**Altitude rule:** say benefit and value language to the business persona first. Keep jargon
(TTL, caching, MCP, gateway, Postgres) for the technical persona's one line, and keep it to one
line. Attempt 2 was marked down for "technobabble in the value story".

**Show the proof live:** if the technical persona asks "is it real time?", show the screen
updating. In attempt 1, the presenter promised to show it and never did.

---

## 6. Path to production: the segment that decides the technical score

Without it: **2/5.** With CI/CD but thin security: **3/5.** To reach 5, cover all eight
areas at the **same depth**. Say what exists **today** and what the **pilot adds**; the judge
rewards honesty about gaps.

| Area | What to cover | Example wording |
|---|---|---|
| **1. Deploy from code** | Bundles or Terraform in Git; nothing hand-built in the UI | "The pipeline, jobs and apps are defined in a Databricks Asset Bundle in Git and deployed with one command." |
| **2. Environments and promotion** | dev → staging → prod; separate catalogs; deployed by a CI service principal | "Each environment has its own catalog and service principal. Prod is deployed by CI, never by a person." |
| **3. Testing** | Unit tests, bundle validation, deploy to staging, run the evaluation there, a gate before prod | "Every pull request runs unit tests and the AI evaluation in staging. Prod deploys only when it's green." |
| **4. Rollback** | Code, app, model and data, one line each | "Redeploy the previous Git tag; point the model's champion alias back at the previous version; Delta time travel for a table." |
| **5. Bad data and schema drift** | Expectations, quarantine, schema evolution, what happens when a source changes | "Expectations drop or quarantine bad rows before gold. New source columns land in bronze without breaking anything. Silver only takes named columns, so gold changes only when we decide." |
| **6. Security controls** | Name the actual mechanism, not "it's governed" | "A row filter on store_id, mapped to groups synced from your identity provider through SCIM. Column masks on supplier and staff PII. API keys in secret scopes, not in code." |
| **7. Identity and network** | SSO, SCIM, Private Link or IP access lists | "Single sign-on through your identity provider; the workspace on Private Link inside your network." |
| **8. Monitoring and alerts** | Job failure alerts, quality-score history, thresholds, who gets paged | "The daily job alerts on failure. The AI quality score is stored every morning, and below 0.80 opens a ticket." |

**Never say:**
- "It's governed at the catalog level, and I'll talk more about governance later", unless you then come back to it. Attempt 2 never did, and was marked down.
- "That's very easy to build." Say instead: "That's a pilot deliverable; I'll confirm scope with our account team."

**Turn a gap into a commitment:**
> "The monitoring dashboard isn't built yet. I'll have a first version ready for the pilot kickoff."

**A real incident helps.** If something broke during your build and you fixed it, tell the story
in 30 seconds: what broke, how the logs showed why, how you rolled back, and what alert you added.

---

## 7. Handle objections with A-C-A-N

**A**cknowledge → **C**larify → **A**nswer with options and trade-offs → **N**ext step.

| Step | Example (the "can it tell a negotiated price from an overcharge?" question) |
|---|---|
| **Acknowledge** | "That's exactly the right question: a false flag wastes the manager's time." |
| **Clarify** (one question) | "Where do negotiated prices live today: on the PO, or in a separate contract?" |
| **Answer with options and trade-offs** | "The check is rule-based against the PO price. If renegotiated prices reach the PO or a contract table we ingest, the line matches. If they only live in email, it's flagged. That's the safe failure, because a person approves. The trade-off is more flags until the contract feed is connected." |
| **Next step** | "In the pilot we measure the false-flag rate on your real invoices, against a target your finance team signs off." |

**Offer choices instead of "it's configurable."** Attempt 2 lost a point for *"we'll make sure
it happens the way you want; everything can be configured."* Say instead:
> "Three options. One: clear the cache whenever inventory updates. That's always fresh, but costs a little more compute. Two: match the cache life to the four-hour refresh. That's cheapest, but can be up to four hours stale. Three: skip the cache for inventory questions and keep it for SOP answers. Which matters more to you, freshness or cost?"

**Words that cost points:**

| Don't say | Say |
|---|---|
| "I hope it works", "I believe it should" | "Here's how we'll measure it in the pilot: [metric, target, who signs off]." |
| "It's very easy" | "It's a pilot deliverable; I'll confirm scope with the account team." |
| "Everything is configurable" | Two or three options, each with its trade-off, then ask which fits. |
| "I'll come back to that" (and never do) | "I'll show that in the next section", then show it there. |

**Before you give any date**, name the dependencies and involve the account team:
> "We can start about two weeks after three things are in place: data access, the pilot stores named, and an identity and network contact. I'll confirm scope and resourcing with our account team this week."

---

## 8. Close on the persona's own number, with a downside case

The judge wants the close **anchored on the number the persona chose**. Attempt 2 led with the
biggest line (invoices) when the persona had said "waste", and lost the 5.

**Close in this order (2 minutes):**
1. **Their number first:**
   > "Alex, you said waste is the number you need to move. Today it's ₹4,572 per store a month, measured, and it varies 3× between stores. The forecast targets a 25% cut, and the pilot measures it store by store against each store's own baseline."
2. **The rest as upside:**
   > "On top of that, invoices and manager time add most of the value: about $264,000 a year in total."
3. **Downside scenario.** Answer "what if it only half works?" before they ask:
   > "Even if waste only falls 10%, the total barely moves, because 81% of the value is invoices and manager time. Payback stays at about four months."
4. **Measured vs assumed:**
   > "These are assumptions, written down. So I'm not asking you to believe the number; I'm asking for six weeks to measure it."
5. **The pilot, with go/no-go including their metric:**
   > "Go/no-go: at least 50% less manager time, AI correctness of 0.80 or more, no increase in stockouts, and **waste down in the pilot stores**."
6. **Dependencies and the account team** (section 7).
7. **One next step per person, each with a date:**
   > "Alex: name five stores by Thursday. Shreya: masked data and an identity contact. Me: the plan and a confirmed timeline by Friday."
8. **Recap the roadmap in one breath, then thank them:**
   > "Ask, see, act, plan, on one governed platform. Thank you both."

**When the persona pushes on an assumption, answer with numbers straight away.** Don't defer.
Weak, from attempt 2: *"I'm confident from the general number… it's just market data I took."*
Strong:
> "Fair push. The 25% is an assumption, and here's the downside. At 10%, the waste line drops from about $3,100 to $1,200 a year. The total goes from $264,500 to about $262,700, and payback stays under four months. Our measured waste is actually double what the model assumes, so the line is conservative. The pilot gives you the real number per store."

**Don't invent support for an assumption.** A judge's sample answer once suggested saying the
assumption "comes from your data" when it didn't. Say what's measured and what's assumed, then
give the downside math.

---

## 9. Prepare for the follow-up questions

The judge asks one or two follow-ups after the call. Questions we were given across both attempts:

| Follow-up | Answer pattern |
|---|---|
| "How will you validate accuracy across different suppliers and invoice formats?" | A hand-checked test set (about 50 real documents across every supplier and format); measure field accuracy and flag accuracy (caught and false); finance signs off the target; low-confidence results go to manual review |
| "What if the pilot hits its time and accuracy goals, but waste only falls 10%?" | Show the downside math (section 8). Say the decision still holds, because the value is mostly elsewhere. Then: "We'd investigate why per store: forecast accuracy, or adoption of the prep plan. Then decide whether to expand the waste use case." |

**General pattern:** restate the scenario → the number → whether the decision changes → what you'd do next.

---

## 10. Delivery

**Fillers.** "You know", "like", "okay?", "correct?" and "does it make sense?" appeared in almost
every turn of attempt 1. Replace them with a pause, or a **specific** check-in:
> "Alex, is that how invoice disputes work in your stores today?"

**Pace**
- Slow down on screens.
- Pause two seconds after each key number.
- Never read a screen word for word: point at one thing and explain why it matters.

**Pronunciation.** The judge flagged each of these:

| Word | Say it as |
|---|---|
| parse / parsing | /pɑːrs/, with the R. Not "pass" |
| waste | /weɪst/, with rounded lips. Not "base" |
| invoice, delivery, volume, versioned | a real /v/: top teeth on your lower lip |
| spreadsheet | a long "sheet" /iː/, not "sit" |
| discrepancy | stress the second syllable: dis-**CREP**-an-cy |
| product names | slowly, the first time (the transcript heard "Copy Breaks" for *Kaapi Bricks*, and "late flow" for *Lakeflow*) |

**Accuracy is part of professionalism.** Before the call, list the statements you must get exactly
right. In attempt 1, these slips each undermined trust:
- "240k" instead of $264k;
- "overdue payments" instead of "overdue deliveries";
- "only managers can approve", which wasn't true yet;
- "I'm asking you to believe the number" (dropping the "not");
- "increase the stockouts" (instead of "no increase").

**Timing**
- Plan about 20 minutes of demo, 6–8 minutes of questions, and 2 minutes to close.
- If you're late, cut the second example in a segment, never the close.

---

## 11. Self-check (run it right after the call)

- [ ] I asked for the business persona's one number, said where I'd address it, and **delivered it there**.
- [ ] Every segment had: pain → what I'll show → show → "this is your ___ number" → one technical line → transition.
- [ ] I covered all eight path-to-production areas, at the same depth.
- [ ] Every objection got acknowledge → clarify → options with trade-offs → next step.
- [ ] I didn't say "hope", "believe", "very easy" or "configurable" without options.
- [ ] I gave dependencies and mentioned the account team before any date.
- [ ] The close led with their number, included a downside case, and the go/no-go included their metric.
- [ ] One next step per person, each with a date, and a closing recap of the roadmap.
- [ ] I used one value figure everywhere, and labelled every number measured or assumed.
- [ ] I finished inside 30 minutes.

---

## Appendix: the worked example

The Kaapi Bricks scenario these lessons come from: a fictional 37-store coffee chain, synthetic
data, deployed on Databricks.

- Minute-by-minute script with prepared answers: `ROLEPLAY_SCRIPT.md`
- Value model, with every assumption and the SQL behind each measured number: `evidence/10_business_kpi_calculations.md`
- Persona metrics: `README.md`, "Who this is for"
