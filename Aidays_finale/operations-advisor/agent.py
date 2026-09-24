"""Kaapi Bricks Operations Advisor — Custom ChatAgent for store planning.

Combines live weather forecasts, Indian holiday/festival calendar, day-of-week
patterns, and historical sales data to generate actionable store preparation
plans with product-level sales forecasts.

This agent is deployed as a Model Serving endpoint and registered as a
sub-agent in the Kaapi Bricks MAS Supervisor.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Generator

import mlflow
import requests
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

# =============================================================================
# CONFIGURATION
# =============================================================================
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "e755eae9d758fdf7")
CATALOG = "fevm_cme_conde_catalog"
SCHEMA = "kaapi_bricks"
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# City to coordinates mapping for weather API
CITY_COORDS = {
    "bangalore": (12.97, 77.59),
    "chennai": (13.08, 80.27),
    "mumbai": (19.08, 72.88),
    "delhi": (28.61, 77.21),
    "hyderabad": (17.39, 78.49),
    "pune": (18.52, 73.86),
    "kolkata": (22.57, 88.36),
    "mysuru": (12.30, 76.66),
    "coimbatore": (11.00, 76.96),
    "kochi": (9.93, 76.27),
    "madurai": (9.92, 78.12),
    "pondicherry": (11.93, 79.83),
    "vizag": (17.69, 83.22),
    "ahmedabad": (23.02, 72.57),
    "jaipur": (26.91, 75.79),
    "chandigarh": (30.73, 76.78),
    "goa": (15.50, 73.83),
    "dubai": (25.20, 55.27),
    "singapore": (1.35, 103.82),
    "london": (51.51, -0.13),
    "san francisco": (37.77, -122.42),
    "kuala lumpur": (3.14, 101.69),
    "sydney": (-33.87, 151.21),
    "toronto": (43.65, -79.38),
}

# Indian holidays & festivals (2026 key dates)
INDIAN_FESTIVALS_2026 = {
    "2026-01-14": "Makar Sankranti / Pongal",
    "2026-01-26": "Republic Day",
    "2026-02-17": "Maha Shivaratri",
    "2026-03-17": "Holi",
    "2026-03-22": "Ugadi / Gudi Padwa",
    "2026-03-28": "Ramzan / Eid ul-Fitr",
    "2026-04-02": "Good Friday",
    "2026-04-06": "Ram Navami",
    "2026-04-14": "Ambedkar Jayanti / Baisakhi",
    "2026-05-01": "May Day",
    "2026-05-12": "Buddha Purnima",
    "2026-06-04": "Eid ul-Adha / Bakrid",
    "2026-07-07": "Rath Yatra",
    "2026-08-15": "Independence Day",
    "2026-08-17": "Janmashtami",
    "2026-08-26": "Ganesh Chaturthi",
    "2026-09-14": "Onam",
    "2026-10-02": "Gandhi Jayanti / Navratri Begins",
    "2026-10-11": "Dussehra / Vijayadashami",
    "2026-10-31": "Diwali",
    "2026-11-01": "Diwali (Day 2) / Govardhan Puja",
    "2026-11-06": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas",
}


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================
@mlflow.trace(name="get_weather_forecast", span_type="TOOL")
def get_weather_forecast(city: str, target_date: str) -> dict:
    """Call OpenWeatherMap API for weather forecast.

    Args:
        city: City name (e.g., "Bangalore", "Chennai")
        target_date: ISO date string (e.g., "2026-04-01")

    Returns:
        dict with temperature, condition, humidity, description
    """
    city_lower = city.lower().split(",")[0].strip()

    coords = CITY_COORDS.get(city_lower)
    if not coords:
        # Try partial match
        for key, val in CITY_COORDS.items():
            if key in city_lower or city_lower in key:
                coords = val
                break

    if not coords or not OPENWEATHER_API_KEY:
        # Fallback: return reasonable defaults based on city and month
        return _weather_fallback(city_lower, target_date)

    try:
        # Use 5-day forecast API (free tier)
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": coords[0],
            "lon": coords[1],
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Find forecast closest to target date noon
        target_dt = datetime.fromisoformat(target_date)
        target_noon = target_dt.replace(hour=12)

        best_forecast = None
        best_diff = float("inf")
        for item in data.get("list", []):
            forecast_dt = datetime.fromtimestamp(item["dt"])
            diff = abs((forecast_dt - target_noon).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_forecast = item

        if best_forecast:
            weather = best_forecast["weather"][0]
            main = best_forecast["main"]
            return {
                "city": city,
                "date": target_date,
                "temperature_high": round(main.get("temp_max", main["temp"]), 1),
                "temperature_low": round(main.get("temp_min", main["temp"]), 1),
                "condition": weather["main"],  # Clear, Clouds, Rain, Thunderstorm, etc.
                "description": weather["description"],
                "humidity": main.get("humidity", 0),
                "source": "OpenWeatherMap",
            }
    except Exception as e:
        print(f"Weather API error: {e}")

    return _weather_fallback(city_lower, target_date)


def _weather_fallback(city: str, target_date: str) -> dict:
    """Generate reasonable weather based on city and season when API unavailable."""
    month = int(target_date.split("-")[1])

    # South Indian cities
    south_cities = {"bangalore", "chennai", "mysuru", "coimbatore", "kochi", "madurai", "pondicherry", "vizag", "hyderabad"}
    is_south = any(c in city for c in south_cities)

    if month in (6, 7, 8, 9):  # Monsoon
        condition = "Rain"
        temp = 28 if is_south else 32
        humidity = 85
        desc = "moderate to heavy rain expected"
    elif month in (3, 4, 5):  # Summer
        condition = "Clear"
        temp = 36 if is_south else 40
        humidity = 45
        desc = "hot and sunny"
    elif month in (10, 11):  # Post-monsoon
        condition = "Cloudy"
        temp = 29 if is_south else 27
        humidity = 70
        desc = "partly cloudy, occasional showers"
    else:  # Winter
        condition = "Clear"
        temp = 24 if is_south else 15
        humidity = 55
        desc = "pleasant and cool"

    return {
        "city": city,
        "date": target_date,
        "temperature_high": temp,
        "temperature_low": temp - 7,
        "condition": condition,
        "description": desc,
        "humidity": humidity,
        "source": "seasonal_estimate",
    }


@mlflow.trace(name="check_calendar", span_type="TOOL")
def check_calendar(target_date: str) -> dict:
    """Check if the target date is a holiday, festival, weekend, or Friday.

    Args:
        target_date: ISO date string (e.g., "2026-04-01")

    Returns:
        dict with day_of_week, is_weekend, is_friday, is_holiday, holiday_name, nearby_festivals
    """
    dt = datetime.fromisoformat(target_date)
    day_name = dt.strftime("%A")
    is_weekend = day_name in ("Saturday", "Sunday")
    is_friday = day_name == "Friday"

    # Check exact holiday match
    holiday_name = INDIAN_FESTIVALS_2026.get(target_date)

    # Check nearby festivals (within 3 days) — affects planning
    nearby = []
    for offset in range(-3, 4):
        check_date = (dt + timedelta(days=offset)).strftime("%Y-%m-%d")
        fest = INDIAN_FESTIVALS_2026.get(check_date)
        if fest and check_date != target_date:
            nearby.append({"date": check_date, "festival": fest, "days_away": offset})

    return {
        "date": target_date,
        "day_of_week": day_name,
        "is_weekend": is_weekend,
        "is_friday": is_friday,
        "is_holiday": holiday_name is not None,
        "holiday_name": holiday_name,
        "nearby_festivals": nearby,
    }


@mlflow.trace(name="query_store_patterns", span_type="RETRIEVER")
def query_store_patterns(store_name: str, day_of_week: str) -> dict:
    """Query existing Delta tables for historical sales patterns.

    Runs SQL via the Databricks SQL Statement API against existing
    orders, order_items, products, and promotions tables.

    Args:
        store_name: Store location (e.g., "Koramangala, Bangalore")
        day_of_week: Day name (e.g., "Wednesday")

    Returns:
        dict with top_products, daily_trend, active_promotions
    """
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()

    def _run_sql(sql: str) -> list[dict]:
        url = f"{w.config.host.rstrip('/')}/api/2.0/sql/statements"
        headers = w.config.authenticate()
        headers["Content-Type"] = "application/json"
        resp = requests.post(
            url, headers=headers,
            json={"warehouse_id": SQL_WAREHOUSE_ID, "statement": sql, "wait_timeout": "30s"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status", {}).get("state") != "SUCCEEDED":
            return []
        columns = [c["name"] for c in data.get("manifest", {}).get("schema", {}).get("columns", [])]
        rows = []
        for chunk in data.get("result", {}).get("data_array", []):
            rows.append(dict(zip(columns, chunk)))
        return rows

    # Store name matching — extract location part for LIKE matching
    store_location = store_name.split(",")[0].strip()

    # Query 1: Top products by volume for this day-of-week at this store
    dow_map = {"Monday": 2, "Tuesday": 3, "Wednesday": 4, "Thursday": 5,
               "Friday": 6, "Saturday": 7, "Sunday": 1}
    dow_num = dow_map.get(day_of_week, 4)

    top_products_sql = f"""
    SELECT p.product_name, p.category, CAST(p.price AS STRING) as price,
           CAST(COUNT(oi.order_item_id) AS STRING) as total_sold,
           CAST(ROUND(COUNT(oi.order_item_id) / COUNT(DISTINCT DATE(o.order_date)), 0) AS STRING) as avg_daily_qty
    FROM {CATALOG}.{SCHEMA}.orders o
    JOIN {CATALOG}.{SCHEMA}.order_items oi ON o.order_id = oi.order_id
    JOIN {CATALOG}.{SCHEMA}.products p ON oi.product_id = p.product_id
    JOIN {CATALOG}.{SCHEMA}.stores s ON o.store_id = s.store_id
    WHERE s.store_name LIKE '%{store_location}%'
      AND DAYOFWEEK(o.order_date) = {dow_num}
    GROUP BY p.product_name, p.category, p.price
    ORDER BY COUNT(oi.order_item_id) DESC
    LIMIT 10
    """

    # Query 2: Daily order count + revenue trend (last 30 days)
    daily_trend_sql = f"""
    SELECT CAST(DATE(o.order_date) AS STRING) as day,
           CAST(COUNT(DISTINCT o.order_id) AS STRING) as orders,
           CAST(ROUND(SUM(o.total_amount), 0) AS STRING) as revenue
    FROM {CATALOG}.{SCHEMA}.orders o
    JOIN {CATALOG}.{SCHEMA}.stores s ON o.store_id = s.store_id
    WHERE s.store_name LIKE '%{store_location}%'
      AND o.order_date >= DATE_ADD(CURRENT_DATE(), -30)
    GROUP BY DATE(o.order_date)
    ORDER BY DATE(o.order_date) DESC
    LIMIT 30
    """

    # Query 3: Active promotions
    promotions_sql = f"""
    SELECT promo_name, discount_type, CAST(discount_value AS STRING) as discount_value,
           description, CAST(start_date AS STRING) as start_date,
           CAST(end_date AS STRING) as end_date
    FROM {CATALOG}.{SCHEMA}.promotions
    WHERE start_date <= CURRENT_DATE() AND end_date >= CURRENT_DATE()
    """

    top_products = _run_sql(top_products_sql)
    daily_trend = _run_sql(daily_trend_sql)
    active_promotions = _run_sql(promotions_sql)

    # Compute summary stats from daily trend
    if daily_trend:
        revenues = [float(d["revenue"]) for d in daily_trend if d.get("revenue")]
        orders_list = [int(d["orders"]) for d in daily_trend if d.get("orders")]
        avg_revenue = round(sum(revenues) / len(revenues)) if revenues else 0
        avg_orders = round(sum(orders_list) / len(orders_list)) if orders_list else 0
    else:
        avg_revenue = 0
        avg_orders = 0

    return {
        "store": store_name,
        "day_of_week": day_of_week,
        "top_products": top_products,
        "daily_trend_last_30d": daily_trend[:7],  # Last 7 days for context
        "avg_daily_revenue": avg_revenue,
        "avg_daily_orders": avg_orders,
        "active_promotions": active_promotions,
    }


# =============================================================================
# AGENT
# =============================================================================
SYSTEM_PROMPT = """You are the Kaapi Bricks Operations Advisor — an AI assistant that helps
store managers plan and prepare for upcoming days.

