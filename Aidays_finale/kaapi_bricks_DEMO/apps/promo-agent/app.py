"""
Kaapi Bricks Promotional Creative Agent
Specialist creative agent with 4 distinct capabilities:
  1. Market research (web trends + competitor intelligence)
  2. Creative brief synthesis (reasoning → emotional angle + visual direction)
  3. Copy writing (headline, subline, body, CTA, hashtags)
  4. Image generation (GPT via Databricks Responses API)

NO SQL tools — analytics data comes from Genie via the MAS supervisor.
Designed to be called standalone OR as a MAS agent endpoint.
"""
import os
import json
import logging
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
from agents.tracing import set_trace_processors
from databricks_openai import AsyncDatabricksOpenAI
import mlflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])
mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

MODEL = os.environ.get("KAAPI_MODEL", "databricks-gpt-5-4")


def _get_headers_and_host():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    auth = dict(w.config.authenticate())
    host = (w.config.host or "").rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return {**auth, "Content-Type": "application/json"}, host


# ── The 4 tools ────────────────────────────────────────────────────────────────

@function_tool
def research_trends(query: str) -> str:
    """Search the internet for market intelligence relevant to a promotional campaign.

    Use this for:
    - Current food & beverage trends for the product/season
    - Competitor campaigns (Blue Tokai, Third Wave, Starbucks India, Café Coffee Day)
    - Cultural moments, festivals, seasonal events in India
    - Instagram aesthetics and visual trends in F&B
    - Consumer sentiment around a product category

    Call this 2-3 times with different focused queries for rich research.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=6))
        if not results:
            return f"No results for '{query}'. Use this to reason about the category instead."
        lines = [f"Research results — '{query}':\n"]
        for i, r in enumerate(results, 1):
            lines.extend([
                f"{i}. {r.get('title','')}",
                f"   {r.get('body','')[:350]}",
                f"   Source: {r.get('href','')}", ""
            ])
        return "\n".join(lines)
    except Exception as e:
        return f"Web search unavailable ({e}). Use category knowledge to reason about trends."


@function_tool
def generate_image(
    image_prompt: str,
    format_type: str,
    emotional_tone: str
) -> str:
    """Generate a promotional image using GPT image generation on Databricks.

    image_prompt: Detailed scene description — be specific about:
      - Subject (the drink, ingredients, setting)
      - Lighting (golden hour, harsh summer sun, soft monsoon light, etc.)
      - Background/environment (terrace, café interior, street stall, market)
      - Color palette (warm browns, cool blues, earthy greens, etc.)
      - Cultural props (davara-tumbler, filter, brass vessels, jaggery block, etc.)
      - Mood (nostalgic, premium, joyful, soulful, energetic)
      - Composition (close-up, hero shot, lifestyle, flat lay)

    format_type: 'instagram' (9:16 portrait) or 'poster' (16:9 landscape)
    emotional_tone: core emotion — 'nostalgia', 'comfort', 'energy', 'romance', 'pride', 'relief'

    Returns: base64 JPEG image data prefixed with IMAGE_B64:
    """
    import requests as req
    headers, host = _get_headers_and_host()
    aspect = "1024x1536" if format_type == "instagram" else "1536x1024"

    full_prompt = (
        f"Professional promotional photography for Kaapi Bricks, a premium South Indian filter coffee brand. "
        f"Emotional tone: {emotional_tone}. "
        f"Visual direction: {image_prompt}. "
        f"Photography style: warm cinematic food photography, rich textures, premium editorial aesthetic. "
        f"South Indian heritage meets modern premium café culture. "
        f"{'Portrait 9:16 for Instagram' if format_type == 'instagram' else 'Landscape 16:9 for store poster'}. "
        f"No text overlays — clean image for design placement."
    )

    try:
        resp = req.post(
            f"{host}/serving-endpoints/responses",
            headers=headers,
            json={
                "model": "databricks-gpt-5-5-pro",
                "input": full_prompt,
                "tools": [{"type": "image_generation", "output_format": "jpeg",
                            "quality": "medium", "size": aspect}]
            },
            timeout=120
        )
        if resp.status_code == 200:
            for item in resp.json().get("output", []):
                if item.get("type") == "image_generation_call":
                    return f"IMAGE_B64:{item.get('result','')}"
            return f"ERROR: Unexpected response structure: {[i.get('type') for i in resp.json().get('output',[])]}"
        return f"ERROR: HTTP {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ── Agent ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Kaapi Bricks Promotional Creative Agent — a specialist creative director for a premium South Indian filter coffee chain with 37 stores across India and internationally.

You have exactly 4 capabilities:
1. research_trends — web research on market trends, competitor campaigns, cultural moments
2. Creative brief synthesis — reason from research + product context to define the campaign strategy
3. Copy writing — write headline, subline, body, CTA, hashtags
4. generate_image — create the promotional visual

IMPORTANT: You do NOT query sales data or inventory. If the user provides sales context or customer data in their message (passed from the analytics agent), use that context. If not, reason from your knowledge of the brand and market.

Follow this EXACT reasoning chain every time:

## STEP 1: Market Research
Run research_trends 2-3 times with targeted queries:
- Query 1: Current trends for this product category + season in India
- Query 2: Competitor campaign patterns (Blue Tokai, Third Wave, Starbucks India)
- Query 3: Cultural/seasonal context (festivals, weather events, consumer mindset)

## STEP 2: Creative Brief Synthesis
Based ONLY on research findings + product context provided, define:
- **Core insight** (one sentence — the human truth this campaign ladders up to)
- **Emotional angle** (choose: nostalgia / comfort / energy / pride / romance / adventure / relief)
- **Visual direction** (specific scene — lighting, setting, props, color palette)
- **Tone of voice** (warm / bold / poetic / playful / premium / earthy)
- **What makes this uniquely Kaapi Bricks** (not generic coffee)

## STEP 3: Copy Creation
Write all copy elements:
- **Headline**: max 6 words, punchy, no generic coffee clichés
- **Subline**: max 12 words, emotional resonance
- **Body copy**: 2-3 sentences, storytelling, South Indian cultural cues
- **CTA**: max 5 words, action-oriented
- **Hashtags**: 6-8 relevant hashtags

## STEP 4: Image Generation
Call generate_image with:
- A detailed, vivid scene description (not just "coffee cup" — describe the whole world)
- Include specific South Indian cultural props and settings
- Match the emotional angle and visual direction from Step 2

## STEP 5: Campaign Recommendation
Conclude with:
- Which type of stores to pilot (based on product fit — e.g. urban millennial areas for cold brew)
- Best posting time on Instagram
- Suggested pairing offers or in-store activation
- Story/reel adaptation idea

Always be specific. Never invent sales numbers. If user provides data context, cite it explicitly."""


