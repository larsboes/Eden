import PodCard from './PodCard'
import Panel from './Panel'
import SimulationRunner from './SimulationRunner'
import DigitalTwinOverlay from './lab/DigitalTwinOverlay'
import AmbientOptimizer from './lab/AmbientOptimizer'

const SIM_TRANSCRIPT = [
  { time: '14:24:00', agent: 'VIRTUAL LAB', color: '#a78bfa', msg: 'Scenario injected: CME-2026-0124 — 1,243 km/s, Mars ETA 50.7h. Running 3 response strategies...' },
  { time: '14:24:03', agent: 'KB QUERY', color: '#60a5fa', msg: '"Wheat radiation tolerance at flowering stage" → Syngenta MCP Plant Stress Guide' },
  { time: '14:24:05', agent: 'KB RESULT', color: '#60a5fa', msg: '"Zadoks 60-69: HIGH sensitivity. UV-B yield reduction 15-40%. Recommend shielding + modified nutrient EC."' },
  { time: '14:24:06', agent: 'SIM-A', color: '#ef4444', msg: 'Strategy A (Do Nothing): 40% crop loss. Wheat destroyed at flowering. Protein deficit by Sol 300. Recovery: 45 sols.' },
  { time: '14:24:07', agent: 'SIM-B', color: '#f59e0b', msg: 'Strategy B (Standard): 12% loss. Shields only. No pre-stockpiling. Water deficit at Sol+3. Recovery: 15 sols.' },
  { time: '14:24:08', agent: 'SIM-C', color: '#22c55e', msg: 'Strategy C (Pre-emptive): 3% loss. Stockpile 240L, pre-harvest spinach, stress-harden wheat EC+0.4. Recovery: 5 sols.' },
  { time: '14:24:09', agent: 'DECISION', color: '#22c55e', msg: 'Strategy C selected — best outcome. Confidence: 87% (Syngenta KB stress data). Initiating pre-storm protocol.' },
]

export default function LabView({ zones, strategies, dashboardState, log }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Lab header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 0',
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: 2, color: 'var(--amber)', marginBottom: 2 }}>
            VIRTUAL FARMING LAB
          </div>
          <div style={{ fontSize: 13, color: 'var(--fg-secondary)' }}>
            The staging environment — canary deployment for crops
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, letterSpacing: 1,
          padding: '4px 12px', borderRadius: 6,
          background: dashboardState === 'crisis' ? 'rgba(239,68,68,0.1)' : dashboardState === 'alert' ? 'rgba(232,145,58,0.1)' : 'rgba(52,211,153,0.1)',
          color: dashboardState === 'crisis' ? '#ef4444' : dashboardState === 'alert' ? '#e8913a' : '#22c55e',
          border: `1px solid ${dashboardState === 'crisis' ? 'rgba(239,68,68,0.2)' : dashboardState === 'alert' ? 'rgba(232,145,58,0.2)' : 'rgba(52,211,153,0.2)'}`,
        }}>
          {dashboardState === 'crisis' ? 'STORM ACTIVE' : dashboardState === 'alert' ? 'PRE-STORM' : dashboardState === 'recovery' ? 'RECOVERING' : 'PRODUCTION'}
        </div>
      </div>

      {/* Pod grid — 2x2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {zones.map(z => (
          <DigitalTwinOverlay key={z.id}>
            <PodCard zone={z} dashboardState={dashboardState} />
          </DigitalTwinOverlay>
        ))}
      </div>

      {/* Ambient AI optimization — always running */}
      <AmbientOptimizer />

      {/* Simulation Runner — visual centerpiece */}
      <SimulationRunner />

      {/* Strategy comparison + Simulation transcript */}
      <div className="eden-grid-2">
        {/* Strategies */}
        <Panel title="Strategy Comparison" icon="🧪" color="#a78bfa" badge="ORACLE">
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
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{s.name}</span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700,
                    color: s.loss <= 5 ? '#22c55e' : s.loss <= 15 ? '#f59e0b' : '#ef4444',
                  }}>{s.loss}% LOSS</span>
                </div>
                <div style={{ fontSize: 10, color: 'var(--fg-muted)', lineHeight: 1.5 }}>
                  {s.detail || `Recovery: ${s.recovery} sols · ${s.resourceCost}`}
                </div>
                {s.confidence && (
                  <div style={{ fontSize: 9, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
                    Confidence: {s.confidence}%
                  </div>
                )}
                {s.selected && (
                  <div style={{
                    marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                    letterSpacing: 1.5, color: '#22c55e', padding: '3px 8px',
                    background: 'rgba(52,211,153,0.1)', borderRadius: 4, display: 'inline-block',
                  }}>SELECTED — BEST OUTCOME</div>
                )}
              </div>
            ))}
          </div>
        </Panel>

        {/* Simulation transcript */}
        <Panel title="Simulation Transcript" icon="🔬" color="#60a5fa" badge="LAB LOG">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 320, overflowY: 'auto' }}>
            {SIM_TRANSCRIPT.map((e, i) => (
              <div key={i} style={{
                padding: '6px 8px',
                background: 'var(--bg-2)',
                borderRadius: 4,
                borderLeft: `2px solid ${e.color}`,
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                lineHeight: 1.6,
                transition: 'background-color 0.3s',
              }}>
                <span style={{ color: 'var(--fg-muted)' }}>[{e.time}]</span>{' '}
                <span style={{ color: e.color, fontWeight: 600 }}>{e.agent}:</span>{' '}
                <span style={{ color: 'var(--fg-secondary)' }}>{e.msg}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Live agent log from current state */}
      {log && log.length > 0 && (
        <Panel title="Live Agent Feed" icon="📡" color="#e8913a" badge={`${log.length} entries`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 250, overflowY: 'auto' }}>
            {log.map((e, i) => (
              <div key={i} style={{
                padding: '6px 10px',
                background: 'var(--bg-2)',
                borderRadius: 4,
                borderLeft: `3px solid ${e.color}`,
                transition: 'background-color 0.3s',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                  <span style={{ fontSize: 9, fontWeight: 700, color: e.color, fontFamily: 'var(--font-mono)', letterSpacing: 1 }}>{e.agent}</span>
                  <span style={{ fontSize: 9, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>{e.time}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--fg-secondary)', lineHeight: 1.5 }}>{e.msg}</div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  )
}
