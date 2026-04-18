# EDEN — Architecture

## System Overview

```
                    ┌──────────────────────────────────────────────┐
                    │           EDEN GREENHOUSE CLUSTER             │
                    │           (Digital Twin)                      │
                    └─────────────────┬────────────────────────────┘
                                      │
         ┌───────────────────────────┼────────────────────────────┐
         │                           │                            │
  ┌──────┴──────┐          ┌────────┴───────┐          ┌────────┴───────┐
  │ Node:       │          │ Node:          │          │ Node:          │
  │ Protein     │          │ Carb           │          │ Vitamin        │
  │ Zone        │          │ Zone           │          │ Zone           │
  │             │          │                │          │                │
  │ Pod:soybean │          │ Pod:potato     │          │ Pod:tomato     │
  │ Pod:lentil  │          │ Pod:wheat      │          │ Pod:spinach    │
  │  +basil(sc) │          │                │          │                │
  └──────┬──────┘          └────────┬───────┘          └────────┬───────┘
         │                          │                            │
         └──────────────────────────┼────────────────────────────┘
                                    │
              ┌─────────────────────┴──────────────────┐
              │ Services Layer                          │
              │ Water | Nutrients | Light | CO2 | Power │
              │ (Circular: water→plant→transpire→water) │
              └────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────────┐     MQTT      ┌──────────────────┐
│   Raspberry Pi   │──────────────→│   AWS IoT Core   │
│                  │               │                  │
│ Sensors:         │     MQTT      │ Rule: forward    │
│ • DHT22 (temp)   │←──────────────│ to Lambda        │
│ • Soil moisture  │ (actuator     └────────┬─────────┘
│ • Light sensor   │  commands)             │
│ • Camera         │                        ▼
│                  │               ┌──────────────────┐
│ Actuators:       │               │  Lambda:         │
│ • Grow light     │               │  Mars Transform  │
│ • Water pump     │               │  Earth → Mars    │
│ • Fan            │               │  + event inject  │
└──────────────────┘               └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │    DynamoDB      │
                                   │ • telemetry      │
                                   │ • desired_state  │
                                   │ • agent_log      │
                                   │ • flight_rules   │
                                   │ • crop_profiles  │
                                   └────────┬─────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────┐
          │                                 │                     │
          ▼                                 ▼                     ▼
 ┌──────────────────┐             ┌──────────────────┐   ┌───────────────┐
 │  EDEN Control    │             │  React Dashboard │   │ External APIs │
 │  Plane           │────────────→│  (Amplify)       │   │               │
 │                  │  council    │                  │   │ • DONKI CME   │
 │  4-Layer Arch:   │  log       │ • Council Log    │   │ • DONKI MPC   │
 │  L0: Flight Rules│  stream    │ • Virtual Lab    │   │ • InSight     │
 │  L1: Triage      │            │ • Triage Panel   │   │ • Syngenta KB │
 │  L2: Council     │←───────────│ • Water/Energy   │   │ • NASA Images │
 │  L3: Dreamer     │  user      │ • Nutrition      │   │               │
 │                  │  inject    │ • Sol Forecast   │   └───────┬───────┘
 │  Agents:         │  events    │ • Sol Counter    │           │
 │  FLORA · AQUA    │            └──────────────────┘           │
 │  VITA · SENTINEL │                                           │
 │  ORACLE          │←──────────────────────────────────────────┘
 └──────────────────┘          agents query external data
```

## 4-Layer Decision Architecture (Detail)

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 0: FLIGHT RULES ENGINE                                        │
│ Deterministic IF/THEN. 0ms latency. Zero compute. Cannot override. │
│ ~50 rules Sol 1 → ~300 by Sol 450 (Dreamer proposes new rules).    │
│                                                                     │
│ IF dome_pressure < 400 hPa → seal zones, alert crew, emergency     │
│ IF soil_moisture < 15% AND priority=CRITICAL → irrigate immediately │
│ IF radiation > threshold → shields ON, non-essential power OFF      │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 1: TRIAGE REFLEXES                                            │
│ Tactical agents. Seconds. Minimal compute. Salvageability scoring. │
│                                                                     │
│ "Where does the next liter of water save the most crop?"           │
│ Medical triage: RED (immediate) / YELLOW (defer) / GREEN (save) /  │
│                 BLACK (expectant — cost exceeds yield)              │
│                                                                     │
│ Ethical Triage Dashboard: every decision shows human cost.          │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 2: THE COUNCIL (Agent Parliament)                             │
│ Strategic decisions. Minutes. Strands SDK multi-agent.              │
│                                                                     │
│ FLORA (crops) · AQUA (resources) · VITA (nutrition/morale)         │
│ SENTINEL (threats) · ORACLE (simulation)                            │
│                                                                     │
│ Debate → Vote → Log reasoning. Flight Rules break deadlocks.       │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 3: THE DREAMER (Virtual Farming Lab)                          │
│ Planning + simulation. Hours. Off-peak compute.                     │
│                                                                     │
│ Monte Carlo simulations of possible futures.                        │
│ Tests 3-5 strategies per threat. Compares outcomes.                │
│ Proposes new flight rules from learned patterns.                    │
│ Dashboard: side-by-side Production vs Simulation panels.           │
└─────────────────────────────────────────────────────────────────────┘
```

## Water / Energy Chain

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐
│  SOLAR   │───→│  POWER   │───→│ DESALINATION │───→│  CROPS   │
│ 4.2 kW   │    │ + Battery│    │ Brine→Clean  │    │ 100L/sol │
│          │    │          │    │ 120L/sol     │    │          │
└──────────┘    └──────────┘    └──────────────┘    └──────────┘
                     │
              ┌──────┴──────────────────────────┐
              │ Also powers:                     │
              │ • Grow lights (30%)             │
              │ • Dome heating (20%)            │
              │ • Radiation shields (15%)       │
              │ • Other systems (10%)           │
              └─────────────────────────────────┘

STORM (30% solar):
  Desal drops: 120L → 36L/sol. Deficit: 64L/sol.
  PRE-STORM: Max desal 48h = +240L reserve. Top battery. Pre-water.
  Result: 7.2 sol autonomy (covers 5-sol storm + margin).
```

