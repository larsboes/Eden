import { useState, useEffect, useRef, useCallback } from 'react'
import { apiLog, startTimer } from '../lib/logger'

const API_BASE = import.meta.env.VITE_EDEN_API || 'http://localhost:8000'
const POLL_INTERVAL = 2000

// Map API zone IDs to dashboard zone IDs (A/B/C/D)
// Backend uses zone-protein/carb/vitamin/support (from MemorySensorAdapter)
const ZONE_MAP = {
  'zone-protein': 'A',
  'zone-carb': 'B',
  'zone-vitamin': 'C',
  'zone-support': 'D',
  // Legacy IDs (kept for backwards compat if backend hasn't been updated)
  'sim-alpha': 'A',
  'sim-beta': 'C',
  'sim-gamma': 'A',
}

// Map agent decision severity to log colors
const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#06b6d4',
  low: '#22c55e',
  info: '#6b7280',
}

function mapFlightRules(apiRules) {
  if (!apiRules?.length) return null
  return apiRules.map(r => ({
    id: r.id,
    rule: r.rule,
    status: r.status,      // "armed" or "triggered"
    count: r.count || 0,
    priority: r.priority,  // "CRITICAL", "HIGH", "MEDIUM", "LOW"
    source: r.source || "Earth baseline",
  }))
}

// Default crew nutritional targets from crew-requirements.json
const CREW_DEFAULTS = {
  'Cmdr. Chen':  { kcalTarget: 2375, kcalActual: 2256, protein: 87, iron: 72, calcium: 85, vitC: 133, zinc: 78, note: 'Light EVA schedule. Iron trending low \u2014 monitoring.' },
  'Dr. Okafor':  { kcalTarget: 2250, kcalActual: 2138, protein: 94, iron: 91, calcium: 88, vitC: 120, zinc: 82, note: 'Lab-focused, lowest energy expenditure.' },
  'Eng. Petrov': { kcalTarget: 2750, kcalActual: 2530, protein: 82, iron: 85, calcium: 68, vitC: 115, zinc: 75, note: 'Higher calorie need from EVA work. Calcium trending low.' },
  'Sci. Tanaka': { kcalTarget: 2375, kcalActual: 2280, protein: 90, iron: 88, calcium: 82, vitC: 140, zinc: 80, note: 'Monitors crop health daily. Emotional attachment to greenhouse.' },
}

function mapCrew(apiCrew) {
  if (!apiCrew?.length) return null
  return apiCrew.map(c => {
    const defaults = CREW_DEFAULTS[c.name] || {}
    // Use || instead of ?? so backend zeros (fresh boot, no harvests yet) fall back to defaults
    return {
      name: c.name,
      role: c.role,
      emoji: c.emoji,
      kcalTarget: c.kcalTarget || defaults.kcalTarget || 2375,
      kcalActual: c.kcalActual || defaults.kcalActual || 2256,
      protein: c.protein || defaults.protein || 85,
      preference: c.preference,
      dietaryFlags: c.dietaryFlags || [],
      iron: c.iron || defaults.iron || 80,
      calcium: c.calcium || defaults.calcium || 80,
      vitC: c.vitC || defaults.vitC || 120,
      vitD: 0,
      zinc: c.zinc || defaults.zinc || 78,
      potassium: 65,
      note: c.note || defaults.note || '',
    }
  })
}

function mapDecisionsToLog(decisions) {
  if (!decisions || !decisions.length) return null
  return decisions
    .slice(-20)
    .reverse()
    .map(d => ({
      time: new Date(d.timestamp * 1000).toLocaleTimeString('en-US', { hour12: false }),
      agent: d.agent_name || 'EDEN',
      msg: d.reasoning || d.action || '',
      color: SEVERITY_COLORS[d.severity] || '#6b7280',
      type: d.severity,
      zone: d.zone_id,
      tier: d.tier,
    }))
}

