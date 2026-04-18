import PlantSVG from '../PlantSVG'

const livenessColors = {
  passing:    '#34d399',
  degraded:   '#f59e0b',
  terminated: '#ef4444',
}

const companionIcons = {
  Soybean:     null,
  Lentil:      null,
  Potato:      null,
  Wheat:       null,
  Tomato:      'Basil',
  Spinach:     null,
  Basil:       'Tomato',
  Microgreens: null,
}

export default function ClusterPodCard({ crop, probe, dashboardState, onClick }) {
  if (!crop) return null

  const isStressed = dashboardState === 'crisis'
  const probeData = probe || { liveness: 'passing', readiness: 'notReady', readinessDetail: '' }
  const isDegraded = probeData.liveness === 'degraded'
  const isTerminated = probeData.liveness === 'terminated'
  const livenessColor = livenessColors[probeData.liveness] || '#34d399'
  const companionName = companionIcons[crop.name]

  const healthColor = crop.health > 80 ? '#34d399' : crop.health > 50 ? '#f59e0b' : '#ef4444'

  const totalDays = crop.daysPlanted + crop.daysToHarvest
  const harvestProgress = totalDays > 0 ? Math.round((crop.daysPlanted / totalDays) * 100) : 0

  const cardStyle = {
    width: 170,
    background: 'var(--bg-1)',
    border: `1px solid ${isTerminated ? 'rgba(239,68,68,0.3)' : isDegraded ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--card-shadow)',
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
    cursor: onClick ? 'pointer' : 'default',
    transition: 'all 0.3s ease',
    opacity: isTerminated ? 0.5 : 1,
    filter: isDegraded ? 'saturate(0.7)' : 'none',
    position: 'relative',
  }

  const monoStyle = {
    fontFamily: 'var(--font-mono)',
  }

  return (
    <div
      style={cardStyle}
      onClick={() => onClick && onClick(crop)}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = 'var(--card-shadow-hover)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'var(--card-shadow)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      {/* Mini PlantSVG */}
      <div style={{
        background: 'var(--bg-2)',
        borderRadius: 'var(--radius-sm)',
        padding: '4px 2px 0',
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        position: 'relative',
      }}>
        <PlantSVG
          crop={crop.name}
          bbch={crop.bbch}
          health={crop.health}
          stressed={isStressed && (isDegraded || isTerminated)}
          width={80}
          height={105}
        />

        {/* Liveness indicator dot */}
        <span style={{
          position: 'absolute',
          top: 6,
          right: 6,
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: livenessColor,
          boxShadow: `0 0 6px ${livenessColor}`,
          animation: probeData.liveness === 'passing' ? 'pulse 3s ease-in-out infinite' : 'none',
        }} />

        {/* Companion / sidecar label */}
        {companionName && (
          <span style={{
            position: 'absolute',
            bottom: 4,
            right: 4,
            fontSize: 8,
            ...monoStyle,
            fontWeight: 500,
            color: 'var(--fg-muted)',
            background: 'var(--bg-1)',
            borderRadius: 4,
            padding: '1px 5px',
            border: '1px solid var(--border)',
            lineHeight: 1.3,
            letterSpacing: 0.3,
          }} title={`Sidecar: ${companionName} (companion planting)`}>
            + {companionName}
          </span>
        )}
      </div>

      {/* Crop name */}
      <div style={{
        ...monoStyle,
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--fg)',
        textAlign: 'center',
        lineHeight: 1.2,
      }}>
        {crop.name}
      </div>

      {/* Health + BBCH row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '100%',
      }}>
        <span style={{
          ...monoStyle,
          fontSize: 13,
          fontWeight: 700,
          color: healthColor,
        }}>
          {crop.health}%
        </span>
        <span style={{
          ...monoStyle,
          fontSize: 10,
          fontWeight: 600,
          color: '#e8913a',
        }}>
          BBCH {crop.bbch}
        </span>
      </div>

      {/* Readiness / harvest info */}
      <div style={{ width: '100%' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 3,
        }}>
          <span style={{ ...monoStyle, fontSize: 9, color: 'var(--fg-muted)', letterSpacing: 0.5 }}>
            READINESS
          </span>
          <span style={{ ...monoStyle, fontSize: 9, color: 'var(--fg-muted)' }}>
            {isTerminated ? 'N/A' : `${crop.daysToHarvest}d`}
          </span>
        </div>
        <div style={{
          width: '100%',
          height: 3,
          background: 'var(--bg-3)',
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          <div style={{
            width: isTerminated ? '100%' : `${harvestProgress}%`,
            height: '100%',
            background: isTerminated ? '#6b7280' : probeData.readiness === 'ready' ? '#34d399' : probeData.readiness === 'approaching' ? '#f59e0b' : 'var(--fg-muted)',
            borderRadius: 2,
            transition: 'width 1s ease',
          }} />
        </div>
      </div>

      {/* Crisis: degraded/terminated label */}
      {isStressed && (isDegraded || isTerminated) && (
        <div style={{
          ...monoStyle,
          fontSize: 8,
          fontWeight: 700,
          color: isTerminated ? '#6b7280' : '#f59e0b',
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          textAlign: 'center',
          lineHeight: 1.3,
        }}>
          {isTerminated ? 'Pre-harvested' : 'Stressed'}
        </div>
      )}
    </div>
  )
}
