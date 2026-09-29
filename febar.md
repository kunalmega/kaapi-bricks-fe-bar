# FE Bar — Kaapi Bricks Submission Checklist

The repository root is the submission. It is a cleaned copy of the earlier Aidays project:
unrelated sibling apps, git history, virtual environments, Terraform state, and a cleartext
credential file were left out.

**Working title:** Kaapi Bricks Intelligent Store Operations
**Industry:** multi-location food service and specialty retail
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

## Evidence (text, committed)

- [x] 01 Lakeflow run · 02 UC + lineage · 03 data quality · 04 Lakebase · 05 Genie Q&A
- [x] 06 invoice parse output · 07 app and API tests · 08 end-to-end trace
- [x] 09 MLflow evaluation: baseline and re-test run IDs, per-question traces, failure analysis
- [x] 10 value model with every assumption labeled
- [x] 11 Unity AI Gateway: services, grants, gateway invoice / preparation plan / cache captures, payload-log rows, 429
- [x] Evaluation source: `scripts/run_genie_evaluation.py`, run as a serverless job; results are
      committed as text in evidence/09. The older KA/MAS notebooks
      (`scripts/run_ka_evaluation*.ipynb`, `scripts/run_mas_evaluation*.ipynb`) call retired
      endpoints and are superseded, so they were not re-run.

## Customer story

- [x] Deck leads with the outcome and follows the required 10-section outline
- [x] One payback formula and one ROI formula, used everywhere (3.9 months; 2.6× over 3 years)
- [x] Value figures labeled as projections from assumptions, not measured outcomes
- [x] Demo script (`DEMO.md`) matches the deployed Genie Agent flow
- [x] Roleplay prep with answers for both personas (`ROLEPLAY_PREP.md`)

## Remaining before submitting

- [ ] **Improve AI correctness.** Genie-direct Correctness 0.50 (runs 2–3). With the governed
      menu-price lookup, measured end to end through the deployed app: **0.70** (run 5, 10/10 scored;
      run 4 void). Below the 0.80 target. Next: supplier terms from a table, a must-have/nice-to-have
      rubric, and a 30+ question set (see evidence/09). Keep the measured
      history visible; do not present unscored metrics as passes.
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