## AgentCore Architecture

```
Agent code (Strands SDK multi-agent)
├── Models: Bedrock Claude
├── Framework: Strands SDK
├── AgentCore Runtime decorator
├── AgentCore Identity config
└── AgentCore Observability config
         ↓
    Docker → ECR → AgentCore Runtime (Firecracker MicroVM)
                        ├── Runtime Agent
                        └── Runtime Endpoint ← Dashboard invokes

Agent → /mcp → AgentCore Gateway → Interceptors →
    ├── Syngenta MCP KB         (PROVIDED — 7 domain knowledge base)
    ├── DONKI CME/MPC           (CUSTOM — OpenAPI → MCP, solar events)
    ├── USDA FoodData Central   (CUSTOM — OpenAPI → MCP, nutritional cross-ref)
    ├── NASA POWER              (CUSTOM — OpenAPI → MCP, solar irradiance)
    ├── EDEN Simulation         (CUSTOM — Lambda, crop outcome modeling)
    └── Mars Transform          (CUSTOM — Lambda, Earth→Mars conversion)
```

## DynamoDB Schema

### Table: `eden-telemetry`
| Key | Type | Description |
|---|---|---|
| `node_id` (PK) | String | `protein`, `carb`, `vitamin` |
| `timestamp` (SK) | Number | Unix epoch |
| `temp_c` | Number | Mars-adjusted temperature |
| `humidity_pct` | Number | Relative humidity |
| `soil_moisture_pct` | Number | Soil moisture |
| `co2_ppm` | Number | CO2 concentration |
| `light_pct` | Number | Light intensity |
| `pressure_hpa` | Number | Dome interior pressure |
| `water_reserve_l` | Number | Clean water in reserve |
| `battery_pct` | Number | Battery charge level |
| `solar_output_pct` | Number | Solar panel output |

### Table: `eden-state`
| Key | Type | Description |
|---|---|---|
| `key` (PK) | String | `desired_state`, `device_status`, `crop_profiles`, `flight_rules` |
| `data` | Map | JSON state object |

### Table: `eden-council-log`
| Key | Type | Description |
|---|---|---|
| `timestamp` (PK) | Number | Unix epoch |
| `agent` | String | `FLORA`, `AQUA`, `VITA`, `SENTINEL`, `ORACLE`, `COUNCIL` |
| `severity` | String | `info`, `warning`, `critical`, `triage` |
| `reasoning` | String | Agent's thought process / debate contribution |
| `action` | String | Decided action |
| `human_cost` | String | Ethical triage: crew impact statement (nullable) |
| `vote` | String | For/against/abstain on council decisions (nullable) |

## Nutritional Model

Mission: 4 astronauts × 450 days = 1,800 person-days.
Daily per astronaut: ~2,500 kcal, 60g protein, full vitamin spectrum.

| Crop | Zone | Cal/kg | Protein g/kg | Growth days | Yield kg/m² | Companion |
|---|---|---|---|---|---|---|
| Soybean | Protein | 446 | 36 | 80-100 | 0.3 | + Wheat (N-fix) |
| Lentil | Protein | 353 | 25 | 80-110 | 0.2 | |
| Potato | Carb | 77 | 2 | 70-120 | 4.0 | Radiation-resilient |
| Wheat | Carb | 339 | 13 | 120-150 | 0.5 | + Soybean |
| Tomato | Vitamin | 18 | 0.9 | 60-80 | 8.0 | + Basil (antifungal) |
| Spinach | Vitamin | 23 | 2.9 | 40-50 | 2.0 | Under tomato canopy |

The Council's VITA agent watches these numbers. When projected output drops below threshold → HPA: scale up crop count.
