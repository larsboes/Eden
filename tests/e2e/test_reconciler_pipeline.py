"""E2E integration tests — full reconciliation pipeline.

sensors → Mars transform → flight rules → (optional) agent parliament → actuator commands

Uses REAL: FlightRulesEngine, Mars transform, SqliteAdapter (temp dir), NutritionTracker.
Uses FAKE: Sensor port (inject test zones), Actuator port (record commands).
Optionally REAL: BedrockAdapter for scenario 2 (skipped if unavailable).
"""

from __future__ import annotations

import os
import tempfile
import time

import pytest

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.adapters.synced_store import SyncedStore
from eden.application.reconciler import Reconciler
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import (
    get_mars_conditions,
    inject_dust_storm,
    transform_light,
    transform_temperature,
)
from eden.domain.models import (
    ActuatorCommand,
    DesiredState,
    DeviceType,
    Severity,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Fake Ports ────────────────────────────────────────────────────────────


class FakeSensor:
    """Inject zone states for testing. Implements SensorPort."""

    def __init__(self, zones: dict[str, ZoneState]) -> None:
        self._zones = zones

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def set_zone(self, zone_id: str, zone: ZoneState) -> None:
        self._zones[zone_id] = zone


class FakeActuator:
    """Record actuator commands. Implements ActuatorPort."""

    def __init__(self) -> None:
        self.commands: list[ActuatorCommand] = []

    def send_command(self, cmd: ActuatorCommand) -> bool:
        self.commands.append(cmd)
        return True

    def commands_for_zone(self, zone_id: str) -> list[ActuatorCommand]:
        return [c for c in self.commands if c.zone_id == zone_id]

    def clear(self) -> None:
        self.commands.clear()


class FakeModel:
    """Model port that is unavailable by default."""

    def __init__(self, available: bool = False) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def reason(self, prompt: str, context: dict) -> str:
        return ""


class TelemetryStoreAdapter:
    """Adapts SyncedStore to TelemetryStorePort interface (mirrors __main__)."""

    def __init__(self, store) -> None:
        self._store = store

    def append(self, reading) -> None:
        self._store.append_telemetry(reading)

    def query(self, zone_id: str, since: float, limit: int = 100):
        return self._store.query_telemetry(zone_id, since, limit)


class AgentLogAdapter:
    """Adapts SyncedStore to AgentLogPort interface (mirrors __main__)."""

    def __init__(self, store) -> None:
        self._store = store

    def append(self, decision) -> None:
        self._store.append_agent_log(decision)

    def query(self, since: float, limit: int = 100):
        return self._store.query_agent_log(since, limit)


class FakeConfig:
    """Minimal config for tests."""
    RECONCILE_INTERVAL_SECONDS = 30
    LOG_LEVEL = "DEBUG"


# ── Helpers ───────────────────────────────────────────────────────────────


def make_zone(
    zone_id: str,
    temperature: float = 23.0,
    humidity: float = 60.0,
    pressure: float = 1013.25,
    light: float = 500.0,
    water_level: float = 50.0,
    fire_detected: bool = False,
    is_alive: bool = True,
) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        light=light,
        water_level=water_level,
        fire_detected=fire_detected,
        last_updated=time.time(),
        is_alive=is_alive,
        source="test",
    )


