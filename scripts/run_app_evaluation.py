"""Evaluate the DEPLOYED Kaapi Bricks app end to end (what a store manager actually sees).

Same 10 questions (scripts/eval_dataset.json, extracted verbatim from run_genie_evaluation.py)
and the same scorers as the Genie-only runs, but predict() calls the app's /api/chat:
Genie Agent mode + governed menu-price lookup. skip_cache=True so every answer is fresh.

Run locally:  DATABRICKS_CONFIG_PROFILE=DEFAULT python scripts/run_app_evaluation.py --app-url <url>
"""
import argparse
import json
import os

import mlflow
import requests
from databricks.sdk import WorkspaceClient
from mlflow.genai.scorers import Correctness, RelevanceToQuery, Safety

EXPERIMENT_ID = "982411422225142"
STORE = "Koramangala, Bangalore"

parser = argparse.ArgumentParser()
parser.add_argument("--app-url", required=True)
parser.add_argument("--profile", default=os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))
args = parser.parse_args()

w = WorkspaceClient(profile=args.profile)
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment_id=EXPERIMENT_ID)


@mlflow.trace
def predict(query: str) -> str:
    headers = w.config.authenticate()  # refreshed per call
    headers["Content-Type"] = "application/json"
    resp = requests.post(f"{args.app_url.rstrip('/')}/api/chat", headers=headers, stream=True, timeout=600,
                         json={"query": query, "store_location": STORE, "history": [], "skip_cache": True})
    resp.raise_for_status()
    resp.encoding = "utf-8"
    final = {}
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            final = json.loads(line[5:].strip())
    mlflow.update_current_trace(tags={"app_trace_id": str(final.get("trace_id")),
                                      "from_cache": str(final.get("from_cache"))})
    return final.get("full_text") or "No response from app."


eval_dataset = json.load(open(os.path.join(os.path.dirname(__file__), "eval_dataset.json")))
with mlflow.start_run(run_name="app-e2e-eval"):
    results = mlflow.genai.evaluate(data=eval_dataset, predict_fn=predict,
                                    scorers=[Safety(), RelevanceToQuery(), Correctness()])
    print("\n=== EVALUATION SUMMARY ===")
    print("run_id:", mlflow.active_run().info.run_id)
    for k, v in sorted(results.metrics.items()):
        print(f"  {k}: {v:.3f}")
