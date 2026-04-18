import MicroBar from '../MicroBar'

const statusConfig = {
  rejected:   { opacity: 0.35, accent: '#ef4444', badge: 'REJECTED',          badgeBg: 'rgba(239,68,68,0.08)',  badgeBorder: 'rgba(239,68,68,0.2)' },
  suboptimal: { opacity: 0.5,  accent: '#f59e0b', badge: 'SUBOPTIMAL',        badgeBg: 'rgba(245,158,11,0.08)', badgeBorder: 'rgba(245,158,11,0.2)' },
  promoted:   { opacity: 1.0,  accent: '#22c55e', badge: 'PROMOTED \u2192 PROD', badgeBg: 'rgba(34,211,153,0.08)',  badgeBorder: 'rgba(34,211,153,0.25)' },
}

export default function CanaryDeployment({ canary, visible }) {
  if (!visible || !canary) return null

  const monoStyle = { fontFamily: 'var(--font-mono)' }

  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid rgba(34,211,153,0.15)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--card-shadow)',
      padding: '16px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      transition: 'all 0.5s ease',
      animation: 'fadeIn 0.4s ease both',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{
          ...monoStyle,
          fontSize: 11,
          fontWeight: 700,
          color: '#22c55e',
          letterSpacing: 1.5,
        }}>
          CANARY DEPLOYMENT
        </span>
        <span style={{
          ...monoStyle,
          fontSize: 9,
          color: 'var(--fg-muted)',
          letterSpacing: 0.5,
        }}>
          Virtual Farming Lab
        </span>
      </div>

      {/* Strategy rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {canary.strategies.map((s) => {
          const cfg = statusConfig[s.status] || statusConfig.rejected
          const isPromoted = s.status === 'promoted'

          return (
            <div
              key={s.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
                padding: '8px 12px',
                background: 'var(--bg-2)',
                border: `1px solid ${isPromoted ? 'rgba(34,211,153,0.3)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-sm)',
                opacity: cfg.opacity,
                transition: 'all 0.5s ease',
              }}
            >
              {/* Strategy name + loss */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                <span style={{
                  ...monoStyle,
                  fontSize: 10,
                  fontWeight: 600,
                  color: 'var(--fg)',
                  letterSpacing: 0.3,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {s.name}
                </span>
                <span style={{
                  ...monoStyle,
                  fontSize: 10,
                  fontWeight: 700,
                  color: cfg.accent,
                  flexShrink: 0,
                }}>
                  {s.loss}% loss
                </span>
              </div>

              {/* Status badge */}
              <span style={{
                ...monoStyle,
                fontSize: 8,
                fontWeight: 700,
                color: cfg.accent,
                background: cfg.badgeBg,
                border: `1px solid ${cfg.badgeBorder}`,
                borderRadius: 'var(--radius-sm)',
                padding: '2px 8px',
                letterSpacing: 0.5,
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}>
                {cfg.badge}
              </span>
            </div>
          )
        })}
      </div>

      {/* Rollout bar */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}>
          <span style={{
            ...monoStyle,
            fontSize: 9,
            fontWeight: 600,
            letterSpacing: 1,
            color: 'var(--fg-muted)',
            textTransform: 'uppercase',
          }}>
            Rollout
          </span>
          <span style={{
            ...monoStyle,
            fontSize: 12,
            fontWeight: 700,
            color: '#22c55e',
          }}>
            {canary.rolloutPct}%
          </span>
        </div>
        <MicroBar value={canary.rolloutPct} max={100} color="#22c55e" height={5} />
      </div>

      {/* Confidence */}
      <div style={{
        ...monoStyle,
        fontSize: 10,
        color: 'var(--fg-muted)',
        letterSpacing: 0.3,
      }}>
        Confidence: <span style={{ color: 'var(--fg-secondary)', fontWeight: 600 }}>
          {canary.confidence}%
        </span> ({canary.source})
      </div>
    </div>
  )
}