function overlayZones(mockZones, apiZones) {
  if (!apiZones || !apiZones.length) return null

  const apiByDashId = {}
  for (const z of apiZones) {
    const dashId = ZONE_MAP[z.zone_id]
    if (dashId) apiByDashId[dashId] = z
  }

  return mockZones.map(mock => {
    const live = apiByDashId[mock.id]
    if (!live) return mock
    return {
      ...mock,
      temp: live.temperature,
      humidity: live.humidity,
      light: Math.round((live.light / 500) * 100), // normalize to %
      soilMoisture: live.water_level,
      pressure: live.pressure,
      _isAlive: live.is_alive,
      _fireDetected: live.fire_detected,
      _live: true,
      _lastUpdated: live.last_updated,
    }
  })
}

// ── Derive ClusterStatus from backend status + zones + mars ──────────

function deriveClusterStatus(status, zones, mars, flightRules) {
  if (!status) return null

  const zonesAlive = zones ? zones.filter(z => z._isAlive !== false).length : 4
  const totalZones = zones ? zones.length : 4
  const totalPods = totalZones * 2 // 2 crops per zone
  const activePods = zonesAlive * 2
  const anyFire = zones ? zones.some(z => z._fireDetected) : false
  const stormActive = mars?.storm_active || false
  const radiationAlert = mars?.radiation_alert || false
  const frCount = flightRules?.length || status.flight_rules_count || 0

  let syncStatus = 'Synced'
  let healthStatus = 'Healthy'
  let networkPolicy = 'OPEN'
  let strategy = null

  if (!status.reconciler_running) {
    syncStatus = 'OutOfSync'
    healthStatus = 'Reconciler Offline'
  } else if (anyFire || zonesAlive < totalZones) {
    syncStatus = 'OutOfSync'
    healthStatus = 'Degraded'
    networkPolicy = 'ISOLATED'
  } else if (stormActive) {
    syncStatus = 'OutOfSync'
    healthStatus = 'Degraded'
    networkPolicy = 'ISOLATED'
    strategy = 'C (Promoted)'
  } else if (radiationAlert) {
    syncStatus = 'Warning'
    healthStatus = 'CME Incoming'
    strategy = 'C'
  }

  const unavailable = totalPods - activePods
  return {
    syncStatus,
    healthStatus,
    reconciledAt: `${Math.round(status.uptime)}s uptime`,
    nodes: totalZones,
    pods: totalPods,
    activePods,
    flightRules: frCount,
    pdb: {
      maxUnavailable: '30%',
      currentUnavailable: unavailable,
      budget: unavailable / totalPods > 0.3 ? 'VIOLATED' : 'OK',
    },
    daemonSet: { desired: totalZones, ready: zonesAlive },
    strategy,
    networkPolicy,
    modelTier: status.model_tier || 'unknown',
    modelAvailable: status.model_available || false,
  }
}

// ── Derive ResourceFlow from backend resources + mars ────────────────

function deriveResourceFlow(resources, mars) {
  if (!resources) return null

  const s = resources.solar || {}
  const b = resources.battery || {}
  const d = resources.desal || {}
  const w = resources.water || {}
  const o = resources.o2 || {}

  const solarPct = s.current ?? 100
  const batteryPct = b.current ?? 78
  const desalVal = d.current ?? 120
  const desalPct = d.max ? Math.round((d.current / d.max) * 100) : 100

  function statusFromPct(pct) {
    if (pct > 80) return 'nominal'
    if (pct > 50) return 'nominal'
    if (pct > 30) return 'degraded'
    return 'critical'
  }

  const solarKW = ((solarPct / 100) * 4.2).toFixed(1)
  const crisis = solarPct < 50 || batteryPct < 40

  return {
    solar:      { label: 'Solar Panels', value: `${solarKW} kW`, pct: solarPct, status: statusFromPct(solarPct) },
    power:      { label: 'Power Grid', value: `${Math.round(batteryPct)}%`, pct: batteryPct, status: statusFromPct(batteryPct) },
    desal:      { label: 'Desalination', value: `${Math.round(desalVal)} L/sol`, pct: desalPct, status: statusFromPct(desalPct) },
    irrigation: { label: 'Irrigation', value: crisis ? 'Reduced' : '4 zones', pct: crisis ? 50 : 100, status: crisis ? 'degraded' : 'nominal' },
    lights:     { label: 'Grow Lights', value: crisis ? 'Minimum' : 'Active', status: crisis ? 'degraded' : 'nominal' },
    heating:    { label: 'Dome Heating', value: mars ? `${Math.round(mars.dome_temp)}\u00B0C` : '22\u00B0C', status: crisis ? 'degraded' : 'nominal' },
    shields:    { label: 'Shields', value: mars?.radiation_alert || mars?.storm_active ? 'ACTIVE' : 'Standby', status: mars?.radiation_alert || mars?.storm_active ? 'critical' : 'standby' },
    battery:    { label: 'Battery', value: `${Math.round(batteryPct)}%`, pct: batteryPct, status: statusFromPct(batteryPct) },
    harvest:    { label: 'Harvest Output', value: crisis ? 'Paused' : 'Nominal', status: crisis ? 'degraded' : 'nominal' },
    crew:       { label: 'Crew (4)', vitC: `${Math.round(o.current ?? 14)}%`, iron: '—', o2: `${(o.current ?? 14.2).toFixed(1)}%`, status: crisis ? 'warning' : 'nominal' },
    ingress:    { label: 'Ingress', sources: ['Syngenta KB', 'DONKI', 'InSight', 'NASA POWER'] },
  }
}

