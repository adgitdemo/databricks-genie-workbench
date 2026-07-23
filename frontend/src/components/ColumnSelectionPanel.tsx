/**
 * ColumnSelectionPanel — per-space, opt-in column allowlist for analysis/scan.
 *
 * Lets the user restrict which columns of each data source (table / view /
 * metric view) are considered during IQ Scan and Create-Agent profiling.
 * Persisted per space via /api/spaces/{id}/column-selection. Opt-in: when the
 * toggle is off (or JSON is empty) all columns are used (default behavior).
 */
import { useState, useEffect, useMemo } from "react"
import { Save, RotateCcw, Sparkles } from "lucide-react"
import { getColumnSelection, saveColumnSelection, recommendColumnSelection } from "@/lib/api"
import type { SpaceColumnSelection } from "@/types"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface Props {
  spaceId: string
  /** Parsed serialized_space, used to prefill a JSON template of data sources. */
  spaceData: Record<string, unknown> | null
}

function safeObj(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}
function safeArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : []
}

/** Build a `{data_sources: {fqn: ["*"]}}` template from the space's data sources. */
function buildTemplate(spaceData: Record<string, unknown> | null): string {
  const ds = safeObj(safeObj(spaceData ?? {}).data_sources)
  const sources = [...safeArray(ds.tables), ...safeArray(ds.metric_views)]
  const map: Record<string, string[]> = {}
  for (const s of sources) {
    const id = String(safeObj(s).identifier || "").trim()
    if (id) map[id] = ["*"]
  }
  return JSON.stringify({ data_sources: map }, null, 2)
}

