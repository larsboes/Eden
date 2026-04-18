"""Tests for eden.application.reconciler — written BEFORE implementation (TDD)."""

import time
import threading
import pytest

from eden.domain.models import (
    SensorType,
    DeviceType,
    Severity,
    Tier,
    SensorReading,
    ActuatorCommand,
    AgentDecision,
    ZoneState,
    DesiredState,
    CrewMember,
    CropProfile,
)
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.nutrition import NutritionTracker
from eden.application.reconciler import Reconciler


# ── Fake Adapters (implement Protocol interfaces structurally) ───────────


class FakeSensorPort:
    def __init__(self, zones: dict[str, ZoneState] | None = None):
        self._zones = zones or {}
        self._callbacks = []
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def subscribe(self, callback):
        self._callbacks.append(callback)

    def set_zone(self, zone_id: str, state: ZoneState):
        self._zones[zone_id] = state

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())


class FakeActuatorPort:
    def __init__(self):
        self.commands_sent: list[ActuatorCommand] = []

    def send_command(self, command: ActuatorCommand) -> bool:
        self.commands_sent.append(command)
        return True


class FakeStateStorePort:
    def __init__(self):
        self._zone_states: dict[str, ZoneState] = {}
        self._desired_states: dict[str, DesiredState] = {}

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        return self._zone_states.get(zone_id)

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self._zone_states[zone_id] = state

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        return self._desired_states.get(zone_id)

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self._desired_states[zone_id] = state


class FakeTelemetryStorePort:
    def __init__(self):
        self.readings: list[SensorReading] = []

    def append(self, reading: SensorReading) -> None:
        self.readings.append(reading)

    def query(self, zone_id: str, since: float, limit: int) -> list[SensorReading]:
        return [r for r in self.readings if r.zone_id == zone_id and r.timestamp >= since][:limit]


class FakeAgentLogPort:
    def __init__(self):
        self.decisions: list[AgentDecision] = []

    def append(self, decision: AgentDecision) -> None:
        self.decisions.append(decision)

    def query(self, since: float, limit: int) -> list[AgentDecision]:
        return [d for d in self.decisions if d.timestamp >= since][:limit]


class FakeModelPort:
    def __init__(self, available: bool = False, response: str = "no action needed"):
        self._available = available
        self._response = response
        self.prompts: list[str] = []
        self.contexts: list[dict] = []

    def reason(self, prompt: str, context: dict) -> str:
        self.prompts.append(prompt)
        self.contexts.append(context)
        return self._response

    def is_available(self) -> bool:
        return self._available


class FakeSettings:
    RECONCILE_INTERVAL_SECONDS = 30
    EDEN_SIMULATE = True
    LOG_LEVEL = "INFO"


# ── Helpers ──────────────────────────────────────────────────────────────


def make_zone(
    zone_id: str = "alpha",
    temperature: float = 22.0,
    humidity: float = 60.0,
    light: float = 500.0,
    water_level: float = 80.0,
    pressure: float = 1013.0,
    fire_detected: bool = False,
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
        is_alive=True,
        source="test",
    )


def make_desired(zone_id: str = "alpha") -> DesiredState:
    return DesiredState(
        zone_id=zone_id,
        temp_min=18.0,
        temp_max=28.0,
        humidity_min=40.0,
        humidity_max=80.0,
        light_hours=16.0,
        soil_moisture_min=30.0,
        soil_moisture_max=70.0,
        water_budget_liters_per_day=5.0,
    )


def make_nutrition() -> NutritionTracker:
    crew = NutritionTracker.get_default_crew()
    crops = [
        CropProfile("lettuce", "alpha", 150.0, 13.0, 30, 3.5, 15.0, 25.0, 40.0, 80.0),
    ]
    return NutritionTracker(crew=crew, crops=crops)


def build_reconciler(
    zones: dict[str, ZoneState] | None = None,
    model_available: bool = False,
    model_response: str = "no action needed",
) -> tuple[Reconciler, FakeSensorPort, FakeActuatorPort, FakeStateStorePort, FakeTelemetryStorePort, FakeAgentLogPort, FakeModelPort]:
    sensor = FakeSensorPort(zones or {})
    actuator = FakeActuatorPort()
    state_store = FakeStateStorePort()
    telemetry = FakeTelemetryStorePort()
    agent_log = FakeAgentLogPort()
    model = FakeModelPort(available=model_available, response=model_response)
    flight_rules = FlightRulesEngine()
    nutrition = make_nutrition()
    config = FakeSettings()

    reconciler = Reconciler(
        sensor=sensor,
        actuator=actuator,
        state_store=state_store,
        telemetry_store=telemetry,
        agent_log=agent_log,
        model=model,
        flight_rules=flight_rules,
        nutrition=nutrition,
        config=config,
    )
    return reconciler, sensor, actuator, state_store, telemetry, agent_log, model


# ── Construction ─────────────────────────────────────────────────────────


