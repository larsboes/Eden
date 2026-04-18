# EDEN — Detailed Feature Specs

> Per-feature specs for team alignment. Each feature has: what it is, how it works, what to build, acceptance criteria, and dependencies.

---

## FEATURE 1: CME Prediction + Mars Transit Calculation

**Owner**: Lars
**Time**: ~3h
**Tier**: 1 (Demo Climax)

### What It Is
Agent polls NASA DONKI CME API, detects new coronal mass ejections, calculates Mars transit time, and triggers the pre-storm protocol.

### How It Works
```python
@tool
def get_solar_events() -> dict:
    """Poll DONKI CME API for recent coronal mass ejections."""
    url = "https://api.nasa.gov/DONKI/CME"
    params = {
        "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "endDate": datetime.now().strftime("%Y-%m-%d"),
        "api_key": NASA_API_KEY
    }
    response = requests.get(url, params=params)
    cmes = response.json()

    for cme in cmes:
        speed = cme.get("cmeAnalyses", [{}])[0].get("speed", 0)  # km/s
        if speed > 0:
            mars_distance_km = 227_000_000  # ~1.52 AU
            eta_seconds = mars_distance_km / speed
            eta_hours = eta_seconds / 3600
            cme["mars_eta_hours"] = round(eta_hours, 1)
            cme["mars_eta_sols"] = round(eta_hours / 24.6, 2)

    return {"events": cmes, "count": len(cmes)}
```

### What to Build
- [ ] DONKI CME API integration (poll, parse speed/half-angle/location)
- [ ] Mars transit ETA calculator
- [ ] DONKI MPC API integration (confirmed Mars impacts — for credibility)
- [ ] Risk assessment per crop: cross-reference CME with current growth stages
- [ ] Agent decision: map ETA to urgency level (>48h=advisory, 24-48h=pre-emptive, <24h=imminent)
- [ ] Write CME events to DynamoDB for dashboard consumption

### Acceptance Criteria
- Given a real DONKI CME event, agent calculates correct Mars ETA (±5%)
- Agent log shows: CME ID, speed, calculated ETA, risk assessment per zone
- ETA triggers appropriate urgency level
- Dashboard receives CME event and displays alert + countdown

### Dependencies
- NASA API key (have it: `YOUR_NASA_API_KEY`)
- DynamoDB table for events
- Agent running with Strands SDK @tool

---

## FEATURE 2: Water/Energy Chain + Pre-Storm Stockpiling

**Owner**: Lars
**Time**: ~3h
**Tier**: 1 (Demo Climax)

### What It Is
Models the resource chain (solar→power→desalination→water→crops) and executes pre-storm water stockpiling when a CME is detected.

### How It Works
```python
@tool
def calculate_resource_chain(solar_pct: float, storm_duration_sols: float) -> dict:
    """Calculate water/energy budget under given solar conditions."""
    SOLAR_MAX_KW = 4.2
    DESAL_RATE_MAX = 120  # L/sol at 100% power
    WATER_CONSUMPTION = 100  # L/sol (all crops)
    BATTERY_CAPACITY_SOLS = 2  # shields + heating autonomy

    solar_kw = SOLAR_MAX_KW * (solar_pct / 100)
    desal_rate = DESAL_RATE_MAX * (solar_pct / 100)
    daily_deficit = WATER_CONSUMPTION - desal_rate

    return {
        "solar_kw": solar_kw,
        "desal_rate_l_per_sol": desal_rate,
        "water_deficit_per_sol": max(0, daily_deficit),
        "total_deficit": max(0, daily_deficit) * storm_duration_sols,
        "pre_storm_target": WATER_CONSUMPTION * storm_duration_sols + 100,  # +100L margin
    }

@tool
def execute_pre_storm_protocol(current_water_l: float, target_water_l: float, eta_hours: float) -> dict:
    """Calculate and initiate pre-storm water/energy stockpiling."""
    water_gap = target_water_l - current_water_l
    hours_available = eta_hours - 4  # 4h margin
    desal_rate_per_hour = 120 / 24.6  # L/hour at max

    if water_gap > 0:
        hours_needed = water_gap / desal_rate_per_hour
        feasible = hours_needed <= hours_available

    return {
        "protocol": "pre_storm_stockpile",
        "actions": [
            {"device": "desalination", "action": "MAX", "duration_hours": min(hours_needed, hours_available)},
            {"device": "battery", "action": "charge_priority", "target": 100},
            {"device": "irrigation", "action": "pre_water_all_zones", "note": "+1 sol buffer"},
            {"device": "non_critical_irrigation", "action": "suspend", "zones": ["herb"]},
        ],
        "feasible": feasible,
        "projected_water_at_storm": current_water_l + (desal_rate_per_hour * min(hours_needed, hours_available)),
        "projected_autonomy_sols": (current_water_l + water_gap) / WATER_CONSUMPTION,
    }
```

