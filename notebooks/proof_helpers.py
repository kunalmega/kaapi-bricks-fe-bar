"""Helpers shared by the executed proof notebooks in this folder.

The notebooks run against the live workspace with your CLI profile
(DATABRICKS_CONFIG_PROFILE, default DEFAULT) and are committed WITH their outputs, so
anyone reading the repo sees what actually ran. Workspace URLs and emails are masked in
printed output.
"""
import base64
import json
import os
import re
import sys
import time

import pandas as pd
import requests
from databricks.sdk import WorkspaceClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath("__file__")), "..", "src", "jobs"))
os.environ.setdefault("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from common import CATALOG, FQ, SCHEMA, WAREHOUSE_ID, sql  # noqa: E402,F401

GENIE_SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"
APP_NAME = "kaapi-bricks-finale"
pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 80)

hq = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"])


def pin_mlflow_credentials():
    """MLflow resolves credentials on its own; pin a short-lived token so a busy OS keyring
    can't drop trace/assessment logging during a long evaluation."""
    token = hq.config.authenticate()["Authorization"].split(" ", 1)[1]
    os.environ.pop("DATABRICKS_CONFIG_PROFILE", None)
    os.environ.update({"DATABRICKS_HOST": hq.config.host, "DATABRICKS_TOKEN": token})


def mask(text: str) -> str:
    text = re.sub(r"https://[\w.-]+\.(?:cloud\.)?databricks(?:apps)?\.com", "https://<workspace>", str(text))
    return re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<user>", text)


def df(statement: str) -> pd.DataFrame:
    return pd.DataFrame(sql(statement))


def store_manager_client() -> WorkspaceClient:
    """The STR-001 (Koramangala) store manager: a service principal mapped to one store."""
    get = lambda k: base64.b64decode(hq.secrets.get_secret("kaapi", k).value).decode()
    return WorkspaceClient(host=hq.config.host, client_id=get("store_mgr_client_id"),
                           client_secret=get("store_mgr_client_secret"), auth_type="oauth-m2m")


def sql_as(client: WorkspaceClient, statement: str) -> pd.DataFrame:
    r = client.statement_execution.execute_statement(statement=statement, warehouse_id=WAREHOUSE_ID,
                                                     wait_timeout="50s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = client.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error)
    cols = [c.name for c in r.manifest.schema.columns]
    return pd.DataFrame(r.result.data_array or [], columns=cols)


def genie_ask(question: str, client: WorkspaceClient | None = None) -> dict:
    """Ask the Genie Agent (Agent mode API, same call the app makes). Returns answer, SQL, seconds."""
    client = client or hq
    headers = client.config.authenticate()
    headers.update({"Content-Type": "application/json", "Accept": "text/event-stream"})
    t = time.time()
    resp = requests.post(f"{client.config.host.rstrip('/')}/api/2.0/genie/agents/{GENIE_SPACE_ID}/responses",
                         headers=headers, stream=True, timeout=300,
                         json={"input": [{"type": "message", "role": "user",
                                          "content": [{"type": "input_text", "text": question}]}]})
    resp.raise_for_status()
    resp.encoding = "utf-8"
    final = {}
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            try:
                ev = json.loads(line[5:].strip())
            except ValueError:
                continue
            if ev.get("type") in ("response.completed", "response.failed"):
                final = ev.get("response", {})
    answer, sqls, tools = [], [], []
    for item in final.get("output", []):
        if item.get("type") == "message":
            answer += [b["text"] for b in item.get("content", []) if b.get("type") == "output_text"]
        elif item.get("type") == "function_call":
            tools.append(item.get("name"))
            try:
                args = json.loads(item.get("arguments") or "{}")
            except ValueError:
                args = {}
            if args.get("sql"):
                sqls.append(args["sql"])
    text = re.sub(r"\s*:citation\[[^\]]*\]", "", "\n\n".join(answer))
    text = mask(re.sub(r"\s*\\?\[\[\d+\]\([^)]*\)\\?\]", "", text)).strip()  # drop Genie chat links
    return {"status": final.get("status"), "seconds": round(time.time() - t, 1), "answer": text,
            "sql": sqls, "tools": tools,
            "cited_documents": sorted(set(re.findall(r"volume_file\.[\w-]+", json.dumps(final))))}


def app_call(method: str, path: str, **kw) -> requests.Response:
    url = hq.apps.get(APP_NAME).url.rstrip("/")
    headers = hq.config.authenticate()
    return requests.request(method, f"{url}{path}", headers=headers, timeout=600, **kw)


def app_chat(query: str, store: str = "Koramangala, Bangalore") -> dict:
    t = time.time()
    r = app_call("POST", "/api/chat", stream=True,
                 json={"query": query, "store_location": store, "history": [], "skip_cache": True})
    r.raise_for_status()
    r.encoding = "utf-8"
    final = {}
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            final = json.loads(line[5:].strip())
    final["seconds"] = round(time.time() - t, 1)
    return final
