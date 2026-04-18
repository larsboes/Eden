import { useRef, useEffect, useState, useCallback } from 'react'

// The AI explores parameter combinations and maps out which work.
// A 10x10 grid fills cell-by-cell as combinations are tested.
// Axes: EC (nutrient concentration) vs Light intensity
// Color: red (low yield) → green (high yield)

const GRID_SIZE = 10
const TOTAL_CELLS = GRID_SIZE * GRID_SIZE

// Pre-computed "optimal zone" — a ridge where EC 1.0-1.6 and Light 40-70% gives best yield
function yieldScore(ecIdx, lightIdx) {
  const ec = 0.4 + ecIdx * 0.16   // 0.4 - 2.0
  const light = 10 + lightIdx * 9  // 10% - 100%

  // Optimal: EC ~1.2, Light ~55%
  const ecDist = Math.abs(ec - 1.2) / 0.8
  const lightDist = Math.abs(light - 55) / 45
  const score = Math.max(0, 1 - Math.sqrt(ecDist * ecDist + lightDist * lightDist))

  // Add a secondary sweet spot at EC 0.8, Light 40
  const ec2 = Math.abs(ec - 0.8) / 0.6
  const l2 = Math.abs(light - 40) / 30
  const score2 = Math.max(0, 0.7 - Math.sqrt(ec2 * ec2 + l2 * l2))

  return Math.min(1, score + score2 * 0.4)
}

// Exploration order — spiral from edges inward (like the AI searching)
function buildExplorationOrder() {
  const order = []
  const visited = new Set()

  // Start with corners and edges, then fill inward
  // This creates a more interesting visual than sequential filling
  const layers = [
    // Edges first
    ...Array.from({ length: GRID_SIZE }, (_, i) => [0, i]),
    ...Array.from({ length: GRID_SIZE }, (_, i) => [GRID_SIZE - 1, i]),
    ...Array.from({ length: GRID_SIZE - 2 }, (_, i) => [i + 1, 0]),
    ...Array.from({ length: GRID_SIZE - 2 }, (_, i) => [i + 1, GRID_SIZE - 1]),
  ]

  layers.forEach(([r, c]) => {
    const key = `${r},${c}`
    if (!visited.has(key)) { visited.add(key); order.push([r, c]) }
  })

  // Then scatter-fill the interior (pseudo-random)
  for (let pass = 0; pass < 4; pass++) {
    for (let r = 1; r < GRID_SIZE - 1; r++) {
      for (let c = 1; c < GRID_SIZE - 1; c++) {
        const key = `${r},${c}`
        if (!visited.has(key) && ((r + c + pass) % 4 === 0)) {
          visited.add(key)
          order.push([r, c])
        }
      }
    }
  }

  // Remaining cells
  for (let r = 0; r < GRID_SIZE; r++) {
    for (let c = 0; c < GRID_SIZE; c++) {
      const key = `${r},${c}`
      if (!visited.has(key)) { visited.add(key); order.push([r, c]) }
    }
  }

  return order
}

const EXPLORATION_ORDER = buildExplorationOrder()

function scoreToColor(score, alpha = 1) {
  // Red → Amber → Green gradient
  if (score < 0.33) {
    const t = score / 0.33
    const r = 239 - t * 20
    const g = 68 + t * 90
    const b = 68 - t * 57
    return `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${alpha})`
  } else if (score < 0.66) {
    const t = (score - 0.33) / 0.33
    const r = 219 - t * 185
    const g = 158 + t * 39
    const b = 11 + t * 83
    return `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${alpha})`
  } else {
    const t = (score - 0.66) / 0.34
    const r = 34
    const g = 197 + t * 14
    const b = 94 - t * 20
    return `rgba(${r},${Math.round(g)},${Math.round(b)},${alpha})`
  }
}

