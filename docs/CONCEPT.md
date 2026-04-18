# EDEN — The Operating System for Autonomous Life Support

> *"We didn't build a greenhouse controller. We built the operating system for autonomous agriculture."*
> *EDEN: Engineered Decision-making for Extraterrestrial Nurture*

## One-Liner

A multi-agent AI system that autonomously manages a Martian greenhouse through a 4-layer decision architecture — combining deterministic flight rules, specialist agent parliament, predictive simulation, and real NASA solar data to supplement 4 astronauts' diet with fresh nutrition for 450 days without human intervention.

## The Insight

Mars communication latency is 4-24 minutes each way. The greenhouse cannot call Earth for help. By the time Houston answers, the crops are already dead or already saved.

Packed rations provide macronutrients — calories, protein, fat. But freeze-dried food degrades over a 450-day mission: vitamin C drops 35% per year, folate breaks down, and crew morale erodes eating the same 20 meals on rotation. The greenhouse is the **fresh nutrition insurance policy** — providing the vitamins, minerals, fiber, and psychological comfort that rations cannot.

The solution: Kubernetes for farming. K8s solved autonomous resource management for containers in unreliable environments. EDEN solves it for life in hostile ones. Same abstractions, same patterns, different substrate.

This isn't a metaphor — it's a structurally exact architecture. Every K8s primitive maps to a greenhouse primitive. Every AWS engineer in the room instantly understands the system's sophistication.

## The Story

This is the loneliest farmer in the solar system. An AI, 227 million km from the nearest expert, tending crops that supplement a crew of 4 — fresh vitamins, iron, potassium, fiber, and the morale that comes from eating something that was alive yesterday. It watches the sky for solar storms. It detects disease before it spreads. It decides which plants live and which die. It tests strategies in simulation before risking real crops. And it gets better every day — writing its own operational playbook from experience.

---

## Four-Layer Decision Architecture

The core innovation. Not all decisions need AI. Not all AI needs to be slow.

```
LAYER 0 — FLIGHT RULES    (deterministic, 0ms, zero compute)
LAYER 1 — REFLEXES         (tactical agents, seconds, minimal compute)
LAYER 2 — THE COUNCIL      (strategic agent parliament, minutes)
LAYER 3 — THE DREAMER      (simulation + planning, hours, off-peak compute)
```

### Layer 0: Flight Rules Engine

Pre-encoded deterministic IF/THEN protocols. Execute in milliseconds. Work offline. Cannot be overridden by AI.

```
FR-T-003: IF soil_moisture < 15% AND crop_priority = CRITICAL THEN irrigate immediately
FR-P-001: IF dome_pressure < 400 hPa THEN seal all zones, alert crew, enter emergency mode
FR-R-001: IF radiation > threshold THEN activate shields, reduce non-essential power
FR-W-001: IF water_reserve < 2_sol_supply THEN suspend all non-critical irrigation
```

These are the greenhouse's constitutional laws. On Sol 1, the system has ~50 rules from Earth knowledge. By Sol 450, it has 300+, all learned from experience and simulation.

Why judges love this: It solves the ACTUAL 22-min latency constraint. Shows you understand that pure AI is insufficient for life-critical systems.

### Layer 1: Reflexes (Triage Engine)

Fast tactical agents running locally. Real-time salvageability scoring — not priority classes, but medical triage:

```
"Where does the next liter of water save the most crop?"

Wheat at day 110/120 (near harvest):   SAVE      — 10 more days = full harvest
Soybean at day 20/90 (early):          DEFER     — survives 5 days dry
Spinach at day 5/45 (seedling):        IMMEDIATE — 2L saves entire future cycle
Tomato at day 60/70 (40% diseased):    EXPECTANT — cost to save exceeds likely yield
```

Disease and stress detection — not just crisis response, but daily vigilance:
```
SENTINEL: Elevated humidity in leafy_green zone. VPD 0.42 kPa — below target 0.8-1.2 kPa.
Botrytis risk rising. Lettuce at BBCH 43 (leaf development) — high susceptibility window.
Querying Syngenta KB: lettuce disease thresholds in CEA...
KB: Botrytis cinerea onset at VPD < 0.5 kPa sustained >6h. Preventive action: increase airflow.
ACTION: Fan speed +30%. Monitoring VPD recovery. If <0.6 kPa in 2h, reduce irrigation 20%.
```

