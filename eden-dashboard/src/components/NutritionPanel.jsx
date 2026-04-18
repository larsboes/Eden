import Panel from './Panel'
import MicroBar from './MicroBar'

export default function NutritionPanel({ crew }) {
  return (
    <Panel title="Crew Nutrition — 4 Astronauts x 450 Sols" icon="👨‍🚀" color="#60a5fa">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
        {crew.map((c, i) => (
          <div key={i} style={{
            padding: 10,
            background: 'var(--bg-2)',
            borderRadius: 8,
            border: '1px solid var(--border)',
            transition: 'background-color 0.3s, border-color 0.3s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <span style={{ fontSize: 20 }}>{c.emoji}</span>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--fg)' }}>{c.name}</div>
                <div style={{ fontSize: 9, color: 'var(--fg-muted)' }}>{c.role}</div>
              </div>
            </div>

            {/* Kcal */}
            <div style={{ marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 8, color: 'var(--fg-muted)' }}>KCAL</span>
                <span style={{
                  fontSize: 10, fontFamily: 'var(--font-mono)',
                  color: c.kcalActual / c.kcalTarget > 0.9 ? '#34d399' : '#f59e0b',
                }}>{c.kcalActual}/{c.kcalTarget}</span>
              </div>
              <MicroBar value={c.kcalActual} max={c.kcalTarget} color="#60a5fa" height={4} />
            </div>

            {/* Nutrients */}
            {[
              { l: 'Protein', v: c.protein },
              { l: 'Iron', v: c.iron },
              { l: 'Vit C', v: c.vitC },
              { l: 'Calcium', v: c.calcium },
            ].map((n, j) => (
              <div key={j} style={{ marginBottom: 3 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 8, color: 'var(--fg-muted)' }}>{n.l}</span>
                  <span style={{
                    fontSize: 9, fontFamily: 'var(--font-mono)',
                    color: n.v > 85 ? '#94a3b8' : n.v > 70 ? '#f59e0b' : '#ef4444',
                  }}>{n.v}%</span>
                </div>
                <MicroBar value={n.v} color={n.v > 85 ? '#34d399' : n.v > 70 ? '#f59e0b' : '#ef4444'} height={3} />
              </div>
            ))}

            {/* Preference */}
            <div style={{ fontSize: 9, color: 'var(--fg-muted)', marginTop: 6, fontStyle: 'italic' }}>
              {c.preference}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}
