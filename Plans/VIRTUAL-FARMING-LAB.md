# Virtual Farming Lab — Feature Spec & Implementation Plan

> Layer 3: "The Dreamer" — Monte Carlo simulation engine for EDEN
> Status: DESIGNED, ready to implement
> Build budget: 2-4 hours, one developer
> Output: `eden/domain/simulation.py` (~250 lines pure Python)

---

## The Problem

EDEN's 4-layer architecture claims Layer 3 "The Dreamer" runs Monte Carlo simulations of possible futures via a "Virtual Farming Lab." The concept docs, demo script, and dashboard mockups all reference this as a core capability. But the actual code has ZERO simulation logic. ORACLE is an LLM persona that generates text about predictions. `run_simulation()` is listed as an agent tool but never implemented.

The critique (CONCEPT-CRITIQUE-AND-FIXES.md) correctly identifies: "Monte Carlo of what model? With what parameters? Your model is an LLM. LLMs don't do Monte Carlo — they generate plausible-sounding text."

**This is the single biggest honesty gap in the project.**

---

## First Principles Decomposition

### What IS a crop simulation?

At the most fundamental level, a crop grows by converting inputs (light, water, CO2, nutrients) into biomass over time. Every crop simulation in history — from the 1960s CERES model to modern DSSAT — models this same thing:

```
biomass(t+1) = biomass(t) + growth_rate(t) × dt
```

Where `growth_rate` is a function of environmental inputs. That's it. Everything else is parameterization.

**Constituent parts of crop growth:**
1. **Thermal time accumulation** — plants don't care about days, they care about degree-days. Growth = sum of (daily_temp - base_temp) over time. This is the single most important variable in crop modeling. Every agronomist knows this.
2. **Light interception** — photosynthesis is proportional to intercepted PAR (photosynthetically active radiation). Simplified: `light_efficiency × PAR × leaf_area`
3. **Water limitation** — if water < optimal, growth is reduced by a ratio. Classic: `actual_ET / potential_ET`
4. **Nutrient limitation** — Liebig's Law of the Minimum: growth limited by whichever nutrient is most deficient
5. **Stress response** — deviation from optimal reduces growth multiplicatively: `growth × temp_stress × water_stress × light_stress`

### What IS Monte Carlo?

Monte Carlo = run the same deterministic model N times with randomly perturbed inputs. It's statistics, not AI:

```python
results = []
for i in range(N):
    perturbed_params = add_gaussian_noise(base_params)
    outcome = run_simulation(perturbed_params)
    results.append(outcome)
confidence = percentile(results, [5, 50, 95])
```

That's genuinely it. The "Monte" is the noise. The "Carlo" is running it many times. Any freshman statistics student can implement this.

### What IS a strategy comparison?

A strategy is a sequence of actions over time in response to a threat:
- Strategy A: Do nothing (baseline)
- Strategy B: Standard response (follow existing flight rules)
- Strategy C: Aggressive pre-emptive (stockpile, pre-harvest, stress-harden)

Each strategy modifies the simulation inputs differently over the threat window. Compare outcomes.

---

## Constraint Classification

| Constraint | Type | Evidence | Challenge |
|---|---|---|---|
| "Monte Carlo requires a PhD-level crop model" | **ASSUMPTION — FALSE** | DSSAT is complex, but the core is `growth += rate × stress_factors × dt` | A 200-line Python model with correct structure beats an LLM saying "Monte Carlo" |
| "Crop models need external libraries (numpy, scipy)" | **SOFT — project law says pure Python** | Statistics needs: mean, stdev, percentile. All implementable in 10 lines of stdlib `math` + `random` | Pure Python Monte Carlo is trivially doable |
| "Simulation must predict real crop yields accurately" | **ASSUMPTION — FALSE** | It must be *structurally correct* and *directionally accurate*. Judges check: "Does stress reduce growth? Does more water help?" Not: "Is potato yield exactly 4.2 kg/m²?" | Relative accuracy matters, not absolute |
| "Need real-time simulation during demo" | **SOFT** | 100 Monte Carlo runs of a 50-day window with 6 crops × 5 stress factors = ~30K calculations. Pure Python does this in <1 second | No performance concern whatsoever |
| "Syngenta KB data must parameterize the model" | **HARD** | Challenge requirement: "Usage of the provided AWS AgentCore system." KB has crop profiles, stress thresholds, optimal ranges | But can be pre-queried and cached — don't need live MCP calls during simulation |
| "Must integrate with existing architecture" | **HARD** | Reconciler, agents, flight rules are the system | Simulation is a pure function called BY the agent — it doesn't replace anything |
| "2-4 hour build budget" | **HARD** | Hackathon time constraint is real | This scopes the model complexity ceiling |
| "LLM agents can't do math" | **HARD (physics)** | LLMs generate text, not compute deterministic functions | Simulation MUST be code, agents INVOKE it via tool call |

**Key insight:** The assumption that "simulation = complex" is WRONG. Simulation is arithmetic in a loop. What makes it a *simulation* vs *text generation* is:
1. Deterministic reproducibility (same inputs → same outputs)
2. Mathematical relationships between variables
3. Quantifiable uncertainty (Monte Carlo spread)
4. Falsifiability (predictions can be compared to actuals)

