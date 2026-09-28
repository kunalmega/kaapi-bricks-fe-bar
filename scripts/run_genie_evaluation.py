# Databricks notebook source
# Kaapi Bricks — Genie Agent Evaluation (replaces KA eval after SA/KA deprecation)
# Experiment: 982411422225142

# COMMAND ----------
%pip install -U 'mlflow[databricks]>=3.1'
%restart_python

# COMMAND ----------
import re, time, requests
import mlflow
from mlflow.genai.scorers import Correctness, Safety, RelevanceToQuery, RetrievalGroundedness
from mlflow.entities import Document
from databricks.sdk import WorkspaceClient

GENIE_SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment_id="982411422225142")

# COMMAND ----------
@mlflow.trace
def predict(query: str) -> str:
    w = WorkspaceClient()
    host = w.config.host.rstrip('/')
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    resp = requests.post(
        f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation",
        headers=headers, json={"content": query}, timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    conv_id = data["conversation_id"]
    msg_id  = data["message_id"]

    for _ in range(60):
        poll = requests.get(
            f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conv_id}/messages/{msg_id}",
            headers=headers, timeout=30,
        )
        msg = poll.json()
        status = msg.get("status", "")
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)

    answer_parts, retrieved_docs = [], []
    for att in msg.get("attachments", []):
        if att.get("text"):
            content = att["text"]["content"]
            answer_parts.append(content)
            retrieved_docs.append(Document(id="text", page_content=content, metadata={"source": "genie"}))
        elif att.get("query"):
            desc = att["query"].get("description", "")
            if desc:
                answer_parts.append(desc)
                retrieved_docs.append(Document(id="query", page_content=desc, metadata={"source": "genie_sql"}))

    answer = "\n\n".join(answer_parts) or "No response from Genie."

    @mlflow.trace(span_type="RETRIEVER", name="retriever")
    def retrieve_genie_docs(q: str) -> list:
        return retrieved_docs
    retrieve_genie_docs(query)
    return answer

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
    scorers=[Safety(), RelevanceToQuery(), Correctness(), RetrievalGroundedness()],
)
display(results.tables["eval_results"])

# COMMAND ----------
# Print summary scores for evidence/09
agg = results.metrics
print("\n=== EVALUATION SUMMARY ===")
for k, v in agg.items():
    print(f"  {k}: {v:.3f}")
