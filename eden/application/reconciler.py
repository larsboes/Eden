"""EDEN Reconciler — K8s-style control loop for the Martian greenhouse.

Runs every N seconds:
1. Collect zone states from sensors (in-memory, zero latency)
2. Apply Mars Transform (pure functions, <1ms)
3. Run Flight Rules (Tier 0, always, safety floor)
4. Execute flight rule commands immediately
5. Persist telemetry + zone state
6. Compute deltas vs desired state
7. If deltas exist + model available → invoke model
8. Log ALL decisions
"""

from __future__ import annotations

import os
import time
import uuid

import structlog

from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import (
    enrich_from_nasa,
    get_mars_conditions,
    transform_light,
    transform_pressure,
    transform_temperature,
)
from eden.domain.models import (
    AgentDecision,
    DesiredState,
    EnergyBudget,
    GasExchange,
    ResourceBudget,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker
from eden.domain.resources import ResourceTracker
from eden.application.retrospective import Retrospective

logger = structlog.get_logger(__name__)


class Reconciler:
    """Main reconciliation loop — the heartbeat of EDEN."""

    # How often to refresh NASA data (seconds) — not every reconcile cycle
    _NASA_REFRESH_INTERVAL = 300  # 5 minutes

    def __init__(
        self,
        sensor,  # SensorPort
        actuator,  # ActuatorPort
        state_store,  # StateStorePort
        telemetry_store,  # TelemetryStorePort
        agent_log,  # AgentLogPort
        model,  # ModelPort | None
        flight_rules: FlightRulesEngine,
        nutrition: NutritionTracker,
        resource_tracker: ResourceTracker,
        config,  # Settings
        event_bus=None,  # EventBus | None
        agent_team=None,  # AgentTeam | None
        nasa_adapter=None,  # NasaAdapter | None
        conditions_fn=None,  # (sol: int) -> MarsConditions | None — override Mars conditions
        transform_fn=None,  # (zone, mars) -> ZoneState | None — override Mars transform
    ) -> None:
        self._sensor = sensor
        self._actuator = actuator
        self._state_store = state_store
        self._telemetry_store = telemetry_store
        self._agent_log = agent_log
        self._model = model
        self._flight_rules = flight_rules
        self._nutrition = nutrition
        self._resource_tracker = resource_tracker
        self._config = config
        self._event_bus = event_bus
        self._agent_team = agent_team
        self._nasa_adapter = nasa_adapter
        self._conditions_fn = conditions_fn
        self._transform_fn = transform_fn
        self._retrospective = Retrospective(
            flight_engine=flight_rules,
            event_bus=event_bus,
        )
        self._running = False
        self._current_sol = int(os.getenv("EDEN_START_SOL", "247"))
        self._energy_budget: EnergyBudget | None = None
        self._gas_exchange: GasExchange | None = None
        self._resource_budget: ResourceBudget | None = None
        self._previous_decisions: list[AgentDecision] = []
        self._previous_zones: dict[str, ZoneState] = {}
        self.last_feedback: list[dict] = []
        self.mars_conditions = None  # Latest enriched MarsConditions (read by API)
        self._cycle_count: int = 0
        self._PARLIAMENT_ROUTINE_INTERVAL = 5  # Run parliament every N cycles even if nominal
        # Cached NASA data (refreshed every _NASA_REFRESH_INTERVAL)
        self._nasa_weather: dict | None = None
        self._nasa_solar: list | None = None
        self._nasa_last_fetch: float = 0.0
        # Actuator feedback tracking (hardware failure detection)
        self._pending_commands: dict[str, list[dict]] = {}  # zone_id → [{device, action, value, timestamp}]
        self._hardware_failures: list[dict] = []  # detected failures for council context

    def _emit(self, event_type: str, data: dict | list | str | None = None) -> None:
        """Publish an event to the EventBus if available."""
        if self._event_bus is not None:
            self._event_bus.publish(event_type, data)

    def _refresh_nasa_data(self) -> None:
        """Fetch NASA weather + solar data if adapter is wired and cache is stale."""
        if self._nasa_adapter is None:
            return
        now = time.time()
        if now - self._nasa_last_fetch < self._NASA_REFRESH_INTERVAL:
            return
        try:
            self._nasa_weather = self._nasa_adapter.get_mars_weather()
            self._nasa_solar = self._nasa_adapter.get_solar_events()
            self._nasa_last_fetch = now
            logger.info(
                "nasa_data_refreshed",
                weather_sol=self._nasa_weather.get("sol", "?"),
                solar_events=len(self._nasa_solar) if self._nasa_solar else 0,
            )
            self._emit("nasa_data", {
                "weather": self._nasa_weather,
                "solar_events_count": len(self._nasa_solar) if self._nasa_solar else 0,
            })
        except Exception:
            logger.warning("nasa_data_fetch_failed", exc_info=True)

    def run(self) -> None:
        """Main loop — runs until stop() is called."""
        self._running = True
        logger.info("reconciler_starting", interval_s=self._config.RECONCILE_INTERVAL_SECONDS)

        while self._running:
            try:
                self.reconcile_once()
            except Exception:
                logger.exception("reconcile_cycle_error", cycle=self._cycle_count)

            # Sleep in small increments so stop() is responsive
            deadline = time.time() + self._config.RECONCILE_INTERVAL_SECONDS
            while self._running and time.time() < deadline:
                time.sleep(0.1)

        logger.info("reconciler_stopped", total_cycles=self._cycle_count)

    def stop(self) -> None:
        """Signal the reconciler to stop after the current cycle."""
        self._running = False

    def reconcile_once(self) -> list[AgentDecision]:
        """Execute a single reconciliation cycle. Returns all decisions made."""
        self._cycle_count += 1
        cycle_start = time.time()
        all_decisions: list[AgentDecision] = []

        # Bind cycle context — all logs during this cycle carry these fields
        structlog.contextvars.bind_contextvars(cycle=self._cycle_count, sol=self._current_sol)

        # 1. Collect zone states from sensor adapter
        zone_ids = self._get_zone_ids()
        if not zone_ids:
            structlog.contextvars.unbind_contextvars("cycle", "sol")
            return all_decisions

        logger.info("reconcile_cycle_start", zones=len(zone_ids), zone_ids=zone_ids)

        if self._conditions_fn is not None:
            mars = self._conditions_fn(self._current_sol)
        else:
            mars = get_mars_conditions(self._current_sol)

        # Enrich with real NASA data (cached, refreshed every 5 min)
        self._refresh_nasa_data()
        if self._nasa_weather or self._nasa_solar:
            mars = enrich_from_nasa(mars, self._nasa_weather, self._nasa_solar)

        # Store for API access (GET /api/mars)
        self.mars_conditions = mars

        self._emit("cycle_start", {
            "sol": self._current_sol,
            "zone_count": len(zone_ids),
            "zones": zone_ids,
            "mars": mars.to_dict() if hasattr(mars, "to_dict") else {},
            "model_available": self._model.is_available() if self._model else False,
        })

        # Track transformed zones for closed-loop feedback
        transformed_zones: dict[str, ZoneState] = {}

        for zone_id in zone_ids:
            zone = self._sensor.get_latest(zone_id)
            if zone is None:
                continue

            # 2. Apply Mars Transform (pure functions, <1ms)
            zone = self._apply_mars_transform(zone, mars)
            transformed_zones[zone_id] = zone

            # Emit zone state after Mars transform
            self._emit("zone_state", zone.to_dict())

            # 3. Run Flight Rules — Tier 0, ALWAYS, safety floor
            energy = self._get_energy_budget()
            gas = self._get_gas_exchange()
            resource = self._get_resource_budget()

            commands, decisions = self._flight_rules.evaluate(
                zone, energy=energy, gas=gas, resource=resource,
            )

            # Mars-specific rules (radiation, etc.)
            mars_decisions = self._flight_rules.evaluate_mars(mars)
            decisions.extend(mars_decisions)

            # Staleness check
            staleness_decisions = self._flight_rules.evaluate_staleness(
                zone, time.time(),
            )
            decisions.extend(staleness_decisions)

            all_decisions.extend(decisions)

            # Emit each flight rule decision
            for decision in decisions:
                self._emit("flight_rule", decision.to_dict())
                # High-severity flight rules become alerts
                if decision.severity.value in ("critical", "high"):
                    self._emit("alert", {
                        "zone_id": zone_id,
                        "severity": decision.severity.value,
                        "rule": decision.action,
                        "reasoning": decision.reasoning,
                        "agent_name": decision.agent_name,
                    })

            # Execute flight rule commands immediately + track for feedback
            for cmd in commands:
                self._actuator.send_command(cmd)
                self._emit("command", cmd.to_dict())
                # Track command for actuator feedback verification next cycle
                self._pending_commands.setdefault(zone_id, []).append({
                    "device": cmd.device.value,
                    "action": cmd.action,
                    "value": cmd.value,
                    "timestamp": cmd.timestamp,
                })

            # 4. Persist telemetry (fire-and-forget)
            self._persist_telemetry(zone)

            # Emit telemetry event
            self._emit("telemetry", {
                "zone_id": zone_id,
                "temperature": zone.temperature,
                "humidity": zone.humidity,
                "pressure": zone.pressure,
                "light": zone.light,
                "water_level": zone.water_level,
                "fire_detected": zone.fire_detected,
                "timestamp": zone.last_updated,
                "source": zone.source,
            })

            # 5. Persist zone state
            self._state_store.put_zone_state(zone_id, zone)

            # Log flight rule decisions
            for decision in decisions:
                self._agent_log.append(decision)
                self._emit("decision", decision.to_dict())

        # 6. Compute deltas for all zones
        all_deltas: dict[str, dict] = {}
        for zone_id, zone in transformed_zones.items():
            desired = self._state_store.get_desired_state(zone_id)
            if desired is None:
                continue
            deltas = self._compute_deltas(zone, desired)
            self._emit("delta", {
                "zone_id": zone_id,
                "deltas": deltas,
                "in_range": len(deltas) == 0,
                "current": {"temperature": zone.temperature, "humidity": zone.humidity},
                "desired": {
                    "temp_min": desired.temp_min, "temp_max": desired.temp_max,
                    "humidity_min": desired.humidity_min, "humidity_max": desired.humidity_max,
                },
            })
            if deltas:
                all_deltas[zone_id] = deltas

        # 6b. Detect hardware failures (actuator sent command but sensor didn't respond)
        self._hardware_failures = self._detect_hardware_failures(transformed_zones)
        if self._hardware_failures:
            for hf in self._hardware_failures:
                self._emit("alert", {
                    "zone_id": hf["zone_id"],
                    "severity": "high",
                    "rule": "FR-ACT-001",
                    "reasoning": (
                        f"Hardware failure suspected: {hf['device']} command "
                        f"'{hf['action']}' sent but sensor did not respond"
                    ),
                    "agent_name": "FLIGHT_RULES",
                })

        # 7. Invoke agent parliament if deltas exist OR on routine interval OR hardware failures
        routine_check = (
            not all_deltas
            and not self._hardware_failures
            and self._cycle_count % self._PARLIAMENT_ROUTINE_INTERVAL == 0
        )
        if all_deltas or self._hardware_failures or routine_check:
            if routine_check:
                logger.info("parliament_routine_check")

            # Inject hardware failure context into council/agent_team
            if self._hardware_failures and hasattr(self._agent_team, "set_hardware_failures"):
                self._agent_team.set_hardware_failures(self._hardware_failures)

            parliament_decisions = self._invoke_parliament(
                transformed_zones, mars, all_deltas or {},
            )
            all_decisions.extend(parliament_decisions)

        # Tick resource tracker (random drift each cycle)
        self._resource_tracker.tick()

        # Closed-loop feedback: did previous cycle's actions improve things?
        self.last_feedback = self._compute_feedback(transformed_zones)
        if self.last_feedback:
            logger.info("closed_loop_feedback", feedback_count=len(self.last_feedback), zones=[f["zone_id"] for f in self.last_feedback])
            self._emit("feedback", self.last_feedback)

        # Flight rule self-improvement
        learned = self._flight_rules.learn()
        for decision in learned:
            self._agent_log.append(decision)
            self._emit("flight_rule", decision.to_dict())
        all_decisions.extend(learned)

        # Shadow evaluation: run candidate rules against live data (no commands)
        for zone_id, zone in transformed_zones.items():
            shadow_decisions = self._flight_rules.run_shadow(
                zone,
                energy=self._get_energy_budget(),
                gas=self._get_gas_exchange(),
                resource=self._get_resource_budget(),
            )
            for sd in shadow_decisions:
                self._emit("shadow_rule", sd.to_dict())
            all_decisions.extend(shadow_decisions)

        # Retrospective: periodic self-assessment of rules + feedback
        self._retrospective.ingest_feedback(self.last_feedback)
        retro_decisions = self._retrospective.tick()
        for rd in retro_decisions:
            self._agent_log.append(rd)
            self._emit("retrospective", rd.to_dict())
        all_decisions.extend(retro_decisions)

        # Store for next cycle comparison (Mars-transformed values)
        self._previous_zones = dict(transformed_zones)
        self._previous_decisions = list(all_decisions)

        cycle_duration_ms = round((time.time() - cycle_start) * 1000)
        fr_decisions = sum(1 for d in all_decisions if d.tier == Tier.FLIGHT_RULES)
        model_decisions = sum(1 for d in all_decisions if d.tier != Tier.FLIGHT_RULES)

        self._emit("cycle_complete", {
            "sol": self._current_sol,
            "total_decisions": len(all_decisions),
            "flight_rule_decisions": fr_decisions,
            "model_decisions": model_decisions,
            "zones_processed": list(transformed_zones.keys()),
            "feedback_count": len(self.last_feedback),
        })

        logger.info(
            "reconcile_cycle_complete",
            total_decisions=len(all_decisions),
            flight_rule_decisions=fr_decisions,
            model_decisions=model_decisions,
            zones_processed=len(transformed_zones),
            feedback_items=len(self.last_feedback),
            duration_ms=cycle_duration_ms,
        )
        structlog.contextvars.unbind_contextvars("cycle", "sol")

        return all_decisions

    # ── Closed-loop feedback ────────────────────────────────────────────

    def _get_energy_budget(self) -> EnergyBudget | None:
        """Return current energy budget from state or stored value."""
        if self._energy_budget is not None:
            return self._energy_budget
        if hasattr(self._state_store, "get_energy_budget"):
            return self._state_store.get_energy_budget()
        return None

    def _get_gas_exchange(self) -> GasExchange | None:
        """Return current gas exchange from state or stored value."""
        if self._gas_exchange is not None:
            return self._gas_exchange
        if hasattr(self._state_store, "get_gas_exchange"):
            return self._state_store.get_gas_exchange()
        return None

    def _get_resource_budget(self) -> ResourceBudget | None:
        """Return current resource budget from state or stored value."""
        if self._resource_budget is not None:
            return self._resource_budget
        if hasattr(self._state_store, "get_resource_budget"):
            return self._state_store.get_resource_budget()
        return None

    def set_energy_budget(self, energy: EnergyBudget) -> None:
        """Update the energy budget used by flight rules."""
        self._energy_budget = energy

    def set_gas_exchange(self, gas: GasExchange) -> None:
        """Update the gas exchange state used by flight rules."""
        self._gas_exchange = gas

    def set_resource_budget(self, resource: ResourceBudget) -> None:
        """Update the resource budget used by flight rules."""
        self._resource_budget = resource

    def _compute_feedback(self, current_zones: dict[str, ZoneState]) -> list[dict]:
        """Compare current zones to previous — did our actions help?"""
        if not self._previous_zones or not self._previous_decisions:
            return []

        feedback = []
        for zone_id, current in current_zones.items():
            prev = self._previous_zones.get(zone_id)
            if prev is None:
                continue

            zone_decisions = [
                d for d in self._previous_decisions if d.zone_id == zone_id
            ]
            if not zone_decisions:
                continue

            improvements: dict[str, dict] = {}

            # Temperature cooled down after a cooling action?
            if current.temperature < prev.temperature and any(
                d.action and ("cool" in d.action.lower() or "fan" in d.action.lower())
                for d in zone_decisions
            ):
                improvements["temperature"] = {
                    "before": prev.temperature,
                    "after": current.temperature,
                    "action": "cooling",
                }

            # Temperature warmed up after a heating action?
            if current.temperature > prev.temperature and any(
                d.action and ("heat" in d.action.lower() or "heater" in d.action.lower())
                for d in zone_decisions
            ):
                improvements["temperature"] = {
                    "before": prev.temperature,
                    "after": current.temperature,
                    "action": "heating",
                }

            # Humidity increased after irrigation/humidification?
            if current.humidity > prev.humidity and any(
                d.action
                and (
                    "humid" in d.action.lower()
                    or "irrigat" in d.action.lower()
                    or "pump" in d.action.lower()
                )
                for d in zone_decisions
            ):
                improvements["humidity"] = {
                    "before": prev.humidity,
                    "after": current.humidity,
                    "action": "humidification",
                }

            # Humidity decreased after ventilation?
            if current.humidity < prev.humidity and any(
                d.action and ("fan" in d.action.lower() or "ventilat" in d.action.lower())
                for d in zone_decisions
            ):
                improvements["humidity"] = {
                    "before": prev.humidity,
                    "after": current.humidity,
                    "action": "ventilation",
                }

            if improvements:
                feedback.append({"zone_id": zone_id, "improvements": improvements})

        return feedback

    # ── Hardware failure detection ────────────────────────────────────────

    def _detect_hardware_failures(
        self, current_zones: dict[str, ZoneState],
    ) -> list[dict]:
        """Detect actuator commands that had no effect on sensors.

        If a command was sent last cycle but the sensor didn't move in the
        expected direction, flag it as a suspected hardware failure.
        """
        failures: list[dict] = []

        for zone_id, commands in list(self._pending_commands.items()):
            current = current_zones.get(zone_id)
            prev = self._previous_zones.get(zone_id)
            if current is None or prev is None:
                continue

            remaining: list[dict] = []
            for cmd in commands:
                device = cmd["device"]
                action = cmd["action"]

                # Check if the expected sensor responded
                # Skip if sensor value is uniformly low across ALL zones
                # (indicates environmental event like dust storm, not hardware)
                failed = False
                if device == "light" and action == "on" and current.light <= prev.light and current.light < 50:
                    # Check if ALL zones have low light — environmental, not hardware
                    all_low = all(
                        z.light < 80 for z in current_zones.values()
                    )
                    if not all_low:
                        failed = True
                elif device == "heater" and action == "on" and current.temperature <= prev.temperature - 0.5:
                    failed = True
                elif device == "fan" and action == "on" and current.temperature >= prev.temperature + 0.5:
                    failed = True
                elif device == "pump" and action == "on" and current.water_level <= prev.water_level:
                    failed = True

                if failed:
                    failures.append({
                        "zone_id": zone_id,
                        "device": device,
                        "action": action,
                        "value": cmd["value"],
                        "sent_at": cmd["timestamp"],
                        "cycles": 1,
                    })
                    logger.warning(
                        "hardware_failure_suspected",
                        zone_id=zone_id,
                        device=device,
                        action=action,
                    )
                else:
                    remaining.append(cmd)

            # Clear verified commands, keep only unresolved
            if remaining:
                self._pending_commands[zone_id] = remaining
            else:
                self._pending_commands.pop(zone_id, None)

        return failures

    # ── Private helpers ──────────────────────────────────────────────────

    def _get_zone_ids(self) -> list[str]:
        """Get all known zone IDs from the sensor adapter."""
        if hasattr(self._sensor, "zone_ids"):
            return self._sensor.zone_ids
        return []

    def _apply_mars_transform(self, zone: ZoneState, mars) -> ZoneState:
        """Apply environmental transforms. Uses injectable transform_fn if set (e.g. Earth mode)."""
        if self._transform_fn is not None:
            return self._transform_fn(zone, mars)
        return ZoneState(
            zone_id=zone.zone_id,
            temperature=transform_temperature(zone.temperature, mars.sol),
            humidity=zone.humidity,
            pressure=transform_pressure(zone.pressure),
            light=transform_light(zone.light, mars.dust_opacity),
            water_level=zone.water_level,
            fire_detected=zone.fire_detected,
            last_updated=zone.last_updated,
            is_alive=zone.is_alive,
            source=zone.source,
        )

    def _persist_telemetry(self, zone: ZoneState) -> None:
        """Convert zone state to sensor readings and persist (fire-and-forget)."""
        now = zone.last_updated
        for sensor_type, value, unit in [
            (SensorType.TEMPERATURE, zone.temperature, "°C"),
            (SensorType.HUMIDITY, zone.humidity, "%"),
            (SensorType.PRESSURE, zone.pressure, "hPa"),
            (SensorType.LIGHT, zone.light, "lux"),
            (SensorType.WATER_LEVEL, zone.water_level, "mm"),
        ]:
            reading = SensorReading(
                zone_id=zone.zone_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                timestamp=now,
                source=zone.source,
            )
            self._telemetry_store.append(reading)

    def _compute_deltas(self, zone: ZoneState, desired: DesiredState) -> dict:
        """Compute which fields are outside the desired min/max range."""
        deltas = {}
        if zone.temperature < desired.temp_min:
            deltas["temperature"] = desired.temp_min - zone.temperature
        elif zone.temperature > desired.temp_max:
            deltas["temperature"] = zone.temperature - desired.temp_max

        if zone.humidity < desired.humidity_min:
            deltas["humidity"] = desired.humidity_min - zone.humidity
        elif zone.humidity > desired.humidity_max:
            deltas["humidity"] = zone.humidity - desired.humidity_max

        return deltas

    def _invoke_parliament(
        self,
        zones: dict[str, ZoneState],
        mars,
        deltas: dict[str, dict],
    ) -> list[AgentDecision]:
        """Invoke the 12-agent parliament for all zones with deltas.

        Falls back to single model.reason() if AgentTeam is not wired.
        """
        # Try full parliament first
        if self._agent_team is not None:
            try:
                # Feed closed-loop feedback to the parliament
                self._agent_team.set_feedback(self.last_feedback)

                self._emit("parliament_start", {
                    "zones_with_deltas": list(deltas.keys()),
                    "total_deltas": sum(len(d) for d in deltas.values()),
                })

                parliament_decisions = self._agent_team.analyze(zones, mars, deltas)

                logger.info(
                    "parliament_complete",
                    decisions=len(parliament_decisions),
                    zones_with_deltas=len(deltas),
                )
                return parliament_decisions

            except Exception:
                logger.exception("parliament_failed", fallback="single_model")

        # Fallback: single model.reason() per zone (no parliament)
        if self._model is None or not self._model.is_available():
            return []

        decisions: list[AgentDecision] = []
        for zone_id, zone_deltas in deltas.items():
            zone = zones.get(zone_id)
            if zone is None:
                continue

            desired = self._state_store.get_desired_state(zone_id)
            if desired is None:
                continue

            self._emit("model_invocation", {
                "zone_id": zone_id,
                "deltas": zone_deltas,
                "mode": "single_model_fallback",
            })

            try:
                context = {
                    "zone_id": zone_id,
                    "current": zone.to_dict(),
                    "desired": desired.to_dict(),
                    "deltas": zone_deltas,
                    "mars_conditions": mars.to_dict(),
                    "nutritional_status": self._nutrition.get_nutritional_status(),
                }
                prompt = (
                    f"Zone {zone_id} has deviations from desired state: {zone_deltas}. "
                    f"Current: temp={zone.temperature:.1f}°C, humidity={zone.humidity:.1f}%. "
                    f"Recommend actions."
                )
                response = self._model.reason(prompt, context)

                decision = AgentDecision(
                    timestamp=time.time(),
                    agent_name="MODEL",
                    severity=Severity.MEDIUM,
                    reasoning=f"Model analysis for zone {zone_id}: deltas={zone_deltas}",
                    action=response,
                    result="recommended",
                    zone_id=zone_id,
                    tier=Tier.LOCAL_MODEL,
                )
                decisions.append(decision)
                self._agent_log.append(decision)
                self._emit("decision", decision.to_dict())

            except Exception:
                logger.exception("model_invocation_failed", zone_id=zone_id)

        return decisions