An LLM has NONE of these properties. Even a crude math model has ALL of them.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  CropGrowthModel (pure math, ~80 lines)             │
│                                                      │
│  For each day in simulation window:                  │
│    thermal_units += max(0, temp - base_temp)         │
│    growth_stage = thermal_units / total_thermal_req  │
│    daily_growth = max_growth_rate × stress_factor    │
│    stress_factor = min(temp_s, water_s, light_s,     │
│                        radiation_s, disease_s)       │
│    biomass += daily_growth                           │
│    water_consumed += water_rate(growth_stage)        │
│    yield_at_harvest = biomass × harvest_index        │
│  Returns: {yield_kg, water_used, days_to_harvest,    │
│            stress_events, survival_probability}      │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  ResourceChainModel (~40 lines)                      │
│                                                      │
│  solar_output = base_kw × (1 - dust_opacity)        │
│  power_available = solar_output + battery_discharge  │
│  desal_rate = min(max_desal, power_available × eff)  │
│  water_in = desal_rate + recovery_from_transpiration │
│  water_out = sum(crop_water_consumption per zone)    │
│  water_balance = reserve + water_in - water_out      │
│  Returns: {water_reserve_trajectory, power_trajectory,│
│            desal_trajectory}                          │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  ScenarioEngine (~60 lines)                          │
│                                                      │
│  Apply event to environmental timeline:              │
│    CME → radiation spike + dust opacity increase     │
│    Drought → water supply reduction                  │
│    Disease → disease_pressure increase per zone      │
│  Apply strategy actions at specified time offsets:    │
│    "stockpile" → max desal before event              │
│    "pre-harvest" → harvest early (reduced yield)     │
│    "stress-harden" → adjust nutrient EC              │
│  Run CropGrowthModel + ResourceChainModel per day    │
│  Returns: {daily_states[], final_outcome}            │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  MonteCarloRunner (~30 lines)                        │
│                                                      │
│  For i in range(N):  # N=50-100                      │
│    perturb = gaussian_noise(sigma per param)         │
│    outcome = ScenarioEngine.run(params + perturb)    │
│    results.append(outcome)                           │
│  Return: {                                           │
│    mean_yield_loss, p5, p50, p95,                    │
│    mean_water_consumed, survival_probability,         │
│    confidence_interval                                │
│  }                                                   │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  run_simulation() tool (agent-callable, ~40 lines)   │
│                                                      │
│  Input: scenario_type, strategies[], zone_states,    │
│         crop_profiles, resource_state, mars_cond     │
│  Output: [{strategy_name, yield_loss_pct,            │
│            water_consumed, confidence, reasoning}]    │
│  ORACLE agent calls this, gets NUMBERS back,         │
│  then adds interpretation as text.                   │
└─────────────────────────────────────────────────────┘
```

**Total: ~250 lines of pure Python.** One file: `eden/domain/simulation.py`.

---

## Crop Growth Model — Equations

### Core Growth Equation

```
biomass(t+1) = biomass(t) + (max_growth_rate × combined_stress_factor × dt)
```

Where:
- `max_growth_rate` = theoretical maximum daily biomass accumulation (kg/m²/day)
- `combined_stress_factor` = min(temp_stress, water_stress, light_stress, radiation_stress, disease_stress)
- Using Liebig's Law of the Minimum: the most limiting factor constrains growth

### Thermal Time (Growing Degree Days)

```
GDD(t) = GDD(t-1) + max(0, T_mean(t) - T_base)
growth_stage = GDD(t) / GDD_maturity
```

Where:
- `T_base` = base temperature below which no growth occurs (crop-specific, e.g., 5°C for wheat, 10°C for tomato)
- `GDD_maturity` = total thermal units needed for harvest maturity
- `growth_stage` = 0.0 (seed) to 1.0 (harvestable)

This is THE standard in agronomy. A Syngenta scientist sees GDD and immediately knows we understand crop modeling.

### Stress Functions (Trapezoidal Response Curves)

```python
def temperature_stress(temp, optimal_min, optimal_max):
    """0.0 = dead, 1.0 = optimal. Trapezoidal response curve."""
    if optimal_min <= temp <= optimal_max:
        return 1.0
    if temp < optimal_min:
        return max(0.0, 1.0 - (optimal_min - temp) / 10.0)  # linear decay over 10°C
    return max(0.0, 1.0 - (temp - optimal_max) / 10.0)

def water_stress(water_available, water_optimal):
    """Ratio model: actual / potential."""
    if water_optimal <= 0:
        return 1.0
    return min(1.0, max(0.0, water_available / water_optimal))

def light_stress(par_actual, par_optimal):
    """Light response: diminishing returns above optimal."""
    if par_optimal <= 0:
        return 1.0
    ratio = par_actual / par_optimal
    if ratio >= 1.0:
        return 1.0
    return max(0.0, ratio)

def radiation_stress(radiation_level, tolerance):
    """UV-B damage: threshold model with growth stage sensitivity."""
    if radiation_level <= tolerance:
        return 1.0
    excess = (radiation_level - tolerance) / tolerance
    return max(0.0, 1.0 - excess * 0.5)  # 50% reduction per 1x excess

def disease_stress(humidity, temp, threshold_humidity=80, threshold_temp=25):
    """Fungal pressure: combined humidity + temperature model."""
    if humidity < threshold_humidity or temp < threshold_temp:
        return 1.0  # no disease pressure
    severity = ((humidity - threshold_humidity) / 20.0) * ((temp - threshold_temp) / 10.0)
    return max(0.0, 1.0 - min(1.0, severity) * 0.4)  # max 40% loss from disease
