# AstroFarm — Predictive Capabilities Brainstorm

> Output of deep analysis session. Optimized against judging criteria.
> Updated with water/energy nexus + virtual farming lab insights.

---

## The Core Insight

Most hackathon teams will build **reactive** systems — sensor detects problem, agent responds. AstroFarm's differentiator is **predictive** — the agent sees the future and acts before problems occur.

**Reactive**: "Temperature dropped → turn on heater"
**Predictive**: "Solar storm will hit Mars in 50 hours → pre-emptively protect crops NOW"

This is qualitatively different. It's what separates a thermostat from a farmer.

---

## The 5 Prediction Types (from First Principles)

Prediction requires 3 things: a **signal**, a **model**, and an **action window**.

| # | Type | Signal | Model | Action Window | Build Time |
|---|---|---|---|---|---|
| **P1** | Solar Event | DONKI CME API (LIVE, real 2026 data) | `ETA = Mars_distance / CME_speed` | 18-96 hours | 4-6h |
| **P2** | Seasonal Cycle | Mars orbital mechanics (deterministic) | Sine wave from Ls solar longitude | 30-100+ sols | 2-3h |
| **P3** | Resource Depletion | Consumption telemetry + budget | Linear projection with safety margins | Days-weeks | 2-3h |
| **P4** | Nutritional Gap | Crop growth rates + crew dietary needs | `projected_yield - required_intake` | Weeks-months | 2-3h |
| **P5** | Dust Storm | Pressure patterns + Ls season correlation | Probability by season (not prediction) | Hours-days | 1-2h |

### Time Horizon Visualization

```
HORIZON          PREDICTION TYPE              DATA SOURCE         STATUS
----------------------------------------------------------------------
Hours (1-96h)    Solar radiation spike         DONKI CME/MPC       LIVE
Days (1-14d)     Dust storm readiness          Ls season + InSight  BASELINE
Weeks (1-8w)     Resource budget warnings      Consumption data     INTERNAL
Months (1-15mo)  Nutritional output gaps       Crop projections     MODELED
Full Mission     Seasonal crop scheduling      Orbital mechanics    DETERMINISTIC
```

---

## P1: Solar Event Prediction (THE DEMO CLIMAX)

### Why This Is The #1 Feature

- **LIVE DATA** — DONKI CME API has real 2026 events. Not simulated.
- **REAL PHYSICS** — CME transit to Mars is calculable from observed speed + known distance
- **DRAMATIC** — 50-hour countdown creates narrative tension in a 3-minute demo
- **CROSS-DOMAIN** — Astrophysics → agriculture is genuinely creative
- **DUAL SOURCE** — DONKI CME (predicted incoming) + DONKI MPC (confirmed Mars impact)

### The Science (Verified)

```
Mars-Sun distance:  ~1.52 AU = ~227,000,000 km
CME speed range:    400 - 2,500 km/s (from DONKI data)

Transit time examples:
  Slow CME  (400 km/s):   227M / 400   = 568,000s = ~6.6 days
  Medium    (1,000 km/s):  227M / 1,000 = 227,000s = ~63 hours
  Fast      (1,250 km/s):  227M / 1,250 = 181,600s = ~50 hours
  Very fast (2,500 km/s):  227M / 2,500 = 90,800s  = ~25 hours
```

### Agent Decision Chain

```
1. DONKI CME event detected (API poll every 5 min)
2. Extract: CME speed, half-angle, source location
3. Calculate: Mars transit ETA = distance / speed
4. Assess risk: Which crops at vulnerable growth stage?
   → Query Syngenta KB: "What growth stages are most radiation-sensitive?"
   → Cross-reference: Current crop day in growth cycle
5. Generate action plan based on ETA:
   → ETA > 48h: "Advisory" — prepare reserves, no immediate action
   → ETA 24-48h: "Pre-emptive" — activate radiation shielding, reduce power draw
   → ETA < 24h: "Imminent" — full survival mode, protect priority crops
6. Execute: Set actuators, log reasoning, alert crew
7. Post-event: Assess damage, recommend recovery actions
```

### What This Looks Like in Agent Log

