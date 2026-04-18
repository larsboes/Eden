"""Tests for eden.domain.models — written BEFORE implementation (TDD)."""

import time
import pytest
from dataclasses import FrozenInstanceError

from eden.domain.models import (
    SensorType,
    DeviceType,
    Severity,
    Tier,
    SensorReading,
    ActuatorCommand,
    AgentDecision,
    MarsConditions,
    ZoneState,
    DesiredState,
    CropProfile,
    CrewMember,
    ResourceBudget,
    EnergyBudget,
    GasExchange,
    FlightRule,
)


# ── Enum Tests ──────────────────────────────────────────────────────────


class TestSensorType:
    def test_values(self):
        assert SensorType.TEMPERATURE.value == "temperature"
        assert SensorType.HUMIDITY.value == "humidity"
        assert SensorType.PRESSURE.value == "pressure"
        assert SensorType.LIGHT.value == "light"
        assert SensorType.WATER_LEVEL.value == "water_level"
        assert SensorType.FIRE.value == "fire"

    def test_member_count(self):
        assert len(SensorType) == 6


class TestDeviceType:
    def test_values(self):
        assert DeviceType.FAN.value == "fan"
        assert DeviceType.LIGHT.value == "light"
        assert DeviceType.PUMP.value == "pump"
        assert DeviceType.HEATER.value == "heater"
        assert DeviceType.MOTOR.value == "motor"

    def test_member_count(self):
        assert len(DeviceType) == 5


class TestSeverity:
    def test_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_member_count(self):
        assert len(Severity) == 5


class TestTier:
    def test_values(self):
        assert Tier.FLIGHT_RULES.value == 0
        assert Tier.LOCAL_MODEL.value == 1
        assert Tier.CLOUD_MODEL.value == 2

    def test_member_count(self):
        assert len(Tier) == 3


# ── Frozen (Value Object) Tests ─────────────────────────────────────────


class TestSensorReading:
    @pytest.fixture
    def reading(self):
        return SensorReading(
            zone_id="alpha",
            sensor_type=SensorType.TEMPERATURE,
            value=23.5,
            unit="celsius",
            timestamp=1710812345.123,
            source="rpi-01",
        )

    def test_creation(self, reading):
        assert reading.zone_id == "alpha"
        assert reading.sensor_type == SensorType.TEMPERATURE
        assert reading.value == 23.5
        assert reading.unit == "celsius"
        assert reading.timestamp == 1710812345.123
        assert reading.source == "rpi-01"

    def test_frozen(self, reading):
        with pytest.raises(FrozenInstanceError):
            reading.value = 99.0

    def test_to_dict(self, reading):
        d = reading.to_dict()
        assert d["zone_id"] == "alpha"
        assert d["sensor_type"] == "temperature"
        assert d["value"] == 23.5
        assert d["unit"] == "celsius"
        assert d["timestamp"] == 1710812345.123
        assert d["source"] == "rpi-01"

    def test_from_dict_roundtrip(self, reading):
        d = reading.to_dict()
        restored = SensorReading.from_dict(d)
        assert restored == reading

    def test_from_dict_with_raw_values(self):
        d = {
            "zone_id": "beta",
            "sensor_type": "humidity",
            "value": 65.0,
            "unit": "percent",
            "timestamp": 100.0,
            "source": "sim",
        }
        r = SensorReading.from_dict(d)
        assert r.sensor_type == SensorType.HUMIDITY


class TestActuatorCommand:
    @pytest.fixture
    def command(self):
        return ActuatorCommand(
            command_id="cmd-001",
            zone_id="alpha",
            device=DeviceType.FAN,
            action="on",
            value=75.0,
            reason="Temperature above target",
            priority=Severity.MEDIUM,
            timestamp=1710812350.0,
        )

    def test_creation(self, command):
        assert command.command_id == "cmd-001"
        assert command.device == DeviceType.FAN
        assert command.action == "on"
        assert command.value == 75.0
        assert command.priority == Severity.MEDIUM

    def test_frozen(self, command):
        with pytest.raises(FrozenInstanceError):
            command.action = "off"

    def test_to_dict(self, command):
        d = command.to_dict()
        assert d["device"] == "fan"
        assert d["priority"] == "medium"

    def test_from_dict_roundtrip(self, command):
        d = command.to_dict()
        restored = ActuatorCommand.from_dict(d)
        assert restored == command


