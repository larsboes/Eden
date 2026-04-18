import { useState, useEffect, useRef } from 'react'

// Always-on ambient visualization showing the AI continuously optimizing.
// Combines: mini parameter sweep + live optimization metrics + data pulses.
// Placed in LabView between pods and simulation runner.

const CYCLE_MS = 15000 // 15s per full optimization cycle
const GRID = 8

// Parameters the AI is continuously tuning
const PARAMS = [
  { name: 'EC',     unit: 'mS/cm', min: 0.6, max: 2.0, optimal: 1.2 },
  { name: 'Light',  unit: '%',     min: 20,  max: 90,  optimal: 55 },
  { name: 'pH',     unit: '',      min: 5.0, max: 7.5, optimal: 6.2 },
  { name: 'Temp',   unit: 'C',     min: 16,  max: 28,  optimal: 22 },
  { name: 'VPD',    unit: 'kPa',   min: 0.4, max: 1.6, optimal: 0.95 },
  { name: 'CO2',    unit: 'ppm',   min: 400, max: 1200, optimal: 850 },
]

// Simulated optimization: current value oscillates toward optimal
function paramValue(param, t) {
  const noise = Math.sin(t * Math.PI * 4 + param.optimal) * 0.15
  const approach = Math.min(1, t * 1.3)
  const range = param.max - param.min
  const start = param.min + range * (0.3 + noise * 0.5)
  return start + (param.optimal - start) * approach
}

export default function AmbientOptimizer() {
  const [t, setT] = useState(0)
  const [cycle, setCycle] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(performance.now())

  useEffect(() => {
    const tick = () => {
      const elapsed = performance.now() - startRef.current
      const cycleT = (elapsed % CYCLE_MS) / CYCLE_MS
      setT(cycleT)
      setCycle(Math.floor(elapsed / CYCLE_MS))
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [])

  // Mini heatmap: how many cells "explored" this cycle
  const explored = Math.floor(t * GRID * GRID)

  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid rgba(167,139,250,0.12)',
      borderRadius: 'var(--radius-lg)',
      padding: '12px 16px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#a78bfa',
            boxShadow: '0 0 8px rgba(167,139,250,0.5)',
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            letterSpacing: 1.5, color: '#a78bfa',
          }}>
            CONTINUOUS OPTIMIZATION
          </span>
        </div>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--fg-muted)',
        }}>
          cycle {cycle + 1} · {Math.round(t * 100)}%
        </span>
      </div>

      {/* Two columns: live params + mini heatmap */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {/* Live parameter tuning */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {PARAMS.map((p, i) => {
            const val = paramValue(p, t)
            const normalized = (val - p.min) / (p.max - p.min)
            const distFromOptimal = Math.abs(val - p.optimal) / (p.max - p.min)
            const color = distFromOptimal < 0.1 ? '#22c55e' : distFromOptimal < 0.25 ? '#f59e0b' : '#ef4444'

            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
                  color: 'var(--fg-muted)', width: 32, letterSpacing: 0.5,
                }}>
                  {p.name}
                </span>
                {/* Progress bar */}
                <div style={{
                  flex: 1, height: 4, borderRadius: 2,
                  background: 'var(--bg-3)', position: 'relative', overflow: 'hidden',
                }}>
                  <div style={{
                    position: 'absolute', left: 0, top: 0, bottom: 0,
                    width: `${normalized * 100}%`,
                    background: color,
                    borderRadius: 2,
                    transition: 'width 0.1s linear, background 0.3s',
                  }} />
                  {/* Optimal marker */}
                  <div style={{
                    position: 'absolute',
                    left: `${((p.optimal - p.min) / (p.max - p.min)) * 100}%`,
                    top: -1, bottom: -1, width: 1,
                    background: 'rgba(167,139,250,0.5)',
                  }} />
                </div>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 600,
                  color, width: 36, textAlign: 'right',
                }}>
                  {val.toFixed(p.unit === '' ? 1 : p.unit === 'ppm' ? 0 : 1)}{p.unit ? ` ${p.unit}` : ''}
                </span>
              </div>
            )
          })}
        </div>

        {/* Mini exploration heatmap */}
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
            color: 'var(--fg-muted)', letterSpacing: 1, marginBottom: 4,
          }}>
            SEARCH SPACE
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${GRID}, 1fr)`,
            gap: 1,
          }}>
            {Array.from({ length: GRID * GRID }, (_, i) => {
              const row = Math.floor(i / GRID)
              const col = i % GRID
              const isExplored = i < explored
              // Score based on distance from center (optimal zone)
              const dx = (col / (GRID - 1)) - 0.5
              const dy = (row / (GRID - 1)) - 0.5
              const score = Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) * 2.2)

              return (
                <div key={i} style={{
                  aspectRatio: '1',
                  borderRadius: 1,
                  background: isExplored
                    ? score > 0.6 ? `rgba(34,197,94,${0.3 + score * 0.5})`
                    : score > 0.3 ? `rgba(245,158,11,${0.2 + score * 0.4})`
                    : `rgba(239,68,68,${0.15 + score * 0.3})`
                    : 'rgba(255,255,255,0.02)',
                  transition: 'background 0.15s',
                }} />
              )
            })}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)',
            marginTop: 3, textAlign: 'center',
          }}>
            {explored}/{GRID * GRID} combinations
          </div>
        </div>
      </div>

      {/* Bottom status line */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginTop: 8, paddingTop: 6,
        borderTop: '1px solid rgba(167,139,250,0.06)',
      }}>
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { label: 'Yield delta', value: `+${(t * 3.2).toFixed(1)}%`, color: '#22c55e' },
            { label: 'Water saved', value: `${(t * 12).toFixed(0)}L`, color: '#06b6d4' },
            { label: 'Convergence', value: `${Math.min(99, Math.round(t * 105))}%`, color: '#a78bfa' },
          ].map((m, i) => (
            <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 7 }}>
              <span style={{ color: 'var(--fg-muted)' }}>{m.label}: </span>
              <span style={{ color: m.color, fontWeight: 700 }}>{m.value}</span>
            </div>
          ))}
        </div>
        {/* Spinning dots indicator */}
        <div style={{ display: 'flex', gap: 2 }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              width: 3, height: 3, borderRadius: '50%',
              background: '#a78bfa',
              animation: `pulse 1.5s ease-in-out ${i * 0.3}s infinite`,
            }} />
          ))}
        </div>
      </div>
    </div>
  )
}
