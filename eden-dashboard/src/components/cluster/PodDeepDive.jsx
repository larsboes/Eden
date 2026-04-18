import PlantSVG from '../PlantSVG'
import MicroBar from '../MicroBar'

const livenessColors = {
  passing: '#34d399',
  degraded: '#f59e0b',
  terminated: '#ef4444',
}

const readinessColors = {
  ready: '#34d399',
  approaching: '#f59e0b',
  notReady: 'var(--fg-muted)',
  terminated: '#6b7280',
}

const quotaConfig = [
  { key: 'water', label: 'Water', unit: 'L/sol', color: '#06b6d4' },
  { key: 'light', label: 'Light', unit: '%', color: '#fbbf24' },
  { key: 'nutrients', label: 'Nutrients', unit: 'mS/cm', color: '#34d399' },
  { key: 'space', label: 'Space', unit: 'm\u00B2', color: '#a78bfa' },
]

function generatePodEvents(crop, zone, probe) {
  const probeData = probe || {}
  const isTerminated = probeData.liveness === 'terminated'
  const isDegraded = probeData.liveness === 'degraded'

  if (isTerminated) {
    return [
      { age: '0s', type: 'Normal', reason: 'PreHarvest', message: `${crop.name} pre-harvested. Yield secured in cold storage.` },
      { age: '30s', type: 'Warning', reason: 'Terminated', message: `Pod terminated. Liveness probe failed. Stress protocol.` },
      { age: '2m', type: 'Normal', reason: 'ScheduledHarvest', message: `Emergency harvest triggered by CME flight rule.` },
      { age: '5m', type: 'Normal', reason: 'Planted', message: `${crop.name} planted Sol ${probeData.startedSol || 'N/A'}. Cycle active.` },
    ]
  }

  if (isDegraded) {
    return [
      { age: '5s', type: 'Warning', reason: 'StressDetected', message: `${crop.name} under radiation stress. Health: ${crop.health}%.` },
      { age: '10s', type: 'Normal', reason: 'StressHarden', message: `EC adjusted +0.4 mS/cm per Syngenta KB recommendation.` },
      { age: '1m', type: 'Normal', reason: 'LivenessProbe', message: `Degraded. Sensors reporting elevated stress markers.` },
      { age: '5m', type: 'Normal', reason: 'BBCHAdvance', message: `BBCH ${crop.bbch - 1} -> ${crop.bbch}. ${crop.bbchLabel.split(' \u2014 ')[0]}.` },
    ]
  }

  return [
    { age: '30s', type: 'Normal', reason: 'LivenessProbe', message: `Sensors nominal. Health ${crop.health}%.` },
    { age: '1h', type: 'Normal', reason: 'BBCHAdvance', message: `BBCH ${crop.bbch - 1} -> ${crop.bbch}. ${crop.bbchLabel.split(' \u2014 ')[0]}.` },
    { age: '3d', type: 'Normal', reason: 'Watering', message: `${zone.waterUsage}L delivered. EC: ${zone.ec} mS/cm.` },
    { age: '5d', type: 'Normal', reason: 'Scheduled', message: crop.companion ? `Adjacent to ${crop.companion.split('(')[0].trim()} (sidecar).` : `Standard growth protocol active.` },
  ]
}

