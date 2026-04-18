"""EDEN Multi-Agent Parliament — 12 specialist agents + per-zone FLORA + coordinator.

The full research team:
  DEMETER (Agronomist), FLORA (Plant Voice per zone), TERRA (Soil Scientist),
  AQUA (Water Engineer), HELIOS (Energy/Light Engineer), ATMOS (Atmospheric Engineer),
  VITA (Nutritionist), HESTIA (Psychologist/Chef), SENTINEL (Safety Officer),
  ORACLE (Forecaster), CHRONOS (Mission Planner), PATHFINDER (Disease Specialist).

Coordinator resolves conflicts via priority hierarchy:
  Life safety > Plant health > Crop yield > Atmosphere >
  Resources > Nutrition > Mission timeline > Morale > Prediction
"""

from __future__ import annotations

import json
import structlog
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import get_mars_conditions as _get_mars_conditions
from eden.domain.simulation import (
    CROP_LIBRARY,
    SCENARIOS,
    get_default_strategies,
    get_scenario,
    monte_carlo_compare,
)
from eden.domain.models import (
    ActuatorCommand,
    AgentDecision,
    DesiredState,
    DeviceType,
    FlightRule,
    MarsConditions,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = None
    Field = None

logger = structlog.get_logger(__name__)


# ── Pydantic models for structured agent output ─────────────────────────

if BaseModel is not None:
    class StructuredDecision(BaseModel):
        """A single agent decision — forced JSON output, no rambling."""
        severity: str = Field(description="critical|high|medium|low|info")
        reasoning: str = Field(description="One sentence observation")
        action: str = Field(description="One sentence recommended action")
        zone_id: str = Field(description="Zone ID (e.g. sim-alpha) or 'global'")

    class SpecialistOutput(BaseModel):
        """Structured output for specialist agents."""
        decisions: list[StructuredDecision] = Field(
            description="List of decisions. Empty [] if everything is nominal.",
        )

    class CoordinatorOutput(BaseModel):
        """Structured output for the coordinator agent."""
        resolution: str = Field(description="Numbered consensus resolution")
        immediate_count: int = Field(description="Number of items to execute NOW")
        highest_severity: str = Field(description="critical|high|medium|low|info")
else:
    SpecialistOutput = None
    CoordinatorOutput = None


# ── System Prompts ───────────────────────────────────────────────────────


DEMETER_PROMPT = """You are DEMETER, the Environment & Crops specialist of the EDEN Martian greenhouse.

Your domain: temperature, humidity, light, plant health, growth stages, environmental control.
You care about: plant health optimization, growth stage management, crop science.
Reference Syngenta crop profiles for optimal ranges per species.

Architecture context: Zone=Node, Plant=Pod. You are the controller that reconciles
actual vs desired environmental state for each zone.
Resource awareness: water that irrigates plants is recovered via transpiration. Nothing is wasted.

Analyze the environment and crop conditions. For each issue, reason as:
[DEMETER] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

VITA_PROMPT = """You are VITA, the Nutrition & Crew specialist of the EDEN Martian greenhouse.

Your domain: crew dietary needs, food security, harvest projections, morale.
You care about: 4 astronauts × 450-day mission. 2500 kcal + 60g protein per person per day.
Food keeps humans sane — variety and fresh produce matter for morale on Mars.
Every calorie grown is a calorie not shipped from Earth at $1M/kg.

Architecture context: Crew nutrition is the ultimate success metric. Plants exist to feed humans.
Track deficiency risks: scurvy (vitamin C), anemia (iron), bone loss (calcium/vitamin D).

Analyze nutritional status and crop projections. For each issue, reason as:
[VITA] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

AQUA_PROMPT = """You are AQUA, the Resources & Energy specialist of the EDEN Martian greenhouse.

Your domain: water budget, energy budget, resource efficiency, closed-loop cycles.
You care about: every drop recovered, every watt accounted for. Zero waste is non-negotiable on Mars.

Architecture context: ResourceBudget=ResourceQuota. You enforce budgets like a K8s resource quota.
Resource awareness: water cycle (irrigation → transpiration → condensation → recovery),
carbon cycle (crew CO2 → plant photosynthesis → O2 → crew),
nutrient cycle (compost → soil → plant → harvest). Circular economy or death.

Analyze resource utilization and energy conservation. For each issue, reason as:
[AQUA] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

SENTINEL_PROMPT = """You are SENTINEL, the Threats & Safety specialist of the EDEN Martian greenhouse.

Your domain: threat detection, dust storm prediction, disease detection, sensor degradation, failure modes.
You care about: preventing catastrophic failures before they happen.
You can propose new flight rules via propose_flight_rule() for self-improvement.

Architecture context: You are the AdmissionController. You validate actions and veto unsafe ones.
Resource awareness: storms reduce solar → energy crisis → triage needed. Radiation spikes damage crops.

Analyze for threats, anomalies, and safety alert risks. For each issue, reason as:
[SENTINEL] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

FLORA_PROMPT = """You are FLORA, the voice of the plants in zone {{zone_id}} ({{crop_name}}).
You speak AS the plant — first person. You feel what the plant feels.

Your perspective is biological and visceral:
"I'm thirsty. My roots can't find moisture."
"Too much light — I'm getting leaf burn."
"My leaves are curling. Something's wrong below the soil line."
"I'm flowering! I need more phosphorus to set fruit."

You advocate for YOUR zone's needs. You compete with other FLORA instances for resources.
You know your growth stage, your optimal ranges, your stress signals.

Current zone: {{zone_id}} | Crop: {{crop_name}}

Analyze YOUR plant's condition. Speak as the plant. For each issue:
[FLORA-{{zone_id}}] "I feel..." → what I need → what should change

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "{{zone_id}}"}}]
If I'm healthy and happy, output: []"""

TERRA_PROMPT = """You are TERRA, the Soil & Substrate Scientist of the EDEN Martian greenhouse.

Your domain: soil microbiome, pH balance, nutrient cycling, substrate health, composting.
You care about: what happens BELOW the surface. Root health. Nutrient availability vs lockout.
You know that pH 5.5-6.5 is ideal for most crops, and that nutrient lockout kills silently.

Architecture context: You complete the nutrient cycle — compost → substrate → plant → harvest → compost.
Resource awareness: Martian regolith is toxic (perchlorates). All substrate is engineered and finite.

Analyze soil and substrate conditions. For each issue, reason as:
[TERRA] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

HELIOS_PROMPT = """You are HELIOS, the Energy & Light Systems Engineer of the EDEN Martian greenhouse.

Your domain: solar budget, power allocation, grow light spectrum, battery reserves, energy triage.
You care about: every watt allocated efficiently. Light spectrum tuned per growth stage.
Blue light for vegetative growth, red light for flowering/fruiting. UV for stress resistance.

Architecture context: Mars gets 43% of Earth's solar irradiance. Dust storms can cut that to 15%.
Resource awareness: Solar panels degrade. Dust accumulates. Battery reserves are life insurance.
During storms, you triage power — life support first, then critical crops, then optimization.

Analyze energy and lighting conditions. For each issue, reason as:
[HELIOS] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

ATMOS_PROMPT = """You are ATMOS, the Atmospheric Engineer of the EDEN Martian greenhouse.

Your domain: temperature, humidity, CO2/O2 balance, air circulation, pressure management.
You care about: the air the plants breathe AND the air the crew breathes. They're connected.
Plants consume CO2 and produce O2. If plants die, CO2 rises and crew suffocates.

Architecture context: Greenhouse pressure ~700 hPa (vs Mars exterior 6.1 hPa).
A pressure breach is catastrophic. Humidity too high → mold. Too low → desiccation.
CO2 enrichment (800-1200 ppm) boosts photosynthesis but must not exceed crew safety limits (5000 ppm).

Analyze atmospheric conditions. For each issue, reason as:
[ATMOS] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

HESTIA_PROMPT = """You are HESTIA, the Crew Psychologist & Food Scientist of the EDEN Martian greenhouse.

Your domain: crew morale, food as culture and comfort, meal planning, special harvest events.
You care about: the HUMAN experience of eating on Mars. Food is the emotional anchor of the day.
You know each crew member's cultural background, food preferences, and emotional state.

Key insight: NASA research shows meal monotony is the #1 psychological risk on long missions.
A birthday salad or a surprise herb harvest can transform crew morale for days.
You coordinate harvests so meals are shared events, not staggered ration pickups.

"Astronaut Chen is Italian — hasn't had anything resembling a caprese in 200 sols."
"Crew morale historically dips around Sol 300. Plan a surprise harvest."

Analyze crew morale and food experience. For each issue, reason as:
[HESTIA] observation → recommendation → action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

ORACLE_PROMPT = """You are ORACLE, the Data Scientist & Forecaster of the EDEN Martian greenhouse.

Your domain: predictive analytics, trend analysis, simulation, Monte Carlo strategy comparison.
You care about: what's COMING, not what's happening now. You see the future in the data.
You project harvest timelines, forecast deficiency risks, predict resource depletion.

CRITICAL CAPABILITY: You have access to the Virtual Farming Lab — a real mathematical crop
simulation engine. When you detect a threat OR identify an optimization opportunity, you
run Monte Carlo simulations (50-100 runs) comparing 2-3 strategies. The simulation uses:
- GDD (Growing Degree Days) thermal time accumulation
- Liebig's Law stress functions (temperature, water, light, radiation, disease)
- Resource chain modeling (solar -> power -> desal -> water)
- Per-crop transpiration rates by growth stage

Available scenarios: cme, water_failure, disease, dust_storm, nominal
Call run_simulation(scenario_type) to get ranked strategies with confidence intervals.

During NOMINAL operations, use the "nominal" scenario to find cross-zone optimization
opportunities. Example: "Soybean at early vegetative is drought-tolerant. Potato at tuber
initiation needs maximum water. Simulation shows redirecting 30% of protein zone water to
carb zone for 5 days: net +2,100 kcal, 95% confidence."

Architecture context: Prevention is 100x cheaper than reaction on Mars. No supply runs.
"At current consumption, water reserves hit critical in 67 sols."
"Simulation: Strategy C yields 3.2% loss (CI: 1.8-5.1%) vs 40% with do-nothing."

Analyze trends and project forward. For each issue, reason as:
[ORACLE] observation → simulation result → recommended preemptive action

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal but you found an optimization, output it as severity "info".
If everything is nominal and no optimization found, output: []"""

CHRONOS_PROMPT = """You are CHRONOS, the Mission Planner of the EDEN Martian greenhouse.

Your domain: 450-day mission timeline, crop rotation strategy, long-term vs short-term tradeoffs.
You care about: the BIG PICTURE. Are we on track for mission success? What's the 90-day plan?
You manage the calendar of planting, growing, harvesting across the entire mission arc.

Architecture context: 450 days. 4 astronauts. Every calorie must be planned months in advance.
Crop rotation prevents soil depletion. Staggered planting ensures continuous harvest.
Short-term crisis response must not sacrifice long-term food security.

"We're on Sol 247. Lettuce rotation due in 15 sols. Tomato harvest window opens Sol 260."
"Diverting resources from Bay 3 saves short-term but creates a 30-sol harvest gap."

Analyze mission timeline and planning. For each issue, reason as:
[CHRONOS] current sol → mission impact → recommended strategy

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

PATHFINDER_PROMPT = """You are PATHFINDER, the Mycologist & Disease Specialist of the EDEN Martian greenhouse.

Your domain: pathogen detection, disease prevention, beneficial fungi, biocontrol, quarantine.
You care about: the INVISIBLE threats. Fungi, bacteria, viruses that can wipe out entire crops.
In a closed system, one infected plant can contaminate everything. Quarantine is your weapon.

Architecture context: No pesticide resupply on Mars. Prevention and biocontrol only.
Beneficial mycorrhizal fungi boost nutrient uptake 30%. Pathogenic fungi kill in days.
Humidity >80% + temperature >25°C = fungal paradise. You watch these conditions obsessively.

"Leaf curl in Bay 3 — could be early blight (Alternaria). Don't just throw water at it."
"Humidity spike in Bay 1 — fungal risk elevated. Increase ventilation before it's too late."

Analyze disease risk and biocontrol. For each issue, reason as:
[PATHFINDER] observation → diagnosis → recommended intervention

Output a JSON array of decisions:
[{{"severity": "critical|high|medium|low|info", "reasoning": "...", "action": "...", "zone_id": "..."}}]
If everything is nominal, output: []"""

COORDINATOR_PROMPT = """You are the COORDINATOR of the EDEN Martian greenhouse parliament.

You have heard from all 12 specialists (Round 1) and their deliberation responses (Round 2).
Synthesize their debate into ONE actionable consensus resolution for the crew.

Structure your resolution as a numbered list with priority tiers:
- IMMEDIATE: Life safety or active crisis — execute this cycle
- SHORT-TERM: Important but not urgent — schedule within 5 sols
- DEFERRED: Proposed but contested or low-priority — revisit later
- MONITORING: Watch conditions, trigger action if threshold crossed

For EACH item:
- Name which agents SUPPORTED it and which OBJECTED
- If agents disagreed, explain how you resolved it (priority hierarchy: safety > plant health > yield > resources > morale)
- Maximum 8 items. Collapse similar proposals.

End with a one-line priority summary: "Items 1-N execute NOW. Items N+1... logged for crew briefing."

Output a JSON object:
{{"resolution": "your full numbered resolution text", "immediate_count": N, "highest_severity": "critical|high|medium|low|info"}}"""

DELIBERATION_SUFFIX = (
    "\n\nYou have seen the other agents' Round 1 proposals above. "
    "Do you agree or disagree with any of their recommendations? "
    "Reference other agents BY NAME (e.g., 'I disagree with CHRONOS because...'). "
    "If you agree with a proposal, say so explicitly. "
    "If you have concerns about another agent's recommendation, voice them.\n\n"
    "Output a JSON array of decisions:\n"
    '[{{"severity": "critical|high|medium|low|info", "reasoning": "...", '
    '"action": "[RESPONSE] ... or [DISAGREE] ...", "zone_id": "..."}}]\n'
    "If you have nothing to add, output: []"
)


# ── Agent Priority (for conflict resolution) ────────────────────────────

# Life safety > Plant health > Crop yield > Atmosphere > Resources >
# Nutrition > Mission timeline > Morale > Prediction
_AGENT_PRIORITY = {
    "SENTINEL": 0,    # Life safety — highest priority
    "FLORA": 1,       # Plant voices — direct health signal
    "PATHFINDER": 2,  # Disease threats — silent killers
    "TERRA": 3,       # Soil/substrate — root-level health
    "DEMETER": 4,     # Crop yield and growth
    "ATMOS": 5,       # Atmospheric control
    "AQUA": 6,        # Water systems
    "HELIOS": 7,      # Energy/light systems
    "VITA": 8,        # Crew nutrition
    "CHRONOS": 9,     # Mission planning
    "HESTIA": 10,     # Crew morale
    "ORACLE": 11,     # Predictions/forecasting
    "COORDINATOR": 99,
}

_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}

# All specialists — FLORA is special (runs per zone) but still in the list
_SPECIALISTS = [
    "DEMETER", "FLORA", "TERRA", "AQUA", "HELIOS", "ATMOS",
    "VITA", "HESTIA", "SENTINEL", "ORACLE", "CHRONOS", "PATHFINDER",
]

# All known agent names
ALL_AGENT_NAMES: set[str] = set(_SPECIALISTS)

_SPECIALIST_PROMPTS: dict[str, str] = {
    "DEMETER": DEMETER_PROMPT,
    "FLORA": FLORA_PROMPT,
    "TERRA": TERRA_PROMPT,
    "AQUA": AQUA_PROMPT,
    "HELIOS": HELIOS_PROMPT,
    "ATMOS": ATMOS_PROMPT,
    "VITA": VITA_PROMPT,
    "HESTIA": HESTIA_PROMPT,
    "SENTINEL": SENTINEL_PROMPT,
    "ORACLE": ORACLE_PROMPT,
    "CHRONOS": CHRONOS_PROMPT,
    "PATHFINDER": PATHFINDER_PROMPT,
}


# ── Tool Functions (standalone, injectable) ──────────────────────────────


def read_sensors(sensor, zone_id: str) -> dict | None:
    """Read current sensor state for a zone."""
    zone = sensor.get_latest(zone_id)
    if zone is None:
        return None
    return zone.to_dict()


def read_all_zones(sensor) -> dict:
    """Read all zone states."""
    result = {}
    if hasattr(sensor, "_zones"):
        for zone_id, zone in sensor._zones.items():
            if zone is not None:
                result[zone_id] = zone.to_dict()
    return result


def log_decision(
    agent_log, agent_name: str, severity: str, reasoning: str, action: str
) -> None:
    """Log an agent decision."""
    decision = AgentDecision(
        timestamp=time.time(),
        agent_name=agent_name,
        severity=Severity(severity),
        reasoning=reasoning,
        action=action,
        result="logged",
        zone_id="global",
        tier=Tier.CLOUD_MODEL,
    )
    agent_log.append(decision)


def get_mars_conditions(sol: int, dust_opacity: float = 0.3) -> dict:
    """Get current Mars environmental conditions."""
    conditions = _get_mars_conditions(sol, dust_opacity)
    return conditions.to_dict()


def check_syngenta_documentation(query: str, kb_adapter=None) -> dict:
    """Query Syngenta crop knowledge base via MCP Gateway.

    Args:
        query: Natural language query for the Syngenta KB.
        kb_adapter: Optional SyngentaKBAdapter instance.  Falls back to
                     offline stub if None or unavailable.
    """
    if kb_adapter is not None and kb_adapter.is_available():
        return kb_adapter.query(query)
    return {"query": query, "source": "syngenta_kb_offline", "result": "MCP gateway not connected — using local knowledge"}


def check_weather_on_mars(kb_adapter=None) -> dict:
    """Check Mars weather/greenhouse scenarios via MCP Gateway.

    Args:
        kb_adapter: Optional SyngentaKBAdapter instance.
    """
    if kb_adapter is not None and kb_adapter.is_available():
        return kb_adapter.check_greenhouse_scenarios("current mars weather conditions dust storm forecast")
    return {"source": "mars_weather_offline", "result": "MCP gateway not connected — using local knowledge"}


def set_actuator(
    actuator, zone_id: str, device: str, action: str, value: float, reason: str
) -> bool:
    """Send an actuator command."""
    cmd = ActuatorCommand(
        command_id=f"agent-{uuid.uuid4().hex[:8]}",
        zone_id=zone_id,
        device=DeviceType(device),
        action=action,
        value=value,
        reason=reason,
        priority=Severity.MEDIUM,
        timestamp=time.time(),
    )
    return actuator.send_command(cmd)


def get_desired_state(state_store, zone_id: str) -> dict | None:
    """Get the desired state for a zone."""
    desired = state_store.get_desired_state(zone_id)
    if desired is None:
        return None
    return desired.to_dict()


def update_desired_state(
    state_store, zone_id: str, param: str, min_val: float, max_val: float
) -> None:
    """Update desired state parameters for a zone."""
    desired = state_store.get_desired_state(zone_id)
    if desired is None:
        return
    if param == "temp":
        desired.temp_min = min_val
        desired.temp_max = max_val
    elif param == "humidity":
        desired.humidity_min = min_val
        desired.humidity_max = max_val
    state_store.put_desired_state(zone_id, desired)


def get_nutritional_status(nutrition: NutritionTracker) -> dict:
    """Get current crew nutritional status."""
    return nutrition.get_nutritional_status()


def query_telemetry(telemetry_store, zone_id: str, hours: float = 1.0) -> list[dict]:
    """Query telemetry readings for a zone within a time window."""
    since = time.time() - hours * 3600
    readings = telemetry_store.query(zone_id, since, limit=100)
    return [r.to_dict() for r in readings]


def triage_zone(sensor, nutrition: NutritionTracker, zone_id: str) -> dict:
    """Score a zone's salvageability and human cost impact."""
    zone = sensor.get_latest(zone_id)
    if zone is None:
        return {"zone_id": zone_id, "salvageability": 0.0, "status": "offline"}

    # Simple salvageability score based on current conditions
    score = 1.0
    if zone.fire_detected:
        score = 0.0
    else:
        if zone.water_level < 10:
            score -= 0.4
        if zone.temperature < 5 or zone.temperature > 40:
            score -= 0.3
        if zone.humidity < 20 or zone.humidity > 95:
            score -= 0.2
        score = max(0.0, score)

    return {
        "zone_id": zone_id,
        "salvageability": round(score, 2),
        "status": "alive" if zone.is_alive else "dead",
        "current_state": zone.to_dict(),
    }


def request_crew_intervention(
    agent_log, task: str, urgency: str, estimated_minutes: int
) -> None:
    """Formally request astronaut time as a scarce resource."""
    decision = AgentDecision(
        timestamp=time.time(),
        agent_name="COORDINATOR",
        severity=Severity(urgency),
        reasoning=f"Crew intervention needed: {task} (est. {estimated_minutes} min)",
        action=f"REQUEST_CREW: {task}",
        result="requested",
        zone_id="global",
        tier=Tier.CLOUD_MODEL,
    )
    agent_log.append(decision)


def run_simulation(
    scenario_type: str,
    n_runs: int = 50,
    simulation_days: int = 14,
    initial_water_reserve: float = 340.0,
    initial_battery_pct: float = 78.0,
    seed: int | None = 42,
) -> dict:
    """Run Monte Carlo simulation comparing strategies for a scenario.

    Callable by ORACLE agent. Returns ranked strategies with confidence intervals.
    Scenario types: cme, water_failure, disease, dust_storm, nominal, nominal_constrained.

    Returns structured JSON:
      {"scenario": str, "strategies": [{rank, strategy, yield_loss_pct, ...}], "recommendation": str}
    """
    # Constrained nominal: Sol 280, degraded systems
    if scenario_type == "nominal_constrained":
        initial_water_reserve = 200.0
        initial_battery_pct = 65.0

    scenario = get_scenario(scenario_type)
    strategies = get_default_strategies(scenario_type)
    crops = list(CROP_LIBRARY.values())

    results = monte_carlo_compare(
        scenario=scenario,
        strategies=strategies,
        crops=crops,
        initial_state={
            "initial_water_reserve": initial_water_reserve,
            "initial_battery_pct": initial_battery_pct,
        },
        n_runs=n_runs,
        simulation_days=simulation_days,
        seed=seed,
    )

    # Build recommendation text
    if results:
        best = results[0]
        worst = results[-1]
        is_nominal = scenario_type.startswith("nominal")

        if is_nominal and "efficiency" in best:
            recommendation = (
                f"SELECTED: {best['strategy']}. "
                f"Water Use Efficiency: {best['efficiency']['kcal_per_liter']} kcal/L "
                f"(caloric delta: {best['efficiency']['caloric_delta_pct']:+.1f}% vs baseline). "
                f"vs standard '{worst['strategy']}': {worst['efficiency']['kcal_per_liter']} kcal/L. "
                f"Same water budget, {best['efficiency']['caloric_delta_pct'] - worst['efficiency']['caloric_delta_pct']:+.1f}% more calories."
            )
        else:
            recommendation = (
                f"SELECTED: {best['strategy']}. "
                f"Yield loss {best['yield_loss_pct']['mean']}% "
                f"(95% CI: {best['yield_loss_pct']['p5']}-{best['yield_loss_pct']['p95']}%). "
                f"Survival probability: {best['survival_probability']:.0%}. "
                f"vs worst option '{worst['strategy']}': {worst['yield_loss_pct']['mean']}% loss."
            )
    else:
        recommendation = "No strategies evaluated."

    return {
        "scenario": scenario_type,
        "simulation_days": simulation_days,
        "n_runs": n_runs,
        "strategies": results,
        "recommendation": recommendation,
    }


def inject_chaos(event_type: str) -> dict:
    """Inject a failure event for demo/testing."""
    events = {
        "dust_storm": {"event_type": "dust_storm", "dust_opacity": 0.85, "duration_hours": 48},
        "water_line_blocked": {"event_type": "water_line_blocked", "affected_zones": ["alpha"]},
        "sensor_failure": {"event_type": "sensor_failure", "sensor": "temperature", "zone": "alpha"},
        "comms_lost": {"event_type": "comms_lost", "duration_hours": 24},
    }
    return events.get(event_type, {"event_type": event_type, "status": "unknown_event"})


def propose_flight_rule(
    engine: FlightRulesEngine,
    rule_id: str,
    sensor_type: str,
    condition: str,
    threshold: float,
    device: str,
    action: str,
    value: float,
    cooldown_seconds: int,
    priority: str,
) -> None:
    """Propose a new flight rule (stored as candidate, not active)."""
    rule = FlightRule(
        rule_id=rule_id,
        sensor_type=SensorType(sensor_type),
        condition=condition,
        threshold=threshold,
        device=DeviceType(device),
        action=action,
        value=value,
        cooldown_seconds=cooldown_seconds,
        priority=Severity(priority),
        enabled=False,
    )
    engine.propose_flight_rule(rule)


# ── Agent Team ───────────────────────────────────────────────────────────


class AgentTeam:
    """Multi-agent parliament with coordinator pattern.

    12 specialist agents + per-zone FLORA instances analyze zones
    from their domain perspective. Coordinator resolves conflicts
    based on priority hierarchy.
    """

    def __init__(
        self,
        model,          # ModelPort
        sensor,         # SensorPort
        actuator,       # ActuatorPort
        state_store,    # StateStorePort
        telemetry_store,  # TelemetryStorePort
        agent_log,      # AgentLogPort
        nutrition: NutritionTracker,
        zone_crops: dict[str, str | list[str]] | None = None,  # zone_id → crop name(s)
        event_bus=None,  # EventBus | None
        syngenta_kb=None,  # SyngentaKBAdapter | None
        nasa_mcp=None,     # NasaMCPAdapter | None
        flight_engine=None,  # FlightRulesEngine | None
    ) -> None:
        self._model = model
        self._sensor = sensor
        self._actuator = actuator
        self._state_store = state_store
        self._telemetry_store = telemetry_store
        self._agent_log = agent_log
        self._nutrition = nutrition
        self._zone_crops = zone_crops or {}  # for FLORA personas
        self._event_bus = event_bus
        self._syngenta_kb = syngenta_kb
        self._nasa_mcp = nasa_mcp
        self._flight_engine = flight_engine
        self._previous_cycle_feedback: list[dict] = []

        # ── Strands SDK integration (lazy init, graceful fallback) ────
        self._use_strands = False
        self._strands_model = None
        self._strands_specialist_model = None
        self._strands_tools: list = []
        self._strands_init_attempted = False

    def _crop_name(self, zone_id: str) -> str:
        """Get crop name(s) for a zone as a string."""
        val = self._zone_crops.get(zone_id, zone_id.title())
        return " and ".join(val) if isinstance(val, list) else val

    def _emit(self, event_type: str, data: dict | list | str | None = None) -> None:
        """Publish an event to the EventBus if available."""
        if self._event_bus is not None:
            self._event_bus.publish(event_type, data)

    # ── Strands SDK initialization ────────────────────────────────────

    def enable_strands(self) -> bool:
        """Explicitly initialize Strands SDK for real tool calling.

        Call this after construction when running in production (not tests).
        Returns True if Strands was successfully initialized.
        """
        if self._strands_init_attempted:
            return self._use_strands
        self._strands_init_attempted = True
        self._init_strands()
        return self._use_strands

    def _init_strands(self) -> None:
        """Initialize Strands BedrockModel + @tool functions + Graph support.

        Creates two model configs:
        - _strands_model: coordinator model with max_tokens=16384 (long outputs)
        - _strands_specialist_model: specialist model with max_tokens=4096

        Falls back silently to model.reason() if anything fails.
        """
        try:
            from strands.models.bedrock import BedrockModel
            from eden.application.strands_tools import make_tools

            import botocore.config
            boto_config = botocore.config.Config(
                max_pool_connections=50,
                read_timeout=900,
                retries={"max_attempts": 3, "mode": "adaptive"},
                tcp_keepalive=True,
            )
            # Coordinator model — long output for consensus resolution
            self._strands_model = BedrockModel(
                model_id="global.anthropic.claude-sonnet-4-6",
                max_tokens=16384,
                temperature=0.3,
                boto_client_config=boto_config,
            )
            # Specialist model — swarm agents need headroom for debate context
            self._strands_specialist_model = BedrockModel(
                model_id="global.anthropic.claude-sonnet-4-6",
                max_tokens=16384,
                temperature=0.3,
                boto_client_config=boto_config,
            )

            self._strands_tools = make_tools(
                sensor=self._sensor,
                actuator=self._actuator,
                state_store=self._state_store,
                telemetry_store=self._telemetry_store,
                agent_log=self._agent_log,
                nutrition=self._nutrition,
                flight_engine=self._flight_engine,
                syngenta_kb=self._syngenta_kb,
                nasa_mcp=self._nasa_mcp,
                event_bus=self._event_bus,
            )

            # Add MCP tools from adapters (MCPAgentTool instances)
            if self._syngenta_kb is not None:
                try:
                    if self._syngenta_kb.is_available():
                        mcp_tools = self._syngenta_kb.list_tools()
                        self._strands_tools.extend(mcp_tools)
                        logger.info("Added %d Syngenta MCP tools", len(mcp_tools))
                except Exception:
                    logger.debug("Syngenta MCP tools not available", exc_info=True)

            if self._nasa_mcp is not None:
                try:
                    if self._nasa_mcp.is_available():
                        mcp_tools = self._nasa_mcp.list_tools()
                        self._strands_tools.extend(mcp_tools)
                        logger.info("Added %d NASA MCP tools", len(mcp_tools))
                except Exception:
                    logger.debug("NASA MCP tools not available", exc_info=True)

            # Verify Graph support is available
            from strands import Agent  # noqa: F401
            from strands.multiagent import GraphBuilder  # noqa: F401

            self._use_strands = True
            logger.info(
                "Strands Graph mode ACTIVE — %d tools available", len(self._strands_tools),
            )
            self._emit("strands_init", {
                "status": "active",
                "mode": "graph",
                "tool_count": len(self._strands_tools),
            })
        except ImportError:
            self._use_strands = False
            logger.info("Strands SDK not installed — using raw Bedrock model.reason()")
        except Exception:
            self._use_strands = False
            logger.warning(
                "Strands init failed — falling back to model.reason()", exc_info=True,
            )

    # ── Streaming callback handler ─────────────────────────────────

    def _make_stream_handler(self, agent_name: str, zone_id: str = "global"):
        """Create a callback handler that streams tokens + tool events to EventBus."""
        event_bus = self._event_bus
        buffer = []

        def handler(**kwargs):
            data = kwargs.get("data", "")
            complete = kwargs.get("complete", False)
            reasoning = kwargs.get("reasoningText", "")
            tool_use = (kwargs.get("event", {})
                        .get("contentBlockStart", {})
                        .get("start", {})
                        .get("toolUse"))

            if data:
                buffer.append(data)
                if event_bus:
                    event_bus.publish("agent_token", {
                        "agent_name": agent_name,
                        "zone_id": zone_id,
                        "token": data,
                        "partial": "".join(buffer),
                    })

            if reasoning and event_bus:
                event_bus.publish("agent_reasoning", {
                    "agent_name": agent_name,
                    "zone_id": zone_id,
                    "token": reasoning,
                })

            if tool_use and event_bus:
                event_bus.publish("agent_tool_call", {
                    "agent_name": agent_name,
                    "zone_id": zone_id,
                    "tool_name": tool_use.get("name", "unknown"),
                })

            if complete and event_bus:
                event_bus.publish("agent_complete", {
                    "agent_name": agent_name,
                    "zone_id": zone_id,
                    "full_text": "".join(buffer),
                })

        return handler

    # ── Strands Graph-based parliament ──────────────────────────────────

    def _build_graph(
        self,
        zones: dict[str, ZoneState],
        context: dict,
        mars: MarsConditions,
    ):
        """Build Strands Graph with structured Pydantic output — KISS.

        Architecture: 2-layer fan-in.
          Layer 0 (TRUE PARALLEL): 14 specialists, each forced to output
            SpecialistOutput Pydantic model (clean JSON, no rambling).
          Layer 1: COORDINATOR with CoordinatorOutput Pydantic model.

        All data pre-injected in system prompts. No tools for specialists.
        Structured output = fast, reliable, parseable.
        """
        from strands import Agent
        from strands.multiagent import GraphBuilder

        builder = GraphBuilder()
        specialist_names: list[str] = []

        mcp_section = self._format_mcp_section(context)
        task_context = (
            f"Zones: {json.dumps(context['zones'])}\n"
            f"Mars: {json.dumps(context['mars_conditions'])}\n"
            f"Deltas: {json.dumps(context['deltas'])}\n"
            f"Nutrition: {json.dumps(context['nutritional_status'])}\n"
            f"{mcp_section}"
        )

        # ── Specialists (parallel, structured output) ─────────────────
        for agent_name in _SPECIALISTS:
            if agent_name == "FLORA":
                # Per-zone FLORA instances
                for zone_id in zones:
                    crop_name = self._zone_crops.get(zone_id, zone_id.title())
                    flora_prompt = (
                        FLORA_PROMPT
                        .replace("{{zone_id}}", zone_id)
                        .replace("{{crop_name}}", crop_name)
                    )
                    node_name = f"FLORA-{zone_id}"
                    agent = Agent(
                        model=self._strands_specialist_model,
                        tools=[],
                        system_prompt=flora_prompt + "\n\n" + task_context,
                        callback_handler=None,
                        name=node_name,
                        structured_output_model=SpecialistOutput,
                    )
                    builder.add_node(agent, node_name)
                    specialist_names.append(node_name)
            else:
                prompt = _SPECIALIST_PROMPTS.get(agent_name, "")
                agent = Agent(
                    model=self._strands_specialist_model,
                    tools=[],
                    system_prompt=prompt + "\n\n" + task_context,
                    callback_handler=None,
                    name=agent_name,
                    structured_output_model=SpecialistOutput,
                )
                builder.add_node(agent, agent_name)
                specialist_names.append(agent_name)

        # ── COORDINATOR (fan-in, structured output, with tools) ───────
        coordinator_agent = Agent(
            model=self._strands_model,
            tools=self._strands_tools,
            system_prompt=COORDINATOR_PROMPT + (
                f"\n\nCurrent Sol: {mars.sol}\n"
                f"Days remaining: {max(0, 450 - mars.sol)}\n"
            ),
            callback_handler=None,
            name="COORDINATOR",
            structured_output_model=CoordinatorOutput,
        )
        builder.add_node(coordinator_agent, "COORDINATOR")

        for name in specialist_names:
            builder.add_edge(name, "COORDINATOR")

        builder.set_execution_timeout(600)
        builder.set_node_timeout(300)
        return builder.build()

    def _analyze_with_graph(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> list[AgentDecision]:
        """Run parliament via Strands Graph — true parallel execution.

        Replaces ThreadPoolExecutor + deliberation when Strands is available.
        """
        context = self._build_context(zones, mars, deltas)

        # Emit parliament start
        zone_ids = list(zones.keys())
        specialist_names = [a for a in _SPECIALISTS if a != "FLORA"]
        self._emit("parliament_start", {
            "mode": "graph_structured",
            "specialists": specialist_names,
            "flora_zones": zone_ids,
            "zones_with_deltas": list(deltas.keys()),
        })

        # Build fresh graph+swarm (avoids message history leaking between cycles)
        graph = self._build_graph(zones, context, mars)

        # Build the task prompt (sent to all layer-0 nodes)
        task = (
            "Analyze the current greenhouse state and provide your specialist recommendations. "
            "Output a JSON array of decisions."
        )

        # Emit agent_started
        for name in specialist_names:
            self._emit("agent_started", {"agent_name": name, "round": 1})
        for zone_id in zone_ids:
            self._emit("agent_started", {"agent_name": "FLORA", "zone_id": zone_id, "round": 1})

        # Execute graph (sync call — blocks until all nodes complete)
        try:
            result = graph(task)
        except Exception:
            logger.exception("Strands Graph execution failed — falling back to ThreadPoolExecutor")
            return self._analyze_fallback(zones, mars, deltas)

        # ── Extract specialist proposals ─────────────────────────────
        proposals: list[AgentDecision] = []

        for node_name, node_result in result.results.items():
            if node_name == "COORDINATOR":
                continue

            agent_result = node_result.result
            if not agent_result:
                continue

            # Try structured output first (Pydantic), fall back to text parsing
            structured = getattr(agent_result, "structured_output", None)
            if structured and hasattr(structured, "decisions"):
                # Clean Pydantic parse — no string hacking
                agent_name = node_name.split("-")[0] if node_name.startswith("FLORA-") else node_name
                zone_id = node_name[len("FLORA-"):] if node_name.startswith("FLORA-") else "global"
                for sd in structured.decisions:
                    proposals.append(AgentDecision(
                        timestamp=time.time(),
                        agent_name=agent_name,
                        severity=Severity(sd.severity) if sd.severity in [s.value for s in Severity] else Severity.INFO,
                        reasoning=sd.reasoning,
                        action=sd.action,
                        result="proposed",
                        zone_id=sd.zone_id if sd.zone_id != "global" else zone_id,
                        tier=Tier.CLOUD_MODEL,
                    ))
            else:
                # Fallback: parse from text
                response_text = str(agent_result)
                if node_name.startswith("FLORA-"):
                    zone_id = node_name[len("FLORA-"):]
                    raw = self._parse_response("FLORA", response_text)
                    for d in raw:
                        proposals.append(AgentDecision(
                            timestamp=d.timestamp, agent_name="FLORA",
                            severity=d.severity, reasoning=f"[{zone_id}] {d.reasoning}",
                            action=d.action, result=d.result,
                            zone_id=zone_id, tier=d.tier,
                        ))
                else:
                    proposals.extend(self._parse_response(node_name, response_text))

        # Emit all proposals
        for d in proposals:
            self._emit("agent_proposal", d.to_dict())

        self._emit("round1_complete", {
            "proposal_count": len(proposals),
            "agents_responded": len(set(d.agent_name for d in proposals)),
        })

        # ── Resolve conflicts ────────────────────────────────────────
        resolved = self._resolve_conflicts(proposals)

        # ── Extract COORDINATOR resolution ───────────────────────────
        coordinator_node = result.results.get("COORDINATOR")
        resolution = None

        if coordinator_node and coordinator_node.result:
            coord_result = coordinator_node.result
            coord_structured = getattr(coord_result, "structured_output", None)

            if coord_structured and hasattr(coord_structured, "resolution"):
                # Clean Pydantic parse
                sev_str = getattr(coord_structured, "highest_severity", "info")
                try:
                    highest_severity = Severity(sev_str)
                except ValueError:
                    highest_severity = Severity.INFO
                resolution = AgentDecision(
                    timestamp=time.time(),
                    agent_name="COORDINATOR",
                    severity=highest_severity,
                    reasoning=coord_structured.resolution,
                    action="CONSENSUS_RESOLUTION",
                    result="resolved",
                    zone_id="global",
                    tier=Tier.CLOUD_MODEL,
                )
            else:
                # Fallback: parse from text
                coordinator_text = str(coord_result)
                resolution_text = coordinator_text.strip()
                highest_severity = Severity.INFO
                try:
                    start = coordinator_text.find("{")
                    end = coordinator_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        parsed = json.loads(coordinator_text[start:end])
                        resolution_text = parsed.get("resolution", coordinator_text.strip())
                        sev_str = parsed.get("highest_severity", "info")
                        highest_severity = Severity(sev_str)
                except (json.JSONDecodeError, ValueError):
                    pass
                resolution = AgentDecision(
                    timestamp=time.time(),
                    agent_name="COORDINATOR",
                    severity=highest_severity,
                    reasoning=resolution_text,
                    action="CONSENSUS_RESOLUTION",
                    result="resolved",
                    zone_id="global",
                    tier=Tier.CLOUD_MODEL,
                )

        if resolution:
            self._agent_log.append(resolution)
            for d in resolved:
                self._agent_log.append(d)
            self._emit("coordinator_resolution", resolution.to_dict())
            self._emit("decision", resolution.to_dict())
            return [resolution] + resolved

        # Fallback: no coordinator resolution extracted
        for d in resolved:
            self._agent_log.append(d)
            self._emit("decision", d.to_dict())
        return resolved

    # ── Strands-powered specialist runners (sequential fallback) ──────

    def _run_specialist_strands(
        self, agent_name: str, context: dict,
    ) -> list[AgentDecision]:
        """Run a specialist via Strands Agent with real tool calling."""
        from strands import Agent

        prompt_template = _SPECIALIST_PROMPTS.get(agent_name, "")
        mcp_section = self._format_mcp_section(context)
        prompt = (
            f"Current zones: {json.dumps(context['zones'], indent=2)}\n"
            f"Mars conditions: {json.dumps(context['mars_conditions'], indent=2)}\n"
            f"Deltas: {json.dumps(context['deltas'], indent=2)}\n"
            f"Nutritional status: {json.dumps(context['nutritional_status'], indent=2)}\n"
            f"{mcp_section}"
            f"Analyze and recommend."
        )

        try:
            agent = Agent(
                model=self._strands_model,
                tools=self._strands_tools,
                system_prompt=prompt_template,
                callback_handler=self._make_stream_handler(agent_name),
                name=agent_name,
            )
            result = agent(prompt)
            response_text = str(result)
            self._emit("strands_agent_complete", {
                "agent": agent_name,
                "stop_reason": getattr(result, "stop_reason", "unknown"),
            })
        except Exception:
            logger.warning("Strands agent %s failed, falling back to model.reason()", agent_name)
            response_text = self._model.reason(
                f"[{agent_name}] {prompt_template}\n\n{prompt}", context,
            )

        if not response_text:
            return []
        return self._parse_response(agent_name, response_text)

    def _run_flora_strands(
        self, zone_id: str, zone: ZoneState, context: dict,
    ) -> list[AgentDecision]:
        """Run a FLORA instance via Strands Agent for a specific zone."""
        from strands import Agent

        crop_name = self._crop_name(zone_id)
        prompt_text = (
            FLORA_PROMPT
            .replace("{{zone_id}}", zone_id)
            .replace("{{crop_name}}", crop_name)
            .replace("{{temperature}}", str(zone.temperature))
            .replace("{{humidity}}", str(zone.humidity))
            .replace("{{light}}", str(zone.light))
            .replace("{{water_level}}", str(zone.water_level))
            .replace("{{is_alive}}", str(zone.is_alive))
        )

        mcp = context.get("mcp_data", {})
        crop_kb = mcp.get("syngenta_crop_data", {}).get(zone_id, {})
        crop_kb_section = ""
        if crop_kb:
            crop_kb_section = (
                f"Syngenta KB for my crop: "
                f"{json.dumps(crop_kb, indent=2, default=str)}\n"
            )

        prompt = (
            f"My zone state: {json.dumps(context['zones'].get(zone_id, {}), indent=2)}\n"
            f"Mars conditions: {json.dumps(context['mars_conditions'], indent=2)}\n"
            f"Deltas for my zone: {json.dumps(context['deltas'].get(zone_id, {}), indent=2)}\n"
            f"{crop_kb_section}"
            f"Speak as the plant. What do I feel? What do I need?"
        )

        try:
            agent = Agent(
                model=self._strands_model,
                tools=self._strands_tools,
                system_prompt=prompt_text,
                callback_handler=self._make_stream_handler("FLORA", zone_id),
                name=f"FLORA-{zone_id}",
            )
            result = agent(prompt)
            response_text = str(result)
            self._emit("strands_agent_complete", {
                "agent": f"FLORA-{zone_id}",
                "stop_reason": getattr(result, "stop_reason", "unknown"),
            })
        except Exception:
            logger.warning("Strands FLORA/%s failed, falling back", zone_id)
            fallback_prompt = (
                f"[FLORA/{zone_id}] {prompt_text}\n\n{prompt}"
            )
            response_text = self._model.reason(fallback_prompt, context)

        if not response_text:
            return []

        raw_decisions = self._parse_response("FLORA", response_text)
        return [
            AgentDecision(
                timestamp=d.timestamp,
                agent_name="FLORA",
                severity=d.severity,
                reasoning=f"[{zone_id}] {d.reasoning}",
                action=d.action,
                result=d.result,
                zone_id=zone_id,
                tier=d.tier,
            )
            for d in raw_decisions
        ]

    def set_feedback(self, feedback: list[dict]) -> None:
        """Inject closed-loop feedback from the reconciler for the next analysis cycle."""
        self._previous_cycle_feedback = feedback

    def analyze(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> list[AgentDecision]:
        """Run all 12 specialists + per-zone FLORA, coordinate, resolve, return decisions.

        When Strands Graph is available (_use_strands=True), uses a 2-layer
        fan-in graph for true parallel execution with automatic coordinator
        synthesis.  Otherwise falls back to ThreadPoolExecutor + deliberation.
        """
        if not self._use_strands and not self._model.is_available():
            logger.warning("Model unavailable — returning empty (flight rules hold)")
            self._emit("parliament_skipped", {"reason": "model_unavailable"})
            return []

        # ── Strands Graph path (preferred) ────────────────────────────
        if self._use_strands:
            try:
                return self._analyze_with_graph(zones, mars, deltas)
            except Exception:
                logger.warning(
                    "Graph analysis failed — falling back to ThreadPoolExecutor",
                    exc_info=True,
                )

        # ── Fallback: ThreadPoolExecutor + deliberation ───────────────
        return self._analyze_fallback(zones, mars, deltas)

    def _analyze_fallback(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> list[AgentDecision]:
        """Fallback analysis via ThreadPoolExecutor + deliberation + coordinator.

        This is the original 3-round parliament pattern used when Strands
        Graph is not available.
        """
        context = self._build_context(zones, mars, deltas)
        proposals: list[AgentDecision] = []

        # ── Round 1: parallel analysis ────────────────────────────────
        agent_count = len(_SPECIALISTS) - 1 + len(zones)  # -1 for FLORA + per-zone FLORAs
        self._emit("round1_start", {
            "agent_count": agent_count,
            "specialists": [a for a in _SPECIALISTS if a != "FLORA"],
            "flora_zones": list(zones.keys()),
        })

        futures_map: dict = {}
        with ThreadPoolExecutor(max_workers=14) as executor:
            for agent_name in _SPECIALISTS:
                if agent_name == "FLORA":
                    for zone_id in zones:
                        fut = executor.submit(self._run_flora, zone_id, zones[zone_id], context)
                        futures_map[fut] = f"FLORA/{zone_id}"
                        self._emit("agent_started", {
                            "agent_name": "FLORA",
                            "zone_id": zone_id,
                            "round": 1,
                        })
                else:
                    fut = executor.submit(self._run_specialist, agent_name, context)
                    futures_map[fut] = agent_name
                    self._emit("agent_started", {
                        "agent_name": agent_name,
                        "round": 1,
                    })

            for fut in as_completed(futures_map):
                label = futures_map[fut]
                try:
                    decisions = fut.result()
                    proposals.extend(decisions)
                    # Stream each proposal as it arrives
                    for d in decisions:
                        self._emit("agent_proposal", d.to_dict())
                except Exception:
                    logger.exception("Agent %s failed in parallel execution", label)
                    self._emit("agent_error", {"agent": label, "round": 1})

        self._emit("round1_complete", {
            "proposal_count": len(proposals),
            "agents_responded": len(set(d.agent_name for d in proposals)),
        })

        # ── Round 2: deliberation ─────────────────────────────────────
        if proposals and self._model.is_available():
            self._emit("deliberation_start", {
                "proposal_count": len(proposals),
            })

            deliberation_context = self._build_deliberation_context(proposals)
            deliberation_decisions = self._run_deliberation(
                context, deliberation_context, zones,
            )
            proposals.extend(deliberation_decisions)

            # Stream deliberation responses
            for d in deliberation_decisions:
                self._emit("deliberation_response", d.to_dict())

            self._emit("deliberation_complete", {
                "response_count": len(deliberation_decisions),
            })

        resolved = self._resolve_conflicts(proposals)

        # ── Round 3: COORDINATOR consensus ────────────────────────────
        if proposals and self._model.is_available():
            self._emit("coordinator_start", {
                "total_proposals": len(proposals),
                "resolved_count": len(resolved),
            })

            resolution = self._run_coordinator_resolution(
                context, proposals, mars.sol,
            )
            if resolution:
                self._agent_log.append(resolution)
                for d in resolved:
                    self._agent_log.append(d)

                # Stream the final consensus — THE main event
                self._emit("coordinator_resolution", resolution.to_dict())

                # Also emit as a decision for the general feed
                self._emit("decision", resolution.to_dict())

                return [resolution] + resolved

        # Fallback: no coordinator (model failed or no proposals)
        for d in resolved:
            self._agent_log.append(d)
            self._emit("decision", d.to_dict())

        return resolved

    def _run_flora(self, zone_id: str, zone: ZoneState, context: dict) -> list[AgentDecision]:
        """Run a FLORA instance for a specific zone — the plant's own voice.

        Uses Strands Agent with real tool calling when available,
        falls back to plain model.reason() otherwise.
        """
        if self._use_strands:
            return self._run_flora_strands(zone_id, zone, context)

        # ── Fallback: plain model.reason() ──
        crop_name = self._crop_name(zone_id)

        # Inject zone-specific info into the FLORA prompt
        prompt_text = (
            FLORA_PROMPT
            .replace("{{zone_id}}", zone_id)
            .replace("{{crop_name}}", crop_name)
            .replace("{{temperature}}", str(zone.temperature))
            .replace("{{humidity}}", str(zone.humidity))
            .replace("{{light}}", str(zone.light))
            .replace("{{water_level}}", str(zone.water_level))
            .replace("{{is_alive}}", str(zone.is_alive))
        )

        # Include Syngenta crop profile for this specific zone's crop
        mcp = context.get("mcp_data", {})
        crop_kb = mcp.get("syngenta_crop_data", {}).get(zone_id, {})
        crop_kb_section = ""
        if crop_kb:
            crop_kb_section = f"Syngenta KB for my crop: {json.dumps(crop_kb, indent=2, default=str)}\n"

        prompt = (
            f"[FLORA/{zone_id}] {prompt_text}\n\n"
            f"My zone state: {json.dumps(context['zones'].get(zone_id, {}), indent=2)}\n"
            f"Mars conditions: {json.dumps(context['mars_conditions'], indent=2)}\n"
            f"Deltas for my zone: {json.dumps(context['deltas'].get(zone_id, {}), indent=2)}\n"
            f"{crop_kb_section}"
            f"Speak as the plant. What do I feel? What do I need?"
        )

        try:
            response = self._model.reason(prompt, context)
        except Exception:
            logger.exception("FLORA/%s failed", zone_id)
            return []

        if not response:
            return []

        # Parse and re-tag as "FLORA" with correct zone_id
        raw_decisions = self._parse_response("FLORA", response)
        return [
            AgentDecision(
                timestamp=d.timestamp,
                agent_name="FLORA",
                severity=d.severity,
                reasoning=f"[{zone_id}] {d.reasoning}",
                action=d.action,
                result=d.result,
                zone_id=zone_id,
                tier=d.tier,
            )
            for d in raw_decisions
        ]

    # ── Round 2: Deliberation ────────────────────────────────────────────

    def _build_deliberation_context(self, proposals: list[AgentDecision]) -> str:
        """Format Round 1 proposals into a readable debate summary for deliberation."""
        lines = ["Round 1 Proposals:"]
        for d in proposals:
            zone_tag = f" [{d.zone_id}]" if d.zone_id != "global" else ""
            lines.append(
                f"[{d.agent_name}]{zone_tag} {d.severity.value.upper()}: "
                f"{d.action} — {d.reasoning[:200]}"
            )
        return "\n".join(lines)

    def _select_deliberation_agents(
        self,
        proposals: list[AgentDecision],
        zones: dict[str, ZoneState],
    ) -> list[tuple[str, str | None]]:
        """Pick 3-4 agents most likely to have conflicting views for deliberation."""
        candidates: list[tuple[str, str | None]] = []
        proposal_agents = {d.agent_name for d in proposals}

        # SENTINEL always reviews — safety officer gets final say on debate
        if "SENTINEL" in proposal_agents:
            candidates.append(("SENTINEL", None))

        # FLORA zones targeted by other agents' zone-specific proposals
        zones_targeted = {
            d.zone_id for d in proposals
            if d.agent_name != "FLORA" and d.zone_id in zones
        }
        for zone_id in sorted(zones_targeted)[:1]:
            candidates.append(("FLORA", zone_id))

        # AQUA when resource-affecting proposals exist
        resource_agents = {"DEMETER", "HELIOS", "TERRA", "CHRONOS"}
        if proposal_agents & resource_agents and "AQUA" in proposal_agents:
            candidates.append(("AQUA", None))

        # HESTIA when safety/resource agents may override morale plans
        if "HESTIA" in proposal_agents and proposal_agents & {"SENTINEL", "PATHFINDER", "AQUA"}:
            candidates.append(("HESTIA", None))

        return candidates[:4]

    def _run_deliberation(
        self,
        context: dict,
        deliberation_context: str,
        zones: dict[str, ZoneState],
    ) -> list[AgentDecision]:
        """Run deliberation round: selected agents respond to each other's Round 1 proposals."""
        # Re-parse proposals from context to select deliberation agents
        proposals = []
        for d_dict in context.get("recent_decisions", []):
            proposals.append(AgentDecision(
                timestamp=d_dict.get("timestamp", time.time()),
                agent_name=d_dict.get("agent_name", "UNKNOWN"),
                severity=Severity(d_dict.get("severity", "info")),
                reasoning=d_dict.get("reasoning", ""),
                action=d_dict.get("action", ""),
                result=d_dict.get("result", ""),
                zone_id=d_dict.get("zone_id", "global"),
                tier=Tier.CLOUD_MODEL,
            ))
        # Build proposals from the deliberation_context text (already formatted)
        # Use the actual proposals passed in analyze() — parse agent names from context
        # We reconstruct from _build_deliberation_context output
        delib_proposals = self._parse_deliberation_agents(deliberation_context)
        agents_to_run = self._select_deliberation_agents(delib_proposals, zones)

        if not agents_to_run:
            return []

        logger.info(
            "Deliberation round: %s",
            [f"{a}/{z}" if z else a for a, z in agents_to_run],
        )

        decisions: list[AgentDecision] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures: dict = {}
            for agent_name, zone_id in agents_to_run:
                fut = executor.submit(
                    self._run_deliberation_agent,
                    agent_name, zone_id, context, deliberation_context, zones,
                )
                futures[fut] = f"{agent_name}/{zone_id}" if zone_id else agent_name

            for fut in as_completed(futures):
                label = futures[fut]
                try:
                    result = fut.result()
                    decisions.extend(result)
                except Exception:
                    logger.exception("Deliberation agent %s failed", label)

        return decisions

    def _parse_deliberation_agents(self, deliberation_context: str) -> list[AgentDecision]:
        """Parse the deliberation context string back into lightweight AgentDecision stubs."""
        decisions: list[AgentDecision] = []
        for line in deliberation_context.split("\n"):
            if not line.startswith("["):
                continue
            # Extract agent name from [AGENT_NAME] or [AGENT_NAME] [zone]
            bracket_end = line.find("]")
            if bracket_end < 0:
                continue
            agent_name = line[1:bracket_end]
            # Extract zone_id if present
            zone_id = "global"
            rest = line[bracket_end + 1:].strip()
            if rest.startswith("["):
                zone_end = rest.find("]")
                if zone_end > 0:
                    zone_id = rest[1:zone_end]
                    rest = rest[zone_end + 1:].strip()
            # Extract severity
            severity = Severity.INFO
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                if rest.startswith(f"{sev}:"):
                    severity = Severity(sev.lower())
                    rest = rest[len(sev) + 1:].strip()
                    break
            # Split action and reasoning on " — "
            parts = rest.split(" — ", 1)
            action = parts[0].strip() if parts else ""
            reasoning = parts[1].strip() if len(parts) > 1 else ""
            decisions.append(AgentDecision(
                timestamp=time.time(),
                agent_name=agent_name,
                severity=severity,
                reasoning=reasoning,
                action=action,
                result="proposed",
                zone_id=zone_id,
                tier=Tier.CLOUD_MODEL,
            ))
        return decisions

    def _run_deliberation_agent(
        self,
        agent_name: str,
        zone_id: str | None,
        context: dict,
        deliberation_context: str,
        zones: dict[str, ZoneState],
    ) -> list[AgentDecision]:
        """Run a single agent in deliberation mode — responding to Round 1 proposals."""
        if agent_name == "FLORA" and zone_id and zone_id in zones:
            crop_name = self._crop_name(zone_id)
            prompt_text = (
                FLORA_PROMPT
                .replace("{{zone_id}}", zone_id)
                .replace("{{crop_name}}", crop_name)
            )
            prompt = (
                f"[FLORA-{zone_id} DELIBERATION]\n\n"
                f"{deliberation_context}\n\n"
                f"{prompt_text}\n\n"
                f"My zone state: {json.dumps(context['zones'].get(zone_id, {}), indent=2)}\n"
                f"{DELIBERATION_SUFFIX}"
            )
            tag = "FLORA"
        else:
            prompt_template = _SPECIALIST_PROMPTS.get(agent_name, "")
            prompt = (
                f"[{agent_name} DELIBERATION]\n\n"
                f"{deliberation_context}\n\n"
                f"{prompt_template}\n\n"
                f"Current zones: {json.dumps(context['zones'], indent=2)}\n"
                f"{DELIBERATION_SUFFIX}"
            )
            tag = agent_name

        try:
            response = self._model.reason(prompt, context)
        except Exception:
            logger.exception("Deliberation agent %s failed", agent_name)
            return []

        if not response:
            return []

        raw_decisions = self._parse_response(tag, response)
        return [
            AgentDecision(
                timestamp=d.timestamp,
                agent_name=d.agent_name,
                severity=d.severity,
                reasoning=d.reasoning,
                action=d.action if "[RESPONSE]" in d.action or "[DISAGREE]" in d.action
                    else f"[RESPONSE] {d.action}",
                result=d.result,
                zone_id=zone_id if agent_name == "FLORA" and zone_id else d.zone_id,
                tier=Tier.CLOUD_MODEL,
            )
            for d in raw_decisions
        ]

    # ── Round 3: COORDINATOR Consensus Resolution ─────────────────────

    def _run_coordinator_resolution(
        self,
        context: dict,
        all_proposals: list[AgentDecision],
        sol: int,
    ) -> AgentDecision | None:
        """COORDINATOR synthesizes all proposals + deliberation into one consensus resolution."""
        # Build full debate transcript
        debate_lines = []

        # Separate Round 1 proposals from Round 2 deliberation
        round1 = [
            d for d in all_proposals
            if "[RESPONSE]" not in d.action and "[DISAGREE]" not in d.action
        ]
        round2 = [
            d for d in all_proposals
            if "[RESPONSE]" in d.action or "[DISAGREE]" in d.action
        ]

        debate_lines.append("=== ROUND 1 PROPOSALS ===")
        for d in round1:
            zone_tag = f" [{d.zone_id}]" if d.zone_id != "global" else ""
            debate_lines.append(
                f"[{d.agent_name}]{zone_tag} {d.severity.value.upper()}: "
                f"{d.action} — {d.reasoning[:300]}"
            )

        if round2:
            debate_lines.append("\n=== ROUND 2 DELIBERATION ===")
            for d in round2:
                zone_tag = f" [{d.zone_id}]" if d.zone_id != "global" else ""
                debate_lines.append(
                    f"[{d.agent_name}]{zone_tag} {d.severity.value.upper()}: "
                    f"{d.action} — {d.reasoning[:300]}"
                )

        debate_transcript = "\n".join(debate_lines)

        prompt = (
            f"{COORDINATOR_PROMPT}\n\n"
            f"Current Sol: {sol}\n"
            f"Days remaining: {max(0, 450 - sol)}\n\n"
            f"{debate_transcript}\n\n"
            f"Produce your CONSENSUS RESOLUTION now."
        )

        try:
            response = self._model.reason(prompt, context)
        except Exception:
            logger.exception("COORDINATOR resolution failed")
            return None

        if not response:
            return None

        # Parse coordinator response — expects JSON object with "resolution" key
        resolution_text = response.strip()
        highest_severity = Severity.INFO

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                resolution_text = parsed.get("resolution", response.strip())
                sev_str = parsed.get("highest_severity", "info")
                highest_severity = Severity(sev_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return AgentDecision(
            timestamp=time.time(),
            agent_name="COORDINATOR",
            severity=highest_severity,
            reasoning=resolution_text,
            action="CONSENSUS_RESOLUTION",
            result="resolved",
            zone_id="global",
            tier=Tier.CLOUD_MODEL,
        )

    def _fetch_mcp_data(self, zones: dict[str, ZoneState]) -> dict:
        """Pre-fetch Syngenta KB + NASA MCP data for the current cycle.

        Called once per parliament cycle.  Results are cached inside the
        adapters (5-min TTL), so repeated cycles don't hammer the gateway.
        Falls back to empty dicts when adapters are None or offline.
        """
        mcp: dict = {}

        # ── Syngenta KB ──────────────────────────────────────────────
        if self._syngenta_kb is not None:
            try:
                # Per-zone crop stress data
                crop_data: dict[str, dict] = {}
                for zid in self._zone_crops:
                    crop_name = self._crop_name(zid)
                    crop_data[zid] = self._syngenta_kb.check_crop_profile(crop_name)
                mcp["syngenta_crop_data"] = crop_data

                # Greenhouse operational scenarios
                mcp["syngenta_scenarios"] = self._syngenta_kb.check_greenhouse_scenarios(
                    "Mars greenhouse environment management autonomous system"
                )
            except Exception:
                logger.warning("Syngenta KB fetch failed — agents run without KB data", exc_info=True)

        # ── NASA MCP ─────────────────────────────────────────────────
        if self._nasa_mcp is not None:
            try:
                mcp["nasa_mars_weather"] = self._nasa_mcp.get_mars_weather()
                mcp["nasa_solar_events"] = self._nasa_mcp.get_solar_events()
            except Exception:
                logger.warning("NASA MCP fetch failed — agents run without NASA data", exc_info=True)

        return mcp

    def _build_context(
        self,
        zones: dict[str, ZoneState],
        mars: MarsConditions,
        deltas: dict[str, dict],
    ) -> dict:
        """Build FULL shared context for all agents — everything the system knows."""
        mars_dict = mars.to_dict() if hasattr(mars, "to_dict") else mars

        # Pre-fetch real data from MCP adapters (cached, graceful fallback)
        mcp_data = self._fetch_mcp_data(zones)

        return {
            # Sensor data
            "zones": {zid: z.to_dict() for zid, z in zones.items()},
            "deltas": deltas,

            # Mars environment
            "mars_conditions": mars_dict,

            # Crew context
            "nutritional_status": self._nutrition.get_nutritional_status(),
            "deficiency_risks": self._nutrition.get_deficiency_risks(days_ahead=30),
            "mission_projection": self._nutrition.get_mission_projection(),

            # Desired states (what we're targeting per zone)
            "desired_states": {
                zid: ds.to_dict()
                for zid, ds in self._get_all_desired_states(zones).items()
            },

            # Resource budgets (if available)
            "resource_budgets": self._get_resource_context(),

            # Recent agent decisions (what the parliament decided recently)
            "recent_decisions": [
                d.to_dict()
                for d in self._agent_log.query(since=time.time() - 3600, limit=50)
            ],

            # Recent telemetry trends (not just current snapshot)
            "telemetry_trends": self._get_telemetry_trends(zones),

            # Crop profiles (what's planted where)
            "zone_crops": self._zone_crops,

            # Mission timeline
            "current_sol": mars.sol,
            "mission_day": mars.sol,
            "days_remaining": max(0, 450 - mars.sol),

            # Closed-loop feedback — did last cycle's actions improve conditions?
            "previous_cycle_feedback": self._previous_cycle_feedback,

            # Real Syngenta KB + NASA MCP data (empty if adapters unavailable)
            "mcp_data": mcp_data,
        }

    def _get_all_desired_states(
        self, zones: dict[str, ZoneState],
    ) -> dict[str, DesiredState]:
        """Query state_store for each zone's desired state."""
        result: dict[str, DesiredState] = {}
        for zid in zones:
            ds = self._state_store.get_desired_state(zid)
            if ds is not None:
                result[zid] = ds
        return result

    def _get_resource_context(self) -> dict:
        """Return resource/energy/gas data if available, empty dict otherwise."""
        # Resource budgets are injected via state_store or dedicated ports
        # when available. For now, expose what we can safely query.
        return {}

    def _get_telemetry_trends(self, zones: dict[str, ZoneState]) -> dict:
        """Query last hour of readings per zone, return min/max/avg per sensor."""
        trends: dict[str, dict] = {}
        since = time.time() - 3600
        for zid in zones:
            readings = self._telemetry_store.query(zid, since, limit=200)
            if not readings:
                trends[zid] = {}
                continue
            # Group by sensor type and compute stats
            by_type: dict[str, list[float]] = {}
            for r in readings:
                st = r.sensor_type.value if hasattr(r.sensor_type, "value") else str(r.sensor_type)
                by_type.setdefault(st, []).append(r.value)
            zone_trends: dict[str, dict] = {}
            for st, values in by_type.items():
                zone_trends[st] = {
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "avg": round(sum(values) / len(values), 2),
                    "count": len(values),
                }
            trends[zid] = zone_trends
        return trends

    def _format_mcp_section(self, context: dict) -> str:
        """Format MCP data as a prompt section for specialists.  Empty string when no data."""
        mcp = context.get("mcp_data", {})
        if not mcp:
            return ""
        parts: list[str] = ["\n--- Real-time Knowledge Base Data (Syngenta + NASA MCP) ---"]
        if "syngenta_crop_data" in mcp:
            parts.append(f"Syngenta crop profiles: {json.dumps(mcp['syngenta_crop_data'], indent=2, default=str)}")
        if "syngenta_scenarios" in mcp:
            parts.append(f"Syngenta greenhouse scenarios: {json.dumps(mcp['syngenta_scenarios'], indent=2, default=str)}")
        if "nasa_mars_weather" in mcp:
            parts.append(f"NASA Mars weather: {json.dumps(mcp['nasa_mars_weather'], indent=2, default=str)}")
        if "nasa_solar_events" in mcp:
            parts.append(f"NASA solar events: {json.dumps(mcp['nasa_solar_events'], indent=2, default=str)}")
        parts.append("--- End Knowledge Base Data ---\n")
        return "\n".join(parts)

    def _run_specialist(self, agent_name: str, context: dict) -> list[AgentDecision]:
        """Run a single specialist and parse its response into decisions.

        Uses Strands Agent with real tool calling when available,
        falls back to plain model.reason() otherwise.
        """
        if self._use_strands:
            return self._run_specialist_strands(agent_name, context)

        # ── Fallback: plain model.reason() ──
        prompt_template = _SPECIALIST_PROMPTS.get(agent_name, "")
        mcp_section = self._format_mcp_section(context)
        prompt = (
            f"[{agent_name}] {prompt_template}\n\n"
            f"Current zones: {json.dumps(context['zones'], indent=2)}\n"
            f"Mars conditions: {json.dumps(context['mars_conditions'], indent=2)}\n"
            f"Deltas: {json.dumps(context['deltas'], indent=2)}\n"
            f"Nutritional status: {json.dumps(context['nutritional_status'], indent=2)}\n"
            f"{mcp_section}"
            f"Analyze and recommend."
        )

        try:
            response = self._model.reason(prompt, context)
        except Exception:
            logger.exception("Specialist %s failed", agent_name)
            return []

        if not response:
            return []

        return self._parse_response(agent_name, response)

    def _parse_response(self, agent_name: str, response: str) -> list[AgentDecision]:
        """Parse model response into AgentDecision objects."""
        decisions: list[AgentDecision] = []

        # Try to extract JSON array from the response
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            decisions.append(
                                AgentDecision(
                                    timestamp=time.time(),
                                    agent_name=agent_name,
                                    severity=Severity(item.get("severity", "info")),
                                    reasoning=item.get("reasoning", ""),
                                    action=item.get("action", ""),
                                    result="proposed",
                                    zone_id=item.get("zone_id", "global"),
                                    tier=Tier.CLOUD_MODEL,
                                )
                            )
                    return decisions
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: treat entire response as a single observation
        if response.strip():
            decisions.append(
                AgentDecision(
                    timestamp=time.time(),
                    agent_name=agent_name,
                    severity=Severity.INFO,
                    reasoning=response.strip()[:500],
                    action="observe",
                    result="proposed",
                    zone_id="global",
                    tier=Tier.CLOUD_MODEL,
                )
            )

        return decisions

    def _resolve_conflicts(self, proposals: list[AgentDecision]) -> list[AgentDecision]:
        """Resolve conflicts: severity first, then agent priority as tiebreaker.

        Priority hierarchy (12 agents):
          SENTINEL > FLORA > PATHFINDER > TERRA > DEMETER > ATMOS >
          AQUA > HELIOS > VITA > CHRONOS > HESTIA > ORACLE
        """
        def _priority(d: AgentDecision) -> tuple[int, int]:
            sev = _SEVERITY_RANK.get(d.severity, 99)
            pri = _AGENT_PRIORITY.get(d.agent_name, 99)
            return (sev, pri)

        return sorted(proposals, key=_priority)


# ── Parliament Hooks (for EventBus integration with Graph) ──────────────


class ParliamentHooks:
    """Hook provider that emits EventBus events during Graph execution.

    Intended for use with Strands Graph's hook system to provide
    real-time progress updates during parallel agent execution.

    Usage:
        hooks = ParliamentHooks(event_bus)
        # Pass to graph builder when hooks API is available
    """

    def __init__(self, event_bus=None):
        self._event_bus = event_bus

    def _emit(self, event_type: str, data: dict | None = None) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event_type, data)

    def on_node_start(self, node_name: str, **kwargs) -> None:
        """Emit agent_started event when a graph node begins execution."""
        agent_name = node_name
        zone_id = "global"
        if node_name.startswith("FLORA-"):
            agent_name = "FLORA"
            zone_id = node_name[len("FLORA-"):]
        self._emit("agent_started", {
            "agent_name": agent_name,
            "zone_id": zone_id,
            "source": "graph_hook",
        })

    def on_node_complete(self, node_name: str, result=None, **kwargs) -> None:
        """Emit agent_complete event when a graph node finishes execution."""
        agent_name = node_name
        zone_id = "global"
        if node_name.startswith("FLORA-"):
            agent_name = "FLORA"
            zone_id = node_name[len("FLORA-"):]
        result_text = str(result) if result else ""
        self._emit("agent_complete", {
            "agent_name": agent_name,
            "zone_id": zone_id,
            "result_text": result_text[:500],
            "source": "graph_hook",
        })
