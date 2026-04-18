"""Tier 0 Flight Rules Engine — deterministic, always-on safety floor.

NOT a fallback. Runs EVERY cycle, BEFORE agents.
PURE PYTHON. Zero external imports. THIS IS THE LAW.
"""

from __future__ import annotations

import time
import uuid

import structlog

from eden.domain.models import (
    ActuatorCommand,
    AgentDecision,
    DeviceType,
    EnergyBudget,
    FlightRule,
    GasExchange,
    MarsConditions,
    ResourceBudget,
    SensorType,
    Severity,
    Tier,
    TriggerRecord,
    ZoneState,
)


# ── Default Flight Rules ────────────────────────────────────────────────


DEFAULT_FLIGHT_RULES: list[FlightRule] = [
    # FR-F-001: fire detected → ALL OFF (handled specially, but define for completeness)
    FlightRule(
        rule_id="FR-F-001",
        sensor_type=SensorType.FIRE,
        condition="eq",
        threshold=1.0,
        device=DeviceType.FAN,  # placeholder — fire handling is special
        action="off",
        value=0.0,
        cooldown_seconds=0,
        priority=Severity.CRITICAL,
    ),
    # FR-T-001: temp < 5°C → heater ON 100% (frost kill)
    FlightRule(
        rule_id="FR-T-001",
        sensor_type=SensorType.TEMPERATURE,
        condition="lt",
        threshold=5.0,
        device=DeviceType.HEATER,
        action="on",
        value=100.0,
        cooldown_seconds=60,
        priority=Severity.CRITICAL,
    ),
    # FR-T-002: temp > 35°C → fan ON 100% (heat stress)
    FlightRule(
        rule_id="FR-T-002",
        sensor_type=SensorType.TEMPERATURE,
        condition="gt",
        threshold=35.0,
        device=DeviceType.FAN,
        action="on",
        value=100.0,
        cooldown_seconds=60,
        priority=Severity.HIGH,
    ),
    # FR-H-001: humidity > 90% → fan ON 50% (mold risk)
    FlightRule(
        rule_id="FR-H-001",
        sensor_type=SensorType.HUMIDITY,
        condition="gt",
        threshold=90.0,
        device=DeviceType.FAN,
        action="on",
        value=50.0,
        cooldown_seconds=120,
        priority=Severity.MEDIUM,
    ),
    # FR-H-002: humidity < 30% → pump ON (desiccation)
    FlightRule(
        rule_id="FR-H-002",
        sensor_type=SensorType.HUMIDITY,
        condition="lt",
        threshold=30.0,
        device=DeviceType.PUMP,
        action="on",
        value=50.0,
        cooldown_seconds=120,
        priority=Severity.MEDIUM,
    ),
    # FR-W-001: water_level < 10mm → pump OFF + alert CRITICAL
    FlightRule(
        rule_id="FR-W-001",
        sensor_type=SensorType.WATER_LEVEL,
        condition="lt",
        threshold=10.0,
        device=DeviceType.PUMP,
        action="off",
        value=0.0,
        cooldown_seconds=30,
        priority=Severity.CRITICAL,
    ),
    # FR-L-001: light < 100 lux → light ON
    FlightRule(
        rule_id="FR-L-001",
        sensor_type=SensorType.LIGHT,
        condition="lt",
        threshold=100.0,
        device=DeviceType.LIGHT,
        action="on",
        value=100.0,
        cooldown_seconds=300,
        priority=Severity.LOW,
    ),
    # FR-E-001: solar efficiency < 50% → power rationing mode
    # sensor_type=LIGHT is a proxy; actual check uses EnergyBudget
    FlightRule(
        rule_id="FR-E-001",
        sensor_type=SensorType.LIGHT,
        condition="lt",
        threshold=0.5,
        device=DeviceType.LIGHT,
        action="power_rationing",
        value=50.0,
        cooldown_seconds=600,
        priority=Severity.HIGH,
    ),
    # FR-G-001: CO2 > 5000ppm → increase ventilation
    # sensor_type=PRESSURE is a proxy; actual check uses GasExchange
    FlightRule(
        rule_id="FR-G-001",
        sensor_type=SensorType.PRESSURE,
        condition="gt",
        threshold=5000.0,
        device=DeviceType.FAN,
        action="on",
        value=100.0,
        cooldown_seconds=120,
        priority=Severity.CRITICAL,
    ),
    # FR-W-010: water < 30% capacity → rationing mode (calorie crops only)
    FlightRule(
        rule_id="FR-W-010",
        sensor_type=SensorType.WATER_LEVEL,
        condition="lt",
        threshold=30.0,
        device=DeviceType.PUMP,
        action="water_rationing",
        value=50.0,
        cooldown_seconds=300,
        priority=Severity.HIGH,
    ),
    # ── NEW SAFETY RULES ────────────────────────────────────────────────
    # FR-P-001: pressure < 600 hPa → seal habitat (depressurization = crew death)
    FlightRule(
        rule_id="FR-P-001",
        sensor_type=SensorType.PRESSURE,
        condition="lt",
        threshold=600.0,
        device=DeviceType.MOTOR,
        action="seal_habitat",
        value=0.0,
        cooldown_seconds=0,
        priority=Severity.CRITICAL,
    ),
    # FR-O2-001: O2 < 18% → increase gas exchange (crew impairment risk)
    # sensor_type=PRESSURE is a proxy; actual check uses GasExchange.greenhouse_o2_pct
    FlightRule(
        rule_id="FR-O2-001",
        sensor_type=SensorType.PRESSURE,
        condition="lt",
        threshold=18.0,
        device=DeviceType.FAN,
        action="increase_exchange",
        value=100.0,
        cooldown_seconds=60,
        priority=Severity.CRITICAL,
    ),
    # FR-O2-002: O2 > 25% → reduce exchange (fire risk)
    # sensor_type=PRESSURE is a proxy; actual check uses GasExchange.greenhouse_o2_pct
    FlightRule(
        rule_id="FR-O2-002",
        sensor_type=SensorType.PRESSURE,
        condition="gt",
        threshold=25.0,
        device=DeviceType.FAN,
        action="reduce_exchange",
        value=30.0,
        cooldown_seconds=60,
        priority=Severity.HIGH,
    ),
    # FR-STALE-001: stale sensor data (>60s) → mark zone compromised
    # Evaluated via evaluate_staleness(), not main evaluate loop
    FlightRule(
        rule_id="FR-STALE-001",
        sensor_type=SensorType.TEMPERATURE,
        condition="gt",
        threshold=60.0,
        device=DeviceType.FAN,
        action="mark_compromised",
        value=0.0,
        cooldown_seconds=0,
        priority=Severity.HIGH,
    ),
    # FR-RAD-001: radiation spike → reduce light exposure + alert crew
    # Evaluated via evaluate_mars(), not main evaluate loop
    FlightRule(
        rule_id="FR-RAD-001",
        sensor_type=SensorType.LIGHT,
        condition="eq",
        threshold=1.0,
        device=DeviceType.LIGHT,
        action="reduce_exposure",
        value=20.0,
        cooldown_seconds=300,
        priority=Severity.HIGH,
    ),
    # FR-RATE-001: rapid temp change (>5°C in 5min) → system failure alert
    # Evaluated via rate-of-change tracking in evaluate()
    FlightRule(
        rule_id="FR-RATE-001",
        sensor_type=SensorType.TEMPERATURE,
        condition="gt",
        threshold=5.0,
        device=DeviceType.FAN,
        action="emergency_ventilation",
        value=100.0,
        cooldown_seconds=60,
        priority=Severity.HIGH,
    ),
    # FR-N-001: nutrient_level > 90 → flush irrigation (over-fertilization kills)
    # sensor_type=WATER_LEVEL is a proxy; actual check uses ResourceBudget.nutrient_level
    FlightRule(
        rule_id="FR-N-001",
        sensor_type=SensorType.WATER_LEVEL,
        condition="gt",
        threshold=90.0,
        device=DeviceType.PUMP,
        action="flush_irrigation",
        value=100.0,
        cooldown_seconds=300,
        priority=Severity.MEDIUM,
    ),
]


