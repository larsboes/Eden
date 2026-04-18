# EDEN Frontend / Dashboard Developer Guide

Build a dashboard that visualizes the EDEN Martian greenhouse agent parliament in real time.

---

## API Base URL

| Environment | URL |
|-------------|-----|
| Local dev | `http://localhost:8000` |
| EC2 | `http://<EC2_IP>:8000` |

CORS is wide open (`*`) for the hackathon — any origin is allowed.

---

## Running the Backend

```bash
# Full system: reconciler + API + simulated sensors (RECOMMENDED)
python -m eden

# The API server starts automatically on port 8000.
# The reconciler runs in a background thread.
# Simulated sensors publish fake data if EDEN_SIMULATE=true.

# Override port/host:
EDEN_API_PORT=3001 EDEN_API_HOST=0.0.0.0 python -m eden
```

---

## API Endpoints

### 1. `GET /api/zones` — All Zone States + Health

Returns all greenhouse zones with current sensor readings, desired state, and computed health.

**Response:**
```json
[
  {
    "zone_id": "sim-alpha",
    "temperature": 24.5,
    "humidity": 62.0,
    "pressure": 700.0,
    "light": 450.0,
    "water_level": 85.0,
    "fire_detected": false,
    "last_updated": 1710812345.123,
    "is_alive": true,
    "source": "simulated",
    "health": "green",
    "desired_state": {
      "zone_id": "sim-alpha",
      "temp_min": 18.0,
      "temp_max": 28.0,
      "humidity_min": 50.0,
      "humidity_max": 80.0,
      "light_hours": 16.0,
      "soil_moisture_min": 40.0,
      "soil_moisture_max": 70.0,
      "water_budget_liters_per_day": 5.0
    }
  }
]
```

**Health values:** `green` (all nominal), `yellow` (sensor out of desired range), `red` (fire/dead/critical)

---

### 2. `GET /api/zones/{zone_id}` — Zone Detail + Trends

Returns current state, desired state, last hour of telemetry, and trend data (min/max/avg per sensor).

**Response:**
```json
{
  "zone_id": "sim-alpha",
  "current_state": { ... },
  "desired_state": { ... },
  "recent_telemetry": [ ... ],
  "trends": {
    "temperature": {"min": 20.1, "max": 26.3, "avg": 23.2, "count": 120},
    "humidity": {"min": 55.0, "max": 72.0, "avg": 63.5, "count": 120}
  }
}
```

---

### 3. `GET /api/zones/{zone_id}/telemetry` — Raw Telemetry

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `since` | float | last hour | Unix timestamp |
| `limit` | int | 500 | Max readings (1–5000) |
| `sensor_type` | string | null | Filter: `temperature`, `humidity`, etc. |

---

### 4. `GET /api/decisions` — Parliament Debate Log

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max decisions (1–500) |
| `since` | float | 0.0 | Only after this timestamp |
| `agent_name` | string | null | Filter by agent: `SENTINEL`, `FLORA`, etc. |
| `zone_id` | string | null | Filter by zone |
| `tier` | int | null | Filter by tier: `0` (flight rules), `1` (local), `2` (cloud) |

**Response:**
```json
[
  {
    "timestamp": 1710812350.456,
    "agent_name": "COORDINATOR",
    "severity": "high",
    "reasoning": "1. IMMEDIATE: Fan Bay Alpha to 80%...",
    "action": "CONSENSUS_RESOLUTION",
    "result": "resolved",
    "zone_id": "global",
    "tier": 2
  }
]
```

---

### 5. `GET /api/decisions/latest-resolution` — Latest Consensus

Returns the most recent COORDINATOR consensus resolution. `null` if none yet.

---

### 6. `GET /api/agents` — Agent Registry

Returns all 13 agents with their domain, color, and icon. Use this to build the legend/key for the parliament view.

**Response:**
```json
[
  {"name": "SENTINEL", "domain": "Safety & Threats", "color": "#E53E3E", "icon": "shield"},
  {"name": "FLORA", "domain": "Plant Voice (per zone)", "color": "#38A169", "icon": "leaf"},
  ...
  {"name": "COORDINATOR", "domain": "Consensus Resolution", "color": "#FFFFFF", "icon": "gavel"}
]
```

---

### 7. `GET /api/nutrition` — Crew Nutritional Status

