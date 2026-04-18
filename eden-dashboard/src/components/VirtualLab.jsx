import Panel from './Panel'

export default function VirtualLab({ strategies, visible }) {
  if (!visible) return null

  return (
    <Panel title="Virtual Farming Lab" icon="🧪" color="#a78bfa" badge="SIMULATION ACTIVE">
      <div style={{ fontSize: 11, color: 'var(--fg-secondary)', marginBottom: 12 }}>
        SCENARIO: CME-2026-0315 — Testing 3 response strategies
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {strategies.map((s, i) => (
          <div key={i} style={{
            padding: 12,
            background: s.selected ? 'rgba(52,211,153,0.06)' : 'var(--bg-2)',
            border: `1px solid ${s.selected ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
            borderRadius: 8,
            opacity: s.selected ? 1 : 0.5,
            transition: 'all 0.3s',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--fg)' }}>{s.name}</span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                fontWeight: 700,
                color: s.loss <= 5 ? '#34d399' : s.loss <= 15 ? '#f59e0b' : '#ef4444',
              }}>{s.loss}% LOSS</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>
              Recovery: {s.recovery} sols · {s.resourceCost}
            </div>
            {s.selected && (
              <div style={{
                marginTop: 8,
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: 1.5,
                color: '#34d399',
                padding: '3px 8px',
                background: 'rgba(52,211,153,0.1)',
                borderRadius: 4,
                display: 'inline-block',
              }}>SELECTED — BEST OUTCOME</div>
            )}
          </div>
        ))}
      </div>
    </Panel>
  )
}