The Ethical Triage Dashboard surfaces the human cost of every decision:
```
TRIAGE: Deprioritizing spinach in Zone C.
CONSEQUENCE: Crew vitamin C drops to 68% of minimum.
SCURVY RISK: Sol 292 unless compensated.
MITIGATION: Increase tomato light +15%, accelerate harvest by 8 sols.
NOTE: Spinach was Dr. Chen's preferred green — substituting with microgreens from reserve.
```

### Layer 2: The Council (Agent Parliament)

Multi-agent system of peer specialists that debate and vote on strategic decisions. Not a hierarchy — a parliament. Built on Strands SDK multi-agent patterns.

| Agent | Role | Advocates for |
|---|---|---|
| **FLORA** | Crop Advocate | Plant health, growth optimization, companion planting |
| **AQUA** | Resource Guardian | Water cycling, nutrient budgets, energy allocation |
| **VITA** | Nutritionist | Crew health, dietary balance, food preferences, morale |
| **SENTINEL** | Threat Detector | Stress detection, failure prediction, quarantine decisions |
| **ORACLE** | The Dreamer | Simulation results, contingency plans, new flight rules |

When agents deadlock, Flight Rules break the tie: human safety > crop survival > resource conservation > optimization. All debates are logged and auditable.

Example Council session:
```
[Sol 247] SENTINEL: CME-2026-0315 detected. Speed 1,247 km/s. Mars ETA: 50.7 hours.
[Sol 247] SENTINEL: Querying Syngenta KB: radiation sensitivity by crop growth stage...
           KB: "Wheat at BBCH 61-65 (anthesis) shows 15-40% yield reduction under elevated UV-B.
           Potato tuber initiation stage shows high radiation resilience."
           Without KB data, I'd prioritize potato by caloric value alone.
           KB changes my assessment: wheat is the urgent priority — it's in its most vulnerable window.
[Sol 247] ORACLE: Running 3 strategies in simulation lab...
[Sol 247] ORACLE: Strategy C (pre-emptive full protocol) = 3% loss vs 40% baseline.
[Sol 247] AQUA: Water reserve at 340L. Need 480L for 5-sol storm autonomy.
           Running desalination at MAX for 48h — solar still at 100%.
[Sol 247] FLORA: Pre-harvest spinach now to lock in nutrition before stress period.
           Querying Syngenta KB: wheat stress-hardening nutrient adjustments...
           KB: "Increase K+ concentration to 6 mmol/L, reduce N by 20% to trigger defensive response."
           Adjusting nutrient solution EC from 1.8 to 2.4 mS/cm per KB recommendation.
[Sol 247] VITA: With spinach pre-harvested, vitamin C buffer is 58 sols. Acceptable.
           Crew macro intake unaffected — rations cover 82% of calories. Greenhouse role is micronutrient insurance.
[Sol 247] COUNCIL VOTE: Strategy C adopted unanimously. Executing.
```

### Layer 3: The Dreamer (Virtual Farming Lab)

Runs during off-peak cycles. Monte Carlo simulations of possible futures. Tests strategies before applying to real crops.

The dashboard shows this as a side-by-side: Production Greenhouse vs Simulation Lab.

```
STRATEGY A — "Do Nothing"           → 40% crop loss  ✗
STRATEGY B — "Standard Survival"     → 12% crop loss  ~
STRATEGY C — "Pre-emptive Protocol"  →  3% crop loss  ✓  SELECTED

C includes: Stockpile water 48h, pre-harvest spinach, stress-harden wheat,
top battery, activate shields. Confidence: 87% (Syngenta KB stress data).
```

After each real event, the Dreamer compares predicted vs actual outcomes and proposes new flight rules. The system writes its own operational playbook over time.

The learning loop in action:
```
ORACLE [Sol 249]: Post-storm debrief. CME-2026-0315 resolved.
  Predicted crop loss: 3.0%. Actual: 4.1%. Delta: +1.1%.
  Root cause: Zone B moisture deficit during hour 38-42 of storm.
  Water stockpiling began at 48h ETA — 2h too late for full saturation.
  PROPOSING NEW RULE: FR-CME-014
    IF cme_eta > 55h AND water_reserve < 80% THEN begin_stockpiling
    Evidence: 2h additional stockpiling = +28L reserve, eliminates Zone B deficit.
    Confidence: 91% (3 simulation runs confirm).
  Flight rule count: 54 → 55. System improving.
```

