import Panel from './Panel'

export default function MemoryWall({ milestones, currentSol }) {
  return (
    <Panel title="Memory Wall" icon="📜" color="#fbbf24" defaultOpen={false}>
      <div style={{ position: 'relative', paddingLeft: 16 }}>
        <div style={{
          position: 'absolute', left: 5, top: 0, bottom: 0, width: 1,
          background: 'linear-gradient(to bottom, var(--border), #fbbf24, var(--border))',
        }} />
        {milestones.map((m, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '6px 0',
            opacity: m.sol <= currentSol ? 1 : 0.3,
          }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: m.sol === currentSol ? '#fbbf24' : m.sol < currentSol ? 'var(--fg-muted)' : 'var(--bg-3)',
              border: m.sol === currentSol ? '2px solid #fbbf24' : 'none',
              boxShadow: m.sol === currentSol ? '0 0 8px #fbbf24' : 'none',
              flexShrink: 0,
              marginLeft: -8,
            }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#fbbf24', width: 50 }}>Sol {m.sol}</span>
            <span style={{ fontSize: 11, color: m.sol === currentSol ? 'var(--fg)' : 'var(--fg-secondary)' }}>{m.event}</span>
          </div>
        ))}
      </div>
    </Panel>
  )
}
