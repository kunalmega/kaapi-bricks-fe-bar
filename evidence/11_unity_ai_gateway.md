# Unity AI Gateway — every non-Genie AI request is governed

Captured 2026-09-29 against the deployed apps. Raw responses are in `evidence/raw/11_*.json`.
Genie Agent calls are the only AI calls that do not pass through the gateway (by design).

## 1. What is routed through the gateway

| App request | Before | Now (Unity AI Gateway) |
|---|---|---|
| Invoice document parsing + field extraction | `ai_parse_document` (SQL) + direct Claude serving endpoint | **one** call to model service `kaapi_llm`, with the PDF sent as a `document` block |
| Semantic-cache embeddings | direct BGE serving endpoint | model service `kaapi_embed` |
| Weather + holiday preparation advice | not called at all | MCP service `kaapi_ops_advisor` (`tools/call operations_advisor`) |
| The MCP server's own LLM call | direct Llama 3.3 serving endpoint | model service `kaapi_llm` |
| Chat Q&A over tables and SOP PDFs | Genie Agent mode | unchanged: Genie Agent mode |

After the change, the main app contains **no** direct `serving-endpoints` calls and no
`ai_parse_document` call. The only fallback is **inside** the gateway (Sonnet → Haiku); the app
never falls back to an ungoverned path.

## 2. Services created (Unity Catalog, `fevm_cme_conde_catalog.kaapi_bricks`)

| Service | Type | Routing | Rate limit (service-wide) | Request log |
|---|---|---|---|---|
| `kaapi_llm` | model service | primary Claude Sonnet 4.6 → fallback Claude Haiku 4.5 | 300 requests/min | `kaapi_llm_payload` |
| `kaapi_embed` | model service | BGE-large-en v1.5 | 600 requests/min | `kaapi_embed_payload` |
| `kaapi_ops_advisor` | MCP service | UC HTTP connection `kaapi_ops_mcp` → `kaapi-ops-mcp` app | 120 requests/min | system tables (MCP services have no request-log table) |

Created with `databricks ai-gateway create-model-service` / `create-mcp-service`. Limits and logs
set with `update-model-service … config.rate_limits` / `config.inference_table` and
`update-mcp-service … config.rate_limits`.

Call surface (the model is the 3-level UC name, passed in the body):

```
POST {workspace}/ai-gateway/mlflow/v1/chat/completions   {"model": "…kaapi_llm", …}
POST {workspace}/ai-gateway/mlflow/v1/embeddings         {"model": "…kaapi_embed", …}
POST {workspace}/ai-gateway/mcp-services/…kaapi_ops_advisor   JSON-RPC tools/list, tools/call
```

## 3. Access control

| Principal | Privilege | On |
|---|---|---|
| Main app service principal | `EXECUTE` | `kaapi_llm`, `kaapi_embed`, `kaapi_ops_advisor` |
| MCP app service principal | `EXECUTE` | `kaapi_llm` |
| Connector SP `kaapi-mcp-connector-v2` | `CAN_USE` | `kaapi-ops-mcp` app (the identity the MCP connection signs in as) |

Both apps carry the `ai-gateway` OAuth scope (`user_api_scopes`, set with `databricks apps update`
and applied on redeploy). All gateway calls use the **app service principal** token, never a user
token. The main app's stale resources (retired KA/MAS endpoints and five unused model endpoints)
were removed. It now declares only the Genie space, Lakebase and the SQL warehouse.

**Connection credential fix.** The first MCP service call failed with *"no credential found for
this MCP service's connection"*: the OAuth M2M connection had no stored secret, and its SP had no
access to the MCP app. We minted a new 90-day secret (expires 2026-12-28) for
`kaapi-mcp-connector-v2`, stored it directly in the UC connection without printing it, and granted
the SP `CAN_USE` on the MCP app. A secret created by a failed first attempt was deleted.

## 4. Proof it works end to end (deployed apps)

### 4.1 Invoice parsing through `kaapi_llm` (2026-09-29 ~12:16 UTC)

Same invoice as evidence/06 (`invoice_mysore_po01057.pdf`, PO-01057): 4 planted discrepancies and
1 control line.

| Line | Result via gateway | Same as evidence/06? |
|---|---|---|
| Badam Paste | match | ✅ |
| Rose Syrup | error: price ₹200 → ₹230 (+₹30) | ✅ |
| Jaggery Blocks | warning: qty 12.69 → 14.0 (+1.3) | ✅ |
| Sugar | extra, not in PO | ✅ |
| Palm Jaggery | missing delivery | ✅ |

