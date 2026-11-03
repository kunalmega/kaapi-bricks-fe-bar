# AI Demo Roleplay Playbook

**Use this for:** AI-scored product-demo roleplays, such as the Yoodli "Demo Bot". The format is
30 minutes with an AI business persona and an AI technical persona, scored against a rubric.

**How to use it:** read sections 1–3 the day before. Rehearse sections 4–8 out loud. Keep the
delivery card (section 10) and the self-check (section 11) next to your screen.

The examples use a fictional retail scenario: a 37-store coffee chain, a store-operations app,
a business persona "Alex" and a technical persona "Shreya". Swap in your own product, numbers
and personas.

---

## 1. What the judge scores

The judge scores **behaviours**, not product knowledge. There are four rubric items:

| Rubric item | What a top score sounds like |
|---|---|
| **Solution framing** | Every segment is tell → show → tell. Each ends with a business outcome in the persona's terms ("Alex, this is your waste number"). The close is anchored on **the one number the persona chose** |
| **Production readiness and deployability** | How it ships and runs safely: deploy from code, environments, tests, rollback, bad data and schema drift, security controls, identity, network, integration, monitoring. All of it concrete, and honest about what exists today versus what a pilot adds |
| **Blocker handling and judgment** | Acknowledge the concern, ask a clarifying question, answer with **options and trade-offs**, and propose a next step. State dependencies before any date, and involve the account team |
| **Professionalism and delivery** | A clear agenda, controlled timing, confident answers under pressure, few fillers, and a close with one next step per person |

**The judge reads a transcript.** It hears your words, not your screen. Describe what's on
screen, say the business point out loud, and say every number clearly.

---

## 2. Prepare

**Content to have ready**
- [ ] **One value number**, in one currency, used the same way every time.
- [ ] A **downside scenario**: what the number becomes if your weakest assumption only half works.
- [ ] For each persona: the metric they're measured on, today's value and the target.
- [ ] Every number labelled **measured** or **assumed**.
- [ ] A one-line answer for each likely follow-up question (section 9).
- [ ] An honest list of **what's built today** versus **what the pilot adds**.
- [ ] A short list of statements you must get exactly right: figures, terms, and anything that's easy to overclaim.

**Screen set-up**
- [ ] Every demo tab open, logged in and warmed up (cached answers, sample data loaded).
- [ ] Any file you'll upload already open in the file picker. Searching for a file on screen wastes time and looks unprepared.
- [ ] A backup for each live step (screenshot or saved output) in case it fails.
- [ ] A visible timer.

**Sanity check:** run the full live flow on the morning of the session. Configuration changes
upstream can break a demo that worked the day before.

---

## 3. Answer the set-up questions crisply

The bot opens with three questions. Prepare each answer word for word, about 20 seconds each.

| Bot asks | Template | Example |
|---|---|---|
| "What are you demoing, and what's the use case?" | *[Product] on [platform]. [Customer] has [pain]. The use case is [one-line capability]. We project [one number], and I'll show how we'd prove it.* | "Store Operations on Databricks. Store managers piece the day together from six tools. One app lets them ask, see, act and plan. About $264,000 a year, and I'll show how we'd prove it in a pilot." |
| "What industry?" | *[Industry]: specifically [segment].* | "Retail and consumer goods, specifically quick-service restaurants." |
| "Which personas should we play?" | For each: **a title, what they own, and the metric they're measured on.** | "Alex, VP of Store Operations: you own all 37 stores and you're measured on stockouts, waste and consistency. Shreya, Head of Data Platform: you'd run this in production." |

**Avoid:**
- shrinking the product ("a chatbot") when it does more;
- a number you can't defend;
- vague personas ("a business person").

---

## 4. Open with a hook, then frame the demo (first 2–3 minutes)

Don't go straight from set-up to a savings figure and a list of capabilities. Use this order:

