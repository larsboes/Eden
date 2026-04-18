/**
 * useEdenSSE — Real-time SSE connection to EDEN backend.
 *
 * Connects to /api/stream, dispatches 30+ event types to handlers,
 * auto-reconnects on disconnect, catches up via /api/events.
 *
 * This is THE integration layer. Everything real-time flows through here.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { sseLog } from '../lib/logger'

const API_BASE = import.meta.env.VITE_EDEN_API || 'http://localhost:8000'
const RECONNECT_DELAY = 3000
const CATCHUP_LIMIT = 100

// Zone ID mapping (backend → dashboard)
const ZONE_MAP = {
  'zone-protein': 'A',
  'zone-carb': 'B',
  'zone-vitamin': 'C',
  'zone-support': 'D',
}

/**
 * @param {Object} handlers - Map of event type → handler function
 *   e.g. { zone_state: (data) => ..., agent_token: (data) => ... }
 * @returns {{ connected, reconnecting, eventCount, lastEvent }}
 */
export function useEdenSSE(handlers = {}) {
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [eventCount, setEventCount] = useState(0)
  const [lastEvent, setLastEvent] = useState(null)
  const handlersRef = useRef(handlers)
  const sourceRef = useRef(null)
  const reconnectTimer = useRef(null)
  const lastSeqRef = useRef(0)

  // Keep handlers ref current without re-triggering effect
  handlersRef.current = handlers

  const dispatch = useCallback((eventType, data) => {
    const handler = handlersRef.current[eventType]
    if (handler) handler(data)
    const wildcard = handlersRef.current['*']
    if (wildcard) wildcard(eventType, data)
    setEventCount(c => c + 1)
    setLastEvent({ type: eventType, timestamp: Date.now() })
    // Log high-value events at info, everything else at debug
    const highValue = ['alert', 'chaos', 'crew_escalation', 'council_consensus', 'council_start', 'council_vote', 'council_complete', 'agent_started', 'flight_rule', 'command']
    if (highValue.includes(eventType)) {
      sseLog.info({ msg: 'sse_event', event_type: eventType, zone_id: data?.zone_id })
    } else {
      sseLog.debug({ msg: 'sse_event', event_type: eventType })
    }
  }, [])

  const catchUp = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/events?limit=${CATCHUP_LIMIT}`)
      if (!res.ok) return
      const events = await res.json()
      let replayed = 0
      for (const evt of events) {
        if (evt.seq > lastSeqRef.current) {
          lastSeqRef.current = evt.seq
          dispatch(evt.type, evt.data)
          replayed++
        }
      }
      if (replayed > 0) sseLog.info({ msg: 'sse_catchup_complete', events_replayed: replayed, total_available: events.length })
    } catch {
      sseLog.warn({ msg: 'sse_catchup_failed' })
    }
  }, [dispatch])

  const connect = useCallback(() => {
    // Clean up existing connection
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    try {
      const source = new EventSource(`${API_BASE}/api/stream`)
      sourceRef.current = source

      source.onopen = () => {
        sseLog.info({ msg: 'sse_connected', endpoint: `${API_BASE}/api/stream` })
        setConnected(true)
        setReconnecting(false)
        catchUp() // Get events we missed
      }

      source.onerror = () => {
        sseLog.warn({ msg: 'sse_disconnected', reconnect_delay_ms: RECONNECT_DELAY })
        setConnected(false)
        source.close()
        sourceRef.current = null
        setReconnecting(true)
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
      }

      // Register handlers for all known event types
      const EVENT_TYPES = [
        // Reconciliation loop
        'cycle_start', 'zone_state', 'flight_rule', 'command',
        'telemetry', 'delta', 'model_invocation', 'decision',
        'alert', 'feedback', 'cycle_complete',
        // Council lifecycle (replaces parliament)
        'council_start', 'council_vote', 'council_consensus', 'council_complete',
        // Parliament lifecycle (legacy, kept for backwards compat)
        'parliament_start', 'round1_start', 'agent_started',
        'agent_proposal', 'round1_complete', 'deliberation_start',
        'deliberation_response', 'deliberation_complete',
        'coordinator_start', 'coordinator_resolution', 'parliament_skipped',
        // Crew escalations
        'crew_escalation', 'escalation_acknowledged', 'escalation_resolved',
        // Live token streaming
        'agent_token', 'agent_reasoning', 'agent_tool_call',
        'agent_complete', 'strands_agent_complete', 'tool_use',
        // Retrospective + shadow rules
        'retrospective', 'retrospective_complete', 'retrospective_triggered',
        'shadow_rule',
        // External data
        'nasa_data', 'sensor_reading', 'chaos',
        // System
        'ping',
      ]

      for (const type of EVENT_TYPES) {
        source.addEventListener(type, (e) => {
          if (type === 'ping') return // Ignore keepalives
          try {
            const data = e.data ? JSON.parse(e.data) : {}
            if (e.lastEventId) {
              lastSeqRef.current = parseInt(e.lastEventId, 10) || lastSeqRef.current
            }
            dispatch(type, data)
          } catch {
            // Malformed event, skip
          }
        })
      }
    } catch (err) {
      sseLog.error({ msg: 'sse_connection_failed', error: err?.message })
      setReconnecting(true)
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }
  }, [dispatch, catchUp])

  useEffect(() => {
    connect()
    return () => {
      if (sourceRef.current) sourceRef.current.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [connect])

  return { connected, reconnecting, eventCount, lastEvent }
}

/**
 * useAgentTokens — Manages live agent token streaming state.
 *
 * Returns an object of { [agentName]: { partial, complete, toolCall, active } }
 * Feed this the agent_token/agent_complete/agent_tool_call events from useEdenSSE.
 */
export function useAgentTokens() {
  const [agents, setAgents] = useState({})
  const [parliamentRound, setParliamentRound] = useState(null)

  const handlers = {
    // ── Old parliament events (AgentTeam) ──
    round1_start: (data) => {
      setParliamentRound(1)
      setAgents({})
    },
    agent_started: (data) => {
      const name = data.agent_name
      const emoji = data.emoji || ''
      setAgents(prev => ({
        ...prev,
        [name]: { partial: '', complete: false, toolCall: null, active: true, zone_id: data.zone_id, emoji },
      }))
    },
    agent_token: (data) => {
      setAgents(prev => ({
        ...prev,
        [data.agent_name]: {
          ...prev[data.agent_name],
          partial: data.partial || (prev[data.agent_name]?.partial || '') + data.token,
          active: true,
        },
      }))
    },
    agent_tool_call: (data) => {
      setAgents(prev => ({
        ...prev,
        [data.agent_name]: { ...prev[data.agent_name], toolCall: data.tool_name },
      }))
    },
    agent_complete: (data) => {
      setAgents(prev => ({
        ...prev,
        [data.agent_name]: {
          ...prev[data.agent_name],
          partial: data.full_text || prev[data.agent_name]?.partial || '',
          complete: true, active: false, toolCall: null,
        },
      }))
    },
    deliberation_start: () => setParliamentRound(2),
    coordinator_start: () => setParliamentRound(3),
    coordinator_resolution: () => setParliamentRound(null),

    // ── Council events (new quorum system) ──
    council_start: (data) => {
      setParliamentRound('council')
      // Keep previous votes dimmed until new ones arrive
      setAgents(prev => {
        const dimmed = {}
        for (const [name, agent] of Object.entries(prev)) {
          if (agent.complete) {
            dimmed[name] = { ...agent, active: false, stale: true }
          }
        }
        return dimmed
      })
    },
    council_vote: (data) => {
      const name = data.member || 'Council'
      const emoji = data.emoji || ''
      const summaries = data.decision_summaries || []
      const assessment = data.assessment || ''
      const details = summaries.length
        ? `${summaries.join(' | ')}\n— ${assessment}`
        : assessment || `${data.decisions || 0} decisions (${((data.confidence || 0) * 100).toFixed(0)}% confidence)`
      setAgents(prev => ({
        ...prev,
        [name]: {
          partial: details,
          complete: true,
          active: false,
          toolCall: null,
          emoji,
          zone_id: 'global',
          decisions: data.decisions || 0,
          confidence: data.confidence || 0,
        },
      }))
    },
    council_consensus: (data) => {
      const label = data.zone_id === 'global' ? 'CONSENSUS' : data.zone_id
      setAgents(prev => ({
        ...prev,
        [`VOTE:${label}:${Date.now()}`]: {
          partial: `[${(data.reasoning || '').slice(0, 200)}] → ${data.action || ''}`,
          complete: true,
          active: false,
          toolCall: null,
          zone_id: data.zone_id,
          severity: data.severity,
        },
      }))
    },
    council_complete: (data) => {
      // Keep votes visible — don't null out the round immediately
      // They'll be replaced when next council_start fires
      setTimeout(() => {
        setParliamentRound(prev => prev === 'council' ? null : prev)
      }, 5000)
    },
    // Live tool use streaming — shows which tools agents are calling
    tool_use: (data) => {
      const agentName = data.agent_name
      if (!agentName) return
      const toolName = data.tool || 'unknown'
      setAgents(prev => {
        const existing = prev[agentName]
        if (!existing || existing.complete) return prev
        return {
          ...prev,
          [agentName]: {
            ...existing,
            toolCall: toolName,
            partial: `🔧 ${toolName}${data.args?.zone_id ? ` (${data.args.zone_id})` : ''}`,
          },
        }
      })
    },
  }

  return { agents, parliamentRound, handlers }
}

/**
 * useSSEEvents — Accumulates SSE events into a rolling buffer for EventStream.
 *
 * Maps raw SSE events to kubectl-style { age, type, reason, object, message } format.
 */
export function useSSEEvents(maxEvents = 50) {
  const [events, setEvents] = useState([])
  const startTimeRef = useRef(Date.now())

  const formatAge = (timestamp) => {
    const delta = Math.round((Date.now() - (timestamp || Date.now())) / 1000)
    if (delta < 60) return `${delta}s`
    if (delta < 3600) return `${Math.round(delta / 60)}m`
    return `${Math.round(delta / 3600)}h`
  }

  const mapEvent = useCallback((eventType, data) => {
    // Map SSE event types to kubectl-style event format
    const mappings = {
      flight_rule: () => ({
        type: 'Normal', reason: 'AdmissionCtrl',
        object: `rule/${data.rule_id || 'FR-?'}`,
        message: data.reasoning || data.action || 'Rule triggered',
      }),
      alert: () => ({
        type: 'Warning', reason: data.rule_id ? 'FlightRule' : 'Alert',
        object: `${data.zone_id ? `node/${data.zone_id}` : 'cluster/eden'}`,
        message: data.reasoning || 'Alert triggered',
      }),
      zone_state: () => ({
        type: 'Normal', reason: 'LivenessProbe',
        object: `pod/${data.zone_id || 'unknown'}`,
        message: `Sensors nominal. Temp ${data.temperature}C, Hum ${data.humidity}%`,
      }),
      cycle_complete: () => ({
        type: 'Normal', reason: 'Reconciled',
        object: 'cluster/eden',
        message: `${data.total_decisions || 0} decisions. Synced.`,
      }),
      command: () => ({
        type: 'Normal', reason: 'Command',
        object: `device/${data.device || 'actuator'}`,
        message: `${data.action || 'command sent'}`,
      }),
      chaos: () => ({
        type: 'Warning', reason: 'ChaosInjected',
        object: 'cluster/eden',
        message: `${data.event_type || eventType}: ${data.description || 'injected'}`,
      }),
      coordinator_resolution: () => ({
        type: 'Normal', reason: 'CouncilVote',
        object: 'parliament/coordinator',
        message: (data.reasoning || '').slice(0, 120),
      }),
      council_consensus: () => ({
        type: 'Normal', reason: 'CouncilConsensus',
        object: `council/${data.zone_id || 'global'}`,
        message: (data.reasoning || '').slice(0, 120),
      }),
      crew_escalation: () => ({
        type: 'Warning', reason: 'CrewEscalation',
        object: `node/${data.zone_id || 'global'}`,
        message: `CREW NEEDED: ${data.task || 'intervention required'} [${(data.urgency || 'high').toUpperCase()}]`,
      }),
      escalation_resolved: () => ({
        type: 'Normal', reason: 'EscalationResolved',
        object: `node/${data.zone_id || 'global'}`,
        message: `Escalation resolved: ${data.task || 'issue fixed'}`,
      }),
      retrospective: () => ({
        type: 'Normal', reason: 'Retrospective',
        object: `rules/${data.action?.split(' ')[1] || 'analysis'}`,
        message: (data.reasoning || '').slice(0, 120),
      }),
      shadow_rule: () => ({
        type: 'Normal', reason: 'ShadowEval',
        object: `rule/${data.action?.split(' ')[1] || 'candidate'}`,
        message: (data.reasoning || '').slice(0, 120),
      }),
      council_vote: () => ({
        type: 'Normal', reason: 'CouncilVote',
        object: `council/${data.member || '?'}`,
        message: `${data.member} voted: ${data.decisions || 0} decisions (confidence: ${(data.confidence || 0).toFixed(1)})`,
      }),
      agent_proposal: () => ({
        type: 'Normal', reason: 'AgentProposal',
        object: `agent/${data.agent_name || '?'}`,
        message: (data.reasoning || data.action || '').slice(0, 100),
      }),
      feedback: () => ({
        type: 'Normal', reason: 'ClosedLoop',
        object: `zone/${data.zone_id || 'global'}`,
        message: JSON.stringify(data.improvements || data).slice(0, 100),
      }),
      delta: () => ({
        type: data.in_range ? 'Normal' : 'Warning',
        reason: data.in_range ? 'InRange' : 'OutOfRange',
        object: `node/${ZONE_MAP[data.zone_id] || data.zone_id || '?'}`,
        message: data.in_range ? 'Desired state matches actual' : `Deltas: ${JSON.stringify(data.deltas || {}).slice(0, 80)}`,
      }),
    }

    const mapper = mappings[eventType]
    if (!mapper) return null

    const mapped = mapper()
    return {
      age: formatAge(data.timestamp ? data.timestamp * 1000 : Date.now()),
      _timestamp: Date.now(),
      ...mapped,
    }
  }, [])

  const handleEvent = useCallback((eventType, data) => {
    const evt = mapEvent(eventType, data)
    if (!evt) return
    setEvents(prev => [evt, ...prev].slice(0, maxEvents))
  }, [mapEvent, maxEvents])

  // SSE handler map — pass this to useEdenSSE handlers
  const handlers = {
    flight_rule: (d) => handleEvent('flight_rule', d),
    alert: (d) => handleEvent('alert', d),
    zone_state: (d) => handleEvent('zone_state', d),
    cycle_complete: (d) => handleEvent('cycle_complete', d),
    command: (d) => handleEvent('command', d),
    chaos: (d) => handleEvent('chaos', d),
    coordinator_resolution: (d) => handleEvent('coordinator_resolution', d),
    agent_proposal: (d) => handleEvent('agent_proposal', d),
    feedback: (d) => handleEvent('feedback', d),
    delta: (d) => handleEvent('delta', d),
    council_consensus: (d) => handleEvent('council_consensus', d),
    crew_escalation: (d) => handleEvent('crew_escalation', d),
    escalation_resolved: (d) => handleEvent('escalation_resolved', d),
    retrospective: (d) => handleEvent('retrospective', d),
    shadow_rule: (d) => handleEvent('shadow_rule', d),
    council_vote: (d) => handleEvent('council_vote', d),
  }

  return { events, handlers }
}
