import Panel from './Panel'

const statusColors = { armed: 'var(--fg-muted)', triggered: '#f59e0b', monitoring: '#a78bfa' }

export default function FlightRules({ rules }) {
  const active = rules.length
  const triggered = rules.filter(r => r.status === 'triggered').length

  return (
    <Panel title="Flight Rules Engine" icon="📋" color="#06b6d4" badge={`${active} active · ${triggered} triggered`} defaultOpen={false}>
      <div style={{ fontSize: 10, color: 'var(--fg-muted)', marginBottom: 10 }}>
        Layer 0 — Deterministic, 0ms latency, cannot be overridden by AI
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {rules.map((fr, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 8px',
            background: fr.status === 'triggered' ? 'rgba(245,158,11,0.06)' : 'var(--bg-2)',
            borderRadius: 6,
            borderLeft: `2px solid ${statusColors[fr.status]}`,
            transition: 'background-color 0.3s',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, color: 'var(--fg-muted)', width: 50 }}>{fr.id}</span>
            <span style={{ fontSize: 11, color: 'var(--fg-secondary)', flex: 1 }}>{fr.rule}</span>
            <span style={{
              fontSize: 8, padding: '2px 6px', borderRadius: 4,
              fontFamily: 'var(--font-mono)', fontWeight: 700,
              background: `${statusColors[fr.status]}22`,
              color: statusColors[fr.status],
              textTransform: 'uppercase',
            }}>{fr.status}</span>
            {fr.count > 0 && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--fg-muted)' }}>x{fr.count}</span>
            )}
          </div>
        ))}
      </div>
    </Panel>
  )
}