---

## Water / Energy / Solar Chain

Mars has subsurface briny water. Desalination requires energy. Energy comes from solar. Storms reduce solar.

```
Solar Panels (4.2 kW) → Electricity → Desalination (brine → 120L/sol clean water)
                                     → Grow Lights
                                     → Dome Heating
                                     → Radiation Shields
                                     → Battery Charging
```

**Pre-Storm Stockpiling** — the predictive system's most impressive concrete feature:

When SENTINEL detects a CME 50 hours out, AQUA runs the resource chain calculation:
- Storm duration: ~5 sols at 30% solar
- Desalination at 30% power: 36L/sol (deficit: 64L/sol × 5 = 320L shortfall)
- ACTION: Run desalination at MAX for 48h while solar is still 100% → stockpile +240L
- Top battery to 100% → shield + heating reserve
- Pre-water all crops to saturation → +1 sol buffer
- RESULT: 7.2 sol water autonomy (covers 5-sol storm + margin)

---

## K8s → Greenhouse Complete Map

| K8s Concept | EDEN Equivalent |
|---|---|
| **Cluster** | Greenhouse dome |
| **Control Plane** | 4-layer decision architecture |
| **Node** | Grow zone (Protein, Carb, Vitamin, Herb) |
| **Pod** | Individual plant unit |
| **Sidecar Container** | Companion planting (Three Sisters: soybean + wheat = nitrogen fixation -18% nutrients) |
| **Scheduler** | Crop planner (FLORA agent) |
| **HPA Autoscaler** | Nutritional gap → scale up crop count |
| **Liveness Probe** | Is the plant alive? (sensor check every 30s) |
| **Readiness Probe** | Is this crop harvestable? (maturity check) |
| **CrashLoopBackOff** | Seed fails 3× → try different conditions → try different crop |
| **Rolling Update** | Crop rotation — zero-downtime food supply |
| **Canary Deployment** | Virtual Farming Lab tests before real deployment |
| **ResourceQuota** | Water/nutrient budget per zone per sol |
| **PodDisruptionBudget** | Never >30% of a crop type offline |
| **Eviction** | Water shortage → evict herbs before potatoes |
| **ConfigMap** | Growth parameters per crop (pH, temp, light hours) |
| **Secrets** | Syngenta proprietary nutrient formulas |
| **DaemonSet** | Environmental monitoring on every zone |
| **CronJob** | Scheduled watering, light cycles, dreamer cycle |
| **NetworkPolicy / Condition Zebra** | Crisis → zone isolation, cross-zone sharing suspended |
| **Admission Controller** | Flight Rules Engine — deterministic gates |
| **Ingress** | AgentCore Gateway: 6 targets (Syngenta KB + DONKI + USDA + NASA POWER + Simulation + Mars Transform) |

---

## Predictive Capabilities (5 Time Horizons)

| Horizon | Type | Data Source | Status |
|---|---|---|---|
| Hours (25-96h) | Solar Event (CME → Mars transit) | DONKI CME API | LIVE — real 2026 data |
| Days (1-14d) | Dust Storm Readiness | InSight baseline + Ls season | Historical baseline + seasonal model |
| Weeks (1-8w) | Resource Depletion Forecast | Consumption telemetry | Internal model |
| Months (1-15mo) | Nutritional Gap Projection | Syngenta KB + crop growth | Modeled from KB data |
| Full Mission | Seasonal Crop Scheduling | Mars orbital mechanics (Ls) | Deterministic — pre-computed |

### CME Prediction Math (Verified)

```
Mars-Sun distance: ~1.52 AU = ~227,000,000 km
CME speed (from DONKI): 400 - 2,500 km/s
Transit time = distance / speed

Slow (400 km/s):    ~6.6 days
Medium (1,000):     ~63 hours
Fast (1,250):       ~50 hours
Very fast (2,500):  ~25 hours
```

This looks like months of astrophysics work. It's literally high school physics. But it uses REAL NASA data and produces REAL predictions.

---

## Syngenta Integration

