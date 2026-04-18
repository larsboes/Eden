# EDEN Dashboard V3 — Frontend-Backend Integration Design

> V1 was the cinematic view. V2 was the K8s ArgoCD tree. V3 makes them real.
> This document bridges the gap between Bryan's backend and the dashboard.

---

## The Problem

The backend is rich: SSE stream with 30+ event types, 15 REST endpoints, agent token streaming, Monte Carlo simulation, chaos injection, closed-loop feedback. The frontend consumes almost none of it. The demo runs on mock data and a scripted timer.

V3 changes this. Every backend capability maps to a frontend visualization.

---

## Architecture: 3-Layer Data Flow

```
                  TRANSPORT LAYER
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  useEdenSSE  │  │ useEdenPoll  │  │   useDemo    │
  │              │  │              │  │              │
  │ EventSource  │  │ /api/state   │  │ 42s script   │
  │ 30+ events   │  │ every 3s     │  │ mock data    │
  │ REAL-TIME    │  │ FALLBACK     │  │ OFFLINE      │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │  priority: 1     │  priority: 2    │  priority: 3
         └─────────┬────────┴─────────┬───────┘
                   ▼                  ▼
              MERGE LAYER (App.jsx)
  ┌──────────────────────────────────────────────────┐
  │  SSE connected + data? → use SSE                  │
  │  API connected + data? → use API poll              │
  │  Neither?              → use mock + demo timer     │
  └──────────────────────────────────────────────────┘
                          │
                   COMPONENT LAYER
  ┌─────────┬──────────┬───────────┬──────────┬──────┐
  │Cluster  │Agent     │Event      │Resource  │Chaos │
  │View     │Stream    │Stream     │Flow      │Panel │
  └─────────┴──────────┴───────────┴──────────┴──────┘
```

Components never know their data source. Same props, same rendering.

---

## Zone Model Alignment (DONE)

### Before (broken)
- Backend: 3 zones (`sim-alpha`, `sim-beta`, `sim-gamma`), 1 crop each
- Frontend: 4 zones (`A`/`B`/`C`/`D`), 2 crops each
- MemorySensorAdapter: 4 zones (`zone-protein/carb/vitamin/support`) — not connected to crops

### After (fixed)
- Backend `__main__.py`: 4 zones, 8 crops, matching dashboard layout:

| Zone ID | Dashboard | Crops | Temp Range |
|---------|-----------|-------|------------|
| `zone-protein` | A: PROTEIN | Soybean, Lentil | 20-28C |
| `zone-carb` | B: CARB | Potato, Wheat | 15-25C |
| `zone-vitamin` | C: VITAMIN | Tomato, Spinach | 18-27C |
| `zone-support` | D: SUPPORT | Basil, Microgreens | 20-26C |

- DesiredState seeded for all 4 zones
- CropProfile for all 8 crops with real agronomic values
- `zone_crops` now `dict[str, list[str]]` — FLORA speaks for both crops
- `useEdenAPI` ZONE_MAP matches backend IDs

---

## Hook Architecture

### useEdenSSE (NEW — the foundation)

```
eden-dashboard/src/hooks/useEdenSSE.js
```

Three exported hooks:

#### `useEdenSSE(handlers)` — SSE connection manager
- Connects to `/api/stream` via EventSource
- Registers listeners for all 30+ event types
- Auto-reconnects on disconnect (3s delay)
- Catches up missed events via `/api/events?limit=100`
- Returns: `{ connected, reconnecting, eventCount, lastEvent }`
- Accepts `handlers` map: `{ event_type: (data) => void, '*': (type, data) => void }`

#### `useAgentTokens()` — Parliament token streaming state
- Tracks per-agent typing state: `{ [agentName]: { partial, complete, toolCall, active } }`
- Tracks parliament round (1/2/3/null)
- Handles: `round1_start`, `agent_started`, `agent_token`, `agent_tool_call`, `agent_complete`, `deliberation_start`, `coordinator_start`, `coordinator_resolution`
- Returns: `{ agents, parliamentRound, handlers }`

#### `useSSEEvents(maxEvents)` — Event stream accumulator
- Converts raw SSE events to kubectl-style format: `{ age, type, reason, object, message }`
- Rolling buffer, newest first
- Maps: `flight_rule` → AdmissionCtrl, `zone_state` → LivenessProbe, `cycle_complete` → Reconciled, `chaos` → ChaosInjected, `delta` → InRange/OutOfRange, etc.
- Returns: `{ events, handlers }`