### What to Build
- [ ] Resource chain model (constants: solar capacity, desal rate, consumption rates)
- [ ] Pre-storm protocol: calculate gap, time available, feasibility
- [ ] AQUA agent integration: invoke resource chain on CME detection
- [ ] Actuator commands: set desalination to max, charge battery, pre-water crops
- [ ] DynamoDB: write resource levels over time (for gauge animation)
- [ ] Dashboard: water gauge, battery gauge, solar output, desal rate (animated)

### Acceptance Criteria
- Given CME ETA of 50h and current water at 340L, agent calculates correct stockpiling plan
- Water gauge in dashboard increases over time during stockpiling
- Agent log shows AQUA's reasoning: "Deficit 320L. Running desal at MAX for 48h. Projected: 580L."
- Power allocation shifts visibly (desal gets priority)

### Dependencies
- Feature 1 (CME detection provides trigger)
- DynamoDB time-series for resource levels

---

## FEATURE 3: Virtual Farming Lab (Simulation)

**Owner**: Lars + Bryan
**Time**: ~5h
**Tier**: 2

### What It Is
Side-by-side Production vs Simulation panel. Agent generates 3 response strategies, simulates outcomes, picks best.

### How It Works
The "simulation" is NOT a physics engine. It's the ORACLE agent asking Claude to reason about outcomes given crop science from the Syngenta KB. The "simulation" is structured reasoning.

```python
@tool
def run_simulation(scenario: str, current_state: dict) -> dict:
    """Run Virtual Farming Lab: generate and evaluate 3 strategies."""
    # ORACLE agent generates strategies
    strategies = [
        {"name": "Do Nothing", "actions": []},
        {"name": "Standard Survival", "actions": ["shields", "reduce_light"]},
        {"name": "Pre-emptive Full Protocol", "actions": ["stockpile_water", "pre_harvest_vulnerable", "shields", "stress_harden"]},
    ]

    # For each strategy, ORACLE queries Syngenta KB for crop stress thresholds
    # and reasons about outcomes using Claude
    for s in strategies:
        # Query: "What happens to wheat at BBCH 60 under 70% reduced light for 5 days?"
        # Query: "Soybean recovery time after moderate radiation stress?"
        # Claude reasons about each crop's outcome given the strategy
        s["predicted_crop_loss_pct"] = ...  # from reasoning
        s["resource_cost"] = ...
        s["recovery_time_sols"] = ...

    # Select best strategy
    best = min(strategies, key=lambda s: s["predicted_crop_loss_pct"])
    best["selected"] = True

    return {"strategies": strategies, "selected": best["name"]}
```

### What to Build
- [ ] Strategy generator: 3 candidates per threat (hardcoded templates is fine for hackathon)
- [ ] Syngenta KB queries: crop stress thresholds per growth stage
- [ ] ORACLE agent: reason about outcomes per strategy using KB data
- [ ] Strategy comparison: rank by crop survival %, resource cost, recovery time
- [ ] Dashboard panel: side-by-side Production (left) vs Simulation Lab (right)
- [ ] Dashboard: Strategy A/B/C cards with predicted outcomes
- [ ] Dashboard: "SELECTED: BEST OUTCOME" badge on winning strategy
- [ ] Dashboard: "APPLY" button (or auto-apply with log entry)