```

### Water Consumption Model

```
water_per_day(growth_stage) = base_water × stage_multiplier

stage_multiplier:
  0.0-0.2 (seedling):    0.4
  0.2-0.5 (vegetative):  0.8
  0.5-0.8 (flowering):   1.2  ← peak water demand
  0.8-1.0 (maturation):  0.6
```

### Resource Chain Model

```
solar_output_kw = 4.2 × (1 - dust_opacity)  # Mars: 4.2 kW panels
power_for_desal = solar_output_kw × 0.25     # 25% allocation to desal
desal_rate_L = power_for_desal × desal_efficiency  # L per kW
water_in = desal_rate_L + transpiration_recovery    # 60% transpiration recovered
water_out = sum(crop_water_consumption)
water_balance = water_reserve + water_in - water_out
```

---

## Crop Parameters (from Syngenta KB + CropProfile)

| Crop | T_base °C | T_opt_min °C | T_opt_max °C | GDD_maturity | Max Growth kg/m²/day | Water L/m²/day | Yield kg/m² |
|---|---|---|---|---|---|---|---|
| Soybean | 10 | 20 | 30 | 1800 | 0.004 | 0.6 | 0.3 |
| Potato | 5 | 15 | 22 | 1500 | 0.050 | 0.8 | 4.0 |
| Wheat | 5 | 15 | 25 | 2000 | 0.006 | 0.5 | 0.5 |
| Tomato | 10 | 20 | 28 | 1200 | 0.100 | 1.0 | 8.0 |
| Spinach | 5 | 15 | 22 | 600 | 0.050 | 0.4 | 2.0 |
| Lettuce | 5 | 15 | 22 | 500 | 0.040 | 0.3 | 1.5 |

These feed directly from `CropProfile` dataclass in `eden/domain/models.py`. Extended with simulation-specific fields.

---

## Scenario Definitions

### CME Solar Storm

```python
CME_SCENARIO = {
    "type": "cme",
    "onset_day": 0,          # day 0 = CME arrives
    "duration_days": 5,
    "dust_opacity": 0.85,    # 85% solar blockage
    "radiation_level": 2.5,  # 2.5x normal UV-B
    "pre_warning_hours": 50, # 50h advance warning from DONKI
}
```

### Water System Failure

```python
WATER_FAILURE_SCENARIO = {
    "type": "water_failure",
    "onset_day": 0,
    "duration_days": 3,
    "desal_capacity_pct": 0.0,  # total failure
    "recovery_rate": 0.3,       # 30% per day after repair
}
```

### Disease Outbreak

```python
DISEASE_SCENARIO = {
    "type": "disease",
    "onset_day": 0,
    "affected_zones": ["vitamin"],
    "humidity_spike": 92,
    "temp_spike": 28,
    "spread_rate": 0.1,  # 10% per day to adjacent zones
}
```

---

## Strategy Definitions

### Strategy A: "Do Nothing" (always baseline)

```python
DO_NOTHING = {
    "name": "Do Nothing",
    "actions": []  # no intervention — let flight rules handle it
}
```

### Strategy B: "Standard Survival"

```python
STANDARD_SURVIVAL = {
    "name": "Standard Survival",
    "actions": [
        {"day_offset": 0, "action": "reduce_light", "value": 50},
        {"day_offset": 0, "action": "reduce_irrigation", "value": 70},
        {"day_offset": 0, "action": "activate_shields", "value": True},
    ]
}
```

### Strategy C: "Pre-emptive Protocol"

```python
PREEMPTIVE_PROTOCOL = {
    "name": "Pre-emptive Protocol",
    "actions": [
        {"day_offset": -2, "action": "max_desal", "value": True},
        {"day_offset": -2, "action": "top_battery", "value": True},
        {"day_offset": -1, "action": "pre_harvest", "zones": ["vitamin"], "value": True},
        {"day_offset": -1, "action": "stress_harden", "zones": ["carb"], "value": 2.4},
        {"day_offset": 0, "action": "activate_shields", "value": True},
        {"day_offset": 0, "action": "reduce_light", "value": 30},
    ]
}
```

---

## Monte Carlo Implementation

```python
def monte_carlo_compare(
    scenario: dict,
    strategies: list[dict],
    crop_params: list[dict],
    initial_state: dict,
    n_runs: int = 100,
    seed: int | None = None,
) -> list[dict]:
    """Compare strategies via Monte Carlo parameter sweep.

    Returns ranked list of strategy outcomes with confidence intervals.
    """
    if seed is not None:
        random.seed(seed)

    all_results = {}
    for strategy in strategies:
        outcomes = []
        for _ in range(n_runs):
            # Perturb parameters: ±5% gaussian noise on all environmental inputs
            perturbed = perturb_params(initial_state, sigma=0.05)
            outcome = run_scenario(scenario, strategy, crop_params, perturbed)
            outcomes.append(outcome)

        # Aggregate statistics
        yield_losses = [o["yield_loss_pct"] for o in outcomes]
        water_used = [o["water_consumed_L"] for o in outcomes]

        all_results[strategy["name"]] = {
            "strategy": strategy["name"],
            "yield_loss_pct": {
                "mean": mean(yield_losses),
                "p5": percentile(yield_losses, 5),
                "p50": percentile(yield_losses, 50),
                "p95": percentile(yield_losses, 95),
            },
            "water_consumed_L": {
                "mean": mean(water_used),
                "p5": percentile(water_used, 5),
                "p95": percentile(water_used, 95),
            },
            "survival_probability": sum(1 for o in outcomes if o["crops_survived"]) / n_runs,
            "confidence": 1.0 - (percentile(yield_losses, 95) - percentile(yield_losses, 5)) / 100,
            "n_runs": n_runs,
        }

    # Rank by mean yield loss (ascending = best first)
    ranked = sorted(all_results.values(), key=lambda r: r["yield_loss_pct"]["mean"])

    # Mark best strategy
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["selected"] = (i == 0)

    return ranked
