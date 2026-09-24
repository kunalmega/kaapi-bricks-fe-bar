#!/bin/bash
# ================================================================
# Kaapi Bricks Demo — Deploy to Any Workspace
# ================================================================
# Usage:
#   ./deploy.sh <profile> <catalog> <warehouse_id>
#
# Example:
#   ./deploy.sh fevm-india-gcc fe_india_gcc_catalog 13a6b534c35ffbcb
#   ./deploy.sh DEFAULT fevm_cme_conde_catalog e755eae9d758fdf7
#
# What this script does (fully automated):
#   1. Creates both Databricks Apps (main chat + MCP server)
#   2. Replaces catalog/warehouse in app code
#   3. Deploys both apps
#   4. Syncs data gen + eval scripts to workspace
#   5. Creates schema + volumes in Unity Catalog
#   6. Runs data generation as serverless jobs (14 tables + 6 PDFs)
#   7. Creates Lakebase instance
#   8. Creates po_line_items table
#   9. Grants all permissions (UC, Lakebase, Apps) to both app SPs
#
# After this script, only 4 manual steps remain:
#   - Create KA in Agent Bricks UI
#   - Create Genie Space in SQL UI
#   - Create MAS Supervisor in Agent Bricks UI
#   - Update main app resources with endpoint names
# ================================================================

set -e

PROFILE=${1:?"Usage: ./deploy.sh <profile> <catalog> <warehouse_id>"}
CATALOG=${2:?"Usage: ./deploy.sh <profile> <catalog> <warehouse_id>"}
WAREHOUSE_ID=${3:?"Usage: ./deploy.sh <profile> <catalog> <warehouse_id>"}
SCHEMA="kaapi_bricks"
LAKEBASE_INSTANCE="kaapi-bricks"
MAIN_APP="kaapi-bricks-finale"
MCP_APP="kaapi-ops-mcp"

DIR="$(cd "$(dirname "$0")" && pwd)"
USER_EMAIL=$(databricks current-user me --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('userName',''))" 2>/dev/null || echo "")
if [ -z "$USER_EMAIL" ]; then
  USER_EMAIL=$(databricks auth env --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('env',{}).get('DATABRICKS_USER','unknown'))" 2>/dev/null || echo "unknown")
fi
WS_PATH="/Workspace/Users/$USER_EMAIL"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          KAAPI BRICKS DEMO — DEPLOYING                  ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Profile:    $PROFILE"
echo "║  Catalog:    $CATALOG"
echo "║  Warehouse:  $WAREHOUSE_ID"
echo "║  Workspace:  $WS_PATH"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ---- Step 1: Prepare app code with correct catalog ----
echo "→ Preparing app code for $CATALOG..."
TMPDIR=$(mktemp -d)
cp -r "$DIR/apps/main-chat-app" "$TMPDIR/main-chat-app"
cp -r "$DIR/apps/mcp-server" "$TMPDIR/mcp-server"

# Replace catalog + warehouse in main app
sed -i '' "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/main-chat-app/app.py" 2>/dev/null || sed -i "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/main-chat-app/app.py"
sed -i '' "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/main-chat-app/app.py" 2>/dev/null || sed -i "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/main-chat-app/app.py"
sed -i '' "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/main-chat-app/app.yaml" 2>/dev/null || sed -i "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/main-chat-app/app.yaml"

# Replace warehouse in MCP app
sed -i '' "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/mcp-server/app.py" 2>/dev/null || sed -i "s/e755eae9d758fdf7/$WAREHOUSE_ID/g" "$TMPDIR/mcp-server/app.py"

echo "  ✓ Catalog: $CATALOG | Warehouse: $WAREHOUSE_ID"

# ---- Step 2: Create Databricks Apps ----
echo ""
echo "→ Creating Databricks Apps..."
databricks apps create kaapi-bricks-finale --profile "$PROFILE" --description "Kaapi Bricks Demo - Main Chat" 2>/dev/null || echo "  (kaapi-bricks-finale already exists)"
databricks apps create kaapi-ops-mcp --profile "$PROFILE" --description "Kaapi Bricks Operations Advisor MCP Server" 2>/dev/null || echo "  (kaapi-ops-mcp already exists)"
echo "  ✓ Apps created"