```json
{
  "status": {
    "crew": [{"name": "Cmdr. Chen", "daily_kcal_target": 2500, ...}],
    "sol": 247,
    "total_daily_kcal_needed": 10000
  },
  "deficiency_risks": [{"nutrient": "vitamin_c", "risk_level": "medium", "days_until_critical": 67}],
  "mission_projection": {"food_security_score": 0.78, "days_remaining": 203}
}
```

---

### 8. `GET /api/mars` — Mars Conditions

```json
{
  "exterior_temp": -63.0,
  "dome_temp": 22.0,
  "pressure_hpa": 6.1,
  "solar_irradiance": 590.0,
  "dust_opacity": 0.3,
  "sol": 247,
  "storm_active": false,
  "radiation_alert": false
}
```

---

### 9. `GET /api/flight-rules` — All Flight Rules

```json
{
  "rules": [
    {"rule_id": "FR-T-001", "sensor_type": "temperature", "condition": "lt", "threshold": 5.0, ...},
    ...
  ],
  "count": 17
}
```

---

### 10. `GET /api/resources` — Resource Budgets

```json
{
  "water": {"water_liters": 500, "nutrient_level": 80, "current_capacity": 1000},
  "energy": {"solar_capacity_kw": 50, "current_efficiency": 0.85, ...},
  "gas_exchange": {"greenhouse_co2_ppm": 800, "greenhouse_o2_pct": 21.0, ...}
}
```

Returns `null` for budgets not yet initialized.

---

### 11. `GET /api/status` — System Health

```json
{
  "reconciler_running": true,
  "model_available": true,
  "model_tier": "bedrock",
  "mqtt_connected": true,
  "zones_count": 3,
  "uptime": 3600.5,
  "event_bus_subscribers": 2,
  "total_events": 1547,
  "current_sol": 247
}
```

---

### 12. `GET /api/feedback` — Closed-Loop Results

```json
[
  {"zone_id": "alpha", "improvements": {"temperature": {"before": 32.5, "after": 26.0, "action": "cooling"}}}
]
```

---

### 13. `POST /api/chaos/{event_type}` — Inject Failure

| Event | Description |
|-------|-------------|
| `dust_storm` | Mars dust storm, cuts solar to 15% |
| `fire` | Fire detected in a zone |
| `comms_lost` | 24h communication blackout |
| `sensor_failure` | Temperature sensor dies |
| `water_line_blocked` | Water supply blocked |

When simulated sensors are running, chaos events are ALSO injected into the sensor simulation (temperature spikes, fire flags, etc.).

---

### 14. `GET /api/events` — Event History

Recent events from the EventBus. Great for catching up when a client connects.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `event_type` | string | null | Filter by type |
| `limit` | int | 50 | Max events |

---

### 15. `GET /api/stream` — SSE Real-Time Stream (THE MAIN EVENT)

Server-Sent Events stream. Connect with `EventSource` and receive live updates as they happen.

**Optional filter:** `?types=decision,alert,chaos` (comma-separated)