1. **Time and agenda (15 s):**
   > "We have 30 minutes. I'll take about 20 for the demo and keep the rest for your questions and next steps. Does that work?"
2. **Discovery (40 s):** ask the business persona for **their one number**, repeat it back, and say **where** you'll address it.
   > "Which one number do you most need to move this year?"
   > "Got it: waste. I'll show the waste impact in the Plan section, and the cost in the close."
3. **The technical persona's questions (20 s):**
   > "Shreya, I expect your questions are: does it run on our platform, how is it governed, how do we know the AI is right, and how does it get to production safely. I'll cover all four."
4. **A hook: a short story, not a feature list (30 s):**
   > "Here's a store manager's Monday. By 9am she's opened six tools, counted a shelf by hand, and still doesn't know a delivery is late. That's 37 managers, every morning."
5. **Roadmap (20 s):** name the steps you'll show, and repeat them in the close.
   > "Four steps: ask, see, act, plan."
6. **What to watch for (15 s), one line per persona:**
   > "Alex, watch for three numbers. Shreya, watch for one idea: every number comes from governed data."
7. **Honesty disclaimer (10 s), if the data is synthetic:**
   > "The company is fictional and the data is synthetic, but the platform is real. I'll say whether each number is measured or assumed."

---

## 5. Run every segment as tell → show → tell

| Part | Length | What to say |
|---|---|---|
| **Tell: the pain** | 15–20 s | The situation today, in the persona's terms. "Today the manager guesses prep from memory, so milk gets thrown away." |
| **Tell: what you'll show** | 5–10 s | "What I'll show you is the same decision made from a forecast." |
| **Show** | 60–120 s | Point at **one thing at a time** and describe what's on screen. **Don't narrate clicks** ("now I click here, then I go there"). |
| **Tell: the business benefit** | 15–20 s | "Alex, this is your **waste** number: every manager plans like your best manager." |
| **One technical line** | 10 s | "Shreya: the model is registered in Unity Catalog and only promoted if it beats the baseline." |
| **Transition** | 5 s | "That's how she plans. Next, how she handles a delivery." |

**Altitude rule:** give the business persona benefit and value language first. Save jargon
(TTL, caching, MCP, gateway, Postgres) for the technical persona's one line, and keep it to
one line.

**Show the proof live.** If the technical persona asks "is it real time?", make the screen
update in front of them. A promise to "show that later" that never happens costs credibility.

