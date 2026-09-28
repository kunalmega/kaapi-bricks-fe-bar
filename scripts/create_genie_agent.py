"""Export or apply the Kaapi Bricks Genie Agent configuration.

The Genie space (21 silver + gold tables, the SOP/recipe PDF volume, instructions,
sample questions) is stored as code in resources/genie_space.json.

    # Save the live space config to resources/genie_space.json
    python scripts/create_genie_agent.py --export

    # Apply resources/genie_space.json to an existing space
    python scripts/create_genie_agent.py

    # Create a new space in another workspace/catalog
    python scripts/create_genie_agent.py --create --catalog my_catalog --warehouse-id <id>

The app and the evaluation call this space through the Genie Agent mode API
(POST /api/2.0/genie/agents/{space_id}/responses), which is required for the
agent to read the PDFs in the attached volume.

Replaces scripts/create_agents.py (legacy Knowledge Assistant + Supervisor Agent).
"""
import argparse
import json
import pathlib

import requests
from databricks.sdk import WorkspaceClient

DEFAULT_SPACE_ID = "01f12a63ec1011e0acbb09158eda7634"
DEFAULT_WAREHOUSE = "e755eae9d758fdf7"
SOURCE_CATALOG = "fevm_cme_conde_catalog"
CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "resources" / "genie_space.json"
TITLE = "Kaapi Bricks Store Operations"
DESCRIPTION = ("Governed analytics and SOP Q&A for Kaapi Bricks store managers — "
               "37 stores, South Indian filter coffee.")


def main():
    parser = argparse.ArgumentParser(description="Export or apply the Kaapi Bricks Genie space")
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID)
    parser.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE)
    parser.add_argument("--catalog", default=SOURCE_CATALOG,
                        help="Target catalog; table and volume paths are rewritten to it")
    parser.add_argument("--export", action="store_true", help="Save the live space to resources/genie_space.json")
    parser.add_argument("--create", action="store_true", help="Create a new space instead of updating --space-id")
    args = parser.parse_args()

    w = WorkspaceClient(profile=args.profile)
    host = w.config.host.rstrip("/")
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"

    if args.export:
        resp = requests.get(f"{host}/api/2.0/genie/spaces/{args.space_id}",
                            params={"include_serialized_space": "true"}, headers=headers, timeout=30)
        resp.raise_for_status()
        space = json.loads(resp.json()["serialized_space"])
        CONFIG_PATH.write_text(json.dumps(space, indent=2) + "\n")
        print(f"Exported space {args.space_id} to {CONFIG_PATH}")
        print(f"  tables : {len(space.get('data_sources', {}).get('tables', []))}")
        print(f"  volumes: {[v.get('path') for v in space.get('data_sources', {}).get('volumes', [])]}")
        return

    serialized = CONFIG_PATH.read_text()
    if args.catalog != SOURCE_CATALOG:
        serialized = serialized.replace(f"{SOURCE_CATALOG}.", f"{args.catalog}.")
        serialized = serialized.replace(f"/Volumes/{SOURCE_CATALOG}/", f"/Volumes/{args.catalog}/")
    serialized = json.dumps(json.loads(serialized))  # the API expects a JSON string

    body = {"title": TITLE, "description": DESCRIPTION,
            "warehouse_id": args.warehouse_id, "serialized_space": serialized}
    if args.create:
        resp = requests.post(f"{host}/api/2.0/genie/spaces", headers=headers, json=body, timeout=60)
    else:
        resp = requests.patch(f"{host}/api/2.0/genie/spaces/{args.space_id}", headers=headers,
                              json=body, timeout=60)
    if not resp.ok:
        raise SystemExit(f"Genie API error {resp.status_code}: {resp.text[:500]}")

    result = resp.json()
    space_id = result.get("space_id", args.space_id)
    space = json.loads(result.get("serialized_space", serialized))
    print(f"{'Created' if args.create else 'Updated'} Genie space {space_id}")
    print(f"  tables : {len(space.get('data_sources', {}).get('tables', []))}")
    print(f"  volumes: {[v.get('path') for v in space.get('data_sources', {}).get('volumes', [])]}")
    if args.create:
        print("Set GENIE_SPACE_ID in apps/main-chat-app/app.yaml to the new space ID and redeploy the app.")


if __name__ == "__main__":
    main()
