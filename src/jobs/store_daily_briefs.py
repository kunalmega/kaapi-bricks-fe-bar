"""Write each store manager's morning action plan from the gold KPI tables.

SQL computes every number (stock, overdue POs, late deliveries, waste, today's forecast);
the LLM (kaapi_llm through Unity AI Gateway) only ranks and words the actions. A
deterministic check then confirms every number in the brief appears in the facts it was
given. Each brief is traced in MLflow and written to Delta store_daily_briefs, then
synced to Lakebase for the Live Dashboard.

Run: python src/jobs/store_daily_briefs.py [--stores STR-001,STR-002]
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

# Job tasks exec the file without __file__; the code object still knows its path.
HERE = os.path.dirname(os.path.abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, HERE)

import mlflow

from common import FQ, GW_LLM_MODEL, gateway_chat, insert_rows, sql

EXPERIMENT = os.environ.get("KAAPI_BRIEF_EXPERIMENT", "/Shared/kaapi_bricks_store_briefs")

SYSTEM = """You write the morning action plan for a Kaapi Bricks filter-coffee store manager.
Use ONLY the facts in the JSON you are given. Every number you write must appear in the facts
exactly as given (you may round money to whole rupees). Never add, subtract or count numbers
yourself: for totals use overdue_total. Do not invent suppliers, items or numbers.
Return JSON only: {"headline": "<one sentence, max 20 words>",
 "actions": [{"priority": 1, "action": "<imperative, max 18 words>", "why": "<the fact behind it, max 22 words>"}]}
Give 3 to 5 actions, most urgent first: stock about to run out, overdue supplier orders,
today's demand, then waste."""


def gather_facts(today: date) -> dict:
    d = today.isoformat()
    facts = {r["store_id"]: {"store": r["name"], "date": d, "weekday": today.strftime("%A"),
                             "low_stock": [], "overdue_pos": [], "today_forecast": [], "top_waste": None}
             for r in sql(f"SELECT store_id, name FROM {FQ}.stores")}
    for r in sql(f"""SELECT store_id, ingredient_name, unit, current_stock, reorder_threshold, days_cover,
                       ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY days_cover) AS rn
                     FROM {FQ}.gold_inventory_position WHERE below_reorder QUALIFY rn <= 4"""):
        facts[r["store_id"]]["low_stock"].append(
            {"item": r["ingredient_name"], "stock": f"{float(r['current_stock']):g} {r['unit']}",
             "reorder_level": f"{float(r['reorder_threshold']):g} {r['unit']}", "days_cover": r["days_cover"]})
    for r in sql(f"""SELECT store_id, po_id, supplier_name, ROUND(total_amount) AS amount,
                       datediff(current_date(), expected_delivery_date) AS days_overdue,
                       ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY total_amount DESC) AS rn
                     FROM {FQ}.gold_open_purchase_orders
                     WHERE expected_delivery_date < current_date() QUALIFY rn <= 3"""):
        facts[r["store_id"]]["overdue_pos"].append(
            {"po": r["po_id"], "supplier": r["supplier_name"], "amount_inr": int(float(r["amount"])),
             "days_overdue": int(r["days_overdue"])})
    for r in sql(f"""SELECT store_id, COUNT(*) AS n, ROUND(SUM(total_amount)) AS v
                     FROM {FQ}.gold_open_purchase_orders WHERE expected_delivery_date < current_date()
                     GROUP BY store_id"""):
        facts[r["store_id"]]["overdue_total"] = {"count": int(r["n"]), "value_inr": int(float(r["v"]))}
    for r in sql(f"""SELECT store_id, product_name, ROUND(forecast_units, 1) AS f,
                       ROUND(baseline_same_weekday, 1) AS b, is_holiday,
                       ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY forecast_units DESC) AS rn
                     FROM {FQ}.ml_demand_forecast WHERE forecast_date = DATE'{d}' QUALIFY rn <= 4"""):
        facts[r["store_id"]]["today_forecast"].append(
            {"drink": r["product_name"], "forecast_units": float(r["f"]),
             "usual_for_this_weekday": None if r["b"] is None else float(r["b"]),
             "holiday": r["is_holiday"] == "1"})
    for r in sql(f"""SELECT store_id, ingredient_name, ROUND(waste_cost) AS c,
                       ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY waste_cost DESC) AS rn
                     FROM {FQ}.gold_waste_summary QUALIFY rn = 1"""):
        facts[r["store_id"]]["top_waste"] = {"item": r["ingredient_name"], "waste_cost_inr": int(float(r["c"]))}
    return facts


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def number_check(text: str, facts: dict) -> tuple[int, int, list[str]]:
    """Every number in the brief must exist in the facts (ignoring commas; ±0.5 for rounding)."""
    known = [float(x.replace(",", "")) for x in _NUM.findall(json.dumps(facts))]
    found = [x for x in _NUM.findall(text)]
    bad = [x for x in found if not any(abs(float(x.replace(",", "")) - k) <= 0.5 for k in known)]
    return len(found), len(found) - len(bad), bad