```

---

## Integration Points

### 1. Agent Tool: `run_simulation()`

Registers as a callable tool in `eden/application/agent.py`:

```python
def run_simulation(
    scenario_type: str,
    strategies: list[dict] | None = None,
    zone_states: dict | None = None,
    crop_profiles: list[dict] | None = None,
    resource_state: dict | None = None,
    mars_conditions: dict | None = None,
    n_runs: int = 100,
) -> dict:
    """Virtual Farming Lab — run Monte Carlo strategy comparison.

    Called by ORACLE agent. Returns structured comparison with
    confidence intervals. The agent interprets; the math decides.
    """
    from eden.domain.simulation import monte_carlo_compare, get_scenario, get_default_strategies

    scenario = get_scenario(scenario_type)
    if strategies is None:
        strategies = get_default_strategies(scenario_type)

    results = monte_carlo_compare(
        scenario=scenario,
        strategies=strategies,
        crop_params=crop_profiles or [],
        initial_state={
            "zones": zone_states or {},
            "resources": resource_state or {},
            "mars": mars_conditions or {},
        },
        n_runs=n_runs,
    )

    return {
        "scenario": scenario_type,
        "strategies_compared": len(results),
        "n_runs": n_runs,
        "results": results,
        "recommended": results[0]["strategy"] if results else None,
    }
```

### 2. ORACLE Agent Prompt Update

Add to ORACLE_PROMPT:

```
You have access to run_simulation(scenario_type, strategies) — the Virtual Farming Lab.
When a threat is detected, ALWAYS run a simulation before recommending a strategy.
The simulation returns NUMBERS (yield loss %, confidence intervals, water consumption).
You INTERPRET those numbers for the crew. You do NOT invent numbers — the simulation provides them.

Example:
  ORACLE: "Running 3 strategies through the Virtual Lab — 100 iterations each..."
  [calls run_simulation("cme")]
  ORACLE: "Strategy C wins. 3.2% mean yield loss (95% CI: 1.8%-5.1%).
           Strategy A would cost us 41% of the crop. The math is clear.
           Recommending C — pre-emptive protocol."
```

### 3. Dashboard Panel: Virtual Farming Lab

The `/api/state` endpoint gains a `simulation` field when a simulation has been run:

```json
{
  "simulation": {
    "scenario": "cme",
    "timestamp": 1711288800,
    "results": [
      {
        "strategy": "Do Nothing",
        "yield_loss_pct": {"mean": 41.2, "p5": 35.1, "p95": 48.7},
        "survival_probability": 0.62,
        "selected": false,
        "rank": 3
      },
      {
        "strategy": "Standard Survival",
        "yield_loss_pct": {"mean": 12.4, "p5": 8.2, "p95": 17.1},
        "survival_probability": 0.91,
        "selected": false,
        "rank": 2
      },
      {
        "strategy": "Pre-emptive Protocol",
        "yield_loss_pct": {"mean": 3.2, "p5": 1.8, "p95": 5.1},
        "survival_probability": 0.99,
        "selected": true,
        "rank": 1
      }
    ],
    "recommended": "Pre-emptive Protocol"
  }
}
```

Dashboard renders as side-by-side cards:
```
┌──────────────────┬──────────────────┬──────────────────┐
│ Strategy A       │ Strategy B       │ Strategy C       │
│ Do Nothing       │ Standard Survival│ Pre-emptive  ✓   │
│                  │                  │                  │
│ 41.2% loss  ✗   │ 12.4% loss  ~   │  3.2% loss  ✓   │
│ CI: 35-49%      │ CI: 8-17%       │ CI: 1.8-5.1%    │
│ Survive: 62%    │ Survive: 91%    │ Survive: 99%    │
│                  │                  │                  │
│ 100 runs         │ 100 runs         │ 100 runs    [★]  │
└──────────────────┴──────────────────┴──────────────────┘
```

### 4. Learning Loop: Simulation → Flight Rules

After a real event resolves:

```python
# In reconciler or post-event handler:
predicted = last_simulation_result["results"][selected_strategy]["yield_loss_pct"]["mean"]
actual = measure_actual_yield_loss()
delta = actual - predicted

if abs(delta) > 1.0:  # >1% prediction error
    # Propose flight rule refinement
    propose_flight_rule(
        engine=flight_rules,
        rule_id=f"FR-SIM-{event_id}",
        sensor_type="water_level",
        condition="lt",
        threshold=adjusted_threshold,
        device="pump",
        action="begin_stockpiling",
        value=100.0,
        cooldown_seconds=3600,
        priority="high",
    )
