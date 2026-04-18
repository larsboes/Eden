# EDEN — Q&A Defense for AWS Solutions Architects & Judges

> Prepared answers for tough technical questions. Read before any AWS/Syngenta conversation.

---

## "Why 12 agents and not just one well-prompted agent?"

One agronomist can't also be a soil scientist, a pathologist, a nutritionist, an energy engineer, and a crew psychologist. On Earth, a farm has specialists. EDEN's parliament IS that specialist team.

Each agent has a fundamentally different **loss function**:

| Agent | Optimizes For | Would Sacrifice |
|---|---|---|
| SENTINEL | Crew survival probability | All crops to prevent 1% suffocation risk |
| FLORA | Individual plant survival | Water budget for one zone's needs |
| VITA | Nutritional completeness | Caloric density for vitamin diversity |
| AQUA | Water efficiency | Short-term yield to preserve reserves |
| HESTIA | Crew morale & food culture | Caloric crops for morale crops (basil over wheat) |
| ORACLE | Long-term mission outcome | Today's yield for mission-arc optimization |
| PATHFINDER | Disease prevention | Growth speed for quarantine safety margins |
| CHRONOS | 450-day timeline | Short-term crisis response for long-term food security |

A single agent with all these objectives in one prompt **collapses to the loudest objective** (typically calories or safety). The parliament forces every objective to be advocated, then the COORDINATOR resolves tension via an explicit priority hierarchy: safety > plant health > yield > atmosphere > resources > nutrition > timeline > morale.

**Concrete example — why this matters agriculturally:**

> Sol 312. Water at 35%. A single agent says: "Save potato — 2,400 kcal/kg." Obvious.
>
> But VITA sees: crew iron drops below 60% threshold without spinach. Dr. Okafor already showing fatigue.
> HESTIA sees: Cmdr. Chen hasn't had fresh greens in 47 sols. Morale dipping.
> ORACLE runs 100 Monte Carlo simulations: save spinach + accelerate radish from quick-harvest reserve has HIGHER total mission caloric output at p50.
>
> The "obvious" caloric choice was wrong. A single agent can't surface this trade-off. 12 specialists can.

---

## "Couldn't you do the same with 3 agents?"

We considered that. Three agents — plants, resources, safety. The problem: when PATHFINDER detects fungal pressure from humidity >80% at the same time AQUA wants to increase irrigation, neither can resolve the conflict from their own perspective. You need ATMOS to say "I can increase airflow to drop humidity without reducing irrigation." That resolution requires a third domain perspective that neither PATHFINDER nor AQUA holds.

The 12-agent structure maps to real agricultural specialization, not arbitrary AI complexity:

- **DEMETER + FLORA + TERRA** = crop science team (canopy, roots, soil)
- **AQUA + HELIOS + ATMOS** = systems engineering team (water, power, air)
- **VITA + HESTIA + CHRONOS** = mission planning team (nutrition, morale, timeline)
- **SENTINEL + PATHFINDER + ORACLE** = risk team (safety, disease, forecasting)

Each group of 3 has internal knowledge that the other groups don't naturally consider. The parliament surfaces cross-group conflicts.

---

## "Is this actually multi-agent, or just different system prompts on the same model?"

It's real multi-agent with genuine tool calling via the Strands Agents SDK.

Each agent is a `strands.Agent` instance with access to 13 tool functions. They don't just generate text — they make real function calls:

