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
MAS_ENDPOINT_NAME = os.environ.get("MAS_ENDPOINT_NAME", "mas-3c936239-endpoint")
LAKEBASE_INSTANCE_NAME = os.environ.get("LAKEBASE_INSTANCE_NAME", "kaapi-bricks")
LAKEBASE_DATABASE_NAME = os.environ.get("LAKEBASE_DATABASE_NAME", "databricks_postgres")
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "e755eae9d758fdf7")
EMBEDDING_ENDPOINT = os.environ.get("EMBEDDING_ENDPOINT", "databricks-bge-large-en")
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.85"))
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "48"))

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
        cur.execute("CREATE SCHEMA IF NOT EXISTS kaapi_finale")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.conversations (
            id TEXT PRIMARY KEY, title TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.messages (
            id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES kaapi_finale.conversations(id) ON DELETE CASCADE,
            role TEXT, content TEXT, trace_id TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON kaapi_finale.messages(conversation_id, created_at)")
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.feedback (
            id TEXT PRIMARY KEY, message_id TEXT, conversation_id TEXT, trace_id TEXT,
            value TEXT, created_at TIMESTAMP DEFAULT NOW())""")
        # Short-term memory cache table
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.qa_cache (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            embedding JSONB,
            store_location TEXT,
            latency_ms DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_qa_cache_time ON kaapi_finale.qa_cache(created_at)")
        # Compare cache table — caches Operations Advisor results per model
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.compare_cache (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            model_endpoint TEXT NOT NULL,
            store_location TEXT,
            latency_ms DOUBLE PRECISION,
            input_tokens INT DEFAULT 0,
            output_tokens INT DEFAULT 0,
            weather_data JSONB,
            calendar_data JSONB,
            created_at TIMESTAMP DEFAULT NOW())""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_compare_cache ON kaapi_finale.compare_cache(question, model_endpoint, store_location)")
        # Admin config table — stores router model and operations model selection
        cur.execute("""CREATE TABLE IF NOT EXISTS kaapi_finale.admin_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW())""")
        # Set defaults if not exists
        cur.execute("""INSERT INTO kaapi_finale.admin_config (key, value) VALUES
            ('router_model', 'databricks-meta-llama-3-3-70b-instruct'),
            ('operations_model', 'databricks-meta-llama-3-3-70b-instruct')
            ON CONFLICT (key) DO NOTHING""")
        # Cleanup stale cache entries on startup
        cur.execute(f"DELETE FROM kaapi_finale.qa_cache WHERE created_at < NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
        cur.execute(f"DELETE FROM kaapi_finale.compare_cache WHERE created_at < NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
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
            "INSERT INTO kaapi_finale.conversations (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (conv_id, title))
    except Exception as e:
        print(f"[Lakebase] save_conversation error: {e}")


def save_message(conv_id, role, content, trace_id=None):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_finale.messages (id, conversation_id, role, content, trace_id) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), conv_id, role, content, trace_id))
    except Exception as e:
        print(f"[Lakebase] save_message error: {e}")



def load_conversations():
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT id, title, created_at FROM kaapi_finale.conversations ORDER BY created_at DESC LIMIT 20")
        return [{"id": r[0], "title": r[1], "created_at": str(r[2])} for r in cur.fetchall()]
    except Exception:
        return []


def load_messages(conv_id):
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT role, content FROM kaapi_finale.messages WHERE conversation_id = %s ORDER BY created_at", (conv_id,))
        return [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
    except Exception:
        return []


def delete_all_conversations():
    try:
        cur = get_conn().cursor()
        cur.execute("DELETE FROM kaapi_finale.messages")
        cur.execute("DELETE FROM kaapi_finale.conversations")
    except Exception:
        pass


def save_feedback(msg_id, conv_id, trace_id, value):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_finale.feedback (id, message_id, conversation_id, trace_id, value) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), msg_id, conv_id, trace_id, value))
    except Exception as e:
        print(f"[Lakebase] save_feedback error: {e}")


# =============================================================================
# ADMIN CONFIG HELPERS
# =============================================================================
def get_admin_config():
    """Get current admin config (router model, operations model)."""
    config = {"router_model": "databricks-meta-llama-3-3-70b-instruct",
              "operations_model": "databricks-meta-llama-3-3-70b-instruct"}
    try:
        cur = get_conn().cursor()
        cur.execute("SELECT key, value FROM kaapi_finale.admin_config")
        for row in cur.fetchall():
            config[row[0]] = row[1]
    except Exception:
        pass
    return config


def set_admin_config(key, value):
    try:
        get_conn().cursor().execute(
            "INSERT INTO kaapi_finale.admin_config (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()",
            (key, value, value))
    except Exception as e:
        print(f"[Lakebase] set_admin_config error: {e}")


# =============================================================================
# COMPARE CACHE HELPERS
# =============================================================================
def find_compare_cache(question, model, store):
    """Check if we have a cached compare result for this question+model+store."""
    try:
        cur = get_conn().cursor()
        cur.execute(
            f"""SELECT answer, latency_ms, input_tokens, output_tokens, weather_data, calendar_data
                FROM kaapi_finale.compare_cache
                WHERE LOWER(TRIM(question)) = LOWER(TRIM(%s))
                  AND model_endpoint = %s AND store_location = %s
                  AND created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'
                ORDER BY created_at DESC LIMIT 1""",
            (question, model, store))
        row = cur.fetchone()
        if row:
            return {"answer": row[0], "latency_ms": row[1], "input_tokens": row[2],
                    "output_tokens": row[3], "weather": json.loads(row[4]) if row[4] else None,
                    "calendar": json.loads(row[5]) if row[5] else None, "from_cache": True}
    except Exception as e:
        print(f"Compare cache lookup error: {e}")
    return None


def save_compare_cache(question, answer, model, store, latency_ms, input_tokens, output_tokens, weather, calendar):
    try:
        get_conn().cursor().execute(
            """INSERT INTO kaapi_finale.compare_cache (id, question, answer, model_endpoint, store_location, latency_ms, input_tokens, output_tokens, weather_data, calendar_data)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), question, answer, model, store, latency_ms, input_tokens, output_tokens,
             json.dumps(weather) if weather else None, json.dumps(calendar) if calendar else None))
    except Exception as e:
        print(f"Compare cache save error: {e}")


