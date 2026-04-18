import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { stateLog, uiLog } from './lib/logger'
import Header from './components/Header'
import AlertBanner from './components/AlertBanner'
import CrewEscalationBanner from './components/CrewEscalationBanner'
import VirtualLab from './components/VirtualLab'
import TriagePanel from './components/TriagePanel'
import MissionTimeline from './components/MissionTimeline'
import LabView from './components/LabView'
import { ClusterView, EventStream } from './components/cluster'
import { useDemo } from './hooks/useDemo'
import { useEdenAPI } from './hooks/useEdenAPI'
import { useEdenSSE, useAgentTokens, useSSEEvents } from './hooks/useEdenSSE'
import './cluster.css'
import {
  ZONES, CREW, RESOURCES, RESOURCES_PRESTORM, RESOURCES_STORM, RESOURCES_RECOVERY,
  STRATEGIES, TRIAGE,
  FLIGHT_RULES,
  COUNCIL_LOG, COUNCIL_LOG_NOMINAL,
  AGENT_COLORS,
} from './data/mock'

const API_BASE = import.meta.env.VITE_EDEN_API || 'http://localhost:8000'

// ── Backend-driven dashboard state ─────────────────────────────────────
// Overrides demo timer when SSE chaos/alert events arrive.
// State machine: nominal ──[chaos]──→ crisis ──[30s]──→ recovery ──[15s]──→ nominal
const RECOVERY_DELAY = 30000
const NOMINAL_DELAY = 15000

function useBackendState() {
  const [state, setState] = useState(null) // null = not driven by backend
  const crisisRef = useRef(null)
  const recoveryRef = useRef(null)

  const clearTimers = useCallback(() => {
    if (crisisRef.current) { clearTimeout(crisisRef.current); crisisRef.current = null }
    if (recoveryRef.current) { clearTimeout(recoveryRef.current); recoveryRef.current = null }
  }, [])

  const triggerCrisis = useCallback(() => {
    clearTimers()
    stateLog.warn({ msg: 'state_transition', from: 'any', to: 'crisis', source: 'backend_event' })
    setState('crisis')
    crisisRef.current = setTimeout(() => {
      setState('recovery')
      crisisRef.current = null
      recoveryRef.current = setTimeout(() => {
        setState(null) // hand back to demo timer
        recoveryRef.current = null
      }, NOMINAL_DELAY)
    }, RECOVERY_DELAY)
  }, [clearTimers])

  const triggerAlert = useCallback(() => {
    setState(prev => (prev === 'crisis' ? prev : 'alert'))
  }, [])

  useEffect(() => clearTimers, [clearTimers])

  // Stable handler refs so useMemo([]) in App doesn't go stale
  const triggerCrisisRef = useRef(triggerCrisis)
  const triggerAlertRef = useRef(triggerAlert)
  triggerCrisisRef.current = triggerCrisis
  triggerAlertRef.current = triggerAlert

  const handlers = useMemo(() => ({
    chaos: () => triggerCrisisRef.current(),
    alert: (data) => {
      if (data?.severity === 'critical') triggerCrisisRef.current()
      else triggerAlertRef.current()
    },
  }), [])

  const reset = useCallback(() => {
    clearTimers()
    setState(null)
  }, [clearTimers])

  return { state, handlers, reset }
}

// ── Mock data for demo timer mode ──────────────────────────────────────