```
[Sol 142, 14:23:07] DONKI MONITOR: New CME detected — CME-2026-0315
  Source: S15W23 | Speed: 1,247 km/s | Half-angle: 42deg

[Sol 142, 14:23:08] PREDICTIVE ANALYSIS:
  Mars-Sun distance: 1.48 AU (227.4M km)
  Calculated ETA: 50.7 hours (Sol 144, ~17:00)
  Confidence: MODERATE (half-angle suggests Mars in path)

[Sol 142, 14:23:09] RISK ASSESSMENT:
  Node:Carb — Wheat at day 65/120 (FLOWERING) → HIGH vulnerability
  Node:Protein — Soybean at day 40/90 (VEGETATIVE) → MODERATE vulnerability
  Node:Vitamin — Tomato at day 55/70 (FRUITING) → LOW vulnerability

[Sol 142, 14:23:10] PRE-EMPTIVE PROTOCOL INITIATED:
  → Radiation shielding: ACTIVATED [100%]
  → Grow lights: REDUCED [30%] — conserving power for dome heating
  → Nutrient mix: ADJUSTED — stress-hardening formula for Node:Carb
  → Water reserve: TOPPED UP — buffer for 72h autonomy
  → Crew notification: SENT — "Solar event ETA 50h. No action required."
```

### Dashboard Elements for P1

- **CME Alert Banner** — appears top-center when event detected, red/amber
- **ETA Countdown** — big, prominent "SOLAR EVENT: 50:42:17" timer
- **Risk Assessment Panel** — per-node vulnerability with crop growth stage
- **Timeline Marker** — red vertical line appears on Sol Forecast at predicted arrival

---

## P2: Seasonal Growth Optimization

### The Science

