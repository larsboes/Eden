"""EDEN domain models — ALL dataclasses + enums.

ZERO external imports. Only stdlib + dataclasses. THIS IS THE LAW.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from enum import Enum, IntEnum


# ── Enums ────────────────────────────────────────────────────────────────


class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    LIGHT = "light"
    WATER_LEVEL = "water_level"
    SOIL_MOISTURE = "soil_moisture"
    FIRE = "fire"


class DeviceType(str, Enum):
    FAN = "fan"
    LIGHT = "light"
    PUMP = "pump"
    HEATER = "heater"
    MOTOR = "motor"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Tier(IntEnum):
    FLIGHT_RULES = 0
    LOCAL_MODEL = 1
    CLOUD_MODEL = 2


# ── Helpers ──────────────────────────────────────────────────────────────


def _enum_to_value(obj: object) -> object:
    """Convert enum members to their .value for dict serialization."""
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ── Value Objects (frozen) ───────────────────────────────────────────────


@dataclass(frozen=True)
class SensorReading:
    zone_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float
    source: str

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "sensor_type": self.sensor_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SensorReading:
        return cls(
            zone_id=d["zone_id"],
            sensor_type=SensorType(d["sensor_type"]),
            value=d["value"],
            unit=d["unit"],
            timestamp=d["timestamp"],
            source=d["source"],
        )


@dataclass(frozen=True)
class TriggerRecord:
    """Immutable record of a flight rule firing."""
    rule_id: str
    zone_id: str
    sensor_value: float
    threshold: float
    timestamp: float


@dataclass(frozen=True)
class ActuatorCommand:
    command_id: str
    zone_id: str
    device: DeviceType
    action: str
    value: float
    reason: str
    priority: Severity
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "zone_id": self.zone_id,
            "device": self.device.value,
            "action": self.action,
            "value": self.value,
            "reason": self.reason,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ActuatorCommand:
        return cls(
            command_id=d["command_id"],
            zone_id=d["zone_id"],
            device=DeviceType(d["device"]),
            action=d["action"],
            value=d["value"],
            reason=d["reason"],
            priority=Severity(d["priority"]),
            timestamp=d["timestamp"],
        )


@dataclass(frozen=True)
class AgentDecision:
    timestamp: float
    agent_name: str
    severity: Severity
    reasoning: str
    action: str
    result: str
    zone_id: str
    tier: Tier

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "severity": self.severity.value,
            "reasoning": self.reasoning,
            "action": self.action,
            "result": self.result,
            "zone_id": self.zone_id,
            "tier": self.tier.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AgentDecision:
        return cls(
            timestamp=d["timestamp"],
            agent_name=d["agent_name"],
            severity=Severity(d["severity"]),
            reasoning=d["reasoning"],
            action=d["action"],
            result=d["result"],
            zone_id=d["zone_id"],
            tier=Tier(d["tier"]),
        )


@dataclass(frozen=True)
class MarsConditions:
    exterior_temp: float
    dome_temp: float
    pressure_hpa: float
    solar_irradiance: float
    dust_opacity: float
    sol: int
    storm_active: bool
    radiation_alert: bool

    def to_dict(self) -> dict:
        return {
            "exterior_temp": self.exterior_temp,
            "dome_temp": self.dome_temp,
            "pressure_hpa": self.pressure_hpa,
            "solar_irradiance": self.solar_irradiance,
            "dust_opacity": self.dust_opacity,
            "sol": self.sol,
            "storm_active": self.storm_active,
            "radiation_alert": self.radiation_alert,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MarsConditions:
        return cls(
            exterior_temp=d["exterior_temp"],
            dome_temp=d["dome_temp"],
            pressure_hpa=d["pressure_hpa"],
            solar_irradiance=d["solar_irradiance"],
            dust_opacity=d["dust_opacity"],
            sol=d["sol"],
            storm_active=d["storm_active"],
            radiation_alert=d["radiation_alert"],
        )


# ── Entities (mutable) ──────────────────────────────────────────────────


@dataclass
class ZoneState:
    zone_id: str
    temperature: float
    humidity: float
    pressure: float
    light: float
    water_level: float
    fire_detected: bool
    last_updated: float
    is_alive: bool
    source: str

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "light": self.light,
            "water_level": self.water_level,
            "fire_detected": self.fire_detected,
            "last_updated": self.last_updated,
            "is_alive": self.is_alive,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ZoneState:
        return cls(
            zone_id=d["zone_id"],
            temperature=d["temperature"],
            humidity=d["humidity"],
            pressure=d["pressure"],
            light=d["light"],
            water_level=d["water_level"],
            fire_detected=d["fire_detected"],
            last_updated=d["last_updated"],
            is_alive=d["is_alive"],
            source=d["source"],
        )


@dataclass
class DesiredState:
    zone_id: str
    temp_min: float
    temp_max: float
    humidity_min: float
    humidity_max: float
    light_hours: float
    soil_moisture_min: float
    soil_moisture_max: float
    water_budget_liters_per_day: float

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "humidity_min": self.humidity_min,
            "humidity_max": self.humidity_max,
            "light_hours": self.light_hours,
            "soil_moisture_min": self.soil_moisture_min,
            "soil_moisture_max": self.soil_moisture_max,
            "water_budget_liters_per_day": self.water_budget_liters_per_day,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DesiredState:
        return cls(
            zone_id=d["zone_id"],
            temp_min=d["temp_min"],
            temp_max=d["temp_max"],
            humidity_min=d["humidity_min"],
            humidity_max=d["humidity_max"],
            light_hours=d["light_hours"],
            soil_moisture_min=d["soil_moisture_min"],
            soil_moisture_max=d["soil_moisture_max"],
            water_budget_liters_per_day=d["water_budget_liters_per_day"],
        )


@dataclass
class CropProfile:
    name: str
    zone_id: str
    calories_per_kg: float
    protein_per_kg: float
    growth_days: int
    yield_kg_per_m2: float
    temp_min: float
    temp_max: float
    humidity_min: float
    humidity_max: float
    # Simulation parameters (defaults from CROP_PARAMS in simulation.py)
    area_m2: float = 25.0
    base_temperature: float = 5.0
    gdd_to_maturity: float = 1000.0
    max_growth_rate: float = 0.020
    harvest_index: float = 0.60
    water_use_efficiency: float = 300.0
    radiation_use_efficiency: float = 1.4

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "zone_id": self.zone_id,
            "calories_per_kg": self.calories_per_kg,
            "protein_per_kg": self.protein_per_kg,
            "growth_days": self.growth_days,
            "yield_kg_per_m2": self.yield_kg_per_m2,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "humidity_min": self.humidity_min,
            "humidity_max": self.humidity_max,
            "area_m2": self.area_m2,
            "base_temperature": self.base_temperature,
            "gdd_to_maturity": self.gdd_to_maturity,
            "max_growth_rate": self.max_growth_rate,
            "harvest_index": self.harvest_index,
            "water_use_efficiency": self.water_use_efficiency,
            "radiation_use_efficiency": self.radiation_use_efficiency,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CropProfile:
        return cls(
            name=d["name"],
            zone_id=d["zone_id"],
            calories_per_kg=d["calories_per_kg"],
            protein_per_kg=d["protein_per_kg"],
            growth_days=d["growth_days"],
            yield_kg_per_m2=d["yield_kg_per_m2"],
            temp_min=d["temp_min"],
            temp_max=d["temp_max"],
            humidity_min=d["humidity_min"],
            humidity_max=d["humidity_max"],
            area_m2=d.get("area_m2", 25.0),
            base_temperature=d.get("base_temperature", 5.0),
            gdd_to_maturity=d.get("gdd_to_maturity", 1000.0),
            max_growth_rate=d.get("max_growth_rate", 0.020),
            harvest_index=d.get("harvest_index", 0.60),
            water_use_efficiency=d.get("water_use_efficiency", 300.0),
            radiation_use_efficiency=d.get("radiation_use_efficiency", 1.4),
        )


@dataclass
class CrewMember:
    name: str
    daily_kcal_target: float
    daily_protein_target: float
    current_kcal_intake: float = 0.0
    current_protein_intake: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "daily_kcal_target": self.daily_kcal_target,
            "daily_protein_target": self.daily_protein_target,
            "current_kcal_intake": self.current_kcal_intake,
            "current_protein_intake": self.current_protein_intake,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CrewMember:
        return cls(
            name=d["name"],
            daily_kcal_target=d["daily_kcal_target"],
            daily_protein_target=d["daily_protein_target"],
            current_kcal_intake=d.get("current_kcal_intake", 0.0),
            current_protein_intake=d.get("current_protein_intake", 0.0),
        )


@dataclass
class ResourceBudget:
    water_liters: float
    nutrient_level: float
    current_capacity: float

    def to_dict(self) -> dict:
        return {
            "water_liters": self.water_liters,
            "nutrient_level": self.nutrient_level,
            "current_capacity": self.current_capacity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ResourceBudget:
        return cls(
            water_liters=d["water_liters"],
            nutrient_level=d["nutrient_level"],
            current_capacity=d["current_capacity"],
        )


@dataclass
class EnergyBudget:
    solar_capacity_kw: float
    current_efficiency: float
    allocations: dict
    reserve_kw: float

    def to_dict(self) -> dict:
        return {
            "solar_capacity_kw": self.solar_capacity_kw,
            "current_efficiency": self.current_efficiency,
            "allocations": dict(self.allocations),
            "reserve_kw": self.reserve_kw,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EnergyBudget:
        return cls(
            solar_capacity_kw=d["solar_capacity_kw"],
            current_efficiency=d["current_efficiency"],
            allocations=dict(d["allocations"]),
            reserve_kw=d["reserve_kw"],
        )


@dataclass
class GasExchange:
    greenhouse_co2_ppm: float
    greenhouse_o2_pct: float
    habitat_co2_ppm: float
    habitat_o2_pct: float
    exchange_rate: float

    def to_dict(self) -> dict:
        return {
            "greenhouse_co2_ppm": self.greenhouse_co2_ppm,
            "greenhouse_o2_pct": self.greenhouse_o2_pct,
            "habitat_co2_ppm": self.habitat_co2_ppm,
            "habitat_o2_pct": self.habitat_o2_pct,
            "exchange_rate": self.exchange_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GasExchange:
        return cls(
            greenhouse_co2_ppm=d["greenhouse_co2_ppm"],
            greenhouse_o2_pct=d["greenhouse_o2_pct"],
            habitat_co2_ppm=d["habitat_co2_ppm"],
            habitat_o2_pct=d["habitat_o2_pct"],
            exchange_rate=d["exchange_rate"],
        )


@dataclass
class FlightRule:
    rule_id: str
    sensor_type: SensorType
    condition: str
    threshold: float
    device: DeviceType
    action: str
    value: float
    cooldown_seconds: int
    priority: Severity
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "sensor_type": self.sensor_type.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "device": self.device.value,
            "action": self.action,
            "value": self.value,
            "cooldown_seconds": self.cooldown_seconds,
            "priority": self.priority.value,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FlightRule:
        return cls(
            rule_id=d["rule_id"],
            sensor_type=SensorType(d["sensor_type"]),
            condition=d["condition"],
            threshold=d["threshold"],
            device=DeviceType(d["device"]),
            action=d["action"],
            value=d["value"],
            cooldown_seconds=d["cooldown_seconds"],
            priority=Severity(d["priority"]),
            enabled=d.get("enabled", True),
        )


# ── Council / Retrospective Models ─────────────────────────────────────


class RuleLifecycle(str, Enum):
    PROPOSED = "proposed"
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    ACTIVE = "active"
    DEMOTED = "demoted"
    REJECTED = "rejected"


@dataclass
class CrewEscalation:
    """Formal request for crew intervention — astronaut time is scarce."""
    escalation_id: str
    timestamp: float
    task: str
    urgency: Severity
    estimated_minutes: int
    zone_id: str
    category: str  # hardware|safety|biological|resource
    status: str = "pending"  # pending|acknowledged|in_progress|resolved|dismissed
    acknowledged_by: str | None = None
    resolved_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "escalation_id": self.escalation_id,
            "timestamp": self.timestamp,
            "task": self.task,
            "urgency": self.urgency.value,
            "estimated_minutes": self.estimated_minutes,
            "zone_id": self.zone_id,
            "category": self.category,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CrewEscalation:
        return cls(
            escalation_id=d["escalation_id"],
            timestamp=d["timestamp"],
            task=d["task"],
            urgency=Severity(d["urgency"]),
            estimated_minutes=d["estimated_minutes"],
            zone_id=d["zone_id"],
            category=d["category"],
            status=d.get("status", "pending"),
            acknowledged_by=d.get("acknowledged_by"),
            resolved_at=d.get("resolved_at"),
        )


@dataclass
class ManagedRule:
    """A flight rule with lifecycle tracking — from retrospective proposal to active."""
    rule: FlightRule
    lifecycle: RuleLifecycle
    source_retro_id: str
    proposed_at: float
    promoted_at: float | None = None
    shadow_hits: int = 0
    active_hits: int = 0
    demotion_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "rule": self.rule.to_dict(),
            "lifecycle": self.lifecycle.value,
            "source_retro_id": self.source_retro_id,
            "proposed_at": self.proposed_at,
            "promoted_at": self.promoted_at,
            "shadow_hits": self.shadow_hits,
            "active_hits": self.active_hits,
            "demotion_reason": self.demotion_reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ManagedRule:
        return cls(
            rule=FlightRule.from_dict(d["rule"]),
            lifecycle=RuleLifecycle(d["lifecycle"]),
            source_retro_id=d["source_retro_id"],
            proposed_at=d["proposed_at"],
            promoted_at=d.get("promoted_at"),
            shadow_hits=d.get("shadow_hits", 0),
            active_hits=d.get("active_hits", 0),
            demotion_reason=d.get("demotion_reason"),
        )
