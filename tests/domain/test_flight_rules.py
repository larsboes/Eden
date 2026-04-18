"""Tests for eden.domain.flight_rules — written BEFORE implementation (TDD)."""

import time
import pytest

from eden.domain.models import (
    SensorType,
    DeviceType,
    Severity,
    Tier,
    FlightRule,
    ZoneState,
    ActuatorCommand,
    AgentDecision,
    EnergyBudget,
    GasExchange,
    MarsConditions,
    ResourceBudget,
)
from eden.domain.flight_rules import FlightRulesEngine, DEFAULT_FLIGHT_RULES, get_default_rules


# ── Helpers ──────────────────────────────────────────────────────────────


def make_zone(
    zone_id: str = "alpha",
    temperature: float = 22.0,
    humidity: float = 60.0,
    pressure: float = 1013.0,
    light: float = 500.0,
    water_level: float = 80.0,
    fire_detected: bool = False,
    last_updated: float | None = None,
) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        light=light,
        water_level=water_level,
        fire_detected=fire_detected,
        last_updated=last_updated if last_updated is not None else time.time(),
        is_alive=True,
        source="test",
    )


def _make_energy(efficiency: float = 0.85) -> EnergyBudget:
    return EnergyBudget(
        solar_capacity_kw=12.0,
        current_efficiency=efficiency,
        allocations={"lights": 3.0},
        reserve_kw=1.5,
    )


def _make_gas(co2: float = 800.0, o2: float = 21.0) -> GasExchange:
    return GasExchange(
        greenhouse_co2_ppm=co2,
        greenhouse_o2_pct=o2,
        habitat_co2_ppm=400.0,
        habitat_o2_pct=20.9,
        exchange_rate=0.5,
    )


def _make_mars(radiation_alert: bool = False) -> MarsConditions:
    return MarsConditions(
        exterior_temp=-60.0,
        dome_temp=18.0,
        pressure_hpa=700.0,
        solar_irradiance=590.0,
        dust_opacity=0.3,
        sol=42,
        storm_active=False,
        radiation_alert=radiation_alert,
    )


def _make_resource(nutrient_level: float = 50.0, capacity: float = 80.0) -> ResourceBudget:
    return ResourceBudget(
        water_liters=500.0,
        nutrient_level=nutrient_level,
        current_capacity=capacity,
    )


# ── Engine Construction ─────────────────────────────────────────────────


class TestFlightRulesEngineConstruction:
    def test_default_rules_loaded(self):
        engine = FlightRulesEngine()
        assert len(engine.rules) > 0

    def test_custom_rules(self):
        rules = [
            FlightRule(
                rule_id="CUSTOM-001",
                sensor_type=SensorType.TEMPERATURE,
                condition="gt",
                threshold=40.0,
                device=DeviceType.FAN,
                action="on",
                value=100.0,
                cooldown_seconds=30,
                priority=Severity.HIGH,
            )
        ]
        engine = FlightRulesEngine(rules=rules)
        assert len(engine.rules) == 1

    def test_default_rules_cover_all_scenarios(self):
        """Ensure all documented rules exist in defaults."""
        rule_ids = {r.rule_id for r in DEFAULT_FLIGHT_RULES}
        expected = {
            "FR-T-001", "FR-T-002",
            "FR-H-001", "FR-H-002",
            "FR-W-001",
            "FR-F-001",
            "FR-L-001",
            "FR-E-001",
            "FR-G-001",
            "FR-W-010",
            # New safety rules
            "FR-P-001",
            "FR-O2-001", "FR-O2-002",
            "FR-STALE-001",
            "FR-RAD-001",
            "FR-RATE-001",
            "FR-N-001",
        }
        assert expected.issubset(rule_ids)

    def test_get_default_rules_returns_all(self):
        rules = get_default_rules()
        assert len(rules) == 17
        rule_ids = {r.rule_id for r in rules}
        assert "FR-F-001" in rule_ids
        assert "FR-P-001" in rule_ids
        assert "FR-O2-001" in rule_ids
        assert "FR-N-001" in rule_ids


# ── Environmental Rule Tests ────────────────────────────────────────────