export default function ParameterHeatmap({ t, running, done }) {
  const canvasRef = useRef(null)
  const [exploredCount, setExploredCount] = useState(0)
  const [bestCell, setBestCell] = useState(null)

  // Canvas setup
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * 2
      canvas.height = rect.height * 2
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // Reset
  useEffect(() => {
    if (!running && !done) {
      setExploredCount(0)
      setBestCell(null)
      const canvas = canvasRef.current
      if (canvas) {
        const ctx = canvas.getContext('2d')
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      }
    }
  }, [running, done])

  // Draw
  const draw = useCallback((numCells) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const dpr = 2

    ctx.clearRect(0, 0, W, H)
    ctx.save()
    ctx.scale(dpr, dpr)

    const w = W / dpr
    const h = H / dpr
    const pad = 24 // left padding for y-axis labels
    const padTop = 4
    const padBottom = 16
    const padRight = 4

    const gridW = w - pad - padRight
    const gridH = h - padTop - padBottom
    const cellW = gridW / GRID_SIZE
    const cellH = gridH / GRID_SIZE

    // Draw explored cells
    let best = null
    let bestScore = -1

    for (let i = 0; i < numCells && i < EXPLORATION_ORDER.length; i++) {
      const [r, c] = EXPLORATION_ORDER[i]
      const score = yieldScore(r, c)
      const x = pad + c * cellW
      const y = padTop + (GRID_SIZE - 1 - r) * cellH // flip Y so low EC is bottom

      // Cell fill
      const isRecent = i >= numCells - 3
      ctx.fillStyle = scoreToColor(score, isRecent ? 0.95 : 0.75)
      ctx.fillRect(x + 0.5, y + 0.5, cellW - 1, cellH - 1)

      // Glow for recently explored
      if (isRecent && running) {
        ctx.strokeStyle = 'rgba(167,139,250,0.6)'
        ctx.lineWidth = 1.5
        ctx.strokeRect(x + 0.5, y + 0.5, cellW - 1, cellH - 1)
      }

      if (score > bestScore) {
        bestScore = score
        best = { r, c, x, y, score }
      }
    }

    // Best cell highlight
    if (best && (done || numCells > 20)) {
      ctx.strokeStyle = 'rgba(34,211,153,0.8)'
      ctx.lineWidth = 1.5
      ctx.setLineDash([2, 2])
      ctx.strokeRect(
        pad + best.c * cellW - 1,
        padTop + (GRID_SIZE - 1 - best.r) * cellH - 1,
        cellW + 2,
        cellH + 2
      )
      ctx.setLineDash([])
    }

    // Grid outline
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.lineWidth = 0.5
    for (let i = 0; i <= GRID_SIZE; i++) {
      ctx.beginPath()
      ctx.moveTo(pad + i * cellW, padTop)
      ctx.lineTo(pad + i * cellW, padTop + gridH)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(pad, padTop + i * cellH)
      ctx.lineTo(pad + gridW, padTop + i * cellH)
      ctx.stroke()
    }

    // Axis labels
    ctx.font = '6px monospace'
    ctx.textAlign = 'right'

    // Y-axis: EC values
    for (let i = 0; i < GRID_SIZE; i += 2) {
      const ec = (0.4 + i * 0.16).toFixed(1)
      const y = padTop + (GRID_SIZE - 1 - i) * cellH + cellH / 2 + 2
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.fillText(ec, pad - 3, y)
    }

    // X-axis: Light values
    ctx.textAlign = 'center'
    for (let i = 0; i < GRID_SIZE; i += 2) {
      const light = `${10 + i * 9}%`
      const x = pad + i * cellW + cellW / 2
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.fillText(light, x, padTop + gridH + 10)
    }

    // Axis titles
    ctx.fillStyle = 'rgba(255,255,255,0.2)'
    ctx.font = '5.5px monospace'
    ctx.textAlign = 'center'
    ctx.fillText('LIGHT INTENSITY', pad + gridW / 2, padTop + gridH + 15)

    ctx.save()
    ctx.translate(6, padTop + gridH / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('EC (mS/cm)', 0, 0)
    ctx.restore()

    ctx.restore()

    if (best) setBestCell(best)
  }, [running, done])

  // Animate exploration
  useEffect(() => {
    if (!running && !done) return

    const numCells = done ? TOTAL_CELLS : Math.min(Math.floor(t * TOTAL_CELLS * 1.1), TOTAL_CELLS)
    setExploredCount(numCells)
    draw(numCells)
  }, [t, running, done, draw])

  return (
    <div style={{ marginTop: 12 }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 6,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          PARAMETER SPACE EXPLORATION
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {(running || done) && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
              color: '#a78bfa',
            }}>
              {exploredCount}/{TOTAL_CELLS} tested
            </span>
          )}
          {bestCell && done && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
              color: '#22c55e', background: 'rgba(34,211,153,0.1)',
              padding: '1px 6px', borderRadius: 3,
            }}>
              OPTIMUM: EC {(0.4 + bestCell.r * 0.16).toFixed(1)} / {10 + bestCell.c * 9}% light
            </span>
          )}
        </div>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: 130,
          borderRadius: 6,
          background: 'var(--bg-2)',
          border: '1px solid var(--border)',
          display: 'block',
        }}
      />

      {/* Legend */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 12, marginTop: 5,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <div style={{ width: 10, height: 6, borderRadius: 1, background: scoreToColor(0.1) }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>Low yield</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <div style={{ width: 10, height: 6, borderRadius: 1, background: scoreToColor(0.5) }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>Medium</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <div style={{ width: 10, height: 6, borderRadius: 1, background: scoreToColor(0.9) }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>High yield</span>
        </div>
      </div>
    </div>
  )
}
