"""E2E scenario tests for the Tier 0 Flight Rules Engine.

Real FlightRulesEngine, real domain objects, no mocks.
Each test simulates a realistic Mars greenhouse condition and verifies
exact commands, device types, actions, and severities.
"""

import time

import pytest

from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.models import (
    DeviceType,
    EnergyBudget,
    GasExchange,
    Severity,
    ZoneState,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _zone(
    zone_id: str = "bay-1",
    temperature: float = 22.0,
    humidity: float = 55.0,
    pressure: float = 1013.0,
    light: float = 500.0,
    water_level: float = 50.0,
    fire_detected: bool = False,
) -> ZoneState:
    """Build a ZoneState with sane defaults — override only what the scenario needs."""
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
        source="test-harness",
    )


def _energy(efficiency: float = 0.85) -> EnergyBudget:
    return EnergyBudget(
        solar_capacity_kw=12.0,
        current_efficiency=efficiency,
        allocations={"lighting": 3.0, "heating": 4.0, "pumps": 1.5},
        reserve_kw=2.0,
    )


def _gas(co2_ppm: float = 800.0) -> GasExchange:
    return GasExchange(
        greenhouse_co2_ppm=co2_ppm,
        greenhouse_o2_pct=21.0,
        habitat_co2_ppm=400.0,
        habitat_o2_pct=20.9,
        exchange_rate=0.5,
    )


# ── Scenario 1: Frost Night ──────────────────────────────────────────────


class TestFrostNight:
    """Mars night cycle drops to 2°C → FR-T-001 fires heater at 100%."""

    def test_heater_fires_on_frost(self):
        engine = FlightRulesEngine()
        zone = _zone(temperature=2.0)

        commands, decisions = engine.evaluate(zone)

        # Must have at least the heater command
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER]
        assert len(heater_cmds) == 1, f"Expected 1 heater command, got {len(heater_cmds)}"

        cmd = heater_cmds[0]
        assert cmd.action == "on"
        assert cmd.value == 100.0
        assert cmd.priority == Severity.CRITICAL
        assert cmd.zone_id == "bay-1"

    def test_frost_decision_logged(self):
        engine = FlightRulesEngine()
        zone = _zone(temperature=2.0)

        _, decisions = engine.evaluate(zone)

        frost_decisions = [d for d in decisions if "temperature" in d.reasoning]
        assert len(frost_decisions) >= 1
        assert frost_decisions[0].severity == Severity.CRITICAL
        assert frost_decisions[0].agent_name == "FLIGHT_RULES"


# ── Scenario 2: Humidity Spike After Irrigation ──────────────────────────


class TestHumiditySpike:
    """Post-irrigation humidity at 92% → FR-H-001 engages fan at 50% (mold risk)."""

    def test_fan_engages_on_high_humidity(self):
        engine = FlightRulesEngine()
        zone = _zone(humidity=92.0)

        commands, _ = engine.evaluate(zone)

        fan_cmds = [c for c in commands if c.device == DeviceType.FAN]
        assert len(fan_cmds) >= 1

        cmd = fan_cmds[0]
        assert cmd.action == "on"
        assert cmd.value == 50.0
        assert cmd.priority == Severity.MEDIUM

    def test_humidity_reason_mentions_threshold(self):
        engine = FlightRulesEngine()
        zone = _zone(humidity=92.0)

        commands, _ = engine.evaluate(zone)
        fan_cmd = next(c for c in commands if c.device == DeviceType.FAN)
        assert "humidity" in fan_cmd.reason.lower()


# ── Scenario 3: Water Crisis ─────────────────────────────────────────────


class TestWaterCrisis:
    """Water level at 8mm → FR-W-001 kills pump + CRITICAL alert."""

    def test_pump_off_on_low_water(self):
        engine = FlightRulesEngine()
        zone = _zone(water_level=8.0)

        commands, decisions = engine.evaluate(zone)

        pump_cmds = [c for c in commands if c.device == DeviceType.PUMP]
        assert len(pump_cmds) >= 1

        cmd = pump_cmds[0]
        assert cmd.action == "off"
        assert cmd.value == 0.0
        assert cmd.priority == Severity.CRITICAL

    def test_water_crisis_severity(self):
        engine = FlightRulesEngine()
        zone = _zone(water_level=8.0)

        _, decisions = engine.evaluate(zone)

        water_decisions = [d for d in decisions if "water_level" in d.reasoning]
        assert len(water_decisions) >= 1
        assert water_decisions[0].severity == Severity.CRITICAL


# ── Scenario 4: Fire in Bay 2 ────────────────────────────────────────────


class TestFireEmergency:
    """Fire sensor triggers in bay-2 → ALL devices OFF (short-circuit)."""

    def test_all_devices_shut_down(self):
        engine = FlightRulesEngine()
        zone = _zone(zone_id="bay-2", fire_detected=True)

        commands, decisions = engine.evaluate(zone)

        # Every DeviceType must have an OFF command
        devices_off = {c.device for c in commands if c.action == "off"}
        for device in DeviceType:
            assert device in devices_off, f"{device.value} was NOT shut down during fire"

    def test_fire_all_commands_critical(self):
        engine = FlightRulesEngine()
        zone = _zone(zone_id="bay-2", fire_detected=True)

        commands, _ = engine.evaluate(zone)

        for cmd in commands:
            assert cmd.priority == Severity.CRITICAL
            assert cmd.zone_id == "bay-2"

    def test_fire_short_circuits_other_rules(self):
        """Even with frost + low water, fire overrides everything."""
        engine = FlightRulesEngine()
        zone = _zone(
            zone_id="bay-2",
            temperature=2.0,
            water_level=5.0,
            fire_detected=True,
        )

        commands, decisions = engine.evaluate(zone)

        # Only fire-related commands — no heater ON, no water alerts
        actions = {c.action for c in commands}
        assert actions == {"off"}, f"Non-off actions found during fire: {actions}"

        # Single emergency decision
        assert len(decisions) == 1
        assert decisions[0].result == "emergency_shutdown"