# ---- Step 3: Wait for compute ----
echo ""
echo "→ Waiting for app compute to start..."
for i in $(seq 1 24); do
  STATE1=$(databricks apps get kaapi-bricks-finale --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('compute_status',{}).get('state',''))" 2>/dev/null || echo "UNKNOWN")
  STATE2=$(databricks apps get kaapi-ops-mcp --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('compute_status',{}).get('state',''))" 2>/dev/null || echo "UNKNOWN")
  echo "  [$i] main=$STATE1 mcp=$STATE2"
  if [ "$STATE1" = "ACTIVE" ] && [ "$STATE2" = "ACTIVE" ]; then
    break
  fi
  sleep 10
done

# ---- Step 4: Sync and deploy main chat app ----
echo ""
echo "→ Deploying main chat app..."
databricks sync "$TMPDIR/main-chat-app" "$WS_PATH/kaapi-bricks-finale" --profile "$PROFILE" 2>&1 | tail -1
databricks apps deploy kaapi-bricks-finale --source-code-path "$WS_PATH/kaapi-bricks-finale" --profile "$PROFILE" 2>&1 | grep -E "state|Error"

# ---- Step 5: Sync and deploy MCP server ----
echo ""
echo "→ Deploying MCP server..."
databricks sync "$TMPDIR/mcp-server" "$WS_PATH/kaapi-ops-mcp" --profile "$PROFILE" 2>&1 | tail -1
databricks apps deploy kaapi-ops-mcp --source-code-path "$WS_PATH/kaapi-ops-mcp" --profile "$PROFILE" 2>&1 | grep -E "state|Error"

# ---- Step 6: Sync setup scripts ----
echo ""
echo "→ Syncing data generation scripts..."
databricks workspace mkdirs "$WS_PATH/kaapi-bricks-setup" --profile "$PROFILE" 2>/dev/null

# Update catalog in scripts
cp "$DIR/scripts/generate_data.py" "$TMPDIR/generate_data.py"
cp "$DIR/scripts/generate_ka_documents.py" "$TMPDIR/generate_ka_documents.py"
sed -i '' "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/generate_data.py" 2>/dev/null || sed -i "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/generate_data.py"
sed -i '' "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/generate_ka_documents.py" 2>/dev/null || sed -i "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/generate_ka_documents.py"

databricks workspace import "$WS_PATH/kaapi-bricks-setup/generate_data" --file "$TMPDIR/generate_data.py" --format SOURCE --language PYTHON --overwrite --profile "$PROFILE" 2>&1
databricks workspace import "$WS_PATH/kaapi-bricks-setup/generate_ka_documents" --file "$TMPDIR/generate_ka_documents.py" --format SOURCE --language PYTHON --overwrite --profile "$PROFILE" 2>&1

# Sync eval scripts
for f in run_ka_evaluation.ipynb run_ka_evaluation_incorrect.ipynb run_mas_evaluation.ipynb run_mas_evaluation_incorrect.ipynb; do
  if [ -f "$DIR/scripts/$f" ]; then
    name="${f%.ipynb}"
    databricks workspace import "$WS_PATH/kaapi-bricks-setup/$name" --file "$DIR/scripts/$f" --format JUPYTER --overwrite --profile "$PROFILE" 2>&1
  fi
done

echo "  ✓ Scripts synced to $WS_PATH/kaapi-bricks-setup/"