| Tool | What It Does | Primary User |
|---|---|---|
| `read_sensors(zone_id)` | Live sensor telemetry from a zone | FLORA, DEMETER |
| `read_all_zones()` | All zones at once | SENTINEL, COORDINATOR |
| `query_syngenta_kb(query)` | Query Syngenta Knowledge Base via MCP Gateway | DEMETER, PATHFINDER, TERRA |
| `check_weather_on_mars()` | NASA DONKI + InSight data via MCP | SENTINEL, ORACLE |
| `run_simulation(scenario, n_runs)` | Monte Carlo crop simulation (GDD, Liebig's Law, VPD) | ORACLE |
| `propose_new_flight_rule(...)` | Propose deterministic safety rules from observed patterns | SENTINEL |
| `triage_zone(zone_id)` | Score zone salvageability during crisis | SENTINEL, COORDINATOR |
| `set_actuator_command(zone, device, action)` | Control pumps, fans, lights, heaters | Any agent |
| `get_nutritional_status()` | Crew caloric/protein intake vs targets | VITA, HESTIA |
| `get_desired_state(zone_id)` | Target environmental ranges per zone | DEMETER, ATMOS |
| `query_telemetry_trends(zone, hours)` | Historical sensor data for trend analysis | ORACLE, PATHFINDER |
| `get_mars_conditions(sol)` | Mars environment: exterior temp, solar irradiance, dust | HELIOS, ATMOS |
| `request_crew_intervention(task, urgency)` | Request astronaut time (scarce resource) | Any agent |

The 3-round deliberation is structurally adversarial:
1. **Round 1**: All 12 specialists analyze in parallel (ThreadPoolExecutor, 14 workers)
2. **Round 2**: Selected agents respond to each other BY NAME — "I disagree with CHRONOS because..."
3. **Round 3**: COORDINATOR synthesizes into a prioritized consensus with IMMEDIATE / SHORT-TERM / DEFERRED / MONITORING tiers

---

## "What's the architecture? Walk me through a single decision cycle."

Every 30 seconds, the reconciler loop executes:

```
1. COLLECT     → Read all zone sensor data (in-memory, <1ms)
2. TRANSFORM   → Apply Mars physics: 43% solar, 700 hPa dome, seasonal coupling
3. ENRICH      → Merge real NASA data (InSight weather, DONKI solar events)
4. FLIGHT RULES → 17 deterministic rules run FIRST, ALWAYS (Tier 0, 0ms)
                  Fire → emergency shutdown. O2 < 18% → increase exchange.
                  Rate-of-change > 5C/5min → emergency ventilation.
5. EXECUTE     → Flight rule commands sent immediately. No waiting.
6. PERSIST     → Telemetry → SQLite (local) + DynamoDB (cloud sync)
7. DELTA       → Compare actual vs desired state per zone
8. PARLIAMENT  → If deltas exist: invoke 12-agent debate (Tier 2)
9. FEEDBACK    → Compare this cycle to last: did our actions help?
                  Inject feedback into next cycle (closed-loop learning)
```

Key insight: **Flight rules are NOT a fallback. They run EVERY cycle BEFORE the AI.** The AI parliament only activates when conditions drift outside desired ranges. This means EDEN is safe even with zero connectivity to any model.

---

## "How does the simulation engine work? Is it real math or LLM text?"

Real math. Zero LLM involvement. ~850 lines of pure Python with zero external dependencies.

**Models implemented:**
- **GDD thermal time accumulation** — standard agronomy since 1960. `gdd_today = max(0, air_temp - base_temp)`
- **Liebig's Law of the Minimum** — growth limited by most deficient factor: `stress = min(temp, water, light, radiation, disease, bolting, tuberization)`
- **Trapezoidal temperature stress** — linear decay outside optimal range, not a step function
- **VPD (Vapor Pressure Deficit)** via Tetens equation — THE metric for CEA disease prediction
- **DLI (Daily Light Integral)** — mol/m2/day from PPFD and photoperiod
- **Stage-aware radiation sensitivity** — flowering is 1.5x more vulnerable than vegetative
- **Crop-specific modifiers** — bolting stress for spinach/lettuce, tuberization factor for potato
- **Resource chain cascade** — solar → power → desalination → water → crops
- **Transpiration recovery** — 95% water recovered in closed Mars greenhouse

6 crops fully parameterized: soybean, potato, wheat, tomato, spinach, lettuce.

**Monte Carlo engine:** N runs (default 50-100) with Gaussian-perturbed parameters (water reserve, battery, temperature, humidity, event severity). Produces confidence intervals (p5/p50/p95), survival probability, kcal/liter efficiency. Strategies are ranked by caloric efficiency for nominal scenarios, yield loss for crisis scenarios.

**Example output (ORACLE calls `run_simulation("nominal")`):**

```
Strategy B — Redirect 30% Protein→Carb for 5 days:
  Soybean yield: -2.4% | Potato yield: +10%
  Net calories: +25% from same water budget
  Monte Carlo 95% CI: +1,400 to +2,800 kcal net gain
  Confidence: 95% net positive

Strategy C — Redirect 50%:
  Soybean yield: -13% | Potato yield: +12.5%
  Monte Carlo: only 88% confidence — soybean stress too high at p95
  REJECTED: diminishing returns past 30% reallocation
```

This is what makes the parliament grounded. ORACLE doesn't say "I think Strategy B is better." ORACLE says "100 runs of math say Strategy B is better, with 95% confidence."

---

## "How does this use AWS services?"

| AWS Service | How EDEN Uses It |
|---|---|
| **Bedrock** (Claude Sonnet 4) | LLM backbone for all 12 agents via Converse API |
| **Strands Agents SDK** | Tool-calling agent framework — each specialist is a `strands.Agent` |
| **AgentCore Gateway** | MCP endpoint routing to Syngenta KB + NASA APIs with Cedar policies |
| **AgentCore Runtime** | Managed deployment: Dockerfile → ECR → Firecracker MicroVM per session |
| **DynamoDB** | Cloud telemetry sync (local SQLite is source of truth, DynamoDB is backup) |
| **MCP Protocol** | Syngenta KB via streamable HTTP, NASA APIs via stdio subprocess |

Architecture follows the Lab 01 → 03 → 04 → 06 progression from the AgentCore samples:
- Lab 01: Local agent with `@tool` decorators + KB RAG
- Lab 03: Gateway wrapping Syngenta MCP + NASA APIs + Cedar access control
- Lab 04: Deploy to AgentCore Runtime (4 lines of code change)
- Lab 06: SSE streaming from Runtime to React dashboard

---

## "What happens when the model is unavailable?"

Graceful degradation across 3 tiers:

| Tier | Latency | What | When Model Down? |
|---|---|---|---|
| **Tier 0: Flight Rules** | 0ms | 17 deterministic rules | Always runs. EDEN is safe with zero AI. |
| **Tier 1: Local Model** | ~2s | Ollama (llama3.2:3b) | Fallback if Bedrock unreachable |
| **Tier 2: Cloud Model** | ~5s | Bedrock Claude Sonnet 4 | Primary — 12-agent parliament |

The ModelChain cascading failover: try Bedrock → try Ollama → fail gracefully. Flight rules always hold the safety floor regardless.

MCP adapters have the same pattern: 5-minute cache TTL on all KB queries, graceful offline fallback. If Syngenta KB is unreachable, agents run with local crop science knowledge hardcoded in the simulation engine (Layer 1 parameterization from 60 years of published agronomy).

---

## "Does the system actually learn?"

Yes. Two mechanisms:

**1. Closed-loop feedback (every cycle):**
The reconciler compares current zone state to previous cycle: "Did our cooling action actually reduce temperature? Did irrigation increase humidity?" This feedback is injected into the next parliament cycle via `set_feedback()`. Agents see: "Previous cycle: cooling action in sim-alpha reduced temperature from 28.1°C to 26.3°C — action was effective."

**2. Flight rule proposal (event-driven):**
SENTINEL can call `propose_new_flight_rule()` to create candidate rules from observed patterns. Example:

```
SENTINEL [Sol 249]: Post-storm debrief.
  Observed: Zone B moisture deficit during hours 38-42.
  Stockpiling started at T-48h — needed T-55h for full zone saturation.

  PROPOSING: FR-CME-014
    IF cme_eta > 55h AND water_reserve < 80% THEN begin_stockpiling

  ORACLE validates via simulation:
    With rule: mean loss 2.1% (CI: 1.2%-3.3%)
    Without:   mean loss 4.3% (CI: 2.8%-6.1%)
    Improvement: 2.2 percentage points. Promoting.
```

Candidates are stored separately from active rules (safety gate — NOT auto-activated). This is how 17 rules on Sol 1 grow over 450 sols.

---

## "What's novel here? What does this do that other teams won't?"

1. **Mathematical simulation backing every decision.** Other teams will have LLMs saying "I recommend Strategy B." EDEN has 100 Monte Carlo runs saying Strategy B yields 25% more calories from the same water, with 95% confidence. Math produces numbers, LLM produces meaning.

2. **Cross-domain insight generation.** EDEN's simulation cross-references Syngenta KB domains to find optimizations that exist in NO single document. Example: "Soybean at early vegetative tolerates 72h water stress. Potato at tuber initiation suffers irreversible yield loss." No KB document says "redirect water from soybean to potato" — EDEN discovers it.

3. **Genuine adversarial debate, not personas.** Round 2 deliberation where PATHFINDER says "I disagree with DEMETER because humidity >80% creates Botrytis risk that your growth optimization ignores" — this surfaces blind spots a single agent architecturally cannot find.

4. **The crew psychology dimension.** HESTIA is a genuinely novel agent. "Dr. Chen is Italian — hasn't had anything resembling a caprese in 200 sols." Food as emotional anchor, not just calories. NASA's own research confirms meal monotony is the #1 psychological risk on long missions.

5. **K8s-pattern reconciliation loop.** Not just "check sensors, call AI." Declarative desired state, delta computation, deterministic safety floor, AI only when needed, closed-loop feedback. This is how production infrastructure works — applied to agriculture.