# =============================================================================
# ROUTING LOGIC — App-Level Supervisor
# =============================================================================
ROUTE_SYSTEM_PROMPT = """You are a routing agent for Kaapi Bricks coffee chain. Classify the user's question into one of these categories:

1. "mas" — Questions about recipes, drink preparation, policies, food safety, training, sales data, inventory levels, revenue, promotions, supplier info, franchise info. Anything that can be answered from existing documents or database tables.
2. "both" — Questions that need operational planning: what to prepare, staffing, weather impact, festival/holiday planning, forecasting, demand planning. These ALWAYS need both weather/calendar info AND store data, so route to "both".

Respond with ONLY one word: "mas" or "both". Nothing else."""


OPS_KEYWORDS = {"prepare", "tomorrow", "staff", "staffing", "forecast", "weather", "festival", "holiday",
                "weekend", "friday", "demand", "plan ahead", "what should i", "how should i"}

@mlflow.trace(name="route_decision", span_type=SpanType.CHAIN)
def route_query(query, router_model):
    """Fast keyword-based routing. Falls back to LLM for ambiguous queries."""
    q_lower = query.lower()
    # Fast path: keyword match for operations questions
    if any(kw in q_lower for kw in OPS_KEYWORDS):
        return "both"
    # Fast path: clearly data/knowledge questions
    if any(kw in q_lower for kw in ("recipe", "how do i make", "policy", "top selling", "revenue", "sales", "inventory level")):
        return "mas"
    # Ambiguous: use LLM router
    try:
        w = _get_workspace_client()
        url = f"{w.config.host.rstrip('/')}/serving-endpoints/{router_model}/invocations"
        headers = w.config.authenticate()
        headers["Content-Type"] = "application/json"
        resp = http_requests.post(url, headers=headers,
            json={"messages": [
                {"role": "system", "content": ROUTE_SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ], "max_tokens": 10, "temperature": 0}, timeout=30)
        resp.raise_for_status()
        decision = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "mas").strip().lower()
        return decision if decision in ("mas", "both") else "mas"
    except Exception as e:
        print(f"Route decision error: {e}")
        return "mas"


