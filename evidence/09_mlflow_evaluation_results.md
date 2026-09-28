# MLflow Evaluation Results — Kaapi Bricks Genie Agent

Two measured runs on the same 10-question dataset: a baseline and a re-test after a fix.
Every score below was read back from MLflow. None are estimates.

| Field | Value |
|---|---|
| Workspace | fevm-fevm-cme-conde.cloud.databricks.com |
| Experiment ID | 982411422225142 |
| Notebook | `scripts/run_genie_evaluation.py` (workspace: `kaapi-bricks-setup/run_genie_evaluation`) |
| System under test | Genie Space `01f12a63ec1011e0acbb09158eda7634`: 21 silver + gold tables + SOP PDF volume |
| Dataset | 10 store-manager questions (recipes, SOPs, food safety, suppliers), 32 expected facts in total |

## Results

| Scorer | Run 1: baseline | Run 2: Agent mode + documents | Change |
|---|---:|---:|---:|
| Correctness | 0.00 | **0.50** | +0.50 |
| RelevanceToQuery | 0.30 | **1.00** | +0.70 |
| Safety | 1.00 | **1.00** | held |
| RetrievalGroundedness | 1.00* | not scored* | n/a |

| | Run 1 | Run 2 |
|---|---|---|
| MLflow run ID | 17e8de540367484f82992d96b4a8fea9 | cbf7938448934232baa109b09a0cb8b1 |
| Job run ID | 53486188180466 | 838317136685612 |
| Started (UTC) | 2026-09-28 07:38 | 2026-09-28 11:59 |
| Genie API | Chat mode `POST /api/2.0/genie/spaces/{id}/start-conversation` | Agent mode `POST /api/2.0/genie/agents/{id}/responses` (SSE) |

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

## Operational trade-off

End-to-end latency through the deployed app's `/api/chat` for Q10 was **22.9 s** in Agent mode, compared with a few seconds in Chat mode. Agent mode reasons over several steps and reads documents. Mitigation already in the app: the Lakebase semantic cache (`kaapi_mcp.qa_cache`) serves repeat SOP questions instantly. SOP content changes rarely, so cache hit rates for these questions should be high.

## Next iteration

1. Split each expected-fact list into "must answer" and "nice to have" facts, or score with a `Guidelines()` rubric, so a missing price doesn't fail a correct recipe.
2. Add an instruction telling Genie to include the menu price and supplier contract terms (minimum order, payment) when they appear in the documents.
3. Re-run with the same scorers. Target: Correctness ≥ 0.80, with Relevance and Safety kept at 1.00.

## Reproduce

```python
import mlflow
mlflow.set_tracking_uri("databricks")
runs = mlflow.search_runs(experiment_ids=["982411422225142"],
    filter_string="attributes.run_id IN ('17e8de540367484f82992d96b4a8fea9','cbf7938448934232baa109b09a0cb8b1')")
print(runs.filter(regex="run_id|metrics").T)
```
