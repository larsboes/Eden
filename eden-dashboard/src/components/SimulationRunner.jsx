import { useState, useEffect, useRef, useCallback } from 'react'
import PlantSVG from './PlantSVG'
import MonteCarloSwarm from './lab/MonteCarloSwarm'
import GrowthScrubber from './lab/GrowthScrubber'
import ParameterHeatmap from './lab/ParameterHeatmap'
import DecisionTree from './lab/DecisionTree'
import NeuralPathways from './lab/NeuralPathways'
import LabNotebook from './lab/LabNotebook'
import GenerationCounter from './lab/GenerationCounter'

// ── Simulation timeline (12s total) ────────────────────────────────────────
const PHASES = [
  { id: 'init',     label: 'INITIALIZING',    duration: 1500, sol: 247 },
  { id: 'prestorm', label: 'PRE-STORM PREP',  duration: 2500, sol: 247 },
  { id: 'impact',   label: 'CME IMPACT',      duration: 4000, sol: 249 },
  { id: 'recovery', label: 'POST-STORM',      duration: 4000, sol: 254 },
]
const TOTAL_DURATION = PHASES.reduce((s, p) => s + p.duration, 0)

// Strategy simulation curves — health over normalized time [0..1]
const STRATEGIES = [
  {
    name: 'A: Do Nothing',
    color: '#ef4444',
    healthCurve: (t) => t < 0.15 ? 90 : t < 0.35 ? 90 - (t - 0.15) * 50 : t < 0.7 ? 80 - (t - 0.35) * 140 : Math.max(31, 30 + (t - 0.7) * 5),
    waterCurve: (t) => t < 0.3 ? 340 : 340 - (t - 0.3) * 400,
    radiationCurve: (t) => t < 0.3 ? 2 : t < 0.7 ? 2 + (t - 0.3) * 650 : 263 - (t - 0.7) * 800,
    loss: 40, outcome: 'CATASTROPHIC',
  },
  {
    name: 'B: Standard',
    color: '#f59e0b',
    healthCurve: (t) => t < 0.15 ? 90 : t < 0.35 ? 90 - (t - 0.15) * 15 : t < 0.7 ? 87 - (t - 0.35) * 50 : Math.min(82, 70 + (t - 0.7) * 40),
    waterCurve: (t) => t < 0.3 ? 340 : t < 0.5 ? 340 - (t - 0.3) * 600 : Math.max(120, 220 - (t - 0.5) * 200),
    radiationCurve: (t) => t < 0.3 ? 2 : t < 0.7 ? 2 + (t - 0.3) * 450 : 182 - (t - 0.7) * 550,
    loss: 12, outcome: 'SUBOPTIMAL',
  },
  {
    name: 'C: Pre-emptive',
    color: '#22c55e',
    healthCurve: (t) => t < 0.15 ? 90 : t < 0.35 ? 90 + (t - 0.15) * 10 : t < 0.7 ? 92 - (t - 0.35) * 25 : Math.min(94, 83 + (t - 0.7) * 37),
    waterCurve: (t) => t < 0.15 ? 340 : t < 0.35 ? 340 + (t - 0.15) * 1200 : t < 0.7 ? 580 - (t - 0.35) * 500 : Math.min(500, 405 + (t - 0.7) * 300),
    radiationCurve: (t) => t < 0.3 ? 2 : t < 0.7 ? 2 + (t - 0.3) * 250 : 102 - (t - 0.7) * 300,
    loss: 3, outcome: 'OPTIMAL',
  },
]

// Crop to simulate in each panel
const SIM_CROP = { name: 'Wheat', bbch: 60 }