def get_default_rules() -> list[FlightRule]:
    """Return a fresh copy of the default flight rules."""
    return list(DEFAULT_FLIGHT_RULES)


# ── Sensor Value Extraction ─────────────────────────────────────────────


_ZONE_SENSOR_MAP: dict[SensorType, str] = {
    SensorType.TEMPERATURE: "temperature",
    SensorType.HUMIDITY: "humidity",
    SensorType.PRESSURE: "pressure",
    SensorType.LIGHT: "light",
    SensorType.WATER_LEVEL: "water_level",
}


def _get_sensor_value(zone: ZoneState, sensor_type: SensorType) -> float:
    """Extract the sensor value from a ZoneState for a given SensorType."""
    if sensor_type == SensorType.FIRE:
        return 1.0 if zone.fire_detected else 0.0
    return getattr(zone, _ZONE_SENSOR_MAP[sensor_type])


def _check_condition(value: float, condition: str, threshold: float) -> bool:
    """Evaluate a comparison condition."""
    if condition == "lt":
        return value < threshold
    elif condition == "gt":
        return value > threshold
    elif condition == "eq":
        return value == threshold
    elif condition == "lte":
        return value <= threshold
    elif condition == "gte":
        return value >= threshold
    return False


# ── Special rule IDs that need non-zone data ────────────────────────────