### Acceptance Criteria
- Given a CME scenario, 3 strategies appear in the Simulation Lab panel
- Each strategy shows: name, predicted crop loss %, resource cost, recovery time
- Best strategy is highlighted with green border
- Agent log shows ORACLE's reasoning including KB query results
- Selecting a strategy triggers the corresponding actions in the Production side

### Dependencies
- Feature 1 (CME scenario triggers simulation)
- Syngenta MCP KB access
- Dashboard frontend

---

## FEATURE 4: Agent Council (Multi-Agent Debate)

**Owner**: Lars
**Time**: ~3h
**Tier**: 3

### What It Is
5 named agents (FLORA, AQUA, VITA, SENTINEL, ORACLE) that visibly debate decisions in the agent log.

### How It Works (Pragmatic)
With 20h remaining, building 5 separate Strands Agent instances is risky. **Pragmatic approach**: ONE agent with a structured system prompt that generates council-style reasoning. Each "agent" is a named reasoning perspective.

```python
COUNCIL_SYSTEM_PROMPT = """
You are the EDEN greenhouse control plane. You reason through decisions by consulting
5 internal perspectives, each a specialist:

- SENTINEL: Threat detection and risk assessment. Speaks first on any alert.
- ORACLE: Simulation results and strategy recommendations.
- AQUA: Resource management (water, energy, nutrients). Calculates budgets.
- FLORA: Crop health advocacy. Argues for plant survival and growth optimization.
- VITA: Crew nutrition and morale. Translates crop decisions into human impact.

When making a decision, structure your reasoning as a council debate:
[SENTINEL]: <threat assessment>
[ORACLE]: <simulation results>
[AQUA]: <resource calculation>
[FLORA]: <crop impact>
[VITA]: <crew impact + ethical triage>
[COUNCIL VOTE]: <decision + reasoning>

Use BBCH growth stage codes. Query the Syngenta KB for specific thresholds.
Surface human cost of every triage decision explicitly.
"""
```

If time allows, upgrade to actual multi-agent with Strands SDK `agent-workflows` patterns.

### What to Build
- [ ] System prompt with 5 perspectives and council debate format
- [ ] Agent output parser: extract [AGENT_NAME]: lines for dashboard display
- [ ] Color-coded agent log: each agent name gets a different color
- [ ] Council vote summary: "COUNCIL VOTE: Strategy C adopted. 5/5 in favor."
- [ ] Ethical triage line: VITA always adds crew impact statement

### Acceptance Criteria
- Agent log shows clearly labeled debate between 5 named agents
- Each agent contributes their specialist perspective
- VITA includes human cost in every triage decision
- Council vote is visible and decisive
- Dashboard colors each agent differently (SENTINEL=red, AQUA=cyan, FLORA=green, VITA=purple, ORACLE=amber)

### Dependencies
- Bedrock Claude access via Strands SDK
- Dashboard agent log component with color parsing

---

## FEATURE 5: Ethical Triage Dashboard

**Owner**: Bryan (frontend) + Lars (agent logic)
**Time**: ~2h
**Tier**: 3

### What It Is
When the agent makes triage decisions (deprioritize a crop, evict a zone), the dashboard surfaces the HUMAN COST — not just what changed, but what it means for the crew.

### What to Build
- [ ] Triage data structure: `{crop, zone, decision, salvageability_score, crew_impact, mitigation, confidence}`
- [ ] Agent generates triage entries with crew impact for every resource reallocation
- [ ] Dashboard panel: Triage cards with color coding (RED/YELLOW/GREEN/BLACK)
- [ ] Each card shows: crop name, salvageability score, crew impact statement
- [ ] Crew impact examples:
  - "Vitamin C drops to 68% of minimum. Scurvy risk: Sol 292."
  - "Protein output reduced 12%. Mitigation: increase lentil allocation."
  - "Dr. Chen's preferred spinach deprioritized. Substituting microgreens."

