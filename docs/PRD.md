# EDEN — Product Requirements Document

## Overview

**Project**: EDEN — Engineered Decision-making for Extraterrestrial Nurture
**Event**: START HACK 2026 (Syngenta x AWS)
**Duration**: 48-hour hackathon build
**Team**: Lars, Bryan (digital), Johannes, PJ (physical)

## Challenge Brief (Syngenta)

> *Full brief: [CHALLENGE_BRIEF.md](CHALLENGE_BRIEF.md)*

**Users**: NASA planners + Syngenta scientists (autonomous cropping for extreme Earth environments)

**Mission Parameters**:
- Crew: 4 astronauts
- Duration: 450-day surface-stay mission on Mars
- Goal: Maximize nutrient output + dietary balance
- Constraints: Minimal resource use, minimal astronaut time, 22-min communication latency

**Provided Knowledge Base** (Amazon Bedrock KB via AgentCore Gateway MCP endpoint):
1. Mars Environmental Constraints
2. Controlled Environment Agriculture Principles
3. Crop Profiles
4. Plant Stress and Response Guide
5. Human Nutritional Strategy
6. Greenhouse Operational Scenarios
7. Innovation Impact (Mars to Earth)

**MCP Endpoint**: `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`
**Gateway tools**: "Check Syngenta Documentation", "Check Weather on Mars"

## Judging Criteria

| Criterion | Weight | Our Angle |
|---|---|---|
| Creativity | 25% | 4-layer architecture, K8s metaphor, ethical triage, companion planting, agent parliament, self-improving flight rules |
| Functionality / accuracy | 25% | Real DONKI data, verified CME math, Syngenta KB integration (causal, not decorative), scientifically honest nutritional model (supplement framing), disease detection, learning loop, working multi-agent system |
| Visual design / UX | 25% | Dark Mars dashboard, Virtual Lab side-by-side, water gauges, Sol Forecast timeline |
| Presentation / demo | 25% | Nominal ops → crisis → learning arc. 50h countdown, physical prop LEDs sync. All 4 challenge requirements visible. |
| **Bonus**: AWS tools | Extra | Bedrock, AgentCore, IoT Core, DynamoDB, Lambda, Amplify, EventBridge, CloudWatch, S3, Cognito |

## Deliverables

1. **Working PoC**: Digital twin with multi-agent system making real decisions
2. **3-minute pitch**: Live demo with physical prop
3. **Working agent system**: Real AI reasoning — Council debates visible in agent log

---

## System Architecture

### Layer 1: Physical (Raspberry Pi)

**Owner**: Johannes + PJ

| Component | Hardware | Data |
|---|---|---|
| Temperature + humidity | DHT22 / BME280 | Air temp, humidity |
| Soil moisture | Capacitive sensor | Moisture % |
| Light sensor | BH1750 / LDR | Lux / light % |
| CO2 sensor | MH-Z19B (if available) | ppm |
| Camera | Pi Camera / USB webcam | Live view |
| Grow light | LED strip + relay | On/off, dimming (synced to agent) |
| Water pump | 5V peristaltic pump + relay | On/off |
| Fan | 5V DC fan + relay | On/off |

**Data flow (pragmatic)**: Sensors → Pi → HTTP JSON endpoint (`http://pi-ip:8080/sensors`) → Dashboard polls directly. NOT IoT Core + MQTT (too many failure points on hackathon WiFi). Pi also accepts actuator commands via HTTP POST.

### Layer 2: Mars Transform Layer

**Owner**: Lars (Lambda function)

Transforms real Earth sensor data into Mars-adjusted values. Also injects simulated events for demo.

```
Earth sensor → Mars Transform → Agent sees "Mars" values

Temperature:  +28°C  →  Mars baseline + dome heating model  →  +18°C (dome interior)
Pressure:     1013 hPa  →  dome target 500 hPa  →  scaled reading
Radiation:    Earth UV  →  ×2.5 (no ozone)  →  triggers shield response
```

Event injection for demo: CME alerts (from real DONKI), dust storms, water line failures, pressure breaches.