class TestAgentDecision:
    @pytest.fixture
    def decision(self):
        return AgentDecision(
            timestamp=1710812400.0,
            agent_name="DEMETER",
            severity=Severity.HIGH,
            reasoning="Humidity too low for tomatoes",
            action="activate_pump",
            result="pump_on_50",
            zone_id="alpha",
            tier=Tier.CLOUD_MODEL,
        )

    def test_creation(self, decision):
        assert decision.agent_name == "DEMETER"
        assert decision.tier == Tier.CLOUD_MODEL

    def test_frozen(self, decision):
        with pytest.raises(FrozenInstanceError):
            decision.result = "failed"

    def test_to_dict(self, decision):
        d = decision.to_dict()
        assert d["severity"] == "high"
        assert d["tier"] == 2

    def test_from_dict_roundtrip(self, decision):
        d = decision.to_dict()
        restored = AgentDecision.from_dict(d)
        assert restored == decision


class TestMarsConditions:
    @pytest.fixture
    def conditions(self):
        return MarsConditions(
            exterior_temp=-60.0,
            dome_temp=22.0,
            pressure_hpa=6.36,
            solar_irradiance=590.0,
            dust_opacity=0.5,
            sol=142,
            storm_active=False,
            radiation_alert=False,
        )

    def test_creation(self, conditions):
        assert conditions.exterior_temp == -60.0
        assert conditions.sol == 142
        assert conditions.storm_active is False

    def test_frozen(self, conditions):
        with pytest.raises(FrozenInstanceError):
            conditions.storm_active = True

    def test_to_dict(self, conditions):
        d = conditions.to_dict()
        assert d["exterior_temp"] == -60.0
        assert d["sol"] == 142

    def test_from_dict_roundtrip(self, conditions):
        d = conditions.to_dict()
        restored = MarsConditions.from_dict(d)
        assert restored == conditions


# ── Mutable Entity Tests ────────────────────────────────────────────────


class TestZoneState:
    @pytest.fixture
    def zone(self):
        return ZoneState(
            zone_id="alpha",
            temperature=23.5,
            humidity=65.0,
            pressure=1013.0,
            light=450.0,
            water_level=85.0,
            fire_detected=False,
            last_updated=1710812345.0,
            is_alive=True,
            source="rpi-01",
        )

    def test_creation(self, zone):
        assert zone.zone_id == "alpha"
        assert zone.temperature == 23.5
        assert zone.is_alive is True

    def test_mutable(self, zone):
        zone.temperature = 25.0
        assert zone.temperature == 25.0

    def test_to_dict(self, zone):
        d = zone.to_dict()
        assert d["zone_id"] == "alpha"
        assert d["fire_detected"] is False

    def test_from_dict_roundtrip(self, zone):
        d = zone.to_dict()
        restored = ZoneState.from_dict(d)
        assert restored.zone_id == zone.zone_id
        assert restored.temperature == zone.temperature


class TestDesiredState:
    @pytest.fixture
    def desired(self):
        return DesiredState(
            zone_id="alpha",
            temp_min=18.0,
            temp_max=28.0,
            humidity_min=50.0,
            humidity_max=80.0,
            light_hours=16.0,
            soil_moisture_min=30.0,
            soil_moisture_max=70.0,
            water_budget_liters_per_day=5.0,
        )

    def test_creation(self, desired):
        assert desired.temp_min == 18.0
        assert desired.light_hours == 16.0

    def test_mutable(self, desired):
        desired.temp_max = 30.0
        assert desired.temp_max == 30.0

    def test_to_dict(self, desired):
        d = desired.to_dict()
        assert d["water_budget_liters_per_day"] == 5.0

    def test_from_dict_roundtrip(self, desired):
        d = desired.to_dict()
        restored = DesiredState.from_dict(d)
        assert restored.zone_id == desired.zone_id
        assert restored.temp_min == desired.temp_min


class TestCropProfile:
    @pytest.fixture
    def crop(self):
        return CropProfile(
            name="tomato",
            zone_id="alpha",
            calories_per_kg=180.0,
            protein_per_kg=9.0,
            growth_days=90,
            yield_kg_per_m2=4.5,
            temp_min=18.0,
            temp_max=30.0,
            humidity_min=50.0,
            humidity_max=80.0,
        )

    def test_creation(self, crop):
        assert crop.name == "tomato"
        assert crop.growth_days == 90

    def test_to_dict(self, crop):
        d = crop.to_dict()
        assert d["name"] == "tomato"
        assert d["yield_kg_per_m2"] == 4.5

    def test_from_dict_roundtrip(self, crop):
        d = crop.to_dict()
        restored = CropProfile.from_dict(d)
        assert restored.name == crop.name
        assert restored.growth_days == crop.growth_days


