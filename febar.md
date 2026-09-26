# FE Bar — Kaapi Bricks Working Copy

Working folder for the FE Bar submission. **The repo root IS the submission** — the project was
flattened out of its old `Aidays_finale/kaapi_bricks_DEMO/` nesting on 2026-09-26, and the
unrelated sibling apps (`kaapi-bricks-india-app`, `kaapi-ops-mcp`, `openai_custom_sdk`,
`operations-advisor`, old `notebooks/`) were dropped so the evaluator reads one clean journey.
Git history, venvs, `.databricks` terraform state and the cleartext `sec` credential file were
all left out of the copy. Original untouched at `../Aidays_finale/`.

**Layout:** see `ARCHITECTURE.md` · **Lakeflow design:** see `LAKEFLOW_PLAN.md`
**Working title:** Kaapi Bricks Intelligent Store Operations
**Industry:** multi-location food service and specialty retail
**Data:** fully synthetic (Faker: ~15k customers, ~200k orders, 37 stores) — no real customer identity

---

## Why this base (verified against the real code, 2026-09-24)

Three candidate projects were checked layer-by-layer. Kaapi Bricks is the only one that is
already public-safe (fully synthetic, no real customer names, no hardcoded secrets) **and**
has 5 of the 6 mandatory layers built.

| Layer | Kaapi Bricks | Novartis v2 | tELCOM |
|---|---|---|---|
| Lakeflow pipeline | ❌ (one-time `read_files()` batch) | ❌ | ⚠️ Auto Loader only |
| Unity Catalog | ✅ | ✅ | ✅ |
| Lakebase | ✅ | ✅ | ✅ |
| ML / GenAI | ✅ KA + MAS + doc parse + MLflow | ✅ | ❌ none distinct |
| Genie | ✅ | ✅ | ✅ |
| Databricks App | ✅ (4 apps) | ✅ | ✅ |
| Public-safe | ✅ synthetic, no secrets | ❌ real Novartis names/URLs | ❌ cleartext token + real customer |

---

## Verified current state of this copy

- ✅ Unity Catalog: catalog `fevm_cme_conde_catalog`, schema `kaapi_bricks`, volume `raw_data`, 14 Delta tables — `scripts/generate_data.py`, `scripts/create_mcp_connection.py`
- ✅ Lakebase: chat history, messages, feedback, QA semantic cache — `apps/main-chat-app/app.yaml`, `app.py`
- ✅ ML/GenAI: Knowledge Assistant + Multi-Agent Supervisor + `ai_parse_document` invoice parsing + MLflow eval notebooks — `scripts/run_ka_evaluation.ipynb`, `run_mas_evaluation.ipynb`
- ✅ Genie Space: `scripts/create_agents.py`, wired into app + MAS
- ✅ Databricks Apps: main-chat-app, growth-advisor-agent, promo-agent, mcp-server
- ✅ Demo narrative: `DEMO.md` (invoice reconciliation ~30 min → seconds)
- ✅ Secret removed: cleartext `sec` file deleted from this copy; `.gitignore` added

---

## Gap checklist to pass (ordered by priority)

### 1. Lakeflow pipeline — the one true product gap  🟡 CODE WRITTEN, DEPLOY PENDING
**Full design in `LAKEFLOW_PLAN.md`** (13 bronze → 13 silver → 7 gold, mapped to the real schema).
- [x] Edit `scripts/generate_data.py`: land raw per-entity dirs, remove the `read_files()` CTAS
- [x] Create `databricks.yml` (bundle root)
- [x] Create `resources/kaapi_pipeline.pipeline.yml` (serverless LDP, UC-enabled)
- [x] `src/pipeline/01_bronze.sql` — 13 Auto Loader streaming tables
- [x] `src/pipeline/02_silver.sql` — 13 conformed tables + expectations
- [x] `src/pipeline/03_gold.sql` — 7 operational/KPI tables
- [x] `scripts/drop_legacy_tables.sql` — one-time migration so the pipeline owns the 13 names
- [ ] **DEPLOY & RUN** (needs `databricks auth login` first):
      `databricks bundle deploy -t dev --profile DEFAULT` → `... run kaapi_bricks_medallion ...`
- [ ] Re-run `scripts/generate_data.py` so raw lands in per-entity dirs
- [ ] Confirm the same entities/keys flow raw → bronze → silver → gold (one integrated journey)
- [ ] Point Genie Space + app at the pipeline-owned silver/gold tables (names unchanged, should just work)

### 2. Lakebase operational serving (make it unambiguous)
- [ ] Sync/write selected gold operational data (current inventory, open POs, delivery exceptions, recommended prep qty) to Lakebase
- [ ] Make at least one app workflow READ business data from Lakebase (not just app memory/cache)

### 3. Committed execution evidence (text-readable — evaluator reads text only)
- [ ] Create `evidence/` folder
- [ ] `01_lakeflow_run.txt` — pipeline name, update ID, status, times, row counts
- [ ] `02_uc_tables_and_lineage.md` — table names + lineage raw→bronze→silver→gold
- [ ] `03_data_quality_results.txt` — expectations passed/failed counts
- [ ] `04_lakebase_queries.txt` — schemas, tables, row counts, sample operational queries
- [ ] `05_genie_questions_and_answers.md` — real questions, generated SQL, results
- [ ] `06_genai_model_outputs.md` — real invoice-parse + advisor inputs/outputs
- [ ] `07_app_health_and_api_tests.txt`
- [ ] `08_end_to_end_record_trace.md` — one delivery/inventory event raw → app
- [ ] `09_mlflow_evaluation_results.md` — scores + one failed-case analysis
- [ ] `10_business_kpi_calculations.md`
- [ ] Re-run eval notebooks and COMMIT them with output cells visible

### 4. Business presentation deck
- [ ] Build deck (PDF or `.md`) leading with outcome + quantified value, not architecture
- [ ] Follow required 10-section outline (context → problem → pain → outcome → journey → arch → governance → AI controls → value → pilot)

### 5. KPI math
- [ ] Explicit assumptions: labor saved, invoice leakage prevented, stockout reduction, waste reduction, annual value
- [ ] Industry KPIs: stockout rate, waste rate, invoice exception rate, supplier fill rate, forecast error, labor min/delivery, margin leakage

### 6. Repo readiness
- [x] Fresh working copy created, secret scrubbed, `.gitignore` added
- [x] `git init` + commits (repo flattened; project is now the tracked submission root)
- [ ] Push to a public (or submission-connected) GitHub repo
- [ ] Verify repo is readable by the submission form

---

## Roleplay prep (Customer Skills)
- [ ] Rehearse 12–15 min demo, tell-show-tell per section
- [ ] Business objections: cost, risk, rollout time, ROI
- [ ] Technical objections: architecture, identity/access, data quality, model grounding, observability, failure handling

---

## Notes
- Full FE Bar rubric + reference guide: `../febar.md`
- Original untouched project: `../Aidays_finale/`
- ⚠️ Rotate the service-principal secret that was in the old `sec` file — it sat in cleartext.