# ---- Step 7: Create schema + volumes ----
echo ""
echo "→ Creating schema and volumes..."
for SQL in \
  "CREATE SCHEMA IF NOT EXISTS $CATALOG.kaapi_bricks" \
  "CREATE VOLUME IF NOT EXISTS $CATALOG.kaapi_bricks.raw_data" \
  "CREATE VOLUME IF NOT EXISTS $CATALOG.kaapi_bricks.invoices"; do
  databricks api post "/api/2.0/sql/statements" --profile "$PROFILE" --json "{
    \"warehouse_id\": \"$WAREHOUSE_ID\",
    \"statement\": \"$SQL\",
    \"wait_timeout\": \"30s\"
  }" 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  {d.get(\"status\",{}).get(\"state\",\"?\")}: $SQL')" 2>/dev/null
done

# ---- Step 8: Run data generation as serverless jobs ----
echo ""
echo "→ Running data generation (serverless jobs)..."

# Create and run generate_data job
echo "  Starting generate_data job..."
JOB1_ID=$(databricks api post "/api/2.0/jobs/create" --profile "$PROFILE" --json "{
  \"name\": \"kaapi-bricks-generate-data\",
  \"tasks\": [{
    \"task_key\": \"generate_data\",
    \"notebook_task\": {\"notebook_path\": \"$WS_PATH/kaapi-bricks-setup/generate_data\"},
    \"environment_key\": \"default\"
  }],
  \"environments\": [{
    \"environment_key\": \"default\",
    \"spec\": {
      \"client\": \"2\",
      \"dependencies\": [\"faker\", \"holidays\", \"numpy\", \"pandas\", \"pyarrow\"]
    }
  }],
  \"queue\": {\"enabled\": true}
}" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)

if [ -n "$JOB1_ID" ]; then
  RUN1_ID=$(databricks api post "/api/2.0/jobs/run-now" --profile "$PROFILE" --json "{\"job_id\": $JOB1_ID}" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))" 2>/dev/null)
  echo "  ✓ generate_data job started (job=$JOB1_ID, run=$RUN1_ID)"
else
  echo "  ✗ Failed to create generate_data job. Run notebook manually."
fi

# Create and run generate_ka_documents job
echo "  Starting generate_ka_documents job..."
JOB2_ID=$(databricks api post "/api/2.0/jobs/create" --profile "$PROFILE" --json "{
  \"name\": \"kaapi-bricks-generate-ka-docs\",
  \"tasks\": [{
    \"task_key\": \"generate_ka_docs\",
    \"notebook_task\": {\"notebook_path\": \"$WS_PATH/kaapi-bricks-setup/generate_ka_documents\"},
    \"environment_key\": \"default\"
  }],
  \"environments\": [{
    \"environment_key\": \"default\",
    \"spec\": {
      \"client\": \"2\",
      \"dependencies\": [\"fpdf2\"]
    }
  }],
  \"queue\": {\"enabled\": true}
}" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)

if [ -n "$JOB2_ID" ]; then
  RUN2_ID=$(databricks api post "/api/2.0/jobs/run-now" --profile "$PROFILE" --json "{\"job_id\": $JOB2_ID}" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))" 2>/dev/null)
  echo "  ✓ generate_ka_documents job started (job=$JOB2_ID, run=$RUN2_ID)"
else
  echo "  ✗ Failed to create ka_documents job. Run notebook manually."
fi

