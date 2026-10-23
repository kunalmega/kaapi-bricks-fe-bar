"""Populate the row-level security mapping (store_access) for this workspace.

HQ (*): you (the pipeline owner, who also runs the sync and ops job), the two app service
principals, and the eval runner. Store-scoped: the demo store manager principal for STR-001.
Run after scripts/setup_row_level_security.sql:
    python scripts/apply_store_access.py --profile DEFAULT
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "jobs"))
p = argparse.ArgumentParser()
p.add_argument("--profile", default=None)
p.add_argument("--store-manager-sp", default="kaapi-store-manager-str001")
p.add_argument("--store-id", default="STR-001")
args = p.parse_args()
if args.profile:
    os.environ["DATABRICKS_CONFIG_PROFILE"] = args.profile

from common import FQ, sql, ws  # noqa: E402

w = ws()


def sp_app_id(display_name):
    sps = list(w.service_principals.list(filter=f'displayName eq "{display_name}"'))
    return sps[0].application_id if sps else None


rows = [(w.current_user.me().user_name, "*", "hq")]
for app in ("kaapi-bricks-finale", "kaapi-ops-mcp"):
    rows.append((w.apps.get(app).service_principal_client_id, "*", f"app:{app}"))
for name, store, role in (("kaapi-eval-runner", "*", "eval"),
                          (args.store_manager_sp, args.store_id, "store_manager")):
    if (app_id := sp_app_id(name)):
        rows.append((app_id, store, role))
    else:
        print(f"  (service principal {name} not found; skipped)")

sql(f"DELETE FROM {FQ}.store_access")
values = ", ".join(f"('{pr}', '{st}', '{ro}')" for pr, st, ro in rows)
sql(f"INSERT INTO {FQ}.store_access (principal, store_id, role) VALUES {values}")
for r in sql(f"SELECT role, store_id FROM {FQ}.store_access ORDER BY store_id, role"):
    print(f"  {r['role']:<28} → {r['store_id']}")
