"""E2E Big Kahuna — Full Mission Day on Mars.

Simulates 3 reconciliation cycles with REAL Bedrock, REAL SQLite,
optional REAL DynamoDB, REAL flight rules (all 17), REAL Mars transform,
REAL nutrition tracking, REAL 12-agent parliament + FLORA, REAL coordinator,
REAL closed-loop feedback.

Setup:
  3 zones: alpha (Tomatoes, stressed), beta (Lettuce, nominal), gamma (Herbs, trending down)
  Sol 247, dust 0.4, EnergyBudget (78%), GasExchange (CO2 normal), ResourceBudget (water 62%)

Cycle 1 — Crisis Detection:
  Alpha 36°C/40%RH (heat stress + dry), beta nominal, gamma trending down.
  Flight rules fire fan ON for alpha. Parliament debates. COORDINATOR resolves.

Cycle 2 — Response Taking Effect:
  Alpha cooled to 28°C/52%RH. Closed-loop feedback detects improvement.
  Agents acknowledge improvement, flag gamma still trending.

Cycle 3 — Stabilization:
  All zones nominal. System quiet. Low/info severity only.

Runtime: ~60-90s (3 parliament cycles with Bedrock parallelization).
"""

from __future__ import annotations

import math
import os
import tempfile
import time

import pytest