class TestReconcilerConstruction:
    def test_can_create(self):
        reconciler, *_ = build_reconciler()
        assert reconciler is not None

    def test_accepts_none_model(self):
        sensor = FakeSensorPort()
        actuator = FakeActuatorPort()
        state_store = FakeStateStorePort()
        telemetry = FakeTelemetryStorePort()
        agent_log = FakeAgentLogPort()
        flight_rules = FlightRulesEngine()
        nutrition = make_nutrition()
        config = FakeSettings()

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=state_store,
            telemetry_store=telemetry,
            agent_log=agent_log,
            model=None,
            flight_rules=flight_rules,
            nutrition=nutrition,
            config=config,
        )
        assert reconciler is not None


# ── Single Cycle (reconcile_once) ────────────────────────────────────────


class TestReconcileOnce:
    def test_normal_zone_no_commands(self):
        """Normal zone within desired range — no commands issued."""
        zones = {"alpha": make_zone()}
        reconciler, sensor, actuator, state_store, *_ = build_reconciler(zones=zones)
        state_store.put_desired_state("alpha", make_desired())

        decisions = reconciler.reconcile_once()

        assert len(actuator.commands_sent) == 0
        assert isinstance(decisions, list)

    def test_returns_list_of_decisions(self):
        """reconcile_once always returns a list of AgentDecision."""
        # Need extreme Earth temp so Mars-transformed dome temp < 5°C
        # transform_temperature(-100, sol=0) ≈ 3.7°C → heater fires
        zones = {"alpha": make_zone(temperature=-100.0)}
        reconciler, *_ = build_reconciler(zones=zones)

        decisions = reconciler.reconcile_once()

        assert isinstance(decisions, list)
        assert len(decisions) >= 1
        assert all(isinstance(d, AgentDecision) for d in decisions)

    def test_cold_zone_triggers_heater(self):
        """Zone below 5°C after Mars transform — flight rules fire heater."""
        # transform_temperature(-100, sol=0) ≈ 3.7°C → below 5°C threshold
        zones = {"alpha": make_zone(temperature=-100.0)}
        reconciler, sensor, actuator, *_ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        heater_cmds = [c for c in actuator.commands_sent if c.device == DeviceType.HEATER]
        assert len(heater_cmds) >= 1
        assert heater_cmds[0].action == "on"

    def test_fire_shuts_down_everything(self):
        """Fire detected → emergency shutdown of ALL devices."""
        zones = {"alpha": make_zone(fire_detected=True)}
        reconciler, sensor, actuator, *_ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        off_cmds = [c for c in actuator.commands_sent if c.action == "off"]
        assert len(off_cmds) >= 5  # All device types

    def test_persists_zone_state(self):
        """Zone state should be persisted to state store."""
        zones = {"alpha": make_zone()}
        reconciler, sensor, actuator, state_store, *_ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        stored = state_store.get_zone_state("alpha")
        assert stored is not None
        assert stored.zone_id == "alpha"

    def test_logs_decisions(self):
        """Flight rule triggers should be logged to agent_log."""
        zones = {"alpha": make_zone(temperature=-100.0)}
        reconciler, _, _, _, _, agent_log, _ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        assert len(agent_log.decisions) >= 1
        assert agent_log.decisions[0].tier == Tier.FLIGHT_RULES

    def test_multiple_zones(self):
        """Reconciler should process all zones in a single cycle."""
        # Extreme Earth temps so Mars-transformed dome temps trigger flight rules
        # alpha: -100 → dome ~3.7°C (heater), beta: 120 → dome ~36.7°C (fan)
        zones = {
            "alpha": make_zone(zone_id="alpha", temperature=-100.0),
            "beta": make_zone(zone_id="beta", temperature=120.0),
        }
        reconciler, sensor, actuator, *_ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        heater_cmds = [c for c in actuator.commands_sent if c.device == DeviceType.HEATER and c.zone_id == "alpha"]
        fan_cmds = [c for c in actuator.commands_sent if c.device == DeviceType.FAN and c.zone_id == "beta"]
        assert len(heater_cmds) >= 1
        assert len(fan_cmds) >= 1

    def test_no_zones_no_crash(self):
        """Empty sensor — reconcile should complete without error."""
        reconciler, *_ = build_reconciler(zones={})
        decisions = reconciler.reconcile_once()
        assert decisions == []

    def test_missing_zone_returns_none_skipped(self):
        """If sensor returns None for a zone, skip it gracefully."""
        sensor = FakeSensorPort({"alpha": make_zone()})
        # Manually add a zone_id that has no state
        sensor._zones["ghost"] = None  # type: ignore
        reconciler, *_ = build_reconciler(zones={"alpha": make_zone()})
        # Override sensor
        reconciler._sensor = sensor
        reconciler.reconcile_once()  # Should not raise


# ── Mars Transform ───────────────────────────────────────────────────────


