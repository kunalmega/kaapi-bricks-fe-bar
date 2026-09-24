"""
Kaapi Bricks Strategic Analyst — FastAPI server.

Follows the official Databricks OpenAI Agents SDK template pattern exactly:

  NON-STREAMING (stream=false, default):
    Input:  request.input → [i.model_dump() for i in request.input]
    Run:    await Runner.run(agent, messages)
    Output: {"output": [item.to_input_item().model_dump() for item in result.new_items]}
    ↑ This is what MAS calls — it sends stream=false and reads the JSON response.

  STREAMING (stream=true):
    Input:  same message list
    Run:    Runner.run_streamed(agent, input=messages)
    Output: process_agent_stream_events(result.stream_events()) → SSE Responses API events
    ↑ This is what the browser UI calls.

/invocations  — both modes (MAS uses non-streaming, browser uses streaming)
/health       — uptime check
/             — browser chat UI
"""
import json
import logging
import os
import uuid

import mlflow
from agents import Runner
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

# Import agent module — registers tools and configures SDK + MLflow autolog
import agent_server.agent  # noqa: F401
from agent_server.agent import MODEL, create_agent
from agent_server.utils import process_agent_stream_events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── MLflow experiment ─────────────────────────────────────────────────────────
try:
    mlflow.set_tracking_uri("databricks")
    _exp_id = os.environ.get("MLFLOW_EXPERIMENT_ID", "1449787236083664")
    mlflow.set_experiment(experiment_id=_exp_id)
    logger.info(f"MLflow experiment: {_exp_id}")
except Exception as e:
    logger.warning(f"MLflow experiment setup failed: {e}")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Kaapi Bricks Strategic Analyst")


