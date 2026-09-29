"""Kaapi Bricks — FastAPI backend with SSE streaming, Lakebase short-term memory,
and embedding-based semantic caching.

Serves a React frontend (static/index.html) and provides API endpoints for
chat (with SSE streaming), conversations, feedback, and store data.
"""

import os
import re
import time
import uuid
import json
import math
import threading
import concurrent.futures
from datetime import datetime, timedelta
import requests as http_requests

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import mlflow
from mlflow.entities import SpanType
from databricks.sdk import WorkspaceClient
import psycopg

# =============================================================================
# CONFIGURATION
# =============================================================================
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "01f12a63ec1011e0acbb09158eda7634")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")
LAKEBASE_INSTANCE_NAME = os.environ.get("LAKEBASE_INSTANCE_NAME", "kaapi-bricks")
LAKEBASE_DATABASE_NAME = os.environ.get("LAKEBASE_DATABASE_NAME", "databricks_postgres")
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "e755eae9d758fdf7")
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.95"))
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "48"))

# Unity AI Gateway: every AI call except Genie goes through governed Unity Catalog
# services (EXECUTE-granted, rate-limited, payload-logged). There is deliberately no
# fallback to direct serving endpoints — a gateway failure must surface, not bypass governance.
GW_SCHEMA = os.environ.get("GW_SCHEMA", "fevm_cme_conde_catalog.kaapi_bricks")
GW_LLM_MODEL = os.environ.get("GW_LLM_MODEL", f"{GW_SCHEMA}.kaapi_llm")        # Claude Sonnet 4.6 (+ Haiku fallback)
GW_EMBED_MODEL = os.environ.get("GW_EMBED_MODEL", f"{GW_SCHEMA}.kaapi_embed")  # BGE-large-en, same as cached vectors
GW_MCP_SERVICE = os.environ.get("GW_MCP_SERVICE", f"{GW_SCHEMA}.kaapi_ops_advisor")

# =============================================================================
# MLFLOW TRACING
# =============================================================================
try:
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_id="3268449285627906")
except Exception:
    pass

# =============================================================================
# LAKEBASE (PostgreSQL) — robust connection management
# =============================================================================
_token_lock = threading.Lock()
_cached_token = None
_token_expiry = 0
TOKEN_REFRESH_MARGIN = 50 * 60

_db_lock = threading.Lock()
_db_conn = None

# Cache workspace client info to avoid repeated API calls
_ws_info_lock = threading.Lock()
_ws_host = None
_ws_user = None
_lb_host = None


def _get_workspace_client():
    return WorkspaceClient()


def _get_ws_info():
    """Cache workspace host, user email, and Lakebase host."""
    global _ws_host, _ws_user, _lb_host
    with _ws_info_lock:
        if _ws_host is None:
            w = _get_workspace_client()
            _ws_host = w.config.host.rstrip("/")
            _ws_user = w.current_user.me().user_name
            instance = w.database.get_database_instance(LAKEBASE_INSTANCE_NAME)
            _lb_host = instance.read_write_dns
    return _ws_host, _ws_user, _lb_host


def get_lakebase_token() -> str:
    global _cached_token, _token_expiry
    with _token_lock:
        if _cached_token is None or time.time() >= _token_expiry:
            w = _get_workspace_client()
            cred = w.database.generate_database_credential(
                instance_names=[LAKEBASE_INSTANCE_NAME],
                request_id=str(uuid.uuid4()),
            )
            _cached_token = cred.token
            _token_expiry = time.time() + TOKEN_REFRESH_MARGIN
        return _cached_token


def get_db_connection():
    _, user, lb_host = _get_ws_info()
    token = get_lakebase_token()
    conn = psycopg.connect(
        host=lb_host, port=5432, dbname=LAKEBASE_DATABASE_NAME,
        user=user, password=token, sslmode="require", autocommit=True,
    )
    return conn


def get_conn():
    """Get a healthy DB connection with automatic reconnection."""
    global _db_conn
    with _db_lock:
        if _db_conn is None:
            _db_conn = get_db_connection()
        # Health check
        try:
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
        except Exception:
            # Connection stale — force token refresh and reconnect
            global _cached_token, _token_expiry
            _cached_token = None
            _token_expiry = 0
            try:
                _db_conn.close()
            except Exception:
                pass
            _db_conn = get_db_connection()
            return _db_conn


def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS kaapi_mcp")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.conversations (
            id TEXT PRIMARY KEY, title TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.messages (
            id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES kaapi_mcp.conversations(id) ON DELETE CASCADE,
            role TEXT, content TEXT, trace_id TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON kaapi_mcp.messages(conversation_id, created_at)")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.feedback (
            id TEXT PRIMARY KEY, message_id TEXT, conversation_id TEXT, trace_id TEXT,
            value TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        # Short-term memory cache table
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.qa_cache (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            embedding JSONB,
            store_location TEXT,
            latency_ms DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_qa_cache_time ON kaapi_mcp.qa_cache(created_at)")
        # Compare cache table
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.compare_cache (
            id TEXT PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL,
            model_endpoint TEXT NOT NULL, store_location TEXT, latency_ms DOUBLE PRECISION,
            input_tokens INT DEFAULT 0, output_tokens INT DEFAULT 0,
            weather_data JSONB, calendar_data JSONB, created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_compare_cache ON kaapi_mcp.compare_cache(question, model_endpoint, store_location)")
        # Admin config table
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_mcp.admin_config (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("""INSERT INTO kaapi_mcp.admin_config (key, value) VALUES
            ('operations_model', 'databricks-meta-llama-3-3-70b-instruct')
            ON CONFLICT (key) DO NOTHING""")
        # Cleanup stale cache
        cur.execute(f"DELETE FROM kaapi_mcp.qa_cache WHERE created_at < NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
        cur.execute(f"DELETE FROM kaapi_mcp.compare_cache WHERE created_at < NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
        return True
    except Exception as e:
        print(f"DB init error: {e}")
        return False


# =============================================================================
# DB HELPERS
# =============================================================================
def save_conversation(conv_id, title):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_mcp.conversations (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (conv_id, title))
    except Exception as e:
        print(f"[Lakebase] save_conversation error: {e}")


def save_message(conv_id, role, content, trace_id=None):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_mcp.messages (id, conversation_id, role, content, trace_id) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), conv_id, role, content, trace_id))
    except Exception as e:
        print(f"[Lakebase] save_message error: {e}")



def load_conversations():
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT id, title, created_at FROM kaapi_mcp.conversations ORDER BY created_at DESC LIMIT 20")
        return [{"id": r[0], "title": r[1], "created_at": str(r[2])} for r in cur.fetchall()]
    except Exception:
        return []


def load_messages(conv_id):
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT role, content FROM kaapi_mcp.messages WHERE conversation_id = %s ORDER BY created_at", (conv_id,))
        return [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
    except Exception:
        return []


def delete_all_conversations():
    try:
        cur = get_conn().cursor()
        cur.execute("DELETE FROM kaapi_mcp.messages")
        cur.execute("DELETE FROM kaapi_mcp.conversations")
    except Exception:
        pass


def save_feedback(msg_id, conv_id, trace_id, value):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_mcp.feedback (id, message_id, conversation_id, trace_id, value) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), msg_id, conv_id, trace_id, value))
    except Exception as e:
        print(f"[Lakebase] save_feedback error: {e}")


# =============================================================================
# EMBEDDING & SEMANTIC CACHE
# =============================================================================
def _gateway_post(path, payload, timeout=180, accept=None):
    """POST to the Unity AI Gateway as the app service principal. Raises on any error."""
    w = _get_workspace_client()
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    if accept:
        headers["Accept"] = accept
    resp = http_requests.post(f"{w.config.host.rstrip('/')}/ai-gateway/{path}",
                              headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Unity AI Gateway {resp.status_code} on {path}: {resp.text[:400]}")
    return resp


def _message_text(content):
    """Chat-completion content may be a string or a list of typed blocks."""
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict)).strip()
    return (content or "").strip()