class TestMarsTransform:
    def test_mars_transform_applied_to_readings(self):
        """Mars transform should modify zone state values before flight rules."""
        # Use Earth-like values that transform differently on Mars
        zones = {"alpha": make_zone(temperature=22.0, pressure=1013.0, light=1000.0)}
        reconciler, _, _, state_store, *_ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        stored = state_store.get_zone_state("alpha")
        assert stored is not None
        # Pressure should be scaled down (Mars greenhouse ~700 hPa vs Earth 1013)
        assert stored.pressure < 1013.0
        # Light should be reduced (Mars solar factor ~0.43)
        assert stored.light < 1000.0


# ── Model Invocation ─────────────────────────────────────────────────────


class TestModelInvocation:
    def test_deltas_with_model_available_invokes_model(self):
        """When deltas exist and model is available, model.reason() is called."""
        # Earth temp -10 → dome temp ≈ 17.2°C (below desired min 18)
        # But above flight rule heater threshold of 5°C
        zones = {"alpha": make_zone(temperature=-10.0)}
        reconciler, _, _, state_store, _, _, model = build_reconciler(
            zones=zones, model_available=True,
        )
        state_store.put_desired_state("alpha", make_desired())  # temp_min=18

        reconciler.reconcile_once()

        assert len(model.prompts) >= 1

    def test_deltas_without_model_only_flight_rules(self):
        """When model is None, only flight rules run — no crash."""
        zones = {"alpha": make_zone(temperature=-10.0)}
        sensor = FakeSensorPort(zones)
        actuator = FakeActuatorPort()
        state_store = FakeStateStorePort()
        telemetry = FakeTelemetryStorePort()
        agent_log = FakeAgentLogPort()
        flight_rules = FlightRulesEngine()
        nutrition = make_nutrition()
        config = FakeSettings()

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=state_store,
            telemetry_store=telemetry,
            agent_log=agent_log,
            model=None,
            flight_rules=flight_rules,
            nutrition=nutrition,
            config=config,
        )
        state_store.put_desired_state("alpha", make_desired())

        decisions = reconciler.reconcile_once()
        assert isinstance(decisions, list)
        # Should not crash without a model

    def test_model_unavailable_not_invoked(self):
        """If model.is_available() returns False, model.reason() is not called."""
        zones = {"alpha": make_zone(temperature=-10.0)}
        reconciler, _, _, state_store, _, _, model = build_reconciler(
            zones=zones, model_available=False,
        )
        state_store.put_desired_state("alpha", make_desired())

        reconciler.reconcile_once()

        assert len(model.prompts) == 0

    def test_no_deltas_model_not_invoked(self):
        """If everything is in range, model should NOT be called."""
        zones = {"alpha": make_zone(temperature=22.0, humidity=60.0)}
        reconciler, _, _, state_store, _, _, model = build_reconciler(
            zones=zones, model_available=True,
        )
        state_store.put_desired_state("alpha", make_desired())

        reconciler.reconcile_once()

        assert len(model.prompts) == 0

    def test_model_context_includes_nutrition(self):
        """Agent context dict should include nutritional status."""
        zones = {"alpha": make_zone(temperature=-10.0)}
        reconciler, _, _, state_store, _, _, model = build_reconciler(
            zones=zones, model_available=True,
        )
        state_store.put_desired_state("alpha", make_desired())

        reconciler.reconcile_once()

        assert len(model.contexts) >= 1
        ctx = model.contexts[0]
        assert "nutritional_status" in ctx


# ── Telemetry Persistence ────────────────────────────────────────────────


class TestTelemetryPersistence:
    def test_telemetry_stored(self):
        """Zone sensor readings should be persisted to telemetry store."""
        zones = {"alpha": make_zone()}
        reconciler, _, _, _, telemetry, _, _ = build_reconciler(zones=zones)

        reconciler.reconcile_once()

        assert len(telemetry.readings) >= 1
        assert telemetry.readings[0].zone_id == "alpha"


# ── Graceful Shutdown ────────────────────────────────────────────────────


class TestGracefulShutdown:
    def test_stop_flag(self):
        reconciler, *_ = build_reconciler()
        reconciler.stop()
        assert reconciler._running is False

    def test_run_stops_on_stop(self):
        """run() should exit when stop() is called."""
        reconciler, *_ = build_reconciler()

        def stop_after_short_delay():
            time.sleep(0.15)
            reconciler.stop()

        t = threading.Thread(target=stop_after_short_delay)
        t.start()
        reconciler.run()  # Should exit quickly
        t.join(timeout=2.0)
        assert not t.is_alive()

    def test_exception_in_cycle_doesnt_kill_loop(self):
        """An exception during reconcile_once should not terminate run()."""
        reconciler, *_ = build_reconciler()
        call_count = 0

        original_reconcile = reconciler.reconcile_once

        def exploding_reconcile():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated failure")
            # Second call succeeds — stop the loop
            reconciler.stop()
            return original_reconcile()

        reconciler.reconcile_once = exploding_reconcile
        # Use very short interval so the test doesn't hang
        reconciler._config.RECONCILE_INTERVAL_SECONDS = 0

        reconciler.run()

        # Should have been called at least twice (first fails, second succeeds + stops)
        assert call_count >= 2
