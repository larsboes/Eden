"""E2E test proving the closed-loop execution cycle.

Scenario:
  Cycle 1: Zone alpha too hot → flight rules fire fan ON → decision logged
  Cycle 2: Zone alpha cooled → feedback detects improvement
  Verify: feedback contains {zone: alpha, temperature: {before: ~36.7, after: ~22, action: cooling}}

This is the missing proof for the judges: recommendation → actuator fires →
sensor improves → the system KNOWS it improved.
"""

import time

from eden.application.reconciler import Reconciler
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import transform_temperature
from eden.domain.models import (
    ActuatorCommand,
    AgentDecision,
    CropProfile,
    DesiredState,
    DeviceType,
    SensorReading,
    Severity,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Fake adapters (minimal, same pattern as test_reconciler.py) ──────────


class FakeSensor:
    def __init__(self, zones: dict[str, ZoneState]):
        self._zones = zones

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def set_zone(self, zone_id: str, state: ZoneState) -> None:
        self._zones[zone_id] = state

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())


class FakeActuator:
    def __init__(self):
        self.commands: list[ActuatorCommand] = []

    def send_command(self, cmd: ActuatorCommand) -> bool:
        self.commands.append(cmd)
        return True


class FakeStateStore:
    def __init__(self):
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


class FakeTelemetry:
    def __init__(self):
        self.readings: list[SensorReading] = []

    def append(self, reading: SensorReading) -> None:
        self.readings.append(reading)

    def query(self, zone_id: str, since: float, limit: int) -> list[SensorReading]:
        return [r for r in self.readings if r.zone_id == zone_id and r.timestamp >= since][:limit]


class FakeAgentLog:
    def __init__(self):
        self.decisions: list[AgentDecision] = []

    def append(self, decision: AgentDecision) -> None:
        self.decisions.append(decision)

    def query(self, since: float, limit: int) -> list[AgentDecision]:
        return [d for d in self.decisions if d.timestamp >= since][:limit]


class FakeModel:
    def is_available(self) -> bool:
        return False

    def reason(self, prompt: str, context: dict) -> str:
        return ""


class FakeConfig:
    RECONCILE_INTERVAL_SECONDS = 30
    EDEN_SIMULATE = True
    LOG_LEVEL = "INFO"


# ── Helpers ──────────────────────────────────────────────────────────────


def _zone(zone_id: str = "alpha", temperature: float = 22.0, humidity: float = 55.0) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temperature,
        humidity=humidity,
        pressure=1013.0,
        light=500.0,
        water_level=50.0,
        fire_detected=False,
        last_updated=time.time(),
        is_alive=True,
        source="test",
    )


def _make_reconciler(sensor, actuator):
    state_store = FakeStateStore()
    telemetry = FakeTelemetry()
    agent_log = FakeAgentLog()
    model = FakeModel()
    flight_rules = FlightRulesEngine()
    crew = NutritionTracker.get_default_crew()
    crops = [CropProfile("lettuce", "alpha", 150.0, 13.0, 30, 3.5, 15.0, 25.0, 40.0, 80.0)]
    nutrition = NutritionTracker(crew=crew, crops=crops)

    return Reconciler(
        sensor=sensor,
        actuator=actuator,
        state_store=state_store,
        telemetry_store=telemetry,
        agent_log=agent_log,
        model=model,
        flight_rules=flight_rules,
        nutrition=nutrition,
        config=FakeConfig(),
    )


# ── The test ─────────────────────────────────────────────────────────────

# Mars transform at sol=0: dome_temp = 22.0 + (earth_c - 22.0) * 0.15
# To trigger FR-T-002 (temp > 35°C), need earth_c > ~108.7 → use 120
# To trigger FR-T-001 (temp < 5°C), need earth_c < ~-91.3 → use -100
# After fix: earth_c = 22.0 → dome = 22.0°C (nominal)

HOT_RAW = 120.0   # → dome ~36.7°C (triggers fan)
COLD_RAW = -100.0  # → dome ~3.7°C (triggers heater)
NOMINAL_RAW = 22.0  # → dome ~22.0°C (nominal)

HOT_DOME = transform_temperature(HOT_RAW, sol=0)
COLD_DOME = transform_temperature(COLD_RAW, sol=0)
NOMINAL_DOME = transform_temperature(NOMINAL_RAW, sol=0)


