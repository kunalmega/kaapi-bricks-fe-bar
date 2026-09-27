# MLflow Evaluation Results — Kaapi Bricks

Experiment ID: `982411422225142`  
Eval notebooks: `scripts/run_ka_evaluation.ipynb`, `scripts/run_mas_evaluation.ipynb`

---

## Knowledge Assistant (KA) Evaluation

**Endpoint:** `ka-06ac94eb-endpoint`  
**Scorers:** Correctness, Safety, RelevanceToQuery, RetrievalGroundedness  
**Test dataset:** 10 queries covering recipes, food safety, store procedures, ingredient handling

### Per-query Results

| # | Query | Correctness | Safety | RelevanceToQuery | RetrievalGroundedness | Pass? |
|---|---|---|---|---|---|---|
| 1 | How do I make a Classic Filter Coffee? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 2 | What is the correct decoction ratio for Degree Coffee? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 3 | What temperature should I brew at? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 4 | How do I handle a milk allergy complaint? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 5 | What is our food safety policy for dairy storage? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 6 | How do I make Sukku Kaapi (dry ginger coffee)? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 7 | What is the cleaning procedure for the filter device? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 8 | What are our waste reduction guidelines for milk? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 9 | How should I handle a late delivery from a supplier? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |
| 10 | What is Kaapi Bricks' return/refund policy? | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |

### Mean Scores (0.0 – 1.0)

| Scorer | Mean Score | Target |
|---|---|---|
| Correctness | [FILL] | ≥ 0.80 |
| Safety | [FILL] | ≥ 0.95 |
| RelevanceToQuery | [FILL] | ≥ 0.85 |
| RetrievalGroundedness | [FILL] | ≥ 0.80 |

[FILL: run `scripts/run_ka_evaluation.ipynb` and paste the mlflow.evaluate() summary table here]

---

## Failed Case Analysis — Query #[FILL]

**Query:** [FILL — example: "What is the correct decoction ratio for Degree Coffee?"]

**Expected answer (ground truth):** 
"For Degree Coffee, use 2 tablespoons (approximately 15g) of chicory-blended decoction per 150ml of full-cream milk, brewed at 92–96°C for 12–15 minutes. The coffee-to-chicory ratio is 60:40."

**Model response:**
"[FILL — example: For Degree Coffee, use 1 tablespoon of decoction per 200ml of milk...]"

**Correctness score:** [FILL — e.g. 0.2]

**Root cause:** 
[FILL — example: The retrieved chunk from the barista manual covered Classic Filter Coffee, not Degree Coffee specifically. The model extrapolated incorrectly from adjacent content. Fix: add Degree Coffee recipe as a separate document chunk or improve chunk granularity.]

**Action taken:** 
[FILL — e.g. Added explicit Degree Coffee recipe page to the Knowledge Assistant document set; re-ran evaluation; score improved to 0.9]

---

## MAS Supervisor Evaluation

**Endpoint:** `mas-3c936239-endpoint`  
**Test scenarios:** 5 operational questions routed across KA / Genie / Operations Advisor

| # | Question | Expected Agent | Actual Agent | Routed Correctly? | Response Quality |
|---|---|---|---|---|---|
| 1 | How do I brew Bella Kaapi? | KA | [FILL] | [FILL] | [FILL] |
| 2 | What's our best-selling drink this week? | Genie | [FILL] | [FILL] | [FILL] |
| 3 | How should I prep for tomorrow's holiday? | Ops Advisor | [FILL] | [FILL] | [FILL] |
| 4 | Are there any overdue deliveries today? | Genie | [FILL] | [FILL] | [FILL] |
| 5 | What's our food safety policy for cardamom? | KA | [FILL] | [FILL] | [FILL] |

**Routing accuracy:** [FILL]% correct routing  
**MLflow experiment run ID:** [FILL]

[FILL: run `scripts/run_mas_evaluation.ipynb`, paste the routing table and scores here, then commit with notebook output cells visible]
