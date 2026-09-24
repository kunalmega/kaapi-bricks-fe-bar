"""Deploy the Operations Advisor agent to Databricks Model Serving.

Usage:
    python deploy.py

This logs the agent to MLflow, registers it in Unity Catalog, and deploys
it as a serving endpoint. The endpoint can then be added to the MAS Supervisor.
"""

import mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksSQLWarehouse
from databricks import agents

# Configuration
REGISTERED_MODEL_NAME = "fevm_cme_conde_catalog.kaapi_bricks.operations_advisor"
LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"
SQL_WAREHOUSE_ID = "e755eae9d758fdf7"

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")

# Resources the agent needs access to
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT),
    DatabricksSQLWarehouse(warehouse_id=SQL_WAREHOUSE_ID),
]

print("Logging agent to MLflow...")
with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        name="operations-advisor",
        python_model="agent.py",
        resources=resources,
        pip_requirements=[
            "mlflow[databricks]>=3.8",
            "databricks-sdk>=0.38.0",
            "databricks-langchain",
            "requests",
        ],
        input_example={
            "input": [{"role": "user", "content": "What should I prepare for tomorrow at Koramangala?"}]
        },
        registered_model_name=REGISTERED_MODEL_NAME,
    )
    print(f"Model logged: {model_info.model_uri}")

# Deploy to serving endpoint
print("Deploying to serving endpoint (this takes ~15 minutes)...")
deployment = agents.deploy(
    REGISTERED_MODEL_NAME,
    version=model_info.registered_model_version,
    tags={"source": "ai-days-demo", "agent_type": "operations-advisor"},
)
print(f"Deployment started. Endpoint: {deployment.endpoint_name}")
print("Monitor at: Workspace > Serving > Endpoints")
