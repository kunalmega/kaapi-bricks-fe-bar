# Kaapi Bricks — AI Days Finale Demo

A multi-agent AI application for a fictional South Indian filter coffee chain with 37 stores across India and internationally. Built on Databricks to showcase the full AI agent lifecycle.

## What It Does

A store manager asks a question → the app decides which AI agent handles it → the answer comes back with real data.

**Three agents, one chat interface:**

| Agent | Handles | Data Source |
|-------|---------|-------------|
| **Knowledge Assistant (KA)** | Recipes, policies, training, food safety | 6 branded PDFs in Unity Catalog Volume |
| **Genie Space** | Sales, inventory, revenue, promotions, suppliers | 14 Delta tables (200K orders, 15K customers) |
| **Operations Advisor** (custom) | Tomorrow's preparation plan, weather impact, holiday planning | Live weather API + Indian festival calendar + store data from Genie |

## Architecture

```
User Question
    │
    ▼
App-Level Router (keyword match → LLM fallback)
    │
    ├── "mas" route (recipes, data, policies)
    │   └── MAS Supervisor Endpoint → KA or Genie
    │
    └── "both" route (planning, forecasting, preparation)
        ├── MAS Endpoint → Genie returns real store data
        └── Operations Advisor → weather API + calendar + LLM reasoning over store data
```

## Three Pages

### 1. Main Chat
Clean chat interface. Store selector. No technical controls.
- Questions auto-route to the right agent
- Answers cached in Lakebase for instant repeat responses
- MLflow traces every request

### 2. Admin Settings
Configure which Foundation Models power the system:
- **Router Model** — classifies questions (fast/cheap model recommended)
- **Operations Model** — generates operational recommendations (capable model recommended)
- Saved to Lakebase, persists across restarts

### 3. Compare & Test
Side-by-side model comparison for the Operations Advisor:
- Pick Model A and Model B from 10+ Foundation Model endpoints
- Ask the same question → see both answers with latency and token counts
- Calls MAS once for real store data, then runs both models with identical context
- Results cached per model+question+store combination

## Key Components

### Backend (`app.py`)
- **FastAPI** server on port 8000
- **Lakebase (PostgreSQL)** for conversations, messages, feedback, cache, admin config, compare cache
- **MLflow tracing** on route decisions, MAS calls, weather/calendar tools, LLM calls
- **Semantic cache** with BGE embeddings — exact match + cosine similarity
- **Inference logging** to Delta table for monitoring

### Frontend (`static/index.html`)
- **React 18** via CDN (no build step)
- Coffee-themed UI (Playfair Display + Inter fonts)
- SSE streaming with progress status updates
- Markdown rendering for tables, lists, formatting

### Operations Advisor Tools
- `get_weather_forecast()` — OpenWeatherMap API with seasonal fallback
- `check_calendar()` — Indian festivals/holidays 2026 + weekend/Friday detection
- LLM reasoning — combines weather + calendar + real store data from Genie

## Data

### Delta Tables (14 tables in `fevm_cme_conde_catalog.kaapi_bricks`)
- stores (37), products (28), toppings (12), ingredients (22), suppliers (8)
- customers (15K), orders (~200K), order_items (~300K), order_item_toppings (~90K)
- purchase_orders (~2K), inventory_transactions (~158K), promotions (15), promotion_redemptions (~8K)
- inference_logs (observability)

### KA Documents (6 PDFs)
- Barista training manual, drink recipes SOP, food safety policy
- Franchise operations guide, equipment maintenance, supplier agreements

## Deployment

Deployed as a **Databricks App** (`kaapi-bricks-finale`).

### Resources Required
- MAS serving endpoint (`mas-3c936239-endpoint`)
- KA serving endpoint (`ka-06ac94eb-endpoint`)
- Genie Space (`Kaapi Bricks Analytics`)
- Lakebase instance (`kaapi-bricks`)
- SQL Warehouse (`kun`)
- Embedding endpoint (`databricks-bge-large-en`)
- Foundation Model endpoints (Llama, Claude, GPT, Gemini, Maverick, etc.)

### Deploy
```bash
databricks sync ./kaapi-bricks-app /Workspace/Users/<user>/kaapi-bricks-finale --profile DEFAULT
databricks apps deploy kaapi-bricks-finale --source-code-path /Workspace/Users/<user>/kaapi-bricks-finale
```

## Demo Flow (5 Acts)

1. **The Magic** — Ask questions, get answers. Three agents invisible to the user.
2. **Multi-Agent Routing** — Show MLflow traces: route decision → MAS or Operations Advisor → tool calls.
3. **Evaluation** — Run eval notebooks: correct answers score green, wrong answers caught red.
4. **Monitoring** — Lakeview dashboard: token usage, latency, errors, queries by store.
5. **CI/CD for AI** — Compare page: test two models side-by-side, pick the winner, update Admin config.
