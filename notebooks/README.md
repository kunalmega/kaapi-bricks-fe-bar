# Executed proof notebooks

Each notebook ran against the live workspace on 2026-10-23/24 and is **committed with its
outputs**, so the results can be read on GitHub without running anything. Workspace URLs and
emails are masked in the saved output.

| # | Notebook | Proves |
|---|---|---|
| 01 | `01_pipeline_and_data_quality` | Lakeflow update timeline, 14/14/7 tables with row counts, 45/45 expectations from the event log |
| 02 | `02_row_level_security` | UC row filter on 10 tables; the same SQL and Genie question as HQ vs a store manager |
| 03 | `03_genie_agent` | Genie Agent answers with the generated SQL (`execute_sql`) and SOP search (`search_context_files`) |
| 04 | `04_app_lakebase_and_ai_workflows` | The deployed app: Lakebase dashboard latency, invoice check via Unity AI Gateway, prep plan with ML forecast + weather |
| 05 | `05_demand_forecast_model` | Forecaster vs baselines on a 14-day holdout, UC registration and `@champion`, scored forecast |
| 06 | `06_store_briefs_and_ai_gateway` | 37 morning briefs, number check, the facts given to the LLM, gateway payload log by caller |
| 07 | `07_evaluation_over_time` | Live `mlflow.genai.evaluate` of the app, the `eval_history` time series, per-question scores |

Re-run (CLI profile `DEFAULT`, Python 3.11 with `mlflow[databricks]`, `databricks-sdk`, `pandas`,
`scikit-learn`, `holidays`, `psycopg[binary]`):

```bash
cd notebooks && jupyter nbconvert --to notebook --execute --inplace 0*.ipynb
```

Notebook 02 signs in as the store-manager service principal from secret scope `kaapi`;
notebook 07 appends a row to `eval_history`. Shared code is in `proof_helpers.py`; the job code
it calls is in `../src/jobs/`.
