"""E2E test: Full 12-agent parliament debate — Sol 247 Birthday Salad Crisis.

Scenario:
  - Zone alpha: Tomatoes at 28°C (high end), humidity 50% (LOW), water 45mm
  - Zone beta: Lettuce at 21°C (good), humidity 62%, water 70mm
  - Zone gamma: Herbs (basil) at 24°C, humidity 58%, water 55mm
  - Mars: Sol 247, dust_opacity 0.4, no storm, no radiation
  - Crew: Chen's birthday in 13 sols, vitamin C at 73% target
  - Water budget: 62% remaining, mission day 247 of 450

All 12 specialists + 3 FLORA instances (one per zone) debate via REAL Bedrock.
This test takes 30-60s — it hits Bedrock 14 times (11 specialists + 3 FLORA).
"""

import json
import time

import pytest

from eden.adapters.bedrock_adapter import BedrockAdapter
from eden.application.agent import AgentTeam, _SPECIALISTS
from eden.domain.models import (
    AgentDecision,
    CrewMember,
    CropProfile,
    DesiredState,
    MarsConditions,
    SensorReading,
    SensorType,
    Severity,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── In-memory port implementations ──────────────────────────────────────


class InMemorySensor:
    """SensorPort — returns pre-loaded zone states."""

    def __init__(self, zones: dict[str, ZoneState]) -> None:
        self._zones = zones

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def subscribe(self, callback) -> None:
        pass


class InMemoryActuator:
    """ActuatorPort — records commands sent."""

    def __init__(self) -> None:
        self.commands: list = []

    def send_command(self, command) -> bool:
        self.commands.append(command)
        return True


class InMemoryStateStore:
    """StateStorePort — stores zone + desired states in dicts."""

    def __init__(self) -> None:
        self._zones: dict[str, ZoneState] = {}
        self._desired: dict[str, DesiredState] = {}

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self._zones[zone_id] = state

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        return self._desired.get(zone_id)

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self._desired[zone_id] = state


class InMemoryTelemetry:
    """TelemetryStorePort — stores readings in a list."""

    def __init__(self) -> None:
        self._readings: list[SensorReading] = []

    def append(self, reading: SensorReading) -> None:
        self._readings.append(reading)

    def query(self, zone_id: str, since: float, limit: int = 100) -> list[SensorReading]:
        results = [
            r for r in self._readings
            if r.zone_id == zone_id and r.timestamp >= since
        ]
        return results[:limit]


class InMemoryAgentLog:
    """AgentLogPort — stores decisions in a list."""

    def __init__(self) -> None:
        self.decisions: list[AgentDecision] = []

    def append(self, decision: AgentDecision) -> None:
        self.decisions.append(decision)

    def query(self, since: float = 0.0, limit: int = 50) -> list[AgentDecision]:
        results = [d for d in self.decisions if d.timestamp >= since]
        return results[:limit]


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def bedrock():
    """Real Bedrock adapter — no mocks."""
    adapter = BedrockAdapter(
        model_id="us.anthropic.claude-sonnet-4-6",
        region="us-west-2",
    )
    if not adapter.is_available():
        pytest.skip("Bedrock not reachable — skipping e2e")
    return adapter


@pytest.fixture
def scenario():
    """Sol 247 Birthday Salad Crisis — full setup."""
    now = time.time()

    # ── Zone states ──────────────────────────────────────────────────
    zones = {
        "alpha": ZoneState(
            zone_id="alpha",
            temperature=28.0,
            humidity=50.0,
            pressure=700.0,
            light=650.0,
            water_level=45.0,
            fire_detected=False,
            last_updated=now,
            is_alive=True,
            source="simulation",
        ),
        "beta": ZoneState(
            zone_id="beta",
            temperature=21.0,
            humidity=62.0,
            pressure=700.0,
            light=550.0,
            water_level=70.0,
            fire_detected=False,
            last_updated=now,
            is_alive=True,
            source="simulation",
        ),
        "gamma": ZoneState(
            zone_id="gamma",
            temperature=24.0,
            humidity=58.0,
            pressure=700.0,
            light=600.0,
            water_level=55.0,
            fire_detected=False,
            last_updated=now,
            is_alive=True,
            source="simulation",
        ),
    }

    # ── Mars conditions ──────────────────────────────────────────────
    mars = MarsConditions(
        exterior_temp=-58.0,
        dome_temp=23.0,
        pressure_hpa=700.0,
        solar_irradiance=480.0,
        dust_opacity=0.4,
        sol=247,
        storm_active=False,
        radiation_alert=False,
    )

    # ── Deltas (alpha humidity below target) ─────────────────────────
    deltas = {
        "alpha": {
            "temperature": "+1.5°C in last 2 hours (approaching upper limit)",
            "humidity": "-12% in last 3 hours (BELOW target range of 55-75%)",
            "water_level": "-5mm in last hour (elevated consumption)",
        },
        "beta": {
            "temperature": "stable",
            "humidity": "stable",
            "water_level": "stable",
        },
        "gamma": {
            "temperature": "stable",
            "humidity": "-3% in last hour (trending down)",
            "water_level": "stable",
        },
    }

    # ── Desired states ───────────────────────────────────────────────
    desired_states = {
        "alpha": DesiredState(
            zone_id="alpha",
            temp_min=20.0, temp_max=28.0,
            humidity_min=55.0, humidity_max=75.0,
            light_hours=14.0,
            soil_moisture_min=40.0, soil_moisture_max=70.0,
            water_budget_liters_per_day=8.0,
        ),
        "beta": DesiredState(
            zone_id="beta",
            temp_min=15.0, temp_max=22.0,
            humidity_min=50.0, humidity_max=70.0,
            light_hours=12.0,
            soil_moisture_min=50.0, soil_moisture_max=80.0,
            water_budget_liters_per_day=6.0,
        ),
        "gamma": DesiredState(
            zone_id="gamma",
            temp_min=18.0, temp_max=27.0,
            humidity_min=50.0, humidity_max=65.0,
            light_hours=14.0,
            soil_moisture_min=35.0, soil_moisture_max=60.0,
            water_budget_liters_per_day=4.0,
        ),
    }

    # ── Crop profiles ────────────────────────────────────────────────
    crops = [
        CropProfile("Tomatoes", "alpha", 180.0, 9.0, 90, 4.5, 20.0, 28.0, 55.0, 75.0),
        CropProfile("Lettuce", "beta", 150.0, 13.0, 45, 3.0, 15.0, 22.0, 50.0, 70.0),
        CropProfile("Basil", "gamma", 230.0, 32.0, 60, 2.0, 18.0, 27.0, 50.0, 65.0),
    ]

    # ── Crew + nutrition ─────────────────────────────────────────────
    crew = [
        CrewMember("Cmdr. Chen", 2500.0, 60.0),
        CrewMember("Dr. Okafor", 2500.0, 60.0),
        CrewMember("Eng. Petrov", 2500.0, 60.0),
        CrewMember("Sci. Tanaka", 2500.0, 60.0),
    ]
    nutrition = NutritionTracker(crew, crops, mission_days=450)
    nutrition.current_sol = 247

    # Simulate partial intake history (vitamin C at 73% → kcal ratio ~0.73)
    for _ in range(30):
        for m in crew:
            m.current_kcal_intake = m.daily_kcal_target * 0.73
            m.current_protein_intake = m.daily_protein_target * 0.75
        nutrition.advance_day()
    nutrition.current_sol = 247  # fix sol after advance_day increments

    # ── Telemetry (recent readings showing the humidity drop in alpha) ──
    telemetry = InMemoryTelemetry()
    for i in range(6):
        ts = now - (6 - i) * 600  # every 10 min for the last hour
        # Alpha humidity dropping
        telemetry.append(SensorReading(
            "alpha", SensorType.HUMIDITY, 62.0 - i * 2.0, "%", ts, "sim",
        ))
        telemetry.append(SensorReading(
            "alpha", SensorType.TEMPERATURE, 26.5 + i * 0.25, "°C", ts, "sim",
        ))
        # Beta and gamma stable
        telemetry.append(SensorReading(
            "beta", SensorType.HUMIDITY, 62.0 + (i % 2) * 0.5, "%", ts, "sim",
        ))
        telemetry.append(SensorReading(
            "gamma", SensorType.HUMIDITY, 59.0 - i * 0.5, "%", ts, "sim",
        ))

    return {
        "zones": zones,
        "mars": mars,
        "deltas": deltas,
        "desired_states": desired_states,
        "crops": crops,
        "nutrition": nutrition,
        "telemetry": telemetry,
    }


# ── The Test ─────────────────────────────────────────────────────────────


def test_parliament_debate_birthday_salad(bedrock, scenario):
    """Full parliament debate: 12 specialists + 3 FLORA instances analyze Sol 247."""

    # ── Wire up all ports ────────────────────────────────────────────
    sensor = InMemorySensor(scenario["zones"])
    actuator = InMemoryActuator()
    state_store = InMemoryStateStore()
    agent_log = InMemoryAgentLog()

    for zone_id, desired in scenario["desired_states"].items():
        state_store.put_desired_state(zone_id, desired)
    for zone_id, zone in scenario["zones"].items():
        state_store.put_zone_state(zone_id, zone)

    zone_crops = {"alpha": "Tomatoes", "beta": "Lettuce", "gamma": "Basil"}

    team = AgentTeam(
        model=bedrock,
        sensor=sensor,
        actuator=actuator,
        state_store=state_store,
        telemetry_store=scenario["telemetry"],
        agent_log=agent_log,
        nutrition=scenario["nutrition"],
        zone_crops=zone_crops,
    )

    # ── Run the parliament ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  SOL 247 — THE BIRTHDAY SALAD CRISIS — PARLIAMENT DEBATE")
    print("=" * 80)
    print(f"  Zones: alpha (Tomatoes 28°C/50%RH), beta (Lettuce 21°C/62%RH), gamma (Basil 24°C/58%RH)")
    print(f"  Mars: Sol 247, dust 0.4, no storm")
    print(f"  Crisis: Alpha humidity below target (50% vs 55-75% range), birthday in 13 sols")
    print(f"  Water budget: 62% remaining | Vitamin C: 73% target")
    print("=" * 80 + "\n")

    t0 = time.time()
    decisions = team.analyze(
        zones=scenario["zones"],
        mars=scenario["mars"],
        deltas=scenario["deltas"],
    )
    elapsed = time.time() - t0

    # ── Print the full debate transcript ─────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"  PARLIAMENT DEBATE RESULTS — {len(decisions)} decisions in {elapsed:.1f}s")
    print(f"{'=' * 80}\n")

    agents_that_spoke = set()
    for i, d in enumerate(decisions):
        agents_that_spoke.add(d.agent_name)
        sev_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵",
        }.get(d.severity.value, "⚪")

        print(f"  [{i+1:02d}] {sev_icon} {d.agent_name:<12} | {d.severity.value:<8} | zone: {d.zone_id}")
        print(f"       Reasoning: {d.reasoning[:200]}")
        if len(d.reasoning) > 200:
            print(f"                  ...{d.reasoning[200:400]}")
        print(f"       Action: {d.action[:150]}")
        print()

    print(f"{'=' * 80}")
    print(f"  AGENTS THAT SPOKE: {sorted(agents_that_spoke)}")
    print(f"  TOTAL DECISIONS: {len(decisions)}")
    print(f"  TIME: {elapsed:.1f}s ({len(decisions)} decisions, {elapsed/max(len(decisions),1):.1f}s avg)")
    print(f"{'=' * 80}\n")

    # ── Assertions ───────────────────────────────────────────────────

    # 1. We got decisions
    assert len(decisions) > 0, "Parliament returned no decisions"

    # 2. Multiple DIFFERENT agents contributed
    assert len(agents_that_spoke) >= 4, (
        f"Expected at least 4 different agents, got {len(agents_that_spoke)}: {agents_that_spoke}"
    )
    print(f"  ✓ {len(agents_that_spoke)} different agents contributed decisions")

    # 3. At least some agents reference specific zone data
    zone_refs = sum(
        1 for d in decisions
        if any(z in d.reasoning.lower() for z in ("alpha", "beta", "gamma", "tomato", "lettuce", "basil"))
    )
    assert zone_refs >= 2, (
        f"Expected at least 2 decisions referencing zone data, got {zone_refs}"
    )
    print(f"  ✓ {zone_refs} decisions reference specific zone/crop data")

    # 4. FLORA speaks in first person ("I feel", "I'm", "I need", "my")
    flora_decisions = [d for d in decisions if d.agent_name == "FLORA"]
    if flora_decisions:
        flora_text = " ".join(d.reasoning.lower() for d in flora_decisions)
        first_person = any(
            phrase in flora_text
            for phrase in ("i feel", "i'm", "i am", "i need", "my ", "me ", "i can", "i want", "i sense", "i'm thirsty", "my roots", "my leaves")
        )
        assert first_person, (
            f"FLORA should speak in first person but didn't. Sample: {flora_text[:300]}"
        )
        print(f"  ✓ FLORA speaks in first person ({len(flora_decisions)} FLORA decisions)")
    else:
        print("  ⚠ No FLORA decisions (FLORA returned empty — not a hard failure)")

    # 5. Decisions are properly structured
    for d in decisions:
        assert isinstance(d, AgentDecision), f"Decision is not AgentDecision: {type(d)}"
        assert d.severity in Severity, f"Invalid severity: {d.severity}"
        assert d.agent_name, "Decision missing agent_name"
        assert d.reasoning, "Decision missing reasoning"
        assert d.zone_id, "Decision missing zone_id"
    print(f"  ✓ All {len(decisions)} decisions properly structured")

    # 6. Priority resolution: sorted by (severity rank, agent priority)
    severity_rank = {
        Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2,
        Severity.LOW: 3, Severity.INFO: 4,
    }
    for i in range(len(decisions) - 1):
        a, b = decisions[i], decisions[i + 1]
        a_rank = severity_rank.get(a.severity, 99)
        b_rank = severity_rank.get(b.severity, 99)
        assert a_rank <= b_rank, (
            f"Decisions not sorted by severity: [{i}] {a.agent_name}/{a.severity.value} "
            f"should be before [{i+1}] {b.agent_name}/{b.severity.value}"
        )
    print(f"  ✓ Priority resolution correct (higher severity first)")

    # 7. Reasoning was logged to agent_log
    logged = agent_log.decisions
    assert len(logged) >= len(decisions), (
        f"Expected at least {len(decisions)} logged, got {len(logged)}"
    )
    print(f"  ✓ {len(logged)} decisions logged to agent log")

    print(f"\n  🎉 PARLIAMENT DEBATE PASSED — {len(decisions)} decisions from {len(agents_that_spoke)} agents in {elapsed:.1f}s")
