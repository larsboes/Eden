import ClusterPodCard from './PodCard'

const triageColorMap = {
  GREEN:      '#34d399',
  YELLOW:     '#f59e0b',
  RED:        '#ef4444',
  BLACK:      '#6b7280',
  amber:      '#e8913a',
  recovering: '#60a5fa',
}

const nodeLabels = {
  A: 'Node:A',
  B: 'Node:B',
  C: 'Node:C',
  D: 'Node:D',
}

export default function NodeBox({ zone, triage, probes, quota, dashboardState, onNodeClick, onPodClick }) {
  if (!zone) return null

  const triageColor = triage ? triageColorMap[triage] || null : null
  const borderColor = triageColor || 'var(--border)'
  const isIsolated = triage === 'RED'
  const isPDBViolated = triage === 'YELLOW'
  const isCrisis = dashboardState === 'crisis'

  const healthColor = zone.health > 85 ? '#34d399' : zone.health > 60 ? '#f59e0b' : '#ef4444'

  const boxStyle = {
    background: 'var(--bg-1)',
    border: `1px solid ${triageColor ? triageColor + '44' : 'var(--border)'}`,
    borderLeft: triageColor ? `3px solid ${triageColor}` : '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: triageColor
      ? `var(--card-shadow), 0 0 12px ${triageColor}15`
      : 'var(--card-shadow)',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    transition: 'all 0.5s ease',
    cursor: 'pointer',
    animation: isCrisis && triage === 'RED' ? 'pulse-border 2s ease-in-out infinite' : 'none',
  }

  const monoStyle = {
    fontFamily: 'var(--font-mono)',
  }

  const labelStyle = {
    ...monoStyle,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 1,
    color: 'var(--fg-muted)',
    textTransform: 'uppercase',
  }

  const zoneQuota = quota || {}

  return (
    <div
      style={boxStyle}
      onClick={() => onNodeClick && onNodeClick(zone)}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.02)'
        e.currentTarget.style.background = 'var(--bg-2)'
        e.currentTarget.style.boxShadow = 'var(--card-shadow-hover)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)'
        e.currentTarget.style.background = 'var(--bg-1)'
        e.currentTarget.style.boxShadow = triageColor
          ? `var(--card-shadow), 0 0 12px ${triageColor}15`
          : 'var(--card-shadow)'
      }}
    >
      {/* Header row: icon + name + node label + health */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>{zone.icon}</span>
          <div>
            <div style={{
              ...monoStyle,
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--fg)',
              letterSpacing: 0.5,
            }}>
              {zone.name}
            </div>
            <div style={{
              ...monoStyle,
              fontSize: 10,
              color: 'var(--fg-muted)',
              letterSpacing: 0.5,
            }}>
              {nodeLabels[zone.id] || `Node:${zone.id}`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            ...monoStyle,
            fontSize: 18,
            fontWeight: 700,
            color: healthColor,
          }}>
            {zone.health}%
          </span>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: triageColor || healthColor,
            boxShadow: `0 0 8px ${triageColor || healthColor}`,
            display: 'inline-block',
          }} />
        </div>
      </div>

      {/* Triage badges */}
      {isIsolated && (
        <div style={{
          ...monoStyle,
          fontSize: 9,
          fontWeight: 700,
          color: '#ef4444',
          background: 'rgba(239,68,68,0.08)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 8px',
          textAlign: 'center',
          letterSpacing: 0.5,
        }}>
          NetworkPolicy: ZONE ISOLATED
        </div>
      )}

      {isPDBViolated && (
        <div style={{
          ...monoStyle,
          fontSize: 9,
          fontWeight: 700,
          color: '#f59e0b',
          background: 'rgba(245,158,11,0.08)',
          border: '1px solid rgba(245,158,11,0.2)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 8px',
          textAlign: 'center',
          letterSpacing: 0.5,
        }}>
          PDB VIOLATED: 50% unavailable
        </div>
      )}

      {/* Pod cards row */}
      <div style={{
        display: 'flex',
        gap: 8,
        justifyContent: 'center',
      }}>
        {zone.cropDetails.map((crop) => {
          const cropProbe = probes ? probes[crop.name] : null
          return (
            <ClusterPodCard
              key={crop.name}
              crop={crop}
              probe={cropProbe}
              dashboardState={dashboardState}
              onClick={onPodClick}
            />
          )
        })}
      </div>

      {/* Bottom stats: water + VPD */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 6,
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div>
            <span style={labelStyle}>Water </span>
            <span style={{ ...monoStyle, fontSize: 12, fontWeight: 600, color: '#06b6d4' }}>
              {zone.waterUsage} L/sol
            </span>
            {zoneQuota.water && (
              <span style={{ ...monoStyle, fontSize: 10, color: 'var(--fg-muted)' }}>
                {' '}/ {zoneQuota.water.limit}
              </span>
            )}
          </div>
        </div>
        <div>
          <span style={labelStyle}>VPD </span>
          <span style={{
            ...monoStyle,
            fontSize: 12,
            fontWeight: 600,
            color: zone.vpd < 0.8 || zone.vpd > 1.3 ? '#f59e0b' : 'var(--fg-secondary)',
          }}>
            {zone.vpd} kPa
          </span>
        </div>
      </div>
    </div>
  )
}