You have access to three data sources:
1. **Live weather forecast** — real-time weather data for any city
2. **Indian holiday & festival calendar** — holidays, weekends, Fridays, and nearby festivals
3. **Historical sales patterns** — product-level sales data from the store's actual transactions

When a store manager asks what to prepare for tomorrow (or any upcoming day):

1. First, get tomorrow's date from the system (today is {today}).
2. Check the weather forecast for the store's city.
3. Check the calendar for holidays, festivals, weekends.
4. Query historical sales patterns for that store on the same day-of-week.
5. REASON across all inputs to generate a preparation plan.

Your output should include:
- **Weather impact**: How weather affects drink preferences (rain → hot drinks up, cold down; heat → cold drinks up)
- **Calendar impact**: Holiday/festival effects (festivals → family visits, higher avg order; weekends → 2-2.5x volume)
- **Product-level forecast table**: For top 8-10 products, show Normal Day estimate vs Tomorrow's estimate with % change and action
- **Expected total orders and revenue**
- **Staffing recommendation**
- **Special preparation notes** (e.g., "Ensure rain-proof delivery packaging", "Stock festive add-ons like cardamom and jaggery")

Always ground your recommendations in the actual historical sales data. Show the numbers.
Format your response with clear headers, a markdown table for the product forecast, and bullet points for actions.
"""


class OperationsAdvisor(ResponsesAgent):
    """Custom ChatAgent that combines weather, calendar, and sales data for store planning."""

    def __init__(self):
        from databricks_langchain import ChatDatabricks

        self.llm = ChatDatabricks(
            endpoint=LLM_ENDPOINT,
            temperature=0.3,
            max_tokens=2000,
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Extract the user's question
        user_message = ""
        store_location = "Koramangala, Bangalore"  # default

        for msg in request.input:
            if msg.role == "user":
                user_message = msg.content
                # Try to extract store from the message context
                if "[Store location:" in user_message:
                    parts = user_message.split("]", 1)
                    store_location = parts[0].replace("[Store location: Kaapi Bricks ", "").strip()
                    user_message = parts[1].strip() if len(parts) > 1 else user_message

        # Determine target date — default to tomorrow
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        target_date = tomorrow.strftime("%Y-%m-%d")

        # Extract city from store location
        city = store_location.split(",")[-1].strip() if "," in store_location else store_location

        # === Call all three tools ===
        weather = get_weather_forecast(city, target_date)
        calendar = check_calendar(target_date)
        patterns = query_store_patterns(store_location, calendar["day_of_week"])

        # === Build context for LLM ===
        context = f"""## Data Collected for {store_location}

### Weather Forecast ({target_date})
{json.dumps(weather, indent=2)}

### Calendar Check ({target_date})
{json.dumps(calendar, indent=2)}

### Historical Sales Patterns (same day-of-week: {calendar['day_of_week']})
**Average daily orders:** {patterns['avg_daily_orders']}
**Average daily revenue:** INR {patterns['avg_daily_revenue']}

**Top products on {calendar['day_of_week']}s:**
{json.dumps(patterns['top_products'], indent=2)}

**Last 7 days trend:**
{json.dumps(patterns['daily_trend_last_30d'], indent=2)}

**Active promotions:**
{json.dumps(patterns['active_promotions'], indent=2)}
"""

        # === Generate recommendation via LLM ===
        system_prompt = SYSTEM_PROMPT.format(today=today.strftime("%Y-%m-%d"))

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_message}\n\n---\n{context}"},
        ]

        response = self.llm.invoke(messages)
        answer = response.content

        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=answer, id="msg_ops")]
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        result = self.predict(request)
        for item in result.output:
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=item,
            )


# Export for MLflow
mlflow.langchain.autolog()
AGENT = OperationsAdvisor()
mlflow.models.set_model(AGENT)
