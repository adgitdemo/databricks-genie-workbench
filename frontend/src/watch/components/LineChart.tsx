/** Minimal dependency-free SVG line/area chart for time-series (e.g. daily
 *  query volume). Stretches to the container width; not interactive. */

interface Point {
  x: string
  y: number
}

export function LineChart({
  data,
  height = 180,
  formatY = (v: number) => v.toLocaleString(),
}: {
  data: Point[]
  height?: number
  formatY?: (v: number) => string
}) {
  if (!data.length) {
    return <p className="text-sm text-muted">No data.</p>
  }

  const W = 600
  const H = height
  const padL = 6
  const padR = 6
  const padT = 12
  const padB = 4
  const innerW = W - padL - padR
  const innerH = H - padT - padB
  const max = Math.max(1, ...data.map(d => d.y))
  const n = data.length
  const xAt = (i: number) => padL + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
  const yAt = (v: number) => padT + innerH - (v / max) * innerH

  const linePts = data.map((d, i) => `${xAt(i).toFixed(1)},${yAt(d.y).toFixed(1)}`).join(' ')
  const areaPts = `${padL},${padT + innerH} ${linePts} ${padL + innerW},${padT + innerH}`

  const fmtDay = (s: string) => {
    const d = new Date(s)
    return isNaN(d.getTime()) ? s : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  // Evenly-spaced date ticks (start → mid → end) so the axis clearly spans the
  // full selected window, not just the days that had activity.
  const tickIdx =
    n <= 1 ? [0]
    : n === 2 ? [0, n - 1]
    : [0, Math.floor((n - 1) / 2), n - 1]

  return (
    <div className="w-full">
      <div className="mb-1 text-right text-xs text-muted">peak {formatY(max)}/day</div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
      >
        <polygon points={areaPts} fill="#3b82f6" fillOpacity={0.12} stroke="none" />
        <polyline
          points={linePts}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
        />
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        {tickIdx.map(i => <span key={i}>{fmtDay(data[i].x)}</span>)}
      </div>
    </div>
  )
}
