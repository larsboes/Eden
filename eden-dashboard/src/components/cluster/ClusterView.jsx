import { useState } from 'react'
import { ClusterBox, NodeBox, ConnectorLine, ResourceFlow, CanaryDeployment, ZoneDeepDive, PodDeepDive } from './index'
import MarsParticles, { ParticleToggle } from './MarsParticles'
import AlertBanner from '../AlertBanner'
import MissionTimeline from '../MissionTimeline'
import MicroBar from '../MicroBar'
import SimulationRunner from '../SimulationRunner'
import {
  ZONES, CREW, FLIGHT_RULES, MEMORY_WALL,
  COUNCIL_LOG, COUNCIL_LOG_NOMINAL,
  CLUSTER_STATUS, POD_PROBES, POD_PROBES_CRISIS,
  EVENTS_NOMINAL, EVENTS_CRISIS, EVENTS_RECOVERY,
  RESOURCE_QUOTAS, ZONE_TRIAGE, RESOURCE_FLOW,
  CANARY_DEPLOYMENT, CROP_PROFILES,
  AGENT_COLORS,
} from '../../data/mock'

const DEMO_LOGS = {
  nominal: COUNCIL_LOG_NOMINAL,
  cme: [
    { time: '14:24:09', agent: 'SENTINEL', msg: 'Sol 247. CME-2026-0124 detected. Speed: 1,243 km/s out of N15E10. Calculating Mars transit...', color: AGENT_COLORS.SENTINEL },
    { time: '14:24:10', agent: 'SENTINEL', msg: 'Mars ETA: 50.7 hours. Wheat in Node:Carb at BBCH 60 \u2014 HIGH radiation vulnerability.', color: AGENT_COLORS.SENTINEL },
  ],
  council: COUNCIL_LOG,
  stockpile: [
    { time: '14:24:19', agent: 'COUNCIL', msg: 'Strategy C adopted unanimously (5/5). Pre-emptive full protocol initiated.', color: AGENT_COLORS.COUNCIL },
    { time: '14:30:00', agent: 'AQUA', msg: 'Desalination at MAX. Water climbing: 340L \u2192 420L. Battery charging: 78% \u2192 89%.', color: AGENT_COLORS.AQUA },
  ],
  storm: [
    { time: 'Sol 249', agent: 'SENTINEL', msg: 'CME IMPACT. Radiation spike: 263 \u00B5Sv/hr. Solar output: 30%. Shields active.', color: AGENT_COLORS.SENTINEL },
    { time: 'Sol 249', agent: 'AQUA', msg: 'Desal at 30% power: 36 L/sol. Pre-stockpiled 580L \u2014 autonomy: 7.2 sols. We\u2019re good.', color: AGENT_COLORS.AQUA },
  ],
  recovery: [
    { time: 'Sol 254', agent: 'SENTINEL', msg: 'Radiation returning to baseline. Solar recovering: 30% \u2192 91%. Storm duration: 4.8 sols.', color: AGENT_COLORS.SENTINEL },
    { time: 'Sol 254', agent: 'ORACLE', msg: 'Post-event analysis. Predicted: 3%. Actual: 2.7%. Proposing FR-CME-012. Rules: 87 \u2192 89.', color: AGENT_COLORS.ORACLE },
  ],
}

const connectorStatus = {
  nominal: 'nominal',
  alert: 'warning',
  crisis: 'critical',
  recovery: 'recovering',
}