def make_desired(
    zone_id: str,
    temp_min: float = 18.0,
    temp_max: float = 28.0,
    humidity_min: float = 40.0,
    humidity_max: float = 80.0,
) -> DesiredState:
    return DesiredState(
        zone_id=zone_id,
        temp_min=temp_min,
        temp_max=temp_max,
        humidity_min=humidity_min,
        humidity_max=humidity_max,
        light_hours=16.0,
        soil_moisture_min=30.0,
        soil_moisture_max=70.0,
        water_budget_liters_per_day=5.0,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite DB, clean up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eden.db")
        sqlite = SqliteAdapter(db_path=db_path)
        store = SyncedStore(local=sqlite, remote=None)
        yield store, sqlite
        sqlite.close()


@pytest.fixture
def pipeline(tmp_db):
    """Build a full reconciler pipeline with fakes for sensor/actuator/model."""
    store, sqlite = tmp_db

    sensor = FakeSensor({})
    actuator = FakeActuator()
    telemetry_store = TelemetryStoreAdapter(store)
    agent_log = AgentLogAdapter(store)
    model = FakeModel(available=False)
    flight_rules = FlightRulesEngine()
    crew = NutritionTracker.get_default_crew()
    nutrition = NutritionTracker(crew=crew, crops=[])
    config = FakeConfig()

    reconciler = Reconciler(
        sensor=sensor,
        actuator=actuator,
        state_store=store,
        telemetry_store=telemetry_store,
        agent_log=agent_log,
        model=model,
        flight_rules=flight_rules,
        nutrition=nutrition,
        config=config,
    )

    return {
        "reconciler": reconciler,
        "sensor": sensor,
        "actuator": actuator,
        "store": store,
        "telemetry_store": telemetry_store,
        "agent_log": agent_log,
        "model": model,
        "flight_rules": flight_rules,
        "nutrition": nutrition,
    }


# ══════════════════════════════════════════════════════════════════════════
# Scenario 1: Normal Operations — Sol 100, clear skies
# ══════════════════════════════════════════════════════════════════════════


class TestScenario1NormalOperations:
    """3 zones, all within desired ranges. Expect ZERO commands."""

    def test_no_flight_rules_fire(self, pipeline):
        """All zones nominal → no actuator commands produced."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]
        store = pipeline["store"]

        # Set sol
        reconciler._current_sol = 100

        # Inject 3 zones — values chosen so post-Mars-transform stays in safe range
        # transform_temperature dampens toward ~22°C (0.15 coupling from Earth input)
        # transform_light: earth_lux * 0.43 * 0.7 (default dust 0.3)
        sensor.set_zone("alpha", make_zone("alpha", temperature=23.0, light=500.0, water_level=50.0))
        sensor.set_zone("beta", make_zone("beta", temperature=20.0, light=500.0, water_level=50.0))
        sensor.set_zone("gamma", make_zone("gamma", temperature=22.0, light=500.0, water_level=50.0))

        # Set desired states (generous ranges — everything is "in spec")
        store.put_desired_state("alpha", make_desired("alpha"))
        store.put_desired_state("beta", make_desired("beta"))
        store.put_desired_state("gamma", make_desired("gamma"))

        # Reconcile
        decisions = reconciler.reconcile_once()

        # Verify: ZERO actuator commands
        assert len(actuator.commands) == 0, (
            f"Expected 0 commands for normal ops, got {len(actuator.commands)}: "
            f"{[(c.zone_id, c.device.value, c.action) for c in actuator.commands]}"
        )

    def test_telemetry_persisted(self, pipeline):
        """Telemetry is written for all 3 zones (5 sensor types each = 15 readings)."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        telemetry_store = pipeline["telemetry_store"]

        reconciler._current_sol = 100
        sensor.set_zone("alpha", make_zone("alpha", temperature=23.0))
        sensor.set_zone("beta", make_zone("beta", temperature=20.0))
        sensor.set_zone("gamma", make_zone("gamma", temperature=22.0))

        before = time.time() - 1
        reconciler.reconcile_once()

        # Check telemetry was written for each zone
        for zone_id in ["alpha", "beta", "gamma"]:
            readings = telemetry_store.query(zone_id, since=before, limit=100)
            assert len(readings) == 5, (
                f"Expected 5 telemetry readings for {zone_id}, got {len(readings)}"
            )

    def test_zone_state_persisted(self, pipeline):
        """Zone state is persisted to storage after reconciliation."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        store = pipeline["store"]

        reconciler._current_sol = 100
        sensor.set_zone("alpha", make_zone("alpha", temperature=23.0))

        reconciler.reconcile_once()

        # Zone state should be in storage (with Mars-transformed values)
        persisted = store.get_zone_state("alpha")
        assert persisted is not None
        assert persisted.zone_id == "alpha"
        # Temperature should be Mars-transformed (~22.5°C, not raw 23°C)
        expected_temp = transform_temperature(23.0, 100)
        assert abs(persisted.temperature - expected_temp) < 0.01

    def test_no_model_invoked(self, pipeline):
        """With all values in desired range, model should NOT be invoked."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        store = pipeline["store"]

        reconciler._current_sol = 100
        sensor.set_zone("alpha", make_zone("alpha", temperature=23.0))
        # Desired state range encompasses the post-transform value (~22.5)
        store.put_desired_state("alpha", make_desired("alpha", temp_min=18.0, temp_max=28.0))

        decisions = reconciler.reconcile_once()

        # No model decisions (model is unavailable AND no deltas)
        model_decisions = [d for d in decisions if d.agent_name == "MODEL"]
        assert len(model_decisions) == 0


# ══════════════════════════════════════════════════════════════════════════
# Scenario 2: Heat Stress — Sol 200, approaching summer
# ══════════════════════════════════════════════════════════════════════════


class TestScenario2HeatStress:
    """Zone alpha extremely hot → FR-T-002 fires (fan ON)."""

    def test_fr_t_002_fan_on_for_heat(self, pipeline):
        """Temperature > 35°C after Mars transform → fan ON 100%."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 200

        # Need post-transform temp > 35°C.
        # transform_temperature dampens: dome = 22 + offset + (raw - 22) * 0.15
        # At sol=200, offset ≈ 0.137. For dome > 35: raw > ~108.8
        # Use raw=120°C (e.g., heater malfunction / extreme event)
        raw_temp = 120.0
        post_transform = transform_temperature(raw_temp, 200)
        assert post_transform > 35.0, f"Post-transform {post_transform} should exceed 35°C"

        sensor.set_zone("alpha", make_zone("alpha", temperature=raw_temp, humidity=40.0))
        sensor.set_zone("beta", make_zone("beta", temperature=20.0))  # nominal

        decisions = reconciler.reconcile_once()

        # FR-T-002 should fire for alpha
        alpha_cmds = actuator.commands_for_zone("alpha")
        fan_cmds = [c for c in alpha_cmds if c.device == DeviceType.FAN and c.action == "on"]
        assert len(fan_cmds) >= 1, (
            f"Expected fan ON command for overheated alpha, got: "
            f"{[(c.device.value, c.action, c.value) for c in alpha_cmds]}"
        )
        assert fan_cmds[0].value == 100.0

        # Beta should have NO commands (nominal)
        beta_cmds = actuator.commands_for_zone("beta")
        assert len(beta_cmds) == 0, f"Beta should have no commands, got {len(beta_cmds)}"

    def test_fr_t_002_decision_logged(self, pipeline):
        """Flight rule decision is logged for heat stress."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        agent_log = pipeline["agent_log"]

        reconciler._current_sol = 200
        sensor.set_zone("alpha", make_zone("alpha", temperature=120.0, humidity=40.0))

        before = time.time() - 1
        decisions = reconciler.reconcile_once()

        # Check decisions returned
        fr_decisions = [d for d in decisions if d.agent_name == "FLIGHT_RULES"]
        assert len(fr_decisions) >= 1
        assert any("FR-T-002" in d.reasoning or "temperature" in d.reasoning for d in fr_decisions)

        # Check decisions persisted to agent log
        logged = agent_log.query(since=before, limit=100)
        assert len(logged) >= 1

    def test_humidity_rules_do_not_fire(self, pipeline):
        """Humidity 40% is within 30-90% range → no humidity rules."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 200
        sensor.set_zone("alpha", make_zone("alpha", temperature=120.0, humidity=40.0))

        reconciler.reconcile_once()

        # No pump commands (humidity rules involve pump for FR-H-002)
        alpha_cmds = actuator.commands_for_zone("alpha")
        pump_cmds = [c for c in alpha_cmds if c.device == DeviceType.PUMP]
        assert len(pump_cmds) == 0

    @pytest.mark.skipif(
        os.getenv("TEST_BEDROCK", "").lower() != "true",
        reason="Bedrock integration requires TEST_BEDROCK=true",
    )
    def test_bedrock_model_recommends_cooling(self, pipeline):
        """With real Bedrock model, DEMETER recommends cooling strategy."""
        from eden.adapters.bedrock_adapter import BedrockAdapter

        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        store = pipeline["store"]

        reconciler._current_sol = 200
        sensor.set_zone("alpha", make_zone("alpha", temperature=120.0, humidity=40.0))

        # Set desired state so deltas exist
        post_temp = transform_temperature(120.0, 200)
        store.put_desired_state(
            "alpha",
            make_desired("alpha", temp_min=18.0, temp_max=28.0),
        )

        # Wire real Bedrock model
        try:
            bedrock = BedrockAdapter(
                model_id="us.anthropic.claude-sonnet-4-6",
                region="us-west-2",
            )
            if not bedrock.is_available():
                pytest.skip("Bedrock not available")
            reconciler._model = bedrock
        except Exception:
            pytest.skip("Bedrock client creation failed")

        decisions = reconciler.reconcile_once()

        model_decisions = [d for d in decisions if d.agent_name == "MODEL"]
        assert len(model_decisions) >= 1, "Expected at least one model decision"
        assert model_decisions[0].action, "Model should have produced a recommendation"


# ══════════════════════════════════════════════════════════════════════════
# Scenario 3: Dust Storm Onset — Sol 250
# ══════════════════════════════════════════════════════════════════════════


class TestScenario3DustStorm:
    """Dust storm at Sol 250 → light drops → FR-L-001 fires."""

    def test_mars_transform_reduces_light_during_storm(self):
        """Pure function test: dust storm dramatically reduces light."""
        mars = inject_dust_storm(250)
        assert mars.dust_opacity == 0.85
        assert mars.storm_active is True

        # Light transform: earth_lux * 0.43 * (1 - 0.85) = earth_lux * 0.0645
        earth_lux = 500.0
        mars_lux = transform_light(earth_lux, mars.dust_opacity)
        assert mars_lux < 100.0, f"Expected light < 100 during storm, got {mars_lux:.1f}"
        assert mars_lux == pytest.approx(500.0 * 0.43 * 0.15, rel=0.01)

    def test_fr_l_001_light_on_during_storm(self, pipeline):
        """Light < 100 lux after dust storm transform → FR-L-001 fires (light ON)."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        # inject_dust_storm produces dust_opacity=0.85
        # But the reconciler uses get_mars_conditions(sol) which has default dust=0.3.
        # The reconciler's _apply_mars_transform uses mars.dust_opacity from get_mars_conditions.
        # To simulate a dust storm, we need to override the mars conditions.
        # The reconciler calls get_mars_conditions(self._current_sol) with default dust.
        # We can't directly inject dust storm into reconciler, so we set light low enough
        # that even default 0.3 dust makes it < 100 lux, OR we monkeypatch.

        # Approach: Set light so low that after default transform it's < 100.
        # transform_light(earth_lux, 0.3) = earth_lux * 0.43 * 0.7 = earth_lux * 0.301
        # For result < 100: earth_lux < 332.2
        # For the "dust storm" scenario, set very low light (simulating overcast + dust)
        # With 100 lux input: 100 * 0.301 = 30.1 lux → well below 100.
        reconciler._current_sol = 250
        sensor.set_zone(
            "alpha",
            make_zone("alpha", temperature=22.0, light=100.0, water_level=50.0),
        )

        decisions = reconciler.reconcile_once()

        alpha_cmds = actuator.commands_for_zone("alpha")
        light_cmds = [c for c in alpha_cmds if c.device == DeviceType.LIGHT and c.action == "on"]
        assert len(light_cmds) >= 1, (
            f"Expected light ON during low-light conditions, got: "
            f"{[(c.device.value, c.action) for c in alpha_cmds]}"
        )

    def test_fr_e_001_power_rationing_standalone(self):
        """FR-E-001: solar efficiency < 50% → power rationing (tested standalone).

        The reconciler doesn't pass EnergyBudget to flight rules, so we test
        the engine directly to verify the rule works.
        """
        from eden.domain.models import EnergyBudget

        engine = FlightRulesEngine()
        energy = EnergyBudget(
            solar_capacity_kw=10.0,
            current_efficiency=0.15,  # 15% — dust storm
            allocations={"lights": 2.0, "heater": 3.0},
            reserve_kw=1.5,
        )

        decisions = engine.evaluate_energy(energy)
        assert len(decisions) >= 1
        assert decisions[0].severity == Severity.HIGH
        assert "rationing" in decisions[0].action.lower()

    def test_dust_storm_conditions_are_extreme(self):
        """Verify inject_dust_storm produces expected extreme conditions."""
        mars = inject_dust_storm(250)

        assert mars.dust_opacity == 0.85
        assert mars.storm_active is True
        assert mars.solar_irradiance < 100.0  # Normal ~413 W/m² → storm ~88.5
        assert mars.exterior_temp < -60.0  # Extra cold during storm


# ══════════════════════════════════════════════════════════════════════════
# Scenario 4: Multi-Zone Crisis — Sol 300
# ══════════════════════════════════════════════════════════════════════════


class TestScenario4MultiZoneCrisis:
    """Fire in alpha, water crisis in beta, gamma normal."""

    def test_fire_short_circuits_alpha(self, pipeline):
        """Fire detected → ALL devices OFF in alpha."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))
        sensor.set_zone("beta", make_zone("beta", water_level=5.0))
        sensor.set_zone("gamma", make_zone("gamma"))

        reconciler.reconcile_once()

        # Alpha: ALL devices should be turned OFF
        alpha_cmds = actuator.commands_for_zone("alpha")
        assert len(alpha_cmds) >= len(DeviceType), (
            f"Expected at least {len(DeviceType)} OFF commands for fire zone, "
            f"got {len(alpha_cmds)}"
        )
        for cmd in alpha_cmds:
            assert cmd.action == "off", f"Fire zone: {cmd.device.value} should be OFF, got {cmd.action}"
            assert cmd.value == 0.0
            assert cmd.priority == Severity.CRITICAL

    def test_water_crisis_beta_pump_off(self, pipeline):
        """Water < 10mm → FR-W-001 fires → pump OFF in beta."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))
        sensor.set_zone("beta", make_zone("beta", water_level=5.0))
        sensor.set_zone("gamma", make_zone("gamma"))

        reconciler.reconcile_once()

        beta_cmds = actuator.commands_for_zone("beta")
        pump_off = [c for c in beta_cmds if c.device == DeviceType.PUMP and c.action == "off"]
        assert len(pump_off) >= 1, (
            f"Expected pump OFF for water crisis, got: "
            f"{[(c.device.value, c.action) for c in beta_cmds]}"
        )

    def test_gamma_unaffected(self, pipeline):
        """Gamma is normal — should have zero commands."""
        sensor: FakeSensor = pipeline["sensor"]
        actuator: FakeActuator = pipeline["actuator"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))
        sensor.set_zone("beta", make_zone("beta", water_level=5.0))
        sensor.set_zone("gamma", make_zone("gamma"))

        reconciler.reconcile_once()

        gamma_cmds = actuator.commands_for_zone("gamma")
        assert len(gamma_cmds) == 0, (
            f"Gamma should be unaffected, got: "
            f"{[(c.device.value, c.action) for c in gamma_cmds]}"
        )

    def test_fire_decision_is_critical(self, pipeline):
        """Fire decision is logged at CRITICAL severity."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))

        decisions = reconciler.reconcile_once()

        fire_decisions = [
            d for d in decisions
            if d.zone_id == "alpha" and d.severity == Severity.CRITICAL
        ]
        assert len(fire_decisions) >= 1
        assert "fire" in fire_decisions[0].reasoning.lower() or "FIRE" in fire_decisions[0].reasoning

    def test_multi_zone_state_persisted(self, pipeline):
        """All 3 zones' state is persisted despite crises."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]
        store = pipeline["store"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))
        sensor.set_zone("beta", make_zone("beta", water_level=5.0))
        sensor.set_zone("gamma", make_zone("gamma"))

        reconciler.reconcile_once()

        for zone_id in ["alpha", "beta", "gamma"]:
            state = store.get_zone_state(zone_id)
            assert state is not None, f"Zone {zone_id} state should be persisted"

    def test_crisis_decisions_count(self, pipeline):
        """Fire + water crisis should produce multiple decisions."""
        sensor: FakeSensor = pipeline["sensor"]
        reconciler: Reconciler = pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", make_zone("alpha", fire_detected=True))
        sensor.set_zone("beta", make_zone("beta", water_level=5.0))
        sensor.set_zone("gamma", make_zone("gamma"))

        decisions = reconciler.reconcile_once()

        # At least 1 fire decision + 1 water decision
        assert len(decisions) >= 2, f"Expected >= 2 decisions, got {len(decisions)}"
        zones_with_decisions = {d.zone_id for d in decisions}
        assert "alpha" in zones_with_decisions, "Alpha (fire) should have decisions"
        assert "beta" in zones_with_decisions, "Beta (water) should have decisions"