class TestFrostProtection:
    """FR-T-001: temp < 5 C -> heater ON 100%."""

    def test_triggers_on_cold(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=3.0)
        commands, decisions = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER]
        assert len(heater_cmds) == 1
        assert heater_cmds[0].action == "on"
        assert heater_cmds[0].value == 100.0
        assert heater_cmds[0].priority == Severity.CRITICAL

    def test_no_trigger_normal_temp(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=22.0)
        commands, decisions = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER and c.action == "on"]
        assert len(heater_cmds) == 0

    def test_boundary_exactly_5(self):
        """Exactly 5 C should NOT trigger (condition is < 5)."""
        engine = FlightRulesEngine()
        zone = make_zone(temperature=5.0)
        commands, _ = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER and c.action == "on"]
        assert len(heater_cmds) == 0

    def test_boundary_just_below_5(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=4.99)
        commands, _ = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER and c.action == "on"]
        assert len(heater_cmds) == 1


class TestHeatStress:
    """FR-T-002: temp > 35 C -> fan ON 100%."""

    def test_triggers_on_hot(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=38.0)
        commands, decisions = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 100.0]
        assert len(fan_cmds) >= 1

    def test_no_trigger_normal_temp(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=25.0)
        commands, decisions = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 100.0]
        assert len(fan_cmds) == 0

    def test_boundary_exactly_35(self):
        """Exactly 35 C should NOT trigger (condition is > 35)."""
        engine = FlightRulesEngine()
        zone = make_zone(temperature=35.0)
        commands, _ = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 100.0]
        assert len(fan_cmds) == 0


class TestHighHumidity:
    """FR-H-001: humidity > 90% -> fan ON 50%."""

    def test_triggers_on_high_humidity(self):
        engine = FlightRulesEngine()
        zone = make_zone(humidity=95.0)
        commands, _ = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 50.0]
        assert len(fan_cmds) >= 1

    def test_no_trigger_normal_humidity(self):
        engine = FlightRulesEngine()
        zone = make_zone(humidity=60.0)
        commands, _ = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 50.0]
        assert len(fan_cmds) == 0

    def test_boundary_exactly_90(self):
        engine = FlightRulesEngine()
        zone = make_zone(humidity=90.0)
        commands, _ = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN and c.value == 50.0]
        assert len(fan_cmds) == 0


class TestLowHumidity:
    """FR-H-002: humidity < 30% -> pump ON."""

    def test_triggers_on_low_humidity(self):
        engine = FlightRulesEngine()
        zone = make_zone(humidity=25.0)
        commands, _ = engine.evaluate(zone)
        pump_cmds = [c for c in commands if c.device == DeviceType.PUMP and c.action == "on"]
        assert len(pump_cmds) >= 1

    def test_boundary_exactly_30(self):
        engine = FlightRulesEngine()
        zone = make_zone(humidity=30.0)
        commands, _ = engine.evaluate(zone)
        pump_cmds = [c for c in commands if c.device == DeviceType.PUMP and c.action == "on"]
        assert len(pump_cmds) == 0


class TestDryReservoir:
    """FR-W-001: water_level < 10mm -> pump OFF + alert CRITICAL."""

    def test_triggers_on_low_water(self):
        engine = FlightRulesEngine()
        zone = make_zone(water_level=5.0)
        commands, decisions = engine.evaluate(zone)
        pump_off = [c for c in commands if c.device == DeviceType.PUMP and c.action == "off"]
        assert len(pump_off) >= 1
        critical_decisions = [d for d in decisions if d.severity == Severity.CRITICAL]
        assert len(critical_decisions) >= 1

    def test_boundary_exactly_10(self):
        engine = FlightRulesEngine()
        zone = make_zone(water_level=10.0)
        commands, _ = engine.evaluate(zone)
        pump_off = [c for c in commands if c.device == DeviceType.PUMP and c.action == "off"]
        assert len(pump_off) == 0