### useEdenAPI (EXISTING — enhanced)
- Polls `/api/state` every 3s (fallback when SSE is down)
- Fixed ZONE_MAP to include both new and legacy zone IDs
- Returns overlay of live sensor data onto mock zone structure

### useDemo (EXISTING — unchanged)
- 42s scripted demo loop
- Works identically when backend is offline
- Manual state override via header buttons

---

## Component Integration Map

### What changed vs V2:

| Component | V2 (mock only) | V3 (live integration) |
|-----------|----------------|----------------------|
| **Agent Stream** (hero text) | Static mock log[0] | Live `agent_token` streaming when SSE connected |
| **EventStream** | Hardcoded EVENTS_NOMINAL/CRISIS | SSE events → kubectl format, rolling buffer |
| **ResourceFlow** | RESOURCE_FLOW mock dict | Backend ResourceTracker (same shape!) via `/api/state` |
| **ClusterBox** | Hardcoded CLUSTER_STATUS | Real zone count, flight rules count from backend |
| **Flight Rules panel** | Mock FLIGHT_RULES array | Live `/api/state` flight_rules + SSE `flight_rule` events |
| **Crew Nutrition** | Mock CREW array | Live `/api/nutrition` via useEdenAPI |
| **Council Log** | Mock COUNCIL_LOG | Live `/api/decisions` via useEdenAPI |
| **CinematicDashboard** | No events | EventStream component with live SSE events |

### New components:

| Component | Location | What it does |
|-----------|----------|-------------|
| **LiveAgentStream** | ClusterView.jsx | Grid of agent cards with live typing animation |
| **ChaosButton** | App.jsx | POST to `/api/chaos/{type}`, inline in demo bar |

---

## SSE Event → Frontend Component Map

Every backend SSE event has a destination:

### Reconciliation Loop Events
| SSE Event | Frontend Target | What Happens |
|-----------|----------------|-------------|
| `cycle_start` | (internal) | Log cycle beginning |
| `zone_state` | useSSEEvents → EventStream | "LivenessProbe pod/zone-protein Sensors nominal" |
| `flight_rule` | useSSEEvents → EventStream | "AdmissionCtrl rule/FR-T-001 ADMITTED" |
| `command` | useSSEEvents → EventStream | "Command device/fan activated" |
| `delta` | useSSEEvents → EventStream | "OutOfRange node/B Deltas: {temperature: +2.3}" |
| `feedback` | useSSEEvents → EventStream | "ClosedLoop zone/zone-protein temperature improved" |
| `cycle_complete` | useSSEEvents → EventStream | "Reconciled cluster/eden N decisions. Synced." |
| `alert` | useSSEEvents → EventStream | "Alert cluster/eden CRITICAL" |

### Parliament Lifecycle Events
| SSE Event | Frontend Target | What Happens |
|-----------|----------------|-------------|
| `parliament_start` | (logged) | Parliament invoked |
| `round1_start` | useAgentTokens → LiveAgentStream | Reset agent grid, show "ROUND 1/3" |
| `agent_started` | useAgentTokens → LiveAgentStream | Agent card activates (pulsing dot) |
| `agent_token` | useAgentTokens → LiveAgentStream | Text appends word-by-word in agent card |
| `agent_tool_call` | useAgentTokens → LiveAgentStream | Tool badge appears: "query_syngenta_kb" |
| `agent_complete` | useAgentTokens → LiveAgentStream | Stop animation, show "DONE" |
| `deliberation_start` | useAgentTokens | Round indicator: "ROUND 2/3" |
| `deliberation_response` | useSSEEvents → EventStream | Agent deliberation logged |
| `coordinator_start` | useAgentTokens | Round indicator: "ROUND 3/3" |
| `coordinator_resolution` | useSSEEvents → EventStream | "CouncilVote parliament/coordinator ..." |

### External Events
| SSE Event | Frontend Target | What Happens |
|-----------|----------------|-------------|
| `chaos` | useSSEEvents → EventStream | "ChaosInjected cluster/eden dust_storm" |
| `nasa_data` | (logged) | NASA data refresh |

---

## Chaos Injection

Buttons in the demo bar (visible only when backend connected):

| Button | Endpoint | Effect |
|--------|----------|--------|
| Dust Storm | `POST /api/chaos/dust_storm` | Solar drops to 15%, triggers parliament |
| Fire | `POST /api/chaos/fire` | Fire detected, flight rules trigger emergency |
| Sensor Fail | `POST /api/chaos/sensor_failure` | Temperature sensor dies |
| Water Block | `POST /api/chaos/water_line_blocked` | Water supply cut |