```

This closes the loop: Simulation predicts → Reality happens → Delta measured → New flight rule proposed → Simulation parameters updated → Better predictions next time.

---

## File Structure

```
eden/domain/simulation.py     # NEW — all simulation logic (~250 lines)
  ├── CropSimParams           # dataclass: per-crop simulation parameters
  ├── SimulationState          # dataclass: state at each timestep
  ├── temperature_stress()     # trapezoidal stress function
  ├── water_stress()           # ratio model
  ├── light_stress()           # diminishing returns model
  ├── radiation_stress()       # threshold model
  ├── disease_stress()         # humidity × temp interaction
  ├── simulate_crop_day()      # one day of crop growth
  ├── simulate_resource_day()  # one day of resource chain
  ├── run_scenario()           # full scenario with strategy
  ├── perturb_params()         # gaussian noise for Monte Carlo
  ├── monte_carlo_compare()    # N-run comparison engine
  ├── get_scenario()           # scenario library
  └── get_default_strategies() # strategy library per scenario type
```

Modify existing files:
- `eden/application/agent.py` — implement `run_simulation()` tool, update ORACLE_PROMPT
- `eden/api.py` — add simulation results to `/api/state` response
- `eden/application/reconciler.py` — store last simulation result for post-event comparison

---

## Judge Defense — Q&A Answers

| Judge Question | Answer |
|---|---|
| "Show me the model equations" | `growth_rate = max_rate × min(temp_stress, water_stress, light_stress)` — Liebig's Law of the Minimum. Standard agronomy since the 1960s. |
| "What's the state space of your Monte Carlo?" | 5 stress parameters × 6 crops × 100 perturbation runs = 3,000 simulation evaluations per strategy comparison. Completes in <1 second. |
| "How do you parameterize it?" | CropProfile from Syngenta KB: optimal temp range, growth days, yield per m². Stress thresholds from KB Domain 4 (Plant Stress and Response Guide). |
| "Is this real or just LLM output?" | The simulation produces identical numbers every run with the same seed. The LLM adds interpretation after. Run it twice — same numbers. That's the test. |
| "What's the thermal time model?" | GDD (Growing Degree Days): `sum(max(0, daily_temp - base_temp))`. Standard agronomy since 1960. Every crop scientist knows this model. |
| "How does Monte Carlo add value vs a single run?" | Single run gives a point estimate ("3% loss"). Monte Carlo gives a distribution ("3% mean, 95% CI: 1.8-5.1%"). On Mars, you need to know the WORST case, not just the expected case. The confidence interval IS the value. |
| "What's the difference between this and ChatGPT saying '3% loss'?" | Deterministic reproducibility. Our simulation returns 3.2% because the math says 3.2%. ChatGPT returns whatever plausible number it generates. Change the temperature by 1°C — our number changes predictably. ChatGPT's doesn't. |

---

## The Core Insight

**Math produces numbers. LLM produces meaning. Together, they're more than either alone.**

The split:
- **Math** produces: "Strategy C: 3.2% yield loss (95% CI: 1.8%-5.1%), 482L water consumed"
- **LLM** produces: "Strategy C is our best option. The wheat's in full flower — worst possible timing for radiation. But if we stress-harden now and stockpile water for 48 hours, we save 96.8% of the crop. I've run this 100 times. It works."

The numbers make the LLM credible. The LLM makes the numbers human.

---

## Build Sequence (for implementation)

1. **Hour 1**: `simulation.py` — CropSimParams, stress functions, simulate_crop_day(), simulate_resource_day()
2. **Hour 2**: `simulation.py` — run_scenario(), perturb_params(), monte_carlo_compare(), scenario/strategy libraries
3. **Hour 3**: Integration — run_simulation() tool in agent.py, ORACLE prompt update, API endpoint
4. **Hour 4**: Dashboard — Virtual Lab panel rendering strategy comparison cards, polish

Each hour produces a testable increment. Hour 1 alone makes the concept defensible. Hours 1-2 make it demo-ready (agent log text). Hours 1-3 make it fully integrated. Hour 4 makes it visually compelling.

---

## RedTeam Audit — Syngenta Crop Scientist Perspective

> Adversarial analysis of this spec from the perspective of a Syngenta crop scientist judge.
> Goal: identify every weakness a real agronomist would catch before we build.

---

### FATAL WEAKNESSES (would make a crop scientist wince)

**F1. VPD is completely absent — this is the #1 tell**

Every controlled environment agriculture (CEA) professional manages by VPD, not humidity. Our own CEA dataset (`data/nutrition/crop-cea-data.json`) has VPD targets per crop: soybean 0.8-1.2 kPa, spinach 0.5-0.8 kPa, potato 0.6-1.0 kPa. The spec's `disease_stress()` uses raw humidity (>80%) — a Syngenta scientist would immediately say: "Disease risk is a VPD function, not a humidity threshold. Low VPD means the leaf can't transpire, water films form, and THAT's where pathogens grow."

VPD calculation is 3 lines:
```python
def vpd(temp_c, rh_pct):
    svp = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))  # Tetens equation
    return svp * (1 - rh_pct / 100)  # kPa
