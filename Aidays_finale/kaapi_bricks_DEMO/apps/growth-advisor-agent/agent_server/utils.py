"""Utility helpers — copied from the official Databricks OpenAI Agents SDK template."""
import logging
from typing import AsyncGenerator, AsyncIterator, Optional
from uuid import uuid4

from agents.result import StreamEvent
from databricks.sdk import WorkspaceClient


def get_databricks_host(workspace_client: WorkspaceClient | None = None) -> Optional[str]:
    workspace_client = workspace_client or WorkspaceClient()
    try:
        return workspace_client.config.host
    except Exception as e:
        logging.exception(f"Error getting databricks host: {e}")
        return None


def build_mcp_url(path: str, workspace_client: WorkspaceClient | None = None) -> str:
    if not path.startswith("/"):
        return path
    hostname = get_databricks_host(workspace_client)
    return f"{hostname}{path}"


def get_user_workspace_client() -> WorkspaceClient:
    """Return a WorkspaceClient authenticated as the forwarded user (on-behalf-of)."""
    try:
        from mlflow.genai.agent_server import get_request_headers
        token = get_request_headers().get("x-forwarded-access-token")
    except ImportError:
        token = None
    return WorkspaceClient(token=token, auth_type="pat") if token else WorkspaceClient()


async def process_agent_stream_events(
    async_stream: AsyncIterator[StreamEvent],
) -> AsyncGenerator[dict, None]:
    """Convert openai-agents stream events to Responses API SSE dicts.

    Matches the official Databricks template pattern. Always yields plain dicts
    so the caller can json.dumps() without special handling.
    """
    curr_item_id = str(uuid4())
    async for event in async_stream:
        if event.type == "raw_response_event":
            event_data = event.data.model_dump() if hasattr(event.data, "model_dump") else {}
            if event_data.get("type") == "response.output_item.added":
                curr_item_id = str(uuid4())
                if event_data.get("item") and event_data["item"].get("id") is not None:
                    event_data["item"]["id"] = curr_item_id
            elif event_data.get("item") is not None and event_data["item"].get("id") is not None:
                event_data["item"]["id"] = curr_item_id
            elif event_data.get("item_id") is not None:
                event_data["item_id"] = curr_item_id
            yield event_data
        elif event.type == "run_item_stream_event" and event.item.type == "tool_call_output_item":
            item = event.item.to_input_item()
            yield {
                "type": "response.output_item.done",
                "item": item.model_dump() if hasattr(item, "model_dump") else dict(item),
            }
