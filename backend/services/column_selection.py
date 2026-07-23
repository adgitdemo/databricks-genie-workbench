"""Optional column allowlist for analysis / profiling / sampling.

When ``COLUMN_SELECTION_ENABLED`` is truthy and ``COLUMN_SELECTION_CONFIG`` points
at a readable JSON file, the create agent's inspection tools (``describe_table``,
``profile_columns``, ``assess_data_quality``, ``assess_readiness``), the plan
builder, and the IQ scanner's UC enrichment restrict themselves to the columns
listed for each table — instead of enumerating every column in the source
table/view/metric view.

Config file shape (JSON)::

    {
      "data_sources": {
        "main.sales.orders":       ["order_id", "amount", "order_date", "region"],
        "main.sales.sales_metrics": ["region", "total_revenue"],
        "main.sales.customers":    ["*"]
      }
    }

The ``data_sources`` map holds any Unity Catalog identifier — tables, views, or
metric views. For a metric view, list the dimension/measure names (which UC
reports as columns).

Semantics (allowlist):
  - A source listed with a column list → only those columns are used.
  - A source listed with ``["*"]`` (or an empty list) → all columns are used.
  - A source NOT listed → all columns are used (feature is opt-in per source).

Identifiers are matched case-insensitively on the fully-qualified
``catalog.schema.name``; column names are matched case-insensitively.
"""
from __future__ import annotations

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

# Sentinel meaning "all columns" — an explicit "*" entry or an empty allowlist.
_WILDCARD = "*"

_lock = threading.Lock()
# Cache is keyed by (enabled_flag, config_path) so a changed env var invalidates it.
_cache_key: tuple[bool, str] | None = None
_cache_value: dict[str, set[str]] | None = None


def _is_enabled() -> bool:
    return os.environ.get("COLUMN_SELECTION_ENABLED", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _load_config() -> dict[str, set[str]]:
    """Load and cache the column allowlist keyed on the current env vars.

    Returns a mapping of lowercased ``catalog.schema.table`` -> set of lowercased
    column names. A table mapped to an empty set means "all columns" (wildcard).
    Returns an empty dict when the feature is disabled or the config is missing
    or unreadable — callers then fall back to using all columns.
    """
    global _cache_key, _cache_value

    enabled = _is_enabled()
    config_path = os.environ.get("COLUMN_SELECTION_CONFIG", "").strip()
    key = (enabled, config_path)

    with _lock:
        if _cache_key == key and _cache_value is not None:
            return _cache_value

        parsed: dict[str, set[str]] = {}
        if enabled and config_path:
            parsed = _parse_config_file(config_path)
        elif enabled and not config_path:
            logger.warning(
                "COLUMN_SELECTION_ENABLED is set but COLUMN_SELECTION_CONFIG is empty; "
                "falling back to using all columns."
            )

        _cache_key = key
        _cache_value = parsed
        return parsed


def _parse_config_file(config_path: str) -> dict[str, set[str]]:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        logger.warning("Column selection config not found at %s; using all columns.", config_path)
        return {}
    except (OSError, ValueError) as e:
        logger.warning("Failed to read column selection config %s: %s; using all columns.", config_path, e)
        return {}

    data_sources = raw.get("data_sources") if isinstance(raw, dict) else None
    if not isinstance(data_sources, dict):
        logger.warning(
            "Column selection config %s missing a 'data_sources' object; using all columns.",
            config_path,
        )
        return {}

    parsed = parse_allowlist(data_sources)
    logger.info(
        "Loaded column selection allowlist for %d data source(s) from %s", len(parsed), config_path
    )
    return parsed


def parse_allowlist(data_sources: dict) -> dict[str, set[str]]:
    """Normalize a ``data_sources`` mapping into ``{fqn_lower: set(col_lower)}``.

    Shared by the global file loader and per-space (Lakebase) payloads so both
    honor identical semantics: an explicit ``"*"`` entry or an empty list means
    "all columns" (stored as an empty set = wildcard). Identifiers and column
    names are lowercased. Non-dict input yields an empty mapping.
    """
    if not isinstance(data_sources, dict):
        return {}
    parsed: dict[str, set[str]] = {}
    for identifier, cols in data_sources.items():
        if not isinstance(identifier, str):
            continue
        key = identifier.strip().lower()
        if not key:
            continue
        if not isinstance(cols, list):
            logger.warning(
                "Column selection for %s is not a list; treating as all columns.", identifier
            )
            parsed[key] = set()  # wildcard
            continue
        names = {str(c).strip().lower() for c in cols if str(c).strip()}
        # An explicit "*" entry (or empty list) means "all columns".
        if _WILDCARD in names or not names:
            parsed[key] = set()  # wildcard
        else:
            parsed[key] = names
    return parsed


def is_active() -> bool:
    """True when the global file feature is enabled and a non-empty config was loaded."""
    return bool(_load_config())


def allowed_columns(
    table_identifier: str, override: dict[str, set[str]] | None = None
) -> set[str] | None:
    """Return the lowercased allowlist for a data source, or None when unrestricted.

    None means "use all columns" — either no config applies, the source is not
    listed, or the source is configured with the ``*`` wildcard. Accepts any UC
    identifier (table, view, or metric view).

    When *override* (an already-parsed per-space allowlist from ``parse_allowlist``)
    is provided, it takes precedence over the global file config. Precedence:
    per-space override → global file → all columns.
    """
    config = override if override is not None else _load_config()
    if not config:
        return None
    entry = config.get((table_identifier or "").strip().lower())
    if entry is None:  # source not listed → unrestricted
        return None
    if not entry:  # wildcard → unrestricted
        return None
    return entry


def filter_columns(
    table_identifier: str,
    columns: list[dict],
    name_key: str = "name",
    override: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Filter a list of column dicts down to the allowlist for *table_identifier*.

    ``columns`` is a list of dicts each carrying the column name under *name_key*
    (``"name"`` for describe_table results, ``"column_name"`` for config entries).
    Returns the input unchanged when the table is unrestricted. Column ordering
    from the source is preserved. See :func:`allowed_columns` for *override*.
    """
    allow = allowed_columns(table_identifier, override=override)
    if allow is None:
        return columns
    return [c for c in columns if str(c.get(name_key, "")).strip().lower() in allow]


def filter_column_names(
    table_identifier: str, names: list[str], override: dict[str, set[str]] | None = None
) -> list[str]:
    """Filter a list of plain column-name strings down to the allowlist."""
    allow = allowed_columns(table_identifier, override=override)
    if allow is None:
        return names
    return [n for n in names if str(n).strip().lower() in allow]


def _reset_cache_for_tests() -> None:
    """Test helper — clears the module-level config cache."""
    global _cache_key, _cache_value
    with _lock:
        _cache_key = None
        _cache_value = None
