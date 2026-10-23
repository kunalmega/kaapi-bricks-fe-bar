# FE Bar — Kaapi Bricks Submission Checklist

The repository root is the submission. It is a cleaned copy of the earlier Aidays project:
unrelated sibling apps, git history, virtual environments, Terraform state, and a cleartext
credential file were left out.

**Working title:** Kaapi Bricks Intelligent Store Operations
**Industry:** Retail & Consumer Goods (quick-service coffee chain)
**Data:** 100% synthetic, fictional company
**Start here:** `README.md` · **Deck:** `deck/FE_BAR_DECK.md` · **Roleplay:** `ROLEPLAY_PREP.md`

---

## Build — the six required layers

- [x] **Lakeflow**: serverless declarative pipeline, 14 bronze + 14 silver + 7 gold, run 065d6a70 completed (evidence/01)
- [x] **Data quality**: 45 silver expectations, 45 passed, 0 failed, from the pipeline event log (evidence/03)
- [x] **Unity Catalog**: governed schema, volumes, comments, lineage, app service-principal grants (evidence/02)
- [x] **Lakebase**: 4 gold operational tables synced; the app's inventory panel reads Lakebase (evidence/04, 07)
- [x] **ML / GenAI**: invoice document parsing through the Unity AI Gateway (`kaapi_llm`, 4/4 discrepancies + control matched, 18.4 s); preparation plan with live weather; MLflow evaluation with measured scores (evidence/06, 09, 11)
- [x] **Genie Agent**: Agent mode over 21 tables + SOP PDF volume; config as code in `resources/genie_space.json`
- [x] **Databricks App**: store manager console deployed and ACTIVE (evidence/07)
- [x] Same keys flow through every layer: PO-00006 traced raw → app (evidence/08)
- [x] Migrated off the deprecated Knowledge Assistant + Supervisor Agent to a single Genie Agent
- [x] **Unity AI Gateway**: every AI call except Genie is governed. Model services `kaapi_llm` and
      `kaapi_embed` and MCP service `kaapi_ops_advisor`, with `EXECUTE` grants, service-wide rate
      limits (a real 429 captured), payload logs from both app identities, the `ai-gateway` scope on
      both apps, and no ungoverned fallback (evidence/11)
- [x] MCP operations advisor now called (through the gateway), fixing the "prepare for today"
      answer (same-weekday baseline, live weather)
- [x] App resources cleaned: retired KA/MAS endpoints and unused model endpoints removed
- [x] **Store Live Dashboard** on Lakebase (all 4 `lb_*` tables read), 10 s refresh, and invoice
      approvals written through to Lakebase with an activity feed; before/after test (evidence/12)

## Beyond the bar (built 2026-10-23, proven in executed notebooks)

- [x] **Executed proof notebooks with outputs committed** (`notebooks/01`–`07`): pipeline + 45/45
      expectations, row-level security, Genie with SQL, app workflows, forecast model, briefs and
      gateway logs, evaluation history
- [x] **ML demand forecaster**: UC model `demand_forecaster@champion`, 9.3% lower MAE than the
      same-weekday baseline on a 14-day holdout, champion-gated, scored daily, used by the prep plan
- [x] **Morning action plan per store**: gold SQL facts → `kaapi_llm` via the gateway → deterministic
      number check with one automatic rewrite; 882/884 numbers verified; MLflow trace per brief
- [x] **Row-level security**: UC row filter on 10 store-keyed tables; a store manager SP sees 1 store
      in SQL and in Genie, HQ sees all
- [x] **Scheduled evaluation**: daily job runs `mlflow.genai.evaluate` against the deployed app as
      SP `kaapi-eval-runner` and appends to `eval_history` (0.90, 1.00, 1.00 on Oct 23)
- [x] **Daily ops job from code** (`resources/kaapi_daily_ops.job.yml`): pipeline → train → score →
      briefs → Lakebase sync → evaluate, 05:30 IST; removes the manual sync-order risk
- [x] Legacy code removed from the tree (old agents, KA/MAS notebooks, hard-coded responses)

## Evidence (text, committed)

- [x] 01 Lakeflow run · 02 UC + lineage · 03 data quality · 04 Lakebase · 05 Genie Q&A
- [x] 06 invoice parse output · 07 app and API tests · 08 end-to-end trace
- [x] 09 MLflow evaluation: baseline and re-test run IDs, per-question traces, failure analysis
- [x] 10 value model with every assumption labeled
- [x] 11 Unity AI Gateway: services, grants, gateway invoice / preparation plan / cache captures, payload-log rows, 429
- [x] 13 plain-text extraction of executed notebook outputs 01–07 for text-only evaluation
- [x] Evaluation source: `src/jobs/evaluate_app.py` (daily job and notebook 07) and
      `scripts/run_genie_evaluation.py`; September history committed as text in evidence/09. The
      retired KA/MAS evaluation notebooks were removed from the tree.

## Customer story

- [x] Deck leads with the outcome and follows the required 10-section outline
- [x] One payback formula and one ROI formula, used everywhere (3.9 months; 2.6× over 3 years)
- [x] Value figures labeled as projections from assumptions, not measured outcomes
- [x] Demo script (`DEMO.md`) matches the deployed Genie Agent flow
- [x] Roleplay prep with answers for both personas (`ROLEPLAY_PREP.md`)

## Remaining before submitting

- [x] **AI correctness at target.** History 0.00 → 0.50 → 0.70 (September) → 0.90, 1.00, 1.00 on
      2026-10-23, tracked in `eval_history` (notebook 07). Next: a 30+ question set from real traces
      with a must-have/nice-to-have rubric, since 10 questions move in steps of 0.10.
- [x] **Verify public access.** Checked 2026-09-28 with an unauthenticated request: repo page
      HTTP 200, raw README HTTP 200, GitHub API `visibility: public`.
- [x] **Scrub before public submission.** Workspace/app/Lakebase hosts, owner email, personal
      workspace paths and service-principal IDs replaced with placeholders in evidence, docs and
      bundle configs (2026-09-28). Kept on purpose, as provenance: pipeline/update IDs, MLflow
      run and trace IDs, Genie space ID, catalog name. Older git history still contains the
      unscrubbed values.
- [ ] **Rehearse the roleplay.** 12–15 minute demo, tell-show-tell per scene, both personas,
      with the prepared answers in `ROLEPLAY_PREP.md`. The roleplay is scored separately.
- [ ] **Attach gateway policies** (UI-only): built-in jailbreak / unsafe-content on `kaapi_llm`;
      optionally a `kaapi_guard` strict lane for question-level policies.
- [ ] **Cost-per-store query** on the gateway usage system tables.
- [ ] *(Optional)* Rewrite git history to drop internal identifiers from older commits (no
      credentials were ever committed); needs a force-push.
- [ ] Rotate the service-principal secret that was found in cleartext in the original project;
      delete the connector SP's older secret (2026-07-07) if unused. The MCP connection's own secret
      was replaced 2026-09-29 (90-day lifetime).

## Production follow-ups (not required for the FE Bar; say them in the roleplay)

- Schedule the Lakebase sync as a job task after each pipeline run, or use Lakebase synced tables.
- Narrow the app service principal's `MODIFY` grant to the two app-write tables.
- Replace the value-model assumptions with a timed 5-store pilot baseline.