export function ColumnSelectionPanel({ spaceId, spaceData }: Props) {
  const [enabled, setEnabled] = useState(false)
  const [jsonText, setJsonText] = useState("")
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const [recommending, setRecommending] = useState(false)
  const [recommendNote, setRecommendNote] = useState<string | null>(null)

  const template = useMemo(() => buildTemplate(spaceData), [spaceData])

  useEffect(() => {
    let cancelled = false
    getColumnSelection(spaceId)
      .then((sel) => {
        if (cancelled) return
        setEnabled(sel.enabled)
        const hasData = sel.data_sources && Object.keys(sel.data_sources).length > 0
        setJsonText(JSON.stringify({ data_sources: hasData ? sel.data_sources : {} }, null, 2))
      })
      .catch(() => {
        if (!cancelled) setJsonText(JSON.stringify({ data_sources: {} }, null, 2))
      })
      .finally(() => !cancelled && setLoaded(true))
    return () => {
      cancelled = true
    }
  }, [spaceId])

  /** Parse + validate the textarea. Returns the data_sources map or throws. */
  function parseDataSources(): Record<string, string[]> {
    let parsed: unknown
    try {
      parsed = JSON.parse(jsonText)
    } catch (e) {
      throw new Error(`Invalid JSON: ${(e as Error).message}`)
    }
    const ds = safeObj(parsed).data_sources
    if (ds === undefined) throw new Error('Missing "data_sources" object.')
    if (typeof ds !== "object" || ds === null || Array.isArray(ds)) {
      throw new Error('"data_sources" must be an object.')
    }
    const out: Record<string, string[]> = {}
    for (const [id, cols] of Object.entries(ds as Record<string, unknown>)) {
      if (id.split(".").length !== 3) {
        throw new Error(`Invalid identifier "${id}": expected catalog.schema.name`)
      }
      if (!Array.isArray(cols) || cols.some((c) => typeof c !== "string")) {
        throw new Error(`Columns for "${id}" must be a list of strings (use ["*"] for all).`)
      }
      out[id] = cols as string[]
    }
    return out
  }

  async function handleSave() {
    setError(null)
    setSavedMsg(null)
    let dataSources: Record<string, string[]> = {}
    if (enabled) {
      try {
        dataSources = parseDataSources()
      } catch (e) {
        setError((e as Error).message)
        return
      }
    }
    setSaving(true)
    try {
      const payload: SpaceColumnSelection = { enabled, data_sources: dataSources }
      await saveColumnSelection(spaceId, payload)
      setSavedMsg("Saved. Applies on the next IQ Scan.")
    } catch (e) {
      setError(`Save failed: ${(e as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  async function handleRecommend() {
    setError(null)
    setSavedMsg(null)
    setRecommendNote(null)
    setRecommending(true)
    try {
      const rec = await recommendColumnSelection(spaceId)
      if (!rec.system_tables_available) {
        setRecommendNote(
          "Usage history is unavailable (the app service principal may be missing " +
          "SELECT on system.access.column_lineage). You can still edit the columns manually."
        )
        return
      }
      // Populate the editable textarea; user can add/modify before saving.
      setJsonText(JSON.stringify({ data_sources: rec.data_sources }, null, 2))
      setEnabled(true)

      const withHistory = Object.keys(rec.data_sources).length
      const total = Object.keys(rec.meta || {}).length
      const noHistory = Object.entries(rec.meta || {})
        .filter(([, m]) => !m.has_history)
        .map(([id]) => id)
      const viaBase = Object.entries(rec.meta || {})
        .filter(([, m]) => m.via_base_tables)
        .map(([id]) => id)
      let note = `Recommended columns for ${withHistory} of ${total} data source(s) ` +
        `from the last ${rec.days} days of usage history.`
      if (viaBase.length) note += ` Base-table history was used for: ${viaBase.join(", ")}.`
      if (noHistory.length) {
        note += ` No history found for: ${noHistory.join(", ")} — add columns manually ` +
          `or use ["*"] to include all.`
      }
      note += " Review and edit before saving."
      setRecommendNote(note)
    } catch (e) {
      setError(`Recommendation failed: ${(e as Error).message}`)
    } finally {
      setRecommending(false)
    }
  }

  if (!loaded) {
    return <div className="px-5 py-4 text-xs text-muted">Loading column selection…</div>
  }

  return (
    <div className="px-5 py-4 border-t border-default">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-secondary">Column Selection</p>
          <p className="text-xs text-muted mt-0.5">
            Limit which columns are considered during analysis / IQ Scan. Off = all columns.
          </p>
        </div>
        {enabled && (
          <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-accent/15 text-accent">
            Active
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center gap-4 text-sm">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="col-sel"
            checked={!enabled}
            onChange={() => setEnabled(false)}
          />
          <span className="text-secondary">Consider all columns (default)</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="col-sel"
            checked={enabled}
            onChange={() => setEnabled(true)}
          />
          <span className="text-secondary">Use selected columns only</span>
        </label>
      </div>

      <div className="mt-3">
        <Button
          onClick={handleRecommend}
          disabled={recommending}
          variant="outline"
          size="sm"
          title="Inspect query/usage history and pre-fill only columns that have been used"
        >
          <Sparkles className="w-3.5 h-3.5 mr-1" />
          {recommending ? "Analyzing usage history…" : "Recommend from usage history"}
        </Button>
      </div>
      {recommendNote && <p className="mt-2 text-xs text-muted">{recommendNote}</p>}

      {enabled && (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-muted">
              JSON: map each data source to its allowed columns. Use{" "}
              <code className="font-mono">["*"]</code> for all columns.
            </p>
            <button
              onClick={() => setJsonText(template)}
              className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
              title="Reset to a template listing this space's data sources"
            >
              <RotateCcw className="w-3 h-3" />
              Template
            </button>
          </div>
          <Textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={12}
            spellCheck={false}
            className="font-mono text-xs"
          />
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      {savedMsg && <p className="mt-2 text-xs text-green-500">{savedMsg}</p>}

      <div className="mt-3">
        <Button onClick={handleSave} disabled={saving} size="sm">
          <Save className="w-3.5 h-3.5 mr-1" />
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  )
}
