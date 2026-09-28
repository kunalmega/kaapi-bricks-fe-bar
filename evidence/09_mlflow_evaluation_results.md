# MLflow Evaluation Results — Kaapi Bricks Genie Agent

Five runs on the same 10-question dataset. Runs 1–3 evaluate **Genie directly**. Runs 4–5 evaluate the **deployed app end to end** (what a store manager sees). Run 4 is void (incomplete scoring); run 5 is the current headline result.
Every score below was read back from MLflow. None are estimates.

| Field | Value |
|---|---|
| Workspace | <workspace-host> |
| Experiment ID | 982411422225142 |
| Notebook | `scripts/run_genie_evaluation.py` (workspace: `kaapi-bricks-setup/run_genie_evaluation`) |
| System under test | Genie Space `01f12a63ec1011e0acbb09158eda7634`: 21 silver + gold tables + SOP PDF volume |
| Dataset | 10 store-manager questions (recipes, SOPs, food safety, suppliers), 32 expected facts in total |

## Results

**Headline (run 5, deployed app end to end, all 10 scored): Correctness 0.70 · Relevance 1.00 · Safety 1.00.**
History below. Runs 1–3 are Genie-direct; runs 4–5 are in *Runs 4–5* further down.

| Scorer | Run 1: baseline | Run 2: Agent mode | Run 3: + completeness instruction |
|---|---:|---:|---:|
| Correctness | 0.00 | 0.50 | **0.50** |
| Expected facts covered† | n/a | 28 / 32 | **28 / 32** |
| RelevanceToQuery | 0.30 | 1.00 | **1.00** |
| Safety | 1.00 | 1.00 | **1.00** |
| RetrievalGroundedness | 1.00* | not scored* | not scored* |

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| MLflow run ID | 17e8de540367484f82992d96b4a8fea9 | cbf7938448934232baa109b09a0cb8b1 | 0878d859cce847c3b970551c4c3defac |
| Job run ID | 53486188180466 | 838317136685612 | 908303685979606 |
| Started (UTC) | 2026-09-28 07:38 | 2026-09-28 11:59 | 2026-09-28 13:58 |
| Genie API | Chat mode `start-conversation` | Agent mode `agents/{id}/responses` (SSE) | Agent mode (same) |
| Change under test | — | API switch | Genie instruction: include price, supplier terms, use-by windows |

† Our own tally of expected facts present in each answer, taken from the judge rationales. It is not an MLflow metric.

\* In Run 1 the retriever span was fed Genie's own answer text, so Groundedness 1.00 was trivially true. Agent mode returns citation IDs (`:citation[volume_file.…]`) but not the retrieved chunks, so there is nothing real to score. We dropped the scorer instead of reporting a meaningless number.

## What changed between runs

**Run 1 root cause:** The SOP/recipe PDFs were attached to the Genie space, but the app and the eval called the **Chat mode** conversation API. Chat mode only works with structured tables. Genie declined 7 of 10 document questions ("I can't answer that from this database…"). It didn't make anything up, which is why Safety held at 1.00.

**Fix:** switched `call_genie_sync()` in `apps/main-chat-app/app.py` and `predict()` in the eval to the **Agent mode** API. Agent mode reads the files in the attached volume and cites them. No other changes: same dataset, same scorers, same Genie space.

## Run 2 per-question results

| # | Question | Correct | Facts covered† | What was missing | Trace ID |
|---|---|---|---|---|---|
| 1 | How do I make a Classic Filter Coffee? | no | 5 / 6 | price (Rs.60) | tr-5730eb7235edd1590824cc435245d259 |
| 2 | What is the correct decoction ratio and timing? | **yes** | 4 / 4 | — | tr-dc88f9a50de2b871bba409e07e837e98 |
| 3 | Barista response to a nut allergy? | **yes** | 4 / 4 | — | tr-4d0371ab77e9e52fc30f5c0959b40a1f |
| 4 | How long does Coorg Arabica take to reorder? | no | 2 / 3 | minimum order 50 kg | tr-039415e0411b8af15896441b6fa316d3 |
| 5 | At what temperature should milk be stored? | no | 2 / 3 | "use within 2 days of delivery" | tr-c4b183dd61fad7cd8990e8dca22bb18e |
| 6 | How do I clean the brass filter coffee maker? | **yes** | 4 / 4 | — | tr-742821752c8b89c779ab8cb9804db9fe |
| 7 | How can I open a Kaapi Bricks franchise? | **yes** | 2 / 2 | — | tr-dde30674e3255f368f0db4257d3cd44c |
| 8 | How do I make Masala Chai? | no | 1 / 2 | price (Rs.50) | tr-88d47b5c05c3ffc5ad522f1998e38ebe |
| 9 | Who supplies our milk and on what terms? | no | 2 / 2 | nothing (judge error, see below) | tr-957c961167fbbca74fcb4de6836e88f1 |
| 10 | How long can prepared decoction be kept? | **yes** | 2 / 2 | — | tr-336f6978eeee74bb75bafd63f4fc84f0 |