```javascript
const source = new EventSource("http://localhost:8000/api/stream");

// Or filtered:
// const source = new EventSource("http://localhost:8000/api/stream?types=decision,alert,chaos");

source.addEventListener("cycle_start", (e) => {
  const data = JSON.parse(e.data);
  console.log(`Reconciliation cycle starting — Sol ${data.sol}, ${data.zone_count} zones`);
});

source.addEventListener("zone_state", (e) => {
  const data = JSON.parse(e.data);
  // Zone sensor data after Mars transform — update zone cards
});

source.addEventListener("flight_rule", (e) => {
  const data = JSON.parse(e.data);
  // Tier 0 deterministic rule fired — show immediately
});

source.addEventListener("command", (e) => {
  const data = JSON.parse(e.data);
  // Actuator command sent — show device animation
});

source.addEventListener("telemetry", (e) => {
  const data = JSON.parse(e.data);
  // Raw sensor values — update graphs
});

source.addEventListener("delta", (e) => {
  const data = JSON.parse(e.data);
  // Zone deviation from desired — color health indicator
});

source.addEventListener("alert", (e) => {
  const data = JSON.parse(e.data);
  // CRITICAL/HIGH severity event — flash red banner
});

source.addEventListener("round1_start", (e) => {
  const data = JSON.parse(e.data);
  console.log(`Parliament Round 1: ${data.agent_count} agents analyzing...`);
  // Show: 14 agent icons, all gray, about to light up
});

source.addEventListener("agent_started", (e) => {
  const data = JSON.parse(e.data);
  // Agent started working — animate its icon (spinning/pulsing)
});

source.addEventListener("agent_proposal", (e) => {
  const data = JSON.parse(e.data);
  // A specialist's proposal just arrived — add to debate log
  // THESE STREAM IN LIVE as each Bedrock call returns (5-30s each)
});

source.addEventListener("deliberation_start", (e) => {
  // Round 2: selected agents are debating each other's proposals
});

source.addEventListener("deliberation_response", (e) => {
  const data = JSON.parse(e.data);
  // An agent's response to the debate — may include [DISAGREE]
});

source.addEventListener("coordinator_start", (e) => {
  // Round 3: COORDINATOR is synthesizing consensus
});

source.addEventListener("coordinator_resolution", (e) => {
  const data = JSON.parse(e.data);
  // THE FINAL CONSENSUS — show as a prominent banner/card
  // data.reasoning contains the full resolution text
  // data.action === "CONSENSUS_RESOLUTION"
});

// ── LIVE TOKEN STREAMING (the money events) ──

source.addEventListener("agent_token", (e) => {
  const data = JSON.parse(e.data);
  // LIVE OUTPUT TOKEN from a Strands agent — arrives word by word
  // data.agent_name = "SENTINEL" | "FLORA" | etc.
  // data.zone_id = "global" | "sim-alpha" | etc.
  // data.token = "The" (single token/word)
  // data.partial = "The temperature in" (accumulated text so far)
  // → Show as live typing animation per agent
});

source.addEventListener("agent_reasoning", (e) => {
  const data = JSON.parse(e.data);
  // Extended thinking token (if model supports it)
  // data.token = partial reasoning text
});

source.addEventListener("agent_tool_call", (e) => {
  const data = JSON.parse(e.data);
  // Agent is calling a tool MID-REASONING
  // data.tool_name = "query_syngenta_kb" | "set_actuator_command" | etc.
  // → Flash "🔧 Calling Syngenta KB..." next to the agent's typing area
});

source.addEventListener("agent_complete", (e) => {
  const data = JSON.parse(e.data);
  // Agent finished generating — full text available
  // data.full_text = complete response
  // → Stop typing animation, show final text
});

source.addEventListener("feedback", (e) => {
  const data = JSON.parse(e.data);
  // Closed-loop: did the previous cycle's actions actually work?
});

source.addEventListener("chaos", (e) => {
  const data = JSON.parse(e.data);
  // Injected failure — show dramatic alert
});

source.addEventListener("sensor_reading", (e) => {
  const data = JSON.parse(e.data);
  // Individual sensor reading from MQTT — high frequency
});

source.addEventListener("cycle_complete", (e) => {
  const data = JSON.parse(e.data);
  console.log(`Cycle done: ${data.total_decisions} decisions, ${data.zones_processed.length} zones`);
});

source.addEventListener("ping", () => {
  // Keepalive every 15s — ignore
});
```

---

## Complete Event Types Reference

| Event | When | Data Shape |
|-------|------|-----------|
| **Reconciliation Loop** | | |
| `cycle_start` | Reconciliation begins | `{sol, zone_count, zones, mars, model_available}` |
| `zone_state` | After Mars transform | Full ZoneState dict |
| `flight_rule` | Tier 0 rule fires | AgentDecision dict |
| `command` | Actuator cmd sent | ActuatorCommand dict |
| `telemetry` | Sensors persisted | `{zone_id, temperature, humidity, ...}` |
| `delta` | Desired vs actual | `{zone_id, deltas, in_range, current, desired}` |
| `model_invocation` | Model called for zone | `{zone_id, deltas}` |
| `decision` | Any agent decision | AgentDecision dict |
| `alert` | Critical/high event | `{zone_id, severity, rule, reasoning}` |
| `feedback` | Closed-loop results | `[{zone_id, improvements}]` |
| `cycle_complete` | Reconciliation done | `{total_decisions, flight_rule_decisions, ...}` |
| **Parliament Lifecycle** | | |
| `parliament_start` | Parliament invoked | `{zones_with_deltas, total_deltas}` |
| `round1_start` | Round 1 begins | `{agent_count, specialists, flora_zones}` |
| `agent_started` | Specialist begins | `{agent_name, zone_id?, round}` |
| `agent_proposal` | Round 1 proposal | AgentDecision dict |
| `round1_complete` | Round 1 done | `{proposal_count, agents_responded}` |
| `deliberation_start` | Round 2 begins | `{proposal_count}` |
| `deliberation_response` | Agent deliberates | AgentDecision dict |
| `deliberation_complete` | Round 2 done | `{response_count}` |
| `coordinator_start` | Round 3 begins | `{total_proposals, resolved_count}` |
| `coordinator_resolution` | Final consensus | AgentDecision dict (action=CONSENSUS_RESOLUTION) |
| `parliament_skipped` | Model unavailable | `{reason}` |
| **Live Token Streaming** | | |
| `agent_token` | Each output token | `{agent_name, zone_id, token, partial}` |
| `agent_reasoning` | Extended thinking token | `{agent_name, zone_id, token}` |
| `agent_tool_call` | Tool called mid-reasoning | `{agent_name, zone_id, tool_name}` |
| `agent_complete` | Agent done generating | `{agent_name, zone_id, full_text}` |
| `strands_agent_complete` | Strands agent finished | `{agent, stop_reason}` |
| `tool_use` | Tool executed by agent | `{agent_name, tool_name, zone_id, ...}` |
| **External Data** | | |
| `nasa_data` | NASA data refreshed | `{weather, solar_events_count}` |
| `sensor_reading` | Raw MQTT reading | SensorReading dict |
| `chaos` | Injected failure | `{event_type, ...}` |
| **System** | | |
| `ping` | Keepalive (15s) | `""` |

