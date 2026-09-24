"""Kaapi Bricks Operations Advisor — Standalone MCP Server.

A dedicated Databricks App that serves MCP tools for the MAS Supervisor.
Separate from the main chat app to avoid circular dependency.
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
import requests as http_requests

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from databricks.sdk import WorkspaceClient

# =============================================================================
# CONFIGURATION
# =============================================================================
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "e755eae9d758fdf7")

FOUNDATION_MODELS = [
    "databricks-meta-llama-3-3-70b-instruct", "databricks-claude-sonnet-4-6",
    "databricks-gpt-5-2", "databricks-gemini-3-flash", "databricks-llama-4-maverick",
    "databricks-claude-haiku-4-5", "databricks-gpt-5-mini", "databricks-gemini-2-5-flash",
    "AI-Days-Gpt-Llama-8020",
]

DEFAULT_MODEL = os.environ.get("OPS_MODEL", "databricks-meta-llama-3-3-70b-instruct")

CITY_COORDS = {
    "bangalore": (12.97, 77.59), "chennai": (13.08, 80.27), "mumbai": (19.08, 72.88),
    "delhi": (28.61, 77.21), "hyderabad": (17.39, 78.49), "pune": (18.52, 73.86),
    "kolkata": (22.57, 88.36), "mysuru": (12.30, 76.66), "coimbatore": (11.00, 76.96),
    "kochi": (9.93, 76.27), "madurai": (9.92, 78.12), "pondicherry": (11.93, 79.83),
    "vizag": (17.69, 83.22), "ahmedabad": (23.02, 72.57), "jaipur": (26.91, 75.79),
    "chandigarh": (30.73, 76.78), "goa": (15.50, 73.83), "dubai": (25.20, 55.27),
    "singapore": (1.35, 103.82), "london": (51.51, -0.13), "san francisco": (37.77, -122.42),
    "kuala lumpur": (3.14, 101.69), "sydney": (-33.87, 151.21), "toronto": (43.65, -79.38),
}

# Real 2026 India holidays (source: timeanddate.com/holidays/india/2026)
# G = Gazetted (national), R = Restricted, S = State (Karnataka)
INDIAN_HOLIDAYS_2026 = {
    # Gazetted (National) Holidays
    "2026-01-26": {"name": "Republic Day", "type": "gazetted"},
    "2026-03-04": {"name": "Holi", "type": "gazetted"},
    "2026-03-21": {"name": "Eid ul-Fitr (Ramzan)", "type": "gazetted"},
    "2026-03-26": {"name": "Ram Navami", "type": "gazetted"},
    "2026-03-31": {"name": "Mahavir Jayanti", "type": "gazetted"},
    "2026-04-03": {"name": "Good Friday", "type": "gazetted"},
    "2026-05-01": {"name": "Buddha Purnima", "type": "gazetted"},
    "2026-05-27": {"name": "Eid ul-Adha (Bakrid)", "type": "gazetted"},
    "2026-06-26": {"name": "Muharram", "type": "gazetted"},
    "2026-08-15": {"name": "Independence Day", "type": "gazetted"},
    "2026-08-26": {"name": "Milad un-Nabi (Prophet's Birthday)", "type": "gazetted"},
    "2026-09-04": {"name": "Janmashtami", "type": "gazetted"},
    "2026-10-02": {"name": "Mahatma Gandhi Jayanti", "type": "gazetted"},
    "2026-10-20": {"name": "Dussehra (Vijayadashami)", "type": "gazetted"},
    "2026-11-08": {"name": "Diwali / Deepavali", "type": "gazetted"},
    "2026-11-24": {"name": "Guru Nanak Jayanti", "type": "gazetted"},
    "2026-12-25": {"name": "Christmas", "type": "gazetted"},
    # Major Restricted / Regional Holidays
    "2026-01-01": {"name": "New Year's Day", "type": "restricted"},
    "2026-01-14": {"name": "Makar Sankranti / Pongal", "type": "restricted"},
    "2026-02-15": {"name": "Maha Shivaratri", "type": "restricted"},
    "2026-03-03": {"name": "Holika Dahana", "type": "restricted"},
    "2026-03-19": {"name": "Ugadi / Gudi Padwa", "type": "restricted"},
    "2026-04-14": {"name": "Vaisakhi / Ambedkar Jayanti", "type": "restricted"},
    "2026-07-16": {"name": "Rath Yatra", "type": "restricted"},
    "2026-08-26": {"name": "Onam", "type": "restricted"},
    "2026-08-28": {"name": "Raksha Bandhan", "type": "restricted"},
    "2026-09-14": {"name": "Ganesh Chaturthi", "type": "restricted"},
    "2026-10-18": {"name": "Maha Saptami (Durga Puja)", "type": "restricted"},
    "2026-10-19": {"name": "Maha Ashtami (Durga Puja)", "type": "restricted"},
    "2026-11-01": {"name": "Karnataka Rajyotsava", "type": "state_karnataka"},
    "2026-11-09": {"name": "Govardhan Puja", "type": "restricted"},
    "2026-11-11": {"name": "Bhai Duj", "type": "restricted"},
    "2026-11-15": {"name": "Chhath Puja", "type": "restricted"},
}

OPS_SYSTEM_PROMPT = """You are the Kaapi Bricks Operations Advisor for a South Indian filter coffee chain with 37 stores.