### Acceptance Criteria
- Every triage decision has a visible crew impact statement
- Triage cards are color-coded by salvageability
- At least one decision references a crew member by name

### Dependencies
- Feature 4 (Council generates triage decisions)

---

## FEATURE 6: Nutritional Tracking

**Owner**: Bryan
**Time**: ~3h
**Tier**: 4

### What It Is
4 astronauts × 450 days. Per-nutrient progress bars. Gap detection triggers crop scaling.

### What to Build
- [ ] Nutritional model: daily requirements (2,500 kcal, 60g protein, vitamins per astronaut)
- [ ] Crop yield projections: growth rate × area × remaining days
- [ ] Gap detection: projected_yield vs required_intake per nutrient
- [ ] HPA trigger: when gap detected, VITA recommends scaling up relevant crops
- [ ] Dashboard: Per-nutrient progress bars (Protein / Carbs / Vitamins / Calories)
- [ ] Dashboard: "ON TRACK" / "GAP DETECTED" status per nutrient
- [ ] Query Syngenta KB: "nutritional content per crop per kg"

### Acceptance Criteria
- Dashboard shows 4 progress bars with percentage
- When protein projected below 80%, agent recommends adding soybean pods
- Syngenta KB is queried for nutritional data (visible in agent log)

### Dependencies
- Syngenta MCP KB access
- DynamoDB for crop state tracking

---

## FEATURE 7: Dashboard Core (React)

**Owner**: Bryan
**Time**: ~6h total (built incrementally alongside other features)
**Tier**: Spans all tiers

### What to Build
- [ ] Dark theme: #0a0c10 bg, Mars amber (#e8913a) accents, Space Grotesk + JetBrains Mono
- [ ] Agent Log panel: color-coded per council member, 18-20px font, max 5 lines visible
- [ ] Sol Counter: ticking, 48px+ font
- [ ] Cluster Status: 3 zones with health gauges
- [ ] Water/Energy panel: 4 resource bars (water, battery, solar, desal) with animation
- [ ] CME Alert: full-width banner + 64px countdown timer (appears on detection)
- [ ] Virtual Lab panel: side-by-side with strategy cards (appears on simulation)
- [ ] Triage panel: color-coded cards with crew impact
- [ ] Nutrition bars: 4 per-nutrient progress bars
- [ ] Dashboard state: NOMINAL → ALERT → CRISIS → RECOVERY color transitions
- [ ] Physical sync: WebSocket/MQTT to Pi for LED control

### Key UX Rules (from judge panel)
- Progressive disclosure: not all panels visible at once
- Alert state: 60% screen becomes CME + countdown + Virtual Lab
- Font sizes: readable from 5 meters on projector
- Color shift on state change (dark blue → amber → red → warm green)

### Dependencies
- Amplify deployment (Bryan already setting up)
- DynamoDB streams or polling for real-time updates
- Agent writing state to DynamoDB

---

## FEATURE 8: Physical Prop Integration

**Owner**: Johannes + PJ
**Time**: ~4h
**Tier**: Parallel (physical team)

### What to Build
- [ ] Pi reads sensors (temp, humidity, soil moisture, light) every 10s
- [ ] Pi publishes to MQTT topic → IoT Core
- [ ] Pi subscribes to actuator commands from agent
- [ ] LED strip: warm-white (nominal) → amber (alert) → dim red (crisis) → warm-white (recovery)
- [ ] LED transitions: 5-second gradual fade, not instant
- [ ] Real plant inside the enclosure (basil or lettuce)
- [ ] Fan: ON during nominal, OFF during crisis (sound cue — sudden quiet)
- [ ] Position prop BETWEEN screen and judges during pitch

### Acceptance Criteria
- LEDs respond to agent commands within 2 seconds
- Visible dimming during storm demo
- Real plant is alive and visible
- Fan stopping is audible

