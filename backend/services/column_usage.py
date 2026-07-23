"""Recommend columns for a Genie space from Databricks usage history.

Powers the "Recommend from usage history" button on the Column Selection page.
For each data source of a space, it finds the columns that have real usage
history and returns them so the UI can pre-fill the (editable) allowlist.

Signal: ``system.access.column_lineage`` — column-level, attributable to a Genie
space via ``entity_metadata.genie_space_id``. Primary and authoritative; no SQL
text parsing needed. For views / metric views we also resolve the underlying
base tables/views and union their column usage.

All queries run as the **service principal** (system tables + information_schema
system views are not OBO-readable). Reuses the SP-authenticated, TTL-cached
statement runner from ``backend.watch.services.system_tables`` (``_run``/``_p``).
Everything is best-effort: on missing grants / no history the caller degrades to
``system_tables_available: false`` rather than erroring.
"""
from __future__ import annotations

import logging
import re

from backend.sql_executor import execute_sql
from backend.watch.services import system_tables as _st

logger = logging.getLogger(__name__)

_DEFAULT_DAYS = 30
_MAX_BASE_DEPTH = 2  # view → base view → base table (cap to avoid cycles)

# FROM/JOIN cat.sch.tbl extraction — fallback when view_table_usage is
# unavailable. Mirrors iq_scan.rls_audit._FROM_JOIN_RE. Only emits fully
# qualified 3-part references (bare "FROM t" is skipped — unresolvable).
_FROM_JOIN_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+"
    r"(?:`(?P<cat_q>[^`]+)`|(?P<cat>[\w]+))"
    r"(?:\s*\.\s*(?:`(?P<sch_q>[^`]+)`|(?P<sch>[\w]+)))"
    r"(?:\s*\.\s*(?:`(?P<tbl_q>[^`]+)`|(?P<tbl>[\w]+)))?",
    re.IGNORECASE,
)


def _norm(identifier: str) -> str:
    return (identifier or "").strip().strip("`").lower()


def _sql_str(s: str) -> str:
    """Escape a string for safe single-quoted SQL literal use."""
    return (s or "").replace("'", "''")


def _parts(fqn: str) -> tuple[str, str, str] | None:
    bits = [b.strip().strip("`") for b in _norm(fqn).split(".")]
    if len(bits) == 3 and all(bits):
        return bits[0], bits[1], bits[2]
    return None


# ── View / metric-view base-table resolution ────────────────────────────────

def _view_definition(fqn: str) -> str:
    """Return the view/metric-view definition text (YAML for MVs), or ''."""
    p = _parts(fqn)
    if not p:
        return ""
    cat, sch, tbl = p
    sql = (
        f"SELECT view_definition FROM `{cat}`.information_schema.views "
        f"WHERE table_schema = '{_sql_str(sch)}' AND table_name = '{_sql_str(tbl)}'"
    )
    rows = _run_sql(sql)
    if rows:
        return str(rows[0].get("view_definition") or "")
    return ""


def _run_sql(sql: str) -> list[dict]:
    """Run a read-only information_schema query as the caller (OBO).

    Used for view/metric-view → base-table resolution. These objects live in the
    user's own catalog (``<catalog>.information_schema.*``), so they run through
    ``execute_sql`` (OBO or SP fallback) rather than the SP-only system-table
    runner. Returns list-of-dicts; errors (e.g. ``view_table_usage`` not existing
    on this DBR) are returned quietly so the caller can fall back to regex —
    they are NOT logged as warnings.
    """
    result = execute_sql(sql)
    if result.get("error"):
        logger.debug("column_usage info_schema query fell back: %s", str(result["error"])[:160])
        return []
    col_names = [c.get("name") for c in result.get("columns", [])]
    return [dict(zip(col_names, row)) for row in result.get("data", [])]


def _base_tables_via_usage(fqn: str) -> list[str]:
    """Resolve a view's base tables via information_schema.view_table_usage."""
    p = _parts(fqn)
    if not p:
        return []
    cat, sch, tbl = p
    sql = (
        f"SELECT table_catalog, table_schema, table_name "
        f"FROM `{cat}`.information_schema.view_table_usage "
        f"WHERE view_schema = '{_sql_str(sch)}' AND view_name = '{_sql_str(tbl)}'"
    )
    out: list[str] = []
    for r in _run_sql(sql):
        b = _norm(f"{r.get('table_catalog')}.{r.get('table_schema')}.{r.get('table_name')}")
        if _parts(b):
            out.append(b)
    return out


def _base_tables_via_regex(fqn: str) -> list[str]:
    """Fallback: parse FROM/JOIN references from the view/MV definition.

    Works for both SQL views and metric-view YAML (whose ``source:`` and any
    joined tables appear as qualified identifiers). Only 3-part refs are kept.
    """
    defn = _view_definition(fqn)
    if not defn:
        return []
    out: list[str] = []
    for m in _FROM_JOIN_RE.finditer(defn):
        cat = (m.group("cat_q") or m.group("cat") or "").lower()
        sch = (m.group("sch_q") or m.group("sch") or "").lower()
        tbl = (m.group("tbl_q") or m.group("tbl") or "").lower()
        if cat and sch and tbl:
            out.append(f"{cat}.{sch}.{tbl}")
    # Metric-view YAML carries `source: cat.sch.tbl` which the FROM/JOIN regex
    # misses; pick it up explicitly.
    for m in re.finditer(r"(?im)^\s*source\s*:\s*['\"]?([\w.`]+)", defn):
        cand = _norm(m.group(1))
        if _parts(cand):
            out.append(cand)
    return out


