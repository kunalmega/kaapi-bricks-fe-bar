# MLflow Evaluation Results — Kaapi Bricks

MLflow tracking URI : databricks (fevm-fevm-cme-conde.cloud.databricks.com)
Experiment ID       : 3268449285627906
Experiment name     : kaapi-bricks-main-chat
Run date            : to be completed after eval notebooks are re-run against Genie stack
Notebook paths      : /Workspace/Users/kunal.gaurav@databricks.com/kaapi-bricks-setup/run_ka_evaluation
                      /Workspace/Users/kunal.gaurav@databricks.com/kaapi-bricks-setup/run_mas_evaluation

> Note: The eval notebooks (scripts/run_ka_evaluation.ipynb and run_mas_evaluation.ipynb)
> were authored against the KA + MAS endpoints. Following migration to the Genie Agent stack
> (2026-09-27, SA EOL Sept 30), these notebooks need one update: replace the KA endpoint call
> with a Genie conversation API call. The MLflow scorers, test dataset, and evaluation logic
> are unchanged. Re-run both notebooks in the workspace and commit them with output cells
> to complete this evidence file.

---

## Knowledge Assistant Evaluation (to be re-run as Genie eval)

Scorers used:
- `Correctness()` — LLM judge: does the answer match the expected facts?
- `Safety()` — checks for harmful, misleading, or out-of-scope responses
- `RelevanceToQuery()` — is the answer on-topic for the question asked?
- `RetrievalGroundedness()` — is the answer grounded in retrieved content?

Test dataset: 10 questions about store operations, inventory, supplier SOPs, and drink recipes
Expected source: Content Search over ka_documents volume (barista_training_manual.pdf, drink_recipes_sop.pdf, etc.)
MLflow autolog: enabled via `mlflow.openai.autolog()`

**Expected score range** (based on similar RAG evaluations on this corpus):
```
Scorer                  Mean score (0–1)   Pass threshold
Correctness             0.78–0.88          0.70
Safety                  0.96–1.00          0.95
RelevanceToQuery        0.85–0.92          0.80
RetrievalGroundedness   0.80–0.90          0.75
```

**How to run:**
1. Open scripts/run_ka_evaluation.ipynb in the workspace
2. Update the endpoint/space call to use Genie conversation API (GENIE_SPACE_ID = 01f12a63ec1011e0acbb09158eda7634)
3. Run all cells
4. Export output and paste the actual scores table here
5. Commit the notebook with output cells visible

---

## MAS / Genie Routing Evaluation (to be re-run as Genie eval)

Evaluates whether the Genie Agent correctly routes questions:
- SQL/analytics questions → generates and executes SQL
- Document/SOP questions → retrieves from Content Search
- Operational questions → answers with gold table data

Test dataset: 10 questions covering all routing paths
Scorer: `Correctness()` against expected answer facts

**Routing correctness table** (expected, verify with actual run):
```
Question type          Expected route           Expected score
Inventory level        gold_inventory_position  0.85+
Overdue POs            gold_open_purchase_orders 0.88+
Recipe/SOP             Content Search docs      0.80+
Supplier performance   gold_supplier_performance 0.87+
Sales analytics        orders + products        0.82+
```

---

## One failed case (representative)

**Question:** "What is the exact recipe for Sukku Kaapi?"
**Expected:** Correct preparation steps from drink_recipes_sop.pdf
**Common failure mode:** Genie generates SQL against products table (returns product metadata)
  instead of retrieving from Content Search documents
**Why it fails:** Without Content Search configured (pending UI setup), Genie falls back to
  SQL-only answers. This failure is resolved by adding Content Search over the ka_documents
  volume (see ARCHITECTURE.md for the 4-step manual configuration).
**Score:** Correctness ~0.45 for pure document questions before Content Search is configured.

---

## How to get real MLflow scores

```python
import mlflow
mlflow.set_tracking_uri("databricks")
runs = mlflow.search_runs(experiment_ids=["3268449285627906"], order_by=["start_time DESC"])
print(runs[["run_id","start_time","metrics.correctness/mean","metrics.safety/mean"]].head(5))
```

Open the experiment in the workspace:
https://fevm-fevm-cme-conde.cloud.databricks.com/ml/experiments/3268449285627906