// ── Derive PodProbes from zones (liveness from is_alive/fire_detected) ──

const ZONE_CROPS = { A: ['Soybean', 'Lentil'], B: ['Potato', 'Wheat'], C: ['Tomato', 'Spinach'], D: ['Basil', 'Microgreens'] }

function derivePodProbes(zones) {
  if (!zones) return null

  const probes = {}
  for (const zone of zones) {
    const crops = ZONE_CROPS[zone.id] || []
    const alive = zone._isAlive !== false
    const fire = zone._fireDetected === true

    for (const crop of crops) {
      probes[crop] = {
        liveness: fire ? 'degraded' : alive ? 'passing' : 'degraded',
        livenessAge: alive ? '30s' : '0s',
        readiness: 'notReady', // Backend doesn't serve crop growth stage
        readinessDetail: '—',
        restarts: 0,
        startedSol: 0,
      }
    }
  }
  return probes
}

export function useEdenAPI(mockZones) {
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const poll = useCallback(async () => {
    try {
      abortRef.current?.abort()
      abortRef.current = new AbortController()

      const done = startTimer(apiLog, 'api_poll')
      const res = await fetch(`${API_BASE}/api/state`, {
        signal: abortRef.current.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const json = await res.json()
      done({ zones: json.zones?.length ?? 0, decisions: json.decisions?.length ?? 0 })
      setData(json)
      if (!connected) apiLog.info({ msg: 'api_connected', endpoint: API_BASE })
      setConnected(true)
      setError(null)
    } catch (err) {
      if (err.name !== 'AbortError') {
        if (connected) apiLog.warn({ msg: 'api_disconnected', error: err.message, endpoint: API_BASE })
        setConnected(false)
        setError(err.message)
      }
    }
  }, [connected])

  useEffect(() => {
    poll()
    const iv = setInterval(poll, POLL_INTERVAL)
    return () => {
      clearInterval(iv)
      abortRef.current?.abort()
    }
  }, [poll])

  // Derive dashboard-compatible data from API response
  const zones = data ? overlayZones(mockZones, data.zones) : null
  const decisions = data ? mapDecisionsToLog(data.decisions) : null
  const flightRules = data ? mapFlightRules(data.flight_rules) : null
  const crew = data ? mapCrew(data.crew) : null

  // Derive higher-level structures from backend data
  const mars = data?.mars ?? null
  const resources = data?.resources ?? null
  const status = data?.status ?? null
  const clusterStatus = data ? deriveClusterStatus(status, zones, mars, flightRules) : null
  const resourceFlow = data ? deriveResourceFlow(resources, mars) : null
  const podProbes = data ? derivePodProbes(zones) : null

  return {
    connected,
    error,
    raw: data,
    zones,
    decisions,
    sol: data?.sol ?? null,
    status,
    mars,
    resources,
    flightRules,
    nutrition: data?.nutrition ?? null,
    crew,
    // Derived structures for ClusterView
    clusterStatus,
    resourceFlow,
    podProbes,
  }
}