def _resolve_analyzed_fqns(identifier: str, kind: str) -> tuple[list[str], bool]:
    """Return (fqns_to_analyze, via_base_tables) for a data source.

    Views / metric views analyze themselves plus their resolved base
    tables/views (capped depth). Plain tables analyze only themselves — but a
    Genie "table" entry may actually be a SQL view (Genie lumps views under
    ``data_sources.tables``), so we still attempt base resolution for tables;
    it's a harmless no-op for real tables (``view_table_usage`` /
    ``view_definition`` return nothing).
    """
    ident = _norm(identifier)
    analyzed = {ident}
    via_base = False
    frontier = [ident]
    seen = {ident}
    depth = 0
    while frontier and depth < _MAX_BASE_DEPTH:
        nxt: list[str] = []
        for fq in frontier:
            bases = _base_tables_via_usage(fq) or _base_tables_via_regex(fq)
            for b in bases:
                if b not in seen:
                    seen.add(b)
                    analyzed.add(b)
                    nxt.append(b)
                    via_base = True
        frontier = nxt
        depth += 1
    return sorted(analyzed), via_base


# ── Column usage from column_lineage ─────────────────────────────────────────

def _column_usage(fqns: list[str], space_id: str, days: int) -> dict[str, set[str]]:
    """Return ``{fqn_lower: {used_column_lower, ...}}`` for the given FQNs.

    Prefers usage attributed to *space_id*; falls back to workspace-wide usage
    of the same FQNs when the space itself has no column-lineage rows yet.
    """
    fqns = [f for f in {_norm(f) for f in fqns} if _parts(f)]
    if not fqns:
        return {}
    in_list = ", ".join(f"'{_sql_str(f)}'" for f in fqns)

    def _query(space_scoped: bool) -> dict[str, set[str]]:
        scope = (
            f"AND entity_metadata.genie_space_id = '{_sql_str(space_id)}' "
            if space_scoped else ""
        )
        sql = (
            f"SELECT lower(source_table_full_name) AS fqn, "
            f"       lower(source_column_name) AS col, COUNT(*) AS uses "
            f"FROM system.access.column_lineage "
            f"WHERE source_column_name IS NOT NULL "
            f"  AND event_time >= current_date() - {int(days)} "
            f"  AND lower(source_table_full_name) IN ({in_list}) "
            f"  {scope}"
            f"GROUP BY 1, 2"
        )
        rows = _st._run(sql, [], track_health=True)
        out: dict[str, set[str]] = {}
        for r in rows:
            fqn = str(r.get("fqn") or "")
            col = str(r.get("col") or "")
            if fqn and col:
                out.setdefault(fqn, set()).add(col)
        return out

    scoped = _query(True)
    if scoped:
        return scoped
    # No space-attributed history — fall back to workspace-wide usage.
    return _query(False)


# ── Public API ───────────────────────────────────────────────────────────────

def recommend_columns(
    space_id: str,
    data_sources: list[dict],
    days: int = _DEFAULT_DAYS,
) -> dict:
    """Recommend used columns per data source from usage history.

    Args:
        space_id: Genie space id (for space-scoped attribution).
        data_sources: list of ``{"identifier": "cat.sch.name", "kind": "table"|"view"|"metric_view"}``.
        days: lookback window.

    Returns a dict:
        {
          "data_sources": {identifier: [used_column, ...]},   # only sources WITH history
          "meta": {identifier: {"analyzed_fqns": [...], "via_base_tables": bool,
                                 "column_count": int, "has_history": bool}},
          "days": days,
          "system_tables_available": bool,
        }
    """
    result_cols: dict[str, list[str]] = {}
    meta: dict[str, dict] = {}

    for ds in data_sources:
        identifier = _norm(ds.get("identifier", ""))
        if not _parts(identifier):
            continue
        kind = (ds.get("kind") or "table").lower()
        analyzed, via_base = _resolve_analyzed_fqns(identifier, kind)
        usage = _column_usage(analyzed, space_id, days)

        # Union used columns across the identifier and all resolved base tables.
        used: set[str] = set()
        for fq in analyzed:
            used |= usage.get(fq, set())

        cols = sorted(used)
        meta[identifier] = {
            "analyzed_fqns": analyzed,
            "via_base_tables": via_base,
            "column_count": len(cols),
            "has_history": bool(cols),
        }
        if cols:
            result_cols[identifier] = cols

    available = _st.system_tables_status()
    return {
        "data_sources": result_cols,
        "meta": meta,
        "days": days,
        # None (unknown) is treated as available=True so a fresh app that simply
        # has no history doesn't look "broken"; only an observed permission
        # failure flips this to False.
        "system_tables_available": available is not False,
    }