† Fact coverage is our own tally from each judge rationale, not an MLflow metric. **28 of 32 expected facts (87.5%) appear in the answers.**

## Failure analysis

- **All-or-nothing judge on secondary facts (Q1, Q8).** The recipe answers were correct and complete, but left out the menu price the question never asked for. `Correctness()` fails a response that is missing any single expected fact.
- **Details not surfaced from the documents (Q4, Q5).** The answers covered the main point (7-day lead time; 2–4 °C storage) but missed a secondary detail stated in the PDFs (the 50 kg minimum order; use within 2 days). These are real retrieval gaps.
- **Judge error (Q9).** The rationale confirms "Nandini Dairy does supply both Full Cream Milk and Toned Milk", which are both expected facts. It then fails the answer because the *expectation* doesn't mention delivery terms. The fault is in the grading, not in the answer.

## Run 3: did the instruction change help?

**Change (one variable only):** the same dataset, scorers and Genie space, with one instruction added.
The instruction tells Genie to include every operational detail the documents state: menu price for
drinks; lead time, minimum order and payment terms for suppliers; storage temperature and use-by
window for perishables.

**Why:** three of the four genuine misses in run 2 were facts that exist in the PDFs but were left
out of the answer. The prices appear in the recipe headings (`## Classic Filter Coffee (PRD-001) - Rs.60`),
and the 50 kg minimum is in the supplier agreements. We confirmed this against the document source
(`scripts/generate_ka_documents.py`), so these are answer gaps, not test-set defects.

**Result: Correctness unchanged at 0.50; the mix of failures shifted.**

| Question | Run 2 | Run 3 | Note |
|---|---|---|---|
| Milk storage temperature | fail | **pass** | now includes "use within 2 days" (instruction worked) |
| Franchise | pass | **fail** | dropped "available across India and select international markets" |
| Classic Filter Coffee | fail | fail | price still omitted |
| Masala Chai | fail | fail | price still omitted |
| Coorg Arabica reorder | fail | fail | 50 kg minimum still omitted |
| Milk supplier | fail | fail | same judge error (both expected facts confirmed present) |
| Other 4 | pass | pass | |

Run 3 traces: milk supplier tr-a3fba1900b33cc7758c17b2b4f14684d · Masala Chai tr-0e558275488b5d3b8b9b46484814e050 ·
franchise tr-2ea310d45318ff74b3dd7d106e2646c9 · Coorg tr-856089e36520743fb58666d8c3c6d41d ·
Classic Filter Coffee tr-44252b2e5af9321de02f7ec0e130a155.

**Conclusion:** a prompt-level instruction is not a reliable way to force completeness. It fixed
one omission, a different fact was dropped, and prices stayed missing. With 10 questions, a swing
of ±1 question between runs is within normal variation, so 0.50 is the stable result. Pushing this
higher needs a structural change, not more prompt text (see Next iteration).

## Runs 4–5: evaluating the deployed app end to end

Runs 1–3 called Genie directly. The store manager uses the **app**, which adds a governed
menu-price lookup on top of Genie Agent mode: after Genie answers, menu items named in the question
are matched against `products.base_price` and the price is appended if missing. That follows
from run 3: structured facts should come from tables, not model recall. Runs 4–5 therefore call
the deployed app's `POST /api/chat` with `skip_cache: true`, so every answer is fresh.

- Script: `scripts/run_app_evaluation.py` (runs locally against the deployed app)
- Dataset: `scripts/eval_dataset.json`, extracted verbatim from `run_genie_evaluation.py`
  (same 10 questions, same 32 expected facts)
- Scorers: the same `Safety()`, `RelevanceToQuery()`, `Correctness()`
- Each eval trace is tagged with the app's own trace ID (`app_trace_id`) and `from_cache`

