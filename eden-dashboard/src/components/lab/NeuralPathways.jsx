import { useState, useEffect, useRef } from 'react'

// Translucent neural connections overlaid on a plant.
// Pathways light up as the AI discovers patterns.
// Two modes:
//   - Simulation mode: driven by external t prop (0-1)
//   - Ambient mode: self-running continuous loop, always alive

const PATHWAYS = [
  { x1: 45, y1: 100, x2: 30, y2: 80, group: 'root', phase: 0.05, label: 'root uptake' },
  { x1: 45, y1: 100, x2: 60, y2: 82, group: 'root', phase: 0.08 },
  { x1: 30, y1: 80, x2: 20, y2: 65, group: 'root', phase: 0.12 },
  { x1: 45, y1: 85, x2: 45, y2: 60, group: 'transport', phase: 0.15, label: 'nutrient flow' },
  { x1: 45, y1: 60, x2: 45, y2: 40, group: 'transport', phase: 0.20 },
  { x1: 45, y1: 55, x2: 25, y2: 45, group: 'photo', phase: 0.25, label: 'photosynthesis' },
  { x1: 45, y1: 55, x2: 65, y2: 42, group: 'photo', phase: 0.28 },
  { x1: 25, y1: 45, x2: 15, y2: 35, group: 'photo', phase: 0.32 },
  { x1: 65, y1: 42, x2: 75, y2: 30, group: 'photo', phase: 0.35 },
  { x1: 45, y1: 40, x2: 35, y2: 25, group: 'stress', phase: 0.40, label: 'stress response' },
  { x1: 35, y1: 25, x2: 25, y2: 15, group: 'stress', phase: 0.45 },
  { x1: 45, y1: 40, x2: 55, y2: 22, group: 'stress', phase: 0.42 },
  { x1: 45, y1: 30, x2: 40, y2: 12, group: 'repro', phase: 0.55, label: 'flowering' },
  { x1: 40, y1: 12, x2: 50, y2: 5, group: 'repro', phase: 0.60 },
  { x1: 30, y1: 80, x2: 45, y2: 55, group: 'insight', phase: 0.50 },
  { x1: 65, y1: 42, x2: 55, y2: 22, group: 'insight', phase: 0.55 },
  { x1: 25, y1: 45, x2: 35, y2: 25, group: 'insight', phase: 0.65 },
]

const SYNAPSES = [
  { x: 45, y: 100, phase: 0.03 },
  { x: 30, y: 80, phase: 0.10 },
  { x: 60, y: 82, phase: 0.10 },
  { x: 45, y: 60, phase: 0.18 },
  { x: 25, y: 45, phase: 0.27 },
  { x: 65, y: 42, phase: 0.30 },
  { x: 45, y: 40, phase: 0.38 },
  { x: 35, y: 25, phase: 0.43 },
  { x: 55, y: 22, phase: 0.44 },
  { x: 40, y: 12, phase: 0.57 },
  { x: 50, y: 5, phase: 0.62 },
]

const GROUP_COLORS = {
  root: '96,165,250',
  transport: '167,139,250',
  photo: '52,211,153',
  stress: '239,68,68',
  repro: '245,158,11',
  insight: '167,139,250',
}

const AMBIENT_CYCLE = 10000 // 10s per cycle

export default function NeuralPathways({ t, running, ambient = false, width = 90, height = 110, id = '' }) {
  const [ambientT, setAmbientT] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(null)

  // Ambient self-running loop
  useEffect(() => {
    if (!ambient) return

    startRef.current = performance.now()
    const tick = () => {
      const elapsed = performance.now() - startRef.current
      // Smooth sawtooth: ramp 0→1 over AMBIENT_CYCLE, then restart
      setAmbientT((elapsed % AMBIENT_CYCLE) / AMBIENT_CYCLE)
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [ambient])

  const active = ambient || running
  if (!active) return null

  // In ambient mode, only show a subset of pathways at reduced opacity
  // Cycle through groups: each group "activates" for part of the cycle
  const progress = ambient ? ambientT : t
  const ambientDim = ambient ? 0.5 : 1 // dimmer in ambient mode

  // In ambient mode, use a rolling window — pathways fade in and out
  const getAmbientVisibility = (phase) => {
    if (!ambient) return progress >= phase ? 1 : 0
    // Rolling window: each pathway visible for ~40% of cycle
    const window = 0.4
    const dist = ((progress - phase) % 1 + 1) % 1
    if (dist < window) return Math.min(1, dist / 0.08) // fade in
    if (dist < window + 0.08) return 1 - (dist - window) / 0.08 // fade out
    return 0
  }

  const filterId = `neuralGlow${id}`

  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 90 110"
      style={{
        position: 'absolute',
        top: 0, left: '50%',
        transform: 'translateX(-50%)',
        pointerEvents: 'none',
        zIndex: 3,
      }}
    >
      <defs>
        <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Pathway connections */}
      {PATHWAYS.map((p, i) => {
        const vis = getAmbientVisibility(p.phase)
        if (vis <= 0) return null
        const rgb = GROUP_COLORS[p.group] || '167,139,250'
        const alpha = vis * ambientDim
        const isInsight = p.group === 'insight'

        return (
          <g key={i} opacity={alpha}>
            <line
              x1={p.x1} y1={p.y1} x2={p.x2} y2={p.y2}
              stroke={`rgba(${rgb},${0.15 + vis * 0.25})`}
              strokeWidth={isInsight ? 0.6 : 0.8}
              strokeDasharray={isInsight ? '2 2' : 'none'}
            />
            <line
              x1={p.x1} y1={p.y1} x2={p.x2} y2={p.y2}
              stroke={`rgba(${rgb},${0.05 + vis * 0.1})`}
              strokeWidth={isInsight ? 2 : 3}
              filter={`url(#${filterId})`}
            />
            {/* Traveling pulse */}
            <circle r={1.2} fill={`rgba(${rgb},${0.5 * alpha})`}>
              <animateMotion
                dur={`${0.8 + i * 0.1}s`}
                repeatCount="indefinite"
                path={`M${p.x1},${p.y1} L${p.x2},${p.y2}`}
              />
            </circle>
            {/* Label — only in simulation mode */}
            {!ambient && p.label && vis > 0.3 && (
              <text
                x={(p.x1 + p.x2) / 2}
                y={(p.y1 + p.y2) / 2 - 3}
                textAnchor="middle"
                fill={`rgba(${rgb},${0.2 + vis * 0.15})`}
                fontSize={4}
                fontFamily="monospace"
                fontWeight={600}
              >
                {p.label}
              </text>
            )}
          </g>
        )
      })}

      {/* Synapse nodes */}
      {SYNAPSES.map((s, i) => {
        const vis = getAmbientVisibility(s.phase)
        if (vis <= 0) return null

        return (
          <g key={i} opacity={vis * ambientDim}>
            <circle
              cx={s.x} cy={s.y}
              r={1.5 + vis * 0.5}
              fill={`rgba(167,139,250,${0.15 + vis * 0.3})`}
            />
            {/* Ambient pulse ring */}
            {vis > 0.8 && (
              <circle
                cx={s.x} cy={s.y} r={3}
                fill="none"
                stroke="rgba(167,139,250,0.15)"
                strokeWidth={0.5}
              >
                <animate attributeName="r" values="3;7" dur="1.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.3;0" dur="1.5s" repeatCount="indefinite" />
              </circle>
            )}
          </g>
        )
      })}
    </svg>
  )
}
