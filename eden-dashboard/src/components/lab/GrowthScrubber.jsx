import { useMemo } from 'react'
import PlantSVG from '../PlantSVG'

// The AI fast-forwards through the entire plant lifecycle in seconds
// Filmstrip of BBCH stages + spinning sol counter = "the AI is simulating the future"

const STAGES = [
  { bbch: 0,  label: 'Germination',  sol: 1 },
  { bbch: 10, label: 'Seedling',     sol: 15 },
  { bbch: 20, label: 'Tillering',    sol: 45 },
  { bbch: 30, label: 'Stem elongation', sol: 90 },
  { bbch: 45, label: 'Booting',      sol: 150 },
  { bbch: 55, label: 'Heading',      sol: 210 },
  { bbch: 65, label: 'Flowering',    sol: 280 },
  { bbch: 75, label: 'Grain fill',   sol: 340 },
  { bbch: 85, label: 'Maturity',     sol: 420 },
  { bbch: 89, label: 'Harvest',      sol: 450 },
]

export default function GrowthScrubber({ t, running, done, crop = 'Wheat' }) {
  // Current simulated BBCH based on progress
  const bbch = Math.round(t * 89)
  const sol = Math.round(t * 450)

  // Find current and adjacent stages for the filmstrip
  const activeIdx = useMemo(() => {
    let idx = 0
    for (let i = 0; i < STAGES.length; i++) {
      if (bbch >= STAGES[i].bbch) idx = i
    }
    return idx
  }, [bbch])

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
          LIFECYCLE SCRUBBER — waiting for simulation
        </div>
      </div>
    )
  }

  return (
    <div style={{
      marginTop: 12, padding: '10px 14px',
      background: 'var(--bg-2)',
      border: `1px solid ${running ? 'rgba(167,139,250,0.2)' : 'rgba(34,211,153,0.2)'}`,
      borderRadius: 8,
      transition: 'border-color 0.5s',
    }}>
      {/* Header with sol odometer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          LIFECYCLE SCRUBBER
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* BBCH badge */}
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            color: '#a78bfa', background: 'rgba(167,139,250,0.1)',
            padding: '2px 6px', borderRadius: 3,
          }}>
            BBCH {bbch}
          </span>
          {/* Sol odometer */}
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700,
            color: running ? '#e8913a' : '#22c55e',
            background: running ? 'rgba(232,145,58,0.08)' : 'rgba(34,211,153,0.08)',
            padding: '2px 8px', borderRadius: 4,
            minWidth: 72, textAlign: 'center',
            letterSpacing: 1,
            transition: 'color 0.3s',
          }}>
            Sol {String(sol).padStart(3, '0')}
          </div>
        </div>
      </div>

      {/* Filmstrip — scrolling stages */}
      <div style={{
        display: 'flex', gap: 4, overflow: 'hidden', position: 'relative',
      }}>
        {STAGES.map((stage, i) => {
          const isActive = i === activeIdx
          const isPast = i < activeIdx
          const isFuture = i > activeIdx

          return (
            <div key={i} style={{
              flex: '0 0 auto',
              width: 64,
              padding: '6px 4px 4px',
              background: isActive
                ? 'rgba(167,139,250,0.08)'
                : isPast
                  ? 'rgba(34,211,153,0.04)'
                  : 'transparent',
              border: `1px solid ${isActive ? 'rgba(167,139,250,0.3)' : isPast ? 'rgba(34,211,153,0.15)' : 'var(--border)'}`,
              borderRadius: 6,
              opacity: isFuture ? 0.3 : isPast ? 0.6 : 1,
              transition: 'all 0.3s',
              position: 'relative',
            }}>
              {/* Stage plant thumbnail */}
              <div style={{
                display: 'flex', justifyContent: 'center', height: 44,
                filter: isFuture ? 'grayscale(1)' : 'none',
                transition: 'filter 0.3s',
              }}>
                <PlantSVG
                  crop={crop}
                  bbch={stage.bbch}
                  health={90}
                  stressed={false}
                  width={40}
                  height={44}
                />
              </div>

              {/* Stage label */}
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 6.5, fontWeight: 600,
                color: isActive ? '#a78bfa' : isPast ? '#22c55e' : 'var(--fg-muted)',
                textAlign: 'center', marginTop: 2,
                letterSpacing: 0.3,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {stage.label}
              </div>

              {/* Active indicator */}
              {isActive && (
                <div style={{
                  position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)',
                  width: 20, height: 2, borderRadius: 1,
                  background: '#a78bfa',
                  boxShadow: '0 0 6px rgba(167,139,250,0.5)',
                }} />
              )}

              {/* Check mark for completed stages */}
              {isPast && (
                <div style={{
                  position: 'absolute', top: 2, right: 2,
                  fontFamily: 'var(--font-mono)', fontSize: 7,
                  color: '#22c55e',
                }}>
                  OK
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Timeline progress bar */}
      <div style={{
        marginTop: 6, height: 2, borderRadius: 1,
        background: 'var(--bg-3)', overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: 1,
          width: `${t * 100}%`,
          background: done
            ? '#22c55e'
            : 'linear-gradient(90deg, #22c55e, #a78bfa, #e8913a)',
          transition: running ? 'none' : 'width 0.3s',
        }} />
      </div>

      {/* Sol range labels */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', marginTop: 3,
      }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>Sol 001</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>Sol 450</span>
      </div>
    </div>
  )
}