@app.exception_handler(Exception)
async def global_err(request: Request, exc: Exception):
    logger.error(f"{request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "kaapi-strategic-analyst", "model": MODEL}


# ── Browser UI ────────────────────────────────────────────────────────────────

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kaapi Bricks — Strategic Analyst</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f5f0eb; display: flex; flex-direction: column; height: 100vh; }
    header { background: #4a2c0a; color: #fff; padding: 16px 24px;
             display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
    header h1 { font-size: 18px; font-weight: 700; }
    header .sub { font-size: 11px; color: #c8a882; margin-top: 2px; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 20px;
             background: #fff; border-bottom: 1px solid #f0e8dc; flex-shrink: 0; }
    .chip { padding: 5px 12px; background: #f5f0eb; border: 1px solid #d0b8a0;
            border-radius: 16px; font-size: 12px; color: #4a2c0a; cursor: pointer; }
    .chip:hover { background: #ede0d4; }
    #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex;
            flex-direction: column; gap: 14px; }
    .msg { max-width: 80%; padding: 12px 16px; border-radius: 12px;
           font-size: 14px; line-height: 1.6; }
    .msg.user { background: #4a2c0a; color: #fff; align-self: flex-end;
                border-radius: 12px 12px 2px 12px; }
    .msg.agent { background: #fff; color: #1a1a1a; align-self: flex-start;
                 box-shadow: 0 1px 6px rgba(0,0,0,0.1); border: 1px solid #f0e8dc;
                 border-radius: 12px 12px 12px 2px; }
    .msg.agent p { margin: 5px 0; }
    .msg.agent ul { margin: 5px 0 5px 18px; }
    .msg.agent h3 { font-size: 13px; font-weight: 700; color: #4a2c0a;
                    border-left: 3px solid #c8a882; padding-left: 8px; margin: 8px 0 4px; }
    .msg.agent strong { color: #2d1a0a; }
    .msg.thinking { background: #fff8f0; color: #aaa; font-style: italic;
                    font-size: 13px; align-self: flex-start; border-radius: 8px;
                    padding: 8px 14px; }
    .form-row { display: flex; gap: 8px; padding: 14px 20px;
                background: #fff; border-top: 1px solid #e8d8c8; flex-shrink: 0; }
    textarea { flex: 1; border: 1px solid #d0b8a0; border-radius: 8px; padding: 10px 12px;
               font-size: 14px; resize: none; height: 44px; font-family: inherit; outline: none; }
    textarea:focus { border-color: #4a2c0a; }
    button { background: #4a2c0a; color: #fff; border: none; border-radius: 8px;
             padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; }
    button:hover { background: #6b3d0f; }
    button:disabled { background: #ccc; cursor: not-allowed; }
  </style>
</head>
<body>
  <header>
    <span style="font-size:24px">&#128202;</span>
    <div>
      <h1>Kaapi Bricks — Strategic Analyst</h1>
      <div class="sub">Genie data + competitive research · OpenAI Agents SDK · Databricks Apps</div>
    </div>
  </header>
  <div class="chips">
    <div class="chip" onclick="ask('Where should we open our next store?')">Next store location</div>
    <div class="chip" onclick="ask('Which stores are underperforming and why?')">Underperforming stores</div>
    <div class="chip" onclick="ask('What new drink should we launch for monsoon?')">New product idea</div>
    <div class="chip" onclick="ask('How are Blue Tokai and Third Wave expanding in India?')">Competitor intel</div>
    <div class="chip" onclick="ask('What are our top 5 revenue stores?')">Top stores</div>
  </div>
  <div id="chat"></div>
  <div class="form-row">
    <textarea id="inp" placeholder="Ask a strategic question about Kaapi Bricks..."
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"></textarea>
    <button id="btn" onclick="send()">Ask</button>
  </div>
  <script>
    marked.setOptions({ breaks: true, gfm: true });
    const chat = document.getElementById('chat');
    const inp  = document.getElementById('inp');
    const btn  = document.getElementById('btn');

    function ask(q) { inp.value = q; send(); }

    function addMsg(html, cls, md) {
      const d = document.createElement('div');
      d.className = 'msg ' + cls;
      d.innerHTML = md ? marked.parse(html) : html;
      chat.appendChild(d);
      chat.scrollTop = 9999;
      return d;
    }

    async function send() {
      const q = inp.value.trim();
      if (!q || btn.disabled) return;
      inp.value = ''; btn.disabled = true;
      addMsg(q, 'user', false);
      const thinking = addMsg('Analysing with Genie + web research...', 'thinking', false);

      try {
        const res = await fetch('/invocations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            input: [{ type: 'message', role: 'user', content: q }],
            stream: true
          })
        });
        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let text = '';
        thinking.remove();
        const msgEl = addMsg('', 'agent', false);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          for (const line of decoder.decode(value).split('\\n')) {
            if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;
            try {
              const d = JSON.parse(line.slice(6));
              // Responses API SSE: type=response.output_text.delta carries text tokens
              if (d?.type === 'response.output_text.delta' && d.delta) {
                text += d.delta;
                msgEl.innerHTML = marked.parse(text);
                chat.scrollTop = 9999;
              }
            } catch(e) {}
          }
        }
        if (!text) msgEl.textContent = 'No response received.';
      } catch(e) {
        thinking.remove();
        addMsg('Error: ' + e.message, 'agent', false);
      }
      btn.disabled = false;
    }
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return CHAT_HTML


# ── /invocations — dual mode, following template pattern exactly ──────────────

@app.post("/invocations")
async def invocations(request: Request):
    """
    NON-STREAMING (stream=false or omitted) — what MAS uses:
      Mirrors template @invoke() handler:
        messages = [i.model_dump() for i in request.input]
        result   = await Runner.run(agent, messages)
        output   = [item.to_input_item().model_dump() for item in result.new_items]

    STREAMING (stream=true) — what the browser uses:
      Mirrors template @stream() handler:
        result = Runner.run_streamed(agent, input=messages)
        yield each event from process_agent_stream_events(result.stream_events())
    """
    body = await request.json()
    logger.info(f"/invocations stream={body.get('stream', False)}")

    # ── Build message list — template pattern: [i.model_dump() for i in request.input]
    # We receive JSON dicts already, so this is just body["input"] as-is.
    # Handles both ResponsesAgentRequest format (input=[]) and chat format (messages=[]).
    raw_input = body.get("input") or body.get("messages") or []

    # Normalise: ensure each item is a plain dict with at minimum role + content
    messages = []
    for item in raw_input:
        if isinstance(item, dict):
            messages.append(item)
        else:
            # pydantic model — shouldn't happen in HTTP context but be safe
            messages.append(item.model_dump() if hasattr(item, "model_dump") else dict(item))

    if not messages:
        return JSONResponse(status_code=400, content={"error": "no input messages"})

    # Optionally tag the trace with session/conversation ID
    try:
        ctx = body.get("context") or {}
        session_id = (ctx.get("conversation_id") if isinstance(ctx, dict) else None) or \
                     (body.get("custom_inputs") or {}).get("session_id")
        if session_id:
            mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    except Exception:
        pass

    wants_stream = body.get("stream", False)

    # ── NON-STREAMING: mirrors @invoke() ─────────────────────────────────────
    if not wants_stream:
        import time as _time
        try:
            agent = create_agent()
            result = await Runner.run(agent, messages, max_turns=20)

            # Filter to ONLY message-type items.
            # result.new_items also contains function_call + function_call_output items
            # (our internal tool steps). If we return those, MAS streams them back as
            # pending tool calls — the client gets function_call JSON it can't render.
            output = []
            for item in result.new_items:
                try:
                    d = item.to_input_item()
                    serialized = d.model_dump() if hasattr(d, "model_dump") else dict(d)
                    if serialized.get("type") == "message":
                        output.append(serialized)
                except Exception as e:
                    logger.warning(f"to_input_item() skipped {type(item).__name__}: {e}")

            return JSONResponse({
                "id": f"resp-{uuid.uuid4().hex[:16]}",
                "object": "response",
                "created_at": int(_time.time()),
                "status": "completed",
                "model": MODEL,
                "output": output,
            })
        except Exception as e:
            logger.error(f"invoke error: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ── STREAMING: mirrors @stream() ─────────────────────────────────────────
    async def stream_gen():
        try:
            agent = create_agent()
            result = Runner.run_streamed(agent, input=messages, max_turns=20)
            async for event in process_agent_stream_events(result.stream_events()):
                ev_type = event.get("type", "")
                # Only forward text-content events.
                # Function call / tool output events (response.output_item.done with
                # type=function_call, response.function_call_arguments.*, etc.) are
                # internal agent steps — if MAS sees them it tries to re-execute our
                # private tools and the client fails schema validation.
                if ev_type.startswith("response.output_text"):
                    yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"stream error: {e}", exc_info=True)
            err = {"type": "response.output_text.delta", "delta": f"\n\nError: {e}",
                   "item_id": "err", "output_index": 0, "content_index": 0}
            yield f"data: {json.dumps(err)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.post("/responses")
async def responses_alias(request: Request):
    """Alias — some callers use /responses."""
    return await invocations(request)