export default function ClusterView({ dashboardState, logKey, sol, zones: zonesProp, crew: crewProp, flightRules: flightRulesProp, log: logProp, resources: resourcesProp, liveEvents, agentTokens, sseConnected, mars, liveClusterStatus, liveResourceFlow, livePodProbes, nutrition, apiStatus }) {
  const [deepDive, setDeepDive] = useState(null)
  const [particles, setParticles] = useState(() => {
    try { return localStorage.getItem('eden-particles') !== 'false' } catch { return true }
  })
  const toggleParticles = () => {
    setParticles(p => { const next = !p; try { localStorage.setItem('eden-particles', next) } catch {} return next })
  }

  const state = dashboardState || 'nominal'

  // Use live API data when available, fall back to mock
  const zones = zonesProp || ZONES
  const crew = crewProp || CREW
  const flightRules = flightRulesProp || FLIGHT_RULES
  const log = logProp?.length ? logProp : (DEMO_LOGS[logKey] || DEMO_LOGS.nominal)

  // Live backend data with mock fallback
  const cluster = liveClusterStatus || CLUSTER_STATUS[state]
  const probes = livePodProbes || (state === 'crisis' ? POD_PROBES_CRISIS : POD_PROBES)
  const triage = ZONE_TRIAGE[state]
  const mockEvents = state === 'crisis' ? EVENTS_CRISIS : state === 'recovery' ? EVENTS_RECOVERY : EVENTS_NOMINAL
  const events = liveEvents || mockEvents
  const flow = liveResourceFlow || RESOURCE_FLOW[state === 'crisis' ? 'crisis' : 'nominal']
  const isAlert = state === 'alert' || state === 'crisis'

  // Deep dive: zone
  if (deepDive?.type === 'zone') {
    const zone = zones.find(z => z.id === deepDive.zoneId)
    if (zone) {
      return (
        <div className={`cluster-view cluster-view--${state}`}>
          <ZoneDeepDive
            zone={zone}
            probes={probes}
            quota={RESOURCE_QUOTAS[zone.id]}
            dashboardState={state}
            onBack={() => setDeepDive(null)}
            onPodClick={(crop) => setDeepDive({ type: 'pod', zoneId: zone.id, cropName: crop.name })}
          />
          <div className={`mars-terrain mars-terrain--${state}`} />
        </div>
      )
    }
  }

  // Deep dive: pod
  if (deepDive?.type === 'pod') {
    const zone = zones.find(z => z.id === deepDive.zoneId)
    const crop = zone?.cropDetails?.find(c => c.name === deepDive.cropName)
    const profile = CROP_PROFILES.find(p => p.name === deepDive.cropName)
    if (zone && crop) {
      return (
        <div className={`cluster-view cluster-view--${state}`}>
          <PodDeepDive
            crop={crop}
            zone={zone}
            probe={probes[crop.name]}
            profile={profile}
            dashboardState={state}
            onBack={() => setDeepDive({ type: 'zone', zoneId: zone.id })}
          />
          <div className={`mars-terrain mars-terrain--${state}`} />
        </div>
      )
    }
  }

  // Main cluster tree view
  return (
    <div className={`cluster-view cluster-view--${state}`}>
      {isAlert && <AlertBanner visible etaHours={50.7} />}

      {/* Agent stream — live SSE tokens or static log */}
      {sseConnected && agentTokens && Object.keys(agentTokens.agents).length > 0 ? (
        <LiveAgentStream agents={agentTokens.agents} round={agentTokens.parliamentRound} />
      ) : (
        <div className={`agent-stream ${isAlert ? `agent-stream--${state}` : ''}`}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, letterSpacing: 2, marginBottom: 10, color: log[0]?.color || 'var(--fg-muted)' }}>
            {log[0]?.agent} &middot; {log[0]?.time}
          </div>
          <div style={{ fontSize: 20, color: 'var(--fg)', lineHeight: 1.6 }}>
            {log[0]?.msg}
          </div>
        </div>
      )}

      {/* Cluster Tree */}
      <div className="cluster-tree">
        <div className="cluster-tree__root">
          <ClusterBox cluster={cluster} sol={sol} proposedCount={flightRules.filter(r => r.status === 'proposed').length} />
        </div>
        <div className="cluster-tree__connectors">
          {zones.map((z, i) => (
            <CSSConnector key={i} status={connectorStatus[state]} animated={isAlert} />
          ))}
        </div>
        <div className="cluster-tree__nodes">
          {zones.map(zone => (
            <NodeBox
              key={zone.id}
              zone={zone}
              triage={triage?.[zone.id]}
              probes={probes}
              quota={RESOURCE_QUOTAS[zone.id]}
              dashboardState={state}
              onNodeClick={() => setDeepDive({ type: 'zone', zoneId: zone.id })}
              onPodClick={(crop) => setDeepDive({ type: 'pod', zoneId: zone.id, cropName: crop.name })}
            />
          ))}
        </div>
      </div>

      {/* Resource Flow */}
      <ResourceFlow flow={flow} dashboardState={state} mars={mars} />

      {/* Crisis panels — simulation + canary */}
      {isAlert && (
        <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SimulationRunner />
          <CanaryDeployment canary={CANARY_DEPLOYMENT} visible />
        </div>
      )}

      {/* Mission timeline */}
      <MissionTimeline sol={sol} />

      {/* Compact hover-to-expand panels — always visible, no folds */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <HoverPanel label="Crew Nutrition" icon="CRW" color="#60a5fa">
          <CrewCompact crew={crew} />
        </HoverPanel>
        <HoverPanel label="Council Log" icon="LOG" color="#e8913a">
          <CouncilCompact log={log} />
        </HoverPanel>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <HoverPanel label={`Flight Rules \u00B7 ${flightRules.length}`} icon="L0" color="#06b6d4">
          <RulesCompact rules={flightRules} />
        </HoverPanel>
        <HoverPanel label={`Events \u00B7 ${events.length}`} icon="EVT" color="#f59e0b">
          <EventsCompact events={events} />
        </HoverPanel>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <HoverPanel label="Memory Wall" icon="MEM" color="#fbbf24">
          <MemoryCompact milestones={MEMORY_WALL} sol={sol} />
        </HoverPanel>
        {nutrition ? (
          <HoverPanel label="Nutrition Analysis" icon="NUT" color="#a855f7">
            <NutritionLive nutrition={nutrition} />
          </HoverPanel>
        ) : (
          <HoverPanel label="System Status" icon="SYS" color="#6b7280">
            <SystemStatusCompact cluster={cluster} />
          </HoverPanel>
        )}
      </div>

      {/* Footer with particle toggle */}
      <div style={{ textAlign: 'center', padding: '16px 0', opacity: 0.3, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: 1 }}>
          EDEN \u00B7 Syngenta x AWS \u00B7 Target humidity: 42%
        </span>
        <ParticleToggle enabled={particles} onToggle={toggleParticles} />
      </div>

      {/* Mars atmosphere layers */}
      <MarsParticles enabled={particles} dashboardState={state} />
      <div className={`mars-terrain mars-terrain--${state}`} />
    </div>
  )
}