class TestCrewMember:
    def test_creation_with_defaults(self):
        crew = CrewMember(
            name="Alex",
            daily_kcal_target=2500.0,
            daily_protein_target=60.0,
        )
        assert crew.current_kcal_intake == 0.0
        assert crew.current_protein_intake == 0.0

    def test_creation_with_values(self):
        crew = CrewMember(
            name="Alex",
            daily_kcal_target=2500.0,
            daily_protein_target=60.0,
            current_kcal_intake=1200.0,
            current_protein_intake=30.0,
        )
        assert crew.current_kcal_intake == 1200.0

    def test_mutable(self):
        crew = CrewMember(name="Alex", daily_kcal_target=2500.0, daily_protein_target=60.0)
        crew.current_kcal_intake = 500.0
        assert crew.current_kcal_intake == 500.0

    def test_to_dict(self):
        crew = CrewMember(name="Alex", daily_kcal_target=2500.0, daily_protein_target=60.0)
        d = crew.to_dict()
        assert d["name"] == "Alex"
        assert d["current_kcal_intake"] == 0.0

    def test_from_dict_roundtrip(self):
        crew = CrewMember(
            name="Alex",
            daily_kcal_target=2500.0,
            daily_protein_target=60.0,
            current_kcal_intake=800.0,
            current_protein_intake=20.0,
        )
        d = crew.to_dict()
        restored = CrewMember.from_dict(d)
        assert restored.name == crew.name
        assert restored.current_kcal_intake == crew.current_kcal_intake


class TestResourceBudget:
    @pytest.fixture
    def budget(self):
        return ResourceBudget(
            water_liters=500.0,
            nutrient_level=75.0,
            current_capacity=80.0,
        )

    def test_creation(self, budget):
        assert budget.water_liters == 500.0
        assert budget.nutrient_level == 75.0

    def test_to_dict(self, budget):
        d = budget.to_dict()
        assert d["current_capacity"] == 80.0

    def test_from_dict_roundtrip(self, budget):
        d = budget.to_dict()
        restored = ResourceBudget.from_dict(d)
        assert restored.water_liters == budget.water_liters


class TestEnergyBudget:
    @pytest.fixture
    def energy(self):
        return EnergyBudget(
            solar_capacity_kw=12.0,
            current_efficiency=0.85,
            allocations={"lights": 3.0, "pumps": 2.0, "heaters": 4.0},
            reserve_kw=1.5,
        )

    def test_creation(self, energy):
        assert energy.solar_capacity_kw == 12.0
        assert energy.allocations["lights"] == 3.0

    def test_mutable(self, energy):
        energy.current_efficiency = 0.5
        assert energy.current_efficiency == 0.5

    def test_to_dict(self, energy):
        d = energy.to_dict()
        assert d["allocations"]["pumps"] == 2.0

    def test_from_dict_roundtrip(self, energy):
        d = energy.to_dict()
        restored = EnergyBudget.from_dict(d)
        assert restored.allocations == energy.allocations
        assert restored.reserve_kw == energy.reserve_kw


class TestGasExchange:
    @pytest.fixture
    def gas(self):
        return GasExchange(
            greenhouse_co2_ppm=800.0,
            greenhouse_o2_pct=21.0,
            habitat_co2_ppm=400.0,
            habitat_o2_pct=20.9,
            exchange_rate=0.5,
        )

    def test_creation(self, gas):
        assert gas.greenhouse_co2_ppm == 800.0

    def test_to_dict(self, gas):
        d = gas.to_dict()
        assert d["exchange_rate"] == 0.5

    def test_from_dict_roundtrip(self, gas):
        d = gas.to_dict()
        restored = GasExchange.from_dict(d)
        assert restored.greenhouse_co2_ppm == gas.greenhouse_co2_ppm


class TestFlightRule:
    @pytest.fixture
    def rule(self):
        return FlightRule(
            rule_id="FR-T-001",
            sensor_type=SensorType.TEMPERATURE,
            condition="lt",
            threshold=5.0,
            device=DeviceType.HEATER,
            action="on",
            value=100.0,
            cooldown_seconds=60,
            priority=Severity.CRITICAL,
        )

    def test_creation(self, rule):
        assert rule.rule_id == "FR-T-001"
        assert rule.enabled is True  # default

    def test_creation_disabled(self):
        rule = FlightRule(
            rule_id="FR-X-001",
            sensor_type=SensorType.FIRE,
            condition="eq",
            threshold=1.0,
            device=DeviceType.FAN,
            action="off",
            value=0.0,
            cooldown_seconds=0,
            priority=Severity.CRITICAL,
            enabled=False,
        )
        assert rule.enabled is False

    def test_to_dict(self, rule):
        d = rule.to_dict()
        assert d["sensor_type"] == "temperature"
        assert d["device"] == "heater"
        assert d["priority"] == "critical"
        assert d["enabled"] is True

    def test_from_dict_roundtrip(self, rule):
        d = rule.to_dict()
        restored = FlightRule.from_dict(d)
        assert restored.rule_id == rule.rule_id
        assert restored.threshold == rule.threshold
        assert restored.enabled == rule.enabled
