import PlantSVG from '../PlantSVG'
import MicroBar from '../MicroBar'

const sensorConfig = [
  { key: 'temp', label: 'TEMP', unit: '\u00B0C', color: '#ef4444' },
  { key: 'humidity', label: 'HUMIDITY', unit: '%', color: '#06b6d4' },
  { key: 'vpd', label: 'VPD', unit: 'kPa', color: '#a78bfa' },
  { key: 'ec', label: 'EC', unit: 'mS/cm', color: '#f59e0b' },
  { key: 'ph', label: 'pH', unit: '', color: '#34d399' },
  { key: 'co2', label: 'CO2', unit: 'ppm', color: '#60a5fa' },
  { key: 'light', label: 'LIGHT', unit: '%', color: '#fbbf24' },
  { key: 'dli', label: 'DLI', unit: 'mol/m\u00B2/d', color: '#e8913a' },
]

const quotaConfig = [
  { key: 'water', label: 'Water', unit: 'L/sol', color: '#06b6d4' },
  { key: 'light', label: 'Light', unit: '%', color: '#fbbf24' },
  { key: 'nutrients', label: 'Nutrients', unit: 'mS/cm', color: '#34d399' },
  { key: 'space', label: 'Space', unit: 'm\u00B2', color: '#a78bfa' },
]

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