// ── CSS Connector line (one per node) ────────────────────────────────────────

const connectorColors = {
  nominal: '#34d399',
  warning: '#f59e0b',
  critical: '#ef4444',
  recovering: '#60a5fa',
}

function CSSConnector({ status = 'nominal', animated = false }) {
  const color = connectorColors[status] || '#34d399'
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 20,
    }}>
      <div style={{
        width: '100%',
        height: 0,
        borderTop: `1.5px ${animated ? 'dashed' : 'solid'} ${color}`,
        opacity: animated ? 0.8 : 0.4,
        position: 'relative',
        animation: animated ? 'flowPulse 1.5s ease-in-out infinite' : 'none',
      }}>
        {/* Arrow tip */}
        <div style={{
          position: 'absolute',
          right: -1,
          top: -4,
          width: 0,
          height: 0,
          borderTop: '4px solid transparent',
          borderBottom: '4px solid transparent',
          borderLeft: `6px solid ${color}`,
          opacity: 0.7,
        }} />
        {/* Origin dot */}
        <div style={{
          position: 'absolute',
          left: -2,
          top: -3,
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: color,
          opacity: 0.5,
        }} />
      </div>
    </div>
  )
}

// ── Hover-to-expand panel ────────────────────────────────────────────────────
// Shows compact content always. On hover: expands with full detail overlay.

function HoverPanel({ label, icon, color, children }) {
  return (
    <div className="hover-panel">
      <div className="hover-panel__header">
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          letterSpacing: 0.5, color: color || 'var(--fg-muted)',
          background: (color || 'var(--fg-muted)') + '15',
          padding: '2px 6px', borderRadius: 3,
        }}>{icon}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
          letterSpacing: 1.5, color: color || 'var(--fg-secondary)', textTransform: 'uppercase',
        }}>{label}</span>
      </div>
      <div className="hover-panel__body">
        {children}
      </div>
    </div>
  )
}

