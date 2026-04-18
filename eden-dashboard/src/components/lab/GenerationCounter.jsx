import { useMemo } from 'react'

// Shows the AI iterating through strategy "generations".
// Each gen is briefly evaluated and either discarded or kept.
// Winning config persists, others fade. Like compressed evolution.

const GENERATIONS = [
  { gen: 1, phase: 0.03, label: 'Random baseline', fitness: 0.12, status: 'fail', detail: 'No protection, no stockpile' },
  { gen: 2, phase: 0.08, label: 'Shield-only variant', fitness: 0.31, status: 'fail', detail: 'Shields but no water prep' },
  { gen: 3, phase: 0.14, label: 'Delayed response', fitness: 0.28, status: 'fail', detail: 'Wait for impact + react' },
  { gen: 4, phase: 0.20, label: 'High-EC stress test', fitness: 0.45, status: 'improve', detail: 'EC+0.8 — too aggressive' },
  { gen: 5, phase: 0.28, label: 'Moderate pre-harden', fitness: 0.62, status: 'improve', detail: 'EC+0.4 + partial shield' },
  { gen: 6, phase: 0.36, label: 'Stockpile variant A', fitness: 0.71, status: 'improve', detail: '180L stockpile + shield' },
  { gen: 7, phase: 0.44, label: 'Stockpile + harvest', fitness: 0.79, status: 'improve', detail: '200L + pre-harvest spinach' },
  { gen: 8, phase: 0.54, label: 'Full pre-emptive v1', fitness: 0.85, status: 'improve', detail: '240L + EC+0.4 + shields' },
  { gen: 9, phase: 0.65, label: 'Optimized pre-emptive', fitness: 0.91, status: 'improve', detail: 'Tuned timing + 240L + EC+0.4' },
  { gen: 10, phase: 0.78, label: 'Final candidate', fitness: 0.97, status: 'optimal', detail: 'Pre-emptive protocol — 3% loss' },
]

function fitnessColor(fitness) {
  if (fitness < 0.3) return '#ef4444'
  if (fitness < 0.5) return '#f59e0b'
  if (fitness < 0.8) return '#60a5fa'
  return '#22c55e'
}

export default function GenerationCounter({ t, running, done }) {
  const progress = done ? 1 : t

  const visibleGens = useMemo(() => {
    return GENERATIONS.filter(g => progress >= g.phase)
  }, [progress])

  const currentGen = visibleGens[visibleGens.length - 1]

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
          EVOLUTIONARY SEARCH — waiting for simulation
        </div>
      </div>
    )
  }

  return (
    <div style={{
      marginTop: 12, padding: '10px 14px',
      background: 'var(--bg-2)',
      border: `1px solid ${done ? 'rgba(34,211,153,0.2)' : 'rgba(167,139,250,0.15)'}`,
      borderRadius: 8,
      transition: 'border-color 0.5s',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          EVOLUTIONARY SEARCH
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {currentGen && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
              color: running ? '#a78bfa' : '#22c55e',
              animation: running ? 'pulse 1.5s ease-in-out infinite' : 'none',
            }}>
              Gen {currentGen.gen}/{GENERATIONS.length}
            </span>
          )}
          {currentGen && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
              color: fitnessColor(currentGen.fitness),
              background: fitnessColor(currentGen.fitness) + '15',
              padding: '1px 6px', borderRadius: 3,
            }}>
              Fitness: {Math.round(currentGen.fitness * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* Generation timeline */}
      <div style={{
        display: 'flex', gap: 2, alignItems: 'flex-end', height: 60,
        marginBottom: 8,
      }}>
        {GENERATIONS.map((gen, i) => {
          const visible = progress >= gen.phase
          const isCurrent = currentGen?.gen === gen.gen
          const barH = gen.fitness * 50

          return (
            <div key={i} style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 2,
            }}>
              {/* Fitness bar */}
              <div style={{
                width: '100%',
                height: visible ? barH : 0,
                background: visible
                  ? isCurrent
                    ? `linear-gradient(180deg, ${fitnessColor(gen.fitness)}, ${fitnessColor(gen.fitness)}80)`
                    : gen.status === 'fail'
                      ? 'rgba(239,68,68,0.15)'
                      : `${fitnessColor(gen.fitness)}30`
                  : 'transparent',
                borderRadius: '3px 3px 0 0',
                border: visible
                  ? `1px solid ${isCurrent ? fitnessColor(gen.fitness) + '60' : 'transparent'}`
                  : 'none',
                borderBottom: 'none',
                transition: 'height 0.4s ease, background 0.3s',
                position: 'relative',
              }}>
                {/* Fail X */}
                {visible && gen.status === 'fail' && (
                  <div style={{
                    position: 'absolute', top: '50%', left: '50%',
                    transform: 'translate(-50%, -50%)',
                    fontFamily: 'var(--font-mono)', fontSize: 7,
                    color: '#ef4444', fontWeight: 700, opacity: 0.5,
                  }}>X</div>
                )}
                {/* Optimal check */}
                {visible && gen.status === 'optimal' && (
                  <div style={{
                    position: 'absolute', top: -8, left: '50%',
                    transform: 'translateX(-50%)',
                    fontFamily: 'var(--font-mono)', fontSize: 8,
                    color: '#22c55e', fontWeight: 700,
                  }}>
                    BEST
                  </div>
                )}
              </div>
              {/* Gen number */}
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 7,
                color: visible
                  ? isCurrent ? fitnessColor(gen.fitness) : 'var(--fg-muted)'
                  : 'var(--bg-3)',
                fontWeight: isCurrent ? 700 : 400,
                transition: 'color 0.3s',
              }}>
                {gen.gen}
              </span>
            </div>
          )
        })}
      </div>

      {/* Current generation detail */}
      {currentGen && (
        <div style={{
          padding: '6px 8px',
          background: fitnessColor(currentGen.fitness) + '08',
          borderRadius: 4,
          borderLeft: `2px solid ${fitnessColor(currentGen.fitness)}40`,
          animation: 'fadeIn 0.3s ease both',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            color: fitnessColor(currentGen.fitness),
            marginBottom: 2,
          }}>
            {currentGen.label}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 8,
            color: 'var(--fg-muted)', lineHeight: 1.5,
          }}>
            {currentGen.detail}
          </div>
        </div>
      )}

      {/* Fitness progress curve (mini sparkline) */}
      {visibleGens.length > 1 && (
        <svg width="100%" height="20" viewBox="0 0 200 20" style={{ marginTop: 6, display: 'block' }}>
          <polyline
            points={visibleGens.map((g, i) => {
              const x = (i / (GENERATIONS.length - 1)) * 196 + 2
              const y = 18 - g.fitness * 16
              return `${x},${y}`
            }).join(' ')}
            fill="none"
            stroke="#a78bfa"
            strokeWidth={1}
            opacity={0.5}
          />
          {/* Dots */}
          {visibleGens.map((g, i) => {
            const x = (i / (GENERATIONS.length - 1)) * 196 + 2
            const y = 18 - g.fitness * 16
            return (
              <circle
                key={i}
                cx={x} cy={y} r={2}
                fill={fitnessColor(g.fitness)}
                opacity={0.7}
              />
            )
          })}
        </svg>
      )}
    </div>
  )
}