All 4 discrepancies detected, control line matched. **Server time 18.4 s** (was 22.7 s with
`ai_parse_document` + a separate LLM call). Payload log row `kaapi_llm_payload` @ 12:16:58.244Z:
status 200, 4,915 ms, requester = main app SP, request contains the `application/pdf` document.

### 4.2 Preparation plan: SQL + Lakebase → MCP service → `kaapi_llm` (~12:17 UTC)

Question: *"How should I prepare for today?"* (Koramangala). MLflow trace
**tr-aaeed4886214ffedd824fdd23513d5e7**, 36.2 s:

| Span | Type | ms | Does |
|---|---|---:|---|
| `chat_request` | AGENT | 36,230 | routes preparation questions away from the cache and Genie |
| `prep_brief` | AGENT | 36,229 | |
| `prep_store_data` | TOOL | 8,135 | same-weekday demand from gold (SQL) + lowest stock cover and overdue POs from **Lakebase** |
| `mcp_ops_advisor` | TOOL | 28,093 | MCP service `kaapi_ops_advisor` → live weather + holiday calendar → plan written by `kaapi_llm` |

Answer excerpt: *"Tuesday, 29 September 2026 … Thunderstorm, 21–28°C, 21mm rain … Tuesday baseline
of 56 orders / ₹8,246 … Classic Filter Coffee: typical Tuesday 12.1 → forecast 14–15 … Cold
Coffee 3.6 → 2–3 … Gandhi Jayanti on 02 Oct: no impact today … Chikmagalur Robusta Beans 69.93 kg,
18.2 days cover."*

This fixes the two defects found in the earlier "prepare for today" answer: it used one past
Thursday instead of the same weekday, and it had no weather. The Tuesday figure 12.1 matches our
independent day-of-week query on `gold_product_demand` (evidence/06 §3). The advisor's LLM call is
payload-logged: `kaapi_llm_payload` @ 12:17:25.942Z, status 200, 26,026 ms, requester = **MCP app
SP**. Preparation answers are never cached, because they depend on today's weather.

### 4.3 Semantic cache through `kaapi_embed` (~12:18 UTC)

| Call | Result |
|---|---|
| 1 (fresh) | Genie answer in 25.3 s; answer and **1024-dim** embedding saved to Lakebase `qa_cache` |
| 2 (same question) | served from cache in **1.1 s** (`from_cache: true`) |

`kaapi_embed` returns vectors identical to the previous BGE endpoint (cosine similarity 1.000000
on a test string), so answers cached before the switch still match. Payload log: 2 rows in
`kaapi_embed_payload`, status 200, 523–713 ms, requester = main app SP.

### 4.4 Rate limiting enforced (12:24 UTC)

`kaapi_llm` temporarily set to **1 request/minute**, then restored to 300:

| Call (UTC) | HTTP | Body |
|---|---|---|
| 12:24:12 | 200 | normal completion |
| 12:24:13 | **429** | `REQUEST_LIMIT_EXCEEDED: User defined rate limit(s) exceeded for 'fevm_cme_conde_catalog.kaapi_bricks.kaapi_llm'. Requests-per-minute (RPM) rate limit exceeded` |
| 12:24:16 | 200 | (rolling window, not a fixed per-minute bucket) |
| 12:24:17 | **429** | same |

Observed: a limit change took more than 20 s to propagate. A first attempt 20 s after the change
saw no 429; after 90 s it was enforced.

## 5. What is still outside the gateway (stated plainly)

| Item | Why |
|---|---|
| Genie Agent calls | By design. Governed by the Genie space and Unity Catalog permissions |
| The MCP server's HTTP call to the Open-Meteo weather API | Made inside the MCP server's code. The gateway governs the MCP tool call, not the HTTP request behind it |
| The MCP app's admin "compare models" UI | Demo tool that calls serving endpoints directly. Not used by the store-manager flows |
| MLflow evaluation judges | Evaluation tooling, not app traffic |

## 6. Not done yet

- **Policies / guardrails.** Service policies are attached in the UI only. None are attached yet;
  candidates are the built-in jailbreak and unsafe-content policies on `kaapi_llm`.
- **Cost per store.** Usage is in system tables; a cost-attribution query is still to be written.
- **Secret rotation.** The connector SP still has an older secret (created 2026-07-07). Delete it
  if nothing else uses it.