const DEMO_LOGS = {
  nominal: COUNCIL_LOG_NOMINAL,
  cme: [
    { time: '14:24:09', agent: 'SENTINEL', msg: 'Sol 247. CME-2026-0124 detected. Speed: 1,243 km/s out of N15E10. Instruments: SOHO LASCO/C2, C3, STEREO A COR2. Calculating Mars transit...', color: AGENT_COLORS.SENTINEL },
    { time: '14:24:10', agent: 'SENTINEL', msg: 'Mars ETA: 50.7 hours. Wheat in Node:Carb at BBCH 60 (flowering) \u2014 HIGH radiation vulnerability. Syngenta KB: yield reduction 15-40% under elevated UV-B.', color: AGENT_COLORS.SENTINEL },
    { time: '14:24:11', agent: 'SENTINEL', msg: 'Querying Syngenta KB: wheat radiation tolerance at BBCH 60... KB response: \u201CYield reduction 15-40% under elevated UV-B during flowering. Recommend radiation shielding and modified nutrient solution.\u201D Source: Plant Stress and Response Guide.', color: AGENT_COLORS.SENTINEL },
  ],
  council: COUNCIL_LOG,
  stockpile: [
    { time: '14:24:19', agent: 'COUNCIL', msg: 'Strategy C adopted unanimously (5/5). Pre-emptive full protocol initiated. All agents executing.', color: AGENT_COLORS.COUNCIL },
    { time: '14:30:00', agent: 'AQUA', msg: 'Desalination at MAX. Water climbing: 340L \u2192 380L \u2192 420L. Battery charging: 78% \u2192 89%. Transpiration capture sealed.', color: AGENT_COLORS.AQUA },
    { time: '18:00:00', agent: 'FLORA', msg: 'Pre-harvesting spinach \u2014 1.9 kg secured. Stress-hardening wheat: EC from 2.0 to 2.4 mS/cm. DLI maintained at 17 mol/m\u00B2/day. She\u2019ll be ornery but she\u2019ll make it.', color: AGENT_COLORS.FLORA },
    { time: '22:00:00', agent: 'AQUA', msg: 'Water 580L. Battery 100%. Crops pre-watered to saturation. Shields ARMED. 7.2-sol autonomy confirmed.', color: AGENT_COLORS.AQUA },
    { time: '22:00:01', agent: 'VITA', msg: 'Pre-harvest spinach secured. Vitamin C buffer: 58 sols. Cmdr. Chen\u2019s portion saved. Setting Condition Zebra \u2014 cross-zone sharing suspended.', color: AGENT_COLORS.VITA },
  ],
  storm: [
    { time: 'Sol 249', agent: 'SENTINEL', msg: 'CME IMPACT. Radiation spike: 263 \u00B5Sv/hr. Solar output: 30%. Shields active. Zone isolation: cross-zone sharing suspended.', color: AGENT_COLORS.SENTINEL },
    { time: 'Sol 249', agent: 'AQUA', msg: 'Desal at 30% power: 36 L/sol. Deficit: 64 L/sol. Pre-stockpiled 580L \u2014 autonomy: 7.2 sols. Covers 5-sol storm + 2.2-sol margin. We\u2019re good.', color: AGENT_COLORS.AQUA },
    { time: 'Sol 250', agent: 'VITA', msg: 'TRIAGE: Wheat 0.72 \u2014 RED, intervening. Tomato 0.85 \u2014 YELLOW, monitoring. Soybean 0.91 \u2014 GREEN. Crew protein reduced 8%. Eng. Petrov supplemented from stored rations.', color: AGENT_COLORS.VITA },
    { time: 'Sol 251', agent: 'FLORA', msg: 'Storm\u2019s here. Wheat\u2019s holding \u2014 stress-hardened mix working. Tomato dormant, expected. Soybean doesn\u2019t care, tough little plant. Lights at minimum. We wait.', color: AGENT_COLORS.FLORA },
  ],
  recovery: [
    { time: 'Sol 254', agent: 'SENTINEL', msg: 'Radiation returning to baseline. Solar recovering: 30% \u2192 68% \u2192 91%. Storm duration: 4.8 sols. Within predicted parameters.', color: AGENT_COLORS.SENTINEL },
    { time: 'Sol 254', agent: 'FLORA', msg: 'We made it. Wheat lost 8% yield at flowering \u2014 better than the 15-40% KB predicted without intervention. Stress-hardening saved 7-32% yield. Soybean never flinched.', color: AGENT_COLORS.FLORA },
    { time: 'Sol 254', agent: 'ORACLE', msg: 'Post-event analysis. Predicted: 3% loss. Actual: 2.7%. Model accuracy: 90%. Proposing FR-CME-012: IF cme_speed > 1000 AND wheat_bbch 55-70 THEN pre-harvest leafy greens + stress-harden EC +0.4.', color: AGENT_COLORS.ORACLE },
    { time: 'Sol 254', agent: 'VITA', msg: 'All crew nutritional targets maintained. Pre-harvested spinach provided 58-sol buffer \u2014 never breached. Zero crew health impact. Cmdr. Chen enjoyed the spinach.', color: AGENT_COLORS.VITA },
    { time: 'Sol 255', agent: 'ORACLE', msg: 'Flight rules updated: 87 \u2192 89. Two new rules from this event. The farm is wiser now. 196 sols remaining. Survival probability: 97.1%.', color: AGENT_COLORS.ORACLE },
  ],
}

