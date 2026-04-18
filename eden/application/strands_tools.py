"""Strands @tool wrappers for EDEN specialist agents.

Each tool function is created via closure to capture injected dependencies
(sensor, actuator, etc.) while exposing a clean @tool interface for the
Strands Agent.  Tools are created once per AgentTeam init and reused across
parliament cycles.
"""

from __future__ import annotations

import contextvars
import structlog
import time
import uuid
from typing import Any

logger = structlog.get_logger(__name__)

# Context var to track which council member is calling tools
_current_agent = contextvars.ContextVar('eden_agent_name', default=None)


def make_tools(
    sensor: Any,
    actuator: Any,
    state_store: Any,
    telemetry_store: Any,
    agent_log: Any,
    nutrition: Any,
    flight_engine: Any | None = None,
    syngenta_kb: Any | None = None,
    nasa_mcp: Any | None = None,
    event_bus: Any | None = None,
) -> list:
    """Create all @tool-decorated functions with injected dependencies.

    Returns a list of tool-decorated callables ready for Agent(tools=...).
    """
    from strands.tools import tool

    def _emit_tool_use(tool_name: str, args: dict | None = None) -> None:
        """Publish a tool_use event to the EventBus, tagged with agent name."""
        if event_bus is not None:
            agent_name = _current_agent.get()
            event_bus.publish("tool_use", {
                "tool": tool_name,
                "agent_name": agent_name,
                "args": {k: str(v)[:100] for k, v in (args or {}).items()},
                "timestamp": time.time(),
            })

    @tool
    def read_sensors(zone_id: str) -> dict:
        """Read current sensor telemetry for a greenhouse zone.

        Args:
            zone_id: Zone identifier (alpha, beta, gamma, delta).
        """
        _emit_tool_use("read_sensors", {"zone_id": zone_id})
        zone = sensor.get_latest(zone_id)
        if zone is None:
            return {"error": f"Zone {zone_id} not found or offline"}
        return zone.to_dict()

    @tool
    def read_all_zones() -> dict:
        """Read sensor telemetry for all greenhouse zones at once."""
        _emit_tool_use("read_all_zones")
        result = {}
        if hasattr(sensor, "_zones"):
            for zid, zone in sensor._zones.items():
                if zone is not None:
                    result[zid] = zone.to_dict()
        return result

    @tool
    def set_actuator_command(
        zone_id: str, device: str, action: str, value: float, reason: str
    ) -> str:
        """Send a command to a greenhouse actuator.

        Args:
            zone_id: Target zone (alpha, beta, gamma, delta).
            device: Device type (pump, light, fan, heater).
            action: Action to perform.
            value: Numeric value for the action.
            reason: Reason for this command.
        """
        from eden.domain.models import ActuatorCommand, DeviceType, Severity

        _emit_tool_use("set_actuator_command", {
            "zone_id": zone_id, "device": device, "action": action, "value": value,
        })
        cmd = ActuatorCommand(
            command_id=f"agent-{uuid.uuid4().hex[:8]}",
            zone_id=zone_id,
            device=DeviceType(device),
            action=action,
            value=value,
            reason=reason,
            priority=Severity.MEDIUM,
            timestamp=time.time(),
        )
        ok = actuator.send_command(cmd)
        return "OK" if ok else "FAILED"

    @tool
    def get_desired_state(zone_id: str) -> dict:
        """Get the target environmental parameters for a zone.

        Args:
            zone_id: Zone identifier (alpha, beta, gamma, delta).
        """
        _emit_tool_use("get_desired_state", {"zone_id": zone_id})
        ds = state_store.get_desired_state(zone_id)
        if ds is None:
            return {"error": f"No desired state for zone {zone_id}"}
        return ds.to_dict()

    @tool
    def get_nutritional_status() -> dict:
        """Get current crew nutritional status, deficiency risks, and dietary needs."""
        _emit_tool_use("get_nutritional_status")
        return nutrition.get_nutritional_status()

    @tool
    def get_mars_conditions(sol: int) -> dict:
        """Get current Mars environmental conditions for a given sol.

        Args:
            sol: Current mission sol (day number).
        """
        from eden.domain.mars_transform import get_mars_conditions as _gmc

        _emit_tool_use("get_mars_conditions", {"sol": sol})
        return _gmc(sol).to_dict()

    @tool
    def query_syngenta_kb(query: str) -> dict:
        """Query Syngenta crop knowledge base for agricultural guidance.

        Args:
            query: Natural language query about crops, diseases, or growing conditions.
        """
        _emit_tool_use("query_syngenta_kb", {"query": query})
        if syngenta_kb is not None and syngenta_kb.is_available():
            return syngenta_kb.query(query)
        return {"source": "offline", "result": "Syngenta KB unavailable — use local knowledge"}

    @tool
    def check_weather_on_mars() -> dict:
        """Check Mars weather conditions and dust storm forecasts via NASA data."""
        _emit_tool_use("check_weather_on_mars")
        if nasa_mcp is not None and nasa_mcp.is_available():
            return nasa_mcp.get_mars_weather()
        if syngenta_kb is not None and syngenta_kb.is_available():
            return syngenta_kb.check_greenhouse_scenarios(
                "current mars weather conditions dust storm forecast"
            )
        return {"source": "offline", "result": "Weather data unavailable — use local knowledge"}

    @tool
    def query_telemetry_trends(zone_id: str, hours: float) -> list:
        """Query recent telemetry readings for a zone within a time window.

        Args:
            zone_id: Zone identifier (alpha, beta, gamma, delta).
            hours: How many hours of history to query (e.g. 1.0 for last hour).
        """
        _emit_tool_use("query_telemetry_trends", {"zone_id": zone_id, "hours": hours})
        since = time.time() - hours * 3600
        readings = telemetry_store.query(zone_id, since, limit=100)
        return [r.to_dict() for r in readings]

    @tool
    def run_simulation(
        scenario_type: str,
        n_runs: int = 50,
        simulation_days: int = 14,
    ) -> dict:
        """Run Monte Carlo crop simulation comparing strategies for a scenario.

        Uses real mathematical models: GDD thermal time, Liebig's Law stress,
        VPD disease prediction, resource chain modeling. Returns ranked strategies
        with confidence intervals from N Monte Carlo runs.

        Args:
            scenario_type: One of: cme, water_failure, disease, dust_storm, nominal, nominal_constrained.
            n_runs: Number of Monte Carlo runs (default 50).
            simulation_days: How many days to simulate (default 14).
        """
        from eden.application.agent import run_simulation as _run_sim

        _emit_tool_use("run_simulation", {
            "scenario_type": scenario_type, "n_runs": n_runs, "days": simulation_days,
        })
        return _run_sim(
            scenario_type=scenario_type,
            n_runs=n_runs,
            simulation_days=simulation_days,
        )

    @tool
    def propose_new_flight_rule(
        rule_id: str,
        sensor_type: str,
        condition: str,
        threshold: float,
        device: str,
        action: str,
        value: float,
        cooldown_seconds: int,
        priority: str,
    ) -> str:
        """Propose a new flight rule based on observed patterns.

        The rule is stored as a CANDIDATE (not active) for safety review.
        Use this when you detect a recurring pattern that should become
        a deterministic rule.

        Args:
            rule_id: Unique rule ID (e.g. 'FR-CME-014').
            sensor_type: Sensor to monitor (temperature, humidity, pressure, light, water_level).
            condition: Comparison operator (lt, gt, eq, lte, gte).
            threshold: Trigger threshold value.
            device: Actuator device (fan, light, pump, heater, motor).
            action: Action to take when triggered.
            value: Numeric value for the action.
            cooldown_seconds: Seconds before rule can fire again.
            priority: Severity level (critical, high, medium, low).
        """
        _emit_tool_use("propose_flight_rule", {"rule_id": rule_id, "sensor_type": sensor_type})
        if flight_engine is None:
            return "Flight engine not available — rule proposal stored in log only"
        from eden.application.agent import propose_flight_rule as _propose
        _propose(
            flight_engine, rule_id, sensor_type, condition, threshold,
            device, action, value, cooldown_seconds, priority,
        )
        return f"Rule {rule_id} proposed as candidate (not active — requires safety review)"

    @tool
    def triage_zone(zone_id: str) -> dict:
        """Score a zone's salvageability and crew impact during a crisis.

        Returns salvageability score (0-1), zone status, and current state.
        Use during resource scarcity to decide which zones to prioritize.

        Args:
            zone_id: Zone identifier to triage.
        """
        _emit_tool_use("triage_zone", {"zone_id": zone_id})
        zone = sensor.get_latest(zone_id)
        if zone is None:
            return {"zone_id": zone_id, "salvageability": 0.0, "status": "offline"}
        score = 1.0
        if zone.fire_detected:
            score = 0.0
        else:
            if zone.water_level < 10:
                score -= 0.4
            if zone.temperature < 5 or zone.temperature > 40:
                score -= 0.3
            if zone.humidity < 20 or zone.humidity > 95:
                score -= 0.2
            score = max(0.0, score)
        return {
            "zone_id": zone_id,
            "salvageability": round(score, 2),
            "status": "alive" if zone.is_alive else "dead",
            "current_state": zone.to_dict(),
        }

    @tool
    def request_crew_intervention(
        task: str, urgency: str, estimated_minutes: int,
        zone_id: str = "global", category: str = "hardware",
    ) -> str:
        """Formally request astronaut time — a scarce resource on Mars.

        Astronaut time costs ~$50,000/hour equivalent. Only request when
        automated systems cannot resolve the issue (hardware failure,
        physical inspection, manual override).

        Args:
            task: Description of what the crew needs to do.
            urgency: How urgent (critical, high, medium, low).
            estimated_minutes: Estimated crew time needed.
            zone_id: Affected zone or 'global'.
            category: Type of issue: hardware, safety, biological, resource.
        """
        from eden.domain.models import AgentDecision, CrewEscalation, Severity, Tier

        _emit_tool_use("request_crew_intervention", {
            "task": task, "urgency": urgency, "minutes": estimated_minutes,
            "zone_id": zone_id, "category": category,
        })

        # Create formal escalation record
        escalation = CrewEscalation(
            escalation_id=f"esc-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            task=task,
            urgency=Severity(urgency),
            estimated_minutes=estimated_minutes,
            zone_id=zone_id,
            category=category,
        )

        # Log as agent decision
        decision = AgentDecision(
            timestamp=time.time(),
            agent_name="COUNCIL",
            severity=Severity(urgency),
            reasoning=f"Crew intervention needed: {task} (est. {estimated_minutes} min)",
            action=f"REQUEST_CREW: {task}",
            result="escalated",
            zone_id=zone_id,
            tier=Tier.CLOUD_MODEL,
        )
        agent_log.append(decision)

        # Emit real-time escalation event for dashboard
        if event_bus is not None:
            event_bus.publish("crew_escalation", escalation.to_dict())

        return f"Crew escalation created: {task} ({urgency}, ~{estimated_minutes}min, zone={zone_id})"

    tools_list = [
        read_sensors,
        read_all_zones,
        set_actuator_command,
        get_desired_state,
        get_nutritional_status,
        get_mars_conditions,
        query_syngenta_kb,
        check_weather_on_mars,
        query_telemetry_trends,
        run_simulation,
        propose_new_flight_rule,
        triage_zone,
        request_crew_intervention,
    ]

    logger.info("Created %d Strands @tool functions", len(tools_list))
    return tools_list