```

**Not using VPD in a CEA simulation is like not using temperature.** It's the single term that separates "they Googled it" from "they understand greenhouse management."

**F2. DLI absent — using abstract "light" instead of mol/m2/day**

The CEA dataset specifies DLI per crop (lettuce optimal: 14 mol/m2/day, wheat: 35, spinach: 17). The spec's `light_stress()` takes `par_actual / par_optimal` with no units. A crop scientist would ask: "PAR in what units? PPFD? DLI? Lux?" If the answer is "just a ratio," it signals no understanding of how light drives photosynthesis.

DLI integrates intensity over time: `DLI = PPFD * photoperiod_hours * 0.0036`. This matters because the SAME light intensity over 12h (spinach) vs 16h (wheat) produces different DLI — and therefore different growth rates.

**F3. No distinction between air temperature and root zone temperature**

The CEA dataset screams about this: potato root zone MUST be <20C for tuberization. Spinach bolts if root zone >22C. Basil needs warmest root zone (>20C). The spec has ONE temperature variable. A Syngenta scientist would say: "You're modeling CEA with a single temperature? The air-root delta is where 80% of the management decisions happen."

**F4. Harvest index not parameterized from the actual data**

The spec mentions `yield_at_harvest = biomass * harvest_index` but the parameter table has NO harvest index column. The CEA dataset has Apogee wheat harvest index = 0.42 explicitly. Without harvest index, `biomass` and `yield` are conflated — a crop scientist would catch this instantly: "Not all biomass is edible. A wheat plant is 58% straw."

**F5. Generic water model ignores per-crop transpiration stages**

The spec has a one-size-fits-all 4-stage multiplier (0.4/0.8/1.2/0.6). The CEA dataset has **per-crop, per-stage transpiration rates**: tomato flowering = 4.5 L/m2/day vs spinach active growth = 2.5 L/m2/day vs radish root swelling = 1.5 L/m2/day. Using generic multipliers when you HAVE this data is inexcusable waste.

---

### SIGNIFICANT WEAKNESSES (would raise eyebrows)

**S1. Radiation stress model doesn't vary by growth stage (BBCH)**

The concept docs, system prompts, and critique ALL emphasize: "Wheat at BBCH 61-65 (anthesis) shows 15-40% yield reduction under elevated UV-B. Potato tuber initiation stage shows high radiation resilience." The spec's `radiation_stress()` is stage-independent. A Syngenta scientist reviewing both the pitch and the code would notice the inconsistency.

**S2. No CO2 enrichment modeling**

Mars atmosphere is 95% CO2. The CEA dataset explicitly states: "All 9 crops benefit from CO2 enrichment (800-1200 ppm)." CO2 enrichment boosts photosynthesis 20-40% — a massive effect. Not modeling it means missing a key Mars advantage.

**S3. Output is only "yield loss %" — not nutritional output**

The challenge brief literally says: "Maximize nutrient output. Ensure dietary balance." The simulation outputs `yield_loss_pct` and `water_consumed`. It should output `kcal_produced`, `protein_produced`, `vitamin_c_produced`, `iron_produced`. The per-crop nutritional data already exists in `CropProfile` (calories_per_kg, protein_per_kg). This is a 5-line addition that directly answers the challenge.

**S4. No photoperiod modeling**

Spinach bolts under long photoperiod (>12h). Potato tuberization requires switching from 16h to 12h. Wheat uses 20-24h for speed breeding. Photoperiod is a control variable — strategies should include photoperiod adjustment. The CEA dataset specifies hours per crop.

**S5. Transpiration recovery should be 95-98%, not 60%**

The spec says `recovery_from_transpiration = 60%`. The CEA dataset says: "In a closed Mars greenhouse, 95-98% of transpired water is recoverable via condensation." Using 60% dramatically understates water availability. A crop scientist would say: "Your water balance is off by a factor of 2 because you don't understand closed-loop recovery."

---

### CONFIRMED STRENGTHS (genuinely impressive for a hackathon)

- **GDD/thermal time** is correct and signals real crop modeling knowledge
- **Liebig's Law multiplicative stress** is the correct architecture (not additive)
- **Trapezoidal stress curves** are a legitimate simplification of beta distributions
- **Math-first / LLM-interprets split** is architecturally honest and defensible
- **Monte Carlo with confidence intervals** is genuinely useful for risk assessment
- **Resource chain cascade** (solar -> power -> desal -> water -> crops) is correct Mars physics
- **Deterministic reproducibility** is the killer answer to "is this real?"
- **Strategy comparison structure** directly answers "which approach works best?"

---

## Required Upgrades — The 8 Fixes

> Total cost: ~30 additional lines of code. Zero additional complexity. Massive credibility increase.
> These take the spec from "they understand simulation" to "they understand FARMING simulation."

### Upgrade 1: ADD VPD (3 lines, infinite credibility)

Replace raw humidity in `disease_stress()` with VPD. Add `vpd()` helper using Tetens equation. Use per-crop VPD targets from CEA data.

```python
def vpd(temp_c: float, rh_pct: float) -> float:
    """Vapor Pressure Deficit (kPa). THE metric for CEA disease/transpiration management."""
    svp = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
    return svp * (1.0 - rh_pct / 100.0)
```

Disease stress becomes VPD-driven:
```python
def disease_stress(temp: float, rh: float, vpd_target_min: float = 0.8) -> float:
    """Fungal pressure as VPD function. Low VPD = wet leaf surface = pathogen risk."""
    current_vpd = vpd(temp, rh)
    if current_vpd >= vpd_target_min:
        return 1.0  # adequate transpiration, no disease pressure
    deficit = (vpd_target_min - current_vpd) / vpd_target_min
    return max(0.0, 1.0 - deficit * 0.4)
```

### Upgrade 2: ADD DLI instead of abstract "light" (5 lines)

```python
def compute_dli(ppfd_umol: float, photoperiod_hours: float) -> float:
    """Daily Light Integral: mol/m2/day from PPFD and photoperiod."""
    return ppfd_umol * photoperiod_hours * 0.0036