You have data from: live weather forecast and Indian holiday/festival calendar.

Generate a preparation plan with:
- Weather impact on drink preferences (rain = hot up, cold down; heat = cold up)
- Calendar impact (festivals = family groups; weekends = 2-2.5x volume)
- Product-level recommendations based on weather and calendar
- Staffing recommendation
- Special notes

RULES:
- If store_data is provided, use those ACTUAL numbers for product forecasts.
- If no store_data, provide general weather/calendar guidance only.
- nearby_festivals are NOT on the target date. Only use if is_holiday_on_this_date is true."""

# =============================================================================
# TOOLS
# =============================================================================
def _get_workspace_client():
    return WorkspaceClient()


# Weather code to condition mapping (WMO codes used by Open-Meteo)
WMO_WEATHER = {
    0: ("Clear", "clear sky"), 1: ("Clear", "mainly clear"), 2: ("Cloudy", "partly cloudy"),
    3: ("Cloudy", "overcast"), 45: ("Fog", "foggy"), 48: ("Fog", "depositing rime fog"),
    51: ("Drizzle", "light drizzle"), 53: ("Drizzle", "moderate drizzle"), 55: ("Drizzle", "dense drizzle"),
    61: ("Rain", "slight rain"), 63: ("Rain", "moderate rain"), 65: ("Rain", "heavy rain"),
    71: ("Snow", "slight snow"), 73: ("Snow", "moderate snow"), 75: ("Snow", "heavy snow"),
    80: ("Rain", "slight rain showers"), 81: ("Rain", "moderate rain showers"), 82: ("Rain", "violent rain showers"),
    95: ("Thunderstorm", "thunderstorm"), 96: ("Thunderstorm", "thunderstorm with hail"), 99: ("Thunderstorm", "thunderstorm with heavy hail"),
}


def _now_ist():
    """Get current datetime in IST (UTC+5:30)."""
    from datetime import timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(IST)


def _get_target_date(query):
    """Detect if user is asking about today, tomorrow, or a specific day. Returns (date_str, day_offset, label)."""
    q = query.lower()
    now = _now_ist()
    if "today" in q or "right now" in q or "this evening" in q or "this morning" in q:
        return now.strftime("%Y-%m-%d"), 0, "today"
    elif "day after tomorrow" in q or "day after" in q:
        return (now + timedelta(days=2)).strftime("%Y-%m-%d"), 2, "day after tomorrow"
    elif "this weekend" in q:
        days_until_sat = (5 - now.weekday()) % 7
        if days_until_sat == 0:
            days_until_sat = 7
        return (now + timedelta(days=days_until_sat)).strftime("%Y-%m-%d"), days_until_sat, "this weekend"
    else:
        # Default: tomorrow
        return (now + timedelta(days=1)).strftime("%Y-%m-%d"), 1, "tomorrow"


def _get_weather(city, target_date, day_offset=1):
    """Get weather from Open-Meteo API (free, no key needed). IST timezone forced."""
    city_lower = city.lower().split(",")[0].strip()
    coords = CITY_COORDS.get(city_lower)
    if not coords:
        for k, v in CITY_COORDS.items():
            if k in city_lower or city_lower in k:
                coords = v
                break
    if not coords:
        coords = (12.97, 77.59)  # Default to Bangalore

    try:
        resp = http_requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": coords[0], "longitude": coords[1],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "UTC+5:30",
            "forecast_days": 7,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])

        # Use day_offset as index: 0=today, 1=tomorrow
        idx = day_offset if day_offset < len(dates) else None

        # Also try matching by date string
        if idx is None:
            for i, d in enumerate(dates):
                if d == target_date:
                    idx = i
                    break

        if idx is not None and idx < len(dates):
            temp_max = daily["temperature_2m_max"][idx]
            temp_min = daily["temperature_2m_min"][idx]
            precip = daily["precipitation_sum"][idx]
            wcode = daily["weather_code"][idx]
            condition, description = WMO_WEATHER.get(wcode, ("Unknown", f"weather code {wcode}"))
            return {
                "city": city, "date": dates[idx],
                "temperature_high": round(temp_max, 1), "temperature_low": round(temp_min, 1),
                "condition": condition, "description": description,
                "precipitation_mm": round(precip, 1),
                "timezone": "IST (UTC+5:30)",
                "source": "Open-Meteo (live)",
            }
    except Exception as e:
        print(f"Open-Meteo API error: {e}")

    # Fallback only if API completely fails
    return {"city": city, "date": target_date, "temperature_high": 30, "condition": "Unknown",
            "description": "weather data unavailable", "source": "fallback"}


def _get_calendar(target_date):
    dt = datetime.fromisoformat(target_date)
    day_name = dt.strftime("%A")
    holiday_entry = INDIAN_HOLIDAYS_2026.get(target_date)
    holiday_name = holiday_entry["name"] if holiday_entry else None
    holiday_type = holiday_entry["type"] if holiday_entry else None
    nearby = []
    for o in range(-3, 4):
        if o == 0:
            continue
        check_date = (dt + timedelta(days=o)).strftime("%Y-%m-%d")
        entry = INDIAN_HOLIDAYS_2026.get(check_date)
        if entry:
            nearby.append({"date": check_date, "festival": entry["name"], "type": entry["type"], "days_away": o})
    return {"date": target_date, "day_of_week": day_name, "is_weekend": day_name in ("Saturday", "Sunday"),
            "is_friday": day_name == "Friday", "is_holiday_on_this_date": holiday_name is not None,
            "holiday_name": holiday_name, "holiday_type": holiday_type,
            "nearby_festivals_NOT_on_this_date": nearby}


def _generate_ops_plan(query, store, model_endpoint, store_data=""):
    target_date, day_offset, day_label = _get_target_date(query)
    city = store.split(",")[-1].strip() if "," in store else store
    weather = _get_weather(city, target_date, day_offset)
    calendar = _get_calendar(target_date)
    context = f"## Weather for {day_label} ({target_date})\n{json.dumps(weather, indent=2)}\n\n## Calendar for {target_date}\n{json.dumps(calendar, indent=2)}"
    if store_data:
        context = f"## Store Data\n{store_data}\n\n{context}"
    w = _get_workspace_client()
    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{model_endpoint}/invocations"
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    start = time.time()
    try:
        resp = http_requests.post(url, headers=headers,
            json={"messages": [{"role": "system", "content": OPS_SYSTEM_PROMPT},
                               {"role": "user", "content": f"{query}\n\n---\n{context}"}],
                  "max_tokens": 2000, "temperature": 0.3}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating plan: {e}"


# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(title="Kaapi Bricks Operations Advisor MCP Server")

MCP_TOOLS = [
    {"name": "operations_advisor",
     "description": "Kaapi Bricks Operations Advisor. Generates a preparation plan for any store for tomorrow or upcoming days. Checks live weather, Indian holiday/festival calendar, and generates recommendations.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "The user's question about operations or preparation"},
         "store": {"type": "string", "description": "Store location (e.g. Koramangala, Bangalore)"},
         "store_data": {"type": "string", "description": "Optional store analytics data"}
     }, "required": ["query"]}},
]


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP JSON-RPC 2.0 endpoint."""
    body = await request.json()
    method = body.get("method", "")
    req_id = body.get("id", 1)
    print(f"[MCP] method={method} body={json.dumps(body)[:300]}")

    if method == "initialize":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05", "serverInfo": {"name": "kaapi-ops-advisor", "version": "1.0"},
            "capabilities": {"tools": {}}}})

    elif method == "tools/list":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}})

    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        print(f"[MCP] tools/call: tool={tool_name} args={json.dumps(args)[:200]}")

        query = args.get("query", "What should I prepare for tomorrow?")
        store = args.get("store", "Koramangala, Bangalore")
        store_data = args.get("store_data", "")
        text = _generate_ops_plan(query, store, DEFAULT_MODEL, store_data)
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text}]}})

    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}})


