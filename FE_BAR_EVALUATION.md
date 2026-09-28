# FE Bar submission evaluation — 28 September 2026

## Verdict

**Not ready to claim a full pass.** The repository has implementations and committed execution records for all six required product stages. The evidence for the invoice and preparation workflows is still illustrative, the measured Genie Agent correctness is 0.50, and the live roleplay and public repository access were not verified in this audit. The FE Bar evaluator, rather than this review, determines the actual rating.

The assessment used read-only checks of the current checkout; this report is the only file added. Databricks CLI profile `DEFAULT` reported `Valid: NO`, and this environment could not resolve `github.com`, so live workspace state and GitHub readability could not be checked independently. Statements marked **recorded** below are supported by committed text, not a fresh workspace query.

## Rubric assessment

| Domain | Assessment | Basis |
|---|---|---|
| Product | **Substantially built; integration needs a final check** | Recorded completed Lakeflow update, 14 bronze + 14 silver + 7 gold tables, Unity Catalog, four Lakebase serving tables, Genie Agent mode, and an app whose inventory panel calls Lakebase. See `evidence/01`, `/02`, `/04`, `/07`, `/09` and `apps/main-chat-app/static/index.html`. |
| Industry | **Good scenario; demonstration claims need correction** | Fictional 37-store food-service business, synthetic data, store/supplier/inventory keys, and KPI assumptions. Current preparation and invoice examples conflict with the generated data and require real outputs. |
| Build + AI mindset | **At risk** | Text-readable pipeline, DQ, Lakebase, Genie, app, and MLflow records exist. The measured Agent mode run is 0.50 correctness, 1.00 relevance, 1.00 safety on ten questions; groundedness was not scored. `evidence/06` presents a representative output rather than a captured invoice API result. |
| Customer skills | **Deck exists; roleplay unverified** | `deck/FE_BAR_DECK.md` has the required story and assumptions. `DEMO.md` still describes the old MAS/KA flow. No roleplay score or rehearsal result is present. |

## Verified in the checkout

1. `evidence/01_lakeflow_run.txt` records completed update `065d6a70-b298-4ccc-be9f-9c0433da45ea`, with row counts for 35 pipeline datasets.
2. `evidence/03_data_quality_results.txt` contains per-constraint counts. Its 45 constraints match the 45 `CONSTRAINT` definitions in `src/pipeline/02_silver.sql`.
3. `evidence/04_lakebase_queries.txt` records four synced operational tables; `evidence/07_app_health_and_api_tests.txt` contains an authenticated inventory response. The UI fetches `/api/lakebase/inventory/STR-001`.
4. `evidence/09_mlflow_evaluation_results.md` includes two measured MLflow run IDs, scores, trace IDs, and failed-case analysis. `scripts/run_genie_evaluation.py` is the current evaluation source. The four older KA/MAS notebooks still have no committed output cells and are no longer the current evaluation path.
5. A business deck and ten text evidence files are committed. Local `main` tracks `origin/main`; GitHub access was not verified from this environment.

## Remaining work, in priority order

### 1. Replace illustrative workflow evidence with captured results

- `evidence/06_genai_model_outputs.md` says its preparation answer is **representative** and asks for a real trace ID. It also says invoice dates were updated to fit the dataset. Commit the actual `POST /api/parse-invoice` response, the actual PO and line-item query results, and an actual advisor response with trace/run identifiers. Clearly label any mock example as mock.
- Reconcile the numbers before demonstrating invoice leakage: the listed invoice price differences are ₹3,990 (30×₹100 + 12×₹20 + 25×₹30), while `evidence/06` says ₹2,300. The generator gives Coorg Coffee Estates a seven-day lead time, while the preparation answer says one day. Do not call the invoice workflow measured until it has a timestamped response and elapsed time.
- The preparation answer calls 27 July 2026 a Sunday; it was a **Monday**. It also claims 892 normal Sunday orders for one store, although 200,000 generated orders across 37 stores over roughly 103 days average about 52.5 orders per store per day. Sales orders stop on 14 May 2026. Replace that answer with a real response grounded in the actual dates and demand.

### 2. Improve and correctly describe the current AI evaluation

- Keep the measured 0.50 correctness result visible; it is useful honest evidence, but weak for a strong AI-quality claim. Investigate the five failed questions, improve the document/answer setup or evaluation rubric with explicit justification, then run and commit a third comparable evaluation. Do not present the unscored groundedness metric as a pass.
- The original `febar.md` asks for eval notebooks with visible outputs. The present run uses `scripts/run_genie_evaluation.py` and a text report. Either commit its actual job output as text (with run/trace IDs) and document why the old notebooks were superseded, or commit a current executed notebook. The FE Bar accepts text run output, so old notebooks need not be run merely for appearances.

### 3. Align the buyer story and repository docs with the deployed architecture

- `deck/FE_BAR_DECK.md` says payback is **3.6 months** on slide 4 and **4.8 months** later; the KPI file says 4.8 months. With its stated $70,000 one-time implementation and $264,500 annual benefit less $50,000 annual operating cost, simple payback is about **3.9 months**. Pick one definition, show the formula, and use it everywhere.
- `README.md`, `ARCHITECTURE.md`, `febar.md`, and `DEMO.md` still describe old KA/MAS agents, a pipeline awaiting deployment, empty evidence, or a setup script that recreates the old architecture. Update them to the actual Genie Agent mode path, 14/14/7 run, Lakebase UI path, and measured evaluation. A reviewer starting at the README currently gets an inaccurate map.
- Treat annual savings as **assumptions**, not measured customer outcomes. The repository has a synthetic demo and no timed baseline/reconciliation trial proving the claim that 30 minutes became seconds.

### 4. Finish submission checks and roleplay

- Verify the submitted GitHub URL is publicly readable (or connected to the submission form) from an unauthenticated browser; the local remote alone does not prove this.
- Review text evidence and deck for internal workspace URLs, app/endpoint IDs, and personal workspace details before public submission, as required by the source FE Bar guide.
- Rehearse the two-persona roleplay with the current Genie workflow and prepare answers on data freshness, sync timing, invoice human approval, the 0.50 correctness result, and assumed ROI. The roleplay is scored separately and cannot be certified from repository files.

## Submission judgment

**Build evidence: much stronger than the earlier audit. Full FE Bar pass: not established.** The most consequential remaining issue is provenance and consistency of the invoice/preparation evidence. After that, improve AI quality, reconcile the value story, update the stale entry-point docs, and verify public access and roleplay performance.
