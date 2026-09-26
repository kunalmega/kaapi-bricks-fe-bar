#!/bin/bash
# ================================================================
# Kaapi Bricks Demo — Finalize Deployment
# ================================================================
# Run this AFTER you have created the KA tile + MAS supervisor in
# the Agent Bricks UI. Takes the MAS endpoint name and binds it to
# the main chat app as a serving_endpoint resource.
#
# Usage:
#   ./finalize.sh <profile> <mas_endpoint_name>
#
# Example:
#   ./finalize.sh fevm-india-gcc agents_kaapi_bricks-kaapi_bricks_HQ
# ================================================================

set -e

PROFILE=${1:?"Usage: ./finalize.sh <profile> <mas_endpoint_name>"}
MAS_ENDPOINT=${2:?"Usage: ./finalize.sh <profile> <mas_endpoint_name>"}
MAIN_APP="kaapi-bricks-finale"

echo "→ Binding MAS endpoint '$MAS_ENDPOINT' to $MAIN_APP..."

databricks apps update "$MAIN_APP" --profile "$PROFILE" --json "{
  \"resources\": [
    {
      \"name\": \"mas-endpoint\",
      \"description\": \"Multi-Agent Supervisor endpoint\",
      \"serving_endpoint\": {
        \"name\": \"$MAS_ENDPOINT\",
        \"permission\": \"CAN_QUERY\"
      }
    }
  ]
}" 2>&1 | grep -E "name|state|error" || true

echo ""
echo "→ Restarting app to pick up new resource..."
databricks apps stop "$MAIN_APP" --profile "$PROFILE" 2>&1 | grep -E "state" || true
sleep 5
databricks apps start "$MAIN_APP" --profile "$PROFILE" 2>&1 | grep -E "state" || true

APP_URL=$(databricks apps get "$MAIN_APP" --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))" 2>/dev/null)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              FINALIZATION COMPLETE                       ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Main App: $APP_URL"
echo "║  Bound MAS endpoint: $MAS_ENDPOINT"
echo "║                                                          ║"
echo "║  Demo is ready. Open the URL above.                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