export default function PodDeepDive({ crop, zone, probe, profile, quota, dashboardState, onBack }) {
  if (!crop || !zone) return null

  const isCrisis = dashboardState === 'crisis'
  const mono = { fontFamily: 'var(--font-mono)' }
  const probeData = probe || { liveness: 'passing', livenessAge: '30s', readiness: 'notReady', readinessDetail: '', restarts: 0, startedSol: 0 }
  const livenessColor = livenessColors[probeData.liveness] || '#34d399'
  const readinessColor = readinessColors[probeData.readiness] || 'var(--fg-muted)'
  const healthColor = crop.health > 80 ? '#34d399' : crop.health > 50 ? '#f59e0b' : '#ef4444'
  const isTerminated = probeData.liveness === 'terminated'
  const isDegraded = probeData.liveness === 'degraded'
  const cropProfile = profile || null

  const labelStyle = {
    ...mono,
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: 1,
    color: 'var(--fg-muted)',
    textTransform: 'uppercase',
  }

  const valueStyle = {
    ...mono,
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--fg-secondary)',
  }

  const cardStyle = {
    background: 'var(--bg-1)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--card-shadow)',
    padding: '14px 16px',
  }

  const cardTitleStyle = {
    ...mono,
    fontSize: 10,
    fontWeight: 700,
    color: 'var(--fg-muted)',
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: 12,
  }

  const events = generatePodEvents(crop, zone, probeData)

  const configMapEntries = [
    { label: 'pH', value: zone.ph, color: '#34d399' },
    { label: 'EC', value: `${zone.ec} mS/cm`, color: '#f59e0b' },
    { label: 'Temp', value: `${zone.temp}\u00B0C`, color: '#ef4444' },
    { label: 'Humidity', value: `${zone.humidity}%`, color: '#06b6d4' },
    { label: 'VPD', value: `${zone.vpd} kPa`, color: '#a78bfa' },
    { label: 'DLI', value: `${zone.dli} mol/m\u00B2/d`, color: '#e8913a' },
    { label: 'Light', value: `${zone.light}%`, color: '#fbbf24' },
    { label: 'CO2', value: `${zone.co2} ppm`, color: '#60a5fa' },
  ]

  return (
    <div className="fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
    }}>
      {/* TOP: Back button + pod header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <button
          onClick={onBack}
          style={{
            ...mono,
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--fg-secondary)',
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 14px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-3)'
            e.currentTarget.style.borderColor = 'var(--border-hover)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--bg-2)'
            e.currentTarget.style.borderColor = 'var(--border)'
          }}
        >
          <span style={{ fontSize: 14 }}>&larr;</span>
          Back
        </button>

        <div style={{ flex: 1 }}>
          <div style={{
            ...mono,
            fontSize: 14,
            fontWeight: 700,
            color: 'var(--fg)',
            letterSpacing: 0.5,
          }}>
            Pod: {crop.name}
          </div>
          <div style={{
            ...mono,
            fontSize: 10,
            color: 'var(--fg-muted)',
          }}>
            Node:{zone.name} &mdash; Zone {zone.id}
          </div>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{
            ...mono,
            fontSize: 20,
            fontWeight: 700,
            color: healthColor,
          }}>
            {crop.health}%
          </span>
          <span style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: livenessColor,
            boxShadow: `0 0 10px ${livenessColor}`,
            display: 'inline-block',
            animation: probeData.liveness === 'passing' ? 'pulse 3s ease-in-out infinite' : 'none',
          }} />
        </div>
      </div>

      {/* PLANT: Very large PlantSVG centered in dome container */}
      <div style={{
        background: 'var(--bg-2)',
        borderRadius: '80px 80px 16px 16px',
        border: '1px solid var(--border)',
        boxShadow: 'var(--card-shadow)',
        overflow: 'hidden',
        position: 'relative',
        transition: 'all 0.5s ease',
      }}>
        {/* Glass dome arc highlight */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '15%',
          right: '15%',
          height: 2,
          borderRadius: '0 0 50% 50%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent)',
          zIndex: 2,
        }} />

        {/* Glass dome reflection */}
        <div style={{
          position: 'absolute',
          top: 12,
          left: '22%',
          right: '62%',
          height: 50,
          borderRadius: '50%',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.04), transparent)',
          transform: 'rotate(-15deg)',
          zIndex: 1,
        }} />

        {/* Plant centered */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '32px 32px 0',
          minHeight: 300,
          justifyContent: 'flex-end',
          position: 'relative',
          zIndex: 2,
        }}>
          {/* BBCH badge floating */}
          <div style={{
            position: 'absolute',
            top: 24,
            right: 32,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: 4,
          }}>
            <div style={{
              ...mono,
              fontSize: 24,
              fontWeight: 700,
              color: '#e8913a',
              lineHeight: 1,
            }}>
              BBCH {crop.bbch}
            </div>
            <div style={{
              ...mono,
              fontSize: 10,
              color: 'var(--fg-secondary)',
              textAlign: 'right',
              maxWidth: 180,
              lineHeight: 1.3,
            }}>
              {crop.bbchLabel}
            </div>
          </div>

          {/* Health badge floating */}
          <div style={{
            position: 'absolute',
            top: 24,
            left: 32,
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}>
            <div style={{
              ...mono,
              fontSize: 28,
              fontWeight: 700,
              color: healthColor,
              lineHeight: 1,
            }}>
              {crop.health}%
            </div>
            <div style={{
              ...mono,
              fontSize: 9,
              color: 'var(--fg-muted)',
              letterSpacing: 1,
              textTransform: 'uppercase',
            }}>
              Health
            </div>
          </div>

          <div style={{
            opacity: isTerminated ? 0.35 : 1,
            filter: isDegraded ? 'saturate(0.6)' : 'none',
            transition: 'all 0.5s ease',
          }}>
            <PlantSVG
              crop={crop.name}
              bbch={crop.bbch}
              health={crop.health}
              stressed={isCrisis && (isDegraded || isTerminated)}
              width={200}
              height={260}
            />
          </div>
        </div>

        {/* Mars soil gradient bar */}
        <div style={{
          height: 32,
          background: 'linear-gradient(180deg, rgba(146, 64, 14, 0.15) 0%, rgba(120, 53, 15, 0.35) 40%, rgba(120, 53, 15, 0.5) 100%)',
          borderTop: '1px solid rgba(146, 64, 14, 0.2)',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(circle, rgba(161, 98, 7, 0.2) 1px, transparent 1px)',
            backgroundSize: '12px 8px',
            opacity: 0.5,
          }} />
        </div>
      </div>

      {/* Two-column cards: ConfigMap + Probes */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
      }}>
        {/* ConfigMap card */}
        <div style={cardStyle}>
          <div style={cardTitleStyle}>ConfigMap</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
          }}>
            {configMapEntries.map((entry) => (
              <div key={entry.label} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                padding: '4px 8px',
                background: 'var(--bg-2)',
                borderRadius: 'var(--radius-sm)',
              }}>
                <span style={{
                  ...mono,
                  fontSize: 9,
                  fontWeight: 600,
                  color: 'var(--fg-muted)',
                  letterSpacing: 0.5,
                }}>
                  {entry.label}
                </span>
                <span style={{
                  ...mono,
                  fontSize: 10,
                  fontWeight: 700,
                  color: entry.color,
                }}>
                  {entry.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Probes card */}
        <div style={cardStyle}>
          <div style={cardTitleStyle}>Probes</div>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}>
            {/* Liveness */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: livenessColor,
                  boxShadow: `0 0 6px ${livenessColor}`,
                  display: 'inline-block',
                  animation: probeData.liveness === 'passing' ? 'pulse 3s ease-in-out infinite' : 'none',
                }} />
                <span style={labelStyle}>Liveness</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ ...mono, fontSize: 11, fontWeight: 600, color: livenessColor }}>
                  {probeData.liveness}
                </span>
                <span style={{ ...mono, fontSize: 9, color: 'var(--fg-muted)', marginLeft: 6 }}>
                  {probeData.livenessAge}
                </span>
              </div>
            </div>

            {/* Readiness */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: readinessColor,
                  display: 'inline-block',
                }} />
                <span style={labelStyle}>Readiness</span>
              </div>
              <div style={{
                ...mono,
                fontSize: 10,
                color: 'var(--fg-secondary)',
                textAlign: 'right',
                maxWidth: 160,
              }}>
                {probeData.readinessDetail}
              </div>
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: 'var(--border)' }} />

            {/* Started + Restarts row */}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <div style={labelStyle}>Started</div>
                <div style={valueStyle}>Sol {probeData.startedSol}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={labelStyle}>Restarts</div>
                <div style={{
                  ...mono,
                  fontSize: 12,
                  fontWeight: 600,
                  color: probeData.restarts > 0 ? '#f59e0b' : 'var(--fg-secondary)',
                }}>
                  {probeData.restarts}
                </div>
              </div>
            </div>

            {/* Sidecar / companion */}
            {crop.companion && (
              <div style={{
                padding: '6px 10px',
                background: 'var(--bg-2)',
                borderRadius: 'var(--radius-sm)',
                borderLeft: '2px solid #34d399',
              }}>
                <div style={labelStyle}>Sidecar (Companion)</div>
                <div style={{
                  ...mono,
                  fontSize: 10,
                  color: 'var(--fg-secondary)',
                  marginTop: 2,
                  lineHeight: 1.4,
                }}>
                  {crop.companion}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ResourceQuota card */}
      <div style={cardStyle}>
        <div style={cardTitleStyle}>ResourceQuota</div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 12,
        }}>
          {quotaConfig.map((q) => {
            const zoneQuota = quota || {}
            /* Try to get quota data from prop, then derive from zone */
            let data = zoneQuota[q.key] || null
            if (!data) {
              if (q.key === 'water') data = { used: zone.waterUsage, limit: 3.0 }
              else if (q.key === 'light') data = { used: zone.light, limit: 100 }
              else if (q.key === 'nutrients') data = { used: zone.ec, limit: 3.0 }
              else if (q.key === 'space') data = { used: zone.pods || 20, limit: 30 }
            }
            if (!data) return null
            const pct = Math.round((data.used / data.limit) * 100)
            return (
              <div key={q.key}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  marginBottom: 4,
                }}>
                  <span style={{ ...mono, fontSize: 10, fontWeight: 600, color: 'var(--fg-secondary)' }}>
                    {q.label}
                  </span>
                  <span style={{ ...mono, fontSize: 10, fontWeight: 600, color: q.color }}>
                    {data.used} / {data.limit} &middot; {pct}%
                  </span>
                </div>
                <MicroBar value={data.used} max={data.limit} color={q.color} height={6} warn={40} crit={20} />
              </div>
            )
          })}
        </div>
      </div>

      {/* Nutritional Output card */}
      {cropProfile && (
        <div style={cardStyle}>
          <div style={cardTitleStyle}>Nutritional Output</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 10,
          }}>
            {[
              { label: 'Calories', value: `${cropProfile.calPer100g} kcal/100g`, color: '#e8913a', icon: null },
              { label: 'Protein', value: `${cropProfile.proteinPer100g}g/100g`, color: '#a78bfa', icon: null },
              { label: 'Vitamin C', value: `${cropProfile.vitCPer100g}mg/100g`, color: '#f59e0b', icon: null },
              { label: 'Iron', value: `${cropProfile.ironPer100g}mg/100g`, color: '#ef4444', icon: null },
            ].map((n) => (
              <div
                key={n.label}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: 'var(--bg-2)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <span style={{
                  ...mono,
                  fontSize: 10,
                  fontWeight: 600,
                  color: 'var(--fg-secondary)',
                }}>
                  {n.label}
                </span>
                <span style={{
                  ...mono,
                  fontSize: 12,
                  fontWeight: 700,
                  color: n.color,
                }}>
                  {n.value}
                </span>
              </div>
            ))}

            {/* Additional crop profile details */}
            <div style={{
              gridColumn: '1 / -1',
              display: 'flex',
              gap: 12,
              paddingTop: 6,
              borderTop: '1px solid var(--border)',
            }}>
              <div>
                <span style={labelStyle}>Growth cycle </span>
                <span style={valueStyle}>{cropProfile.growthDays} days</span>
              </div>
              <div>
                <span style={labelStyle}>Cycles </span>
                <span style={valueStyle}>{cropProfile.cycles}</span>
              </div>
              <div>
                <span style={labelStyle}>Total yield </span>
                <span style={valueStyle}>{cropProfile.totalYield} kg</span>
              </div>
              <div>
                <span style={labelStyle}>Radiation </span>
                <span style={{
                  ...mono,
                  fontSize: 12,
                  fontWeight: 600,
                  color: cropProfile.radiationTolerance === 'high' ? '#34d399'
                    : cropProfile.radiationTolerance === 'moderate' ? '#f59e0b' : '#ef4444',
                }}>
                  {cropProfile.radiationTolerance}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Events card */}
      <div style={cardStyle}>
        <div style={cardTitleStyle}>Events</div>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 0,
        }}>
          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '48px 60px auto',
            gap: 8,
            padding: '4px 8px',
            borderBottom: '1px solid var(--border)',
            marginBottom: 2,
          }}>
            <span style={{ ...mono, fontSize: 8, fontWeight: 700, color: 'var(--fg-muted)', letterSpacing: 1 }}>AGE</span>
            <span style={{ ...mono, fontSize: 8, fontWeight: 700, color: 'var(--fg-muted)', letterSpacing: 1 }}>REASON</span>
            <span style={{ ...mono, fontSize: 8, fontWeight: 700, color: 'var(--fg-muted)', letterSpacing: 1 }}>MESSAGE</span>
          </div>

          {events.map((evt, i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '48px 60px auto',
                gap: 8,
                padding: '5px 8px',
                borderRadius: 'var(--radius-sm)',
                background: i % 2 === 0 ? 'transparent' : 'var(--bg-2)',
                transition: 'background 0.2s',
              }}
            >
              <span style={{
                ...mono,
                fontSize: 10,
                color: 'var(--fg-muted)',
              }}>
                {evt.age}
              </span>
              <span style={{
                ...mono,
                fontSize: 10,
                fontWeight: 600,
                color: evt.type === 'Warning' ? '#f59e0b' : 'var(--fg-secondary)',
              }}>
                {evt.reason}
              </span>
              <span style={{
                ...mono,
                fontSize: 10,
                color: 'var(--fg-secondary)',
                lineHeight: 1.3,
              }}>
                {evt.message}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
