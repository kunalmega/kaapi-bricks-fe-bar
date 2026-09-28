# Databricks notebook source
# Kaapi Bricks — Genie Agent (Agent mode) Evaluation (replaces KA eval after SA/KA deprecation)
# Experiment: 982411422225142

# COMMAND ----------
%pip install -U 'mlflow[databricks]>=3.1'
%restart_python

# COMMAND ----------
import re, json, requests
import mlflow
from mlflow.genai.scorers import Correctness, Safety, RelevanceToQuery
from databricks.sdk import WorkspaceClient

GENIE_SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment_id="982411422225142")

# COMMAND ----------
# Agent mode API: required for Genie to read the SOP/recipe PDFs in the attached volume.
# (The Chat-mode start-conversation API only sees structured tables.)
@mlflow.trace
def predict(query: str) -> str:
    w = WorkspaceClient()
    host = w.config.host.rstrip('/')
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "text/event-stream"

    resp = requests.post(
        f"{host}/api/2.0/genie/agents/{GENIE_SPACE_ID}/responses",
        headers=headers,
        json={"input": [{"type": "message", "role": "user",
                         "content": [{"type": "input_text", "text": query}]}]},
        stream=True, timeout=300,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"

    final = {}
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            try:
                event = json.loads(line[5:].strip())
            except ValueError:
                continue
            if event.get("type") in ("response.completed", "response.failed"):
                final = event.get("response", {})

    parts = [b["text"] for item in final.get("output", []) if item.get("type") == "message"
             for b in item.get("content", []) if b.get("type") == "output_text" and b.get("text")]
    answer = re.sub(r"\s*:citation\[[^\]]*\]", "", "\n\n".join(parts)).strip()
    return answer or "No response from Genie."

# COMMAND ----------
eval_dataset = [
    {"inputs": {"query": "How do I make a Classic Filter Coffee?"}, "expectations": {"expected_facts": ["Uses 30ml freshly dripped decoction", "House blend is 70% Chikmagalur Robusta + 30% Chicory", "Brewed at 92-96 degrees C, dripped 12-15 minutes", "120ml hot full cream milk", "Serve in tumbler-davara with 3-4 pours for froth", "Price is Rs.60"]}},
    {"inputs": {"query": "What is the correct decoction ratio and timing?"}, "expectations": {"expected_facts": ["2 heaped tablespoons (20g) of house blend per 150ml water", "Water temperature 92-96 degrees C", "Drip for 12-15 minutes", "Maximum hold time is 4 hours"]}},
    {"inputs": {"query": "What should a barista do if a customer reports a nut allergy?"}, "expectations": {"expected_facts": ["Confirm the specific allergen", "Check all ingredients including syrups and add-ons", "Use freshly cleaned equipment to prevent cross-contact", "If unsure, consult the manager before preparing the drink"]}},
    {"inputs": {"query": "How long does Coorg Arabica take to reorder?"}, "expectations": {"expected_facts": ["Lead time is 7 days", "Supplier is Coorg Coffee Estates", "Minimum order is 50 kg"]}},
    {"inputs": {"query": "At what temperature should milk be stored?"}, "expectations": {"expected_facts": ["Full Cream Milk must be refrigerated at 2-4 degrees C", "Use within 2 days of delivery", "Refrigerator must be below 4 degrees C"]}},
    {"inputs": {"query": "How do I clean the brass filter coffee maker?"}, "expectations": {"expected_facts": ["After each batch: rinse both chambers with hot water", "End of day: disassemble, wash with warm soapy water, air dry upside down", "Weekly: soak in baking soda solution for 30 minutes", "Never use abrasive scrubbers"]}},
    {"inputs": {"query": "How can I open a Kaapi Bricks franchise?"}, "expectations": {"expected_facts": ["Kaapi Bricks expands through a franchise model", "Available across India and select international markets"]}},
    {"inputs": {"query": "How do I make Masala Chai?"}, "expectations": {"expected_facts": ["Uses Kerala spice blend with cardamom, ginger, and cinnamon", "Price is Rs.50"]}},
    {"inputs": {"query": "Who supplies our milk and what are their delivery terms?"}, "expectations": {"expected_facts": ["Nandini Dairy (SUP-004)", "Supplies Full Cream Milk and Toned Milk"]}},
    {"inputs": {"query": "How long can prepared decoction be kept before discarding?"}, "expectations": {"expected_facts": ["Maximum 4 hours for prepared decoction", "After 4 hours the coffee oxidizes and tastes stale"]}},
]

# COMMAND ----------
results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict,
    scorers=[Safety(), RelevanceToQuery(), Correctness()],
)
display(results.tables["eval_results"])

# COMMAND ----------
# Print summary scores for evidence/09
agg = results.metrics
print("\n=== EVALUATION SUMMARY ===")
for k, v in agg.items():
    print(f"  {k}: {v:.3f}")