Mars orbital parameters (all deterministic, calculable for any date):
- Axial tilt: 25.19deg (similar to Earth's 23.44deg) → real seasons
- Orbital eccentricity: 0.0934 (Earth: 0.0167) → 40% solar intensity variation
- Year length: 668.6 sols
- Solar longitude (Ls): 0deg-360deg, standard Mars seasonal coordinate
  - Ls 0deg: Northern spring equinox
  - Ls 90deg: Northern summer solstice
  - Ls 180deg: Northern autumn equinox
  - Ls 270deg: Northern winter solstice
  - Dust storm season: Ls 180deg-330deg (southern spring/summer near perihelion)

### Agent Application

The 450-day mission spans ~67% of a Mars year. Solar intensity varies significantly.

```python
# Deterministic — can pre-compute entire mission
def solar_intensity(sol, mission_start_ls=0):
    ls = (mission_start_ls + (sol / 668.6) * 360) % 360
    # Mars eccentricity effect on solar flux
    eccentricity = 0.0934
    # Simplified solar flux relative to mean
    flux = 1.0 / (1 - eccentricity * math.cos(math.radians(ls - 251)))**2
    return flux  # ~0.84 at aphelion to ~1.19 at perihelion
```

### What This Enables

- **Crop Scheduling**: Plant light-hungry crops (wheat, soybean) during high-flux seasons
- **Harvest Timing**: Align harvest cycles with seasonal peaks
- **Power Budgeting**: More solar → more grow light power → faster growth
- **Pre-computed Mission Plan**: Agent shows entire 450-sol plan on day 1

### Dashboard Element

- **Ls Indicator**: Single number (0deg-360deg) with season label
- **Season Band**: Colored strip on Sol Forecast timeline (spring=green, summer=yellow, autumn=orange, winter=blue)
- **Solar Flux Graph**: Predicted vs actual light intensity across mission

---

## P3: Resource Depletion Forecasting

### The Math

```
Water budget: 450 days × 4 astronauts × ~3L/day plant water = ~5,400L minimum
Current rate: measured from telemetry
Projection: linear + seasonal adjustment

If projected_depletion_sol < 450:
  Agent: "At current rate, water exhausts Sol 380.
          Recommending 12% reduction in vitamin zone irrigation
          starting Sol 200 to extend to Sol 460."
```

### Agent Application

- Track water, nutrients, power consumption daily
- Project forward using consumption trends
- Alert when any resource projected to exhaust before Sol 450
- Recommend conservation measures with quantified impact
- Tie to crop priority classes: "Reducing herb irrigation saves 8L/sol. Impact: luxury crop yield -30%, calorie crop yield unchanged."

### Dashboard Element

- **Resource Trend Lines**: Water/nutrients/power plotted across mission with projection cone
- **Budget Bar**: "Water: 67% remaining | Projected: sufficient through Sol 450"

---

## P4: Nutritional Gap Projection

### Why This Is Critical for Judges

The challenge literally says: "optimize nutrient output, dietary balance, and resource efficiency for a crew of four astronauts." This is THE STATED PROBLEM. Solar events are flashy, but nutritional planning is the ANSWER.

### The Math

```
Daily requirement (4 astronauts): 10,000 kcal, 240g protein, full vitamin spectrum
Current crop yields: from growth tracking + Syngenta KB profiles
Projected harvests: growth_rate × remaining_days × area

Example gap detection:
  Protein needed by Sol 300: 240g × 300 = 72,000g
  Projected soybean harvest: 45,000g
  Projected lentil harvest: 18,000g
  Total projected: 63,000g
  GAP: -9,000g (12.5% shortfall)

  Agent: "Protein output projected 12.5% below target by Sol 300.
          Recommending: plant 2 additional soybean pods in Node:Protein
          by Sol 160 to close gap."
```

### This Is The K8s HPA

Horizontal Pod Autoscaler equivalent: nutritional output below threshold → scale up crop count. This is where the K8s metaphor is most powerful AND most functional.

### Dashboard Element

- **Nutritional Progress Bars**: Per-nutrient tracking (protein/carbs/vitamins/calories)
- **4-Astronaut × 450-Day Tracker**: "On track" / "Gap detected" with projected shortfall
- **HPA Trigger Log**: "Scaling up soybean pods: 4 → 6 to meet protein target"

---

## P5: Dust Storm Readiness (Honest Framing)

### Critical Note on InSight Data

InSight mission ended December 2022. Data is frozen at Sol 675-681 (October 2020). **Do NOT claim live Mars weather.** Instead:

**Honest framing**: "We use InSight's historical atmospheric data as our Mars baseline — the same data NASA uses for mission planning. Our agent uses this calibrated baseline combined with seasonal dust storm probability models to maintain heightened readiness during storm season (Ls 180-330)."

### What We Can Do

- Use InSight data for realistic Mars temperature/pressure/wind baselines
- Use Ls-based storm season probability (scientifically valid)
- Inject simulated storm events via Mars Transform Layer for demo purposes
- Frame injection honestly: "For demonstration, we're simulating a dust storm event to show the agent's response protocol"

### Dashboard Element

- **Mars Exterior Panel**: Shows InSight baseline conditions (labeled "Historical Baseline")
- **Storm Season Indicator**: When Ls is in 180-330 range, show "STORM SEASON" badge

---

## The Killer Feature: Sol Forecast Timeline

### What It Is

A single horizontal timeline spanning the full 450-sol mission, combining ALL prediction types into one unified visualization.

```
Sol 0          Sol 100         Sol 200         Sol 300         Sol 400    Sol 450
|──────────────|──────────────|──────────────|──────────────|──────────|

SEASON:  [===SPRING===][====SUMMER====][====AUTUMN====][==WINTER==]
         green          yellow          orange          blue

CROPS:   ╔═wheat═══════╗  ╔═wheat.2══════╗
         ╔═soybean══╗      ╔═soybean.2═══╗
         ╔═potato════════════╗  ╔═potato.2═══════╗
         ╔═tomato═══╗╔═tomato.2══╗╔═tomato.3═══╗
         ╔═spinach╗╔spin.2╗╔spin.3╗╔spin.4╗

EVENTS:        ▼CME          ▼CME               ▼CME
               (50h)         (25h)               (63h)

RESOURCES: ────water──────────────────────────────────
           ─────nutrients──────────────────────────────

NUTRITION: Protein  ████████████████████████████░░░░░  87%
           Carbs    █████████████████████████████░░░░  92%
           Vitamins ███████████████████████░░░░░░░░░░  78%
```

### Why It Wins All 4 Criteria

| Criterion (25% each) | How Sol Forecast Scores |
|---|---|
| **Creativity** | No other team will have a forward-looking mission timeline. It's a paradigm shift from reactive dashboards to predictive mission planning. |
| **Functionality/Accuracy** | DONKI data is REAL. Orbital mechanics are CORRECT. Crop profiles from Syngenta KB. Every layer is grounded in data. |
| **Visual Design** | A beautiful timeline is the most impactful single dashboard element. Color-coded seasons, crop bars growing, red event markers appearing — it's visually rich and information-dense. |
| **Demo/Presentation** | "Watch — a CME just appeared on our Sol Forecast. The agent is already rescheduling harvests around the radiation window." One sentence, judges understand the entire system. |

### The Demo Moment (Revised Script)

**Act 2 — "The Agent Sees The Future" (60s)**

1. Dashboard shows Sol Forecast timeline — crops growing, everything green
2. DONKI polling detects a real CME event
3. Red marker APPEARS on the timeline at Sol 144 (50 hours out)
4. Agent log: "PREDICTIVE ALERT: CME-2026-0315 detected. ETA: 50.7 hours."
5. Agent log: "Risk assessment: Wheat at flowering stage — HIGH vulnerability."
6. Agent log: "Pre-emptive protocol: Radiation shields activated. Lights reduced 70%."
7. Dashboard shifts green → amber. Countdown appears: "SOLAR EVENT: 50:42:17"
8. Physical LEDs dim in sync
9. Presenter: "Our agent just detected a REAL coronal mass ejection from NASA's DONKI database. It calculated the transit time to Mars — 50 hours — and is already protecting our crops. No human told it to do this."

---

---

## NEW: Water/Energy/Storm Nexus (The Resource Chain)

### The Mars Water Reality

Mars has confirmed subsurface briny water (perchlorate brines). Converting this to usable water requires energy-intensive desalination. The greenhouse runs on:

```
Solar Panels → Electricity → Desalination (brine → clean water)
                           → Grow Lights
                           → Dome Heating
                           → Radiation Shields
                           → Battery Charging

STORM HITS → Solar drops to 30% → TRIAGE REQUIRED
```

### Why This Changes Everything

Without the water/energy model, storm prediction is just "activate shields." WITH it, the agent runs a full resource cascade calculation:

```
AGENT ANALYSIS (50 hours before storm):

  CURRENT STATE:
    Solar output:         100% (4.2 kW)
    Clean water reserve:  340L (3.4 sol supply @ 100L/sol)
    Battery charge:       78%
    Desalination rate:    120L/sol at full power

  PREDICTED STATE (during 5-sol storm):
    Solar output:         30% (1.26 kW)
    Desalination at 30%:  36L/sol
    Water deficit:        64L/sol × 5 sols = 320L shortfall
    Battery drain:        shields + heating > solar input

  PRE-STORM PROTOCOL:
    1. Desalination → MAX (48h @ 100% = +240L reserve)
    2. Top battery → 100% (shield + heating reserve)
    3. Pre-water all crops to saturation (+1 sol buffer)
    4. Reduce non-critical irrigation (herbs -100%, vitamin -30%)
    5. Pre-harvest any mature crops (lock in nutrition before stress)

  PROJECTED OUTCOME:
    Water autonomy: 7.2 sols (covers 5-sol storm + 2-sol margin)
    Battery autonomy: 6.1 sols for shields
    Crop survival: 97% (spinach stressed, all others nominal)
```

### K8s Parallel

This is **pre-scaling before a known traffic spike**. The agent frontloads resources the same way a cluster auto-scales pods before a predicted load surge.

### Why Judges Love This

- **Creativity**: Nobody else will model the solar→water→crop energy chain
- **Functionality**: Real resource optimization with real math — not hand-waving
- **Applicability (Syngenta's priority)**: This IS resource-constrained farming on Earth — drought, energy costs, water scarcity. The Mars scenario proves the concept, Earth is the market.
- **Demo moment**: "Watch the water reserves climb as the agent stockpiles before the storm hits"

### Dashboard Elements

- **Resource Chain Diagram**: Solar → Power → Water → Crops flow with live values
- **Water Reserve Gauge**: Big, visual, showing reserves climbing during pre-storm stockpiling
- **Power Budget Bar**: How electricity is allocated across subsystems
- **Pre-Storm Checklist**: Agent's preparation steps with checkmarks appearing in real-time

---

## NEW: Virtual Farming Lab (The Staging Environment)

### Concept

A simulation sandbox where the agent TESTS response strategies before applying them to the real greenhouse. Like a staging cluster / dry-run / canary deployment in K8s.

### K8s Mapping

| K8s Concept | Virtual Lab Equivalent |
|---|---|
| Staging cluster | Simulated greenhouse — same model, no real consequences |
| Dry-run mode | "What happens if I cut light by 50% for 3 sols?" |
| Canary deployment | Test new crop config on 1 simulated bed before rollout |
| Chaos engineering | "Simulate pump failure — does my recovery protocol work?" |
| A/B testing | Run 3 strategies, compare simulated outcomes, pick best |

### Agent Workflow

```
1. DETECT  → Threat identified (CME incoming, resource shortage, etc.)
2. GENERATE → Create 3-5 candidate response strategies
3. SIMULATE → Run each strategy in virtual lab (fast-forward time)
4. COMPARE  → Rank by: crop survival %, resource usage, recovery time
5. SELECT   → Pick optimal strategy with reasoning
6. APPLY    → Execute on real greenhouse
7. LEARN    → Compare actual outcome vs simulation → improve model
```

### What the Agent Logs

```
[Sol 142, 14:24:00] VIRTUAL LAB: Running 3 response strategies for CME-2026-0315

  STRATEGY A — "Do Nothing" (baseline):
    Simulated outcome: 40% crop loss, wheat dies at Sol 144, protein deficit by Sol 200
    Resource usage: nominal
    Recovery time: 45 sols (replant from seed)

  STRATEGY B — "Standard Survival Mode":
    Simulated outcome: 12% crop loss, spinach stressed, soybean reduced yield
    Resource usage: shields + heating draw 2.1 kW for 5 sols
    Recovery time: 15 sols

  STRATEGY C — "Pre-emptive Full Protocol":
    Simulated outcome: 3% crop loss (only herbs affected)
    Actions: Stockpile water 48h, pre-harvest spinach, stress-harden wheat nutrients
    Resource usage: high for 48h pre-storm, then survival mode
    Recovery time: 5 sols

  DECISION: Strategy C selected — lowest crop loss, acceptable resource cost
  CONFIDENCE: 87% (based on Syngenta KB stress response data + historical storm models)
```

### Dashboard Layout

```
┌─────────────────────────────────┬─────────────────────────────────┐
│  PRODUCTION GREENHOUSE          │  VIRTUAL FARMING LAB            │
│  (Live state)                   │  (Simulation sandbox)           │
│                                 │                                 │
│  Node:Protein  [healthy]        │  SCENARIO: CME-2026-0315        │
│  Node:Carb     [healthy]        │  Testing 3 strategies...        │
│  Node:Vitamin  [warning]        │                                 │
│                                 │  A: Do Nothing    → 40% loss ✗  │
│  Water: 340L ████████░░ 68%     │  B: Survival Mode → 12% loss ~  │
│  Power: 4.2kW ██████████ 100%   │  C: Full Protocol →  3% loss ✓  │
│  Battery: 78% ████████░░        │                                 │
│                                 │  SELECTED: Strategy C           │
│                                 │  [APPLY]  [MODIFY]  [RERUN]     │
└─────────────────────────────────┴─────────────────────────────────┘
```

### Why This Wins

This is potentially the **highest-scoring single feature** across all criteria:

| Criterion | Why it scores |
|---|---|
| **Creativity (25%)** | A simulation-within-a-simulation is meta, novel, and deeply creative. Nobody else will have this. |
| **Functionality (25%)** | Shows the agent REASONS about strategies — real AI decision-making, not rule-following. |
| **Visual Design (25%)** | Side-by-side production vs simulation is visually striking and intuitive. |
| **Demo (25%)** | "Watch the agent test 3 strategies, pick the best, then apply it" — judges see AI THINKING. |

### Syngenta MCP KB Integration

The virtual lab's simulations are parameterized by Syngenta KB data:
- **Crop stress thresholds**: At what light %, temp, water level does each crop die/stress/survive?
- **Growth stage vulnerability**: Flowering wheat is more radiation-sensitive than vegetative soybean
- **Recovery profiles**: How long does each crop take to recover from stress?
- **Nutrient impact**: How does stress affect nutritional output per crop?

This makes the KB integration DEEP, not superficial. The agent queries it continuously during simulation runs. The provided AWS AgentCore system becomes ESSENTIAL to the core feature.

---

## Syngenta MCP Knowledge Base — Integration Plan

**Endpoint**: `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`
**Tools**: "Check Syngenta Documentation", "Check Weather on Mars"
**Status**: MANDATORY for judging (Key Element + AWS bonus points)

### Where the KB Feeds Into Each Feature

| Feature | KB Query | Domain Used |
|---|---|---|
| CME Prediction | "What growth stages are most radiation-sensitive?" | Plant Stress and Response Guide |
| CME Prediction | "How do crops respond to reduced light for 3-5 days?" | Crop Profiles |
| Water Stockpiling | "Water requirements per crop per growth stage?" | Crop Profiles |
| Water Stockpiling | "Minimum water for crop survival vs optimal?" | Controlled Environment Agriculture |
| Virtual Lab Sims | "What happens to wheat at 50% light for 3 sols?" | Plant Stress + Crop Profiles |
| Virtual Lab Sims | "Recovery time for stressed soybean?" | Greenhouse Operational Scenarios |
| Nutritional Tracking | "Nutritional content per crop per kg?" | Human Nutritional Strategy |
| Nutritional Tracking | "Optimal diet composition for 4 astronauts?" | Human Nutritional Strategy |
| Earth Application | "How does this apply to drought farming on Earth?" | Innovation Impact (Mars to Earth) |

### Integration Approach

**Option A (fastest)**: Connect Claude Code to the MCP endpoint directly. Query it during brainstorming and development to extract crop data, then hardcode key values into the agent.

**Option B (for demo)**: Agent queries the MCP KB in real-time during the demo. Agent log shows: "Querying Syngenta Knowledge Base: wheat radiation tolerance at flowering stage... Response: 'Wheat at flowering (Zadoks 60-69) is highly sensitive to UV-B radiation. Yield reduction of 15-40% at elevated UV exposure...'"

**Option B is better for judges** — they SEE the agent using their provided system in real-time.

---

## Implementation Priority (REVISED — Hackathon Time Budget)

### TIER 1 — MUST BUILD (Demo Climax) — ~6 hours

- [ ] DONKI CME API integration (poll every 5 min, parse speed/location)
- [ ] CME → Mars ETA calculator (`distance / speed`)
- [ ] Water/energy chain model (solar → power → desalination → water → crops)
- [ ] Pre-storm stockpiling logic (max desalination, top battery, pre-water crops)
- [ ] Agent decision chain: detect → simulate → select strategy → pre-empt → log reasoning
- [ ] Dashboard: CME alert banner + countdown timer
- [ ] Dashboard: Water reserve gauge + power budget bar (climbing during stockpiling)
- [ ] Dashboard: Agent log showing predictive reasoning chain
- [ ] Physical sync: LEDs dim when survival mode activates

### TIER 2 — SHOULD BUILD (Biggest Differentiator) — ~5 hours

- [ ] Virtual Farming Lab: simulation engine (fast-forward crop outcomes under conditions)
- [ ] Strategy generator: create 3 candidate responses per threat
- [ ] Strategy evaluator: simulate each, rank by crop survival + resource cost
- [ ] Dashboard: side-by-side Production vs Simulation Lab panel
- [ ] Dashboard: Strategy comparison (A/B/C with predicted outcomes)
- [ ] Syngenta MCP KB integration: query crop stress thresholds for simulation params

### TIER 3 — SHOULD BUILD (Challenge Answer) — ~3 hours

- [ ] Nutritional tracking: 4 astronauts × 450 days progress bars
- [ ] Nutritional gap detection: projected yield vs required intake
- [ ] HPA trigger: auto-scale crop count when gap detected
- [ ] Dashboard: Nutrition panel with per-nutrient progress

### TIER 4 — NICE TO HAVE (The Unified Vision) — ~4 hours

- [ ] Sol Forecast timeline component (horizontal, 450-sol span)
- [ ] Season band (Ls-based color coding)
- [ ] Crop growth bars on timeline
- [ ] Solar event markers on timeline (red vertical lines)
- [ ] Resource trend lines projected forward

### TIER 5 — POLISH (Scientific Credibility) — ~2 hours

- [ ] Ls solar longitude indicator on dashboard
- [ ] Mars exterior conditions panel (InSight baseline, labeled honestly)
- [ ] Seasonal solar flux calculation for power budgeting
- [ ] DONKI MPC integration (confirmed historical Mars impacts)

---

## Syngenta MCP KB Integration Points

For each prediction type, the agent should query the Syngenta KB:

| Query | Prediction Type | Expected Answer |
|---|---|---|
| "What growth stages are most radiation-sensitive?" | P1 Solar | Flowering > fruiting > vegetative |
| "Optimal temperature ranges per crop?" | P2 Seasonal | Crop-specific temp profiles |
| "Water requirements per growth stage?" | P3 Resource | L/day/m2 by stage |
| "Nutritional content per crop per kg?" | P4 Nutritional | Calorie/protein/vitamin profiles |
| "How do crops respond to reduced light?" | P1/P5 Storm | Stress responses, survival thresholds |

This ensures the provided AWS AgentCore system is deeply integrated — not just used but ESSENTIAL to the prediction logic.

---

## What To Say in the Pitch

> "Every other greenhouse on Mars waits for problems. AstroFarm sees the future."
>
> "Our agent monitors NASA's real-time solar event database. When it detects a coronal mass ejection, it calculates the transit time to Mars — 50 hours. But it doesn't just activate shields. It runs three response strategies in our Virtual Farming Lab, simulating crop outcomes for each. It picks the best: stockpile water by running desalination at max while solar is still at 100%, pre-harvest vulnerable crops, stress-harden the wheat. By the time the storm arrives, the greenhouse is already prepared."
>
> "And this isn't just Mars. Every drought, every energy crisis, every extreme weather event on Earth poses the same resource-constrained farming challenge. Syngenta's crop science combined with predictive AI — that's how we feed 10 billion people."

## Demo Script (3 minutes, revised)

### Act 1 — "The Farm is Running" (30s)
- Dashboard live: 3 zones green, nutritional tracking shows "4 astronauts on track"
- Agent log streaming: "Sol 142. Systems nominal. Protein zone at 87%. Wheat approaching harvest."
- Show the Sol Forecast timeline: crop bars, seasonal band, everything planned out
- Physical prop: LEDs on, pump running

### Act 2 — "The Agent Sees the Future" (45s)
- DONKI data: "CME-2026-0315 detected. Speed: 1,247 km/s."
- Agent: "Calculating Mars transit... ETA: 50.7 hours."
- Agent: "Running virtual farming lab — testing 3 response strategies..."
- Dashboard: Simulation panel appears with strategies A/B/C and predicted outcomes
- Agent: "Strategy C selected: Pre-emptive Full Protocol. 3% crop loss vs 40% baseline."
- Strategy C details stream in agent log

### Act 3 — "Stockpiling Before the Storm" (45s)
- Agent: "Initiating pre-storm protocol. Desalination → MAX."
- Dashboard: Water reserve gauge climbing (340L → 420L → 500L → 580L)
- Dashboard: Battery charging (78% → 85% → 92% → 100%)
- Agent: "Pre-harvesting spinach — locking in nutrition before stress period"
- Agent: "Stress-hardening nutrient mix applied to Node:Carb wheat"
- Physical prop: LEDs dim gradually, showing power reallocation
- Countdown: "SOLAR EVENT: 48:12:33"

### Act 4 — "The Vision" (30s)
- "Our agent queried Syngenta's crop knowledge base to know wheat flowering is radiation-vulnerable. It used real NASA solar data to predict the storm. It tested strategies in simulation before acting. And it stockpiled water because it modeled the entire energy chain."
- "This is autonomous farming that THINKS. Not just for Mars — for every resource-constrained farm on Earth."
- Flash: Target humidity = 42% (the Hitchhiker's Guide easter egg from the slides)