class TestFireDetected:
    """FR-F-001: fire detected -> ALL OFF + alert CRITICAL. Short-circuits."""

    def test_triggers_on_fire(self):
        engine = FlightRulesEngine()
        zone = make_zone(fire_detected=True)
        commands, decisions = engine.evaluate(zone)
        # Should have commands to turn off multiple devices
        off_cmds = [c for c in commands if c.action == "off"]
        assert len(off_cmds) >= 3  # fan, light, pump, heater, motor
        # All should be critical
        for cmd in off_cmds:
            assert cmd.priority == Severity.CRITICAL
        # Should have a critical decision
        critical = [d for d in decisions if d.severity == Severity.CRITICAL]
        assert len(critical) >= 1

    def test_fire_short_circuits(self):
        """Fire with other conditions -- fire commands should dominate."""
        engine = FlightRulesEngine()
        # Fire + cold + low humidity -- fire should short-circuit
        zone = make_zone(fire_detected=True, temperature=3.0, humidity=25.0)
        commands, _ = engine.evaluate(zone)
        # All commands should be "off" -- fire overrides everything
        for cmd in commands:
            assert cmd.action == "off"

    def test_fire_turns_off_all_device_types(self):
        engine = FlightRulesEngine()
        zone = make_zone(fire_detected=True)
        commands, _ = engine.evaluate(zone)
        devices_off = {c.device for c in commands}
        for device in DeviceType:
            assert device in devices_off


class TestLowLight:
    """FR-L-001: light < 100 lux -> light ON."""

    def test_triggers_on_low_light(self):
        engine = FlightRulesEngine()
        zone = make_zone(light=50.0)
        commands, _ = engine.evaluate(zone)
        light_cmds = [c for c in commands if c.device == DeviceType.LIGHT and c.action == "on"]
        assert len(light_cmds) >= 1

    def test_no_trigger_adequate_light(self):
        engine = FlightRulesEngine()
        zone = make_zone(light=500.0)
        commands, _ = engine.evaluate(zone)
        light_cmds = [c for c in commands if c.device == DeviceType.LIGHT and c.action == "on"]
        assert len(light_cmds) == 0

    def test_boundary_exactly_100(self):
        engine = FlightRulesEngine()
        zone = make_zone(light=100.0)
        commands, _ = engine.evaluate(zone)
        light_cmds = [c for c in commands if c.device == DeviceType.LIGHT and c.action == "on"]
        assert len(light_cmds) == 0


# ── Energy / Gas / Water Rationing via evaluate() ─────────────────────


