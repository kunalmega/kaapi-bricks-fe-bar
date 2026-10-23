"""Shared helpers for the Kaapi Bricks daily operations job (src/jobs/*.py).

Same code runs locally (DATABRICKS_CONFIG_PROFILE=DEFAULT) and as serverless job tasks
(workspace identity). SQL goes through the Statement Execution API, Lakebase through
psycopg with a short-lived OAuth credential, AI through Unity AI Gateway.
"""
import os
import time
import uuid

import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout, StatementState

CATALOG = os.environ.get("KAAPI_CATALOG", "fevm_cme_conde_catalog")
SCHEMA = os.environ.get("KAAPI_SCHEMA", "kaapi_bricks")
FQ = f"{CATALOG}.{SCHEMA}"
WAREHOUSE_ID = os.environ.get("KAAPI_WAREHOUSE_ID", "e755eae9d758fdf7")
LAKEBASE_INSTANCE = os.environ.get("KAAPI_LAKEBASE_INSTANCE", "kaapi-bricks")
LAKEBASE_DB = os.environ.get("KAAPI_LAKEBASE_DB", "databricks_postgres")
GW_LLM_MODEL = os.environ.get("GW_LLM_MODEL", f"{FQ}.kaapi_llm")

_w = None


def ws() -> WorkspaceClient:
    global _w
    if _w is None:
        profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
        _w = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
    return _w


def sql(statement: str, params: list | None = None) -> list[dict]:
    """Run SQL on the warehouse and return every row (all result chunks) as dicts."""
    w = ws()
    resp = w.statement_execution.execute_statement(
        statement=statement, warehouse_id=WAREHOUSE_ID, catalog=CATALOG, schema=SCHEMA,
        parameters=params, wait_timeout="50s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE)
    while resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"SQL {resp.status.state}: {resp.status.error}\n{statement[:300]}")
    if not resp.manifest or not resp.manifest.schema:
        return []
    cols = [c.name for c in resp.manifest.schema.columns]
    rows = list(resp.result.data_array or []) if resp.result else []
    for n in range(1, resp.manifest.total_chunk_count or 1):
        chunk = w.statement_execution.get_statement_result_chunk_n(resp.statement_id, n)
        rows.extend(chunk.data_array or [])
    return [dict(zip(cols, r)) for r in rows]


def lakebase():
    """Autocommit psycopg connection to Lakebase as the current identity."""
    import psycopg
    w = ws()
    cred = w.database.generate_database_credential(instance_names=[LAKEBASE_INSTANCE],
                                                   request_id=str(uuid.uuid4()))
    inst = w.database.get_database_instance(LAKEBASE_INSTANCE)
    return psycopg.connect(host=inst.read_write_dns, port=5432, dbname=LAKEBASE_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True)


def gateway_chat(messages: list[dict], max_tokens: int = 900, temperature: float = 0.2) -> dict:
    """One chat completion through the Unity AI Gateway model service (kaapi_llm)."""
    w = ws()
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    resp = requests.post(f"{w.config.host.rstrip('/')}/ai-gateway/mlflow/v1/chat/completions",
                         headers=headers, timeout=180,
                         json={"model": GW_LLM_MODEL, "messages": messages,
                               "max_tokens": max_tokens, "temperature": temperature})
    resp.raise_for_status()
    return resp.json()


def sql_literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def insert_rows(table: str, columns: list[str], rows: list[tuple], batch: int = 500) -> int:
    """INSERT rows into a Delta table in batches (small result sets only)."""
    for i in range(0, len(rows), batch):
        values = ",\n".join("(" + ", ".join(sql_literal(v) for v in r) + ")" for r in rows[i:i + batch])
        sql(f"INSERT INTO {FQ}.{table} ({', '.join(columns)}) VALUES\n{values}")
    return len(rows)
