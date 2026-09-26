"""
Kaapi Bricks Strategic Analyst — agent definition.
Follows the official Databricks OpenAI Agents SDK template structure.
"""
import logging
import os
import time

import mlflow
from agents import Agent, function_tool, set_default_openai_api, set_default_openai_client
from agents.tracing import set_trace_processors
from databricks_openai import AsyncDatabricksOpenAI

logger = logging.getLogger(__name__)

# ── SDK + MLflow setup (template pattern) ────────────────────────────────────
# NOTE: this works for all Databricks models except GPT-OSS (different API shape)
set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])  # only use MLflow for trace processing
mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

MODEL = os.environ.get("KAAPI_MODEL", "databricks-gpt-5-4")
GENIE_SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"


# ── Tool 1: Genie — ALL internal business data ────────────────────────────────

@function_tool
def ask_genie(question: str) -> str:
    """Query Kaapi Bricks business data using plain English.

    Connects to the Kaapi Bricks Analytics Genie space which covers:
    stores, sales, orders, order items, products, customers, inventory,
    ingredients, suppliers, promotions, and purchase orders.

    Ask ANY business data question in plain English — Genie writes and runs
    the SQL automatically. You never write SQL yourself.

    Call this 2-3 times with focused questions to build a complete picture.

    Examples:
    - "What are the top 5 stores by total revenue?"
    - "Which products have declining sales over the last 3 months?"
    - "How many repeat customers do we have in each city?"
    - "What is current inventory level for Arabica beans across all stores?"
    - "Which promotions had the highest redemption rate?"
    - "What is average order value by store?"
    """
    from databricks.sdk import WorkspaceClient

    try:
        w = WorkspaceClient()

        # w.api_client.do() handles OAuth scopes internally.
        # Direct requests with X-Forwarded-Access-Token fail ("required scopes: genie")
        # because user tokens lack the genie scope. SDK requests it automatically.
        data = w.api_client.do(
            "POST",
            f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation",
            body={"content": question},
        )

        conversation_id = data.get("conversation_id") or data.get("id")
        message_id = (
            data.get("message_id")
            or (data.get("messages") or [{}])[0].get("id")
            or data.get("id")
        )

        if not conversation_id:
            return f"Genie: no conversation_id in response: {str(data)[:300]}"

        # Poll for completion (max 90s, 2s intervals)
        for _ in range(45):
            time.sleep(2)
            msg = w.api_client.do(
                "GET",
                f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}",
            )
            status = msg.get("status", "")

            if status == "COMPLETED":
                parts = []
                for att in (msg.get("attachments") or []):
                    text_block = att.get("text") or {}
                    if text_block.get("content"):
                        parts.append(text_block["content"])
                    query_block = att.get("query") or {}
                    if query_block.get("description"):
                        parts.append(f"Query: {query_block['description']}")
                    result = query_block.get("result") or {}
                    sr = result.get("statement_response") or {}
                    schema = sr.get("manifest", {}).get("schema", {}).get("columns", [])
                    cols = [c.get("name", "") for c in schema]
                    rows = sr.get("result", {}).get("data_array", [])
                    if cols and rows:
                        parts.append(" | ".join(cols))
                        parts.append("-" * 60)
                        for row in rows[:25]:
                            parts.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
                        if len(rows) > 25:
                            parts.append(f"... {len(rows)} total rows")
                return "\n".join(parts) if parts else f"Genie returned no data for: {question}"

            elif status in ("FAILED", "CANCELLED", "ERROR"):
                err = msg.get("error") or msg.get("error_message") or status
                return f"Genie query failed ({status}): {err}"

        return f"Genie timeout: '{question}' did not complete in 90 seconds"

    except Exception as e:
        logger.error(f"ask_genie error: {e}", exc_info=True)
        return f"Genie unavailable: {type(e).__name__}: {e}"


# ── Tool 2: Competitor + market intelligence ──────────────────────────────────

@function_tool
def research_competitor(query: str) -> str:
    """Search the internet for competitive intelligence and market trends.

    Use for external information that Genie cannot answer:
    - Competitor activity: Blue Tokai, Third Wave Coffee, Starbucks India,
      Cafe Coffee Day, Araku Coffee, Brewing Thoughts, etc.
    - Market expansion: which cities are growing for premium café culture
    - Consumer trends: what coffee drinkers in India want right now
    - Real estate / footfall: new tech parks, residential corridors, malls
    - Industry reports: F&B market in India, café sector growth
    - Festival or seasonal campaigns competitors are running

    Do NOT use for Kaapi Bricks internal data — use ask_genie for that.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=6))
        if not results:
            return f"No web results for: {query}"
        lines = [f"Web research — '{query}':\n"]
        for i, r in enumerate(results, 1):
            lines.extend([
                f"{i}. {r.get('title', '')}",
                f"   {r.get('body', '')[:350]}",
                f"   {r.get('href', '')}",
                "",
            ])
        return "\n".join(lines)
    except Exception as e:
        return f"Web search unavailable: {e}"


# ── Agent instructions ────────────────────────────────────────────────────────

INSTRUCTIONS = """You are the Kaapi Bricks Strategic Analyst — senior business advisor
for a premium South Indian filter coffee chain with 37 stores across India and
internationally (Dubai, Singapore, London, NYC).

YOU HAVE TWO TOOLS:
1. ask_genie — for ALL internal Kaapi Bricks data. Ask in plain English.
   You can call this 2-3 times with different focused questions.
2. research_competitor — for external market intelligence, competitor news,
   and city/demographic trends. Call once or twice with focused queries.

HOW TO ANSWER STRATEGIC QUESTIONS:

  Step 1 → ask_genie with a precise business question to get internal data
  Step 2 → ask_genie again if you need a different angle or follow-up data
  Step 3 → research_competitor if the question involves competitors, expansion,
            market trends, or external signals
  Step 4 → Synthesise: combine internal numbers + external context

ANSWER FORMAT:
  → Recommendation (lead with this — what should they do?)
  → Evidence (what do the numbers say? cite specific figures from Genie)
  → External context (what does the market/competitor research show?)
  → Risks (what could go wrong?)
  → Next steps (concrete actions)

RULES:
  - Never invent or guess numbers. Only cite figures returned by ask_genie.
  - Never write SQL. ask_genie handles all data queries.
  - Be specific: name stores, cities, products, INR amounts.
  - If Genie returns no data, say so clearly."""


def create_agent() -> Agent:
    return Agent(
        name="Kaapi Bricks Strategic Analyst",
        instructions=INSTRUCTIONS,
        model=MODEL,
        tools=[ask_genie, research_competitor],
    )
