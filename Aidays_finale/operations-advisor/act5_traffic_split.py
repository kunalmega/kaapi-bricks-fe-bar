"""Act 5: CI/CD for AI — Traffic splitting on the Operations Advisor endpoint.

Demonstrates routing 10% of traffic to a challenger model while keeping
90% on the current model. This is the CI/CD story for AI agents.

Usage:
    python act5_traffic_split.py show        # Show current config
    python act5_traffic_split.py split       # Apply 90/10 split
    python act5_traffic_split.py promote     # Promote challenger to 100%
    python act5_traffic_split.py rollback    # Rollback to original 100%
"""

import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    ServedEntityInput,
    TrafficConfig,
    Route,
)

# The Operations Advisor endpoint (created by deploy.py)
# Update this after deployment with the actual endpoint name
ENDPOINT_NAME = "operations-advisor-endpoint"
MODEL_NAME = "fevm_cme_conde_catalog.kaapi_bricks.operations_advisor"

# Current model version (update after deployment)
CURRENT_VERSION = "1"
CHALLENGER_VERSION = "2"  # Deploy with a different LLM (e.g., Claude) as v2

w = WorkspaceClient()


def show_config():
    """Show current endpoint configuration and traffic routing."""
    endpoint = w.serving_endpoints.get(ENDPOINT_NAME)
    print(f"\n  Endpoint: {ENDPOINT_NAME}")
    print(f"  State: {endpoint.state.ready}")

    config = endpoint.config
    if config and config.served_entities:
        print(f"\n  Served Entities:")
        for entity in config.served_entities:
            print(f"    - {entity.name} (model: {entity.entity_name}, version: {entity.entity_version})")

    if config and config.traffic_config:
        print(f"\n  Traffic Config:")
        for route in config.traffic_config.routes:
            print(f"    - {route.served_model_name}: {route.traffic_percentage}%")
    else:
        print("\n  Traffic: 100% to default entity")


def apply_split():
    """Apply 90/10 traffic split between current and challenger."""
    print(f"\n  Applying 90/10 traffic split...")
    print(f"    Current (v{CURRENT_VERSION}): 90%")
    print(f"    Challenger (v{CHALLENGER_VERSION}): 10%")

    w.serving_endpoints.update_config(
        name=ENDPOINT_NAME,
        served_entities=[
            ServedEntityInput(
                name="current",
                entity_name=MODEL_NAME,
                entity_version=CURRENT_VERSION,
                scale_to_zero_enabled=True,
            ),
            ServedEntityInput(
                name="challenger",
                entity_name=MODEL_NAME,
                entity_version=CHALLENGER_VERSION,
                scale_to_zero_enabled=True,
            ),
        ],
        traffic_config=TrafficConfig(
            routes=[
                Route(served_model_name="current", traffic_percentage=90),
                Route(served_model_name="challenger", traffic_percentage=10),
            ]
        ),
    )
    print("  Done. Both models now serving live traffic.")
    print("  Monitor quality in MLflow and the Lakeview dashboard.")


def promote_challenger():
    """Promote challenger to 100% — the new model won."""
    print(f"\n  Promoting challenger (v{CHALLENGER_VERSION}) to 100%...")
    w.serving_endpoints.update_config(
        name=ENDPOINT_NAME,
        served_entities=[
            ServedEntityInput(
                name="promoted",
                entity_name=MODEL_NAME,
                entity_version=CHALLENGER_VERSION,
                scale_to_zero_enabled=True,
            ),
        ],
        traffic_config=TrafficConfig(
            routes=[
                Route(served_model_name="promoted", traffic_percentage=100),
            ]
        ),
    )
    print("  Done. Challenger is now the primary model.")


def rollback():
    """Rollback to original model — the challenger didn't perform."""
    print(f"\n  Rolling back to current (v{CURRENT_VERSION}) at 100%...")
    w.serving_endpoints.update_config(
        name=ENDPOINT_NAME,
        served_entities=[
            ServedEntityInput(
                name="current",
                entity_name=MODEL_NAME,
                entity_version=CURRENT_VERSION,
                scale_to_zero_enabled=True,
            ),
        ],
        traffic_config=TrafficConfig(
            routes=[
                Route(served_model_name="current", traffic_percentage=100),
            ]
        ),
    )
    print("  Done. Rolled back to original model. Zero downtime.")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "show"

    print(f"\n{'='*50}")
    print(f"  Act 5: CI/CD for AI — Traffic Splitting")
    print(f"{'='*50}")

    if action == "show":
        show_config()
    elif action == "split":
        apply_split()
    elif action == "promote":
        promote_challenger()
    elif action == "rollback":
        rollback()
    else:
        print(f"  Unknown action: {action}")
        print(f"  Usage: python act5_traffic_split.py [show|split|promote|rollback]")
