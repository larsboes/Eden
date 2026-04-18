import { useMemo } from 'react'

// Visual decision tree that grows as the AI makes choices.
// Branches fork at decision points. Failed branches wither (gray).
// Optimal path glows green. Grows left-to-right.

const NODES = [
  // Level 0: Root
  { id: 'start', x: 0, y: 0.5, label: 'CME Detected', phase: 0 },

  // Level 1: First decision
  { id: 'assess', x: 0.15, y: 0.5, label: 'Assess Risk', phase: 0.05 },

  // Level 2: Strategy fork
  { id: 'doNothing', x: 0.32, y: 0.15, label: 'Do Nothing', phase: 0.12, strategy: 'A' },
  { id: 'standard',  x: 0.32, y: 0.50, label: 'Shield Only', phase: 0.12, strategy: 'B' },
  { id: 'preemptive', x: 0.32, y: 0.85, label: 'Pre-emptive', phase: 0.12, strategy: 'C' },

  // Level 3: Outcomes of each strategy
  { id: 'a_impact', x: 0.52, y: 0.10, label: 'No Protection', phase: 0.35, strategy: 'A' },
  { id: 'b_shield', x: 0.52, y: 0.42, label: 'Shields Up', phase: 0.25, strategy: 'B' },
  { id: 'b_nowater', x: 0.52, y: 0.58, label: 'No Stockpile', phase: 0.35, strategy: 'B' },
  { id: 'c_stock', x: 0.52, y: 0.78, label: 'Stockpile 240L', phase: 0.20, strategy: 'C' },
  { id: 'c_harden', x: 0.52, y: 0.92, label: 'Harden EC+0.4', phase: 0.25, strategy: 'C' },

  // Level 4: Final outcomes
  { id: 'a_loss', x: 0.75, y: 0.10, label: '40% LOSS', phase: 0.60, strategy: 'A', terminal: true },
  { id: 'b_loss', x: 0.75, y: 0.50, label: '12% LOSS', phase: 0.60, strategy: 'B', terminal: true },
  { id: 'c_loss', x: 0.75, y: 0.85, label: '3% LOSS', phase: 0.60, strategy: 'C', terminal: true },

  // Level 5: Verdict
  { id: 'selected', x: 0.92, y: 0.85, label: 'SELECTED', phase: 0.85, strategy: 'C', selected: true },
]

const EDGES = [
  { from: 'start', to: 'assess', phase: 0.02 },
  { from: 'assess', to: 'doNothing', phase: 0.08 },
  { from: 'assess', to: 'standard', phase: 0.08 },
  { from: 'assess', to: 'preemptive', phase: 0.08 },
  { from: 'doNothing', to: 'a_impact', phase: 0.20 },
  { from: 'standard', to: 'b_shield', phase: 0.20 },
  { from: 'standard', to: 'b_nowater', phase: 0.25 },
  { from: 'preemptive', to: 'c_stock', phase: 0.15 },
  { from: 'preemptive', to: 'c_harden', phase: 0.20 },
  { from: 'a_impact', to: 'a_loss', phase: 0.45 },
  { from: 'b_shield', to: 'b_loss', phase: 0.45 },
  { from: 'b_nowater', to: 'b_loss', phase: 0.50 },
  { from: 'c_stock', to: 'c_loss', phase: 0.45 },
  { from: 'c_harden', to: 'c_loss', phase: 0.50 },
  { from: 'c_loss', to: 'selected', phase: 0.75 },
]

const STRATEGY_COLORS = {
  A: '#ef4444',
  B: '#f59e0b',
  C: '#22c55e',
}