export default function SimulationRunner({ onComplete }) {
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [done, setDone] = useState(false)
  const startRef = useRef(null)
  const rafRef = useRef(null)

  const tick = useCallback(() => {
    const now = performance.now()
    const dt = now - startRef.current
    if (dt >= TOTAL_DURATION) {
      setElapsed(TOTAL_DURATION)
      setRunning(false)
      setDone(true)
      onComplete?.()
      return
    }
    setElapsed(dt)
    rafRef.current = requestAnimationFrame(tick)
  }, [onComplete])

  const start = useCallback(() => {
    setDone(false)
    setElapsed(0)
    startRef.current = performance.now()
    setRunning(true)
    rafRef.current = requestAnimationFrame(tick)
  }, [tick])

  useEffect(() => {
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [])

  const t = elapsed / TOTAL_DURATION // normalized 0..1

  // Current phase
  let accumulated = 0
  let currentPhase = PHASES[0]
  let phaseProgress = 0
  for (const phase of PHASES) {
    if (elapsed <= accumulated + phase.duration) {
      currentPhase = phase
      phaseProgress = (elapsed - accumulated) / phase.duration
      break
    }
    accumulated += phase.duration
  }

  const isStorm = currentPhase.id === 'impact'

  return (
    <div style={{
      background: 'var(--bg-1)',
      border: `1px solid ${running ? 'rgba(167,139,250,0.3)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)',
      padding: '16px 18px',
      boxShadow: running ? '0 0 30px rgba(167,139,250,0.08)' : 'var(--card-shadow)',
      transition: 'all 0.5s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
            letterSpacing: 1.5, color: '#a78bfa',
          }}>SIMULATION ENGINE</span>
          {running && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
              color: isStorm ? '#ef4444' : '#a78bfa',
              background: isStorm ? 'rgba(239,68,68,0.1)' : 'rgba(167,139,250,0.1)',
              padding: '2px 8px', borderRadius: 4, letterSpacing: 1,
              animation: isStorm ? 'pulse 0.8s ease-in-out infinite' : 'none',
            }}>
              {currentPhase.label} — Sol {currentPhase.sol}
            </span>
          )}
          {done && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
              color: '#22c55e', background: 'rgba(34,211,153,0.1)',
              padding: '2px 8px', borderRadius: 4, letterSpacing: 1,
            }}>COMPLETE</span>
          )}
        </div>
        <button
          onClick={start}
          disabled={running}
          style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            letterSpacing: 1, padding: '5px 14px', borderRadius: 6,
            border: `1px solid ${running ? 'var(--border)' : 'rgba(167,139,250,0.4)'}`,
            background: running ? 'var(--bg-2)' : 'rgba(167,139,250,0.08)',
            color: running ? 'var(--fg-muted)' : '#a78bfa',
            cursor: running ? 'default' : 'pointer',
            transition: 'all 0.2s',
          }}
        >
          {running ? 'RUNNING...' : done ? 'RE-RUN' : 'RUN SIMULATION'}
        </button>
      </div>

      {/* Progress bar */}
      <div style={{ marginBottom: 16 }}>
        <div style={{
          height: 3, borderRadius: 2, background: 'var(--bg-3)', overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${t * 100}%`,
            background: isStorm
              ? 'linear-gradient(90deg, #a78bfa, #ef4444)'
              : done
                ? '#22c55e'
                : '#a78bfa',
            transition: running ? 'none' : 'all 0.3s',
          }} />
        </div>
        {/* Phase markers */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          {PHASES.map((p, i) => {
            const phaseStart = PHASES.slice(0, i).reduce((s, pp) => s + pp.duration, 0) / TOTAL_DURATION
            const active = t >= phaseStart
            return (
              <span key={p.id} style={{
                fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: 0.5,
                color: active ? (p.id === 'impact' && running ? '#ef4444' : 'var(--fg-secondary)') : 'var(--fg-muted)',
                fontWeight: active ? 700 : 400,
              }}>{p.label}</span>
            )
          })}
        </div>
      </div>

      {/* Three strategy panels side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
        {STRATEGIES.map((strat) => {
          const health = Math.round(strat.healthCurve(t))
          const water = Math.round(strat.waterCurve(t))
          const radiation = Math.max(0, Math.round(strat.radiationCurve(t)))
          const stressed = health < 70
          const dying = health < 45

          return (
            <div key={strat.name} style={{
              background: 'var(--bg-2)',
              border: `1px solid ${done && strat.loss <= 5 ? 'rgba(34,211,153,0.4)' : 'var(--border)'}`,
              borderRadius: 8,
              padding: '10px 12px',
              position: 'relative',
              overflow: 'hidden',
              transition: 'border-color 0.5s',
            }}>
              {/* Radiation overlay during storm */}
              {running && isStorm && (
                <div style={{
                  position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
                  background: `radial-gradient(ellipse at 50% 0%, rgba(239,68,68,${strat.loss > 15 ? 0.12 : strat.loss > 5 ? 0.06 : 0.02}) 0%, transparent 70%)`,
                  animation: 'pulse 1.5s ease-in-out infinite',
                }} />
              )}
              {/* Radiation particles */}
              {running && isStorm && (
                <RadiationParticles intensity={strat.loss > 15 ? 3 : strat.loss > 5 ? 2 : 1} />
              )}

              {/* Strategy label */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, position: 'relative', zIndex: 2 }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                  color: strat.color, letterSpacing: 0.5,
                }}>{strat.name}</span>
                {done && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
                    color: strat.color, letterSpacing: 0.5,
                    background: strat.color + '18',
                    padding: '1px 6px', borderRadius: 3,
                  }}>{strat.outcome}</span>
                )}
              </div>

              {/* Plant visualization with ghost afterimages */}
              <div style={{
                display: 'flex', justifyContent: 'center', alignItems: 'flex-end',
                height: 120, position: 'relative', zIndex: 2,
              }}>
                {/* Ghost afterimages — show range of possible outcomes */}
                {running && t > 0.1 && [
                  { healthOffset: -25, opacity: 0.08, scale: 0.97, dx: -3 },
                  { healthOffset: -15, opacity: 0.12, scale: 0.98, dx: -1 },
                  { healthOffset: +10, opacity: 0.10, scale: 1.01, dx: 2 },
                  { healthOffset: +5,  opacity: 0.08, scale: 1.02, dx: 4 },
                ].map((ghost, gi) => {
                  const ghostHealth = Math.max(10, Math.min(100, health + ghost.healthOffset * (strat.loss / 10)))
                  const ghostStressed = ghostHealth < 70
                  return (
                    <div key={gi} style={{
                      position: 'absolute',
                      bottom: 0,
                      left: '50%',
                      transform: `translateX(calc(-50% + ${ghost.dx}px)) scale(${ghost.scale})`,
                      opacity: ghost.opacity,
                      filter: ghostStressed ? 'saturate(0.3) brightness(0.7)' : 'saturate(0.5)',
                      pointerEvents: 'none',
                      transition: 'opacity 0.5s',
                    }}>
                      <PlantSVG
                        crop={SIM_CROP.name}
                        bbch={SIM_CROP.bbch}
                        health={ghostHealth}
                        stressed={ghostStressed}
                        width={90}
                        height={110}
                      />
                    </div>
                  )
                })}

                {/* Main plant — the "most likely" outcome */}
                <div style={{
                  position: 'relative',
                  filter: dying ? 'saturate(0.3) brightness(0.7)' : stressed ? 'saturate(0.6)' : 'none',
                  transition: 'filter 0.8s',
                }}>
                  <PlantSVG
                    crop={SIM_CROP.name}
                    bbch={SIM_CROP.bbch}
                    health={health}
                    stressed={stressed}
                    width={90}
                    height={110}
                  />
                </div>

                {/* Neural pathway overlay — AI learning visualization */}
                <NeuralPathways t={t} running={running} width={90} height={110} />

                {/* Shield effect for Strategy C */}
                {strat.loss <= 5 && running && t > 0.15 && (
                  <div style={{
                    position: 'absolute', inset: '10px 15px', borderRadius: '50%',
                    border: '1.5px solid rgba(34,211,153,0.25)',
                    boxShadow: '0 0 15px rgba(34,211,153,0.1)',
                    animation: 'pulse 3s ease-in-out infinite',
                    pointerEvents: 'none',
                  }} />
                )}
              </div>

              {/* Live metrics */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4,
                marginTop: 8, position: 'relative', zIndex: 2,
              }}>
                <MetricPill
                  label="HEALTH"
                  value={`${running || done ? health : '--'}%`}
                  color={health > 80 ? '#22c55e' : health > 50 ? '#f59e0b' : '#ef4444'}
                  active={running || done}
                />
                <MetricPill
                  label="H2O"
                  value={`${running || done ? water : '--'}L`}
                  color={water > 400 ? '#06b6d4' : water > 200 ? '#f59e0b' : '#ef4444'}
                  active={running || done}
                />
                <MetricPill
                  label="RAD"
                  value={`${running || done ? radiation : '--'}`}
                  color={radiation > 100 ? '#ef4444' : radiation > 20 ? '#f59e0b' : '#22c55e'}
                  active={running || done}
                  unit="uSv"
                />
              </div>

              {/* Final loss result */}
              {done && (
                <div style={{
                  marginTop: 8, textAlign: 'center',
                  fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700,
                  color: strat.color,
                  animation: 'fadeIn 0.6s ease both',
                }}>
                  {strat.loss}% LOSS
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Growth lifecycle scrubber */}
      <GrowthScrubber t={t} running={running} done={done} crop="Wheat" />

      {/* Parameter space exploration + Monte Carlo side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <ParameterHeatmap t={t} running={running} done={done} />
        <MonteCarloSwarm t={t} running={running} done={done} />
      </div>

      {/* Decision tree + Lab notebook side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <DecisionTree t={t} running={running} done={done} />
        <LabNotebook t={t} running={running} done={done} />
      </div>

      {/* Generational evolution */}
      <GenerationCounter t={t} running={running} done={done} />

      {/* Verdict */}
      {done && (
        <div style={{
          marginTop: 12, padding: '10px 14px',
          background: 'rgba(34,211,153,0.04)',
          border: '1px solid rgba(34,211,153,0.2)',
          borderRadius: 8,
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: '#22c55e', lineHeight: 1.6,
          animation: 'fadeIn 0.6s ease both',
        }}>
          ORACLE: Strategy C selected — pre-emptive protocol. 3% loss vs 40% baseline.
          Confidence 87% (Syngenta KB stress data). Promoting to production.
        </div>
      )}
    </div>
  )
}