export default function ZoneDeepDive({ zone, probes, quota, dashboardState, onBack, onPodClick }) {
  if (!zone) return null

  const isCrisis = dashboardState === 'crisis'
  const mono = { fontFamily: 'var(--font-mono)' }
  const sans = { fontFamily: 'var(--font-sans)' }

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

  const zoneQuota = quota || {}

  return (
    <div className="fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
    }}>
      {/* TOP: Back button + zone header */}
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
          Back to Cluster
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          <span style={{ fontSize: 20 }}>{zone.icon}</span>
          <div>
            <div style={{
              ...mono,
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--fg)',
              letterSpacing: 0.5,
            }}>
              Node: {zone.name}
            </div>
            <div style={{
              ...mono,
              fontSize: 10,
              color: 'var(--fg-muted)',
            }}>
              Zone {zone.id} &mdash; {zoneQuota.space ? zoneQuota.space.limit : 30}m&sup2;
            </div>
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
            color: zone.health > 85 ? '#34d399' : zone.health > 60 ? '#f59e0b' : '#ef4444',
          }}>
            {zone.health}%
          </span>
          <span style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: zone.health > 85 ? '#34d399' : zone.health > 60 ? '#f59e0b' : '#ef4444',
            boxShadow: `0 0 10px ${zone.health > 85 ? '#34d399' : zone.health > 60 ? '#f59e0b' : '#ef4444'}`,
            display: 'inline-block',
            animation: isCrisis ? 'pulse 2s ease-in-out infinite' : 'none',
          }} />
        </div>
      </div>

      {/* DOME SECTION: Glass greenhouse with plants */}
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

        {/* Subtle dome glass reflection */}
        <div style={{
          position: 'absolute',
          top: 10,
          left: '20%',
          right: '60%',
          height: 40,
          borderRadius: '50%',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.04), transparent)',
          transform: 'rotate(-15deg)',
          zIndex: 1,
        }} />

        {/* Plants container */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-end',
          gap: 32,
          padding: '40px 32px 0',
          minHeight: 220,
          position: 'relative',
          zIndex: 2,
        }}>
          {zone.cropDetails.map((crop) => {
            const probe = probes ? probes[crop.name] : null
            const isTerminated = probe && probe.liveness === 'terminated'
            const isDegraded = probe && probe.liveness === 'degraded'
            return (
              <div
                key={crop.name}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                  opacity: isTerminated ? 0.4 : 1,
                  filter: isDegraded ? 'saturate(0.6)' : 'none',
                  transition: 'all 0.5s ease',
                }}
              >
                <PlantSVG
                  crop={crop.name}
                  bbch={crop.bbch}
                  health={crop.health}
                  stressed={isCrisis && (isDegraded || isTerminated)}
                  width={120}
                  height={160}
                />
                <div style={{
                  ...mono,
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--fg-secondary)',
                  textAlign: 'center',
                }}>
                  {crop.name}
                </div>
              </div>
            )
          })}
        </div>

        {/* Mars soil gradient bar */}
        <div style={{
          height: 28,
          background: 'linear-gradient(180deg, rgba(146, 64, 14, 0.15) 0%, rgba(120, 53, 15, 0.35) 40%, rgba(120, 53, 15, 0.5) 100%)',
          borderTop: '1px solid rgba(146, 64, 14, 0.2)',
          position: 'relative',
        }}>
          {/* Soil texture dots */}
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(circle, rgba(161, 98, 7, 0.2) 1px, transparent 1px)',
            backgroundSize: '12px 8px',
            opacity: 0.5,
          }} />
        </div>
      </div>

      {/* PODS SECTION: Two pod detail cards side by side */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: zone.cropDetails.length > 1 ? '1fr 1fr' : '1fr',
        gap: 12,
      }}>
        {zone.cropDetails.map((crop) => {
          const probe = probes ? probes[crop.name] : null
          const probeData = probe || { liveness: 'passing', livenessAge: '30s', readiness: 'notReady', readinessDetail: '', restarts: 0, startedSol: 0 }
          const livenessColor = livenessColors[probeData.liveness] || '#34d399'
          const readinessColor = readinessColors[probeData.readiness] || 'var(--fg-muted)'
          const healthColor = crop.health > 80 ? '#34d399' : crop.health > 50 ? '#f59e0b' : '#ef4444'
          const isTerminated = probeData.liveness === 'terminated'

          return (
            <div
              key={crop.name}
              onClick={() => onPodClick && onPodClick(crop)}
              style={{
                background: 'var(--bg-1)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--card-shadow)',
                padding: '16px',
                cursor: onPodClick ? 'pointer' : 'default',
                transition: 'all 0.3s ease',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                opacity: isTerminated ? 0.6 : 1,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = 'var(--card-shadow-hover)'
                e.currentTarget.style.borderColor = 'var(--border-hover)'
                e.currentTarget.style.transform = 'translateY(-2px)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'var(--card-shadow)'
                e.currentTarget.style.borderColor = 'var(--border)'
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              {/* Pod header: name + health */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{
                  ...mono,
                  fontSize: 13,
                  fontWeight: 700,
                  color: 'var(--fg)',
                }}>
                  Pod: {crop.name}
                </div>
                <span style={{
                  ...mono,
                  fontSize: 16,
                  fontWeight: 700,
                  color: healthColor,
                }}>
                  {crop.health}%
                </span>
              </div>

              {/* BBCH stage */}
              <div style={{
                padding: '6px 10px',
                background: 'var(--bg-2)',
                borderRadius: 'var(--radius-sm)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{
                    ...mono,
                    fontSize: 11,
                    fontWeight: 700,
                    color: '#e8913a',
                  }}>
                    BBCH {crop.bbch}
                  </span>
                  <span style={{
                    ...mono,
                    fontSize: 9,
                    color: 'var(--fg-secondary)',
                  }}>
                    {crop.bbchLabel.split(' \u2014 ')[0]}
                  </span>
                </div>
                <div style={{
                  ...mono,
                  fontSize: 9,
                  color: 'var(--fg-muted)',
                  marginTop: 2,
                }}>
                  {crop.bbchLabel.includes(' \u2014 ') ? crop.bbchLabel.split(' \u2014 ')[1] : crop.bbchLabel}
                </div>
              </div>

              {/* Probes row */}
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: livenessColor,
                    boxShadow: `0 0 6px ${livenessColor}`,
                    display: 'inline-block',
                    animation: probeData.liveness === 'passing' ? 'pulse 3s ease-in-out infinite' : 'none',
                  }} />
                  <span style={{ ...mono, fontSize: 9, color: livenessColor, fontWeight: 600 }}>
                    {probeData.liveness}
                  </span>
                  <span style={{ ...mono, fontSize: 8, color: 'var(--fg-muted)' }}>
                    {probeData.livenessAge}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: readinessColor,
                    display: 'inline-block',
                  }} />
                  <span style={{ ...mono, fontSize: 9, color: readinessColor, fontWeight: 600 }}>
                    {probeData.readiness}
                  </span>
                </div>
              </div>

              {/* Harvest countdown + companion */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                paddingTop: 6,
                borderTop: '1px solid var(--border)',
              }}>
                <div>
                  <div style={labelStyle}>Harvest</div>
                  <div style={{
                    ...mono,
                    fontSize: 11,
                    fontWeight: 600,
                    color: crop.daysToHarvest <= 10 ? '#34d399' : 'var(--fg-secondary)',
                  }}>
                    {isTerminated ? 'Pre-harvested' : `${crop.daysToHarvest} sols`}
                  </div>
                </div>
                {crop.companion && (
                  <div style={{ textAlign: 'right' }}>
                    <div style={labelStyle}>Sidecar</div>
                    <div style={{
                      ...mono,
                      fontSize: 9,
                      color: 'var(--fg-secondary)',
                      maxWidth: 140,
                      lineHeight: 1.3,
                    }}>
                      {crop.companion.split('(')[0].trim()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* SENSORS: 2x4 grid */}
      <div style={{
        background: 'var(--bg-1)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--card-shadow)',
        padding: '14px 16px',
      }}>
        <div style={{
          ...mono,
          fontSize: 10,
          fontWeight: 700,
          color: 'var(--fg-muted)',
          letterSpacing: 1,
          textTransform: 'uppercase',
          marginBottom: 10,
        }}>
          ConfigMap: Zone Sensors
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
        }}>
          {sensorConfig.map((s) => {
            const val = zone[s.key]
            if (val === undefined) return null
            return (
              <div
                key={s.key}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '8px 6px',
                  background: 'var(--bg-2)',
                  borderRadius: 'var(--radius-sm)',
                  transition: 'background-color 0.3s',
                }}
              >
                <span style={{
                  ...mono,
                  fontSize: 7,
                  fontWeight: 700,
                  letterSpacing: 1.2,
                  color: 'var(--fg-muted)',
                  textTransform: 'uppercase',
                  marginBottom: 4,
                }}>
                  {s.label}
                </span>
                <span style={{
                  ...mono,
                  fontSize: 14,
                  fontWeight: 700,
                  color: s.color,
                }}>
                  {val}
                </span>
                <span style={{
                  ...mono,
                  fontSize: 8,
                  color: 'var(--fg-muted)',
                  marginTop: 1,
                }}>
                  {s.unit}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* RESOURCE QUOTA: 4 MicroBar progress bars */}
      <div style={{
        background: 'var(--bg-1)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--card-shadow)',
        padding: '14px 16px',
      }}>
        <div style={{
          ...mono,
          fontSize: 10,
          fontWeight: 700,
          color: 'var(--fg-muted)',
          letterSpacing: 1,
          textTransform: 'uppercase',
          marginBottom: 10,
        }}>
          ResourceQuota
        </div>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          {quotaConfig.map((q) => {
            const data = zoneQuota[q.key]
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
                  <span style={{
                    ...mono,
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--fg-secondary)',
                  }}>
                    {q.label}
                  </span>
                  <span style={{
                    ...mono,
                    fontSize: 10,
                    fontWeight: 600,
                    color: q.color,
                  }}>
                    {data.used} / {data.limit} {q.unit} &middot; {pct}%
                  </span>
                </div>
                <MicroBar value={data.used} max={data.limit} color={q.color} height={6} warn={40} crit={20} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