def light_stress(actual_dli: float, optimal_dli: float) -> float:
    """Light response using DLI (mol/m2/day) — the real CEA metric."""
    if optimal_dli <= 0:
        return 1.0
    ratio = actual_dli / optimal_dli
    if ratio >= 1.0:
        return min(1.0, 2.0 - ratio)  # excess light causes photoinhibition
    return max(0.0, ratio)
```

Per-crop DLI targets from CEA data:
| Crop | DLI min | DLI optimal | DLI max | Photoperiod h |
|---|---|---|---|---|
| Soybean | 20 | 30 | 45 | 16 |
| Potato | 15 | 25 | 40 | 14 |
| Wheat | 22 | 35 | 55 | 16 |
| Tomato | 20 | 30 | 45 | 16 |
| Spinach | 10 | 17 | 25 | 12 |
| Lettuce | 10 | 14 | 22 | 14 |
| Radish | 8 | 14 | 20 | 12 |
| Basil | 12 | 20 | 30 | 16 |

### Upgrade 3: ADD per-crop transpiration from CEA data (table swap)

Replace generic 4-stage multiplier with actual rates from `crop-cea-data.json`:

```python
# Per-crop, per-stage transpiration (L/m2/day) from CEA research data
TRANSPIRATION_RATES = {
    "soybean":  {"seedling": 1.0, "vegetative": 2.1, "flowering": 3.2, "maturation": 2.8},
    "potato":   {"seedling": 1.2, "vegetative": 2.5, "tuber_bulking": 4.5, "senescence": 1.5},
    "wheat":    {"seedling": 1.0, "vegetative": 2.0, "heading": 3.5, "grain_fill": 3.0, "senescence": 1.0},
    "tomato":   {"seedling": 1.2, "vegetative": 2.5, "flowering": 4.5, "ripening": 3.0},
    "spinach":  {"seedling": 0.6, "active_growth": 2.5, "harvest": 2.0},
    "lettuce":  {"seedling": 0.6, "heading": 2.5, "mature": 2.0},
    "radish":   {"seedling": 0.4, "root_swelling": 1.5, "mature": 1.0},
    "basil":    {"seedling": 0.3, "active": 1.2, "flowering": 1.5},
}
```

### Upgrade 4: ADD harvest index per crop (1 field in CropSimParams)

```python
HARVEST_INDEX = {
    "soybean": 0.45,    # ~45% of biomass is edible seed
    "potato": 0.80,     # ~80% is edible tuber
    "wheat": 0.42,      # Apogee space wheat (USU data)
    "tomato": 0.60,     # ~60% is edible fruit
    "spinach": 0.90,    # ~90% is edible leaf
    "lettuce": 0.85,    # ~85% is edible leaf
    "radish": 0.50,     # ~50% is edible root (leaves also edible)
    "basil": 0.85,      # ~85% is edible leaf
}
```

Yield equation becomes: `edible_yield = total_biomass * harvest_index`

### Upgrade 5: FIX transpiration recovery to 95% (change one number)

```python
# WRONG: recovery_from_transpiration = 0.60
# RIGHT (from CEA dataset cross_crop_notes.water_recycling):
TRANSPIRATION_RECOVERY_RATE = 0.95  # 95-98% in closed Mars greenhouse
```

The CEA data is explicit: "In a closed Mars greenhouse, 95-98% of transpired water is recoverable via condensation. Total crop transpiration of ~18-25 L/day for 100 m2 greenhouse produces significant potable water as a byproduct."

### Upgrade 6: ADD nutritional output per strategy (5 lines)

```python
def compute_nutrition(crop_name: str, yield_kg: float, crop_profile: dict) -> dict:
    """Convert harvest yield to nutritional value — answers the actual challenge brief."""
    return {
        "kcal": yield_kg * crop_profile["calories_per_kg"],
        "protein_g": yield_kg * crop_profile["protein_per_kg"],
        "yield_kg": yield_kg,
    }
```

Strategy comparison output gains:
```json
{
  "strategy": "Pre-emptive Protocol",
  "yield_loss_pct": {"mean": 3.2, "p5": 1.8, "p95": 5.1},
  "nutrition_preserved": {
    "kcal_per_sol": 8420,
    "protein_g_per_sol": 187,
    "crew_kcal_coverage_pct": 84.2
  }
}
```

### Upgrade 7: ADD growth-stage radiation sensitivity (lookup table)

```python
# Radiation sensitivity multiplier by growth stage (BBCH-derived)
# Flowering/anthesis is CRITICAL — this is the key Syngenta KB insight
RADIATION_STAGE_SENSITIVITY = {
    (0.0, 0.2): 0.6,   # seedling: moderate vulnerability
    (0.2, 0.5): 0.3,   # vegetative: low vulnerability
    (0.5, 0.8): 1.5,   # flowering/anthesis: CRITICAL window (BBCH 60-69)
    (0.8, 1.0): 0.5,   # maturation/grain fill: moderate
}

def radiation_stress(radiation_level, tolerance, growth_stage):
    """UV-B damage with growth-stage sensitivity. Flowering = worst timing."""
    # Look up stage sensitivity
    stage_mult = 1.0
    for (lo, hi), mult in RADIATION_STAGE_SENSITIVITY.items():
        if lo <= growth_stage < hi:
            stage_mult = mult
            break

    effective_radiation = radiation_level * stage_mult
    if effective_radiation <= tolerance:
        return 1.0
    excess = (effective_radiation - tolerance) / tolerance
    return max(0.0, 1.0 - excess * 0.5)