# Also serve at /api/mcp for backward compat
@app.post("/api/mcp")
async def mcp_api_endpoint(request: Request):
    return await mcp_endpoint(request)


@app.get("/health")
def health():
    return {"status": "ok", "tools": [t["name"] for t in MCP_TOOLS], "model": DEFAULT_MODEL}


# =============================================================================
# UI ENDPOINTS — Admin + Compare (does NOT touch MCP)
# =============================================================================
import threading

# In-memory config (persists as long as app runs)
_config = {"operations_model": DEFAULT_MODEL}
_config_lock = threading.Lock()


@app.get("/api/models")
def get_models():
    return {"models": FOUNDATION_MODELS}


@app.get("/api/config")
def get_config():
    with _config_lock:
        return dict(_config)


@app.post("/api/config")
async def save_config(request: Request):
    body = await request.json()
    with _config_lock:
        if "operations_model" in body:
            _config["operations_model"] = body["operations_model"]
            # Also update the global DEFAULT_MODEL so MCP uses it
            global DEFAULT_MODEL
            DEFAULT_MODEL = body["operations_model"]
    return {"ok": True, "config": dict(_config)}


@app.post("/api/compare")
async def compare_models(request: Request):
    """Run operations advisor with two models, return both results."""
    body = await request.json()
    query = body.get("query", "What should I prepare for tomorrow?")
    store = body.get("store", "Koramangala, Bangalore")
    model_a = body.get("model_a", FOUNDATION_MODELS[0])
    model_b = body.get("model_b", FOUNDATION_MODELS[1])

    result_holder = [None]
    error_holder = [None]

    def _process():
        try:
            ra = _generate_ops_plan(query, store, model_a)
            rb = _generate_ops_plan(query, store, model_b)
            result_holder[0] = {"model_a": {"text": ra, "model": model_a}, "model_b": {"text": rb, "model": model_b}}
        except Exception as e:
            error_holder[0] = str(e)

    t = threading.Thread(target=_process)
    t.start()

    from fastapi.responses import StreamingResponse

    def event_stream():
        msgs = ["Running Model A...", "Running Model B...", "Almost done..."]
        i = 0
        while t.is_alive():
            yield f"data: {json.dumps({'keepalive': True, 'status': msgs[min(i, len(msgs)-1)]})}\n\n"
            i += 1
            t.join(timeout=8)
        if result_holder[0]:
            yield f"data: {json.dumps({'done': True, 'result': result_holder[0]})}\n\n"
        else:
            err = error_holder[0] or "Unknown error"
            yield f"data: {json.dumps({'done': True, 'result': {'model_a': {'text': 'Error: ' + err}, 'model_b': {'text': 'Error: ' + err}}})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


# Serve UI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r") as f:
        return f.read()

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