# Wait for jobs to complete
if [ -n "$RUN1_ID" ] || [ -n "$RUN2_ID" ]; then
  echo ""
  echo "→ Waiting for data generation jobs to complete (~5-10 min)..."
  for i in $(seq 1 60); do
    DONE=true
    if [ -n "$RUN1_ID" ]; then
      S1=$(databricks api get "/api/2.0/jobs/runs/get?run_id=$RUN1_ID" --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state',{}).get('life_cycle_state',''))" 2>/dev/null)
      if [ "$S1" != "TERMINATED" ] && [ "$S1" != "SKIPPED" ] && [ "$S1" != "INTERNAL_ERROR" ]; then DONE=false; fi
    fi
    if [ -n "$RUN2_ID" ]; then
      S2=$(databricks api get "/api/2.0/jobs/runs/get?run_id=$RUN2_ID" --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state',{}).get('life_cycle_state',''))" 2>/dev/null)
      if [ "$S2" != "TERMINATED" ] && [ "$S2" != "SKIPPED" ] && [ "$S2" != "INTERNAL_ERROR" ]; then DONE=false; fi
    fi
    echo "  [$i] data=${S1:-n/a} ka_docs=${S2:-n/a}"
    if $DONE; then
      echo "  ✓ All data generation jobs complete"
      break
    fi
    sleep 15
  done
fi

# ---- Step 9: Create Lakebase instance + permissions ----
echo ""
echo "→ Setting up Lakebase..."
databricks api post "/api/2.0/database/instances" --profile "$PROFILE" --json '{"name": "kaapi-bricks", "capacity": "CU_1"}' 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Lakebase: {d.get(\"name\",\"?\")} — {d.get(\"state\",\"already exists\")}')" 2>/dev/null || echo "  Lakebase kaapi-bricks already exists"

# Get app SPs
MAIN_SP=$(databricks apps get kaapi-bricks-finale --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('service_principal_client_id',''))" 2>/dev/null || echo "")
MCP_SP=$(databricks apps get kaapi-ops-mcp --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('service_principal_client_id',''))" 2>/dev/null || echo "")
echo "  Main app SP: $MAIN_SP"
echo "  MCP app SP:  $MCP_SP"

# Wait for Lakebase to be AVAILABLE before creating roles (this fixes the common race-condition error)
echo "  Waiting for Lakebase instance to become AVAILABLE..."
for i in $(seq 1 40); do
  LB_STATE=$(databricks api get "/api/2.0/database/instances/kaapi-bricks" --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('state',''))" 2>/dev/null || echo "")
  echo "  [$i] Lakebase state=$LB_STATE"
  if [ "$LB_STATE" = "AVAILABLE" ]; then
    break
  fi
  if [ "$LB_STATE" = "FAILED" ] || [ "$LB_STATE" = "DELETED" ]; then
    echo "  ✗ Lakebase reached terminal state $LB_STATE — aborting role creation"
    break
  fi
  sleep 15
done

# Create Lakebase roles for both app SPs (only if instance AVAILABLE)
if [ "$LB_STATE" = "AVAILABLE" ]; then
  echo "  Creating Lakebase roles..."
  for SP in "$MAIN_SP" "$MCP_SP"; do
    if [ -n "$SP" ]; then
      RESP=$(databricks api post "/api/2.0/database/instances/kaapi-bricks/roles" --profile "$PROFILE" --json "{\"name\": \"$SP\", \"identity_type\": \"SERVICE_PRINCIPAL\"}" 2>&1)
      if echo "$RESP" | grep -q "already exists\|ALREADY_EXISTS"; then
        echo "  ✓ Role for $SP already exists"
      elif echo "$RESP" | grep -q '"name"'; then
        echo "  ✓ Role created for $SP"
      else
        echo "  ⚠ Role creation for $SP: $(echo $RESP | head -c 120)"
      fi
    fi
  done
else
  echo "  ⚠ Skipping role creation — Lakebase not AVAILABLE (state=$LB_STATE)"
fi

# Grant catalog/schema/volume access to both app SPs
echo "  Granting UC permissions..."
for SP in "$MAIN_SP" "$MCP_SP"; do
  if [ -n "$SP" ]; then
    for SQL in \
      "GRANT USE SCHEMA ON SCHEMA $CATALOG.kaapi_bricks TO \`$SP\`" \
      "GRANT SELECT ON SCHEMA $CATALOG.kaapi_bricks TO \`$SP\`" \
      "GRANT MODIFY ON SCHEMA $CATALOG.kaapi_bricks TO \`$SP\`" \
      "GRANT READ VOLUME ON VOLUME $CATALOG.kaapi_bricks.raw_data TO \`$SP\`" \
      "GRANT READ VOLUME ON VOLUME $CATALOG.kaapi_bricks.invoices TO \`$SP\`" \
      "GRANT WRITE VOLUME ON VOLUME $CATALOG.kaapi_bricks.invoices TO \`$SP\`"; do
      databricks api post "/api/2.0/sql/statements" --profile "$PROFILE" --json "{
        \"warehouse_id\": \"$WAREHOUSE_ID\",
        \"statement\": \"$SQL\",
        \"wait_timeout\": \"30s\"
      }" 2>/dev/null | python3 -c "import sys,json; pass" 2>/dev/null
    done
  fi
done
echo "  ✓ Permissions granted"

# Grant app SP access to each other's apps (for MCP calls)
echo "  Granting app permissions..."
if [ -n "$MCP_SP" ]; then
  databricks apps set-permissions kaapi-ops-mcp --profile "$PROFILE" --json "{
    \"access_control_list\": [
      {\"user_name\": \"$USER_EMAIL\", \"permission_level\": \"CAN_MANAGE\"},
      {\"service_principal_name\": \"$MAIN_SP\", \"permission_level\": \"CAN_MANAGE\"}
    ]
  }" 2>/dev/null || true
fi
echo "  ✓ App permissions set"

# ---- Step 10: Create po_line_items table ----
echo ""
echo "→ Creating po_line_items table..."
databricks api post "/api/2.0/sql/statements" --profile "$PROFILE" --json "{
  \"warehouse_id\": \"$WAREHOUSE_ID\",
  \"statement\": \"CREATE TABLE IF NOT EXISTS $CATALOG.kaapi_bricks.po_line_items (line_id STRING, po_id STRING, ingredient_id STRING, ingredient_name STRING, quantity DOUBLE, unit STRING, unit_price DOUBLE, line_total DOUBLE)\",
  \"wait_timeout\": \"30s\"
}" 2>/dev/null | python3 -c "import sys,json; print(f'  {json.load(sys.stdin).get(\"status\",{}).get(\"state\",\"?\")}')" 2>/dev/null

# Insert PO line items for demo
databricks api post "/api/2.0/sql/statements" --profile "$PROFILE" --json "{
  \"warehouse_id\": \"$WAREHOUSE_ID\",
  \"statement\": \"INSERT INTO $CATALOG.kaapi_bricks.po_line_items SELECT * FROM (SELECT 'pl-001' as line_id, po_id, 'ING-001' as ingredient_id, 'Coorg Arabica Beans' as ingredient_name, 25.0 as quantity, 'kg' as unit, 1200.0 as unit_price, 30000.0 as line_total FROM $CATALOG.kaapi_bricks.purchase_orders WHERE supplier_id = 'SUP-001' ORDER BY order_date DESC LIMIT 1) UNION ALL SELECT * FROM (SELECT 'pl-002', po_id, 'ING-004', 'Chicory', 15.0, 'kg', 400.0, 6000.0 FROM $CATALOG.kaapi_bricks.purchase_orders WHERE supplier_id = 'SUP-001' ORDER BY order_date DESC LIMIT 1) UNION ALL SELECT * FROM (SELECT 'pl-003', po_id, 'ING-002', 'House Blend Pre-Mix', 25.0, 'kg', 820.0, 20500.0 FROM $CATALOG.kaapi_bricks.purchase_orders WHERE supplier_id = 'SUP-001' ORDER BY order_date DESC LIMIT 1) UNION ALL SELECT * FROM (SELECT 'pl-004', po_id, 'ING-021', 'Paper Cups (200ml)', 10.0, 'case', 800.0, 8000.0 FROM $CATALOG.kaapi_bricks.purchase_orders WHERE supplier_id = 'SUP-001' ORDER BY order_date DESC LIMIT 1) UNION ALL SELECT * FROM (SELECT 'pl-005', po_id, 'ING-022', 'Stirrer Sticks', 5.0, 'case', 300.0, 1500.0 FROM $CATALOG.kaapi_bricks.purchase_orders WHERE supplier_id = 'SUP-001' ORDER BY order_date DESC LIMIT 1)\",
  \"wait_timeout\": \"50s\"
}" 2>/dev/null | python3 -c "import sys,json; print(f'  PO line items: {json.load(sys.stdin).get(\"status\",{}).get(\"state\",\"?\")}')" 2>/dev/null

# ---- Step 11: MCP UC HTTP Connection (M2M OAuth) ----
# REQUIRES ACCOUNT-ADMIN: needs to create a Service Principal via SCIM API.
# We sync the notebook so it's runnable, but only attempt to run it if the
# caller has account-admin privileges. Most workspaces require manual SP setup
# via Account Console, then editing CLIENT_SECRET in the notebook.
echo ""
echo "→ Syncing MCP UC connection notebook (manual run required)..."
cp "$DIR/scripts/create_mcp_connection.py" "$TMPDIR/create_mcp_connection.py"
sed -i '' "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/create_mcp_connection.py" 2>/dev/null || sed -i "s/fevm_cme_conde_catalog/$CATALOG/g" "$TMPDIR/create_mcp_connection.py"
databricks workspace import "$WS_PATH/kaapi-bricks-setup/create_mcp_connection" --file "$TMPDIR/create_mcp_connection.py" --format SOURCE --language PYTHON --overwrite --profile "$PROFILE" > /dev/null 2>&1
echo "  ✓ Notebook at $WS_PATH/kaapi-bricks-setup/create_mcp_connection"
echo "  ℹ Note: requires account-admin to auto-create the SP. If you are not"
echo "    account-admin, when creating the MAS supervisor in Agent Bricks UI,"
echo "    add the MCP server directly by URL instead of via UC connection."

# Note: Genie Space creation via SDK requires an existing space export in
# proprietary GenieSpaceExport format — cannot be auto-created from JSON.
# Marked as manual UI step in the summary below.

# ---- Step 13: Print final status ----
MAIN_URL=$(databricks apps get kaapi-bricks-finale --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))" 2>/dev/null || echo "")
MCP_URL=$(databricks apps get kaapi-ops-mcp --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))" 2>/dev/null || echo "")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              DEPLOYMENT COMPLETE                         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Main App:    $MAIN_URL"
echo "║  MCP App:     $MCP_URL"
echo "║  Data:        $CATALOG.kaapi_bricks (14 tables + 6 PDFs)"
echo "║  Lakebase:    kaapi-bricks (with SP roles for both apps)"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  REMAINING MANUAL STEPS (UI — ~10 min):                  ║"
echo "║                                                          ║"
echo "║  1. Create Genie Space in SQL UI                         ║"
echo "║     • Name: Kaapi Bricks Analytics                       ║"
echo "║     • Warehouse: $WAREHOUSE_ID"
echo "║     • Tables: all 14 in $CATALOG.kaapi_bricks"
echo "║                                                          ║"
echo "║  2. Create KA tile in Agent Bricks UI                    ║"
echo "║     • Name: Kaapi Bricks Operations Knowledge            ║"
echo "║     • Volume: /Volumes/$CATALOG/kaapi_bricks/raw_data/ka_documents"
echo "║                                                          ║"
echo "║  3. (Optional) MCP UC Connection                         ║"
echo "║     If you are account-admin, run the notebook:          ║"
echo "║     $WS_PATH/kaapi-bricks-setup/create_mcp_connection"
echo "║     Otherwise, in step 4 add MCP via URL directly:       ║"
echo "║     $MCP_URL"
echo "║                                                          ║"
echo "║  4. Create MAS Supervisor in Agent Bricks UI             ║"
echo "║     • Name: Kaapi Bricks HQ                              ║"
echo "║     • Add KA from step 2                                 ║"
echo "║     • Add Genie Space from step 1                        ║"
echo "║     • Add MCP server (from step 3 or direct URL)         ║"
echo "║                                                          ║"
echo "║  5. Run: ./finalize.sh $PROFILE <MAS_ENDPOINT_NAME>"
echo "║     (binds the MAS endpoint to the main app + restarts)  ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Cleanup
rm -rf "$TMPDIR"
