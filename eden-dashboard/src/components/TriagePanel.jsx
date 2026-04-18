import Panel from './Panel'
import MicroBar from './MicroBar'

const tagColors = { stable: '#34d399', 'at-risk': '#f59e0b', declining: '#ef4444' }

export default function TriagePanel({ triage, visible }) {
  if (!visible) return null

  return (
    <Panel title="Ethical Triage" icon="⚖️" color="#ef4444" badge="ACTIVE">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {triage.map((t, i) => (
          <div key={i} style={{
            padding: 10,
            background: 'var(--bg-2)',
            borderRadius: 6,
            borderLeft: `3px solid ${t.score > 0.7 ? '#34d399' : t.score > 0.4 ? '#f59e0b' : '#ef4444'}`,
            transition: 'background-color 0.3s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: '#e8913a' }}>Zone {t.zone}</span>
              <span style={{ fontSize: 11, color: 'var(--fg-secondary)' }}>{t.crop}</span>
              <span style={{
                marginLeft: 'auto',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                fontWeight: 700,
                color: t.score > 0.7 ? '#34d399' : t.score > 0.4 ? '#f59e0b' : '#ef4444',
              }}>{(t.score * 100).toFixed(0)}%</span>
              <span style={{ fontSize: 9, color: tagColors[t.trend] }}>
                {t.trend === 'declining' ? '▼' : t.trend === 'at-risk' ? '◆' : '─'} {t.trend}
              </span>
            </div>
            <MicroBar value={t.score * 100} color={t.score > 0.7 ? '#34d399' : t.score > 0.4 ? '#f59e0b' : '#ef4444'} height={4} />
            <div style={{ fontSize: 10, color: 'var(--fg-muted)', marginTop: 4 }}>
              Decision: <span style={{ color: 'var(--fg-secondary)' }}>{t.decision}</span>
            </div>
            {t.crewImpact && (
              <div style={{
                marginTop: 6,
                padding: 8,
                background: 'rgba(239,68,68,0.06)',
                border: '1px solid rgba(239,68,68,0.15)',
                borderRadius: 4,
                fontSize: 10,
                color: '#fca5a5',
                lineHeight: 1.5,
              }}>
                CREW IMPACT: {t.crewImpact}
              </div>
            )}
          </div>
        ))}
      </div>
    </Panel>
  )
}