### MCP Knowledge Base (MANDATORY)

Endpoint: `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`

7 domains. The agent queries it continuously — not just for data, but for REASONING:

| Agent Query | KB Domain | What It Enables |
|---|---|---|
| "Wheat radiation tolerance at flowering?" | Plant Stress + Crop Profiles | CME risk assessment per growth stage |
| "Water requirements per crop per stage?" | Crop Profiles + CEA | Water budget + pre-storm stockpiling targets |
| "Recovery time for stressed soybean?" | Greenhouse Scenarios | Simulation accuracy in Virtual Lab |
| "Optimal diet for 4 astronauts 450 days?" | Human Nutritional Strategy | Nutritional gap detection |
| "Companion planting synergies?" | Crop Profiles + CEA | Three Sisters scheduling |
| "How does this apply to Earth drought?" | Innovation Impact | Pitch closer |

**Creative KB use**: The agent derives insights NO SINGLE document contains. Cross-referencing stress thresholds + nutritional requirements + Mars constraints to generate novel recommendations. The agent CREATES knowledge from the KB ingredients.

### The Nutritional Reality: Supplement, Not Sole Source

The greenhouse doesn't feed the crew alone — and it shouldn't. Packed rations provide 82% of calories, protein, and fat. The greenhouse provides what rations cannot:

| What Rations Provide | What Greenhouse Provides |
|---|---|
| Calories (stable, shelf-life 3+ years) | Fresh vitamins (C degrades 35%/yr in storage) |
| Protein (freeze-dried, complete) | Iron (193% coverage from fresh greens) |
| Fat (shelf-stable oils, nuts) | Folate (139% — heat-destroyed in processing) |
| Carbs (rice, pasta, bars) | Fiber (81% — absent in most rations) |
| Monotony (20 meal rotations) | Morale (fresh food, variety, crew agency) |

EDEN's Sol 1 nutritional projection:
```
VITA [Sol 1]: Mission nutritional analysis complete.
  Greenhouse role: micronutrient insurance + fresh food morale.
  Ration complement: 82% calories, 95% protein, 97% fat from packed stores.
  Greenhouse covers: 193% vitamin C, 146% iron, 139% folate, 107% potassium.
  Critical gaps (ration + greenhouse combined): vitamin D (supplement required),
    vitamin B12 (supplement required). Flagged to crew medical officer.
  Optimization target: maximize vitamin/mineral yield per liter of water.
  Fresh food morale factor: NASA studies show 23% crew satisfaction increase
    with access to fresh produce on ISS missions.
```

This is the scientifically honest framing: EDEN optimizes for the nutrition that only fresh crops can provide, complementing — not replacing — the ration supply chain.

### The Earth Transfer

> "The technology we built for four astronauts works for four billion farmers."

Syngenta has approximately 1 agronomist per 5,000 farmers in Sub-Saharan Africa. 800 million people are food insecure. They face the same fundamental problem as Mars: limited resources, extreme conditions, and no expert available in real-time.

Specific scenario: A smallholder maize farmer in Kenya facing erratic rainfall. EDEN's architecture translates directly:
- **Flight Rules** → proven agronomic protocols for the region (from Syngenta KB)
- **Triage Engine** → "This field is saveable, this one isn't — redirect water here"
- **Predictive system** → monsoon delay detection, drought early warning
- **Syngenta KB** → the same crop science, same stress thresholds, same nutritional data

Mars forced us to build agriculture's hardest system. The Earth version is easier — but the architecture is identical. EDEN makes Syngenta's crop science accessible where no expert exists, at the moment it matters most.

---

## Companion Planting (Three Sisters on Mars)

7,000-year-old Milpa system meets AI. 30 minutes to implement (system prompt + KB query):

- **Soybean + Wheat**: Nitrogen fixation reduces nutrient solution by ~18%
- **Tomato + Basil**: Basil VOCs provide antifungal protection in closed dome
- **Spinach under Tomato canopy**: Vertical space optimization

Maps to K8s Sidecar Containers. Agent: "Scheduling soybean adjacent to wheat. Companion planting: nitrogen fixation reduces nutrient requirement by 18%. Source: Syngenta KB."

Ancient wisdom + AI on Mars = Creativity score through the roof.

---