class TestEnergyRuleViaEvaluate:
    """FR-E-001: solar efficiency < 50% -> power rationing mode."""

    def test_triggers_low_efficiency(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        energy = _make_energy(efficiency=0.3)
        commands, decisions = engine.evaluate(zone, energy=energy)
        rationing = [d for d in decisions if "rationing" in d.action.lower() or "rationing" in d.reasoning.lower()]
        assert len(rationing) >= 1

    def test_no_trigger_normal_efficiency(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        energy = _make_energy(efficiency=0.85)
        commands, decisions = engine.evaluate(zone, energy=energy)
        rationing = [d for d in decisions if "rationing" in d.action.lower() or "rationing" in d.reasoning.lower()]
        assert len(rationing) == 0

    def test_boundary_exactly_50_percent(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        energy = _make_energy(efficiency=0.5)
        commands, decisions = engine.evaluate(zone, energy=energy)
        rationing = [d for d in decisions if "rationing" in d.action.lower() or "rationing" in d.reasoning.lower()]
        assert len(rationing) == 0

    def test_no_energy_param_skips_rule(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        commands, decisions = engine.evaluate(zone)
        rationing = [d for d in decisions if "rationing" in d.action.lower()]
        assert len(rationing) == 0


class TestGasRuleViaEvaluate:
    """FR-G-001: CO2 > 5000ppm -> increase ventilation."""

    def test_triggers_high_co2(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(co2=6000.0)
        commands, decisions = engine.evaluate(zone, gas=gas)
        vent = [c for c in commands if c.device == DeviceType.FAN]
        assert len(vent) >= 1

    def test_no_trigger_normal_co2(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(co2=800.0)
        commands, decisions = engine.evaluate(zone, gas=gas)
        # Should be no fan commands from gas rule (normal zone has normal readings)
        gas_fan = [d for d in decisions if "co2" in d.reasoning.lower() or "ventilation" in d.action.lower()]
        assert len(gas_fan) == 0

    def test_boundary_exactly_5000(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(co2=5000.0)
        commands, decisions = engine.evaluate(zone, gas=gas)
        gas_decisions = [d for d in decisions if "co2" in d.reasoning.lower()]
        assert len(gas_decisions) == 0

    def test_no_gas_param_skips_rule(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        commands, decisions = engine.evaluate(zone)
        vent = [d for d in decisions if "ventilation" in d.action.lower()]
        assert len(vent) == 0


class TestWaterRationingViaEvaluate:
    """FR-W-010: water_level < 30 -> rationing mode."""

    def test_triggers_low_water(self):
        engine = FlightRulesEngine()
        zone = make_zone(water_level=25.0)
        commands, decisions = engine.evaluate(zone)
        rationing = [d for d in decisions if "rationing" in d.reasoning.lower() or "rationing" in d.action.lower()]
        assert len(rationing) >= 1

    def test_no_trigger_normal_water(self):
        engine = FlightRulesEngine()
        zone = make_zone(water_level=80.0)
        commands, decisions = engine.evaluate(zone)
        rationing = [d for d in decisions if "rationing" in d.action.lower()]
        assert len(rationing) == 0

    def test_boundary_exactly_30(self):
        engine = FlightRulesEngine()
        zone = make_zone(water_level=30.0)
        commands, decisions = engine.evaluate(zone)
        rationing = [d for d in decisions if "rationing" in d.action.lower()]
        assert len(rationing) == 0


# ── Cooldown Tests ───────────────────────────────────────────────────────


class TestCooldown:
    def test_cooldown_prevents_repeated_fire(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=3.0)
        # First evaluation -- should trigger
        commands1, _ = engine.evaluate(zone)
        assert len(commands1) > 0
        # Second evaluation immediately -- should be suppressed by cooldown
        commands2, _ = engine.evaluate(zone)
        heater_cmds = [c for c in commands2 if c.device == DeviceType.HEATER]
        assert len(heater_cmds) == 0

    def test_cooldown_expires(self):
        # Use a rule with 0s cooldown
        rules = [
            FlightRule(
                rule_id="TEST-001",
                sensor_type=SensorType.TEMPERATURE,
                condition="lt",
                threshold=5.0,
                device=DeviceType.HEATER,
                action="on",
                value=100.0,
                cooldown_seconds=0,
                priority=Severity.CRITICAL,
            )
        ]
        engine = FlightRulesEngine(rules=rules)
        zone = make_zone(temperature=3.0)
        commands1, _ = engine.evaluate(zone)
        assert len(commands1) == 1
        # With 0s cooldown, should fire again immediately
        commands2, _ = engine.evaluate(zone)
        assert len(commands2) == 1


# ── Multiple Rules Fire Simultaneously ───────────────────────────────────


class TestMultipleRules:
    def test_cold_and_low_light_both_fire(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=3.0, light=50.0)
        commands, decisions = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER]
        light_cmds = [c for c in commands if c.device == DeviceType.LIGHT]
        assert len(heater_cmds) >= 1
        assert len(light_cmds) >= 1
        assert len(decisions) >= 2

    def test_hot_and_humid_both_fire(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=38.0, humidity=95.0)
        commands, decisions = engine.evaluate(zone)
        fan_cmds = [c for c in commands if c.device == DeviceType.FAN]
        # Both heat stress (100%) and mold risk (50%) should fire
        assert len(fan_cmds) >= 2


# ── Disabled Rules ───────────────────────────────────────────────────────


class TestDisabledRules:
    def test_disabled_rule_does_not_fire(self):
        rules = [
            FlightRule(
                rule_id="DISABLED-001",
                sensor_type=SensorType.TEMPERATURE,
                condition="lt",
                threshold=5.0,
                device=DeviceType.HEATER,
                action="on",
                value=100.0,
                cooldown_seconds=0,
                priority=Severity.CRITICAL,
                enabled=False,
            )
        ]
        engine = FlightRulesEngine(rules=rules)
        zone = make_zone(temperature=3.0)
        commands, _ = engine.evaluate(zone)
        assert len(commands) == 0


# ── Propose Flight Rule (Self-Improvement) ──────────────────────────────


class TestProposeFlightRule:
    def test_propose_stores_candidate(self):
        engine = FlightRulesEngine()
        candidate = FlightRule(
            rule_id="PROPOSED-001",
            sensor_type=SensorType.PRESSURE,
            condition="lt",
            threshold=900.0,
            device=DeviceType.FAN,
            action="on",
            value=50.0,
            cooldown_seconds=120,
            priority=Severity.MEDIUM,
            enabled=False,
        )
        engine.propose_flight_rule(candidate)
        assert candidate in engine.get_candidates()

    def test_proposed_rule_not_active(self):
        engine = FlightRulesEngine()
        candidate = FlightRule(
            rule_id="PROPOSED-002",
            sensor_type=SensorType.TEMPERATURE,
            condition="lt",
            threshold=10.0,
            device=DeviceType.HEATER,
            action="on",
            value=100.0,
            cooldown_seconds=0,
            priority=Severity.HIGH,
        )
        engine.propose_flight_rule(candidate)
        # Candidate should NOT be in active rules
        assert candidate not in engine.rules
        # Should not trigger on evaluation
        zone = make_zone(temperature=8.0)
        commands, _ = engine.evaluate(zone)
        heater_cmds = [c for c in commands if c.device == DeviceType.HEATER]
        assert len(heater_cmds) == 0

    def test_get_candidates_returns_list(self):
        engine = FlightRulesEngine()
        assert engine.get_candidates() == []
        candidate = FlightRule(
            rule_id="PROPOSED-003",
            sensor_type=SensorType.TEMPERATURE,
            condition="gt",
            threshold=40.0,
            device=DeviceType.FAN,
            action="on",
            value=100.0,
            cooldown_seconds=60,
            priority=Severity.HIGH,
        )
        engine.propose_flight_rule(candidate)
        candidates = engine.get_candidates()
        assert len(candidates) == 1
        assert candidates[0].rule_id == "PROPOSED-003"


# ── Decision Logging ────────────────────────────────────────────────────


class TestDecisionLogging:
    def test_every_triggered_rule_produces_a_decision(self):
        engine = FlightRulesEngine()
        zone = make_zone(temperature=3.0)
        commands, decisions = engine.evaluate(zone)
        assert len(decisions) >= 1
        for d in decisions:
            assert d.tier == Tier.FLIGHT_RULES
            assert d.agent_name == "FLIGHT_RULES"
            assert d.zone_id == zone.zone_id

    def test_normal_zone_produces_no_decisions(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        commands, decisions = engine.evaluate(zone)
        assert len(commands) == 0
        assert len(decisions) == 0


# ── Resource Rule Tests (separate methods kept for compat) ──────────────


class TestResourceRules:
    def test_evaluate_energy_low_efficiency(self):
        engine = FlightRulesEngine()
        energy = EnergyBudget(
            solar_capacity_kw=12.0,
            current_efficiency=0.3,
            allocations={"lights": 3.0},
            reserve_kw=1.5,
        )
        decisions = engine.evaluate_energy(energy)
        assert len(decisions) >= 1
        assert any(d.severity == Severity.HIGH for d in decisions)

    def test_evaluate_energy_normal(self):
        engine = FlightRulesEngine()
        energy = EnergyBudget(
            solar_capacity_kw=12.0,
            current_efficiency=0.85,
            allocations={"lights": 3.0},
            reserve_kw=1.5,
        )
        decisions = engine.evaluate_energy(energy)
        assert len(decisions) == 0

    def test_evaluate_gas_high_co2(self):
        engine = FlightRulesEngine()
        gas = GasExchange(
            greenhouse_co2_ppm=6000.0,
            greenhouse_o2_pct=21.0,
            habitat_co2_ppm=400.0,
            habitat_o2_pct=20.9,
            exchange_rate=0.5,
        )
        decisions = engine.evaluate_gas(gas)
        assert len(decisions) >= 1
        assert any(d.severity == Severity.CRITICAL for d in decisions)

    def test_evaluate_gas_normal(self):
        engine = FlightRulesEngine()
        gas = GasExchange(
            greenhouse_co2_ppm=800.0,
            greenhouse_o2_pct=21.0,
            habitat_co2_ppm=400.0,
            habitat_o2_pct=20.9,
            exchange_rate=0.5,
        )
        decisions = engine.evaluate_gas(gas)
        assert len(decisions) == 0

    def test_evaluate_water_low(self):
        engine = FlightRulesEngine()
        water = ResourceBudget(
            water_liters=100.0,
            nutrient_level=50.0,
            current_capacity=25.0,
        )
        decisions = engine.evaluate_water(water)
        assert len(decisions) >= 1
        assert any(d.severity == Severity.HIGH for d in decisions)

    def test_evaluate_water_normal(self):
        engine = FlightRulesEngine()
        water = ResourceBudget(
            water_liters=500.0,
            nutrient_level=50.0,
            current_capacity=80.0,
        )
        decisions = engine.evaluate_water(water)
        assert len(decisions) == 0


# ══════════════════════════════════════════════════════════════════════════
# NEW SAFETY RULE TESTS
# ══════════════════════════════════════════════════════════════════════════


# ── FR-P-001: Pressure Loss ─────────────────────────────────────────────


class TestPressureLoss:
    """FR-P-001: pressure < 600 hPa → CRITICAL alert + seal habitat."""

    def test_triggers_on_low_pressure(self):
        engine = FlightRulesEngine()
        zone = make_zone(pressure=500.0)
        commands, decisions = engine.evaluate(zone)
        seal_cmds = [c for c in commands if c.device == DeviceType.MOTOR and c.action == "seal_habitat"]
        assert len(seal_cmds) >= 1
        assert seal_cmds[0].priority == Severity.CRITICAL

    def test_no_trigger_normal_pressure(self):
        engine = FlightRulesEngine()
        zone = make_zone(pressure=700.0)
        commands, _ = engine.evaluate(zone)
        seal_cmds = [c for c in commands if c.action == "seal_habitat"]
        assert len(seal_cmds) == 0

    def test_boundary_exactly_600(self):
        """Exactly 600 hPa should NOT trigger (condition is < 600)."""
        engine = FlightRulesEngine()
        zone = make_zone(pressure=600.0)
        commands, _ = engine.evaluate(zone)
        seal_cmds = [c for c in commands if c.action == "seal_habitat"]
        assert len(seal_cmds) == 0

    def test_boundary_just_below_600(self):
        engine = FlightRulesEngine()
        zone = make_zone(pressure=599.9)
        commands, _ = engine.evaluate(zone)
        seal_cmds = [c for c in commands if c.action == "seal_habitat"]
        assert len(seal_cmds) == 1


# ── FR-O2-001: O2 Depletion ─────────────────────────────────────────────


class TestO2Depletion:
    """FR-O2-001: O2 < 18% → CRITICAL alert + increase gas exchange."""

    def test_triggers_on_low_o2_via_evaluate(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=16.0)
        commands, decisions = engine.evaluate(zone, gas=gas)
        exchange_cmds = [c for c in commands if c.action == "increase_exchange"]
        assert len(exchange_cmds) >= 1
        assert exchange_cmds[0].priority == Severity.CRITICAL

    def test_no_trigger_normal_o2(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=21.0)
        commands, _ = engine.evaluate(zone, gas=gas)
        exchange_cmds = [c for c in commands if c.action == "increase_exchange"]
        assert len(exchange_cmds) == 0

    def test_boundary_exactly_18(self):
        """Exactly 18% should NOT trigger (condition is < 18)."""
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=18.0)
        commands, _ = engine.evaluate(zone, gas=gas)
        exchange_cmds = [c for c in commands if c.action == "increase_exchange"]
        assert len(exchange_cmds) == 0

    def test_triggers_via_evaluate_gas(self):
        engine = FlightRulesEngine()
        gas = _make_gas(o2=16.0)
        decisions = engine.evaluate_gas(gas)
        o2_decisions = [d for d in decisions if "o2" in d.reasoning.lower() and "18" in d.reasoning]
        assert len(o2_decisions) >= 1
        assert o2_decisions[0].severity == Severity.CRITICAL

    def test_no_gas_param_skips_o2_rule(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        commands, _ = engine.evaluate(zone)
        exchange_cmds = [c for c in commands if c.action == "increase_exchange"]
        assert len(exchange_cmds) == 0


# ── FR-O2-002: O2 Excess (Fire Risk) ────────────────────────────────────


class TestO2Excess:
    """FR-O2-002: O2 > 25% → HIGH alert + reduce exchange."""

    def test_triggers_on_high_o2_via_evaluate(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=27.0)
        commands, decisions = engine.evaluate(zone, gas=gas)
        reduce_cmds = [c for c in commands if c.action == "reduce_exchange"]
        assert len(reduce_cmds) >= 1
        assert reduce_cmds[0].priority == Severity.HIGH

    def test_no_trigger_normal_o2(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=21.0)
        commands, _ = engine.evaluate(zone, gas=gas)
        reduce_cmds = [c for c in commands if c.action == "reduce_exchange"]
        assert len(reduce_cmds) == 0

    def test_boundary_exactly_25(self):
        """Exactly 25% should NOT trigger (condition is > 25)."""
        engine = FlightRulesEngine()
        zone = make_zone()
        gas = _make_gas(o2=25.0)
        commands, _ = engine.evaluate(zone, gas=gas)
        reduce_cmds = [c for c in commands if c.action == "reduce_exchange"]
        assert len(reduce_cmds) == 0

    def test_triggers_via_evaluate_gas(self):
        engine = FlightRulesEngine()
        gas = _make_gas(o2=27.0)
        decisions = engine.evaluate_gas(gas)
        o2_decisions = [d for d in decisions if "o2" in d.reasoning.lower() and "25" in d.reasoning]
        assert len(o2_decisions) >= 1
        assert o2_decisions[0].severity == Severity.HIGH


# ── FR-STALE-001: Stale Sensor Data ─────────────────────────────────────


class TestStaleSensorData:
    """FR-STALE-001: sensor data older than 60s → HIGH alert + mark compromised."""

    def test_triggers_on_stale_data(self):
        engine = FlightRulesEngine()
        now = time.time()
        zone = make_zone(last_updated=now - 120)  # 2 minutes old
        decisions = engine.evaluate_staleness(zone, now)
        assert len(decisions) >= 1
        assert decisions[0].severity == Severity.HIGH
        assert "compromised" in decisions[0].action.lower()

    def test_no_trigger_fresh_data(self):
        engine = FlightRulesEngine()
        now = time.time()
        zone = make_zone(last_updated=now - 10)  # 10 seconds old
        decisions = engine.evaluate_staleness(zone, now)
        assert len(decisions) == 0

    def test_boundary_exactly_60s(self):
        """Exactly 60s should NOT trigger (condition is > 60)."""
        engine = FlightRulesEngine()
        now = time.time()
        zone = make_zone(last_updated=now - 60)
        decisions = engine.evaluate_staleness(zone, now)
        assert len(decisions) == 0

    def test_boundary_just_over_60s(self):
        engine = FlightRulesEngine()
        now = time.time()
        zone = make_zone(last_updated=now - 61)
        decisions = engine.evaluate_staleness(zone, now)
        assert len(decisions) == 1

    def test_reports_correct_zone_id(self):
        engine = FlightRulesEngine()
        now = time.time()
        zone = make_zone(zone_id="bravo", last_updated=now - 120)
        decisions = engine.evaluate_staleness(zone, now)
        assert decisions[0].zone_id == "bravo"


# ── FR-RAD-001: Radiation Spike ──────────────────────────────────────────


class TestRadiationSpike:
    """FR-RAD-001: radiation_alert → HIGH alert + reduce light exposure."""

    def test_triggers_on_radiation_alert(self):
        engine = FlightRulesEngine()
        mars = _make_mars(radiation_alert=True)
        decisions = engine.evaluate_mars(mars)
        assert len(decisions) >= 1
        assert decisions[0].severity == Severity.HIGH
        assert "radiation" in decisions[0].reasoning.lower()

    def test_no_trigger_no_radiation(self):
        engine = FlightRulesEngine()
        mars = _make_mars(radiation_alert=False)
        decisions = engine.evaluate_mars(mars)
        assert len(decisions) == 0

    def test_decision_is_global(self):
        engine = FlightRulesEngine()
        mars = _make_mars(radiation_alert=True)
        decisions = engine.evaluate_mars(mars)
        assert decisions[0].zone_id == "global"


# ── FR-RATE-001: Rate of Change Detection ────────────────────────────────


class TestRateOfChange:
    """FR-RATE-001: temp changed >5°C in ≤5min → HIGH alert."""

    def test_triggers_on_rapid_temp_increase(self):
        engine = FlightRulesEngine()
        # First reading at 22°C
        zone1 = make_zone(temperature=22.0)
        engine.evaluate(zone1)
        # Simulate rapid change: inject past reading, then evaluate with new temp
        engine._last_readings["alpha"] = (22.0, time.time() - 60)  # 1 min ago
        zone2 = make_zone(temperature=30.0)  # +8°C in 1 min
        commands, decisions = engine.evaluate(zone2)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) >= 1
        assert rate_cmds[0].priority == Severity.HIGH

    def test_triggers_on_rapid_temp_decrease(self):
        engine = FlightRulesEngine()
        engine._last_readings["alpha"] = (30.0, time.time() - 60)
        zone = make_zone(temperature=22.0)  # -8°C in 1 min
        commands, _ = engine.evaluate(zone)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) >= 1

    def test_no_trigger_slow_change(self):
        engine = FlightRulesEngine()
        engine._last_readings["alpha"] = (22.0, time.time() - 60)
        zone = make_zone(temperature=24.0)  # +2°C in 1 min — within normal
        commands, _ = engine.evaluate(zone)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) == 0

    def test_no_trigger_first_reading(self):
        """First reading has no history — should not trigger."""
        engine = FlightRulesEngine()
        zone = make_zone(temperature=22.0)
        commands, _ = engine.evaluate(zone)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) == 0

    def test_no_trigger_outside_5min_window(self):
        """Change over >5 min shouldn't trigger (could be gradual)."""
        engine = FlightRulesEngine()
        engine._last_readings["alpha"] = (22.0, time.time() - 600)  # 10 min ago
        zone = make_zone(temperature=30.0)
        commands, _ = engine.evaluate(zone)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) == 0

    def test_boundary_exactly_5_degrees(self):
        """Exactly 5°C change should NOT trigger (condition is > 5)."""
        engine = FlightRulesEngine()
        engine._last_readings["alpha"] = (22.0, time.time() - 60)
        zone = make_zone(temperature=27.0)  # exactly +5°C
        commands, _ = engine.evaluate(zone)
        rate_cmds = [c for c in commands if c.action == "emergency_ventilation"]
        assert len(rate_cmds) == 0


# ── FR-N-001: Nutrient Toxicity ──────────────────────────────────────────


class TestNutrientToxicity:
    """FR-N-001: nutrient_level > 90 → MEDIUM alert + flush irrigation."""

    def test_triggers_on_high_nutrients_via_evaluate(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        resource = _make_resource(nutrient_level=95.0)
        commands, decisions = engine.evaluate(zone, resource=resource)
        flush_cmds = [c for c in commands if c.action == "flush_irrigation"]
        assert len(flush_cmds) >= 1
        assert flush_cmds[0].priority == Severity.MEDIUM

    def test_no_trigger_normal_nutrients(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        resource = _make_resource(nutrient_level=50.0)
        commands, _ = engine.evaluate(zone, resource=resource)
        flush_cmds = [c for c in commands if c.action == "flush_irrigation"]
        assert len(flush_cmds) == 0

    def test_boundary_exactly_90(self):
        """Exactly 90 should NOT trigger (condition is > 90)."""
        engine = FlightRulesEngine()
        zone = make_zone()
        resource = _make_resource(nutrient_level=90.0)
        commands, _ = engine.evaluate(zone, resource=resource)
        flush_cmds = [c for c in commands if c.action == "flush_irrigation"]
        assert len(flush_cmds) == 0

    def test_triggers_via_evaluate_nutrients(self):
        engine = FlightRulesEngine()
        resource = _make_resource(nutrient_level=95.0)
        decisions = engine.evaluate_nutrients(resource)
        assert len(decisions) >= 1
        assert decisions[0].severity == Severity.MEDIUM
        assert "nutrient" in decisions[0].reasoning.lower()

    def test_no_resource_param_skips_rule(self):
        engine = FlightRulesEngine()
        zone = make_zone()
        commands, _ = engine.evaluate(zone)
        flush_cmds = [c for c in commands if c.action == "flush_irrigation"]
        assert len(flush_cmds) == 0