const resourcesByState = {
  nominal: RESOURCES,
  alert: RESOURCES_PRESTORM,
  crisis: RESOURCES_STORM,
  recovery: RESOURCES_RECOVERY,
}

export default function App() {
  const [view, _setView] = useState('cluster')
  const setView = useCallback((v) => {
    stateLog.info({ msg: 'view_changed', from: view, to: v })
    _setView(v)
  }, [view])
  const [escalations, setEscalations] = useState([])
  const demo = useDemo()
  const api = useEdenAPI(ZONES)

  // Load escalations from backend on mount + when reconnecting
  useEffect(() => {
    if (!api.connected) return
    fetch(`${API_BASE}/api/escalations`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data) && data.length) {
          stateLog.info({ msg: 'escalations_loaded', count: data.length })
          setEscalations(data)
        }
      })
      .catch(() => {})
  }, [api.connected])
  const backend = useBackendState()

  // SSE: live agent token streaming + event stream + backend state drive
  const agentTokens = useAgentTokens()
  const sseEvents = useSSEEvents()
  const escalationsRef = useRef(escalations)
  escalationsRef.current = escalations
  const sseHandlers = useMemo(() => ({
    ...agentTokens.handlers,
    ...sseEvents.handlers,
    // chaos/alert drive BOTH event stream AND dashboard state
    chaos: (d) => { sseEvents.handlers.chaos?.(d); backend.handlers.chaos?.(d) },
    alert: (d) => { sseEvents.handlers.alert?.(d); backend.handlers.alert?.(d) },
    // Crew escalations
    crew_escalation: (d) => {
      sseEvents.handlers.crew_escalation?.(d)
      backend.handlers.alert?.(d)
      setEscalations(prev => [{ ...d, status: 'pending' }, ...prev])
    },
    escalation_resolved: (d) => {
      sseEvents.handlers.escalation_resolved?.(d)
      setEscalations(prev => prev.filter(e => e.escalation_id !== d.escalation_id))
    },
  }), []) // Stable ref — all handlers use refs internally
  const sse = useEdenSSE(sseHandlers)

  // Backend-driven state overrides demo timer when connected and active
  const isConnected = api.connected || sse.connected
  const prevConnectedRef = useRef(false)
  useEffect(() => {
    if (isConnected !== prevConnectedRef.current) {
      stateLog.info({ msg: 'connection_state_changed', connected: isConnected, api: api.connected, sse: sse.connected })
      prevConnectedRef.current = isConnected
    }
  }, [isConnected, api.connected, sse.connected])
  const state = isConnected && backend.state ? backend.state : demo.state
  const isAlert = state === 'alert' || state === 'crisis'

  const sol = api.sol ?? (state === 'nominal' ? 247 : state === 'recovery' ? 254 : 249)

  const resources = (api.connected && api.resources) ? api.resources : resourcesByState[state]

  // Use real agent decisions when connected and available, else mock
  const mockLog = DEMO_LOGS[demo.logKey] || DEMO_LOGS.nominal
  const log = (api.connected && api.decisions?.length) ? api.decisions : mockLog

  // Use real zone data when connected, else mock
  const zones = api.zones || ZONES
  const flightRules = (api.connected && api.flightRules?.length) ? api.flightRules : FLIGHT_RULES
  const crew = (api.connected && api.crew?.length) ? api.crew : CREW

  // Live events: SSE events when connected, else mock events from ClusterView
  const liveEvents = sse.connected && sseEvents.events.length > 0 ? sseEvents.events : null

  // Mars conditions: live from backend, or mock based on state
  const MOCK_MARS = {
    nominal:  { exterior_temp: -63, dome_temp: 22, pressure_hpa: 6.1, solar_irradiance: 590, dust_opacity: 0.3, sol: 247, storm_active: false, radiation_alert: false },
    alert:    { exterior_temp: -63, dome_temp: 22, pressure_hpa: 6.1, solar_irradiance: 590, dust_opacity: 0.3, sol: 247, storm_active: false, radiation_alert: true },
    crisis:   { exterior_temp: -58, dome_temp: 18, pressure_hpa: 5.8, solar_irradiance: 250, dust_opacity: 0.8, sol: 249, storm_active: true, radiation_alert: true },
    recovery: { exterior_temp: -61, dome_temp: 21, pressure_hpa: 6.0, solar_irradiance: 520, dust_opacity: 0.4, sol: 254, storm_active: false, radiation_alert: false },
  }
  const mars = api.mars || MOCK_MARS[state]

  const stateColor = {
    nominal: '#34d399',
    alert: '#e8913a',
    crisis: '#ef4444',
    recovery: '#60a5fa',
  }[state]

  return (
    <div className="eden-app">
      <Header
        sol={sol}
        dashboardState={state}
        onStateChange={(s) => { backend.reset(); demo.setManualState(s) }}
        demoRunning={demo.running}
        view={view}
        onViewChange={setView}
        apiConnected={api.connected}
        sseConnected={sse.connected}
        mars={mars}
        apiStatus={api.connected ? api.status : null}
      />

      {/* ── MOCK DATA BANNER — impossible to miss ─────────────────── */}
      {!isConnected && (
        <div style={{
          background: 'repeating-linear-gradient(45deg, rgba(245,158,11,0.08), rgba(245,158,11,0.08) 10px, transparent 10px, transparent 20px)',
          borderBottom: '2px solid rgba(245,158,11,0.3)',
          padding: '6px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
        }}>
          <span style={{
            background: '#f59e0b',
            color: '#000',
            fontWeight: 800,
            fontSize: 9,
            padding: '2px 8px',
            borderRadius: 3,
            letterSpacing: 1.5,
          }}>
            MOCK DATA
          </span>
          <span style={{ color: '#f59e0b', fontWeight: 600 }}>
            Backend unreachable at {API_BASE}
          </span>
          <span style={{ color: 'var(--fg-muted)' }}>
            {api.error ? `(${api.error})` : '— All data shown is simulated'}
          </span>
          <span style={{ color: 'var(--fg-muted)', fontSize: 10 }}>
            Start backend: <code style={{ color: '#f59e0b' }}>python -m eden</code>
          </span>
        </div>
      )}

      {/* Demo control bar */}
      <div className={`demo-bar ${demo.running ? 'demo-bar--running' : ''}`}>
        <button
          onClick={demo.running ? demo.stop : demo.start}
          className={`demo-btn ${demo.running ? 'demo-btn--stop' : 'demo-btn--start'}`}
        >
          {demo.running ? '■ STOP' : '▶ DEMO'}
        </button>

        {demo.running && (
          <>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${(demo.currentT / demo.loopDuration) * 100}%`,
                  background: stateColor,
                }}
              />
            </div>
            <span style={{ fontSize: 11, color: 'var(--fg-secondary)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
              {demo.currentStep?.label}
            </span>
            <span style={{ fontSize: 11, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
              {demo.currentT}s / {demo.loopDuration}s
            </span>
          </>
        )}

        {!demo.running && (
          <span style={{ fontSize: 11, color: backend.state ? stateColor : 'var(--fg-muted)' }}>
            {backend.state
              ? `LIVE: ${state.toUpperCase()}`
              : <>Full 42s demo loop: nominal &rarr; CME &rarr; council &rarr; stockpile &rarr; storm &rarr; recovery</>
            }
          </span>
        )}

        {/* Action buttons — visible when backend is connected */}
        {isConnected && (
          <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
            <RetroButton />
            <span style={{ width: 1, background: 'var(--border)', margin: '2px 4px' }} />
            <ChaosButton type="dust_storm" label="Dust Storm" />
            <ChaosButton type="fire" label="Fire" />
            <ChaosButton type="sensor_failure" label="Sensor Fail" />
            <ChaosButton type="light_failure" label="Light Fail" />
            <ChaosButton type="water_line_blocked" label="Water Block" />
            <RecoverButton />
          </div>
        )}
      </div>

      {/* Crew escalation notifications */}
      <CrewEscalationBanner
        escalations={escalations}
        onUpdate={(id, action) => {
          if (action === 'resolve' || action === 'dismiss') {
            setEscalations(prev => prev.filter(e => e.escalation_id !== id))
          } else if (action === 'acknowledge') {
            setEscalations(prev => prev.map(e =>
              e.escalation_id === id ? { ...e, status: 'acknowledged' } : e
            ))
          }
        }}
      />

      {view === 'cluster' ? (
        <ClusterView
          dashboardState={state}
          logKey={demo.logKey}
          sol={sol}
          zones={zones}
          crew={crew}
          flightRules={flightRules}
          log={log}
          resources={resources}
          liveEvents={liveEvents}
          agentTokens={agentTokens}
          sseConnected={sse.connected}
          mars={mars}
          liveClusterStatus={api.connected ? api.clusterStatus : null}
          liveResourceFlow={api.connected ? api.resourceFlow : null}
          livePodProbes={api.connected ? api.podProbes : null}
          nutrition={api.connected ? api.nutrition : null}
          apiStatus={api.connected ? api.status : null}
        />
      ) : view === 'dashboard' ? (
        <CinematicDashboard
          log={log}
          resources={resources}
          zones={zones}
          flightRules={flightRules}
          sol={sol}
          state={state}
          isAlert={isAlert}
          strategies={STRATEGIES}
          triage={TRIAGE}
          liveEvents={liveEvents}
          agentTokens={agentTokens}
          sseConnected={sse.connected}
        />
      ) : (
        <LabView zones={zones} strategies={STRATEGIES} dashboardState={state} log={log} />
      )}

      <div className="eden-footer">
        <span>EDEN · Syngenta x AWS · Target humidity: 42%</span>
      </div>
    </div>
  )
}

const resourceColors = {
  water: '#06b6d4',
  battery: '#34d399',
  solar: '#fbbf24',
  desal: '#e8913a',
  o2: '#a78bfa',
}

const statusColors = { nominal: '#34d399', watch: '#f59e0b', warning: '#f59e0b', critical: '#ef4444' }

function RetroButton() {
  const [firing, setFiring] = useState(false)
  const [result, setResult] = useState(null)
  const fire = async () => {
    setFiring(true)
    setResult(null)
    uiLog.info({ msg: 'retrospective_triggered' })
    try {
      const res = await fetch(`${API_BASE}/api/retrospective/trigger`, { method: 'POST' })
      const json = await res.json()
      uiLog.info({ msg: 'retrospective_complete', decisions: json.decisions?.length || 0 })
      setResult(json)
    } catch { /* backend might be down */ }
    setTimeout(() => { setFiring(false); setResult(null) }, 4000)
  }
  return (
    <button
      onClick={fire}
      disabled={firing}
      title={result ? `${result.decisions?.length || 0} decisions, report generated` : 'Trigger retrospective analysis of flight rules and agent performance'}
      style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
        padding: '3px 8px', borderRadius: 4, border: '1px solid rgba(168,85,247,0.4)',
        background: firing ? 'rgba(168,85,247,0.15)' : 'transparent',
        color: firing ? '#a855f7' : '#a855f7',
        cursor: firing ? 'default' : 'pointer', letterSpacing: 0.5,
        transition: 'all 0.2s',
      }}
    >
      {firing ? (result ? `${result.decisions?.length || 0} decisions` : 'Analyzing...') : 'Retrospective'}
    </button>
  )
}

function RecoverButton() {
  const [firing, setFiring] = useState(false)
  const fire = async () => {
    setFiring(true)
    try {
      await fetch(`${API_BASE}/api/chaos/recover`, { method: 'POST' })
    } catch { /* */ }
    setTimeout(() => setFiring(false), 2000)
  }
  return (
    <button
      onClick={fire}
      disabled={firing}
      style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
        padding: '3px 8px', borderRadius: 4, border: '1px solid rgba(52,211,153,0.4)',
        background: firing ? 'rgba(52,211,153,0.15)' : 'transparent',
        color: '#34d399',
        cursor: firing ? 'default' : 'pointer', letterSpacing: 0.5,
        transition: 'all 0.2s',
      }}
    >
      {firing ? 'RECOVERED' : 'Recover'}
    </button>
  )
}

function ChaosButton({ type, label }) {
  const [firing, setFiring] = useState(false)
  const fire = async () => {
    setFiring(true)
    uiLog.info({ msg: 'chaos_injection', event_type: type })
    try {
      await fetch(`${API_BASE}/api/chaos/${type}`, { method: 'POST' })
    } catch { /* backend might be down */ }
    setTimeout(() => setFiring(false), 2000)
  }
  return (
    <button
      onClick={fire}
      disabled={firing}
      style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
        padding: '3px 8px', borderRadius: 4, border: '1px solid rgba(239,68,68,0.3)',
        background: firing ? 'rgba(239,68,68,0.15)' : 'transparent',
        color: firing ? '#ef4444' : 'var(--fg-muted)',
        cursor: firing ? 'default' : 'pointer', letterSpacing: 0.5,
        transition: 'all 0.2s',
      }}
    >
      {firing ? 'INJECTED' : label}
    </button>
  )
}

function CinematicDashboard({ log, resources, zones, flightRules, sol, state, isAlert, strategies, triage, liveEvents, agentTokens, sseConnected }) {
  const heroClass = state === 'crisis' ? 'cinematic-hero--crisis'
    : state === 'alert' ? 'cinematic-hero--alert'
    : state === 'recovery' ? 'cinematic-hero--recovery' : ''

  const triggered = flightRules.filter(r => r.status === 'triggered')
  const armed = flightRules.filter(r => r.status === 'armed')

  return (
    <div className="cinematic fade-in">
      {/* Alert banner */}
      {isAlert && <AlertBanner visible etaHours={50.7} />}

      {/* Hero agent thought */}
      <div className={`cinematic-hero ${heroClass}`}>
        <div className="cinematic-hero__agent" style={{ color: log[0]?.color || 'var(--fg-muted)' }}>
          {log[0]?.agent} · {log[0]?.time}
        </div>
        <div className="cinematic-hero__text">
          {log[0]?.msg}
        </div>
      </div>

      {/* Virtual Lab + Triage during crisis */}
      {isAlert && (
        <div className="cinematic-crisis fade-in">
          <VirtualLab strategies={strategies} visible />
          <TriagePanel triage={triage} visible />
        </div>
      )}

      {/* Metrics strip — bare numbers */}
      <div className="cinematic-metrics">
        {Object.entries(resources).map(([key, r]) => {
          const color = resourceColors[key] || 'var(--fg-secondary)'
          return (
            <div key={key} className="cinematic-metric">
              <div className="cinematic-metric__value" style={{ color }}>
                {r.current}{r.unit === '%' ? '%' : ` ${r.unit}`}
              </div>
              <div className="cinematic-metric__label">{r.label}</div>
              <div className="cinematic-metric__rate">{r.rate}</div>
            </div>
          )
        })}
      </div>

      {/* Zone indicators */}
      <div className="cinematic-zones">
        {zones.map(z => (
          <div key={z.id} className="cinematic-zone">
            <div
              className="cinematic-zone__dot"
              style={{
                background: statusColors[z.status],
                boxShadow: `0 0 8px ${statusColors[z.status]}`,
              }}
            />
            <div className="cinematic-zone__info">
              <div className="cinematic-zone__name">
                {z.icon} {z.name} · {z.health}%
              </div>
              <div className="cinematic-zone__detail">
                {z.crops.join(' + ')} · BBCH {z.bbch} · {z.waterUsage} L/sol
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Secondary: council log + flight rules */}
      <div className="cinematic-secondary">
        <div className="cinematic-secondary__section">
          <div className="cinematic-secondary__title">Council Log · {log.length} entries</div>
          {log.slice(0, 4).map((e, i) => (
            <div key={i} className="cinematic-log-entry" style={{ borderLeftColor: e.color }}>
              <span style={{ color: e.color, fontWeight: 600 }}>{e.agent}</span>{' '}
              <span style={{ color: 'var(--fg-muted)', fontSize: 9 }}>{e.time}</span>
              <div>{e.msg}</div>
            </div>
          ))}
        </div>
        <div className="cinematic-secondary__section">
          <div className="cinematic-secondary__title">
            Flight Rules · {flightRules.length} active · {triggered.length} triggered
          </div>
          {triggered.map((fr, i) => (
            <div key={i} className="cinematic-rule" style={{ color: '#f59e0b' }}>
              <span className="cinematic-rule__id">{fr.id}</span>
              <span>{fr.rule}</span>
            </div>
          ))}
          {armed.slice(0, 3).map((fr, i) => (
            <div key={i} className="cinematic-rule">
              <span className="cinematic-rule__id">{fr.id}</span>
              <span>{fr.rule}</span>
            </div>
          ))}
          {armed.length > 3 && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--fg-muted)', padding: '4px 0' }}>
              + {armed.length - 3} more armed
            </div>
          )}
        </div>
      </div>

      {/* Live events from SSE — visible in cinematic view too */}
      {liveEvents && liveEvents.length > 0 && (
        <EventStream events={liveEvents} maxVisible={6} />
      )}

      {/* Timeline — full bleed */}
      <div className="cinematic-timeline">
        <MissionTimeline sol={sol} />
      </div>
    </div>
  )
}
