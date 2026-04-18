import Panel from './Panel'
import MicroBar from './MicroBar'

const resourceColors = {
  water: '#06b6d4',
  battery: '#34d399',
  solar: '#fbbf24',
  desal: '#e8913a',
}

export default function ResourcePanel({ resources, state }) {
  return (
    <Panel title="Water / Energy Chain" icon="⚡" color="#06b6d4" badge={state !== 'nominal' ? state.toUpperCase() : undefined} collapsible={true}>
      {/* Chain flow */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {[
          { label: 'Solar', emoji: '☀️', color: resourceColors.solar },
          { label: 'Power', emoji: '⚡', color: resourceColors.battery },
          { label: 'Desal', emoji: '💧', color: resourceColors.water },
          { label: 'Crops', emoji: '🌱', color: '#34d399' },
        ].map((n, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              padding: '4px 10px',
              background: 'var(--bg-2)',
              border: `1px solid ${n.color}44`,
              borderRadius: 6,
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              color: n.color,
              fontWeight: 600,
              transition: 'background-color 0.3s, border-color 0.3s',
            }}>
              {n.emoji} {n.label}
            </div>
            {i < 3 && <span style={{ color: 'var(--fg-muted)', fontSize: 12, animation: 'pulse 2s infinite' }}>→</span>}
          </div>
        ))}
      </div>

      {/* Resource bars */}
      {Object.entries(resources).map(([key, r]) => (
        <div key={key} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)', letterSpacing: 1 }}>{r.label}</span>
            <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)', color: resourceColors[key] }}>
              {r.current}{r.unit === '%' ? '%' : ` ${r.unit}`}
            </span>
          </div>
          <MicroBar value={r.current} max={r.max} color={resourceColors[key]} height={8} warn={30} crit={15} />
          <div style={{ fontSize: 9, color: 'var(--fg-muted)', marginTop: 2 }}>{r.rate}</div>
        </div>
      ))}

      {state !== 'nominal' && (
        <div style={{
          marginTop: 8,
          padding: 10,
          background: state === 'crisis' ? 'rgba(239,68,68,0.08)' : 'rgba(232,145,58,0.08)',
          border: `1px solid ${state === 'crisis' ? 'rgba(239,68,68,0.2)' : 'rgba(232,145,58,0.2)'}`,
          borderRadius: 6,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          color: state === 'crisis' ? '#ef4444' : '#e8913a',
          lineHeight: 1.6,
        }}>
          {state === 'alert' && 'PRE-STORM: Desalination at MAX. Water climbing. Battery charging to 100%.'}
          {state === 'crisis' && 'STORM: Solar at 30%. Desalination degraded. Consuming reserves. 3.5 sols autonomy remaining.'}
          {state === 'recovery' && 'CLEARING: Solar recovering. Desalination ramping up. Crisis averted.'}
        </div>
      )}
    </Panel>
  )
}