def _extract_first_json_object(text: str) -> dict | None:
    """Best-effort JSON object extraction from model output."""
    if not text:
        return None
    text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def extract_query_intent(query: str, router_model: str) -> dict:
    """Extract structured intent for routing and planning date."""
    default_route = route_query(query, router_model)
    default_time_sensitive = is_time_sensitive_query(query)
    default_target_date = resolve_target_date(query) if default_time_sensitive else None
    fallback = {
        "route": default_route,
        "target_date": default_target_date,
        "needs_weather": default_route == "both",
        "is_time_sensitive": default_time_sensitive,
        "date_confidence": "low" if default_time_sensitive else "n/a",
    }
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        w = _get_workspace_client()
        url = f"{w.config.host.rstrip('/')}/serving-endpoints/{router_model}/invocations"
        headers = w.config.authenticate()
        headers["Content-Type"] = "application/json"
        prompt = (
            "You are a query intent parser for a coffee chain assistant.\n"
            f"Today is {today}.\n"
            "Return ONLY strict JSON with keys:\n"
            'route: "mas" or "both"\n'
            "target_date: ISO date YYYY-MM-DD or null\n"
            "is_time_sensitive: boolean\n"
            "needs_weather: boolean\n"
            'date_confidence: "high" | "medium" | "low"\n'
            "Rules:\n"
            '- route="both" only for operations planning questions (prepare/staff/forecast/demand/date-sensitive planning).\n'
            '- route="mas" for knowledge/data queries (recipes, policies, sales lookup, inventory lookup).\n'
            "- If a date is requested or implied, set target_date.\n"
            f"User query: {query}"
        )
        resp = http_requests.post(
            url,
            headers=headers,
            json={
                "messages": [
                    {"role": "system", "content": "You return strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 200,
                "temperature": 0,
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = _extract_first_json_object(content)
        if not parsed:
            return fallback

        route = parsed.get("route")
        if route not in ("mas", "both"):
            route = default_route

        target_date = parsed.get("target_date")
        if target_date is not None:
            try:
                target_date = datetime.fromisoformat(str(target_date)).strftime("%Y-%m-%d")
            except Exception:
                target_date = None

        is_time_sensitive = bool(parsed.get("is_time_sensitive"))
        needs_weather = bool(parsed.get("needs_weather")) if route == "both" else False
        date_confidence = str(parsed.get("date_confidence", "low")).lower()
        if date_confidence not in ("high", "medium", "low"):
            date_confidence = "low"

        if route == "both" and not target_date:
            target_date = resolve_target_date(query)
            is_time_sensitive = True

        return {
            "route": route,
            "target_date": target_date,
            "needs_weather": needs_weather,
            "is_time_sensitive": is_time_sensitive or bool(target_date),
            "date_confidence": date_confidence,
        }
    except Exception as e:
        print(f"[Intent parser] error: {e}")
        return fallback


# =============================================================================
# EMBEDDING & SEMANTIC CACHE
# =============================================================================
@mlflow.trace(name="get_embedding", span_type=SpanType.EMBEDDING)
def get_embedding(text: str) -> list:
    """Get embedding vector from Databricks BGE endpoint."""
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{EMBEDDING_ENDPOINT}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    resp = http_requests.post(
        url, headers=headers,
        json={"input": [text[:8000]]},  # BGE max input ~8K chars
        timeout=15,
    )
    resp.raise_for_status()
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
def find_cached_answer(question: str) -> dict | None:
    """Check Lakebase for a semantically similar question from last 48 hours."""
    try:
        cur = get_conn().cursor()
        # Layer 1: Exact match (instant, no embedding needed)
        cur.execute(
            f"""SELECT answer, latency_ms FROM kaapi_finale.qa_cache
                WHERE LOWER(TRIM(question)) = LOWER(TRIM(%s))
                  AND created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'
                ORDER BY created_at DESC LIMIT 1""",
            (question,))
        row = cur.fetchone()
        if row:
            return {"answer": row[0], "from_cache": True, "match": "exact",
                    "original_latency_ms": row[1] or 0}

        # Layer 2: Embedding similarity
        q_embedding = get_embedding(question)

        cur.execute(
            f"""SELECT question, answer, embedding, latency_ms FROM kaapi_finale.qa_cache
                WHERE created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'
                  AND embedding IS NOT NULL""")
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
            """INSERT INTO kaapi_finale.qa_cache (id, question, answer, embedding, store_location, latency_ms)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), question, answer,
             json.dumps(embedding) if embedding else None,
             store, latency_ms))
    except Exception as e:
        print(f"Cache save error: {e}")


# =============================================================================
# MAS ENDPOINT — STREAMING
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


def _prepare_messages(messages, store_location):
    """Prepend store location to the first user message."""
    input_messages = []
    first_user = True
    for msg in messages:
        if msg["role"] == "user" and first_user:
            input_messages.append({
                "role": "user",
                "content": f"[Store location: Kaapi Bricks {store_location}] {msg['content']}",
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


@mlflow.trace(name="mas_call", span_type=SpanType.CHAT_MODEL)
def call_mas_sync(messages, store_location):
    """Non-streaming MAS call with token usage extraction and MLflow tracing."""
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{MAS_ENDPOINT_NAME}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    input_messages = _prepare_messages(messages, store_location)

    start_time = time.time()
    try:
        resp = http_requests.post(
            url, headers=headers,
            json={"input": input_messages},
            timeout=300,
        )
        resp.raise_for_status()
        latency_ms = (time.time() - start_time) * 1000

        data = resp.json()
        raw_text = _extract_text_from_output(data)
        cleaned = clean_response(raw_text)
        input_tokens, output_tokens = _extract_token_usage(data)

        return {
            "text": cleaned,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "error": None,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(e),
        }


def stream_mas(messages, store_location):
    """Call MAS endpoint with streaming and yield SSE chunks. Extracts token usage."""
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{MAS_ENDPOINT_NAME}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    input_messages = _prepare_messages(messages, store_location)

    start_time = time.time()
    try:
        resp = http_requests.post(
            url, headers=headers,
            json={"input": input_messages, "config": {"output_mode": "stream"}},
            stream=True, timeout=300,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            full_text = ""
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = ""
                        for item in chunk.get("output", []):
                            if item.get("type") == "message":
                                for block in item.get("content", []):
                                    if block.get("type") == "output_text":
                                        delta = block.get("text", "")
                        if delta:
                            full_text += delta
                            yield f"data: {json.dumps({'delta': delta})}\n\n"
                    except json.JSONDecodeError:
                        pass

            cleaned = clean_response(full_text)
            latency_ms = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({'done': True, 'full_text': cleaned, 'latency_ms': latency_ms, 'input_tokens': 0, 'output_tokens': 0})}\n\n"
        else:
            data = resp.json()
            raw_text = _extract_text_from_output(data)
            cleaned = clean_response(raw_text)
            input_tokens, output_tokens = _extract_token_usage(data)
            latency_ms = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({'done': True, 'full_text': cleaned, 'latency_ms': latency_ms, 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        yield f"data: {json.dumps({'done': True, 'full_text': f'Error: {str(e)}', 'latency_ms': latency_ms, 'error': str(e), 'input_tokens': 0, 'output_tokens': 0})}\n\n"


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
                'MAS', '{MAS_ENDPOINT_NAME}', {input_tokens}, {output_tokens}, '{error or ""}')"""
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
    "Which stores are running low on Coorg Arabica beans?",
    "What promotions are active right now?",
    "How long does Coorg Arabica take to reorder?",
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


@app.post("/api/reinit-db")
async def reinit_database():
    """Force reinitialize all Lakebase tables."""
    ok = init_db()
    return {"ok": ok}


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
        stats["connected"] = True
    except Exception as e:
        print(f"[Stats] connection error: {e}")
        return stats
    # Individual queries — each wrapped so one failure doesn't break the rest
    def _count(sql):
        try:
            cur = conn.cursor()
            cur.execute(sql)
            return cur.fetchone()[0]
        except Exception as e:
            print(f"[Stats] query error: {e}")
            return 0
    stats["chats"] = _count("SELECT COUNT(*) FROM kaapi_finale.conversations")
    stats["messages"] = _count("SELECT COUNT(*) FROM kaapi_finale.messages")
    stats["feedback_total"] = _count("SELECT COUNT(*) FROM kaapi_finale.feedback")
    stats["feedback_positive"] = _count("SELECT COUNT(*) FROM kaapi_finale.feedback WHERE value = 'positive'")
    stats["cache_entries"] = _count(f"SELECT COUNT(*) FROM kaapi_finale.qa_cache WHERE created_at > NOW() - INTERVAL '{CACHE_TTL_HOURS} hours'")
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


@mlflow.trace(name="chat_request", span_type=SpanType.AGENT)
def process_chat(query, store, history, conv_id):
    """Traced end-to-end chat with app-level routing: MAS, Operations Advisor, or both."""
    # 1. Check short-term memory cache
    cached = None
    if not is_time_sensitive_query(query):
        cached = find_cached_answer(query)
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
            "text": cached["answer"], "latency_ms": 0, "input_tokens": 0, "output_tokens": 0,
            "from_cache": True, "match_type": cached.get("match", "exact"),
            "similarity": cached.get("similarity", 1.0), "matched_question": cached.get("matched_question", ""),
            "trace_id": trace_id, "error": None, "route": "cache",
        }

    # 2. Get admin config for model selection
    config = get_admin_config()
    router_model = config.get("router_model", FOUNDATION_MODELS[0])
    ops_model = config.get("operations_model", FOUNDATION_MODELS[0])

    # 3. Parse intent (route + target date)
    intent = extract_query_intent(query, router_model)
    route = intent.get("route", "mas")
    target_date = intent.get("target_date")
    date_confidence = intent.get("date_confidence", "n/a")

    # 4. Execute based on route
    if route == "both":
        # Step 1: Call MAS for store data (Genie queries sales, inventory, promotions)
        mas_data_query = f"For the {store} store, show me: top selling products with quantities, current inventory levels for key ingredients, recent daily order counts and revenue, and any active promotions."
        mas_messages = [{"role": "user", "content": mas_data_query}]
        mas_result = call_mas_sync(mas_messages, store)

        # Step 2: Call Operations Advisor with MAS data included as context
        result = run_ops_advisor_with_data(query, store, ops_model, mas_result.get("text", ""), target_date=target_date)
        result["input_tokens"] = result.get("input_tokens", 0) + mas_result.get("input_tokens", 0)
        result["output_tokens"] = result.get("output_tokens", 0) + mas_result.get("output_tokens", 0)
        result["latency_ms"] = result.get("latency_ms", 0) + mas_result.get("latency_ms", 0)
        route_tag = "both"

    else:
        # Default: MAS only (recipes, data, policies)
        messages = history + [{"role": "user", "content": query}]
        result = call_mas_sync(messages, store)
        route_tag = "mas"

    # 5. Update trace metadata
    trace_id = None
    try:
        span = mlflow.get_current_active_span()
        if span:
            trace_id = span.request_id
            mlflow.update_current_trace(
                tags={"cache_hit": "false", "route": route_tag, "router_model": router_model,
                      "ops_model": ops_model if route_tag != "mas" else "n/a"},
                metadata={
                    "input_tokens": str(result.get("input_tokens", 0)),
                    "output_tokens": str(result.get("output_tokens", 0)),
                    "target_date": str(target_date or ""),
                    "date_confidence": str(date_confidence),
                },
            )
    except Exception:
        pass

    result["from_cache"] = False
    result["match_type"] = ""
    result["similarity"] = 0
    result["matched_question"] = ""
    result["trace_id"] = trace_id
    result["route"] = route_tag
    return result


@mlflow.trace(name="ops_advisor_with_data", span_type=SpanType.CHAIN)
def run_ops_advisor_with_data(query: str, store: str, model_endpoint: str, mas_data: str, target_date: str | None = None) -> dict:
    """Operations Advisor with MAS store data + weather + calendar — ONE LLM call, no synthesis needed."""
    target_date = target_date or resolve_target_date(query)
    city = store.split(",")[-1].strip() if "," in store else store

    # Get weather + calendar
    weather = get_weather_forecast(city, target_date)
    calendar = check_calendar(target_date)

    # Build combined context: MAS data + weather + calendar
    context = f"""## Planning Target Date (resolved from user request)
{target_date}

## Store Data (from analytics — real sales, inventory, products, promotions):
{mas_data}

## Weather Forecast for {target_date}:
{json.dumps(weather, indent=2)}

## Calendar for {target_date}:
{json.dumps(calendar, indent=2)}
"""

    # Single LLM call with all context
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{model_endpoint}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    messages = [
        {"role": "system", "content": OPS_SYSTEM_PROMPT},
        {"role": "user", "content": f"{query}\n\n---\n{context}"},
    ]

    start_time = time.time()
    try:
        resp = http_requests.post(url, headers=headers,
            json={"messages": messages, "max_tokens": 2000, "temperature": 0.3}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start_time) * 1000
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        usage = data.get("usage", {})
        return {
            "text": answer, "latency_ms": latency_ms, "model": model_endpoint,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "weather": weather, "calendar": calendar, "error": None,
        }
    except Exception as e:
        return {"text": f"Error: {e}", "latency_ms": (time.time() - start_time) * 1000,
                "model": model_endpoint, "input_tokens": 0, "output_tokens": 0,
                "weather": weather, "calendar": calendar, "error": str(e)}


@app.post("/api/chat")
async def chat(request: Request):
    """SSE chat endpoint — streams real progress updates to keep connection alive."""
    body = await request.json()
    query = body.get("query", "")
    conv_id = body.get("conversation_id")
    store = body.get("store_location", "Koramangala, Bangalore")
    history = body.get("history", [])

    if not conv_id:
        conv_id = str(uuid.uuid4())
        title = query[:60] + ("..." if len(query) > 60 else "")
        save_conversation(conv_id, title)

    save_message(conv_id, "user", query)

    def event_stream():
        try:
            # Emit immediately so clients/proxies know stream is alive.
            yield f"data: {json.dumps({'status': 'Brewing your answer...'})}\n\n"
            yield f"data: {json.dumps({'status': 'Understanding question and planning path...'})}\n\n"
            # Run the traced chat pipeline in a single execution context so
            # child spans (router, MAS, weather/calendar, ops) roll up to one trace.
            result = process_chat(query, store, history, conv_id)
            route_tag = result.get("route", "mas")

            # 4. Save and return
            save_message(conv_id, "assistant", result.get("text", ""), trace_id=result.get("trace_id"))

            # Background cache + log
            def _cache_and_log():
                if not is_time_sensitive_query(query):
                    try:
                        embedding = get_embedding(query)
                    except Exception:
                        embedding = None
                    try:
                        save_to_cache(query, result.get("text", ""), embedding, store, result.get("latency_ms", 0))
                    except Exception as e:
                        print(f"[Cache] save error: {e}")
                try:
                    log_inference(result.get("trace_id"), conv_id, store, query, result.get("text", ""),
                        result.get("latency_ms", 0), result.get("input_tokens", 0),
                        result.get("output_tokens", 0), result.get("error"))
                except Exception as e:
                    print(f"[Inference log] error: {e}")
            threading.Thread(target=_cache_and_log, daemon=True).start()

            yield f"data: {json.dumps({'done': True, 'full_text': result.get('text', ''), 'latency_ms': result.get('latency_ms', 0), 'input_tokens': result.get('input_tokens', 0), 'output_tokens': result.get('output_tokens', 0), 'from_cache': False, 'match_type': '', 'similarity': 0, 'matched_question': '', 'route': route_tag})}\n\n"
        except Exception as e:
            err = str(e)
            print(f"[Chat SSE] error: {err}")
            yield f"data: {json.dumps({'done': True, 'full_text': f'Error: {err}', 'latency_ms': 0, 'input_tokens': 0, 'output_tokens': 0, 'from_cache': False, 'match_type': '', 'similarity': 0, 'matched_question': '', 'route': 'error'})}\n\n"

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
# OPERATIONS ADVISOR — Custom Agent (Weather + Calendar + Sales + LLM)
# =============================================================================
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

CITY_COORDS = {
    "bangalore": (12.97, 77.59), "chennai": (13.08, 80.27),
    "mumbai": (19.08, 72.88), "delhi": (28.61, 77.21),
    "hyderabad": (17.39, 78.49), "pune": (18.52, 73.86),
    "kolkata": (22.57, 88.36), "mysuru": (12.30, 76.66),
    "coimbatore": (11.00, 76.96), "kochi": (9.93, 76.27),
    "madurai": (9.92, 78.12), "pondicherry": (11.93, 79.83),
    "vizag": (17.69, 83.22), "ahmedabad": (23.02, 72.57),
    "jaipur": (26.91, 75.79), "chandigarh": (30.73, 76.78),
    "goa": (15.50, 73.83), "dubai": (25.20, 55.27),
    "singapore": (1.35, 103.82), "london": (51.51, -0.13),
    "san francisco": (37.77, -122.42), "kuala lumpur": (3.14, 101.69),
    "sydney": (-33.87, 151.21), "toronto": (43.65, -79.38),
}

INDIAN_FESTIVALS_2026 = {
    "2026-01-14": "Makar Sankranti / Pongal", "2026-01-26": "Republic Day",
    "2026-02-17": "Maha Shivaratri", "2026-03-17": "Holi",
    "2026-03-22": "Ugadi / Gudi Padwa", "2026-03-28": "Ramzan / Eid ul-Fitr",
    "2026-04-02": "Good Friday", "2026-04-06": "Ram Navami",
    "2026-04-14": "Ambedkar Jayanti / Baisakhi", "2026-05-01": "May Day",
    "2026-05-12": "Buddha Purnima", "2026-06-04": "Eid ul-Adha / Bakrid",
    "2026-07-07": "Rath Yatra", "2026-08-15": "Independence Day",
    "2026-08-17": "Janmashtami", "2026-08-26": "Ganesh Chaturthi",
    "2026-09-14": "Onam", "2026-10-02": "Gandhi Jayanti / Navratri Begins",
    "2026-10-11": "Dussehra / Vijayadashami", "2026-10-31": "Diwali",
    "2026-11-01": "Diwali (Day 2) / Govardhan Puja",
    "2026-11-06": "Guru Nanak Jayanti", "2026-12-25": "Christmas",
}

FOUNDATION_MODELS = [
    "databricks-meta-llama-3-3-70b-instruct",
    "databricks-claude-sonnet-4-6",
    "databricks-gpt-5-2",
    "databricks-gemini-3-flash",
    "databricks-llama-4-maverick",
    "databricks-claude-haiku-4-5",
    "databricks-gpt-5-mini",
    "databricks-gemini-2-5-flash",
    "databricks-meta-llama-3-1-8b-instruct",
    "databricks-qwen3-next-80b-a3b-instruct",
    "AI-Days-Gpt-Llama-8020",
]

MONTH_NAME_TO_NUM = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAY_TO_NUM = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_target_date(query: str, now_dt: datetime | None = None) -> str:
    """Resolve planning date from user query; defaults to tomorrow."""
    now_dt = now_dt or datetime.now()
    base = now_dt.date()
    q = " ".join((query or "").lower().split())

    m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", q)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", q)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(20\d{2}))?\b",
        q,
    )
    if m:
        month_name = m.group(1)
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else base.year
        month = MONTH_NAME_TO_NUM[month_name]
        try:
            dt = datetime(year, month, day).date()
            if not m.group(3) and dt < base:
                dt = datetime(year + 1, month, day).date()
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    if "day after tomorrow" in q:
        return (now_dt + timedelta(days=2)).strftime("%Y-%m-%d")
    if "tomorrow" in q:
        return (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in q:
        return now_dt.strftime("%Y-%m-%d")

    m = re.search(r"\bin\s+(\d+)\s+day", q)
    if m:
        return (now_dt + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"\bin\s+(\d+)\s+week", q)
    if m:
        return (now_dt + timedelta(days=7 * int(m.group(1)))).strftime("%Y-%m-%d")

    for wd_name, wd_num in WEEKDAY_TO_NUM.items():
        if f"next {wd_name}" in q:
            delta = (wd_num - base.weekday()) % 7
            if delta == 0:
                delta = 7
            return (now_dt + timedelta(days=delta)).strftime("%Y-%m-%d")
        if f"this {wd_name}" in q:
            delta = (wd_num - base.weekday()) % 7
            return (now_dt + timedelta(days=delta)).strftime("%Y-%m-%d")
        if re.search(rf"\b(on\s+)?{wd_name}\b", q):
            delta = (wd_num - base.weekday()) % 7
            if delta == 0:
                delta = 7
            return (now_dt + timedelta(days=delta)).strftime("%Y-%m-%d")

    llm_date = infer_target_date_with_llm(query, now_dt)
    if llm_date:
        return llm_date

    return (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")


def is_time_sensitive_query(query: str) -> bool:
    """Return True when query meaning depends on target date/time."""
    q = (query or "").lower()
    temporal_tokens = (
        "today", "tomorrow", "day after tomorrow",
        "next ", "this ",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "new year", "nye", "christmas", "eve", "holiday", "festival", "weekend",
    )
    return any(tok in q for tok in temporal_tokens) or bool(
        re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", q)
        or re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", q)
    )


def infer_target_date_with_llm(query: str, now_dt: datetime | None = None) -> str | None:
    """Use a lightweight model to infer a target date from natural language."""
    now_dt = now_dt or datetime.now()
    today = now_dt.strftime("%Y-%m-%d")
    try:
        config = get_admin_config()
        model = config.get("router_model", FOUNDATION_MODELS[0])
        w = _get_workspace_client()
        url = f"{w.config.host.rstrip('/')}/serving-endpoints/{model}/invocations"
        headers = w.config.authenticate()
        headers["Content-Type"] = "application/json"
        prompt = (
            "Infer the user's requested planning date.\n"
            f"Today is {today}.\n"
            "Return ONLY one ISO date in format YYYY-MM-DD. "
            "If no date can be inferred, return UNKNOWN.\n"
            f"User query: {query}"
        )
        resp = http_requests.post(
            url,
            headers=headers,
            json={
                "messages": [
                    {"role": "system", "content": "You extract dates from user text."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 16,
                "temperature": 0,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not content:
            return None
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", content)
        if not match:
            return None
        dt = datetime.fromisoformat(match.group(1))
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"[Date resolver] LLM fallback error: {e}")
        return None

OPS_SYSTEM_PROMPT = """You are the Kaapi Bricks Operations Advisor. You help store managers plan for upcoming days.

You have been given data from three sources:
1. Live weather forecast for the store's city
2. Indian holiday/festival calendar check
3. Historical sales patterns from the store's actual transaction data

Based on ALL this data, generate a preparation plan that includes:
- Weather impact on drink preferences (rain = hot drinks up, cold down; heat = cold drinks up)
- Calendar impact (festivals = family groups, higher avg order; weekends = 2-2.5x volume; Friday = evening spike)
- A product-level forecast TABLE showing: Product | Normal Day | Target Day Estimate | Change % | Action
- Expected total orders and revenue
- Staffing recommendation
- Special notes (rain-proof packaging, festive add-ons, etc.)

IMPORTANT RULES:
- ONLY use numbers from the store data provided. NEVER invent or estimate product quantities if no store data is given.
- If no store data is provided, say "Store data not available — showing weather and calendar analysis only."
- The "nearby_festivals" field shows festivals NEAR the target date, NOT on the target date. Only mention a festival if its date matches the target date exactly (is_holiday=true).
- Be precise about which date you are forecasting for."""


@mlflow.trace(name="get_weather_forecast", span_type="TOOL")
def get_weather_forecast(city: str, target_date: str) -> dict:
    city_lower = city.lower().split(",")[0].strip()
    coords = CITY_COORDS.get(city_lower)
    if not coords:
        for key, val in CITY_COORDS.items():
            if key in city_lower or city_lower in key:
                coords = val
                break

    if not coords or not OPENWEATHER_API_KEY:
        return _weather_fallback(city_lower, target_date)

    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": coords[0], "lon": coords[1], "appid": OPENWEATHER_API_KEY, "units": "metric"}
        resp = http_requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        target_dt = datetime.fromisoformat(target_date)
        target_noon = target_dt.replace(hour=12)
        best_forecast, best_diff = None, float("inf")
        for item in data.get("list", []):
            diff = abs((datetime.fromtimestamp(item["dt"]) - target_noon).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_forecast = item
        if best_forecast:
            weather = best_forecast["weather"][0]
            main = best_forecast["main"]
            return {
                "city": city, "date": target_date,
                "temperature_high": round(main.get("temp_max", main["temp"]), 1),
                "temperature_low": round(main.get("temp_min", main["temp"]), 1),
                "condition": weather["main"], "description": weather["description"],
                "humidity": main.get("humidity", 0), "source": "OpenWeatherMap",
            }
    except Exception as e:
        print(f"Weather API error: {e}")
    return _weather_fallback(city_lower, target_date)


def _weather_fallback(city: str, target_date: str) -> dict:
    month = int(target_date.split("-")[1])
    south = {"bangalore", "chennai", "mysuru", "coimbatore", "kochi", "madurai", "pondicherry", "vizag", "hyderabad"}
    is_south = any(c in city for c in south)
    if month in (6, 7, 8, 9):
        condition, temp, humidity, desc = "Rain", (28 if is_south else 32), 85, "moderate to heavy rain expected"
    elif month in (3, 4, 5):
        condition, temp, humidity, desc = "Clear", (36 if is_south else 40), 45, "hot and sunny"
    elif month in (10, 11):
        condition, temp, humidity, desc = "Cloudy", (29 if is_south else 27), 70, "partly cloudy, occasional showers"
    else:
        condition, temp, humidity, desc = "Clear", (24 if is_south else 15), 55, "pleasant and cool"
    return {"city": city, "date": target_date, "temperature_high": temp, "temperature_low": temp - 7,
            "condition": condition, "description": desc, "humidity": humidity, "source": "seasonal_estimate"}


@mlflow.trace(name="check_calendar", span_type="TOOL")
def check_calendar(target_date: str) -> dict:
    dt = datetime.fromisoformat(target_date)
    day_name = dt.strftime("%A")
    holiday_name = INDIAN_FESTIVALS_2026.get(target_date)
    nearby = []
    for offset in range(-3, 4):
        check_date = (dt + timedelta(days=offset)).strftime("%Y-%m-%d")
        fest = INDIAN_FESTIVALS_2026.get(check_date)
        if fest and check_date != target_date:
            nearby.append({"date": check_date, "festival": fest, "days_away": offset})
    return {
        "date": target_date, "day_of_week": day_name,
        "is_weekend": day_name in ("Saturday", "Sunday"), "is_friday": day_name == "Friday",
        "is_holiday_on_this_date": holiday_name is not None,
        "holiday_name_on_this_date": holiday_name,
        "nearby_festivals_NOT_on_this_date": [{"date": n["date"], "festival": n["festival"], "days_away": n["days_away"]} for n in nearby],
        "summary": "This date ({}) is a {}.{}{}".format(
            target_date, day_name,
            " It IS a holiday: {}.".format(holiday_name) if holiday_name else " It is NOT a holiday.",
            " Note: {} is {} day(s) away but NOT on this date.".format(nearby[0]["festival"], abs(nearby[0]["days_away"])) if nearby else ""
        ),
    }


@mlflow.trace(name="ops_advisor_call", span_type=SpanType.AGENT)
def run_ops_advisor(query: str, store: str, model_endpoint: str, target_date: str | None = None) -> dict:
    """Run the Operations Advisor: weather + calendar context, then call selected LLM.
    Data queries (sales, inventory, products) go through MAS/Genie, not here."""
    target_date = target_date or resolve_target_date(query)
    city = store.split(",")[-1].strip() if "," in store else store

    # Call weather + calendar tools only
    weather = get_weather_forecast(city, target_date)
    calendar = check_calendar(target_date)

    # Build context
    context = f"""## Planning Target Date (resolved from user request)
{target_date}

## Context for {store} — {target_date} ({calendar['day_of_week']})

### Weather Forecast
{json.dumps(weather, indent=2)}

### Calendar
{json.dumps(calendar, indent=2)}
"""

    # Call selected LLM
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{model_endpoint}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    system_prompt = OPS_SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{query}\n\n---\n{context}"},
    ]

    start_time = time.time()
    try:
        resp = http_requests.post(url, headers=headers,
            json={"messages": messages, "max_tokens": 2000, "temperature": 0.3}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start_time) * 1000
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        usage = data.get("usage", {})
        return {
            "text": answer, "latency_ms": latency_ms, "model": model_endpoint,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "weather": weather, "calendar": calendar, "error": None,
        }
    except Exception as e:
        return {"text": f"Error: {e}", "latency_ms": (time.time() - start_time) * 1000,
                "model": model_endpoint, "input_tokens": 0, "output_tokens": 0,
                "weather": weather, "calendar": calendar, "error": str(e)}


# =============================================================================
# ADMIN CONFIG ENDPOINTS
# =============================================================================
@app.get("/api/admin/config")
def get_config():
    return get_admin_config()


@app.post("/api/admin/config")
async def save_config(request: Request):
    body = await request.json()
    for key in ("router_model", "operations_model"):
        if key in body:
            set_admin_config(key, body[key])
    return {"ok": True, "config": get_admin_config()}


# =============================================================================
# OPERATIONS ADVISOR API ENDPOINTS
# =============================================================================
@app.get("/api/models")
def get_models():
    return {"models": FOUNDATION_MODELS}


@app.post("/api/ops-advisor")
async def ops_advisor_endpoint(request: Request):
    body = await request.json()
    query = body.get("query", "What should I prepare for tomorrow?")
    store = body.get("store_location", "Koramangala, Bangalore")
    model = body.get("model", FOUNDATION_MODELS[0])
    config = get_admin_config()
    router_model = config.get("router_model", FOUNDATION_MODELS[0])
    intent = extract_query_intent(query, router_model)
    result = run_ops_advisor(query, store, model, target_date=intent.get("target_date"))
    return result


def _compare_cache_key(query: str, target_date: str | None) -> str:
    """Scope compare cache by normalized date context."""
    return f"{query.strip()} || target_date:{target_date or 'none'}"


def _run_ops_with_data_cached(query, store, model, mas_data, target_date=None):
    """Run Operations Advisor with MAS data + cache check. No MLflow tracing (runs in background thread)."""
    cache_key = _compare_cache_key(query, target_date)
    cached = find_compare_cache(cache_key, model, store)
    if cached:
        cached["model"] = model
        return cached
    # Call the LLM directly (skip traced function to avoid thread/trace conflicts)
    result = _call_ops_advisor_raw(query, store, model, mas_data, target_date=target_date)
    # Cache in background
    try:
        save_compare_cache(cache_key, result.get("text", ""), model, store, result.get("latency_ms", 0),
            result.get("input_tokens", 0), result.get("output_tokens", 0),
            result.get("weather"), result.get("calendar"))
    except Exception as e:
        print(f"[Compare cache] save error: {e}")
    return result


def _call_ops_advisor_raw(query, store, model_endpoint, mas_data, target_date=None):
    """Raw ops advisor call without MLflow tracing — safe for background threads."""
    target_date = target_date or resolve_target_date(query)
    city = store.split(",")[-1].strip() if "," in store else store

    # Get weather (use fallback directly to avoid MLflow trace in thread)
    weather = _weather_fallback(city.lower(), target_date)
    # Get calendar directly
    dt = datetime.fromisoformat(target_date)
    day_name = dt.strftime("%A")
    holiday_name = INDIAN_FESTIVALS_2026.get(target_date)
    nearby = []
    for offset in range(-3, 4):
        check_date = (dt + timedelta(days=offset)).strftime("%Y-%m-%d")
        fest = INDIAN_FESTIVALS_2026.get(check_date)
        if fest and check_date != target_date:
            nearby.append({"date": check_date, "festival": fest, "days_away": offset})
    calendar = {
        "date": target_date, "day_of_week": day_name,
        "is_weekend": day_name in ("Saturday", "Sunday"), "is_friday": day_name == "Friday",
        "is_holiday_on_this_date": holiday_name is not None,
        "holiday_name_on_this_date": holiday_name,
        "nearby_festivals_NOT_on_this_date": nearby,
        "summary": "This date ({}) is a {}.{}".format(target_date, day_name,
            " It IS a holiday: {}.".format(holiday_name) if holiday_name else " It is NOT a holiday.")
    }

    context = f"""## Planning Target Date (resolved from user request)\n{target_date}\n\n## Store Data (from analytics):\n{mas_data}\n\n## Weather Forecast for {target_date}:\n{json.dumps(weather, indent=2)}\n\n## Calendar for {target_date}:\n{json.dumps(calendar, indent=2)}"""

    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{model_endpoint}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    messages = [{"role": "system", "content": OPS_SYSTEM_PROMPT}, {"role": "user", "content": f"{query}\n\n---\n{context}"}]

    start_time = time.time()
    try:
        resp = http_requests.post(url, headers=headers,
            json={"messages": messages, "max_tokens": 2000, "temperature": 0.3}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start_time) * 1000
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        usage = data.get("usage", {})
        return {"text": answer, "latency_ms": latency_ms, "model": model_endpoint,
                "input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0),
                "weather": weather, "calendar": calendar, "error": None}
    except Exception as e:
        return {"text": f"Error: {e}", "latency_ms": (time.time() - start_time) * 1000,
                "model": model_endpoint, "input_tokens": 0, "output_tokens": 0,
                "weather": weather, "calendar": calendar, "error": str(e)}


@mlflow.trace(name="compare_request", span_type=SpanType.AGENT)
def process_compare(query: str, store: str, model_a: str, model_b: str) -> dict:
    """Single-trace compare flow: MAS once, then model A/B sequentially."""
    target_date = resolve_target_date(query) if is_time_sensitive_query(query) else None
    cache_key = _compare_cache_key(query, target_date)

    # 1) MAS once for shared analytics context
    mas_data_query = (
        f"For the {store} store, show me: top selling products with quantities, "
        "current inventory levels for key ingredients, recent daily order counts and revenue, "
        "and any active promotions."
    )
    mas_messages = [{"role": "user", "content": mas_data_query}]
    mas_result = call_mas_sync(mas_messages, store)
    mas_data = mas_result.get("text", "")

    def run_one(model_endpoint: str) -> dict:
        cached = find_compare_cache(cache_key, model_endpoint, store)
        if cached:
            cached["model"] = model_endpoint
            return cached
        result = run_ops_advisor_with_data(
            query, store, model_endpoint, mas_data, target_date=target_date
        )
        try:
            save_compare_cache(
                cache_key,
                result.get("text", ""),
                model_endpoint,
                store,
                result.get("latency_ms", 0),
                result.get("input_tokens", 0),
                result.get("output_tokens", 0),
                result.get("weather"),
                result.get("calendar"),
            )
        except Exception as e:
            print(f"[Compare cache] save error: {e}")
        return result

    # Sequential by design to keep one parent trace with clean nested spans.
    result_a = run_one(model_a)
    result_b = run_one(model_b)

    return {
        "ok": True,
        "target_date": target_date,
        "result": {"model_a": result_a, "model_b": result_b},
    }


@app.post("/api/ops-advisor/compare")
async def ops_advisor_compare(request: Request):
    """JSON endpoint — calls MAS once, then both models in parallel."""
    body = await request.json()
    query = body.get("query", "What should I prepare for tomorrow?")
    store = body.get("store_location", "Koramangala, Bangalore")
    model_a = body.get("model_a") or FOUNDATION_MODELS[0]
    # Allow compare to work even when only one model is configured in UI.
    model_b = body.get("model_b") or model_a
    try:
        return process_compare(query, store, model_a, model_b)
    except Exception as e:
        err = str(e)
        print(f"[Compare] error: {err}")
        fallback = {
            "model_a": {"text": f"Error: {err}", "model": model_a, "latency_ms": 0, "input_tokens": 0, "output_tokens": 0, "error": err},
            "model_b": {"text": f"Error: {err}", "model": model_b, "latency_ms": 0, "input_tokens": 0, "output_tokens": 0, "error": err},
        }
        return JSONResponse({"ok": False, "result": fallback, "error": err}, status_code=500)


# Serve static files and index.html
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r") as f:
        return f.read()


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