# ── Scenario 5: Dust Storm Power Drop ────────────────────────────────────


class TestDustStormPowerDrop:
    """Solar efficiency at 40% → FR-E-001 power rationing via evaluate()."""

    def test_power_rationing_via_evaluate(self):
        engine = FlightRulesEngine()
        zone = _zone()
        energy = _energy(efficiency=0.40)

        commands, decisions = engine.evaluate(zone, energy=energy)

        # FR-E-001 should fire — light device, power_rationing action
        rationing_cmds = [c for c in commands if c.action == "power_rationing"]
        assert len(rationing_cmds) == 1
        assert rationing_cmds[0].priority == Severity.HIGH

    def test_power_rationing_via_dedicated_method(self):
        engine = FlightRulesEngine()
        energy = _energy(efficiency=0.40)

        decisions = engine.evaluate_energy(energy)

        assert len(decisions) == 1
        assert decisions[0].action == "power_rationing_on"
        assert decisions[0].severity == Severity.HIGH
        assert "40%" in decisions[0].reasoning


# ── Scenario 6: CO2 Buildup ──────────────────────────────────────────────


class TestCO2Buildup:
    """Greenhouse CO2 at 5500ppm → FR-G-001 ventilation increase."""

    def test_ventilation_increase_via_evaluate(self):
        engine = FlightRulesEngine()
        zone = _zone()
        gas = _gas(co2_ppm=5500.0)

        commands, decisions = engine.evaluate(zone, gas=gas)

        fan_cmds = [c for c in commands if c.device == DeviceType.FAN]
        assert len(fan_cmds) >= 1

        co2_cmd = next(c for c in fan_cmds if "FR-G-001" in c.command_id)
        assert co2_cmd.action == "on"
        assert co2_cmd.value == 100.0
        assert co2_cmd.priority == Severity.CRITICAL

    def test_co2_via_dedicated_method(self):
        engine = FlightRulesEngine()
        gas = _gas(co2_ppm=5500.0)

        decisions = engine.evaluate_gas(gas)

        assert len(decisions) == 1
        assert decisions[0].severity == Severity.CRITICAL
        assert "5500" in decisions[0].reasoning


# ── Scenario 7: Multi-Rule Cascade ───────────────────────────────────────


class TestMultiRuleCascade:
    """Temp 3°C AND humidity 95% → both heater AND fan fire simultaneously."""

    def test_both_heater_and_fan_fire(self):
        engine = FlightRulesEngine()
        zone = _zone(temperature=3.0, humidity=95.0)

        commands, decisions = engine.evaluate(zone)

        devices_activated = {c.device for c in commands}
        assert DeviceType.HEATER in devices_activated, "Heater must fire for 3°C"
        assert DeviceType.FAN in devices_activated, "Fan must fire for 95% humidity"

    def test_cascade_correct_values(self):
        engine = FlightRulesEngine()
        zone = _zone(temperature=3.0, humidity=95.0)

        commands, _ = engine.evaluate(zone)

        heater = next(c for c in commands if c.device == DeviceType.HEATER)
        fan = next(c for c in commands if c.device == DeviceType.FAN)

        assert heater.value == 100.0  # FR-T-001: full blast
        assert fan.value == 50.0      # FR-H-001: 50% ventilation
        assert heater.priority == Severity.CRITICAL
        assert fan.priority == Severity.MEDIUM

    def test_cascade_produces_multiple_decisions(self):
        engine = FlightRulesEngine()
        zone = _zone(temperature=3.0, humidity=95.0)

        _, decisions = engine.evaluate(zone)

        assert len(decisions) >= 2, "Both frost and humidity rules should produce decisions"


# ── Scenario 8: Normal Operations ────────────────────────────────────────


class TestNormalOperations:
    """Everything in range → NO commands issued (don't over-actuate)."""

    def test_no_commands_when_normal(self):
        engine = FlightRulesEngine()
        zone = _zone(
            temperature=22.0,
            humidity=55.0,
            light=500.0,
            water_level=50.0,
        )
        energy = _energy(efficiency=0.85)
        gas = _gas(co2_ppm=800.0)

        commands, decisions = engine.evaluate(zone, energy=energy, gas=gas)

        assert len(commands) == 0, (
            f"Normal conditions should produce zero commands, got: "
            f"{[(c.device.value, c.action) for c in commands]}"
        )
        assert len(decisions) == 0

    def test_boundary_values_do_not_trigger(self):
        """Values exactly AT thresholds should NOT fire (strict inequalities)."""
        engine = FlightRulesEngine()
        # temp=5.0 is NOT < 5.0, humidity=90.0 is NOT > 90.0, etc.
        # water_level=30.0 avoids FR-W-010 (lt 30.0) and FR-W-001 (lt 10.0)
        zone = _zone(
            temperature=5.0,
            humidity=90.0,
            light=100.0,
            water_level=30.0,
        )

        commands, decisions = engine.evaluate(zone)

        assert len(commands) == 0, (
            f"Boundary values should NOT trigger rules, got: "
            f"{[(c.device.value, c.action) for c in commands]}"
        )