**Keep your promises.** Only defer something you can place on the agenda ("I'll show that in
the next section"), then deliver it there. If you have to say "I'll come back to that" more
than once, or the persona asks the same question twice, you've lost control of the
conversation.

---

## 6. Path to production: the segment that decides the technical score

Leaving this out is the most common reason for a low production-readiness score. A strong
CI/CD story with thin security still falls short. Cover all eight areas **at the same depth**,
and say clearly what exists **today** and what the **pilot adds**. Honesty about gaps scores
better than overclaiming.

| Area | What to cover | Example wording |
|---|---|---|
| **1. Deploy from code** | Bundles or Terraform in Git; nothing hand-built in the UI | "The pipeline, jobs and apps are defined in a Databricks Asset Bundle in Git and deployed with one command." |
| **2. Environments and promotion** | dev → staging → prod; separate catalogs; deployed by a CI service principal | "Each environment has its own catalog and service principal. Prod is deployed by CI, never by a person." |
| **3. Testing** | Unit tests, bundle validation, deploy to staging, run the evaluation there, a gate before prod | "Every pull request runs unit tests and the AI evaluation in staging. Prod deploys only when it's green." |
| **4. Rollback** | Code, app, model and data, one line each | "Redeploy the previous Git tag; point the model's champion alias back at the previous version; Delta time travel for a table." |
| **5. Bad data and schema drift** | Expectations, quarantine, schema evolution, what happens when a source changes | "Expectations drop or quarantine bad rows before gold. New source columns land in bronze without breaking anything. Silver only takes named columns, so gold changes only when we decide." |
| **6. Security controls** | Name the actual mechanism, not "it's governed" | "A row filter on store_id, mapped to groups synced from your identity provider through SCIM. Column masks on supplier and staff PII. API keys in secret scopes, not in code." |
| **7. Identity and network** | SSO, SCIM, Private Link or IP access lists | "Single sign-on through your identity provider; the workspace on Private Link inside your network." |
| **8. Monitoring and alerts** | Job failure alerts, quality-score history, thresholds, who gets notified | "The daily job alerts on failure. The AI quality score is stored every morning, and below 0.80 opens a ticket." |

**Avoid:**
- "It's governed at the catalog level, and I'll talk more about governance later", unless you come back to it with specifics.
- "That's very easy to build." Say instead: "That's a pilot deliverable; I'll confirm scope with our account team."

**Turn a gap into a commitment:**
> "The monitoring dashboard isn't built yet. I'll have a first version ready for the pilot kickoff."

**A real incident helps.** If something broke during the build and was fixed, tell it in 30
seconds: what broke, how the logs showed why, how it was rolled back, and what alert was added.

---

## 7. Handle objections with A-C-A-N

**A**cknowledge → **C**larify → **A**nswer with options and trade-offs → **N**ext step.

| Step | Example ("can it tell a negotiated price from an overcharge?") |
|---|---|
| **Acknowledge** | "That's exactly the right question: a false flag wastes the manager's time." |
| **Clarify** (one question) | "Where do negotiated prices live today: on the PO, or in a separate contract?" |
| **Answer with options and trade-offs** | "The check is rule-based against the PO price. If renegotiated prices reach the PO or a contract table we ingest, the line matches. If they only live in email, it's flagged. That's the safe failure, because a person approves. The trade-off is more flags until the contract feed is connected." |
| **Next step** | "In the pilot we measure the false-flag rate on your real invoices, against a target your finance team signs off." |

**Offer choices instead of "it's configurable."** For example, on stale cached answers:
> "Three options. One: clear the cache whenever inventory updates. That's always fresh, but costs a little more compute. Two: match the cache life to the four-hour refresh. That's cheapest, but can be up to four hours stale. Three: skip the cache for inventory questions and keep it for SOP answers. Which matters more to you, freshness or cost?"

**Phrases to replace:**

| Don't say | Say |
|---|---|
| "I hope it works", "I believe it should" | "Here's how we'll measure it in the pilot: [metric, target, who signs off]." |
| "It's very easy" | "It's a pilot deliverable; I'll confirm scope with the account team." |
| "Everything is configurable" | Two or three options, each with its trade-off, then ask which fits. |
| "I'll come back to that" | "I'll show that in the next section", then show it there. |

**Before you give any date**, name the dependencies and involve the account team:
> "We can start about two weeks after three things are in place: data access, the pilot stores named, and an identity and network contact. I'll confirm scope and resourcing with our account team this week."

---

## 8. Close on the persona's own number, with a downside case

Lead the close with the number the persona chose, even if another line in the business case
is bigger.

**Close in this order (about 2 minutes):**
1. **Their number first:**
   > "Alex, you said waste is the number you need to move. Today it's ₹4,572 per store a month, measured, and it varies 3× between stores. The forecast targets a 25% cut, and the pilot measures it store by store against each store's own baseline."
2. **The rest as upside:**
   > "On top of that, invoices and manager time add most of the value: about $264,000 a year in total."
3. **A downside scenario.** Answer "what if it only half works?" before they ask:
   > "Even if waste only falls 10%, the total barely moves, because most of the value is invoices and manager time. Payback stays at about four months."
4. **Measured versus assumed:**
   > "These are assumptions, and they're written down. So I'm not asking you to believe the number; I'm asking for six weeks to measure it."
5. **The pilot, with their metric in the go/no-go:**
   > "Go/no-go: at least 50% less manager time, AI correctness of 0.80 or more, no increase in stockouts, and **waste down in the pilot stores**."
6. **Dependencies and the account team** (section 7).
7. **One next step per person, each with a date:**
   > "Alex: name five stores by Thursday. Shreya: masked data and an identity contact. Me: the plan and a confirmed timeline by Friday."
8. **Recap the roadmap in one breath, then thank them:**
   > "Ask, see, act, plan, on one governed platform. Thank you both."

**When a persona pushes on an assumption, answer with numbers straight away.**

| Weak | Strong |
|---|---|
| "I'm confident from the general number; it's just market data." | "Fair push. The 25% is an assumption, and here's the downside. At 10%, the waste line drops from about $3,100 to $1,200 a year. The total goes from $264,500 to about $262,700, and payback stays under four months. Our measured waste is double what the model assumes, so the line is conservative. The pilot gives you the real number per store." |

**Don't invent support for an assumption.** If a number is assumed, say so, then give the
downside math.

---

## 9. Prepare for follow-up questions

After the call the judge asks one or two follow-up questions. They usually test the weakest
assumption or a scenario where the pilot only partly succeeds. Typical examples:

| Follow-up | Answer pattern |
|---|---|
| "How will you validate accuracy across different suppliers and document formats?" | A hand-checked test set (about 50 real documents across every supplier and format); measure field accuracy and flag accuracy (caught and false); finance signs off the target; low-confidence results go to manual review |
| "What if the pilot hits its time and accuracy goals, but waste only falls 10%?" | Give the downside math (section 8) and say whether the decision still holds. Then: "We'd investigate why, store by store: forecast accuracy, or adoption of the prep plan. Then decide whether to expand that use case." |

**General pattern:** restate the scenario → the number → whether the decision changes → what you'd do next.

---

## 10. Delivery card

**Fillers.** "You know", "like", "okay?", "correct?" and "does it make sense?" add up fast.
Replace them with a pause, or a **specific** check-in:
> "Alex, is that how invoice disputes work in your stores today?"

**Pace**
- Slow down on screens.
- Pause for two seconds after each key number.
- Never read a screen word for word: point at one thing and explain why it matters.

**Pronunciation.** Words that are often flagged:

| Word | Say it as |
|---|---|
| parse / parsing | /pɑːrs/, with the R. Not "pass" |
| waste | /weɪst/, with rounded lips. Not "base" |
| invoice, delivery, volume, versioned | a real /v/: top teeth on your lower lip |
| spreadsheet | a long "sheet" /iː/, not "sit" |
| discrepancy | stress the second syllable: dis-**CREP**-an-cy |
| product and company names | slowly and clearly the first time; transcripts often mis-hear them |

**Accuracy is part of professionalism.** Common slips that undermine trust:
- quoting a different figure from the deck;
- using the wrong word for a business object (for example "overdue payments" when you mean "overdue deliveries");
- claiming a control that isn't built yet;
- dropping a "not" ("I'm asking you to believe…").

**Timing**
- Plan about 20 minutes of demo, 6–8 minutes of questions and 2 minutes to close.
- If you're running late, cut the second example in a segment. Never cut the close.

---

## 11. Self-check (run it right after the call)

- [ ] I asked for the business persona's one number, said where I'd address it, and **delivered it there**.
- [ ] Every segment had: pain → what I'll show → show → "this is your ___ number" → one technical line → transition.
- [ ] I covered all eight path-to-production areas, at the same depth.
- [ ] Every objection got acknowledge → clarify → options with trade-offs → next step.
- [ ] I didn't say "hope", "believe", "very easy" or "configurable" without giving options.
- [ ] I stated dependencies and mentioned the account team before any date.
- [ ] The close led with their number, included a downside case, and the go/no-go included their metric.
- [ ] One next step per person, each with a date, and a closing recap of the roadmap.
- [ ] I used one value figure throughout, and labelled every number measured or assumed.
- [ ] I finished inside 30 minutes.