@mlflow.trace(name="store_daily_brief", span_type="CHAIN")
def write_brief(store_id: str, facts: dict) -> dict:
    """Write the brief; if the number check fails, retry once telling the model what was wrong."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(facts)}]
    for attempt in (1, 2):
        text = gateway_chat(messages)["choices"][0]["message"]["content"]
        brief = json.loads(text[text.find("{"): text.rfind("}") + 1])
        rendered = brief["headline"] + " " + " ".join(a["action"] + " " + a["why"] for a in brief["actions"])
        checked, grounded, bad = number_check(rendered, facts)
        if not bad:
            break
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"These numbers are not in the facts: {bad}. "
                                                 "Rewrite using only numbers that appear in the facts."}]
    mlflow.update_current_trace(tags={"store_id": store_id, "numbers_grounded": f"{grounded}/{checked}",
                                      "attempts": str(attempt)})
    return {"store_id": store_id, "brief": brief, "checked": checked, "grounded": grounded, "ungrounded": bad,
            "attempts": attempt, "trace_id": mlflow.get_current_active_span().trace_id}


def main(stores: list[str] | None = None):
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(EXPERIMENT)
    today = date.today()
    facts = gather_facts(today)
    targets = stores or sorted(facts)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda s: write_brief(s, facts[s]), targets))

    sql(f"""CREATE TABLE IF NOT EXISTS {FQ}.store_daily_briefs (
              brief_date DATE, store_id STRING, store_name STRING, headline STRING, actions_json STRING,
              facts_json STRING, numbers_checked INT, numbers_grounded INT, model STRING, trace_id STRING,
              created_at TIMESTAMP)
            COMMENT 'Morning action plan per store: numbers from gold SQL, wording from kaapi_llm (AI Gateway).'""")
    sql(f"DELETE FROM {FQ}.store_daily_briefs WHERE brief_date = DATE'{today}'"
        + (f" AND store_id IN ({', '.join(repr(s) for s in targets)})" if stores else ""))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    insert_rows("store_daily_briefs",
                ["brief_date", "store_id", "store_name", "headline", "actions_json", "facts_json",
                 "numbers_checked", "numbers_grounded", "model", "trace_id", "created_at"],
                [(today.isoformat(), r["store_id"], facts[r["store_id"]]["store"], r["brief"]["headline"],
                  json.dumps(r["brief"]["actions"]), json.dumps(facts[r["store_id"]]), r["checked"],
                  r["grounded"], GW_LLM_MODEL.split(".")[-1], r["trace_id"], now) for r in results])

    checked = sum(r["checked"] for r in results)
    grounded = sum(r["grounded"] for r in results)
    retried = sum(1 for r in results if r["attempts"] > 1)
    print(f"{len(results)} briefs for {today}; numbers grounded in facts: {grounded}/{checked}; "
          f"{retried} brief(s) rewritten after a failed number check")
    for r in results:
        if r["ungrounded"]:
            print(f"  {r['store_id']}: ungrounded numbers {r['ungrounded']}")
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stores", default=None)
    a, _ = p.parse_known_args()
    main(a.stores.split(",") if a.stores else None)