@mlflow.trace(name="gateway_llm", span_type=SpanType.CHAT_MODEL)
def gateway_chat(messages, max_tokens=1000):
    """Chat completion through the governed kaapi_llm model service."""
    resp = _gateway_post("mlflow/v1/chat/completions",
                         {"model": GW_LLM_MODEL, "messages": messages, "max_tokens": max_tokens})
    return _message_text(resp.json()["choices"][0]["message"].get("content"))


@mlflow.trace(name="get_embedding", span_type=SpanType.EMBEDDING)
def get_embedding(text: str) -> list:
    """Embedding through the governed kaapi_embed model service (BGE-large-en)."""
    resp = _gateway_post("mlflow/v1/embeddings",
                         {"model": GW_EMBED_MODEL, "input": [text[:8000]]},  # BGE max input ~8K chars
                         timeout=30)
    return resp.json()["data"][0]["embedding"]


def cosine_similarity(a, b):
    """Compute cosine similarity using pure math (no numpy dependency)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@mlflow.trace(name="cache_lookup", span_type=SpanType.RETRIEVER)
def find_cached_answer(question: str, store: str = "") -> dict | None:
    """Check Lakebase for a cached answer matching question + store."""
    try:
        cur = get_conn().cursor()
        # Layer 1: Exact match on question + store
        cur.execute(
            f"""SELECT answer, latency_ms FROM kaapi_mcp.qa_cache
                WHERE LOWER(TRIM(question)) = LOWER(TRIM(%s))
                  AND LOWER(TRIM(store_location)) = LOWER(TRIM(%s))
                  AND created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'
                ORDER BY created_at DESC LIMIT 1""",
            (question, store))
        row = cur.fetchone()
        if row:
            return {"answer": row[0], "from_cache": True, "match": "exact",
                    "original_latency_ms": row[1] or 0}

        # Layer 2: Embedding similarity (also filtered by store)
        q_embedding = get_embedding(question)

        cur.execute(
            f"""SELECT question, answer, embedding, latency_ms FROM kaapi_mcp.qa_cache
                WHERE created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'
                  AND embedding IS NOT NULL
                  AND LOWER(TRIM(store_location)) = LOWER(TRIM(%s))""",
            (store,))
        candidates = cur.fetchall()

        best_score, best_answer, best_q, best_lat = 0.0, None, None, 0
        for cached_q, cached_a, cached_emb, cached_lat in candidates:
            emb = json.loads(cached_emb) if isinstance(cached_emb, str) else cached_emb
            score = cosine_similarity(q_embedding, emb)
            if score > best_score:
                best_score = score
                best_answer = cached_a
                best_q = cached_q
                best_lat = cached_lat or 0

        if best_score >= SIMILARITY_THRESHOLD:
            return {
                "answer": best_answer,
                "from_cache": True,
                "match": "semantic",
                "similarity": round(best_score, 3),
                "matched_question": best_q,
                "original_latency_ms": best_lat,
            }
    except Exception as e:
        print(f"Cache lookup error: {e}")
    return None


@mlflow.trace(name="save_to_cache", span_type=SpanType.TOOL)
def save_to_cache(question, answer, embedding, store, latency_ms):
    """Save Q&A pair + embedding to Lakebase for short-term memory."""
    try:
        get_conn().cursor().execute(
            """INSERT INTO kaapi_mcp.qa_cache (id, question, answer, embedding, store_location, latency_ms)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), question, answer,
             json.dumps(embedding) if embedding else None,
             store, latency_ms))
    except Exception as e:
        print(f"Cache save error: {e}")


# =============================================================================
# GENIE AGENT — conversation API (replaces MAS + KA)
# =============================================================================
def clean_response(text):
    """Clean MAS response: extract only the final HQ supervisor summary."""
    hq_parts = re.split(r'(?:Kaapi-Bricks-HQ|KaapiBricks-HQ)\s*\n+', text)
    if len(hq_parts) > 1:
        text = hq_parts[-1].strip()

    text = re.sub(r"</?name>", "", text)
    text = re.sub(r"</?content>", "", text)
    text = re.sub(r"</?turn_\w+>", "", text)
    text = re.sub(r'^Kaapi-Bricks-[\w-]+\s*\n', '', text, flags=re.MULTILINE)

    # Strip Databricks source citation URLs
    text = re.sub(r'\]\(https?://[^)]*cloud\.databricks\.com/ajax-api[^)]*\)', '', text)
    text = re.sub(r'\]\(https?://[^)]*databricks[^)]*\)', '', text)
    text = re.sub(r'^\[\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]*)\]\(https?://[^)]*databricks[^)]*\)', r'\1', text)

    # Strip RAG source citations
    text = re.sub(r'\n?: [A-Z].*?\.pdf\b', '', text, flags=re.DOTALL)
    text = re.sub(r'\s*\w+\.pdf\b', '', text)

    # Strip footnote citations
    text = re.sub(r'\^BGAP-\d+', '', text)
    text = re.sub(r'\n\^BGAP-\d+:.*?(?=\n\^BGAP-|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'\[\^[^\]]+\]', '', text)
    text = re.sub(r'\n\[\^[^\]]+\]:.*?(?=\n\[\^|\n\n|\Z)', '', text, flags=re.DOTALL)

    # Strip preamble
    text = re.sub(r"^I'll (?:search|look|check|query|consult|get).*?(?:knowledge base|operations|documents|database|instructions).*?\.\s*\n*", '', text, flags=re.IGNORECASE)
    text = re.sub(r',You:.*$', '', text)
    text = re.sub(r'^\s*[\[\]]\s*$', '', text, flags=re.MULTILINE)

    # Strip trailing footnote numbers (e.g. " 12" or " 1 2" at end of paragraphs)
    text = re.sub(r'\s+\d+\s*\d*\s*$', '', text, flags=re.MULTILINE)

    # Strip "This is noted as..." filler sentences
    text = re.sub(r'This is noted as.*?(?:\.|$)', '', text, flags=re.MULTILINE)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# Map dropdown value → exact store name in Delta table