// ── Crew Nutrition — compact inline ──────────────────────────────────────────

function CrewCompact({ crew }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {crew.map((c, i) => {
        const ironLow = c.iron < 75
        const calPct = Math.round((c.kcalActual / c.kcalTarget) * 100)
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 20, flexShrink: 0 }}>{c.emoji}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg)' }}>{c.name}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>{c.role}</span>
              </div>
              <div style={{ display: 'flex', gap: 12, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                <span style={{ color: calPct > 90 ? '#34d399' : '#f59e0b' }}>kcal {calPct}%</span>
                <span style={{ color: c.protein > 85 ? 'var(--fg-muted)' : '#f59e0b' }}>P:{c.protein}%</span>
                <span style={{ color: ironLow ? '#ef4444' : 'var(--fg-muted)' }}>Fe:{c.iron}%{ironLow ? ' \u25BC' : ''}</span>
                <span style={{ color: c.vitC > 100 ? '#34d399' : 'var(--fg-muted)' }}>C:{c.vitC}%</span>
                <span style={{ color: c.calcium > 80 ? 'var(--fg-muted)' : '#f59e0b' }}>Ca:{c.calcium}%</span>
              </div>
            </div>
          </div>
        )
      })}
      {/* Hover overlay — expanded table */}
      <div className="hover-panel__overlay">
        {/* Header row */}
        <div style={{
          display: 'grid', gridTemplateColumns: '140px repeat(6, 1fr)',
          gap: 8, marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border)',
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--fg-muted)', letterSpacing: 1, fontWeight: 700, textTransform: 'uppercase',
        }}>
          <span>CREW</span>
          <span>KCAL</span><span>PROT</span><span>IRON</span><span>VIT C</span><span>CA</span><span>ZN</span>
        </div>
        {crew.map((c, i) => {
          const calPct = Math.round((c.kcalActual / c.kcalTarget) * 100)
          const vals = [
            { v: calPct },
            { v: c.protein }, { v: c.iron }, { v: c.vitC }, { v: c.calcium }, { v: c.zinc },
          ]
          return (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '140px repeat(6, 1fr)',
              gap: 8, padding: '10px 0',
              borderBottom: i < crew.length - 1 ? '1px solid var(--border)' : 'none',
              alignItems: 'center',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 20 }}>{c.emoji}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{c.name}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)' }}>{c.role}</div>
                </div>
              </div>
              {vals.map((n, j) => {
                const v = n.v
                const color = v > 100 ? '#34d399' : v > 85 ? 'var(--fg-secondary)' : v > 70 ? '#f59e0b' : '#ef4444'
                return (
                  <div key={j} style={{ textAlign: 'center' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color }}>{v}%</div>
                    <MicroBar value={v} color={color} height={3} />
                  </div>
                )
              })}
            </div>
          )
        })}
        {/* Notes row */}
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', lineHeight: 1.7 }}>
          {crew.filter(c => c.note).map((c, i) => (
            <div key={i}>{c.name.split('.')[1] || c.name}: {c.note}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Council Log — compact inline ─────────────────────────────────────────────

function CouncilCompact({ log }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {log.slice(0, 3).map((e, i) => (
        <div key={i} style={{
          padding: '6px 10px', borderRadius: 6,
          borderLeft: `3px solid ${e.color}`,
          fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.5,
        }}>
          <span style={{ color: e.color, fontWeight: 600 }}>{e.agent}</span>{' '}
          <span style={{ color: 'var(--fg-muted)' }}>{e.msg.slice(0, 90)}{e.msg.length > 90 ? '...' : ''}</span>
        </div>
      ))}
      {/* Hover overlay with full log */}
      <div className="hover-panel__overlay">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
          {log.map((e, i) => (
            <div key={i} style={{
              padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6,
              borderLeft: `3px solid ${e.color}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: e.color, letterSpacing: 1 }}>{e.agent}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>{e.time}</span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--fg-secondary)', lineHeight: 1.6 }}>{e.msg}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Flight Rules — compact inline ────────────────────────────────────────────

function RulesCompact({ rules }) {
  const triggered = rules.filter(r => r.status === 'triggered')
  const armed = rules.filter(r => r.status === 'armed')
  const proposed = rules.filter(r => r.status === 'proposed')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {triggered.length > 0 && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#f59e0b', marginBottom: 2 }}>
          {triggered.length} triggered
        </div>
      )}
      {triggered.slice(0, 2).map((fr, i) => (
        <div key={i} style={{
          padding: '6px 10px', borderRadius: 6, fontSize: 12,
          borderLeft: '3px solid #f59e0b', background: 'rgba(245,158,11,0.04)',
          fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)', lineHeight: 1.5,
        }}>
          <span style={{ color: 'var(--fg-muted)', marginRight: 8 }}>{fr.id}</span>
          {fr.rule.slice(0, 70)}...
        </div>
      ))}
      {proposed.length > 0 && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#a855f7', marginBottom: 2, marginTop: 4 }}>
          {proposed.length} proposed (learned)
        </div>
      )}
      {proposed.slice(0, 2).map((fr, i) => (
        <div key={`p-${i}`} style={{
          padding: '6px 10px', borderRadius: 6, fontSize: 12,
          borderLeft: '3px solid #a855f7', background: 'rgba(168,85,247,0.04)',
          fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)', lineHeight: 1.5,
        }}>
          <span style={{ color: '#a855f7', marginRight: 8, fontWeight: 600 }}>{fr.id}</span>
          {fr.rule.slice(0, 70)}...
          <span style={{
            fontSize: 9, marginLeft: 8, padding: '1px 6px', borderRadius: 3, fontWeight: 700,
            background: 'rgba(168,85,247,0.12)', color: '#a855f7',
          }}>LEARNED</span>
        </div>
      ))}
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>
        + {armed.length} armed{proposed.length > 0 ? ` \u00B7 ${proposed.length} proposed` : ''}
      </div>
      {/* Hover overlay */}
      <div className="hover-panel__overlay">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 400, overflowY: 'auto' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginBottom: 6, paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
            Layer 0 \u2014 Deterministic, 0ms, cannot be overridden by AI
          </div>
          {rules.map((fr, i) => {
            const isProposed = fr.status === 'proposed'
            const isTriggered = fr.status === 'triggered'
            const borderColor = isProposed ? '#a855f7' : isTriggered ? '#f59e0b' : 'var(--fg-muted)'
            const bgColor = isProposed ? 'rgba(168,85,247,0.06)' : isTriggered ? 'rgba(245,158,11,0.06)' : 'var(--bg-2)'
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px',
                background: bgColor,
                borderRadius: 6, borderLeft: `3px solid ${borderColor}`,
                fontFamily: 'var(--font-mono)', fontSize: 11,
              }}>
                <span style={{ color: isProposed ? '#a855f7' : 'var(--fg-muted)', width: 100, flexShrink: 0, fontWeight: 600 }}>{fr.id}</span>
                <span style={{ color: 'var(--fg-secondary)', flex: 1 }}>{fr.rule}</span>
                {isProposed && fr.source && (
                  <span style={{
                    fontSize: 8, padding: '2px 6px', borderRadius: 3, fontWeight: 700,
                    background: 'rgba(168,85,247,0.12)', color: '#a855f7',
                  }}>{fr.source}</span>
                )}
                <span style={{
                  fontSize: 9, padding: '2px 8px', borderRadius: 4, fontWeight: 700,
                  background: isProposed ? 'rgba(168,85,247,0.15)' : isTriggered ? 'rgba(245,158,11,0.15)' : 'var(--bg-3)',
                  color: isProposed ? '#a855f7' : isTriggered ? '#f59e0b' : 'var(--fg-muted)',
                }}>{fr.status.toUpperCase()}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Memory Wall — compact inline ─────────────────────────────────────────────

function MemoryCompact({ milestones, sol }) {
  const recent = milestones.filter(m => m.sol <= sol).slice(-3)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {recent.map((m, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 10,
          fontFamily: 'var(--font-mono)', fontSize: 12,
        }}>
          <span style={{
            color: m.sol === sol ? '#fbbf24' : 'var(--fg-muted)', fontWeight: 600, width: 54, flexShrink: 0,
          }}>Sol {m.sol}</span>
          <span style={{
            color: m.sol === sol ? 'var(--fg)' : 'var(--fg-secondary)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{m.event}</span>
        </div>
      ))}
      {/* Hover overlay */}
      <div className="hover-panel__overlay">
        <div style={{ position: 'relative', paddingLeft: 18, maxHeight: 400, overflowY: 'auto' }}>
          <div style={{
            position: 'absolute', left: 5, top: 0, bottom: 0, width: 2,
            background: 'linear-gradient(to bottom, var(--border), #fbbf24, var(--border))',
            borderRadius: 1,
          }} />
          {milestones.map((m, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
              opacity: m.sol <= sol ? 1 : 0.3,
              borderBottom: i < milestones.length - 1 ? '1px solid var(--border)' : 'none',
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: '50%', flexShrink: 0, marginLeft: -9,
                background: m.sol === sol ? '#fbbf24' : m.sol < sol ? 'var(--fg-muted)' : 'var(--bg-3)',
                boxShadow: m.sol === sol ? '0 0 8px #fbbf24' : 'none',
              }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: '#fbbf24', width: 54, flexShrink: 0 }}>Sol {m.sol}</span>
              <span style={{ fontSize: 12, color: m.sol === sol ? 'var(--fg)' : 'var(--fg-secondary)', lineHeight: 1.4 }}>{m.event}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Live Agent Token Streaming ────────────────────────────────────────────────
// THE demo showstopper: 14 agents typing simultaneously, word by word

const AGENT_SSE_COLORS = {
  SENTINEL: '#E53E3E', FLORA: '#38A169', PATHFINDER: '#8B6914', TERRA: '#6B4226',
  DEMETER: '#D69E2E', ATMOS: '#63B3ED', AQUA: '#3182CE', HELIOS: '#ECC94B',
  VITA: '#ED64A6', HESTIA: '#9F7AEA', ORACLE: '#5A67D8', CHRONOS: '#A0AEC0',
  COORDINATOR: '#FFFFFF',
  // Council member colors
  Lena: '#60a5fa',   // blue — safety-first
  Kai: '#fbbf24',    // amber — efficiency
  Yara: '#34d399',   // green — plant biologist
  Marcus: '#38bdf8',  // cyan — resource hawk
  Suki: '#f472b6',   // pink — crew advocate
  Niko: '#a78bfa',   // purple — data-driven
  Ren: '#fb923c',    // orange — mission planner
}

function LiveAgentStream({ agents, round }) {
  const entries = Object.entries(agents)
  if (!entries.length) return null

  return (
    <div style={{
      background: 'var(--bg-1)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '14px 16px',
      boxShadow: 'var(--card-shadow)',
    }}>
      {/* Header with round indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: '#e8913a', letterSpacing: 1.5 }}>
          PARLIAMENT
        </span>
        {round && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, letterSpacing: 0.5,
            color: round === 'council' ? '#a78bfa' : round === 3 ? '#34d399' : '#f59e0b',
            background: (round === 'council' ? '#a78bfa' : round === 3 ? '#34d399' : '#f59e0b') + '15',
            padding: '2px 6px', borderRadius: 3,
          }}>
            {round === 'council' ? 'COUNCIL QUORUM' : `ROUND ${round}/3`}
          </span>
        )}
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--fg-muted)' }}>
          {entries.filter(([, a]) => a.active).length} active / {entries.length} agents
        </span>
      </div>

      {/* Agent grid — each agent typing live */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 8 }}>
        {entries.map(([name, agent]) => {
          const color = AGENT_SSE_COLORS[name] || 'var(--fg-muted)'
          return (
            <div key={name} style={{
              background: 'var(--bg-2)', borderRadius: 8,
              border: `1px solid ${agent.active ? color + '44' : 'var(--border)'}`,
              padding: '8px 10px', transition: 'border-color 0.3s',
              opacity: agent.complete ? 0.7 : 1,
            }}>
              {/* Agent name + status */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%', background: color,
                  boxShadow: agent.active ? `0 0 6px ${color}` : 'none',
                  animation: agent.active ? 'pulse 1.5s ease-in-out infinite' : 'none',
                }} />
                {agent.emoji && (
                  <span style={{ fontSize: 13 }}>{agent.emoji}</span>
                )}
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color, letterSpacing: 1 }}>
                  {name}
                </span>
                {agent.toolCall && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, color: '#f59e0b',
                    background: 'rgba(245,158,11,0.1)', padding: '1px 5px', borderRadius: 3,
                  }}>
                    {agent.toolCall}
                  </span>
                )}
                {agent.complete && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#34d399' }}>DONE</span>
                )}
              </div>
              {/* Streaming text */}
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-secondary)',
                lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
                wordBreak: 'break-word',
              }}>
                {agent.partial?.slice(-400) || '...'}
                {agent.active && <span style={{ animation: 'blink 1s step-end infinite' }}>|</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Events — compact inline with hover table ────────────────────────────────

const typeColor = (type) => type === 'Warning' ? '#f59e0b' : '#34d399'

function EventsCompact({ events }) {
  if (!events?.length) return null
  const warnings = events.filter(e => e.type === 'Warning')
  const recent = events.slice(0, 3)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {warnings.length > 0 && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#f59e0b' }}>
          {warnings.length} warning{warnings.length > 1 ? 's' : ''}
        </div>
      )}
      {recent.map((evt, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'baseline', gap: 8,
          fontFamily: 'var(--font-mono)', fontSize: 11,
          padding: '4px 0',
          borderBottom: i < recent.length - 1 ? '1px solid var(--border)' : 'none',
        }}>
          <span style={{ color: 'var(--fg-muted)', width: 36, flexShrink: 0, fontSize: 10 }}>{evt.age}</span>
          <span style={{ color: typeColor(evt.type), fontWeight: 700, width: 52, flexShrink: 0 }}>{evt.type}</span>
          <span style={{ color: 'var(--fg)', fontWeight: 600 }}>{evt.reason}</span>
          <span style={{ color: 'var(--fg-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{evt.message}</span>
        </div>
      ))}
      {events.length > 3 && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)' }}>
          + {events.length - 3} more
        </div>
      )}
      {/* Hover overlay — full event table */}
      <div className="hover-panel__overlay">
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
          kubectl get events — {events.length} total
        </div>
        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: '40px 60px 120px 110px 1fr',
          gap: 0, padding: '0 0 6px 0', marginBottom: 4,
          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, letterSpacing: 1,
          color: 'var(--fg-muted)', textTransform: 'uppercase',
        }}>
          <span>AGE</span><span>TYPE</span><span>REASON</span><span>OBJECT</span><span>MESSAGE</span>
        </div>
        <div style={{ maxHeight: 350, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 0 }}>
          {events.map((evt, i) => (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '40px 60px 120px 110px 1fr',
              gap: 0, padding: '6px 0', alignItems: 'baseline',
              background: evt.type === 'Warning' ? 'rgba(245,158,11,0.04)' : 'transparent',
              borderBottom: i < events.length - 1 ? '1px solid var(--border)' : 'none',
              fontFamily: 'var(--font-mono)', fontSize: 11,
            }}>
              <span style={{ color: 'var(--fg-muted)' }}>{evt.age}</span>
              <span style={{ fontWeight: 700, color: typeColor(evt.type) }}>{evt.type}</span>
              <span style={{ fontWeight: 600, color: 'var(--fg)' }}>{evt.reason}</span>
              <span style={{ color: 'var(--fg-muted)' }}>{evt.object}</span>
              <span style={{ color: 'var(--fg-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{evt.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Nutrition from live backend ───────────────────────────────────────────────

function NutritionLive({ nutrition }) {
  const risks = nutrition?.deficiency_risks || []
  const proj = nutrition?.mission_projection || {}
  const crewStatus = nutrition?.status?.crew || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Deficiency risks */}
      {risks.length > 0 ? risks.map((r, i) => (
        <div key={i} style={{
          padding: '6px 10px', borderRadius: 6, fontSize: 12,
          borderLeft: `3px solid ${r.level === 'critical' ? '#ef4444' : '#f59e0b'}`,
          background: r.level === 'critical' ? 'rgba(239,68,68,0.04)' : 'rgba(245,158,11,0.04)',
          fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)', lineHeight: 1.5,
        }}>
          <span style={{ fontWeight: 700, color: r.level === 'critical' ? '#ef4444' : '#f59e0b', textTransform: 'uppercase' }}>
            {r.level}
          </span>{' '}
          {r.message}
        </div>
      )) : (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#34d399' }}>
          No deficiency risks detected
        </div>
      )}

      {/* Mission projection */}
      {proj.kcal_coverage_pct !== undefined && (
        <div style={{ display: 'flex', gap: 16, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          <span style={{ color: proj.kcal_coverage_pct > 10 ? 'var(--fg-secondary)' : '#ef4444' }}>
            kcal: {proj.kcal_coverage_pct?.toFixed(1)}%
          </span>
          <span style={{ color: proj.protein_coverage_pct > 20 ? 'var(--fg-secondary)' : '#f59e0b' }}>
            protein: {proj.protein_coverage_pct?.toFixed(1)}%
          </span>
          <span style={{ color: 'var(--fg-muted)' }}>
            Sol {proj.current_sol || 0}/{proj.mission_days || 450}
          </span>
        </div>
      )}

      {/* Hover overlay — per-crew detail */}
      {crewStatus.length > 0 && (
        <div className="hover-panel__overlay">
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
            Live nutritional status from backend
          </div>
          {crewStatus.map((c, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', padding: '6px 0',
              borderBottom: i < crewStatus.length - 1 ? '1px solid var(--border)' : 'none',
              fontFamily: 'var(--font-mono)', fontSize: 11,
            }}>
              <span style={{ color: 'var(--fg)', fontWeight: 600 }}>{c.name}</span>
              <span style={{ color: c.kcal_deficit > 0 ? '#f59e0b' : '#34d399' }}>
                kcal: {Math.round(c.current_kcal_intake)}/{Math.round(c.daily_kcal_target)}
              </span>
              <span style={{ color: c.protein_deficit > 0 ? '#f59e0b' : '#34d399' }}>
                P: {c.current_protein_intake?.toFixed(1)}g/{c.daily_protein_target}g
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── System Status (shown when nutrition unavailable) ──────────────────────────

function SystemStatusCompact({ cluster }) {
  if (!cluster) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--fg-muted)' }}>Sync</span>
        <span style={{ color: cluster.syncStatus === 'Synced' ? '#34d399' : '#f59e0b', fontWeight: 600 }}>{cluster.syncStatus}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--fg-muted)' }}>Health</span>
        <span style={{ color: cluster.healthStatus === 'Healthy' ? '#34d399' : '#f59e0b', fontWeight: 600 }}>{cluster.healthStatus}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--fg-muted)' }}>Pods</span>
        <span style={{ color: 'var(--fg-secondary)' }}>{cluster.activePods}/{cluster.pods}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--fg-muted)' }}>Flight Rules</span>
        <span style={{ color: 'var(--fg-secondary)' }}>{cluster.flightRules}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--fg-muted)' }}>Network</span>
        <span style={{ color: cluster.networkPolicy === 'OPEN' ? '#34d399' : '#ef4444', fontWeight: 600 }}>{cluster.networkPolicy}</span>
      </div>
      {cluster.modelTier && (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--fg-muted)' }}>Model</span>
          <span style={{ color: cluster.modelAvailable ? '#34d399' : 'var(--fg-muted)', fontWeight: 600 }}>{cluster.modelTier}</span>
        </div>
      )}
    </div>
  )
}