export default function DecisionTree({ t, running, done }) {
  const nodeMap = useMemo(() => {
    const m = {}
    NODES.forEach(n => { m[n.id] = n })
    return m
  }, [])

  const progress = done ? 1 : t

  if (!running && !done) {
    return (
      <div style={{
        marginTop: 12, padding: '10px 14px',
        background: 'var(--bg-2)', border: '1px solid var(--border)',
        borderRadius: 8, opacity: 0.5,
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          DECISION TREE — waiting for simulation
        </div>
      </div>
    )
  }

  const W = 600
  const H = 160
  const padX = 50
  const padY = 14

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 6,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          DECISION TREE
        </span>
        {done && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
            color: '#22c55e', background: 'rgba(34,211,153,0.1)',
            padding: '1px 6px', borderRadius: 3,
          }}>
            OPTIMAL PATH FOUND
          </span>
        )}
      </div>

      <div style={{
        background: 'var(--bg-2)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '8px 4px', overflow: 'hidden',
      }}>
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
          {/* Edges */}
          {EDGES.map((edge, i) => {
            const from = nodeMap[edge.from]
            const to = nodeMap[edge.to]
            if (!from || !to) return null

            const visible = progress >= edge.phase
            if (!visible) return null

            const x1 = padX + from.x * (W - padX * 2)
            const y1 = padY + from.y * (H - padY * 2)
            const x2 = padX + to.x * (W - padX * 2)
            const y2 = padY + to.y * (H - padY * 2)

            const strat = to.strategy || from.strategy
            const color = strat ? STRATEGY_COLORS[strat] : '#a78bfa'
            const isOptimal = strat === 'C'
            const isFailed = strat === 'A' && progress > 0.65
            const isSubopt = strat === 'B' && progress > 0.65

            // Bezier control point for organic curves
            const cpx = (x1 + x2) / 2
            const cpy1 = y1
            const cpy2 = y2

            return (
              <g key={i}>
                <path
                  d={`M${x1},${y1} C${cpx},${cpy1} ${cpx},${cpy2} ${x2},${y2}`}
                  fill="none"
                  stroke={isFailed || isSubopt ? 'rgba(255,255,255,0.08)' : color}
                  strokeWidth={isOptimal && done ? 2 : 1}
                  opacity={isFailed ? 0.3 : isSubopt ? 0.4 : isOptimal ? 0.8 : 0.5}
                  strokeDasharray={isFailed ? '3 3' : 'none'}
                  style={{ transition: 'all 0.5s' }}
                />
                {/* Glow for optimal path */}
                {isOptimal && done && (
                  <path
                    d={`M${x1},${y1} C${cpx},${cpy1} ${cpx},${cpy2} ${x2},${y2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={4}
                    opacity={0.1}
                  />
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const visible = progress >= node.phase
            if (!visible) return null

            const x = padX + node.x * (W - padX * 2)
            const y = padY + node.y * (H - padY * 2)

            const color = node.strategy ? STRATEGY_COLORS[node.strategy] : '#a78bfa'
            const isFailed = node.strategy === 'A' && progress > 0.65
            const isSubopt = node.strategy === 'B' && progress > 0.65
            const isOptimal = node.strategy === 'C'
            const dimmed = isFailed || isSubopt

            return (
              <g key={node.id} style={{ transition: 'opacity 0.5s' }}>
                {/* Node circle */}
                <circle
                  cx={x} cy={y}
                  r={node.terminal ? 6 : node.selected ? 7 : 4}
                  fill={dimmed ? 'var(--bg-3)' : node.selected ? color : 'var(--bg-2)'}
                  stroke={dimmed ? 'rgba(255,255,255,0.1)' : color}
                  strokeWidth={node.selected ? 2 : 1}
                  opacity={dimmed ? 0.4 : 1}
                />

                {/* Glow for selected */}
                {node.selected && (
                  <circle cx={x} cy={y} r={12} fill="none" stroke={color} strokeWidth={1} opacity={0.2}>
                    <animate attributeName="r" values="10;14;10" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.2;0.05;0.2" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}

                {/* Terminal loss badge */}
                {node.terminal && (
                  <rect
                    x={x - 20} y={y - 18} width={40} height={12} rx={3}
                    fill={dimmed ? 'rgba(255,255,255,0.03)' : color + '18'}
                    stroke={dimmed ? 'rgba(255,255,255,0.05)' : color + '40'}
                    strokeWidth={0.5}
                  />
                )}

                {/* Label */}
                <text
                  x={x}
                  y={node.terminal ? y - 10 : y + (node.y < 0.3 ? -10 : 14)}
                  textAnchor="middle"
                  fill={dimmed ? 'rgba(255,255,255,0.2)' : color}
                  fontSize={node.terminal || node.selected ? 7 : 6}
                  fontFamily="monospace"
                  fontWeight={node.terminal || node.selected ? 700 : 400}
                  style={{ transition: 'fill 0.5s' }}
                >
                  {node.label}
                </text>

                {/* X mark on failed paths */}
                {isFailed && node.terminal && (
                  <g opacity={0.5}>
                    <line x1={x - 4} y1={y - 4} x2={x + 4} y2={y + 4} stroke="#ef4444" strokeWidth={1.5} />
                    <line x1={x + 4} y1={y - 4} x2={x - 4} y2={y + 4} stroke="#ef4444" strokeWidth={1.5} />
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