STORE_DB_NAMES = {
    "Koramangala, Bangalore": "Kaapi Bricks Koramangala",
    "Indiranagar, Bangalore": "Kaapi Bricks Indiranagar",
    "Jayanagar, Bangalore": "Kaapi Bricks Jayanagar",
    "Whitefield, Bangalore": "Kaapi Bricks Whitefield",
    "MG Road, Bangalore": "Kaapi Bricks MG Road",
    "HSR Layout, Bangalore": "Kaapi Bricks HSR Layout",
    "Malleshwaram, Bangalore": "Kaapi Bricks Malleshwaram",
    "Basavanagudi, Bangalore": "Kaapi Bricks Basavanagudi",
    "Electronic City, Bangalore": "Kaapi Bricks Electronic City",
    "JP Nagar, Bangalore": "Kaapi Bricks JP Nagar",
    "T. Nagar, Chennai": "Kaapi Bricks Chennai T. Nagar",
    "Adyar, Chennai": "Kaapi Bricks Chennai Adyar",
    "Mysuru": "Kaapi Bricks Mysuru",
    "Banjara Hills, Hyderabad": "Kaapi Bricks Hyderabad Banjara",
    "Jubilee Hills, Hyderabad": "Kaapi Bricks Hyderabad Jubilee",
    "Coimbatore": "Kaapi Bricks Coimbatore", "Kochi": "Kaapi Bricks Kochi",
    "Madurai": "Kaapi Bricks Madurai", "Pondicherry": "Kaapi Bricks Pondicherry",
    "Vizag": "Kaapi Bricks Vizag", "Bandra, Mumbai": "Kaapi Bricks Mumbai Bandra",
    "Andheri, Mumbai": "Kaapi Bricks Mumbai Andheri",
    "Connaught Place, Delhi": "Kaapi Bricks Delhi CP",
    "Hauz Khas, Delhi": "Kaapi Bricks Delhi Hauz Khas",
    "Pune": "Kaapi Bricks Pune", "Kolkata": "Kaapi Bricks Kolkata",
    "Ahmedabad": "Kaapi Bricks Ahmedabad", "Jaipur": "Kaapi Bricks Jaipur",
    "Chandigarh": "Kaapi Bricks Chandigarh", "Goa": "Kaapi Bricks Goa",
    "Dubai": "Kaapi Bricks Dubai", "Singapore": "Kaapi Bricks Singapore",
    "London": "Kaapi Bricks London", "San Francisco": "Kaapi Bricks San Francisco",
    "Kuala Lumpur": "Kaapi Bricks Kuala Lumpur", "Sydney": "Kaapi Bricks Sydney",
    "Toronto": "Kaapi Bricks Toronto",
}


def _prepare_messages(messages, store_location):
    """Prepend exact store name so Genie filters correctly."""
    db_name = STORE_DB_NAMES.get(store_location, f"Kaapi Bricks {store_location}")
    input_messages = []
    first_user = True
    for msg in messages:
        if msg["role"] == "user" and first_user:
            input_messages.append({
                "role": "user",
                "content": f"{msg['content']} (Filter results for store name = '{db_name}' only. Do not show data for all stores.)",
            })
            first_user = False
        else:
            input_messages.append(msg)
    return input_messages


def _extract_text_from_output(data):
    """Extract ONLY the final assistant message from MAS response.

    MAS returns multiple output items: sub-agent thinking, function calls,
    tool results, and the final HQ supervisor summary. We want only the last
    message's text — that's the clean supervisor answer.
    """
    # Collect all output_text blocks
    all_texts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    text = block.get("text", "").strip()
                    if text:
                        all_texts.append(text)

    if not all_texts:
        return "No response from agent."

    # The LAST text block is always the HQ supervisor's final answer
    return all_texts[-1]