Each button flashes "INJECTED" for 2s after firing. Events cascade through SSE:
1. `chaos` event appears in EventStream
2. Flight rules fire → `flight_rule` events
3. Parliament convenes → `agent_token` streaming begins
4. Resolution → `coordinator_resolution` event

---

## Data Shape Compatibility

### Resources — PERFECT MATCH
Backend `ResourceTracker.get_state()`:
```json
{ "water": { "current": 340.0, "max": 600.0, "unit": "L", "rate": "+20 L/sol surplus", "label": "Clean Water Reserve" } }
```

Frontend mock `RESOURCES`:
```json
{ "water": { "current": 340, "max": 600, "unit": "L", "rate": "+20 L/sol surplus", "label": "Clean Water Reserve" } }
```

Identical. No mapping needed.

### Zones — MAPPED
Backend `ZoneState.to_dict()`:
```json
{ "zone_id": "zone-protein", "temperature": 22.3, "humidity": 63.0, "light": 400.0, ... }
```

Frontend overlay in `useEdenAPI.overlayZones()` merges live sensor values onto mock zone structure (which has crops, BBCH, icons, etc.).

### Decisions — MAPPED
Backend `AgentDecision.to_dict()`:
```json
{ "timestamp": 1710812350.456, "agent_name": "SENTINEL", "severity": "high", "reasoning": "...", "action": "...", "zone_id": "global", "tier": 2 }
```

`useEdenAPI.mapDecisionsToLog()` converts to: `{ time, agent, msg, color, type, zone, tier }`.

---

## Demo Flow: What Judges See

### Backend Running (live mode)
1. Dashboard loads, SSE connects, green indicator in header
2. Zones update every 30s from reconciler via SSE
3. Events stream in kubectl format — real reconciliation events
4. Judge clicks "Dust Storm" → chaos injects
5. Flight rules fire immediately (SSE events)
6. Parliament convenes — 14 agent cards appear, typing word-by-word
7. Agents call Syngenta KB mid-reasoning (tool badges flash)
8. Coordinator consensus appears
9. Events show the full cascade

### Backend Offline (demo mode)
1. Dashboard loads, SSE fails silently, demo bar shows
2. Click "DEMO" → 42s scripted loop
3. Mock data drives all components identically
4. No chaos buttons (backend required)

### Hybrid (partial connection)
1. Backend running but slow/intermittent
2. SSE connected → live events flow
3. SSE disconnects → auto-reconnect in 3s, catches up
4. API poll continues as fallback for zone data
5. Demo timer can still be used for scripted narrative

---

## Implementation Priority

### DONE
- [x] Backend zone model: 4 zones, 8 crops, matching dashboard
- [x] useEdenSSE hook: EventSource + reconnect + catchup
- [x] useAgentTokens: per-agent streaming state
- [x] useSSEEvents: SSE → kubectl format event accumulator
- [x] LiveAgentStream component: agent grid with typing animation
- [x] ChaosButton component: POST chaos injection
- [x] EventStream in CinematicDashboard: live events in both views
- [x] Zone ID mapping fix in useEdenAPI
- [x] CSS blink animation for typing cursor

### TODO (P2)
- [ ] Simulation trigger: button + POST `/api/simulate/{type}` + render results in CanaryDeployment
- [ ] Parliament round visualization: 3-step progress indicator as standalone element
- [ ] Feedback panel: before/after values from `feedback` SSE events
- [ ] Dynamic cluster status: derive from real zone health instead of CLUSTER_STATUS mock

### TODO (P3)
- [ ] Mars conditions display: TBD (awaiting design decision)
- [ ] Resource flow from backend: map ResourceTracker to flow diagram (shapes already match)
- [ ] Agent color scheme from `/api/agents` endpoint

---

## Files Modified

### Backend
- `eden/__main__.py` — 4 zones, 8 crops, correct zone IDs and desired states
- `eden/application/agent.py` — zone_crops supports list[str], `_crop_name()` helper

### Frontend
- `eden-dashboard/src/hooks/useEdenSSE.js` — NEW: SSE hook + agent tokens + event accumulator
- `eden-dashboard/src/hooks/useEdenAPI.js` — Updated zone ID mapping
- `eden-dashboard/src/App.jsx` — SSE integration, chaos buttons, EventStream in cinematic view
- `eden-dashboard/src/components/cluster/ClusterView.jsx` — LiveAgentStream, SSE events, live event fallback
- `eden-dashboard/src/index.css` — blink keyframe animation
