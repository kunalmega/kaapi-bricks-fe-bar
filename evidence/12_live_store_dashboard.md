# Store Live Dashboard — served from Lakebase, updated by invoice approvals

Captured 2026-09-29 against the deployed app. Raw before/after JSON:
`evidence/raw/12_live_dashboard_writethrough_test.json`. Screenshot (supplementary, rendered
from that captured response): `evidence/raw/12_live_dashboard_screenshot.png`.

## What it is

A new app view, **📊 Live Dashboard** (landing-page nav), for a store manager. It reads **only
Lakebase**: one `GET /api/lakebase/dashboard?store=…` call returns everything, and the page
re-polls every **10 seconds**.

| Panel | Lakebase source | Notes |
|---|---|---|
| Items below reorder (tile) | `lb_inventory_position` | status icon + label, lowest-cover item named |
| Overdue purchase orders (tile + table) | `lb_open_purchase_orders` | **days overdue computed at query time** (`CURRENT_DATE - expected_delivery_date`) |
| Late deliveries on record (tile + table) | `lb_delivery_exceptions` | previously synced but unused; now read |
| Units sold (tile, daily columns, top drinks) | `lb_product_demand` | previously synced but unused; latest 8 days of sales data (07–14 May 2026) |
| Stock cover by ingredient | `lb_inventory_position` | days of cover per ingredient: ⛔ below reorder · ⚠ under 21 days · ✓ OK |
| Live activity feed | `kaapi_mcp.activity_log` | written by invoice approvals (below) |
| Status card | `lb_sync_log` + response timing | LIVE/OFFLINE, "updated Ns ago", Lakebase query time, last sync from gold |

## What makes it live: write-through on invoice approval

`POST /api/approve-invoice` still writes the receipts to Delta (`app_inventory_receipts`,
`app_po_approvals`), which stays the system of record. It now **also** updates Lakebase in the
same request:

- `UPDATE lb_inventory_position`: adds the received quantity and recomputes `below_reorder` and
  `days_cover`.
- `DELETE FROM lb_open_purchase_orders` for the approved PO.
- One `kaapi_mcp.activity_log` row per received item, plus one for the closed PO.

If the Lakebase update fails, the approval still succeeds (Delta is written) and the response
reports the error. The next pipeline run plus sync reconciles Lakebase from gold.

Permissions: the sync script now grants the app service principal `UPDATE, DELETE` on
`lb_inventory_position` and `lb_open_purchase_orders`, and `SELECT` on `lb_sync_log`.

## Live test (deployed app, store Koramangala STR-001)

1. `GET /api/lakebase/dashboard` (before).
2. Parse `invoice_mysore_po01057.pdf` through the app (Unity AI Gateway), then
   `POST /api/approve-invoice` for the 3 matched lines + PO-01057.
3. `GET /api/lakebase/dashboard` (after), 2 s later.

Approve response: `{"ok": true, "inserted": 3, "po_updated": "PO-01057", "lakebase": {"updated_items": 3, "po_closed": true, "error": null}}`

| | Before | After | Check |
|---|---:|---:|---|
| Badam Paste stock | 16.71 kg (58.6 d) | **18.86 kg (66.2 d)** | 16.71 + 2.15 ✅ |
| Rose Syrup stock | 16.79 L (35.0 d) | **23.18 L (48.4 d)** | 16.79 + 6.39 ✅ |
| Jaggery stock | 43.67 kg (44.6 d) | **57.67 kg (58.9 d)** | 43.67 + 14 ✅ |
| Overdue POs | 8 · ₹31,065.06 | **7 · ₹29,664.56** | −PO-01057 (₹1,400.50) ✅ |
| PO-01057 in open POs | yes | **no** | ✅ |
| Activity feed | empty | **4 events** (3 receipts + "PO-01057 (Mysore Sweet Works) invoice approved and closed") | ✅ |
| Lakebase query time | 37.0 ms | 29.0 ms | |

The "Synced from gold" card showed 2026-09-29 12:57 UTC. The approval moved the numbers without
any pipeline run or sync.

**Test clean-up.** The test's 3 receipt rows, 1 PO-approval row and 4 activity rows were deleted
by exact ID, and Lakebase was re-synced from gold, restoring the pre-test state (Badam 16.71,
Rose 16.79, Jaggery 43.67; 8 overdue; PO-01057 open; empty feed). This keeps the demo invoice
reusable.

## Performance

| Measure | Value |
|---|---|
| Lakebase time for the full dashboard (6 queries) | **22.8–37.0 ms** |
| End-to-end request from outside the app (network, auth, app) | ~1.1 s warm; ~4 s on the first request after a deploy (one-time store-ID lookup via the SQL warehouse) |

Also verified for another store: Indiranagar (STR-002) → 7 overdue POs, ₹49,893.01, 870 units,
22.8 ms.

## Limits

- Stock values are the gold position at the last sync **plus** approvals written through since;
  there is no live point-of-sale feed of usage.
- Sales data in the synthetic set ends 14 May 2026, so the demand panels show that week (labelled
  on screen).
- If the sync runs after an approval but **before** the next pipeline refresh, it reloads the
  pre-approval gold value and the write-through change is temporarily lost until the pipeline
  runs (gold unions `app_inventory_receipts`). Production fix: run sync only as a task after the
  pipeline, or use Lakebase synced tables.