def _extract_token_usage(data):
    """Extract token usage from MAS response."""
    usage = data.get("usage") or {}
    input_tokens = (usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = (usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    return int(input_tokens), int(output_tokens)


@mlflow.trace(name="genie_call", span_type=SpanType.CHAT_MODEL)
def call_genie_sync(messages, store_location):
    """Call the Genie Agent mode API (replaces MAS + KA).

    Agent mode (not the Chat-mode conversation API) is required for Genie to
    read the SOP/recipe PDFs attached to the space as a volume. It streams SSE
    events; the final `response.completed` event carries the full output.
    """
    w = _get_workspace_client()
    host = w.config.host.rstrip("/")
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "text/event-stream"

    user_query = messages[-1]["content"] if messages else ""
    db_name = STORE_DB_NAMES.get(store_location, f"Kaapi Bricks {store_location}")
    content = f"[Store: {db_name}] {user_query}"

    start_time = time.time()
    try:
        resp = http_requests.post(
            f"{host}/api/2.0/genie/agents/{GENIE_SPACE_ID}/responses",
            headers=headers,
            json={"input": [{"type": "message", "role": "user",
                             "content": [{"type": "input_text", "text": content}]}]},
            stream=True, timeout=300,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"

        final = None
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except ValueError:
                continue
            if event.get("type") in ("response.completed", "response.failed"):
                final = event.get("response", {})

        latency_ms = (time.time() - start_time) * 1000

        if not final or final.get("status") != "completed":
            err = (final or {}).get("error") or "no_response"
            return {"text": "Sorry, I couldn't get an answer right now. Please try again.",
                    "latency_ms": latency_ms, "input_tokens": 0, "output_tokens": 0, "error": str(err)}

        answer_parts = []
        for item in final.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text" and block.get("text"):
                        answer_parts.append(block["text"])
        # Agent mode marks document sources inline as :citation[volume_file.<id>]
        answer = re.sub(r"\s*:citation\[[^\]]*\]", "", "\n\n".join(answer_parts)).strip()
        if not answer:
            answer = "I don't have specific data on that. Try asking about sales, inventory, or purchase orders."

        print(f"[Genie] Done in {latency_ms:.0f}ms")
        return {"text": answer, "latency_ms": latency_ms,
                "input_tokens": 0, "output_tokens": 0, "error": None}

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {"text": f"Error: {str(e)}", "latency_ms": latency_ms,
                "input_tokens": 0, "output_tokens": 0, "error": str(e)}



def log_inference(trace_id, conv_id, store, query_text, response, latency_ms,
                  input_tokens=0, output_tokens=0, error=None):
    try:
        w = _get_workspace_client()
        url = f"{w.config.host.rstrip('/')}/api/2.0/sql/statements"
        headers = w.config.authenticate()
        headers["Content-Type"] = "application/json"
        summary = (response[:500] if response else "").replace("'", "''")
        query_escaped = (query_text or "").replace("'", "''")
        sql = f"""INSERT INTO fevm_cme_conde_catalog.kaapi_bricks.inference_logs
        (trace_id, request_id, timestamp, conversation_id, store_location, query, response_summary, latency_ms, agent_name, endpoint_name, input_tokens, output_tokens, error)
        VALUES ('{trace_id or ""}', '{str(uuid.uuid4())}', current_timestamp(), '{conv_id or ""}',
                '{store or ""}', '{query_escaped}', '{summary}', {latency_ms:.1f},
                'Genie', '{GENIE_SPACE_ID}', {input_tokens}, {output_tokens}, '{error or ""}')"""
        http_requests.post(url, headers=headers, json={"warehouse_id": SQL_WAREHOUSE_ID, "statement": sql, "wait_timeout": "10s"})
    except Exception as e:
        print(f"[Inference log] error: {e}")


# =============================================================================
# STORE DATA
# =============================================================================
STORES = [
    "Koramangala, Bangalore", "Indiranagar, Bangalore", "Jayanagar, Bangalore",
    "Whitefield, Bangalore", "MG Road, Bangalore", "HSR Layout, Bangalore",
    "Malleshwaram, Bangalore", "Basavanagudi, Bangalore", "Electronic City, Bangalore",
    "JP Nagar, Bangalore", "T. Nagar, Chennai", "Adyar, Chennai", "Mysuru",
    "Banjara Hills, Hyderabad", "Jubilee Hills, Hyderabad", "Coimbatore", "Kochi",
    "Madurai", "Pondicherry", "Vizag", "Bandra, Mumbai", "Andheri, Mumbai",
    "Connaught Place, Delhi", "Hauz Khas, Delhi", "Pune", "Kolkata", "Ahmedabad",
    "Jaipur", "Chandigarh", "Goa", "Dubai", "Singapore", "London",
    "San Francisco", "Kuala Lumpur", "Sydney", "Toronto",
]

EXAMPLE_PROMPTS = [
    "What's our best-selling drink this month?",
    "How do I make a Classic Filter Coffee?",
    "What are the sales data for yesterday?",
    "How should I prepare for today?",
    "How should I prepare for tomorrow?",
]

# Pre-cached answers for demo — instant response for left-panel example prompts
CACHED_ANSWERS = {
    "What's our best-selling drink this month?": {
        "answer": "## Best-Selling Drinks This Month\n\nBased on our sales data across all 37 stores:\n\n| Rank | Drink | Category | Price | Share |\n|------|-------|----------|-------|-------|\n| 1 | **Classic Filter Coffee** | Filter Coffee | \u20b960 | 14% |\n| 2 | **Strong Decoction** | Filter Coffee | \u20b970 | 10% |\n| 3 | **Masala Chai** | Traditional | \u20b950 | 9% |\n| 4 | **Degree Coffee** | Filter Coffee | \u20b960 | 8% |\n| 5 | **Bella Kaapi (Jaggery)** | Filter Coffee | \u20b965 | 6% |\n\nClassic Filter Coffee continues to dominate with 14% of all orders. Filter Coffee as a category accounts for ~55% of total sales. The Bangalore stores (especially Koramangala and Indiranagar) drive the highest volumes.\n\n**Trending:** Cold Coffee and Kaapi Frappe are gaining popularity in the specialty segment, especially at the MG Road and Whitefield stores.",
        "tokens": 180,
    },
    "How do I make a Classic Filter Coffee?": {
        "answer": "## Classic Filter Coffee (PRD-001) \u2014 \u20b960\n\n### Ingredients\n- **Decoction:** 30ml freshly dripped (house blend: 70% Chikmagalur Robusta + 30% Chicory)\n- **Milk:** 120ml hot full cream milk (Nandini Dairy)\n- **Sweetener:** 10g sugar (adjust per preference)\n\n### Brewing the Decoction\n1. Add 2 heaped tablespoons (20g) of house blend to the brass filter\n2. Pour 150ml boiling water at **92-96\u00b0C**\n3. Allow to drip for **12-15 minutes** (don't rush\u2014weak coffee results)\n\n### Tumbler-Davara Pour Technique \u2615\nThis is the **signature Kaapi Bricks experience:**\n1. Hold the davara (saucer) at waist height, tumbler at shoulder height\n2. Pour in a steady stream, extending distance to **2-3 feet**\n3. Repeat **3-4 pours** to create a rich, frothy top layer\n4. Final pour should leave visible foam on top\n5. Serve immediately in tumbler placed inside davara\n\n**Serve at 65-70\u00b0C** (never exceed 75\u00b0C). Prep time: 2 minutes.\n\n*Recommended add-ons: Extra Decoction Shot, Jaggery Sweetener*",
        "tokens": 210,
    },
    "Which stores are running low on Coorg Arabica beans?": {
        "answer": "## Inventory Alert: Coorg Arabica Beans (ING-001)\n\n**Supplier:** Coorg Coffee Estates (SUP-001)  \n**Lead time:** 7 days | **Reorder threshold:** 10 kg  \n**Price:** \u20b91,200/kg\n\n### Stores Below Reorder Threshold\n\n| Store | Location | Current Stock | Status |\n|-------|----------|---------------|--------|\n| STR-009 | Electronic City, Bangalore | 4.2 kg | \u26a0\ufe0f Critical |\n| STR-018 | Madurai | 6.8 kg | \u26a0\ufe0f Low |\n| STR-020 | Vizag | 7.1 kg | \u26a0\ufe0f Low |\n| STR-030 | Goa | 8.5 kg | Watch |\n\n**Recommendation:** Place purchase orders immediately for Electronic City and Madurai. With a 7-day lead time from Coorg Coffee Estates, these stores could run out within 3-4 days at current consumption rates.\n\nElectronic City (our newest store) has been consuming Arabica beans at a higher rate due to the Grand Opening promotion traffic.",
        "tokens": 165,
    },
    "What promotions are active right now?": {
        "answer": "## Active Promotions\n\n| Promotion | Type | Discount | Scope |\n|-----------|------|----------|-------|\n| **Morning Rush Hour (7-9am)** | Happy Hour | 20% off | All stores |\n| **Free Add-on Friday** | Free Item | Free add-on | All stores |\n| **Student Discount** | Discount | 10% off | All stores |\n| **Birthday Month Special** | Birthday | 25% off | All stores |\n| **Referral Reward** | Referral | 15% off | All stores |\n| **New Member Welcome** | Discount | 20% off | All stores |\n| **Filter Coffee Monday** | Day of Week | 15% off filter coffees | All stores |\n| **Buy 5 Get 1 Free** | Loyalty Punch | Free drink | All stores |\n| **App Launch Promo** | App Exclusive | 25% off | App orders only |\n\n### Recently Ended\n- **Grand Opening - Electronic City**: BOGO 50% (ended after 2 weeks)\n- **Monsoon Kaapi Special**: 15% off (seasonal, ended)\n\n**Top performer:** Morning Rush Hour drives the most redemptions, especially at IT hub stores (Whitefield, Electronic City, HSR Layout).",
        "tokens": 195,
    },
    "How long does Coorg Arabica take to reorder?": {
        "answer": "## Coorg Arabica Beans \u2014 Reorder Details\n\n| Field | Value |\n|-------|-------|\n| **Supplier** | Coorg Coffee Estates (SUP-001) |\n| **Location** | Coorg (Kodagu), Karnataka |\n| **Lead time** | **7 days** |\n| **Reliability score** | 4.8/5.0 |\n| **Minimum order** | 50 kg |\n| **Price** | \u20b91,200/kg (contracted, reviewed annually) |\n| **Reorder threshold** | 10 kg per store |\n| **Typical weekly usage** | 5-8 kg per store |\n| **Payment terms** | Net 30 days |\n| **Delivery** | Weekly shipment to Bangalore central warehouse |\n\n### Reorder Timing\nWith a 7-day lead time and weekly usage of 5-8 kg, you should **place orders when stock hits 10 kg** to maintain buffer. The inventory system generates automatic purchase orders when stock drops below threshold.\n\n**Quality:** Single-origin Arabica, shade-grown, hand-picked. Certificate of origin provided with each shipment.\n\n*For emergency same-day orders, Coorg Coffee Estates requires a minimum 24-hour notice by phone.*",
        "tokens": 175,
    },
}


# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(title="Kaapi Bricks")

# Initialize DB on startup
db_available = init_db()


@app.get("/api/stores")
def get_stores():
    return {"stores": STORES}


@app.get("/api/examples")
def get_examples():
    return {"examples": EXAMPLE_PROMPTS}


@app.get("/api/cached/{prompt_index}")
def get_cached_answer(prompt_index: int):
    """Return pre-cached answer for an example prompt (instant demo)."""
    if 0 <= prompt_index < len(EXAMPLE_PROMPTS):
        prompt = EXAMPLE_PROMPTS[prompt_index]
        cached = CACHED_ANSWERS.get(prompt)
        if cached:
            return {"cached": True, "query": prompt, "answer": cached["answer"], "tokens": cached["tokens"]}
    return {"cached": False}


@app.get("/api/stats")
def get_stats():
    """Return usage stats and Lakebase connection info."""
    stats = {
        "connected": False,
        "instance": LAKEBASE_INSTANCE_NAME,
        "database": LAKEBASE_DATABASE_NAME,
        "engine": "PostgreSQL 16 (Lakebase)",
        "auth": "OAuth token (auto-refresh)",
        "tables": "conversations, messages, feedback, qa_cache",
        "chats": 0,
        "messages": 0,
        "feedback_total": 0,
        "feedback_positive": 0,
        "cache_entries": 0,
        "cache_hits": 0,
    }
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        stats["engine"] = version.split(",")[0] if version else "PostgreSQL (Lakebase)"
        cur.execute("SELECT COUNT(*) FROM kaapi_mcp.conversations")
        stats["chats"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kaapi_mcp.messages")
        stats["messages"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kaapi_mcp.feedback")
        stats["feedback_total"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kaapi_mcp.feedback WHERE value = 'positive'")
        stats["feedback_positive"] = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM kaapi_mcp.qa_cache WHERE created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
        stats["cache_entries"] = cur.fetchone()[0]
        stats["connected"] = True
    except Exception:
        pass
    return stats


@app.get("/api/conversations")
def get_conversations():
    return {"conversations": load_conversations()}


@app.get("/api/conversations/{conv_id}/messages")
def get_messages(conv_id: str):
    return {"messages": load_messages(conv_id)}


@app.post("/api/conversations/{conv_id}/clear")
def clear_conversations(conv_id: str = "all"):
    delete_all_conversations()
    return {"ok": True}


@app.post("/api/feedback")
async def post_feedback(request: Request):
    body = await request.json()
    save_feedback(body.get("message_id", ""), body.get("conversation_id", ""),
                  body.get("trace_id"), body.get("value", ""))
    return {"ok": True}


_PREP_RE = re.compile(
    r"\b(prepare|prep|preparation)\b|\bplan\b.*\b(today|tomorrow|weekend)\b", re.IGNORECASE)


def is_prep_question(query):
    return bool(_PREP_RE.search(query or ""))


def _prep_target_day(query):
    """Target date in store time (IST) and its Spark dayofweek (1 = Sunday … 7 = Saturday)."""
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    q = (query or "").lower()
    target = now + timedelta(days=1) if "tomorrow" in q and "today" not in q else now
    return target, (target.weekday() + 1) % 7 + 1


@mlflow.trace(name="prep_store_data", span_type=SpanType.TOOL)
def build_prep_store_data(query, store_location):
    """Deterministic store facts for a preparation plan.

    Demand comes from the SAME weekday across the full history (gold_product_demand),
    not from the most recent single day. Stock and overdue POs come from Lakebase,
    the operational serving copy.
    """
    target, dow = _prep_target_day(query)
    db_name = STORE_DB_NAMES.get(store_location, f"Kaapi Bricks {store_location}").replace("'", "''")
    rows = _run_sql(f"SELECT store_id FROM {CATALOG_SCHEMA}.stores WHERE name = '{db_name}'")
    if not rows:
        return None, target
    store_id = rows[0]["store_id"]
    day = target.strftime("%A")
    demand = _run_sql(f"""
        SELECT product_name, ROUND(AVG(units), 1) AS avg_units, COUNT(*) AS days
        FROM {CATALOG_SCHEMA}.gold_product_demand
        WHERE store_id = '{store_id}' AND dayofweek(order_date) = {dow}
        GROUP BY product_name ORDER BY avg_units DESC LIMIT 8""")
    volume = _run_sql(f"""
        SELECT ROUND(AVG(orders), 0) AS avg_orders, ROUND(AVG(revenue), 0) AS avg_revenue, COUNT(*) AS days
        FROM {CATALOG_SCHEMA}.gold_store_daily_kpis
        WHERE store_id = '{store_id}' AND dayofweek(order_date) = {dow}""")
    lines = [f"Store: {db_name.replace(chr(39) * 2, chr(39))} ({store_id}). Target day: {day} {target:%Y-%m-%d}.",
             f"Order history covers 2026-02-01 to 2026-05-14; figures are averages over past {day}s."]
    if volume and volume[0].get("avg_orders"):
        v = volume[0]
        lines.append(f"Typical {day}: {v['avg_orders']} orders, Rs.{v['avg_revenue']} revenue (over {v['days']} {day}s).")
    lines.append(f"Average units per drink on a {day}:")
    lines += [f"- {d['product_name']}: {d['avg_units']}" for d in demand]
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT ingredient_name, current_stock, unit, days_cover FROM lb_inventory_position "
                    "WHERE store_id = %s ORDER BY days_cover NULLS LAST LIMIT 4", (store_id,))
        stock = cur.fetchall()
        cur.execute("SELECT po_id, supplier_name, days_overdue, total_amount FROM lb_open_purchase_orders "
                    "WHERE store_id = %s AND is_overdue ORDER BY days_overdue DESC LIMIT 5", (store_id,))
        overdue = cur.fetchall()
        lines.append("Lowest stock cover (Lakebase):")
        lines += [f"- {r[0]}: {r[1]} {r[2]}, {r[3]} days of cover" for r in stock]
        lines.append(f"Overdue purchase orders (Lakebase): {len(overdue)}")
        lines += [f"- {r[0]} {r[1]}: {r[2]} days overdue, Rs.{r[3]}" for r in overdue]
    except Exception as e:
        print(f"[Prep] Lakebase read failed: {e}")
        lines.append("Stock and purchase-order status unavailable right now.")
    return "\n".join(lines), target


@mlflow.trace(name="mcp_ops_advisor", span_type=SpanType.TOOL)
def call_ops_advisor(query, store_location, store_data):
    """operations_advisor tool on the governed MCP service, through the Unity AI Gateway."""
    resp = _gateway_post(
        f"mcp-services/{GW_MCP_SERVICE}",
        {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
         "params": {"name": "operations_advisor",
                    "arguments": {"query": query, "store": store_location, "store_data": store_data}}},
        timeout=240, accept="application/json, text/event-stream")
    body = resp.text
    if "text/event-stream" in resp.headers.get("content-type", ""):
        body = [l[5:].strip() for l in body.splitlines() if l.startswith("data:")][-1]
    msg = json.loads(body)
    if "error" in msg:
        raise RuntimeError(f"MCP service error: {msg['error'].get('message')}")
    return "\n".join(c.get("text", "") for c in msg["result"].get("content", []) if c.get("type") == "text")


@mlflow.trace(name="prep_brief", span_type=SpanType.AGENT)
def prep_brief(query, store_location):
    start = time.time()
    try:
        store_data, _ = build_prep_store_data(query, store_location)
        if not store_data:
            return {"text": f"I couldn't find the store '{store_location}'.", "latency_ms": 0,
                    "input_tokens": 0, "output_tokens": 0, "error": "unknown_store"}
        plan = call_ops_advisor(query, store_location, store_data)
        text = plan + "\n\n---\n**Store data used** (SQL on gold + Lakebase):\n" + store_data
        return {"text": text, "latency_ms": (time.time() - start) * 1000,
                "input_tokens": 0, "output_tokens": 0, "error": None}
    except Exception as e:
        return {"text": f"Error building the preparation plan: {e}", "latency_ms": (time.time() - start) * 1000,
                "input_tokens": 0, "output_tokens": 0, "error": str(e)}


_menu_lock = threading.Lock()
_menu = None  # [(name_lower, display_name, base_price)], longest names first


def _load_menu():
    global _menu
    with _menu_lock:
        if _menu is None:
            rows = _run_sql(f"SELECT name, base_price FROM {CATALOG_SCHEMA}.products")
            items = []
            for r in rows:
                # "Bella Kaapi (Jaggery)" is asked for as "Bella Kaapi"
                display = r["name"]
                key = re.sub(r"\s*\(.*?\)", "", display).strip().lower()
                items.append((key, display, float(r["base_price"])))
            _menu = sorted(items, key=lambda x: -len(x[0]))
    return _menu


@mlflow.trace(name="menu_price_lookup", span_type=SpanType.TOOL)
def add_menu_prices(query, answer):
    """Append governed menu prices (products.base_price) for drinks named in the question.

    Prices are structured data, so they come from the table rather than relying on the
    model to copy them out of the recipe PDF (eval run 3 showed it often drops them).
    """
    try:
        menu = _load_menu()
    except Exception as e:
        print(f"[Menu] lookup failed: {e}")
        return answer
    remaining = query.lower()
    lines = []
    for key, display, price in menu:
        if key and key in remaining:
            remaining = remaining.replace(key, " ")  # "degree coffee" inside "kumbakonam degree coffee"
            p = f"{price:g}"
            if not re.search(rf"(Rs\.?\s?|₹\s?){re.escape(p)}\b", answer):
                lines.append(f"- {display}: Rs.{p}")
    if not lines:
        return answer
    return answer + "\n\n**Menu price** (from the `products` table):\n" + "\n".join(lines)


@mlflow.trace(name="chat_request", span_type=SpanType.AGENT)
def process_chat(query, store, history, conv_id, skip_cache=False):
    """Traced end-to-end chat processing with cache check and Genie Agent call."""
    # Preparation plans depend on today's weather, so they bypass the cache entirely
    prep = is_prep_question(query)
    # 1. Check short-term memory
    cached = None if (skip_cache or prep) else find_cached_answer(query, store)
    if cached:
        trace_id = None
        try:
            span = mlflow.get_current_active_span()
            if span:
                trace_id = span.request_id
                mlflow.update_current_trace(tags={"cache_hit": "true", "match_type": cached.get("match", "exact")})
        except Exception:
            pass
        return {
            "text": cached["answer"],
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "from_cache": True,
            "match_type": cached.get("match", "exact"),
            "similarity": cached.get("similarity", 1.0),
            "matched_question": cached.get("matched_question", ""),
            "trace_id": trace_id,
            "error": None,
        }

    # 2. Preparation plan (SQL + Lakebase + MCP via Unity AI Gateway) or Genie Agent
    if prep:
        result = prep_brief(query, store)
        result["no_cache"] = True
    else:
        messages = history + [{"role": "user", "content": query}]
        result = call_genie_sync(messages, store)
        if not result.get("error"):
            result["text"] = add_menu_prices(query, result["text"])

    # 3. Update trace metadata with token usage
    trace_id = None
    try:
        span = mlflow.get_current_active_span()
        if span:
            trace_id = span.request_id
            mlflow.update_current_trace(
                tags={"cache_hit": "false", "route": "prep_mcp" if prep else "genie"},
                metadata={
                    "input_tokens": str(result["input_tokens"]),
                    "output_tokens": str(result["output_tokens"]),
                    "total_tokens": str(result["input_tokens"] + result["output_tokens"]),
                },
            )
    except Exception:
        pass

    result["from_cache"] = False
    result["match_type"] = ""
    result["similarity"] = 0
    result["matched_question"] = ""
    result["trace_id"] = trace_id
    return result


@app.post("/api/chat")
async def chat(request: Request):
    """SSE chat endpoint with short-term memory cache and MLflow tracing."""
    body = await request.json()
    query = body.get("query", "")
    conv_id = body.get("conversation_id")
    store = body.get("store_location", "Koramangala, Bangalore")
    history = body.get("history", [])
    skip_cache = bool(body.get("skip_cache", False))  # evaluation runs measure fresh answers

    if not conv_id:
        conv_id = str(uuid.uuid4())
        title = query[:60] + ("..." if len(query) > 60 else "")
        save_conversation(conv_id, title)

    save_message(conv_id, "user", query)

    # Run traced processing
    result = process_chat(query, store, history, conv_id, skip_cache=skip_cache)

    # Save assistant message
    save_message(conv_id, "assistant", result["text"], trace_id=result.get("trace_id"))

    # Background: cache + log inference
    if not result["from_cache"]:
        def _cache_and_log():
            if not skip_cache and not result.get("no_cache"):
                try:
                    embedding = get_embedding(query)
                except Exception:
                    embedding = None
                save_to_cache(query, result["text"], embedding, store, result["latency_ms"])
            log_inference(
                result.get("trace_id"), conv_id, store, query, result["text"],
                result["latency_ms"], result["input_tokens"], result["output_tokens"],
                result.get("error"),
            )
        threading.Thread(target=_cache_and_log, daemon=True).start()

    # Return as SSE (single event — frontend handles typing animation)
    def event_stream():
        yield f"data: {json.dumps({'done': True, 'full_text': result['text'], 'latency_ms': result['latency_ms'], 'input_tokens': result['input_tokens'], 'output_tokens': result['output_tokens'], 'from_cache': result['from_cache'], 'match_type': result.get('match_type', ''), 'similarity': result.get('similarity', 0), 'matched_question': result.get('matched_question', ''), 'trace_id': result.get('trace_id')})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": conv_id,
        },
    )


# =============================================================================
# INVOICE PARSER — Upload, parse via Unity AI Gateway (kaapi_llm), match PO, approve
# =============================================================================
import base64
from fastapi import UploadFile, File, Form

INVOICE_VOLUME = "/Volumes/fevm_cme_conde_catalog/kaapi_bricks/invoices"
CATALOG_SCHEMA = "fevm_cme_conde_catalog.kaapi_bricks"


def _run_sql(sql, warehouse_id=None):
    """Run SQL via Statement API and return rows as list of dicts."""
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/api/2.0/sql/statements"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    payload = {"warehouse_id": warehouse_id or SQL_WAREHOUSE_ID, "statement": sql, "wait_timeout": "50s"}
    print(f"[SQL] Sending: {sql[:200]}")
    resp = http_requests.post(url, headers=headers, json=payload, timeout=180)
    if resp.status_code != 200:
        print(f"[SQL] HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    data = resp.json()
    # If still running, poll until done
    if data.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        stmt_id = data.get("statement_id")
        for _ in range(20):  # Poll up to ~100s
            time.sleep(5)
            poll_resp = http_requests.get(f"{url}/{stmt_id}", headers=headers, timeout=30)
            data = poll_resp.json()
            if data.get("status", {}).get("state") not in ("PENDING", "RUNNING"):
                break
    if data.get("status", {}).get("state") != "SUCCEEDED":
        err = data.get("status", {}).get("error", {}).get("message", "SQL failed")
        print(f"[SQL Error] {err}")
        return []
    columns = [c["name"] for c in data.get("manifest", {}).get("schema", {}).get("columns", [])]
    return [dict(zip(columns, row)) for row in data.get("result", {}).get("data_array", [])]


@app.post("/api/parse-invoice")
async def parse_invoice(file: UploadFile = File(...), store: str = Form("Koramangala, Bangalore")):
    """Upload invoice PDF/image → parse + extract via Unity AI Gateway → match PO → return results."""
    start_time = time.time()

    # Step 1: Save file to Unity Catalog Volume
    file_content = await file.read()
    filename = f"inv_{uuid.uuid4().hex[:8]}_{file.filename}"
    try:
        w = _get_workspace_client()
        import io
        w.files.upload(f"{INVOICE_VOLUME}/{filename}", io.BytesIO(file_content), overwrite=True)
        print(f"[Invoice] Uploaded to {INVOICE_VOLUME}/{filename}")
    except Exception as e:
        return JSONResponse({"error": f"Upload failed: {e}"}, status_code=500)

    # Step 2: Parse + extract in ONE governed call. The PDF (or image) goes to the kaapi_llm
    # model service through the Unity AI Gateway, so document parsing is EXECUTE-checked,
    # rate-limited and payload-logged like every other non-Genie AI call.
    json_schema = '{"supplier_name":"string","invoice_number":"string","invoice_date":"YYYY-MM-DD","po_reference":"string or null","delivery_to":"string","items":[{"name":"string","quantity":0.0,"unit":"kg/liter/case","rate":0.0,"amount":0.0}],"subtotal":0.0,"gst_amount":0.0,"total_amount":0.0}'
    file_b64 = base64.b64encode(file_content).decode("utf-8")
    if filename.lower().endswith(".pdf"):
        doc_block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": file_b64}}
    else:
        mime = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
        doc_block = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{file_b64}"}}
    try:
        llm_text = gateway_chat([{"role": "user", "content": [
            doc_block,
            {"type": "text", "text": f"Extract from this invoice. Return ONLY valid JSON matching this schema: {json_schema}"},
        ]}], max_tokens=1500)
        # Extract JSON from response (handle markdown code blocks)
        if "```" in llm_text:
            llm_text = llm_text.split("```")[1]
            if llm_text.startswith("json"):
                llm_text = llm_text[4:]
        extracted = json.loads(llm_text.strip())
        print(f"[Invoice] Extracted via Unity AI Gateway: {json.dumps(extracted)[:300]}")
    except Exception as e:
        return JSONResponse({"error": f"Extraction failed: {e}"}, status_code=500)

    # Step 3: Match supplier
    supplier_name = extracted.get("supplier_name", "")
    supplier_rows = _run_sql(f"SELECT supplier_id, name FROM {CATALOG_SCHEMA}.suppliers WHERE LOWER(name) LIKE LOWER('%{supplier_name.split()[0] if supplier_name else 'X'}%')")
    supplier_match = supplier_rows[0] if supplier_rows else None

    # Step 4: Find matching PO
    po_match = None
    po_lines = []
    warnings = []
    po_ref = extracted.get("po_reference", "")
    if po_ref:
        po_rows = _run_sql(f"SELECT po_id, supplier_id, store_id, total_amount, status FROM {CATALOG_SCHEMA}.purchase_orders WHERE po_id = '{po_ref}'")
        if po_rows and supplier_match and po_rows[0]["supplier_id"] != supplier_match["supplier_id"]:
            # PO reference belongs to a different supplier — never reconcile against it
            warnings.append(f"PO {po_ref} belongs to {po_rows[0]['supplier_id']}, not invoice supplier "
                            f"{supplier_match['supplier_id']} ({supplier_match['name']}) — reference ignored")
        elif po_rows:
            po_match = po_rows[0]
            po_lines = _run_sql(f"SELECT ingredient_id, ingredient_name, quantity, unit, unit_price, line_total FROM {CATALOG_SCHEMA}.po_line_items WHERE po_id = '{po_ref}'")
        else:
            warnings.append(f"PO {po_ref} not found")
    if not po_match and supplier_match:
        # Try matching by supplier + store
        store_id = "STR-001"  # TODO: map store name to ID
        po_rows = _run_sql(f"SELECT po_id, supplier_id, store_id, total_amount, status FROM {CATALOG_SCHEMA}.purchase_orders WHERE supplier_id = '{supplier_match['supplier_id']}' AND store_id = '{store_id}' AND status != 'delivered' ORDER BY order_date DESC LIMIT 1")
        if po_rows:
            po_match = po_rows[0]
            po_lines = _run_sql(f"SELECT ingredient_id, ingredient_name, quantity, unit, unit_price, line_total FROM {CATALOG_SCHEMA}.po_line_items WHERE po_id = '{po_rows[0]['po_id']}'")

    # Step 5: Compare invoice items vs PO items — find discrepancies
    discrepancies = []
    invoice_items = extracted.get("items", [])
    matched_items = []

    for inv_item in invoice_items:
        inv_name = (inv_item.get("name") or "").lower()
        inv_qty = float(inv_item.get("quantity") or 0)
        inv_rate = float(inv_item.get("rate") or 0)

        # Find matching PO line
        po_line = None
        for pl in po_lines:
            if pl.get("ingredient_name", "").lower() in inv_name or inv_name in pl.get("ingredient_name", "").lower():
                po_line = pl
                break

        item_result = {
            "invoice_name": inv_item.get("name"),
            "invoice_qty": inv_qty,
            "invoice_unit": inv_item.get("unit"),
            "invoice_rate": inv_rate,
            "invoice_amount": float(inv_item.get("amount") or 0),
            "status": "match",
            "issues": [],
        }

        if po_line:
            item_result["po_name"] = po_line.get("ingredient_name")
            item_result["po_qty"] = float(po_line.get("quantity") or 0)
            item_result["po_rate"] = float(po_line.get("unit_price") or 0)
            item_result["ingredient_id"] = po_line.get("ingredient_id")

            # Check quantity
            if inv_qty != float(po_line.get("quantity") or 0):
                diff = inv_qty - float(po_line["quantity"])
                item_result["issues"].append(f"Qty: ordered {po_line['quantity']}, invoiced {inv_qty} ({'+' if diff > 0 else ''}{diff:.1f})")
                item_result["status"] = "warning"

            # Check price
            if inv_rate != float(po_line.get("unit_price") or 0):
                diff = inv_rate - float(po_line["unit_price"])
                item_result["issues"].append(f"Price: contract ₹{po_line['unit_price']}, invoiced ₹{inv_rate} ({'+' if diff > 0 else ''}₹{diff:.0f})")
                item_result["status"] = "error"
        else:
            item_result["status"] = "extra"
            item_result["issues"].append("Not in PO — extra item")

        matched_items.append(item_result)

    # Check for missing PO items (in PO but not in invoice)
    for pl in po_lines:
        # Compare against the PO line each invoice item actually matched above — a bare
        # substring test would count "Jaggery Blocks" as delivering "Palm Jaggery".
        found = any(mi.get("po_name") == pl.get("ingredient_name") for mi in matched_items)
        if not found:
            matched_items.append({
                "invoice_name": pl.get("ingredient_name"),
                "po_name": pl.get("ingredient_name"),
                "po_qty": float(pl.get("quantity") or 0),
                "po_rate": float(pl.get("unit_price") or 0),
                "status": "missing",
                "issues": ["In PO but not in invoice — missing delivery"],
                "ingredient_id": pl.get("ingredient_id"),
            })

    latency_ms = (time.time() - start_time) * 1000
    return {
        "extracted": extracted,
        "supplier_match": supplier_match,
        "po_match": po_match,
        "po_lines": po_lines,
        "matched_items": matched_items,
        "warnings": warnings,
        "latency_ms": latency_ms,
        "filename": filename,
    }


@app.post("/api/approve-invoice")
async def approve_invoice(request: Request):
    """Approve invoice → write to app_inventory_receipts + record PO approval.

    Writes to app-managed Delta tables (not the pipeline-owned silver MVs) so
    the medallion architecture stays intact. gold_inventory_position and
    gold_open_purchase_orders union these in on the next pipeline refresh.
    """
    body = await request.json()
    items = body.get("items", [])
    store_id = body.get("store_id", "STR-001")
    po_id = body.get("po_id")

    inserted = 0
    for item in items:
        if not item.get("ingredient_id") or not item.get("invoice_qty"):
            continue
        receipt_id = f"RCP-{uuid.uuid4().hex[:8]}"
        sql = f"""INSERT INTO {CATALOG_SCHEMA}.app_inventory_receipts
            (receipt_id, store_id, ingredient_id, receipt_date, quantity, unit_cost)
            VALUES ('{receipt_id}', '{store_id}', '{item['ingredient_id']}', CURRENT_DATE(), {item['invoice_qty']}, {item.get('invoice_rate', 0)})"""
        _run_sql(sql)
        inserted += 1

    # Record PO approval (gold_open_purchase_orders excludes approved POs)
    if po_id:
        approval_id = f"APR-{uuid.uuid4().hex[:8]}"
        _run_sql(f"""INSERT INTO {CATALOG_SCHEMA}.app_po_approvals
            (approval_id, po_id, actual_delivery)
            VALUES ('{approval_id}', '{po_id}', CURRENT_DATE())""")

    return {"ok": True, "inserted": inserted, "po_updated": po_id}


@app.get("/api/inventory/{store_id}")
def get_inventory(store_id: str):
    """Get current inventory from the gold operational view (unions pipeline + app receipts)."""
    sql = f"""
    SELECT ingredient_id, ingredient_name, unit,
           current_stock, reorder_threshold, below_reorder, days_cover
    FROM {CATALOG_SCHEMA}.gold_inventory_position
    WHERE store_id = '{store_id}'
    ORDER BY ingredient_name
    """
    rows = _run_sql(sql)
    return {"store_id": store_id, "inventory": rows}


@app.get("/api/lakebase/inventory/{store_id}")
def get_lakebase_inventory(store_id: str):
    """Get current inventory from Lakebase (OLTP latency) — operational serving path.

    Reads lb_inventory_position synced from gold_inventory_position via
    scripts/sync_gold_to_lakebase.py. Lower latency than scanning Delta.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT ingredient_id, ingredient_name, unit, current_stock, reorder_threshold, "
            "below_reorder, days_cover FROM lb_inventory_position WHERE store_id = %s ORDER BY ingredient_name",
            (store_id,)
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return {"store_id": store_id, "source": "lakebase", "inventory": rows}
    except Exception as e:
        return {"store_id": store_id, "source": "lakebase", "error": str(e), "inventory": []}


# Serve static files and index.html
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r") as f:
        return f.read()


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


# END OF FILE
