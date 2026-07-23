---
sidebar_position: 5
description: "Per-space column allowlists for analysis, with usage-history-driven recommendations."
---

# Column Selection

Column Selection lets you restrict, **per Genie Space**, which columns of each data source are
considered during analysis — IQ Scan, the Create/Fix agent, and the Auto-Optimize (GSO) pipeline.
It is **opt-in**: when off (the default), all columns are used, exactly as before.

You configure it in the UI on the **Space Configuration** panel (Space detail → Score tab →
*Space Configuration* → *Column Selection*). No redeploy is needed to change a selection — it is
stored per space in Lakebase and applied on the next run.

## Why

A Genie Space's tables often carry far more columns than the questions actually need (ETL metadata,
audit fields, unused dimensions). Narrowing analysis to the columns that matter:

- makes IQ Scan and Create-agent profiling focus on relevant fields,
- reduces noise in generated benchmarks and optimization proposals,
- and lets you encode "these are the columns this space cares about" once, per space.

## Semantics

The selection is a JSON allowlist keyed by fully-qualified data source
(`catalog.schema.name` — a table, view, or metric view):

```json
{
  "data_sources": {
    "main.sales.orders":        ["order_id", "amount", "order_date", "region"],
    "main.sales.sales_metrics": ["region", "order_month", "total_revenue"],
    "main.sales.customers":     ["*"]
  }
}
```

Rules (**allowlist**, case-insensitive on both identifier and column name):

- A source listed with a column list → only those columns are used.
- A source listed with `["*"]` (or an empty list) → all columns are used.
- A source **not** listed → all columns are used.
- The toggle off, or an empty config → all columns everywhere (backward compatible).

For a **metric view**, list its dimension/measure names (Unity Catalog reports these as columns).

### Precedence

`per-space UI setting → global file (COLUMN_SELECTION_CONFIG) → all columns`

The per-space setting always wins. The global file (`COLUMN_SELECTION_ENABLED` +
`COLUMN_SELECTION_CONFIG`, see [Environment Variables](../reference/environment-variables.md)) is a
deployment-wide fallback for spaces that have no per-space setting.

## Where it applies

| Path | Honors column selection |
|---|---|
| IQ Scan (`scanner.py` UC enrichment) | ✅ |
| Create / Fix agent (`describe_table`, `profile_columns`, `assess_data_quality`, `assess_readiness`) | ✅ |
| Auto-Optimize / GSO (benchmark generation, evaluation, RCA, proposals) | ✅ |

All three read the same allowlist so behavior is consistent across analysis, agents, and optimization.

## Recommend from usage history

Rather than hand-typing the allowlist, click **Recommend from usage history**. The app inspects
Databricks usage history and pre-fills the allowlist with only the columns that have been used —
which you can then edit before saving.

**Signal.** It reads `system.access.column_lineage`, which records the columns read by each query and
attributes them to the Genie Space via `entity_metadata.genie_space_id`. Column-level and
authoritative — no SQL-text parsing.

**Algorithm** (per data source, default 30-day window):

1. **Resolve the FQNs to analyze.** Tables analyze themselves. Views and metric views also resolve
   their **base tables/views** (breadth-first, depth-capped) so their base-table history counts too:
   - Views → `information_schema.view_table_usage`, falling back to a `FROM`/`JOIN` regex over
     `view_definition` when that view is unavailable on the running DBR.
   - Metric views → the `source:` in the metric-view YAML definition.
2. **Fetch column usage** for that FQN set from `column_lineage`, scoped to the space. If the space
   has no history of its own yet (brand-new space), it falls back to **workspace-wide** usage of the
   same tables so recommendations are still useful.
3. **Union** the used columns across the source and all its resolved base tables, keyed under the
   configured identifier. A column is recommended if it was used ≥ 1 time in the window.
4. Sources with **no** history are surfaced (empty) so you know to add columns manually or use `["*"]`.

The result populates the editable JSON textarea and enables "Use selected columns only" — you review
and **Save**. A note summarizes per-source counts, which sources used base-table history, and which
had none.

**Permissions.** The recommendation runs as the app **service principal**; system tables are not
OBO-readable. The SP needs `SELECT` on `system.access.column_lineage` (and `table_lineage` /
`query.history` for the GenieWatch panels). These are in the deploy's grant list
(`scripts/deploy_lib/uc.py` → `WATCH_SYSTEM_GRANTS`), but **granting on `system.*` requires an
account admin** — until applied, the button degrades gracefully to "usage history unavailable"
instead of erroring.

## Architecture

**Storage.** `genie.space_column_selection(space_id, enabled, data_sources JSONB, updated_at)` in
Lakebase, with an in-memory fallback when Lakebase is not configured
(`backend/services/lakebase.py`).

**Filtering.** `backend/services/column_selection.py` — `parse_allowlist()` normalizes the config to
`{fqn_lower: {col_lower}}`; `allowed_columns()` / `filter_columns()` / `filter_column_names()` apply
it (with an optional per-call `override` for the per-space case). `set()` (empty) means wildcard.

**Endpoints** (`backend/routers/spaces.py`):

- `GET  /api/spaces/{id}/column-selection` — load current selection.
- `PUT  /api/spaces/{id}/column-selection` — save (validates `catalog.schema.name` + string lists).
- `POST /api/spaces/{id}/column-selection/recommend` — usage-history recommendation
  (`backend/services/column_usage.py`).

**Scan wiring.** `scanner.scan_space()` loads the per-space selection and threads it into
`_enrich_with_uc_descriptions(..., override=...)`.

**Create agent.** The selection is carried on `AgentSession.column_selection` and threaded through
`handle_tool_call(..., column_override=...)` into the inspection tools; a session targeting an
existing space is seeded from that space's saved selection.

**Auto-Optimize (GSO).** Because the GSO job cannot import backend code, the selection travels in the
run **snapshot**: `auto_optimize` reads it from Lakebase → `trigger_optimization(..., column_selection=)`
stashes it under `snapshot["_column_selection"]` → the preflight stage filters `config["_uc_columns"]`
so every downstream stage inherits the reduced set (`optimization/preflight.py`).

**Frontend.** `frontend/src/components/ColumnSelectionPanel.tsx` (toggle, JSON editor, Template and
Recommend buttons); API in `frontend/src/lib/api.ts`; types in `frontend/src/types/index.ts`.

## Notes and limits

- "Has usage history" today means **used ≥ 1 time** in the window; there is no minimum-count or
  top-N ranking yet (the usage count is fetched but not used to rank).
- Only **read** columns (`source_column_name`) count as usage.
- Column Selection scopes what analysis **considers** — it does not rewrite the deployed Genie Space
  config or remove columns from the space itself.
