# MLflow Evaluation Results — Kaapi Bricks Genie Agent

Measured results from a real evaluation run. Nothing on this page is estimated.

| Field | Value |
|---|---|
| Workspace | fevm-fevm-cme-conde.cloud.databricks.com |
| Experiment ID | 982411422225142 |
| MLflow run ID | 17e8de540367484f82992d96b4a8fea9 |
| Run start | 2026-09-28 07:38:05 UTC |
| Job run ID | 53486188180466 (serverless, TERMINATED / SUCCESS) |
| Notebook | `scripts/run_genie_evaluation.py` (workspace copy: `kaapi-bricks-setup/run_genie_evaluation`) |
| System under test | Genie Space `01f12a63ec1011e0acbb09158eda7634` (21 silver + gold tables; Content Search **not yet configured**) |
| Dataset | 10 store-manager questions (recipes, SOPs, food safety, suppliers) with expected facts |
| Scorers | `Safety()`, `RelevanceToQuery()`, `Correctness()`, `RetrievalGroundedness()` |

## Aggregate scores

| Scorer | Mean |
|---|---:|
| Safety | **1.00** |
| RetrievalGroundedness | **1.00** |
| RelevanceToQuery | **0.30** |
| Correctness | **0.00** |

## Per-question results

| # | Question | Relevance | Correctness | Trace ID |
|---|---|---|---|---|
| 1 | How do I make a Classic Filter Coffee? | yes | no | tr-09ad64a900fbd49f9ebd526f274eb372 |
| 2 | What is the correct decoction ratio and timing? | no | no | tr-32cce36f36bceccd460ea997060c4b49 |
| 3 | What should a barista do if a customer reports a nut allergy? | no | no | tr-61694c162a5e7f7381597ee256eaf236 |
| 4 | How long does Coorg Arabica take to reorder? | yes | no | tr-54ac46b414ca8443bbbd809e823f2e42 |
| 5 | At what temperature should milk be stored? | no | no | tr-89ab9abe4d57f47895fbaaf39b6106ca |
| 6 | How do I clean the brass filter coffee maker? | no | no | tr-eb3e64e8d3fa5f4ccc78de5cdd5e01d5 |
| 7 | How can I open a Kaapi Bricks franchise? | no | no | tr-a8a4aa4f3e246e214599eef1ee2d7acb |
| 8 | How do I make Masala Chai? | no | no | tr-a5c712be18acbfbc1e8ef4482f9f4253 |
| 9 | Who supplies our milk and what are their delivery terms? | yes | no | tr-24cb1a65b4e20e24e832a54c70dcce21 |
| 10 | How long can prepared decoction be kept before discarding? | no | no | tr-9eaf460454bcc9b74703580cf3ad29e8 |

## Failure analysis

**Root cause: the documents are not connected to the agent.** Seven of the ten questions (1, 2, 3, 5, 6, 7, 8, 10) can only be answered from the six SOP and training PDFs in `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/ka_documents/`. These PDFs were served by the Knowledge Assistant before it was deprecated. Content Search on the Genie space has not been set up yet, so the agent can see only structured tables. Real response to question 2:

> "I can't answer that from this database because it doesn't contain brewing SOPs or recipe instructions. I can only fetch data from the available tables on sales, inventory, purchase orders, suppliers, waste, customers, stores, products, and orders."

**Partial answers from structured data.**
- **Question 4:** Genie correctly returned "Coorg Arabica Beans from Coorg Coffee Estates has a reorder lead time of 7 days" from the `suppliers` and `ingredients` tables. The judge marked it incorrect because the expected fact "minimum order is 50 kg" appears only in the supplier agreements PDF.
- **Question 9:** Genie correctly identified the milk suppliers from the tables. It could not give delivery or payment terms, which exist only in the PDF.

**What went right.** Safety and Groundedness both scored 1.00. When the agent had no source, it said so and did not invent a recipe or a food-safety temperature. For a store-operations assistant, refusing is the right failure mode. A made-up allergen procedure or milk storage temperature would be a real safety risk.

## Remediation and re-test plan

1. Add Content Search to the Genie space: Settings → Content Search → Add Volume → `/Volumes/fevm_cme_conde_catalog/kaapi_bricks/raw_data/ka_documents`.
2. Run `scripts/run_genie_evaluation.py` again with the same dataset and scorers.
3. Acceptance targets for the re-test: Correctness ≥ 0.70, RelevanceToQuery ≥ 0.80, Safety = 1.00.
4. Add the re-test run ID and scores to this file next to the baseline above.

## Reproduce

```python
import mlflow
mlflow.set_tracking_uri("databricks")
runs = mlflow.search_runs(experiment_ids=["982411422225142"],
                          filter_string="attributes.run_id = '17e8de540367484f82992d96b4a8fea9'")
print(runs.filter(like="metrics.").T)
```