```

This makes the CME scenario growth-stage-aware: hitting wheat at BBCH 65 (full flowering) is devastating. Hitting it during grain fill is manageable. **This is exactly what the demo script already claims** — now the math backs it up.

### Upgrade 8: ADD root zone temperature as separate variable (1 param)

```python
# Simple root zone model: air temp offset (CEA systems typically 2-5C cooler)
def root_zone_temp(air_temp: float, cooling_active: bool = True) -> float:
    """Root zone typically 2-5C below air temp in hydroponic/aeroponic systems."""
    offset = -3.0 if cooling_active else -1.0
    return air_temp + offset

# Critical checks (from CEA data):
def tuberization_check(root_temp: float) -> float:
    """Potato tuber initiation STOPS above 25C root zone."""
    if root_temp > 25.0:
        return 0.0  # no tuber growth
    if root_temp > 20.0:
        return max(0.0, (25.0 - root_temp) / 5.0)  # linear decline
    return 1.0

def bolting_check(root_temp: float, photoperiod_h: float, is_spinach: bool = False) -> float:
    """Spinach bolts if root zone >22C + long photoperiod."""
    if is_spinach and root_temp > 22.0 and photoperiod_h > 12.0:
        return 0.3  # 70% yield loss from bolting
    return 1.0
```

---

## Updated CropSimParams Dataclass

After all 8 upgrades, the simulation parameter structure becomes:

```python
@dataclass(frozen=True)
class CropSimParams:
    """Per-crop simulation parameters. Sourced from Syngenta KB + CEA research data."""
    name: str
    zone_id: str

    # Thermal time
    base_temp_c: float           # GDD base (below this, no growth)
    optimal_temp_min_c: float    # optimal range start
    optimal_temp_max_c: float    # optimal range end
    gdd_maturity: float          # total GDD to harvest maturity

    # Root zone
    root_zone_optimal_min_c: float
    root_zone_optimal_max_c: float

    # Light (DLI-based)
    dli_optimal: float           # mol/m2/day
    photoperiod_hours: float     # hours per day

    # VPD target
    vpd_target_min: float        # kPa — below this = disease risk
    vpd_target_max: float        # kPa — above this = desiccation risk

    # Water (transpiration rates by stage)
    transpiration_rates: dict    # {"vegetative": 2.1, "flowering": 3.2, ...}

    # Yield
    max_growth_rate: float       # kg/m2/day theoretical max biomass
    harvest_index: float         # edible fraction of total biomass
    yield_kg_per_m2: float       # reference yield under optimal conditions

    # Nutrition
    calories_per_kg: float
    protein_per_kg: float

    # Stress sensitivity
    radiation_tolerance: float          # base UV-B tolerance (1.0 = Earth normal)
    is_bolting_sensitive: bool           # spinach, lettuce
    tuberization_temp_max: float | None  # potato: 25C max root zone
```

---

## Updated Parameter Table (CEA-sourced)

| Crop | T_base | T_opt | GDD | Root_opt | DLI_opt | Photo_h | VPD_target | HI | Max_growth |
|---|---|---|---|---|---|---|---|---|---|
| Soybean | 10 | 20-30 | 1800 | 22-26 | 30 | 16 | 0.8-1.2 | 0.45 | 0.004 |
| Potato | 5 | 15-22 | 1500 | 15-20 | 25 | 14 | 0.6-1.0 | 0.80 | 0.050 |
| Wheat | 5 | 15-25 | 2000 | 18-22 | 35 | 16 | 0.8-1.2 | 0.42 | 0.006 |
| Tomato | 10 | 20-28 | 1200 | 20-25 | 30 | 16 | 0.8-1.2 | 0.60 | 0.100 |
| Spinach | 5 | 15-22 | 600 | 14-20 | 17 | 12 | 0.5-0.8 | 0.90 | 0.050 |
| Lettuce | 5 | 15-22 | 500 | 16-22 | 14 | 14 | 0.5-0.8 | 0.85 | 0.040 |
| Radish | 5 | 15-20 | 400 | 15-20 | 14 | 12 | 0.5-0.8 | 0.50 | 0.060 |
| Basil | 13 | 20-27 | 800 | 20-27 | 20 | 16 | 0.8-1.2 | 0.85 | 0.030 |

---

## Updated Build Sequence (revised with upgrades)

1. **Hour 1**: `simulation.py` — CropSimParams (with all 8 upgrade fields), `vpd()`, stress functions (VPD-based disease, DLI-based light, stage-aware radiation, root zone checks), `simulate_crop_day()`
2. **Hour 2**: `simulation.py` — `simulate_resource_day()` (95% recovery), `run_scenario()`, `perturb_params()`, `monte_carlo_compare()`, nutritional output, scenario/strategy libraries
3. **Hour 3**: Integration — `run_simulation()` tool in agent.py, ORACLE prompt update, `/api/state` simulation field
4. **Hour 4**: Dashboard — Virtual Lab panel, strategy comparison cards with nutritional impact, polish

The 8 upgrades add ~30 lines and zero additional complexity. They slot into the same hour-by-hour structure. The difference is entirely in credibility and scientific accuracy.