---

## Agent Color Scheme

| Agent | Color | Icon | Domain |
|-------|-------|------|--------|
| SENTINEL | Red `#E53E3E` | Shield | Safety |
| FLORA | Green `#38A169` | Leaf/Plant | Plant voice (per zone) |
| PATHFINDER | Brown `#8B6914` | Microscope | Disease |
| TERRA | Dark brown `#6B4226` | Soil/Root | Soil |
| DEMETER | Gold `#D69E2E` | Wheat | Crops/Environment |
| ATMOS | Light blue `#63B3ED` | Cloud | Atmosphere |
| AQUA | Blue `#3182CE` | Water drop | Water/Resources |
| HELIOS | Yellow `#ECC94B` | Sun | Energy/Light |
| VITA | Pink `#ED64A6` | Heart | Nutrition |
| HESTIA | Purple `#9F7AEA` | Home/Fire | Morale/Food culture |
| ORACLE | Indigo `#5A67D8` | Crystal ball | Forecasting |
| CHRONOS | Silver `#A0AEC0` | Clock | Mission planning |
| COORDINATOR | White `#FFFFFF` | Gavel | Consensus |

---

## The 3 Demo Moments to Optimize For

**1. Live Parliament Debate (THE KILLER FEATURE)**
- Subscribe to `round1_start`, `agent_started`, `agent_token`, `agent_tool_call`, `agent_complete`, `agent_proposal`, `coordinator_resolution`
- Show 14 agent cards in a grid. When `agent_started` fires, card pulses/glows
- **`agent_token` streams text word-by-word** — show live typing animation in each agent's card. 14 agents typing simultaneously = insane visual
- **`agent_tool_call` flashes** — show tool icon + name (e.g., "Querying Syngenta KB...") mid-typing
- `agent_complete` → stop animation, show final text
- `agent_proposal` → parsed decision card slides in
- FLORA speaks in first person: `"I feel the thirst... I am a tomato. I am not a cactus."`
- COORDINATOR resolution appears as a banner when Round 3 completes
- **The 20-30s of Bedrock generation becomes a 20-30s live show, not a loading spinner**

**2. Chaos Injection Cascade**
- Button press → POST to `/api/chaos/dust_storm` → chaos event on SSE
- Flight rules fire immediately → `flight_rule` + `alert` events
- Parliament reacts in next cycle → full debate visible
- Show the whole cascade: chaos → alert → debate → resolution

**3. Zone Health Dashboard**
- `zone_state` events update cards in real-time
- `delta` events show which sensors are out of range
- `feedback` events show closed-loop: "temperature dropped 6°C after fan activation"
- `telemetry` events feed live graphs

---

## Recommended Polling Strategy

- **Primary:** SSE stream (`/api/stream`) for everything real-time
- **Fallback:** Poll `/api/zones` every 5s, `/api/decisions` with `since` param every 5s
- **On load:** Fetch `/api/events?limit=100` for recent history + `/api/agents` for color scheme
- **Infrequent:** `/api/mars` every 30s, `/api/nutrition` every 60s, `/api/status` every 10s