def create_agent() -> Agent:
    return Agent(
        name="Kaapi Bricks Promotional Creative Agent",
        instructions=SYSTEM_PROMPT,
        model=MODEL,
        tools=[research_trends, generate_image],
    )


# ── Streaming with step events ─────────────────────────────────────────────────

TOOL_META = {
    "research_trends": ("🔍", "Researching market trends"),
    "generate_image": ("🎨", "Generating promotional image"),
}

async def stream_agent(product: str, occasion: str, format_type: str,
                        data_context: str = "") -> AsyncGenerator[str, None]:
    agent = create_agent()

    context_block = f"\n\nAnalytics context provided:\n{data_context}" if data_context else ""
    user_msg = (
        f"Create a complete promotional campaign for:\n"
        f"Product: {product}\n"
        f"Occasion/Theme: {occasion}\n"
        f"Format: {format_type} ({'Instagram 9:16 portrait' if format_type == 'instagram' else 'Store poster landscape'})"
        f"{context_block}\n\n"
        f"Follow all 5 steps in your reasoning chain."
    )

    result = Runner.run_streamed(agent, user_msg)
    image_b64 = None
    full_text = ""
    current_tool = None

    async for event in result.stream_events():
        if event.type == "raw_response_event":
            data = event.data.model_dump() if hasattr(event.data, "model_dump") else {}
            ev_type = data.get("type", "")

            if ev_type == "response.output_item.added":
                item = data.get("item", {})
                if item.get("type") == "function_call":
                    fn = item.get("name", "")
                    current_tool = fn
                    if fn in TOOL_META:
                        icon, label = TOOL_META[fn]
                        extra = {}
                        if fn == "generate_image":
                            extra["format"] = format_type
                        yield f"data: {json.dumps({'type': 'step_start', 'tool': fn, 'icon': icon, 'label': label, **extra})}\n\n"

            elif ev_type == "response.output_text.delta":
                delta = data.get("delta", "")
                if delta:
                    full_text += delta
                    yield f"data: {json.dumps({'type': 'text_delta', 'delta': delta})}\n\n"

        elif event.type == "run_item_stream_event":
            item = event.item
            if item.type == "tool_call_output_item":
                output = str(item.output) if hasattr(item, "output") else ""
                tool = current_tool or ""

                if output.startswith("IMAGE_B64:"):
                    image_b64 = output[len("IMAGE_B64:"):]
                    yield f"data: {json.dumps({'type': 'step_done', 'tool': tool, 'icon': '🎨', 'label': 'Image created!', 'has_image': True})}\n\n"
                elif output.startswith("ERROR:"):
                    yield f"data: {json.dumps({'type': 'step_done', 'tool': tool, 'icon': '⚠️', 'label': output[6:80], 'error': True})}\n\n"
                else:
                    summary = output[:100] + "..." if len(output) > 100 else output
                    icon, label = TOOL_META.get(tool, ("✓", "Done"))
                    yield f"data: {json.dumps({'type': 'step_done', 'tool': tool, 'icon': icon, 'label': label, 'summary': summary})}\n\n"

    yield f"data: {json.dumps({'type': 'final', 'text': full_text, 'image_b64': image_b64 or ''})}\n\n"
    yield "data: [DONE]\n\n"