### Dependencies
- Agent actuator commands via HTTP (Lars)

---

## FEATURE 9: Custom AgentCore Gateway Targets

**Owner**: Lars
**Time**: ~2h total (30min per target)
**Tier**: AWS Bonus (HIGH value)

### What It Is
Wrap our own APIs/Lambdas as MCP tools through the AgentCore Gateway. Transforms "we used the provided endpoint" into "we built a multi-target gateway architecture."

### The 6-Target Gateway

```
AgentCore Gateway
├── Syngenta KB target        (PROVIDED — knowledge base, 7 domains)
├── DONKI Solar target        (CUSTOM — OpenAPI spec → MCP, solar events)
├── USDA FoodData target      (CUSTOM — OpenAPI spec → MCP, nutritional data)
├── NASA POWER target         (CUSTOM — OpenAPI spec → MCP, solar irradiance)
├── Simulation Lambda target  (CUSTOM — Lambda, crop outcome modeling)
└── Mars Transform target     (CUSTOM — Lambda, Earth→Mars sensor conversion)
```

1 provided + 5 custom targets. Agent uses ONE gateway for knowledge (Syngenta + USDA), external data (DONKI + NASA POWER), and compute (Simulation + Mars Transform).

### Target 1: DONKI CME as MCP Tool (~30min)

Follow the OpenAPI-to-MCP tutorial from the AgentCore samples repo.

```python
# 1. Write OpenAPI spec for DONKI CME endpoint
donki_openapi = {
    "openapi": "3.0.0",
    "info": {"title": "NASA DONKI", "version": "1.0"},
    "paths": {
        "/DONKI/CME": {
            "get": {
                "operationId": "get_cme_events",
                "summary": "Get recent Coronal Mass Ejection events from NASA DONKI",
                "parameters": [
                    {"name": "startDate", "in": "query", "schema": {"type": "string"}},
                    {"name": "endDate", "in": "query", "schema": {"type": "string"}},
                    {"name": "api_key", "in": "query", "schema": {"type": "string"}}
                ]
            }
        }
    }
}

# 2. Upload to S3
# 3. Create gateway target with API key credential provider
gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='NasaDONKI',
    targetConfiguration={"mcp": {"openApiSchema": {"s3": {"uri": "s3://bucket/donki-spec.json"}}}},
    credentialProviderConfigurations=[api_key_config]
)
```

### Target 2: Simulation Lambda (~30min)

The Virtual Farming Lab as a Gateway target. Agent calls `simulate_crop_outcome` through the gateway.

```python
# Lambda handler
def handler(event, context):
    tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    params = json.loads(event["body"])

    if "simulate_crop_outcome" in tool_name:
        crop = params["crop"]
        stress_type = params["stress_type"]  # "radiation", "drought", "temperature"
        severity = params["severity"]  # 0.0-1.0
        duration_sols = params["duration_sols"]
        growth_stage_bbch = params["growth_stage_bbch"]

        # Lookup table based on Syngenta KB data (pre-extracted)
        survival = CROP_STRESS_TABLE[crop][stress_type][severity_bucket(severity)]
        yield_impact = survival * GROWTH_STAGE_MODIFIER[growth_stage_bbch]
        recovery_sols = RECOVERY_TABLE[crop][stress_type]

        return {
            "crop": crop,
            "predicted_survival_pct": round(survival * 100, 1),
            "yield_impact_pct": round((1 - yield_impact) * 100, 1),
            "recovery_sols": recovery_sols,
            "confidence": 0.85,
            "source": "EDEN simulation engine v1 + Syngenta KB stress data"
        }

# Gateway target
gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='EDENSimulation',
    targetConfiguration={"mcp": {"lambda": {
        "lambdaArn": simulation_lambda_arn,
        "toolSchema": {"inlinePayload": sim_tool_spec}
    }}},
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
)
```

### Target 3: Mars Transform Lambda (~30min)

Earth sensor data → Mars-adjusted values. Already building this — just route through Gateway.