function MetricPill({ label, value, color, active, unit }) {
  return (
    <div style={{
      textAlign: 'center', padding: '4px 0',
      background: active ? color + '08' : 'transparent',
      borderRadius: 4, transition: 'background 0.3s',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
        letterSpacing: 1, color: 'var(--fg-muted)', marginBottom: 2,
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
        color: active ? color : 'var(--fg-muted)',
        transition: 'color 0.3s',
      }}>
        {value}
      </div>
      {unit && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--fg-muted)' }}>{unit}</div>
      )}
    </div>
  )
}

// Animated radiation particles falling from top
function RadiationParticles({ intensity = 1 }) {
  const count = intensity * 4
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 1 }}>
      {Array.from({ length: count }, (_, i) => {
        const left = 10 + ((i * 23) % 80)
        const delay = (i * 0.3) % 2
        const duration = 1.2 + (i % 3) * 0.4
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${left}%`,
              top: -4,
              width: 2,
              height: 8 + (i % 3) * 4,
              borderRadius: 2,
              background: `rgba(239,68,68,${0.3 + intensity * 0.1})`,
              boxShadow: `0 0 4px rgba(239,68,68,${0.2 + intensity * 0.05})`,
              animation: `radFall ${duration}s linear ${delay}s infinite`,
            }}
          />
        )
      })}
      <style>{`
        @keyframes radFall {
          0% { transform: translateY(-10px); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 0.6; }
          100% { transform: translateY(200px); opacity: 0; }
        }
      `}</style>
    </div>
  )
}