### Layer 3: EDEN Control Plane — 4-Layer Decision Architecture

**Owner**: Lars + Bryan

**Runtime**: AWS Bedrock (Claude) via Strands SDK multi-agent patterns

```
┌─────────────────── EDEN Control Plane ───────────────────┐
│                                                           │
│  LAYER 0: Flight Rules Engine (deterministic, 0ms)        │
│  ~50 rules on Sol 1 → ~300 by Sol 450 (self-improving)   │
│                                                           │
│  LAYER 1: Triage Reflexes (tactical, seconds)             │
│  Salvageability scoring + ethical cost transparency        │
│                                                           │
│  LAYER 2: Agent Council (strategic, minutes)              │
│  FLORA · AQUA · VITA · SENTINEL · ORACLE                 │
│  Peer agents that debate, vote, log reasoning             │
│                                                           │
│  LAYER 3: The Dreamer / Virtual Farming Lab (hours)       │
│  Monte Carlo simulation, strategy testing, flight rule    │
│  generation. Runs during off-peak cycles.                 │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Ethical Triage Dashboard — surfaces human cost      │   │
│  │ "I chose to let the spinach die. Crew vitamin C    │   │
│  │  drops below scurvy threshold in 45 sols."         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Crew Interface — "Rent-a-Human" API                │   │
│  │ request_crew_intervention(task, urgency, duration) │   │
│  └────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

**Agent Tools (Strands SDK)**:
- `read_sensors()` — pull latest telemetry from DynamoDB
- `query_syngenta_kb()` — hit MCP knowledge base (crop profiles, stress thresholds)
- `get_mars_weather()` — InSight baseline + "Check Weather on Mars" MCP tool
- `get_solar_events()` — DONKI CME/MPC for solar threat prediction
- `set_actuator(device, action, value)` — command physical devices via MQTT
- `run_simulation(scenario, strategies)` — Virtual Farming Lab
- `calculate_triage(resources, crops)` — salvageability scoring with human cost
- `log_council_decision(agents, votes, reasoning)` — transparent decision log
- `get_nutritional_status()` — crew dietary tracking (4 × 450 days)
- `request_crew_intervention(task, urgency, duration)` — "Rent-a-Human"
- `propose_flight_rule(trigger, action, evidence)` — self-improving rules
- `trigger_alert(severity, message)` — crew notification

### Layer 4: Dashboard — The Lens

**Owner**: Bryan + Lars
**Tech**: React + Next.js on AWS Amplify

```
┌───────────────────────────────┬───────────────────────────────┐
│  LIVE VIEW / SOL COUNTER      │  COUNCIL LOG                  │
│  Camera feed or Mars view     │  Agent debate stream          │
│  Sol 142.07 (ticking)         │  SENTINEL: "CME detected..."  │
│                               │  AQUA: "Water at 340L..."     │
│                               │  COUNCIL VOTE: Strategy C     │
├───────────────────────────────┼───────────────────────────────┤
│  PRODUCTION GREENHOUSE        │  VIRTUAL FARMING LAB          │
│  Node:Protein [healthy] 87%   │  Strategy A: 40% loss  ✗     │
│  Node:Carb    [healthy] 92%   │  Strategy B: 12% loss  ~     │
│  Node:Vitamin [warning] 64%   │  Strategy C:  3% loss  ✓     │
│                               │  [APPLY] [MODIFY] [RERUN]    │
├───────────────────────────────┼───────────────────────────────┤
│  WATER / ENERGY CHAIN         │  TRIAGE DASHBOARD             │
│  Solar: 100% → Desal: 120L   │  Salvageability scores        │
│  Water: ████████░░ 68%        │  Human cost per decision      │
│  Battery: ████████░ 78%       │  Crew nutrition impact        │
├───────────────────────────────┴───────────────────────────────┤
│  NUTRITIONAL TRACKING  (4 astronauts × 450 days)              │
│  Protein: 87% ████████░░  Carbs: 92% █████████░              │
│  Vitamins: 78% ████████░  Calories: 91% █████████░           │
├───────────────────────────────────────────────────────────────┤
│  SOL FORECAST TIMELINE  (450 sols)                            │
│  [crop bars][season band][solar events][resource trends]      │
│  ▼CME(50h)        ▼harvest       ▼CME          ▼harvest     │
└───────────────────────────────────────────────────────────────┘
```

### Layer 5: External Data Sources

| Source | Data | Status |
|---|---|---|
| **DONKI CME** | Coronal mass ejections (speed, location) | LIVE — real 2026 data |
| **DONKI MPC** | Confirmed Mars magnetopause crossings | LIVE — 3 events in 2026 |
| **InSight Weather** | Mars temp, pressure, wind baseline | Frozen Sol 675-681 (historical baseline) |
| **Syngenta MCP KB** | 7 domains: crops, stress, nutrition, scenarios | Provided by challenge |
| **NASA Images** | Mars imagery for dashboard visuals | LIVE |
| **JPL Close Approach** | Asteroid flybys near Mars | LIVE — Easter egg |

---

## Feature Map (Build Priority)

### TIER 1: Demo Climax — CME + Water Stockpiling (~6h)

The single "impossible demo" moment. Looks like months of work, is `distance / speed`.

- [ ] DONKI CME API polling (parse speed, location, half-angle)
- [ ] CME → Mars ETA calculator (verified: 50h at 1,247 km/s)
- [ ] Water/energy chain model (solar → power → desal → water → crops)
- [ ] Pre-storm stockpiling (max desal 48h, top battery, pre-water crops)
- [ ] SENTINEL agent: detect → assess risk per crop growth stage
- [ ] AQUA agent: resource chain calculation + stockpiling protocol
- [ ] Dashboard: CME alert banner + 50h countdown timer
- [ ] Dashboard: Water reserve gauge climbing during stockpiling
- [ ] Physical: LEDs dim when survival mode activates

### TIER 2: Virtual Farming Lab (~2-5h, two versions)

**CHEAP VERSION (~2h, 80% of impact)**: Strategy comparison happens in agent log text only. Agent outputs: "Evaluating Strategy A: Do Nothing... 40% crop loss. Strategy B: Survival Mode... 12%. Strategy C: Pre-emptive Protocol... 3%. SELECTED: C." No dedicated UI panel. This is prompt engineering, not frontend work.

**FULL VERSION (~5h)**: Side-by-side dashboard panel. Only if cheap version is done and time remains.

- [ ] Agent prompt: generate 3 strategies per threat with predicted outcomes
- [ ] Syngenta KB queries for stress thresholds to parameterize predictions
- [ ] Agent log: strategy comparison with reasoning visible
- [ ] (FULL) Dashboard: Production vs Simulation Lab side-by-side panel
- [ ] (FULL) Dashboard: Strategy A/B/C cards with outcomes + SELECTED badge

### TIER 3: Council + Triage (~4h)

The agent parliament that debates decisions.

- [ ] Multi-agent setup: FLORA, AQUA, VITA, SENTINEL, ORACLE as Strands agents
- [ ] Council debate protocol: agents argue → vote → log reasoning
- [ ] Ethical triage: salvageability scoring with human cost transparency
- [ ] Dashboard: Council log showing agent-by-agent debate
- [ ] Dashboard: Triage panel with color-coded scores (RED/YELLOW/GREEN/BLACK)

### TIER 4: Nutritional Tracking (~3h)

Directly answers the challenge prompt.

- [ ] 4 astronauts × 450 days nutritional model
- [ ] Projected yield vs required intake per nutrient
- [ ] HPA trigger: auto-scale crop count when gap detected
- [ ] Companion planting: Three Sisters scheduling (soybean + wheat = -18% nutrients)
- [ ] Dashboard: Per-nutrient progress bars + gap alerts

### TIER 5: Sol Forecast Timeline (~4h)

Unified multi-horizon visualization.

- [ ] 450-sol horizontal timeline component
- [ ] Crop growth bars (per zone, showing plant → harvest cycles)
- [ ] Solar event markers (red vertical lines with ETA)
- [ ] Season band (Ls-based color: spring/summer/autumn/winter)
- [ ] Resource trend lines (water, nutrients projected forward)

### TIER 6: Flight Rules + Self-Improvement (~3h) — CHALLENGE REQUIREMENT

Deterministic fast-path + learning loop. **NOTE: "Learn and adapt" is one of 4 explicit challenge requirements. Must be visible in demo.**

- [ ] Flight Rules DSL (IF condition THEN action — deterministic)
- [ ] Layer 0 enforcement: rules fire before agent reasoning
- [ ] Dreamer → propose new rules from simulation results
- [ ] Agent log: post-event debrief with predicted vs actual + new rule proposal (MINIMUM — system prompt)
- [ ] Dashboard: Flight Rules panel (count growing over mission)
- [ ] Post-event: actual vs predicted comparison → model improvement

### TIER 7: High-Leverage Polish (~3h)

- [ ] Agent personality: inner monologue style, not system output ("Sol 142. CME coming in hot. Wheat's in full flower — worst possible timing. I have 50 hours.")
- [ ] "Mission Day 1" — agent generates 450-sol crop rotation plan on startup. Displayed as simple timeline. Pitch: "On Sol 1, it already planned every harvest through Sol 450." (~1h, wild card — nobody else opens with PLANNING)
- [ ] Disease detection in nominal operations: agent log shows VPD/humidity monitoring → Botrytis risk → preventive action. Checks "detect and respond to plant stress" requirement. (System prompt, 0 build time)
- [ ] Post-event learning: agent log shows predicted vs actual → new flight rule proposal. Checks "learn and adapt" requirement. (System prompt, 0 build time)
- [ ] KB causality: agent explicitly states "Without KB data I'd do X. KB changes my decision to Y." Proves integration is real. (System prompt, 0 build time)
- [ ] Honest nutritional framing: VITA agent surfaces ration + greenhouse complement. "Rations: 82% calories. Greenhouse: 193% vitamin C, 146% iron." (System prompt, 0 build time)
- [ ] O₂/CO₂ life support indicator: "Greenhouse O₂ Contribution: 14.2% of crew requirements" — when crops degrade, this drops. Pitch: "If these crops die, the astronauts don't just go hungry — they suffocate."
- [ ] Memory Wall panel (Sol 1: First seed. Sol 14: First sprout. Sol 67: First harvest.)
- [ ] Companion planting mention in agent log ("Scheduling soybean adjacent to wheat. Nitrogen fixation reduces nutrient requirement by 18%. Source: Syngenta KB.")
- [ ] 42% humidity Easter egg
- [ ] Dashboard state transitions: background tint shifts from dark blue → amber → red → warm green across demo acts (shortcut version of full state machine — 1h for 70% of impact)

---

## AWS Services (Bonus Points)

| Service | Purpose |
|---|---|
| **Amazon Bedrock** | AI agent runtime (Claude model) |
| **AgentCore Gateway** | 6 targets: Syngenta KB (provided) + DONKI + USDA FoodData + NASA POWER + Simulation Lambda + Mars Transform Lambda |
| **AgentCore Runtime** | Isolated Firecracker MicroVM per agent session |
| **Strands SDK** | Multi-agent framework with @tool decorators |
| **AWS IoT Core** | MQTT broker for Pi ↔ Cloud |
| **DynamoDB** | Telemetry + state + agent log + flight rules |
| **Lambda** | Mars Transform Layer + event injection |
| **Amplify** | Dashboard hosting |
| **EventBridge** | Scheduled triggers (watering, dreamer cycle) |
| **CloudWatch** | Monitoring + log aggregation |
| **S3** | Assets, OpenAPI specs, simulation results |
| **Cognito** | JWT auth for gateway |

---

## Demo Script (3 Minutes)

### Act 1: "The Loneliest Farmer" (0:00-0:45)

"4 astronauts. 450 days on Mars. 22-minute signal delay. They can't bring a farmer. So we built one."

Dashboard live. Sol counter ticking. 5 zones green. Nutritional tracking shows ration + greenhouse complement.

"On Sol 1, EDEN already planned every harvest through Sol 450." Brief flash of 450-sol crop rotation timeline.

**Nominal operations moment** — agent log shows daily vigilance:
- SENTINEL: "VPD drifting low in leafy green zone. Botrytis risk. Increasing airflow." (Disease detection — checks challenge requirement)
- FLORA: "Querying Syngenta KB: lettuce disease thresholds in CEA..." (KB integration visible)
- Physical prop: LEDs warm-white, plant alive.

"EDEN doesn't just react to crises. It prevents them. But let's see what happens when one comes."

### Act 2: "EDEN Sees the Future" (0:45-1:20)

DONKI alert: real CME detected. SENTINEL: "Speed 1,247 km/s. Mars ETA: 50.7 hours."

SENTINEL queries Syngenta KB: "Wheat at BBCH 65 — KB says 15-40% yield loss under elevated UV-B. Without this data, I'd prioritize potato. KB changes my assessment: wheat is the urgent priority." (KB causality — agent shows data changed its decision)

Council convenes. ORACLE runs 3 strategies in Virtual Lab. Strategy C selected: 3% loss vs 40%.

Dashboard: green → amber. Countdown: 50:42:17. Virtual Lab panel shows strategy comparison.

### Act 3: "Preparing for the Storm" (1:20-2:00)

AQUA: "Desalination → MAX." Water gauge climbing. Battery charging to 100%. FLORA: "Pre-harvest spinach. Stress-harden wheat — adjusting nutrient EC from 1.8 to 2.4 per KB recommendation."

Triage dashboard: "Consequence: Crew vitamin C drops to 68%. Rations cover macros — greenhouse role is micronutrient insurance. Mitigation: accelerate radish harvest from quick_harvest zone."

Physical LEDs dim gradually. Fan stops (sound cue).

**Post-storm learning moment** (agent log): "Actual loss: 4.1% vs predicted 3%. Promoting new flight rule FR-CME-014: begin stockpiling at 60h ETA. Rule count: 55. System improving." (Learning loop — checks "adapt over time" requirement)

### Act 4: "The Mirror" (2:00-2:30)

"Everything you just saw works on Earth too. Syngenta has 1 agronomist per 5,000 farmers in Sub-Saharan Africa. Same Syngenta KB. Same decision architecture. Same crop science — now accessible where no expert exists."

"800 million people are food insecure. Mars forced us to build the hardest version. The Earth version is easier."

### Close (2:30-3:00)

"We built the loneliest farmer in the solar system. It plans every harvest. It detects disease before symptoms appear. It sees storms 50 hours ahead. It learns from every decision. And it gets better every day. Because on Mars, there is no second chance."

---

## Q&A Prep

**"Is this real AI or scripted?"**
Real Claude on Bedrock via Strands SDK. Agent logs generated live. Different crop states = different decisions. We can show tool calls right now.

**"22-minute delay — how does it work?"**
Layer 0 Flight Rules handle known scenarios in 0ms. No cloud needed. Agent reasoning only for novel situations. Earth sends daily config updates — GitOps model.

**"What's the Earth application?"**
Syngenta has ~1 agronomist per 5,000 farmers in Sub-Saharan Africa. 800M people face the same constraints: limited water, climate stress, no expert in real-time. Same agent, same Syngenta KB, same decision architecture. Mars forced us to build the hardest version — the Earth version is easier. EDEN makes Syngenta's crop science accessible at the moment it matters most.

**"How accurate is the science?"**
Crop profiles from Syngenta KB. DONKI CME data is live/real. Mars conditions from NASA InSight. Dome assumption consistent with NASA's current architecture. Nutritional model is honest: greenhouse supplements rations (17.7% calories, but 193% vitamin C, 146% iron) — we don't pretend the greenhouse feeds the crew alone.

**"Does the system really learn?"**
Yes. After every event, the Dreamer compares predicted vs actual outcomes and proposes new flight rules. Sol 1: 50 rules from Earth knowledge. By Sol 450: 300+ rules learned from experience. We show one rule promotion live in the demo.

**"What would you build next?"**
Computer vision for leaf health. Multi-dome federation (K8s cluster of greenhouses). Closed learning loop where simulation accuracy improves every growing cycle.