_ENERGY_RULES = {"FR-E-001"}
_GAS_RULES = {"FR-G-001"}
_O2_RULES = {"FR-O2-001", "FR-O2-002"}
_NUTRIENT_RULES = {"FR-N-001"}
# These are evaluated by separate methods, skipped in main evaluate loop
_SEPARATE_EVAL_RULES = {"FR-STALE-001", "FR-RAD-001", "FR-RATE-001"}


# ── Flight Rules Engine ─────────────────────────────────────────────────


logger = structlog.get_logger(__name__)


class FlightRulesEngine:
    """Tier 0 deterministic rules engine.

    Evaluates zone state against flight rules and produces actuator commands
    and agent decisions. Tracks cooldowns to prevent rapid re-triggering.
    """

    def __init__(self, rules: list[FlightRule] | None = None) -> None:
        self.rules: list[FlightRule] = rules if rules is not None else list(DEFAULT_FLIGHT_RULES)
        self._candidates: list[FlightRule] = []
        # rule_id -> last trigger timestamp
        self._cooldowns: dict[str, float] = {}
        # zone_id -> (temperature, timestamp) for rate-of-change detection
        self._last_readings: dict[str, tuple[float, float]] = {}
        # Learning pipeline state
        self._trigger_history: list[TriggerRecord] = []
        self._candidate_cycles: dict[str, int] = {}
        # Shadow evaluation tracking
        self._shadow_hits: dict[str, int] = {}
        # Active rule trigger counts (for managed rule reporting)
        self._trigger_counts: dict[str, int] = {}

    # Keep .candidates as property for backwards compat
    @property
    def candidates(self) -> list[FlightRule]:
        return self._candidates

    def get_candidates(self) -> list[FlightRule]:
        """Return the list of proposed candidate rules."""
        return list(self._candidates)

    def evaluate(
        self,
        zone: ZoneState,
        energy: EnergyBudget | None = None,
        gas: GasExchange | None = None,
        resource: ResourceBudget | None = None,
    ) -> tuple[list[ActuatorCommand], list[AgentDecision]]:
        """Evaluate all rules against a zone state.

        Returns (commands, decisions). Fire short-circuits all other rules.
        """
        now = time.time()

        # FR-F-001: Fire check — short-circuit everything
        if zone.fire_detected:
            logger.critical("fire_detected", zone_id=zone.zone_id)
            return self._handle_fire(zone, now)

        commands: list[ActuatorCommand] = []
        decisions: list[AgentDecision] = []

        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.rule_id == "FR-F-001":
                continue  # fire handled above
            if rule.rule_id in _SEPARATE_EVAL_RULES:
                continue  # handled by separate methods

            # Check cooldown (per rule + zone combo)
            cooldown_key = f"{rule.rule_id}:{zone.zone_id}"
            last_fired = self._cooldowns.get(cooldown_key, 0.0)
            if now - last_fired < rule.cooldown_seconds:
                continue

            # Get value — special handling for energy/gas/o2/nutrient rules
            value = self._get_rule_value(rule, zone, energy, gas, resource)
            if value is None:
                continue  # data not available, skip

            if _check_condition(value, rule.condition, rule.threshold):
                cmd, decision = self._make_command_and_decision(rule, zone, value, now)
                commands.append(cmd)
                decisions.append(decision)
                self._cooldowns[cooldown_key] = now
                logger.info(
                    "flight_rule_triggered",
                    rule_id=rule.rule_id,
                    zone_id=zone.zone_id,
                    sensor_type=rule.sensor_type.value,
                    value=round(value, 2),
                    threshold=rule.threshold,
                    condition=rule.condition,
                    priority=rule.priority.value,
                    device=rule.device.value,
                    action=rule.action,
                )
                self._trigger_counts[rule.rule_id] = (
                    self._trigger_counts.get(rule.rule_id, 0) + 1
                )
                # Record trigger for learning pipeline
                self._trigger_history.append(TriggerRecord(
                    rule_id=rule.rule_id, zone_id=zone.zone_id,
                    sensor_value=value, threshold=rule.threshold, timestamp=now,
                ))
                if len(self._trigger_history) > 500:
                    self._trigger_history = self._trigger_history[-500:]

        # FR-RATE-001: Rate-of-change detection
        self._check_rate_of_change(zone, now, commands, decisions)

        return commands, decisions

    def _check_rate_of_change(
        self,
        zone: ZoneState,
        now: float,
        commands: list[ActuatorCommand],
        decisions: list[AgentDecision],
    ) -> None:
        """FR-RATE-001: detect rapid temperature changes (>5°C in ≤5min)."""
        rate_rule = next(
            (r for r in self.rules if r.rule_id == "FR-RATE-001" and r.enabled),
            None,
        )
        zone_key = zone.zone_id

        if rate_rule and zone_key in self._last_readings:
            last_temp, last_time = self._last_readings[zone_key]
            elapsed = now - last_time
            if 0 < elapsed <= 300:  # within 5-minute window
                temp_delta = abs(zone.temperature - last_temp)
                if temp_delta > rate_rule.threshold:
                    last_fired = self._cooldowns.get("FR-RATE-001", 0.0)
                    if now - last_fired >= rate_rule.cooldown_seconds:
                        cmd, decision = self._make_command_and_decision(
                            rate_rule, zone, temp_delta, now
                        )
                        commands.append(cmd)
                        decisions.append(decision)
                        self._cooldowns["FR-RATE-001"] = now

        # Always update last reading
        self._last_readings[zone_key] = (zone.temperature, now)

    def _get_rule_value(
        self,
        rule: FlightRule,
        zone: ZoneState,
        energy: EnergyBudget | None,
        gas: GasExchange | None,
        resource: ResourceBudget | None = None,
    ) -> float | None:
        """Extract the relevant value for a rule, or None if data unavailable."""
        if rule.rule_id in _ENERGY_RULES:
            if energy is None:
                return None
            return energy.current_efficiency
        if rule.rule_id in _GAS_RULES:
            if gas is None:
                return None
            return gas.greenhouse_co2_ppm
        if rule.rule_id in _O2_RULES:
            if gas is None:
                return None
            return gas.greenhouse_o2_pct
        if rule.rule_id in _NUTRIENT_RULES:
            if resource is None:
                return None
            return resource.nutrient_level
        return _get_sensor_value(zone, rule.sensor_type)

    def _make_command_and_decision(
        self,
        rule: FlightRule,
        zone: ZoneState,
        value: float,
        now: float,
    ) -> tuple[ActuatorCommand, AgentDecision]:
        cmd = ActuatorCommand(
            command_id=f"fr-{rule.rule_id}-{uuid.uuid4().hex[:8]}",
            zone_id=zone.zone_id,
            device=rule.device,
            action=rule.action,
            value=rule.value,
            reason=f"Flight rule {rule.rule_id}: {rule.sensor_type.value} "
                   f"{rule.condition} {rule.threshold}",
            priority=rule.priority,
            timestamp=now,
        )
        decision = AgentDecision(
            timestamp=now,
            agent_name="FLIGHT_RULES",
            severity=rule.priority,
            reasoning=f"{rule.sensor_type.value}={value}, "
                      f"threshold {rule.condition} {rule.threshold}",
            action=f"{rule.device.value} {rule.action} {rule.value}",
            result="executed",
            zone_id=zone.zone_id,
            tier=Tier.FLIGHT_RULES,
        )
        return cmd, decision

    def _handle_fire(
        self, zone: ZoneState, now: float
    ) -> tuple[list[ActuatorCommand], list[AgentDecision]]:
        """Fire emergency — kill ALL devices, short-circuit all other rules."""
        commands: list[ActuatorCommand] = []
        for device in DeviceType:
            cmd = ActuatorCommand(
                command_id=f"fr-FIRE-{device.value}-{uuid.uuid4().hex[:8]}",
                zone_id=zone.zone_id,
                device=device,
                action="off",
                value=0.0,
                reason="FIRE DETECTED — emergency shutdown",
                priority=Severity.CRITICAL,
                timestamp=now,
            )
            commands.append(cmd)

        decision = AgentDecision(
            timestamp=now,
            agent_name="FLIGHT_RULES",
            severity=Severity.CRITICAL,
            reasoning="Fire detected in zone — emergency shutdown all devices",
            action="ALL devices OFF",
            result="emergency_shutdown",
            zone_id=zone.zone_id,
            tier=Tier.FLIGHT_RULES,
        )
        return commands, [decision]

    # ── Resource Rules (separate methods for convenience) ─────────

    def evaluate_energy(self, energy: EnergyBudget) -> list[AgentDecision]:
        """FR-E-001: solar efficiency < 50% → power rationing mode."""
        now = time.time()
        if energy.current_efficiency < 0.5:
            return [
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.HIGH,
                    reasoning=f"Solar efficiency {energy.current_efficiency:.0%} < 50% — "
                              f"entering power rationing mode",
                    action="power_rationing_on",
                    result="rationing_active",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            ]
        return []

    def evaluate_gas(self, gas: GasExchange) -> list[AgentDecision]:
        """FR-G-001: CO2 > 5000ppm; FR-O2-001: O2 < 18%; FR-O2-002: O2 > 25%."""
        now = time.time()
        decisions: list[AgentDecision] = []

        # FR-G-001: dangerous CO2 levels
        if gas.greenhouse_co2_ppm > 5000.0:
            decisions.append(
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.CRITICAL,
                    reasoning=f"CO2 at {gas.greenhouse_co2_ppm}ppm > 5000ppm — "
                              f"dangerous levels, increase ventilation",
                    action="increase_ventilation",
                    result="ventilation_increased",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            )

        # FR-O2-001: O2 depletion — crew impairment risk
        if gas.greenhouse_o2_pct < 18.0:
            decisions.append(
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.CRITICAL,
                    reasoning=f"O2 at {gas.greenhouse_o2_pct:.1f}% < 18% — "
                              f"crew impairment risk, increase gas exchange",
                    action="increase_gas_exchange",
                    result="exchange_increased",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            )

        # FR-O2-002: O2 excess — fire risk
        if gas.greenhouse_o2_pct > 25.0:
            decisions.append(
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.HIGH,
                    reasoning=f"O2 at {gas.greenhouse_o2_pct:.1f}% > 25% — "
                              f"fire risk, reduce gas exchange",
                    action="reduce_gas_exchange",
                    result="exchange_reduced",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            )

        return decisions

    def evaluate_water(self, water: ResourceBudget) -> list[AgentDecision]:
        """FR-W-010: water capacity < 30% → rationing mode."""
        now = time.time()
        if water.current_capacity < 30.0:
            return [
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.HIGH,
                    reasoning=f"Water capacity {water.current_capacity:.0f}% < 30% — "
                              f"entering water rationing mode (calorie crops only)",
                    action="water_rationing_on",
                    result="rationing_active",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            ]
        return []

    def evaluate_nutrients(self, resource: ResourceBudget) -> list[AgentDecision]:
        """FR-N-001: nutrient_level > 90 → flush irrigation (toxicity risk)."""
        now = time.time()
        if resource.nutrient_level > 90.0:
            return [
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.MEDIUM,
                    reasoning=f"Nutrient level {resource.nutrient_level:.0f}% > 90% — "
                              f"toxicity risk, flush irrigation",
                    action="flush_irrigation",
                    result="irrigation_flushed",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            ]
        return []

    def evaluate_mars(self, mars: MarsConditions) -> list[AgentDecision]:
        """FR-RAD-001: radiation alert → reduce light exposure + alert crew."""
        now = time.time()
        decisions: list[AgentDecision] = []

        if mars.radiation_alert:
            decisions.append(
                AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.HIGH,
                    reasoning="Radiation alert active — reducing light exposure "
                              "to protect crops and crew",
                    action="reduce_light_exposure",
                    result="exposure_reduced",
                    zone_id="global",
                    tier=Tier.FLIGHT_RULES,
                )
            )

        return decisions

    def evaluate_staleness(
        self, zone: ZoneState, current_time: float
    ) -> list[AgentDecision]:
        """FR-STALE-001: sensor data older than 60s → mark zone compromised."""
        decisions: list[AgentDecision] = []
        age = current_time - zone.last_updated
        if age > 60.0:
            decisions.append(
                AgentDecision(
                    timestamp=current_time,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.HIGH,
                    reasoning=f"Zone {zone.zone_id} sensor data is {age:.0f}s old (>60s) — "
                              f"potentially compromised readings",
                    action="mark_zone_compromised",
                    result="zone_compromised",
                    zone_id=zone.zone_id,
                    tier=Tier.FLIGHT_RULES,
                )
            )
        return decisions

    # ── Self-Improvement: Learning Pipeline ────────────────────────

    def learn(self) -> list[AgentDecision]:
        """Analyze trigger patterns -> propose/promote rules. Pure domain logic."""
        events: list[AgentDecision] = []
        now = time.time()
        events.extend(self._propose_from_frequency(now))
        events.extend(self._promote_mature_candidates(now))
        for rule_id in list(self._candidate_cycles):
            self._candidate_cycles[rule_id] += 1
        return events

    def _propose_from_frequency(self, now: float) -> list[AgentDecision]:
        """Count triggers per rule_id in recent history; propose tighter rules."""
        events: list[AgentDecision] = []
        recent = self._trigger_history[-100:]
        if not recent:
            return events

        # Count triggers per rule_id
        counts: dict[str, list[TriggerRecord]] = {}
        for tr in recent:
            counts.setdefault(tr.rule_id, []).append(tr)

        existing_ids = {r.rule_id for r in self.rules}
        candidate_ids = {r.rule_id for r in self._candidates}

        for rule_id, triggers in counts.items():
            count = len(triggers)
            if count < 3:
                continue

            # Extract numeric suffix from source rule_id (e.g. "FR-L-001" → "001")
            suffix = rule_id.rsplit("-", 1)[-1] if "-" in rule_id else rule_id
            new_id = f"FR-LRN-{suffix}"
            if new_id in existing_ids or new_id in candidate_ids:
                continue

            # Find the source rule
            source = next((r for r in self.rules if r.rule_id == rule_id), None)
            if source is None:
                continue

            # Compute tightened threshold from average trigger values
            avg_value = sum(t.sensor_value for t in triggers) / count
            new_threshold = source.threshold + (avg_value - source.threshold) * 0.3

            candidate = FlightRule(
                rule_id=new_id,
                sensor_type=source.sensor_type,
                condition=source.condition,
                threshold=round(new_threshold, 2),
                device=source.device,
                action=source.action,
                value=source.value,
                cooldown_seconds=source.cooldown_seconds,
                priority=Severity.LOW,
                enabled=False,
            )
            self._candidates.append(candidate)
            self._candidate_cycles[new_id] = 0
            candidate_ids.add(new_id)
            logger.info(
                "flight_rule_proposed",
                rule_id=new_id,
                source_rule=rule_id,
                trigger_count=count,
                original_threshold=source.threshold,
                new_threshold=round(new_threshold, 2),
            )

            events.append(AgentDecision(
                agent_name="FLIGHT_RULES",
                action=f"PROPOSE {new_id}",
                result="proposed",
                reasoning=(
                    f"Rule {rule_id} triggered {count}x -- proposing tighter "
                    f"threshold {source.threshold} -> {new_threshold:.2f}"
                ),
                tier=Tier.FLIGHT_RULES,
                severity=Severity.INFO,
                zone_id="global",
                timestamp=now,
            ))

        return events

    def _promote_mature_candidates(self, now: float) -> list[AgentDecision]:
        """Promote candidates that have survived enough cycles without conflict."""
        events: list[AgentDecision] = []
        promoted_ids: list[str] = []

        for candidate in list(self._candidates):
            cycles = self._candidate_cycles.get(candidate.rule_id, 0)
            if cycles < 3:
                continue

            # Conflict check: no active rule with same sensor_type+condition
            # that already has a tighter threshold
            has_conflict = False
            for active in self.rules:
                if not active.enabled:
                    continue
                if (active.sensor_type == candidate.sensor_type
                        and active.condition == candidate.condition):
                    # "Tighter" depends on condition direction
                    if candidate.condition in ("gt", "gte"):
                        if active.threshold <= candidate.threshold:
                            has_conflict = True
                            break
                    elif candidate.condition in ("lt", "lte"):
                        if active.threshold >= candidate.threshold:
                            has_conflict = True
                            break

            if has_conflict:
                continue

            # Promote: create an enabled copy, add to active rules
            promoted = FlightRule(
                rule_id=candidate.rule_id,
                sensor_type=candidate.sensor_type,
                condition=candidate.condition,
                threshold=candidate.threshold,
                device=candidate.device,
                action=candidate.action,
                value=candidate.value,
                cooldown_seconds=candidate.cooldown_seconds,
                priority=candidate.priority,
                enabled=True,
            )
            self.rules.append(promoted)
            promoted_ids.append(candidate.rule_id)
            logger.info(
                "flight_rule_promoted",
                rule_id=candidate.rule_id,
                total_active_rules=len(self.rules),
            )

            events.append(AgentDecision(
                agent_name="FLIGHT_RULES",
                action=f"PROMOTE {candidate.rule_id}",
                result="promoted",
                reasoning=(
                    f"Candidate {candidate.rule_id} matured -- "
                    f"no conflicts -- promoted to active"
                ),
                tier=Tier.FLIGHT_RULES,
                severity=Severity.INFO,
                zone_id="global",
                timestamp=now,
            ))

        # Remove promoted from candidates
        for pid in promoted_ids:
            self._candidates = [c for c in self._candidates if c.rule_id != pid]
            self._candidate_cycles.pop(pid, None)

        return events

    def propose_flight_rule(self, rule: FlightRule) -> None:
        """Store a candidate rule proposed by an agent.

        Candidates are NOT active — they're stored for review and activation
        on next restart (safety gate).
        """
        self._candidates.append(rule)

    # ── Shadow Rule Evaluation ─────────────────────────────────────

    def run_shadow(
        self,
        zone: ZoneState,
        energy: EnergyBudget | None = None,
        gas: GasExchange | None = None,
        resource: ResourceBudget | None = None,
    ) -> list[AgentDecision]:
        """Evaluate candidate rules in SHADOW mode — no commands, just tracking.

        Shadow rules run against live data exactly like active rules, but:
        - No ActuatorCommands are produced
        - Hits are counted (shadow_hits)
        - Decisions are logged as INFO for audit trail

        This is the safety gate between "proposed" and "active".
        A candidate must accumulate enough shadow hits without conflict
        before being promoted to active.
        """
        now = time.time()
        shadow_decisions: list[AgentDecision] = []

        for candidate in self._candidates:
            if candidate.rule_id in _SEPARATE_EVAL_RULES:
                continue

            # Get value the same way as active evaluation
            value = self._get_rule_value(candidate, zone, energy, gas, resource)
            if value is None:
                continue

            if _check_condition(value, candidate.condition, candidate.threshold):
                # Record shadow hit
                self._shadow_hits[candidate.rule_id] = (
                    self._shadow_hits.get(candidate.rule_id, 0) + 1
                )

                shadow_decisions.append(AgentDecision(
                    timestamp=now,
                    agent_name="FLIGHT_RULES",
                    severity=Severity.INFO,
                    reasoning=(
                        f"SHADOW: {candidate.rule_id} would fire — "
                        f"{candidate.sensor_type.value}={value}, "
                        f"threshold {candidate.condition} {candidate.threshold} "
                        f"(shadow hits: {self._shadow_hits[candidate.rule_id]})"
                    ),
                    action=f"SHADOW {candidate.rule_id}",
                    result="shadow_hit",
                    zone_id=zone.zone_id,
                    tier=Tier.FLIGHT_RULES,
                ))

        return shadow_decisions

    def get_shadow_hits(self) -> dict[str, int]:
        """Return shadow hit counts for all candidate rules."""
        return dict(self._shadow_hits)

    def get_managed_rules(self) -> list[dict]:
        """Return all rules (active + candidates) with lifecycle metadata."""
        managed: list[dict] = []

        for rule in self.rules:
            managed.append({
                "rule": rule.to_dict(),
                "lifecycle": "active",
                "shadow_hits": 0,
                "active_hits": self._trigger_counts.get(rule.rule_id, 0),
            })

        for candidate in self._candidates:
            managed.append({
                "rule": candidate.to_dict(),
                "lifecycle": "shadow" if self._shadow_hits.get(candidate.rule_id, 0) > 0 else "proposed",
                "shadow_hits": self._shadow_hits.get(candidate.rule_id, 0),
                "active_hits": 0,
            })

        return managed
