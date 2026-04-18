import Panel from './Panel'

export default function AgentLog({ entries }) {
  return (
    <Panel title="Council Log" icon="🤖" color="#e8913a" badge={`${entries.length} entries`}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 400, overflowY: 'auto' }}>
        {entries.map((e, i) => (
          <div key={i} style={{
            padding: '8px 10px',
            background: 'var(--bg-2)',
            borderRadius: 6,
            borderLeft: `3px solid ${e.color}`,
            transition: 'background-color 0.3s',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                color: e.color,
                fontFamily: 'var(--font-mono)',
                letterSpacing: 1,
              }}>{e.agent}</span>
              <span style={{ fontSize: 9, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>{e.time}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--fg-secondary)', lineHeight: 1.5 }}>{e.msg}</div>
          </div>
        ))}
      </div>
    </Panel>
  )
}