```python
# Tool spec
mars_transform_tool = {
    "name": "transform_to_mars",
    "description": "Convert Earth sensor readings to Mars-equivalent values for the greenhouse dome",
    "parameters": {
        "earth_temp_c": {"type": "number"},
        "earth_humidity_pct": {"type": "number"},
        "earth_pressure_hpa": {"type": "number"},
        "sol": {"type": "integer"},
        "inject_event": {"type": "string", "enum": ["none", "dust_storm", "cme_impact", "pressure_breach"]}
    }
}
```

### Target 4: USDA FoodData Central (~30min)

Detailed nutritional data per 100g for every crop. Cross-reference with Syngenta KB — agent synthesizes from TWO knowledge sources.

```python
# OpenAPI spec for USDA FoodData Central
usda_openapi = {
    "openapi": "3.0.0",
    "info": {"title": "USDA FoodData Central", "version": "1.0"},
    "servers": [{"url": "https://api.nal.usda.gov/fdc/v1"}],
    "paths": {
        "/foods/search": {
            "get": {
                "operationId": "search_food_nutrition",
                "summary": "Search USDA food database for detailed nutritional breakdown per 100g",
                "parameters": [
                    {"name": "query", "in": "query", "schema": {"type": "string"},
                     "description": "Food name, e.g. 'soybean raw', 'wheat grain', 'potato raw'"},
                    {"name": "pageSize", "in": "query", "schema": {"type": "integer", "default": 3}},
                    {"name": "api_key", "in": "query", "schema": {"type": "string"}}
                ]
            }
        }
    }
}

# Gateway target — same pattern as DONKI
gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='USDANutrition',
    targetConfiguration={"mcp": {"openApiSchema": {"s3": {"uri": "s3://bucket/usda-spec.json"}}}},
    credentialProviderConfigurations=[api_key_config]  # USDA API key (free)
)
```

**Why this matters for judges**: Agent queries Syngenta KB ("what does wheat provide in this growth scenario?") AND USDA ("exact macros: 339 kcal, 13.2g protein, 2.5g fat per 100g wheat grain"). Cross-referencing two sources shows the agent AUGMENTS the provided KB. Syngenta judge: "They're not just using our data — they're enriching it."

### Target 5: NASA POWER API (~30min)

Solar irradiance data. Feeds the water/energy chain model: solar flux at Mars latitude/season → panel efficiency → desalination capacity.

```python
# OpenAPI spec for NASA POWER
power_openapi = {
    "openapi": "3.0.0",
    "info": {"title": "NASA POWER", "version": "1.0"},
    "servers": [{"url": "https://power.larc.nasa.gov/api"}],
    "paths": {
        "/temporal/daily/point": {
            "get": {
                "operationId": "get_solar_irradiance",
                "summary": "Get solar irradiance and meteorological data for a location",
                "parameters": [
                    {"name": "parameters", "in": "query", "schema": {"type": "string"},
                     "description": "Comma-separated: ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN"},
                    {"name": "community", "in": "query", "schema": {"type": "string", "default": "RE"}},
                    {"name": "longitude", "in": "query", "schema": {"type": "number"}},
                    {"name": "latitude", "in": "query", "schema": {"type": "number"}},
                    {"name": "start", "in": "query", "schema": {"type": "string"}},
                    {"name": "end", "in": "query", "schema": {"type": "string"}},
                    {"name": "format", "in": "query", "schema": {"type": "string", "default": "json"}}
                ]
            }
        }
    }
}

gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='NASAPower',
    targetConfiguration={"mcp": {"openApiSchema": {"s3": {"uri": "s3://bucket/power-spec.json"}}}},
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]  # No key needed
)
```

**Why this matters**: Agent says "Solar flux at Ls 220 = 493 W/m². Panel efficiency: 22%. Available power: 4.2 kW. Desalination capacity: 120L/sol. Source: NASA POWER API." Real data feeding real calculations.

