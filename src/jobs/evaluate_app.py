"""Scheduled end-to-end evaluation of the deployed app, tracked over time.

Same 10 store-manager questions and scorers as scripts/run_app_evaluation.py. Each run
logs an MLflow evaluation run and appends one row to the Delta table eval_history, so
Correctness / Relevance / Safety are a time series, not a one-off capture.

As a job task it calls the app as the service principal kaapi-eval-runner (OAuth M2M,
credentials in secret scope `kaapi`); locally it uses your CLI profile.
Run: python src/jobs/evaluate_app.py [--source manual]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Job tasks exec the file without __file__; the code object still knows its path.
HERE = os.path.dirname(os.path.abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, HERE)

import mlflow
import requests
from databricks.sdk import WorkspaceClient
from mlflow.genai.scorers import Correctness, RelevanceToQuery, Safety

from common import FQ, insert_rows, sql, ws

EXPERIMENT_ID = os.environ.get("KAAPI_EVAL_EXPERIMENT_ID", "982411422225142")
APP_NAME = os.environ.get("KAAPI_APP_NAME", "kaapi-bricks-finale")
STORE = "Koramangala, Bangalore"
DATASET = os.path.join(HERE, "..", "..", "scripts", "eval_dataset.json")


def app_caller() -> WorkspaceClient:
    """Identity used to call the app: SP via M2M OAuth in a job, the CLI profile locally."""
    try:
        from databricks.sdk.runtime import dbutils
        cid = dbutils.secrets.get("kaapi", "eval_client_id")
        secret = dbutils.secrets.get("kaapi", "eval_client_secret")
        return WorkspaceClient(host=ws().config.host, client_id=cid, client_secret=secret,
                               auth_type="oauth-m2m")
    except Exception:
        return ws()


def main(source: str):
    caller = app_caller()
    app_url = ws().apps.get(APP_NAME).url.rstrip("/")
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_id=EXPERIMENT_ID)

    @mlflow.trace
    def predict(query: str) -> str:
        headers = caller.config.authenticate()
        headers["Content-Type"] = "application/json"
        resp = requests.post(f"{app_url}/api/chat", headers=headers, stream=True, timeout=600,
                             json={"query": query, "store_location": STORE, "history": [], "skip_cache": True})
        resp.raise_for_status()
        resp.encoding = "utf-8"
        final = {}
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                final = json.loads(line[5:].strip())
        return final.get("full_text") or "No response from app."

    data = json.load(open(DATASET))
    with mlflow.start_run(run_name=f"app-e2e-eval-{source}") as run:
        res = mlflow.genai.evaluate(data=data, predict_fn=predict,
                                    scorers=[Safety(), RelevanceToQuery(), Correctness()])
    m = res.metrics
    row = (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), run.info.run_id, source, len(data),
           m.get("correctness/mean"), m.get("relevance_to_query/mean"), m.get("safety/mean"))
    sql(f"""CREATE TABLE IF NOT EXISTS {FQ}.eval_history (
              evaluated_at TIMESTAMP, mlflow_run_id STRING, source STRING, n_questions INT,
              correctness DOUBLE, relevance DOUBLE, safety DOUBLE)
            COMMENT 'One row per scheduled/manual end-to-end evaluation of the deployed app.'""")
    insert_rows("eval_history", ["evaluated_at", "mlflow_run_id", "source", "n_questions",
                                 "correctness", "relevance", "safety"], [row])
    print(f"run_id {run.info.run_id}")
    for k in sorted(m):
        print(f"  {k}: {m[k]:.3f}")
    return run.info.run_id, m, res


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="scheduled")
    a, _ = p.parse_known_args()
    main(a.source)
