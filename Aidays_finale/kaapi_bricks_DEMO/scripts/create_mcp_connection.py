# Databricks notebook source
# Creates the MCP UC HTTP Connection with M2M OAuth
# Run this AFTER deploying the kaapi-ops-mcp app

# MAGIC %pip install databricks-sdk>=0.38.0
# MAGIC %restart_python

# ========================================
# CONFIG
# ========================================
MCP_APP_NAME = "kaapi-ops-mcp"
CONNECTION_NAME = "kaapi_ops_mcp"
SP_NAME = "kaapi-mcp-connector"
# ========================================

from databricks.sdk import WorkspaceClient
import requests, json

w = WorkspaceClient()
host = w.config.host.rstrip("/")
user = w.current_user.me().user_name
headers = w.config.authenticate()
headers["Content-Type"] = "application/json"

# Step 1: Get the MCP app URL
print("Step 1: Getting MCP app URL...")
app_info = requests.get(f"{host}/api/2.0/apps/{MCP_APP_NAME}", headers=headers).json()
mcp_url = app_info["url"]
print(f"  App URL: {mcp_url}")

# Step 2: Find or create Service Principal
print("\nStep 2: Finding/creating Service Principal...")
sp_client_id = None
sp_id = None

# Search existing
existing = list(w.service_principals.list(filter=f'displayName eq "{SP_NAME}"'))
if existing:
    sp = existing[0]
    sp_client_id = sp.application_id
    sp_id = sp.id
    print(f"  Found existing SP: {sp_client_id} (ID: {sp_id})")
else:
    sp = w.service_principals.create(display_name=SP_NAME, active=True)
    sp_client_id = sp.application_id
    sp_id = sp.id
    print(f"  Created SP: {sp_client_id} (ID: {sp_id})")

# Step 3: Generate OAuth secret using service_principal_secrets_proxy
print("\nStep 3: Generating OAuth secret...")
try:
    secret_response = w.service_principal_secrets_proxy.create(service_principal_id=sp_id)
    client_secret = secret_response.secret
    print(f"  OAuth secret generated (starts with: {client_secret[:8]}...)")
except Exception as e:
    print(f"  SDK method failed: {e}")
    print("  Trying REST API...")
    try:
        secret_resp = requests.post(
            f"{host}/api/2.0/service-principal-secrets/{sp_id}/credentials/secrets",
            headers=headers
        )
        if secret_resp.status_code == 200:
            secret_data = secret_resp.json()
            client_secret = secret_data.get("secret", "")
            print(f"  OAuth secret generated via REST")
        else:
            # Try another endpoint format
            secret_resp2 = requests.post(
                f"{host}/api/2.0/accounts/service-principals/{sp_id}/credentials/secrets",
                headers=headers
            )
            if secret_resp2.status_code == 200:
                secret_data = secret_resp2.json()
                client_secret = secret_data.get("secret", "")
                print(f"  OAuth secret generated via accounts API")
            else:
                print(f"  Could not generate secret via API.")
                print(f"  Go to Account Console > Service Principals > {SP_NAME} > Generate Secret")
                print(f"  Then set client_secret manually below and re-run from Step 5")
                client_secret = None
    except Exception as e2:
        print(f"  Error: {e2}")
        client_secret = None

# Step 4: Grant SP access to MCP app
print("\nStep 4: Granting SP access to MCP app...")
try:
    perm_resp = requests.patch(
        f"{host}/api/2.0/permissions/apps/{app_info['id']}",
        headers=headers,
        json={"access_control_list": [
            {"service_principal_name": sp_client_id, "permission_level": "CAN_MANAGE"}
        ]}
    )
    print(f"  Granted (status: {perm_resp.status_code})")
except Exception as e:
    print(f"  Warning: {e}")

# Step 5: Create the UC HTTP Connection
print(f"\nStep 5: Creating UC Connection '{CONNECTION_NAME}'...")
spark.sql(f"DROP CONNECTION IF EXISTS {CONNECTION_NAME}")

token_endpoint = f"{host}/oidc/v1/token"

if client_secret:
    # M2M OAuth — permanent, no expiry
    spark.sql(f"""
        CREATE CONNECTION {CONNECTION_NAME} TYPE HTTP OPTIONS (
            host '{mcp_url}',
            port '443',
            base_path '/mcp',
            client_id '{sp_client_id}',
            client_secret '{client_secret}',
            oauth_scope 'all-apis',
            token_endpoint '{token_endpoint}',
            is_mcp_connection 'true'
        )
    """)
    auth_type = "M2M OAuth (permanent)"
    print(f"  Connection created with M2M OAuth")
else:
    # Fallback: PAT token (90 days)
    print("  Falling back to PAT token (90 days)...")
    token_resp = requests.post(f"{host}/api/2.0/token/create", headers=headers, json={
        "comment": f"MCP connection for {CONNECTION_NAME}",
        "lifetime_seconds": 7776000
    })
    pat_token = token_resp.json().get("token_value", "")
    spark.sql(f"""
        CREATE CONNECTION {CONNECTION_NAME} TYPE HTTP OPTIONS (
            host '{mcp_url}',
            port '443',
            base_path '/mcp',
            bearer_token '{pat_token}',
            is_mcp_connection 'true'
        )
    """)
    auth_type = "PAT token (expires in 90 days)"
    print(f"  Connection created with PAT token")

# Step 6: Grant access
print("\nStep 6: Granting connection access...")
try:
    spark.sql(f"GRANT ALL PRIVILEGES ON CONNECTION {CONNECTION_NAME} TO `account users`")
    print("  Granted to account users")
except:
    spark.sql(f"GRANT USE CONNECTION ON CONNECTION {CONNECTION_NAME} TO `{user}`")
    print(f"  Granted to {user}")

# Step 7: Test
print("\nStep 7: Testing connection...")
result = spark.sql(f"""
    SELECT http_request(
        conn => '{CONNECTION_NAME}',
        method => 'POST',
        path => '',
        json => '{{"jsonrpc":"2.0","method":"tools/list","id":1}}'
    )
""").collect()
response = json.loads(result[0][0])
if response.get("status_code") == "200":
    tools = json.loads(response["text"]).get("result", {}).get("tools", [])
    print(f"  SUCCESS — Tools: {[t['name'] for t in tools]}")
else:
    print(f"  HTTP {response.get('status_code')}: {response.get('text','')[:200]}")

# Summary
print(f"""
╔══════════════════════════════════════════════════════╗
║           MCP CONNECTION READY                       ║
╠══════════════════════════════════════════════════════╣
║  Connection:  {CONNECTION_NAME:<37} ║
║  MCP App:     {mcp_url:<37} ║
║  SP:          {sp_client_id:<37} ║
║  Auth:        {auth_type:<37} ║
║                                                      ║
║  Add to MAS Supervisor:                              ║
║    Name: operations_advisor                          ║
║    Type: MCP Connection                              ║
║    Connection: {CONNECTION_NAME:<37} ║
║    Description: Handles operational planning,        ║
║      weather impact, holiday/festival planning,      ║
║      staffing, demand forecasting.                   ║
╚══════════════════════════════════════════════════════╝
""")