import uuid

app = FastAPI(title="Kaapi Bricks Promo Agent")


@app.exception_handler(Exception)
async def err_handler(request, exc):
    logger.error(f"Error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kaapi Bricks — Promo Creator</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f5f0eb; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    header { background: #4a2c0a; color: #fff; padding: 14px 24px; display: flex;
             align-items: center; gap: 12px; flex-shrink: 0; }
    header h1 { font-size: 17px; font-weight: 700; }
    .subtitle { font-size: 11px; color: #c8a882; }
    .main { display: flex; flex: 1; overflow: hidden; }

    /* LEFT */
    .left { width: 290px; min-width: 290px; background: #fff; border-right: 1px solid #e8d8c8;
            display: flex; flex-direction: column; overflow-y: auto; }
    .section { padding: 14px 16px; border-bottom: 1px solid #f0e8dc; }
    .section h3 { font-size: 10px; font-weight: 700; color: #999; text-transform: uppercase;
                  letter-spacing: 0.5px; margin-bottom: 10px; }
    label { display: block; font-size: 10px; font-weight: 600; color: #666;
            text-transform: uppercase; letter-spacing: 0.3px; margin: 10px 0 4px; }
    label:first-of-type { margin-top: 0; }
    input, textarea { width: 100%; border: 1px solid #d0b8a0; border-radius: 7px;
                      padding: 8px 10px; font-size: 12px; font-family: inherit;
                      outline: none; background: #faf8f6; }
    input:focus, textarea:focus { border-color: #4a2c0a; }
    textarea { height: 55px; resize: none; }
    .data-ctx { height: 70px; font-size: 11px; }
    .fmt-row { display: flex; gap: 6px; }
    .fmt-btn { flex: 1; padding: 6px 4px; border: 1px solid #d0b8a0; border-radius: 7px;
               background: #faf8f6; cursor: pointer; font-size: 11px; text-align: center; }
    .fmt-btn.active { background: #4a2c0a; color: #fff; border-color: #4a2c0a; }
    .presets { display: flex; flex-wrap: wrap; gap: 5px; }
    .preset { padding: 4px 9px; border: 1px solid #d0b8a0; border-radius: 12px;
              font-size: 10px; color: #4a2c0a; cursor: pointer; background: #faf8f6; }
    .preset:hover { background: #f0e8dc; }
    .gen-btn { margin: 12px 16px; padding: 11px; background: #4a2c0a; color: #fff;
               border: none; border-radius: 8px; font-size: 13px; font-weight: 600;
               cursor: pointer; width: calc(100% - 32px); }
    .gen-btn:hover { background: #6b3d0f; }
    .gen-btn:disabled { background: #ccc; cursor: not-allowed; }

    /* MIDDLE — reasoning */
    .middle { width: 300px; min-width: 300px; background: #faf8f6;
              border-right: 1px solid #e8d8c8; display: flex; flex-direction: column; overflow: hidden; }
    .mid-header { padding: 12px 14px; font-size: 10px; font-weight: 700; color: #999;
                  text-transform: uppercase; letter-spacing: 0.5px;
                  border-bottom: 1px solid #e8d8c8; background: #fff; flex-shrink: 0; }
    #steps { flex: 1; overflow-y: auto; padding: 12px; display: flex;
             flex-direction: column; gap: 6px; }
    .step { border-radius: 7px; padding: 9px 11px; font-size: 12px; transition: all 0.3s; }
    .step.idle { background: #fff; border: 1px solid #e8d8c8; color: #bbb; }
    .step.running { background: #fff8f0; border: 1px solid #f0d9c0; color: #4a2c0a; animation: pulse 1.5s infinite; }
    .step.done { background: #f0faf0; border: 1px solid #c0dcc0; color: #2a4a2a; }
    .step.done.img-done { background: #f8f0ff; border: 1px solid #d0c0e0; color: #3a2a4a; }
    .step.error { background: #fff0f0; border: 1px solid #e0c0c0; color: #5a2020; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
    .step-icon { margin-right: 6px; }
    .step-sum { font-size: 10px; color: #888; margin-top: 3px; overflow: hidden;
                text-overflow: ellipsis; white-space: nowrap; }
    #full-reasoning { flex: 1; overflow-y: auto; padding: 12px; font-size: 12px;
                      color: #333; line-height: 1.65; display: none; }
    #full-reasoning h2 { font-size: 11px; font-weight: 700; color: #fff;
                          background: #4a2c0a; padding: 5px 10px; border-radius: 5px;
                          margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.3px; }
    #full-reasoning h3 { font-size: 11px; font-weight: 700; color: #4a2c0a;
                          padding-left: 8px; border-left: 2px solid #c8a882; margin: 8px 0 4px; }
    #full-reasoning p { margin: 4px 0; }
    #full-reasoning ul { margin: 4px 0 6px 14px; }
    #full-reasoning strong { color: #2d1a0a; }
    .vtabs { border-top: 1px solid #e8d8c8; background: #fff; display: flex;
             gap: 6px; padding: 8px 14px; flex-shrink: 0; }
    .vtab { flex: 1; padding: 5px; font-size: 10px; border: 1px solid #d0b8a0;
            border-radius: 6px; cursor: pointer; text-align: center; background: #faf8f6; }
    .vtab.active { background: #4a2c0a; color: #fff; border-color: #4a2c0a; }

    /* RIGHT */
    .right { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    .out-tabs { display: flex; background: #fff; border-bottom: 1px solid #e8d8c8; flex-shrink: 0; }
    .otab { padding: 10px 16px; font-size: 12px; font-weight: 600; cursor: pointer;
            color: #999; border-bottom: 2px solid transparent; }
    .otab.active { color: #4a2c0a; border-bottom-color: #4a2c0a; }
    .out-panel { flex: 1; overflow-y: auto; padding: 20px; display: none; }
    .out-panel.active { display: block; }
    .empty { display: flex; flex-direction: column; align-items: center;
             justify-content: center; height: 100%; color: #ccc; gap: 8px; }
    .big-icon { font-size: 40px; }

    /* Image */
    .img-container { display: inline-block; }
    .img-card { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.12); display: inline-block; }
    .img-card img { display: block; max-height: 480px; }
    .img-bar { padding: 8px 12px; background: #f5f0eb; font-size: 10px; font-weight: 700;
               color: #666; text-transform: uppercase; letter-spacing: 0.3px; }
    .img-actions { margin-top: 10px; display: flex; gap: 8px; }
    .btn-sm { padding: 6px 14px; border: 1px solid #d0b8a0; border-radius: 7px;
              font-size: 11px; cursor: pointer; background: #fff; }
    .btn-sm:hover { background: #f0e8dc; }

    /* Copy */
    .copy-block { margin-bottom: 16px; }
    .copy-lbl { font-size: 9px; font-weight: 700; color: #999; text-transform: uppercase;
                letter-spacing: 0.5px; margin-bottom: 5px; }
    .headline { font-size: 26px; font-weight: 800; color: #2d1a0a; line-height: 1.1; }
    .subline { font-size: 14px; color: #6b3d0f; font-style: italic; margin-top: 4px; }
    .body-copy { font-size: 13px; color: #444; line-height: 1.7; background: #faf8f6;
                 padding: 12px; border-radius: 8px; }
    .cta { display: inline-block; background: #4a2c0a; color: #fff; padding: 7px 18px;
           border-radius: 16px; font-size: 12px; font-weight: 600; }
    .ht { font-size: 12px; color: #c8a882; line-height: 1.9; }

    /* Campaign plan */
    .plan h2 { font-size: 12px; font-weight: 700; color: #fff; background: #4a2c0a;
               padding: 6px 12px; border-radius: 6px; margin: 14px 0 8px; text-transform: uppercase; }
    .plan h3 { font-size: 12px; font-weight: 700; color: #4a2c0a; padding-left: 8px;
               border-left: 3px solid #c8a882; margin: 10px 0 5px; }
    .plan p { font-size: 13px; color: #444; line-height: 1.7; margin: 4px 0; }
    .plan ul { margin: 5px 0 6px 16px; }
    .plan li { font-size: 13px; color: #444; margin: 3px 0; }
    .plan strong { color: #2d1a0a; }
    .plan table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px; }
    .plan th { background: #4a2c0a; color: #fff; padding: 6px 10px; text-align: left; }
    .plan td { padding: 5px 10px; border-bottom: 1px solid #f0e8dc; }
  </style>
</head>
<body>
  <header>
    <span>🎨</span>
    <div>
      <h1>Kaapi Bricks — Promotional Creative Agent</h1>
      <div class="subtitle">Market research → Creative brief → Copy → Image generation (GPT on Databricks)</div>
    </div>
  </header>

  <div class="main">
    <!-- LEFT: Brief -->
    <div class="left">
      <div class="section">
        <h3>Campaign Brief</h3>
        <label>Product / Drink</label>
        <input id="product" value="Cold Brew Kaapi" placeholder="e.g. Monsoon Spice Kaapi">
        <label>Occasion / Theme</label>
        <textarea id="occasion" placeholder="e.g. Peak summer heat relief campaign">Peak summer 2026 — beat the heat</textarea>
        <label>Format</label>
        <div class="fmt-row">
          <div class="fmt-btn active" id="fmt-ig" onclick="setFmt('instagram')">📱 Instagram</div>
          <div class="fmt-btn" id="fmt-po" onclick="setFmt('poster')">🖼️ Poster</div>
        </div>
      </div>
      <div class="section">
        <h3>Analytics Context (optional)</h3>
        <p style="font-size:10px;color:#aaa;margin-bottom:8px">Paste sales data from Genie here — the agent will incorporate it into the creative brief</p>
        <textarea id="data-ctx" class="data-ctx" placeholder="e.g. Cold Brew sold 8,234 cups last month. Top cities: Bangalore (42%), Chennai (28%). Peak hours: 11am-2pm..."></textarea>
      </div>
      <div class="section">
        <h3>Quick Presets</h3>
        <div class="presets">
          <div class="preset" onclick="sp('Bella Kaapi','Ugadi festival celebration')">🎉 Ugadi</div>
          <div class="preset" onclick="sp('Cold Brew Kaapi','Peak summer heat')">☀️ Summer</div>
          <div class="preset" onclick="sp('Filter Kaapi','Morning ritual')">🌅 Morning</div>
          <div class="preset" onclick="sp('Sukku Kaapi','Monsoon wellness')">🌧️ Monsoon</div>
          <div class="preset" onclick="sp('Mocha Kaapi','Weekend treat')">🍫 Weekend</div>
        </div>
      </div>
      <button class="gen-btn" id="gen-btn" onclick="generate()">✨ Generate Campaign</button>
    </div>

    <!-- MIDDLE: Chain of thought -->
    <div class="middle">
      <div class="mid-header">Reasoning Chain</div>
      <div id="steps">
        <div class="step idle" id="s0"><span class="step-icon">🔍</span>Research market trends</div>
        <div class="step idle" id="s1"><span class="step-icon">🔍</span>Research competitors</div>
        <div class="step idle" id="s2"><span class="step-icon">🔍</span>Research cultural moments</div>
        <div class="step idle" id="s3"><span class="step-icon">💡</span>Synthesise creative brief</div>
        <div class="step idle" id="s4"><span class="step-icon">✍️</span>Write promotional copy</div>
        <div class="step idle" id="s5"><span class="step-icon">🎨</span>Generate image</div>
        <div class="step idle" id="s6"><span class="step-icon">📋</span>Build campaign plan</div>
      </div>
      <div id="full-reasoning"></div>
      <div class="vtabs">
        <div class="vtab active" id="vt-steps" onclick="vswitch('steps')">Steps</div>
        <div class="vtab" id="vt-text" onclick="vswitch('text')">Full Reasoning</div>
      </div>
    </div>

    <!-- RIGHT: Output -->
    <div class="right">
      <div class="out-tabs">
        <div class="otab active" onclick="ot('image')">🖼️ Image</div>
        <div class="otab" onclick="ot('copy')">✍️ Copy</div>
        <div class="otab" onclick="ot('plan')">📋 Campaign Plan</div>
      </div>
      <div class="out-panel active" id="op-image">
        <div class="empty"><div class="big-icon">🎨</div><span>Image appears here</span></div>
      </div>
      <div class="out-panel" id="op-copy">
        <div class="empty"><div class="big-icon">✍️</div><span>Copy appears here</span></div>
      </div>
      <div class="out-panel" id="op-plan">
        <div class="empty"><div class="big-icon">📋</div><span>Campaign plan appears here</span></div>
      </div>
    </div>
  </div>

  <script>
    marked.setOptions({ breaks: true, gfm: true });
    let fmt = 'instagram';
    let fullText = '';
    let researchCount = 0;

    const sp = (p, o) => { document.getElementById('product').value=p; document.getElementById('occasion').value=o; };
    const setFmt = f => {
      fmt = f;
      document.getElementById('fmt-ig').className = 'fmt-btn'+(f==='instagram'?' active':'');
      document.getElementById('fmt-po').className = 'fmt-btn'+(f==='poster'?' active':'');
    };
    const ot = t => {
      document.querySelectorAll('.otab').forEach((e,i)=>e.className='otab'+(['image','copy','plan'][i]===t?' active':''));
      document.querySelectorAll('.out-panel').forEach(e=>e.className='out-panel');
      document.getElementById('op-'+t).className='out-panel active';
    };
    const vswitch = v => {
      document.getElementById('vt-steps').className='vtab'+(v==='steps'?' active':'');
      document.getElementById('vt-text').className='vtab'+(v==='text'?' active':'');
      document.getElementById('steps').style.display = v==='steps'?'flex':'none';
      document.getElementById('full-reasoning').style.display = v==='text'?'block':'none';
    };

    function resetUI() {
      researchCount = 0; fullText = '';
      for(let i=0;i<7;i++) {
        const el = document.getElementById('s'+i);
        if(el) { el.className='step idle'; el.querySelector('.step-sum')?.remove(); }
      }
      document.getElementById('full-reasoning').innerHTML='';
    }

    function handleStep(msg) {
      if (msg.tool === 'research_trends') {
        const idx = Math.min(researchCount, 2);
        const el = document.getElementById('s'+idx);
        if (el) el.className = 'step running';
        if (msg.type === 'step_done') {
          if (el) { el.className = 'step done' + (msg.error?' error':''); }
          if (msg.summary) {
            const s = document.createElement('div');
            s.className='step-sum'; s.textContent=msg.summary;
            el?.appendChild(s);
          }
          researchCount++;
          // Mark synthesis step running
          if (researchCount >= 2) document.getElementById('s3').className='step running';
        }
      } else if (msg.tool === 'generate_image') {
        const el = document.getElementById('s5');
        if (msg.type === 'step_start') { el.className='step running'; }
        else {
          el.className = msg.has_image ? 'step done img-done' : 'step done error';
          if (msg.has_image) ot('image');
        }
      }
    }

    async function generate() {
      const product = document.getElementById('product').value.trim();
      const occasion = document.getElementById('occasion').value.trim();
      const ctx = document.getElementById('data-ctx').value.trim();
      if (!product||!occasion) { alert('Fill in product and occasion'); return; }

      const btn = document.getElementById('gen-btn');
      btn.disabled=true; btn.textContent='⏳ Generating...';
      resetUI();
      ['image','copy','plan'].forEach(t => {
        document.getElementById('op-'+t).innerHTML='<div class="empty"><div class="big-icon">⏳</div></div>';
      });

      const params = new URLSearchParams({product, occasion, format: fmt});
      if (ctx) params.append('context', ctx);
      const es = new EventSource('/stream?' + params);

      es.onmessage = e => {
        if (e.data==='[DONE]') {
          es.close(); btn.disabled=false; btn.textContent='✨ Generate Campaign';
          renderOutputs(); return;
        }
        try {
          const msg = JSON.parse(e.data);
          if (msg.type==='step_start'||msg.type==='step_done') handleStep(msg);
          else if (msg.type==='text_delta') {
            fullText += msg.delta;
            // Mark reasoning steps based on content
            if (fullText.includes('STEP 3') || fullText.includes('Creative Brief')) document.getElementById('s3').className='step running';
            if (fullText.includes('STEP 4') || fullText.includes('Copy Creation')) { document.getElementById('s3').className='step done'; document.getElementById('s4').className='step running'; }
            document.getElementById('full-reasoning').innerHTML = marked.parse(fullText);
            document.getElementById('full-reasoning').scrollTop = 9999;
          }
          else if (msg.type==='final') {
            if (msg.text) fullText=msg.text;
            if (msg.image_b64) { window.__b64=msg.image_b64; renderImage(msg.image_b64); }
          }
        } catch(err){}
      };
      es.onerror = () => { es.close(); btn.disabled=false; btn.textContent='✨ Generate Campaign'; };
    }

    function renderImage(b64) {
      const lbl = fmt==='instagram'?'📱 Instagram (9:16)':'🖼️ Store Poster (16:9)';
      document.getElementById('op-image').innerHTML = `
        <div class="img-container">
          <div class="img-card">
            <div class="img-bar">${lbl}</div>
            <img src="data:image/jpeg;base64,${b64}" alt="Promo">
          </div>
          <div class="img-actions">
            <button class="btn-sm" onclick="dl()">⬇️ Download</button>
            <button class="btn-sm" onclick="ot('copy')">✍️ View Copy →</button>
          </div>
        </div>`;
      // Mark remaining steps done
      [3,4,6].forEach(i => { const e=document.getElementById('s'+i); if(e&&e.className.includes('idle')||e?.className.includes('running')) e.className='step done'; });
      document.getElementById('s6').className='step done';
    }

    function renderOutputs() {
      const t = fullText;
      // Extract copy elements
      const ex = (patterns) => { for(const p of patterns){const m=t.match(p); if(m) return m[1].replace(/\*+/g,'').trim();} return ''; };
      const hl = ex([/\*{0,2}Headline\*{0,2}[:\s*]+(.+)/i, /#{1,3} *(?:Headline)[:\s]*\n+(.+)/i]) || document.getElementById('product').value;
      const sl = ex([/\*{0,2}Subline\*{0,2}[:\s*]+(.+)/i]);
      const bd = ex([/\*{0,2}Body(?:\s*[Cc]opy)?\*{0,2}[:\s*]+([^\n#]{30,})/i]);
      const ct = ex([/\*{0,2}CTA\*{0,2}[:\s*]+(.+)/i, /\*{0,2}Call[- ]to[- ]Action\*{0,2}[:\s*]+(.+)/i]) || 'Try Now';
      const ht = (t.match(/((?:#\w+\s*){3,})/) || ['',''])[1];

      document.getElementById('op-copy').innerHTML = `
        <div class="copy-block"><div class="copy-lbl">Headline</div>
          <div class="headline">${hl}</div>${sl?`<div class="subline">${sl}</div>`:''}
        </div>
        ${bd?`<div class="copy-block"><div class="copy-lbl">Body Copy</div><div class="body-copy">${bd}</div></div>`:''}
        <div class="copy-block"><div class="cta">${ct}</div></div>
        ${ht?`<div class="copy-block"><div class="copy-lbl">Hashtags</div><div class="ht">${ht}</div></div>`:''}
        <div style="margin-top:14px;display:flex;gap:8px">
          <button class="btn-sm" onclick="copyCaption()">📋 Copy Caption</button>
        </div>`;

      document.getElementById('op-plan').innerHTML = `<div class="plan">${marked.parse(t)}</div>`;
      [4,6].forEach(i=>{const e=document.getElementById('s'+i);if(e)e.className='step done';});
    }

    function copyCaption() {
      const hl=document.querySelector('.headline')?.textContent||'';
      const sl=document.querySelector('.subline')?.textContent||'';
      const bd=document.querySelector('.body-copy')?.textContent||'';
      const ht=document.querySelector('.ht')?.textContent||'';
      navigator.clipboard.writeText([hl,sl,'',bd,'',ht].join('\n'));
      alert('Caption copied!');
    }
    function dl() {
      if(!window.__b64) return;
      const a=document.createElement('a'); a.href='data:image/jpeg;base64,'+window.__b64;
      a.download='kaapi-promo.jpg'; a.click();
    }
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def ui(): return HTML


@app.get("/health")
async def health(): return {"status": "ok"}


@app.get("/stream")
async def stream_ep(request: Request):
    product = request.query_params.get("product", "Filter Kaapi")
    occasion = request.query_params.get("occasion", "Monsoon season")
    format_type = request.query_params.get("format", "instagram")
    data_context = request.query_params.get("context", "")
    return StreamingResponse(
        stream_agent(product, occasion, format_type, data_context),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def create_fast_agent() -> Agent:
    """MAS-compatible agent — research + brief + copy only. NO image generation.
    Image gen takes 60-90s and causes MAS 290s timeout. Images only in the web UI.
    """
    return Agent(
        name="Kaapi Bricks Promotional Creative Agent",
        instructions=SYSTEM_PROMPT.replace(
            "## STEP 4: Image Generation\nCall generate_image with:",
            "## STEP 4: Image Brief (no image generation via API)\nDescribe in detail what the image should look like — scene, lighting, props, colors, mood."
        ).replace(
            "4. generate_image — create the promotional visual",
            "4. Describe the image brief (image generation available in standalone web UI only)"
        ),
        model=MODEL,
        tools=[research_trends],  # only research — no image gen for MAS calls
    )


@app.post("/invocations")
async def invocations_ep(request: Request):
    """MAS-compatible endpoint. Uses fast agent (no image generation) to stay under 290s timeout."""
    body = await request.json()
    msgs = body.get("input") or body.get("messages") or []
    wants_stream = body.get("stream", False)
    def gf(m, f): return m.get(f) if isinstance(m, dict) else getattr(m, f, None)
    last_user = next((gf(m,"content") for m in reversed(msgs) if gf(m,"role")=="user"), "")
    if not last_user:
        return JSONResponse(status_code=400, content={"error": "no user message"})

    # Add a note so the agent knows it's in API mode
    api_msg = (
        f"{last_user}\n\n"
        f"[API MODE — skip image generation. Return: market research findings, "
        f"creative brief, full copy (headline/subline/body/CTA/hashtags), and campaign plan. "
        f"Mention that images can be generated in the standalone Promo Creator app.]"
    )

    agent = create_fast_agent()
    result = await Runner.run(agent, api_msg)
    final_text = result.final_output or ""

    import time
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    created = int(time.time())

    # Always stream — MAS expects SSE, and streaming avoids timeout issues.
    # Return ONLY final text as chat.completion.chunk — no tool call artifacts.
    async def gen():
        def c(d, f=None):
            return "data: " + json.dumps({
                "id": chat_id, "object": "chat.completion.chunk",
                "created": created, "model": MODEL,
                "choices": [{"index": 0, "delta": d, "finish_reason": f}]
            }) + "\n\n"
        yield c({"role": "assistant", "content": ""})
        for i in range(0, len(final_text), 100):
            yield c({"content": final_text[i:i+100]})
        yield c({}, f="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