### Acceptance Criteria
- Agent calls tools through Gateway URL (not direct Lambda/API calls)
- Gateway logs show tool invocations
- At least 3 custom targets created beyond the provided Syngenta endpoint
- Agent log shows source attribution: "Source: USDA FoodData Central", "Source: NASA POWER"
- Cross-referencing visible: agent queries Syngenta KB AND USDA for same crop, synthesizes both

### Dependencies
- AgentCore Gateway access (from hackathon AWS account)
- Lambda functions deployed
- S3 bucket for OpenAPI specs
- USDA API key (free: https://api.nal.usda.gov/fdc — sign up takes 2 min)
- NASA POWER API (no key needed)

---

## FEATURE 10: Mission Architect Mode (Day -1 Planning)

**Owner**: Lars
**Time**: ~1h (one structured LLM call + display)
**Tier**: 7 (High-leverage polish — wild card)

### What It Is
Before the crisis demo, agent generates a complete 450-sol mission plan from constraints. Opens the demo with PLANNING, not just reacting. "On Sol 1, it already planned every harvest through Sol 450."

### How It Works
Single LLM call with structured output. The prompt includes:
- Mission constraints (cargo kg, dome area, crew size, duration)
- Syngenta KB crop profiles (pre-queried)
- Nutritional requirements per astronaut

```python
@tool
def generate_mission_plan(
    cargo_kg: float,
    dome_area_m2: float,
    crew_size: int,
    mission_sols: int
) -> dict:
    """Generate optimal greenhouse configuration for a Mars mission."""
    # This is a single structured LLM call
    # Agent reasons about: crop selection, zone allocation, planting schedule,
    # resource requirements, companion planting, risk assessment
    # Returns structured JSON that the dashboard renders as a plan view

    return {
        "zones": [
            {"name": "Protein", "area_m2": 30, "crops": [
                {"name": "Soybean", "area": 20, "first_harvest_sol": 90, "cycles": 4},
                {"name": "Lentil", "area": 10, "first_harvest_sol": 85, "cycles": 4}
            ]},
            # ... other zones
        ],
        "companion_pairs": [
            {"crops": ["Soybean", "Wheat"], "benefit": "N-fixation -18% nutrients"}
        ],
        "resource_requirements": {
            "water_reserve_l": 500,
            "desal_rate_l_sol": 120,
            "solar_kw": 4.2,
            "seed_reserve_multiplier": 3.0
        },
        "nutritional_projection": {
            "calories_pct": 108,
            "protein_pct": 94,
            "vitamin_pct": 87
        },
        "risk_flags": [
            "Wheat flowering (BBCH 60) overlaps Ls 220 storm season",
            "Protein gap Sol 1-80 before first soybean harvest"
        ],
        "extension_triggers": [
            "If crew > 4: add 12m² protein module",
            "If mission extends > 500 sols: add rotation buffer zone"
        ]
    }
```

### Dashboard Display
Simple structured view — NOT a complex visualization. A "mission briefing" card:
```
EDEN MISSION PLAN — 4 crew × 450 sols
Zones: Protein (30m²) | Carb (30m²) | Vitamin (25m²) | Support (15m²)
Projected: 108% cal | 94% protein | 87% vitamins
Risk: Wheat flowering overlaps storm season
Next harvest: Sol 45 (Spinach, Zone C)
```

### Why This Is a Wild Card
- Nobody else opens with planning. Every other team shows reacting.
- Shows the agent THINKS strategically, not just tactically
- The plan becomes the "desired state" — every crisis is about PROTECTING this plan
- K8s: this is the manifest. The agent is the reconciliation loop.
- Pitch: "Everything you see next is about protecting this plan."

### Acceptance Criteria
- Agent generates structured mission plan from constraints
- Plan includes: zones, crops, nutritional projection, risk flags
- Dashboard displays plan as a briefing card
- Plan references Syngenta KB data (companion planting, crop profiles)

### Dependencies
- Syngenta KB access (for crop profiles)
- Dashboard component for plan display