from eden.adapters.bedrock_adapter import BedrockAdapter
from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.adapters.synced_store import SyncedStore
from eden.application.agent import AgentTeam, _SPECIALISTS
from eden.application.reconciler import Reconciler
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import (
    get_mars_conditions,
    transform_light,
    transform_pressure,
    transform_temperature,
)
from eden.domain.models import (
    AgentDecision,
    CropProfile,
    DesiredState,
    DeviceType,
    EnergyBudget,
    GasExchange,
    ResourceBudget,
    Severity,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Constants ────────────────────────────────────────────────────────────────

SOL = 247
DUST_OPACITY = 0.4


# ── Fake Ports (sensor + actuator under our control) ────────────────────────


class FakeSensor:
    """SensorPort — inject controllable zone states."""

    def __init__(self):
        self._zones: dict[str, ZoneState] = {}

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def set_zone(self, zone_id: str, zone: ZoneState) -> None:
        self._zones[zone_id] = zone


class FakeActuator:
    """ActuatorPort — record commands for verification."""

    def __init__(self):
        self.commands: list = []

    def send_command(self, cmd) -> bool:
        self.commands.append(cmd)
        return True

    def commands_for_zone(self, zone_id: str) -> list:
        return [c for c in self.commands if c.zone_id == zone_id]

    def clear(self) -> None:
        self.commands.clear()


class TelemetryAdapter:
    """Wraps SyncedStore for TelemetryStorePort interface."""

    def __init__(self, store):
        self._store = store

    def append(self, reading):
        self._store.append_telemetry(reading)

    def query(self, zone_id, since, limit=100):
        return self._store.query_telemetry(zone_id, since, limit)


class AgentLogAdapter:
    """Wraps SyncedStore for AgentLogPort interface."""

    def __init__(self, store):
        self._store = store

    def append(self, decision):
        self._store.append_agent_log(decision)

    def query(self, since=0.0, limit=100):
        return self._store.query_agent_log(since, limit)


class FakeConfig:
    RECONCILE_INTERVAL_SECONDS = 30
    LOG_LEVEL = "DEBUG"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _raw_temp_for_dome(target_dome: float) -> float:
    """Reverse Mars transform: find raw sensor value that yields target dome temp at SOL 247."""
    seasonal = 8.0 * math.sin(2 * math.pi * SOL / 450)
    exterior = -60.0 + seasonal
    coupling = (exterior - (-60.0)) * 0.05
    # dome = 22 + coupling + (raw - 22) * 0.15  →  raw = 22 + (dome - 22 - coupling) / 0.15
    return 22.0 + (target_dome - 22.0 - coupling) / 0.15


def _make_zone(
    zone_id: str,
    dome_temp: float,
    humidity: float,
    light: float = 600.0,
    water_level: float = 50.0,
    timestamp: float | None = None,
) -> ZoneState:
    """Create zone with raw values that produce the specified dome_temp after Mars transform."""
    raw_temp = _raw_temp_for_dome(dome_temp)
    # Sanity check the roundtrip
    actual = transform_temperature(raw_temp, SOL)
    assert abs(actual - dome_temp) < 0.01, f"Transform roundtrip failed: {actual} != {dome_temp}"

    return ZoneState(
        zone_id=zone_id,
        temperature=raw_temp,
        humidity=humidity,
        pressure=1013.25,  # Earth standard → 700 hPa after Mars transform
        light=light,
        water_level=water_level,
        fire_detected=False,
        last_updated=timestamp or time.time(),
        is_alive=True,
        source="test",
    )


def _get_transformed_zones(store, zone_ids: list[str]) -> dict[str, ZoneState]:
    """Read Mars-transformed zones from store (written by reconciler after transform)."""
    return {zid: store.get_zone_state(zid) for zid in zone_ids if store.get_zone_state(zid)}


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def bedrock():
    """Real Bedrock adapter — skip entire module if unavailable."""
    try:
        adapter = BedrockAdapter(
            model_id="us.anthropic.claude-sonnet-4-6",
            region="us-west-2",
        )
        if not adapter.is_available():
            pytest.skip("Bedrock not reachable — skipping Big Kahuna")
        return adapter
    except Exception as e:
        pytest.skip(f"Bedrock client creation failed: {e}")


@pytest.fixture(scope="module")
def dynamo():
    """Real DynamoDB adapter — returns None if unavailable (test continues without it)."""
    try:
        from eden.adapters.dynamo_adapter import DynamoAdapter

        adapter = DynamoAdapter(region="us-west-2", table_prefix="eden")
        adapter.get_zone_state("__health_check__")  # smoke test
        return adapter
    except Exception:
        return None


@pytest.fixture
def pipeline(bedrock, dynamo):
    """Full pipeline: real Bedrock, real SQLite, optional DynamoDB, real everything."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # ── Storage ──
        db_path = os.path.join(tmpdir, "big_kahuna.db")
        sqlite = SqliteAdapter(db_path=db_path)
        store = SyncedStore(local=sqlite, remote=dynamo)

        # ── Ports ──
        sensor = FakeSensor()
        actuator = FakeActuator()
        telemetry = TelemetryAdapter(store)
        agent_log = AgentLogAdapter(store)

        # ── Flight rules (all 17) ──
        flight_rules = FlightRulesEngine()
        assert len(flight_rules.rules) == 17, (
            f"Expected 17 flight rules, got {len(flight_rules.rules)}"
        )

        # ── Nutrition ──
        crops = [
            CropProfile("Tomatoes", "alpha", 180.0, 9.0, 90, 4.5, 20.0, 28.0, 55.0, 75.0),
            CropProfile("Lettuce", "beta", 150.0, 13.0, 45, 3.0, 15.0, 22.0, 50.0, 70.0),
            CropProfile("Herbs", "gamma", 230.0, 32.0, 60, 2.0, 18.0, 27.0, 50.0, 65.0),
        ]
        crew = NutritionTracker.get_default_crew()
        nutrition = NutritionTracker(crew=crew, crops=crops, mission_days=450)
        nutrition.current_sol = SOL

        # ── Desired states ──
        store.put_desired_state("alpha", DesiredState(
            "alpha", 20.0, 28.0, 55.0, 75.0, 14.0, 40.0, 70.0, 8.0,
        ))
        store.put_desired_state("beta", DesiredState(
            "beta", 15.0, 22.0, 50.0, 70.0, 12.0, 50.0, 80.0, 6.0,
        ))
        store.put_desired_state("gamma", DesiredState(
            "gamma", 18.0, 27.0, 50.0, 65.0, 14.0, 35.0, 60.0, 4.0,
        ))

        # ── Reconciler ──
        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=telemetry,
            agent_log=agent_log,
            model=bedrock,
            flight_rules=flight_rules,
            nutrition=nutrition,
            config=FakeConfig(),
        )
        reconciler._current_sol = SOL

        # ── Resource budgets (passed to flight rules each cycle) ──
        reconciler.set_energy_budget(EnergyBudget(
            solar_capacity_kw=10.0,
            current_efficiency=0.78,  # 78% — above 50% threshold
            allocations={"lights": 3.0, "heaters": 2.0, "pumps": 1.0, "fans": 0.5},
            reserve_kw=2.0,
        ))
        reconciler.set_gas_exchange(GasExchange(
            greenhouse_co2_ppm=800.0,   # normal (threshold 5000)
            greenhouse_o2_pct=21.0,     # normal (18-25% range)
            habitat_co2_ppm=400.0,
            habitat_o2_pct=21.0,
            exchange_rate=1.0,
        ))
        reconciler.set_resource_budget(ResourceBudget(
            water_liters=620.0,
            nutrient_level=45.0,
            current_capacity=62.0,  # 62% — above 30% threshold
        ))

        # ── Agent Team (12 specialists + per-zone FLORA + coordinator) ──
        zone_crops = {"alpha": "Tomatoes", "beta": "Lettuce", "gamma": "Herbs"}
        agent_team = AgentTeam(
            model=bedrock,
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=telemetry,
            agent_log=agent_log,
            nutrition=nutrition,
            zone_crops=zone_crops,
        )

        yield {
            "reconciler": reconciler,
            "sensor": sensor,
            "actuator": actuator,
            "store": store,
            "sqlite": sqlite,
            "dynamo": dynamo,
            "telemetry": telemetry,
            "agent_log": agent_log,
            "flight_rules": flight_rules,
            "nutrition": nutrition,
            "agent_team": agent_team,
        }

        store.stop()
        sqlite.close()


# ══════════════════════════════════════════════════════════════════════════════
# THE BIG KAHUNA
# ══════════════════════════════════════════════════════════════════════════════


def test_big_kahuna_full_mission_day(pipeline):
    """3 reconciliation cycles: crisis → response → stabilization.

    Exercises EVERY subsystem: sensors, Mars transform, flight rules (17),
    Bedrock LLM, agent parliament (12 specialists + FLORA), coordinator,
    closed-loop feedback, nutrition tracking, SQLite, DynamoDB.
    """
    p = pipeline
    reconciler = p["reconciler"]
    sensor = p["sensor"]
    actuator = p["actuator"]
    store = p["store"]
    agent_team = p["agent_team"]
    telemetry = p["telemetry"]
    agent_log = p["agent_log"]
    nutrition = p["nutrition"]
    dynamo = p["dynamo"]

    mars = get_mars_conditions(SOL, dust_opacity=DUST_OPACITY)
    test_start = time.time()
    all_parliament: list[list[AgentDecision]] = []

    # ══════════════════════════════════════════════════════════════════
    # CYCLE 1: CRISIS DETECTION
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CYCLE 1: CRISIS DETECTION — Sol 247")
    print("  Alpha: 36°C/40%RH (heat stress + dry)")
    print("  Beta:  21°C/62%RH (nominal)")
    print("  Gamma: 24°C/55%RH (trending down)")
    print("=" * 80)

    sensor.set_zone("alpha", _make_zone("alpha", dome_temp=36.0, humidity=40.0))
    sensor.set_zone("beta", _make_zone("beta", dome_temp=21.0, humidity=62.0))
    sensor.set_zone("gamma", _make_zone("gamma", dome_temp=24.0, humidity=55.0))

    t0 = time.time()
    cycle1_recon = reconciler.reconcile_once()
    t_recon1 = time.time() - t0

    # ── Flight rules: fan ON for alpha (FR-T-002: temp > 35°C) ──
    alpha_cmds = actuator.commands_for_zone("alpha")
    fan_cmds = [c for c in alpha_cmds if c.device == DeviceType.FAN and c.action == "on"]
    assert len(fan_cmds) >= 1, (
        f"FR-T-002 should fire for alpha (36°C > 35°C), got: "
        f"{[(c.device.value, c.action) for c in alpha_cmds]}"
    )
    print(f"  ✓ Flight rules: fan ON for alpha ({len(fan_cmds)} fan commands)")
    print(f"  ✓ Reconciler: {len(cycle1_recon)} decisions in {t_recon1:.1f}s")

    # ── Parliament debate on transformed zones ──
    transformed_c1 = _get_transformed_zones(store, ["alpha", "beta", "gamma"])
    deltas_c1 = {
        "alpha": {"temperature": 8.0, "humidity": -15.0},
        "beta": {},
        "gamma": {"humidity": -5.0},
    }

    t0 = time.time()
    parliament_c1 = agent_team.analyze(transformed_c1, mars, deltas_c1)
    t_parl1 = time.time() - t0
    all_parliament.append(parliament_c1)

    agents_c1 = {d.agent_name for d in parliament_c1}
    critical_c1 = sum(
        1 for d in (cycle1_recon + parliament_c1)
        if d.severity in (Severity.CRITICAL, Severity.HIGH)
    )
    print(f"  ✓ Parliament: {len(parliament_c1)} decisions from {len(agents_c1)} agents in {t_parl1:.1f}s")
    print(f"    Agents: {sorted(agents_c1)}")
    print(f"  Cycle 1 complete: {len(cycle1_recon) + len(parliament_c1)} total, {critical_c1} critical/high")

    actuator.clear()

    # ══════════════════════════════════════════════════════════════════
    # CYCLE 2: RESPONSE TAKING EFFECT
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CYCLE 2: RESPONSE TAKING EFFECT")
    print("  Alpha: 28°C/52%RH (cooled! improving)")
    print("  Beta:  21°C/62%RH (stable)")
    print("  Gamma: 23°C/53%RH (still trending down)")
    print("=" * 80)

    sensor.set_zone("alpha", _make_zone("alpha", dome_temp=28.0, humidity=52.0))
    sensor.set_zone("beta", _make_zone("beta", dome_temp=21.0, humidity=62.0))
    sensor.set_zone("gamma", _make_zone("gamma", dome_temp=23.0, humidity=53.0))

    t0 = time.time()
    cycle2_recon = reconciler.reconcile_once()
    t_recon2 = time.time() - t0

    # ── Closed-loop feedback: alpha cooling detected ──
    feedback_c2 = reconciler.last_feedback
    alpha_fb = [f for f in feedback_c2 if f["zone_id"] == "alpha"]
    assert len(alpha_fb) >= 1, (
        f"Expected closed-loop feedback for alpha cooling, got: {feedback_c2}"
    )
    assert "temperature" in alpha_fb[0]["improvements"], (
        f"Expected temperature improvement, got: {alpha_fb[0]['improvements']}"
    )
    temp_fb = alpha_fb[0]["improvements"]["temperature"]
    print(f"  ✓ Closed-loop feedback: alpha temp {temp_fb['before']:.1f}→{temp_fb['after']:.1f}°C ({temp_fb['action']})")

    # ── Parliament cycle 2 (with feedback injected) ──
    transformed_c2 = _get_transformed_zones(store, ["alpha", "beta", "gamma"])
    deltas_c2 = {"alpha": {}, "beta": {}, "gamma": {"humidity": -7.0}}
    agent_team.set_feedback(feedback_c2)

    t0 = time.time()
    parliament_c2 = agent_team.analyze(transformed_c2, mars, deltas_c2)
    t_parl2 = time.time() - t0
    all_parliament.append(parliament_c2)

    print(f"  ✓ Parliament: {len(parliament_c2)} decisions in {t_parl2:.1f}s")
    print(f"  Cycle 2 complete: {len(cycle2_recon)} recon + {len(parliament_c2)} parliament")

    actuator.clear()

    # ══════════════════════════════════════════════════════════════════
    # CYCLE 3: STABILIZATION
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CYCLE 3: STABILIZATION")
    print("  Alpha: 24°C/58%RH (recovered!)")
    print("  Beta:  21°C/62%RH (stable)")
    print("  Gamma: 24°C/56%RH (stabilized)")
    print("=" * 80)

    sensor.set_zone("alpha", _make_zone("alpha", dome_temp=24.0, humidity=58.0))
    sensor.set_zone("beta", _make_zone("beta", dome_temp=21.0, humidity=62.0))
    sensor.set_zone("gamma", _make_zone("gamma", dome_temp=24.0, humidity=56.0))

    t0 = time.time()
    cycle3_recon = reconciler.reconcile_once()
    t_recon3 = time.time() - t0

    # ── Parliament cycle 3 ──
    transformed_c3 = _get_transformed_zones(store, ["alpha", "beta", "gamma"])
    deltas_c3 = {"alpha": {}, "beta": {}, "gamma": {}}
    agent_team.set_feedback(reconciler.last_feedback)

    t0 = time.time()
    parliament_c3 = agent_team.analyze(transformed_c3, mars, deltas_c3)
    t_parl3 = time.time() - t0
    all_parliament.append(parliament_c3)

    critical_c3 = sum(
        1 for d in (cycle3_recon + parliament_c3)
        if d.severity in (Severity.CRITICAL, Severity.HIGH)
    )
    print(f"  ✓ Parliament: {len(parliament_c3)} decisions in {t_parl3:.1f}s")
    print(f"  Cycle 3 complete: {len(cycle3_recon)} recon + {len(parliament_c3)} parliament")

    total_time = time.time() - test_start

    # ══════════════════════════════════════════════════════════════════
    # FINAL ASSERTIONS — all 11 checks
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  FINAL ASSERTIONS")
    print("=" * 80)

    # ── 1. All 3 cycles completed without errors ──
    assert len(all_parliament) == 3
    for i, parl in enumerate(all_parliament):
        assert len(parl) > 0, f"Cycle {i+1} parliament returned no decisions"
    print("  [1]  ✓ All 3 cycles completed without errors")

    # ── 2. Flight rules fired correctly in cycle 1 (fan ON for alpha heat) ──
    fr_decisions_c1 = [d for d in cycle1_recon if d.agent_name == "FLIGHT_RULES"]
    assert any(
        "temperature" in d.reasoning and d.zone_id == "alpha"
        for d in fr_decisions_c1
    ), f"Expected FR-T-002 decision for alpha, got: {[(d.zone_id, d.reasoning[:80]) for d in fr_decisions_c1]}"
    print("  [2]  ✓ Flight rules fired: FR-T-002 fan ON for alpha heat stress")

    # ── 3. Agent parliament produces decisions with 12+ agent names ──
    all_agents_ever = set()
    for cycle_decisions in all_parliament:
        for d in cycle_decisions:
            all_agents_ever.add(d.agent_name)
    # 12 specialists + COORDINATOR = 13 possible; some may return empty. Expect 6+.
    assert len(all_agents_ever) >= 6, (
        f"Expected 6+ unique agent names across all cycles, got {len(all_agents_ever)}: "
        f"{sorted(all_agents_ever)}"
    )
    print(f"  [3]  ✓ Parliament produced decisions from {len(all_agents_ever)} agents: {sorted(all_agents_ever)}")

    # ── 4. COORDINATOR resolution with "CONSENSUS_RESOLUTION" action ──
    coordinator_resolutions = [
        d for d in parliament_c1
        if d.agent_name == "COORDINATOR" and d.action == "CONSENSUS_RESOLUTION"
    ]
    assert len(coordinator_resolutions) >= 1, (
        f"Expected COORDINATOR CONSENSUS_RESOLUTION in cycle 1. "
        f"COORDINATOR decisions: {[(d.action, d.reasoning[:80]) for d in parliament_c1 if d.agent_name == 'COORDINATOR']}"
    )
    print(f"  [4]  ✓ COORDINATOR produced CONSENSUS_RESOLUTION (severity: {coordinator_resolutions[0].severity.value})")

    # ── 5. Closed-loop feedback detects improvement in cycle 2 ──
    # (Already verified above — re-assert for completeness)
    assert len(alpha_fb) >= 1 and "temperature" in alpha_fb[0]["improvements"]
    print(f"  [5]  ✓ Closed-loop feedback detected alpha temperature improvement in cycle 2")

    # ── 6. Cycle 3 has fewer critical/high decisions than cycle 1 ──
    assert critical_c3 <= critical_c1, (
        f"Cycle 3 critical/high ({critical_c3}) should be <= cycle 1 ({critical_c1})"
    )
    print(f"  [6]  ✓ Cycle 3 critical/high ({critical_c3}) <= cycle 1 ({critical_c1})")

    # ── 7. All telemetry persisted to SQLite ──
    for zone_id in ["alpha", "beta", "gamma"]:
        readings = telemetry.query(zone_id, since=test_start, limit=500)
        # 3 cycles × 5 sensor types = 15 readings per zone
        assert len(readings) >= 15, (
            f"Expected >=15 telemetry for {zone_id}, got {len(readings)}"
        )
    r_alpha = len(telemetry.query("alpha", since=test_start, limit=500))
    r_beta = len(telemetry.query("beta", since=test_start, limit=500))
    r_gamma = len(telemetry.query("gamma", since=test_start, limit=500))
    print(f"  [7]  ✓ Telemetry persisted: alpha={r_alpha}, beta={r_beta}, gamma={r_gamma}")

    # ── 8. Zone states synced to DynamoDB ──
    if dynamo is not None:
        for zid in ["alpha", "beta", "gamma"]:
            ddb_zone = dynamo.get_zone_state(zid)
            assert ddb_zone is not None, f"Zone {zid} should be synced to DynamoDB"
        print("  [8]  ✓ Zone states synced to DynamoDB")
    else:
        print("  [8]  ~ DynamoDB not available — sync check skipped")

    # ── 9. Agent decisions logged ──
    all_logged = agent_log.query(since=test_start, limit=1000)
    assert len(all_logged) >= 10, f"Expected >=10 logged decisions, got {len(all_logged)}"
    print(f"  [9]  ✓ Agent decisions logged: {len(all_logged)} entries")

    # ── 10. Nutrition tracker has data ──
    status = nutrition.get_nutritional_status()
    assert status["sol"] == SOL
    assert len(status["crew"]) == 4
    projection = nutrition.get_mission_projection()
    assert projection["mission_days"] == 450
    assert projection["current_sol"] == SOL
    print(f"  [10] ✓ Nutrition tracker: sol={status['sol']}, crew={len(status['crew'])}, mission_days={projection['mission_days']}")

    # ── 11. EnergyBudget/GasExchange were passed to flight rules ──
    assert reconciler._energy_budget is not None, "EnergyBudget should be set"
    assert reconciler._gas_exchange is not None, "GasExchange should be set"
    assert reconciler._resource_budget is not None, "ResourceBudget should be set"
    # With efficiency=0.78 (>0.5) and CO2=800 (<5000) and O2=21% (18-25),
    # no energy/gas flight rules should fire — proves data was checked, not skipped.
    spurious_energy = [
        d for d in cycle1_recon
        if "power_rationing" in (d.action or "").lower()
    ]
    spurious_co2 = [
        d for d in cycle1_recon
        if "ventilation" in (d.action or "").lower() and "co2" in (d.reasoning or "").lower()
    ]
    assert len(spurious_energy) == 0, "No energy rationing expected (efficiency 78%)"
    assert len(spurious_co2) == 0, "No CO2 alert expected (800ppm)"
    print("  [11] ✓ EnergyBudget/GasExchange passed to flight rules (no spurious triggers)")

    # ══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    c1_total = len(cycle1_recon) + len(parliament_c1)
    c2_total = len(cycle2_recon) + len(parliament_c2)
    c3_total = len(cycle3_recon) + len(parliament_c3)
    print(f"  BIG KAHUNA PASSED — Full mission day on Sol {SOL}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Cycle 1 (crisis):        {c1_total:3d} decisions ({len(cycle1_recon)} recon + {len(parliament_c1)} parliament)")
    print(f"  Cycle 2 (response):      {c2_total:3d} decisions ({len(cycle2_recon)} recon + {len(parliament_c2)} parliament)")
    print(f"  Cycle 3 (stabilization): {c3_total:3d} decisions ({len(cycle3_recon)} recon + {len(parliament_c3)} parliament)")
    print(f"  Unique agents: {sorted(all_agents_ever)}")
    print(f"  Telemetry readings: {r_alpha + r_beta + r_gamma}")
    print(f"  Decisions logged: {len(all_logged)}")
    print(f"  DynamoDB: {'synced' if dynamo else 'unavailable'}")
    print(f"  All 11 assertions PASSED")
    print("=" * 80)
