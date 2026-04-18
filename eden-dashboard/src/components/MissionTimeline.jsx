export default function MissionTimeline({ sol }) {
  const pct = (sol / 450) * 100
  const markers = [
    { sol: 1, label: 'LANDING', color: '#34d399' },
    { sol: 45, label: 'FIRST HARVEST', color: '#60a5fa' },
    { sol: 150, label: 'FULL CAPACITY', color: '#a78bfa' },
    { sol, label: `NOW (${sol})`, color: '#e8913a' },
    { sol: 350, label: 'WIND DOWN', color: '#f59e0b' },
    { sol: 450, label: 'DEPARTURE', color: '#ef4444' },
  ]

  return (
    <div className="eden-card" style={{ padding: '10px 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#e8913a' }}>
          MISSION TIMELINE — 450 SOL SURFACE STAY
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)' }}>
          {pct.toFixed(1)}% complete · {450 - sol} sols remaining
        </span>
      </div>

      <div style={{ position: 'relative', height: 20, background: 'var(--bg-3)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, height: '100%',
          width: `${pct}%`,
          background: 'linear-gradient(90deg, #34d399, #e8913a)',
          borderRadius: 4,
          transition: 'width 1s',
          boxShadow: '0 0 10px rgba(232,145,58,0.3)',
        }} />
        {markers.map((m, i) => (
          <div key={i} style={{
            position: 'absolute',
            left: `${(m.sol / 450) * 100}%`,
            top: 0, height: '100%',
            transform: 'translateX(-50%)',
          }}>
            <div style={{ width: 1, height: '100%', background: m.color, opacity: 0.6 }} />
            <div style={{
              position: 'absolute', top: -2,
              fontSize: 7, color: m.color,
              whiteSpace: 'nowrap',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              transform: 'translateY(-100%)',
            }}>{m.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 8, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>SOL 0</span>
        <span style={{ fontSize: 8, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>SOL 450</span>
      </div>
    </div>
  )
}