## EDEN as Platform: Mission Architect + Extension Planner

EDEN isn't just a greenhouse operator. It's a planning platform with three modes:

### Mode 1: Mission Architect (Day -1)

Before Sol 1, EDEN designs the optimal greenhouse from constraints:

**Input**: Cargo budget (kg), dome area (m²), crew size, mission duration, nutritional targets
**Output**: Crop mix, zone layout, resource requirements, planting schedule, risk assessment

```
EDEN MISSION ARCHITECT — Mars 2037

CONSTRAINTS: 2,400kg payload | 100m² dome | 4 crew | 450 sols
RECOMMENDED:
  Zone A (Protein 30m²): Soybean 20m² + Lentil 10m²
  Zone B (Carb 30m²):    Potato 20m² + Wheat 10m²
  Zone C (Vitamin 25m²): Tomato 15m² + Spinach 10m²
  Zone D (Support 15m²): Basil 5m² (companion) + Reserve 10m²

  Companion: Soybean ↔ Wheat (N-fixation -18% nutrients)
  Water: 500L reserve + 120L/sol desalination
  Projected: 108% calories, 94% protein, 87% vitamins
  Risk: Wheat flowering (BBCH 60) overlaps Ls 220 storm season
```

K8s parallel: cluster provisioning before deploying workloads.
Syngenta parallel: "Given a farmer's 5ha, $2,000 budget, semi-arid climate — what should they grow?"

### Mode 2: Operations (Sol 1-450)

The 4-layer decision architecture. Everything else in this document.

### Mode 3: Extension Planner (Adaptive Scaling)

EDEN detects capacity limits and proposes greenhouse expansion:

```
EXTENSION PROPOSAL — Sol 280

TRIGGER: Iron deficiency trend detected in crew medical data.
         Vitamin zone at 96% capacity.

RECOMMENDATION: 12m² extension module
  Crops: Spinach 8m² + Kale 4m²
  Impact: Iron +34%, Vitamin C +22%
  Cost: 180kg cargo, 8h crew time, +15L/sol water

ALTERNATIVE: Reallocate 4m² from herbs to spinach (zero cargo cost)
```

K8s parallel: `kubectl scale --replicas=4` — adding nodes to the cluster.
Syngenta parallel: "Your farm is at capacity. Here's the optimal expansion with ROI analysis."

### Output Formats

| Output | Format | Audience |
|---|---|---|
| Mission Plan | Structured zones + crops + timeline + risk | NASA planners |
| Extension Proposal | Cost-benefit with alternatives | Mission commanders |
| Daily Ops Report | Decisions, sensor summary, crew impact | Astronaut crew |
| Post-Mission Codex | Learned rules, recommendations for next mission | Future missions |
| Earth Advisory | Same structure for terrestrial farming | Syngenta customers |

The **Codex** is the flywheel: Syngenta KB → EDEN → Mars Codex → Next Mission's EDEN. The agent becomes a researcher, not just a manager. Knowledge compounds across missions.

---

## What Makes EDEN Win

1. **4-layer architecture** — Flight Rules + Reflexes + Council + Dreamer = architecturally novel
2. **Predictive, not reactive** — sees storms 50 hours ahead, stockpiles resources, tests strategies
3. **Learns and adapts** — writes its own flight rules from experience (50 on Sol 1 → 300 by Sol 450)
4. **Disease + stress detection** — catches Botrytis risk from VPD drift before symptoms appear
5. **Ethical triage** — surfaces human cost of decisions, not just optimization metrics
6. **Scientifically honest** — greenhouse supplements rations, doesn't pretend to replace them
7. **KB-driven decisions** — agent shows WHERE Syngenta data changed its reasoning
8. **K8s vocabulary** — AWS engineers instantly understand; Syngenta sees precision agriculture
9. **Physical + Digital** — real plant with real sensors synced to digital twin
10. **Real NASA data** — DONKI CME (live), verified transit math, honest InSight framing
11. **Water/energy chain** — models the full resource cascade, not just individual systems
12. **Virtual Farming Lab** — tests before deploying, like staging clusters
13. **Companion planting** — 7,000-year-old wisdom meets AI on Mars
14. **Earth transfer** — 1 agronomist per 5,000 farmers. EDEN is the always-on expert Syngenta can deploy.