| | Run 4 | Run 5 |
|---|---|---|
| MLflow run ID | bb82919a855e4341a31126dd36c60462 | **b14becd1d6384a9586d38726b3622de6** |
| Started (UTC) | 2026-09-28 ~14:25 | 2026-09-28 ~14:45 |
| Questions scored | **9 of 10** (void) | **10 of 10** |
| Correctness | 0.90 reported, **not valid** | **0.70** |
| RelevanceToQuery | 1.00 | **1.00** |
| Safety | 1.00 | **1.00** |
| Answers served from cache | 0 | 0 |

**Why run 4 is void:** an OAuth token refresh failed partway through the run
(`fetching OAuth endpoints … EOF`). The Masala Chai trace (tr-7bc39947ed1fe837ef16249754fb0f6b)
has **zero** assessments, so the reported 0.90 averages 9 questions, not 10. We re-ran the full
dataset instead of scoring the one missing question separately.

**Run 5 per-question results (all 10 scored):**

| Question | Correct | Price appended by lookup? | Note | Eval trace → app trace |
|---|---|---|---|---|
| Classic Filter Coffee | **yes** | **yes** | the lookup supplied Rs.60 | tr-598c5bf7… → tr-f221a083… |
| Masala Chai | **yes** | no | Genie included Rs.50 itself this run | tr-199704bc… → tr-740f7e4f… |
| Coorg Arabica reorder | **yes** | n/a | 50 kg minimum included this run | tr-e4910747… → tr-8e5015eb… |
| Milk storage temperature | **yes** | n/a | | tr-6e1b9dfb… → tr-1ef2e486… |
| Decoction ratio and timing | **yes** | n/a | | tr-cdae37af… → tr-171a00a4… |
| Decoction hold time | **yes** | n/a | | tr-2c7de898… → tr-d3bdd7ca… |
| Brass filter cleaning | **yes** | n/a | | tr-78380c30… → tr-9a540876… |
| Nut allergy | no | n/a | missed "if unsure, consult the manager" | tr-9a5215c0… → tr-ef1123d7… |
| Franchise | no | n/a | missed "India and select international markets" | tr-6a1e63d1… → tr-a4b0dea5… |
| Milk supplier | no | n/a | same judge error as runs 2–3 (both facts confirmed present) | tr-662a5d88… → tr-dea6f1fa… |

**How to read 0.70:**
- It is the best *complete* measurement so far, and it measures the product as deployed.
- The price lookup demonstrably fixed one question (Classic Filter Coffee: the price came from the table).
- The other gains (Masala Chai price, Coorg minimum order) came from Genie including the fact
  *this time*. Runs 2–3 show it doesn't do that reliably. Some of the gain from 0.50 to 0.70 is
  therefore run-to-run variation, which with 10 questions is about ±0.1–0.2.
- One of the three remaining failures is a grading error, so the correct-answer rate is 8/10 if
  that answer is counted as correct. We still report the judge's 0.70.
- **Safety has been 1.00 in every run.** When the agent lacks a fact, it omits it rather than
  inventing one. That matters most for allergen and food-safety questions.

## Operational trade-off

End-to-end latency through the deployed app's `/api/chat` for Q10 was **22.9 s** in Agent mode, compared with a few seconds in Chat mode. Agent mode reasons over several steps and reads documents. Mitigation already in the app: the Lakebase semantic cache (`kaapi_mcp.qa_cache`) serves repeat SOP questions instantly. SOP content changes rarely, so cache hit rates for these questions should be high.

## Next iteration

1. **Structured facts from tables, not documents. Done for menu prices** (runs 4–5). Extend the
   same lookup to supplier lead time and minimum order, which would need the contract terms loaded
   into a governed table.
2. **A rubric that separates must-have from nice-to-have facts.** Keep strict `Correctness()` for
   comparability, and add a `Guidelines()` scorer that grades the safety-critical facts (temperatures,
   hold times, allergen steps) separately from secondary ones (price).
3. **Larger dataset (≥30 questions)** so a one-question swing no longer moves the mean by 0.10.
4. Target for the next comparable run: Correctness ≥ 0.80, Relevance and Safety at 1.00.

## Reproduce

```python
import mlflow
mlflow.set_tracking_uri("databricks")
runs = mlflow.search_runs(experiment_ids=["982411422225142"],
    filter_string="attributes.run_id IN ('17e8de540367484f82992d96b4a8fea9','cbf7938448934232baa109b09a0cb8b1','0878d859cce847c3b970551c4c3defac','b14becd1d6384a9586d38726b3622de6')")
print(runs.filter(regex="run_id|metrics").T)
```