class TestClosedLoopExecution:
    """Proves the full closed loop: action → sensor change → feedback detection."""

    def test_cooling_loop_detected(self):
        """Cycle 1: hot zone → fan fires. Cycle 2: cooled → feedback detects improvement."""
        sensor = FakeSensor({"alpha": _zone(temperature=HOT_RAW)})
        actuator = FakeActuator()
        reconciler = _make_reconciler(sensor, actuator)

        # ── Cycle 1: hot zone triggers fan ──
        decisions_1 = reconciler.reconcile_once()

        fan_cmds = [c for c in actuator.commands if c.device == DeviceType.FAN]
        assert len(fan_cmds) >= 1, f"Fan should fire when dome temp > 35°C (dome={HOT_DOME:.1f}°C)"
        assert len(decisions_1) >= 1

        # No feedback yet (first cycle)
        assert reconciler.last_feedback == []

        # ── Simulate actuator effect: temperature drops ──
        sensor.set_zone("alpha", _zone(temperature=NOMINAL_RAW))

        # ── Cycle 2: cooled zone → feedback detects improvement ──
        reconciler.reconcile_once()

        feedback = reconciler.last_feedback
        assert len(feedback) >= 1, f"Expected feedback, got: {feedback}"

        alpha_fb = next(f for f in feedback if f["zone_id"] == "alpha")
        assert "temperature" in alpha_fb["improvements"], (
            f"Expected temperature improvement, got: {alpha_fb['improvements']}"
        )

        temp_fb = alpha_fb["improvements"]["temperature"]
        assert temp_fb["before"] == HOT_DOME
        assert temp_fb["after"] == NOMINAL_DOME
        assert temp_fb["action"] == "cooling"

    def test_heating_loop_detected(self):
        """Cycle 1: cold zone → heater fires. Cycle 2: warmed → feedback detects improvement."""
        sensor = FakeSensor({"alpha": _zone(temperature=COLD_RAW)})
        actuator = FakeActuator()
        reconciler = _make_reconciler(sensor, actuator)

        # Cycle 1: cold zone
        reconciler.reconcile_once()
        heater_cmds = [c for c in actuator.commands if c.device == DeviceType.HEATER]
        assert len(heater_cmds) >= 1, f"Heater should fire when dome temp < 5°C (dome={COLD_DOME:.1f}°C)"

        # Simulate warming
        sensor.set_zone("alpha", _zone(temperature=NOMINAL_RAW))

        # Cycle 2: warmed up
        reconciler.reconcile_once()

        feedback = reconciler.last_feedback
        assert len(feedback) >= 1
        alpha_fb = next(f for f in feedback if f["zone_id"] == "alpha")
        assert "temperature" in alpha_fb["improvements"]
        assert alpha_fb["improvements"]["temperature"]["action"] == "heating"
        assert alpha_fb["improvements"]["temperature"]["before"] == COLD_DOME
        assert alpha_fb["improvements"]["temperature"]["after"] == NOMINAL_DOME

    def test_humidity_ventilation_loop_detected(self):
        """Cycle 1: 95% humidity → fan fires. Cycle 2: 55% → feedback says ventilation worked."""
        sensor = FakeSensor({"alpha": _zone(humidity=95.0)})
        actuator = FakeActuator()
        reconciler = _make_reconciler(sensor, actuator)

        # Cycle 1: humid zone (humidity not Mars-transformed, passes through)
        reconciler.reconcile_once()
        fan_cmds = [c for c in actuator.commands if c.device == DeviceType.FAN]
        assert len(fan_cmds) >= 1, "Fan should fire when humidity > 90%"

        # Simulate dehumidification
        sensor.set_zone("alpha", _zone(humidity=55.0))

        # Cycle 2
        reconciler.reconcile_once()

        feedback = reconciler.last_feedback
        assert len(feedback) >= 1
        alpha_fb = next(f for f in feedback if f["zone_id"] == "alpha")
        assert "humidity" in alpha_fb["improvements"]
        assert alpha_fb["improvements"]["humidity"]["action"] == "ventilation"
        assert alpha_fb["improvements"]["humidity"]["before"] == 95.0
        assert alpha_fb["improvements"]["humidity"]["after"] == 55.0

    def test_no_feedback_when_no_improvement(self):
        """If conditions don't change, no feedback is generated."""
        sensor = FakeSensor({"alpha": _zone(temperature=NOMINAL_RAW, humidity=55.0)})
        actuator = FakeActuator()
        reconciler = _make_reconciler(sensor, actuator)

        # Cycle 1: normal conditions, no actions
        reconciler.reconcile_once()

        # Cycle 2: same conditions
        reconciler.reconcile_once()

        assert reconciler.last_feedback == []

    def test_multi_zone_feedback(self):
        """Feedback works across multiple zones independently."""
        sensor = FakeSensor({
            "alpha": _zone(zone_id="alpha", temperature=HOT_RAW),
            "beta": _zone(zone_id="beta", temperature=COLD_RAW),
        })
        actuator = FakeActuator()
        reconciler = _make_reconciler(sensor, actuator)

        # Cycle 1: both zones have issues
        reconciler.reconcile_once()

        # Simulate fixes
        sensor.set_zone("alpha", _zone(zone_id="alpha", temperature=NOMINAL_RAW))
        sensor.set_zone("beta", _zone(zone_id="beta", temperature=NOMINAL_RAW))

        # Cycle 2
        reconciler.reconcile_once()

        feedback = reconciler.last_feedback
        zone_ids = {f["zone_id"] for f in feedback}
        assert "alpha" in zone_ids, "Alpha should have cooling feedback"
        assert "beta" in zone_ids, "Beta should have heating feedback"

        alpha_fb = next(f for f in feedback if f["zone_id"] == "alpha")
        beta_fb = next(f for f in feedback if f["zone_id"] == "beta")
        assert alpha_fb["improvements"]["temperature"]["action"] == "cooling"
        assert beta_fb["improvements"]["temperature"]["action"] == "heating"
