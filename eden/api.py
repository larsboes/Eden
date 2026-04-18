"""EDEN Dashboard API — FastAPI backend for the Martian greenhouse dashboard.

Streams EVERYTHING: agent debates, sensor telemetry, flight rules, commands,
closed-loop feedback, Mars conditions, nutrition, chaos events.

All state is wired via app.state.* from __main__.py.
SSE stream pushes every event in real-time via the EventBus.
"""

from __future__ import annotations

import asyncio
import json
import queue
import time
import uuid

import structlog
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sse_starlette.sse import EventSourceResponse

logger = structlog.get_logger("eden.api")

app = FastAPI(title="EDEN Greenhouse API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ────────────────────────────────────────────


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging with request_id and duration."""

    # Paths to skip logging (high-frequency polling / SSE)
    _SKIP_PATHS = {"/api/stream", "/api/state"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000)
            logger.info(
                "http_request",
                status=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["x-request-id"] = request_id
            return response
        except Exception:
            duration_ms = round((time.time() - start) * 1000)
            logger.exception("http_request_error", duration_ms=duration_ms)
            raise
        finally:
            structlog.contextvars.unbind_contextvars("request_id", "method", "path")


app.add_middleware(RequestLoggingMiddleware)


# ── Zone Endpoints ───────────────────────────────────────────────────────


@app.get("/api/zones")
def list_zones() -> list[dict]:
    """List all zone states with current + desired + health status."""
    store = getattr(app.state, "state_store", None)
    zone_ids = getattr(app.state, "zone_ids", [])
    if not store:
        return []

    zones = []
    for zone_id in zone_ids:
        state = store.get_zone_state(zone_id)
        if state is None:
            continue

        desired = store.get_desired_state(zone_id)
        zone_data = state.to_dict()

        # Compute health status
        health = "green"
        if state.fire_detected:
            health = "red"
        elif not state.is_alive:
            health = "red"
        elif desired:
            if (state.temperature < desired.temp_min or
                    state.temperature > desired.temp_max):
                health = "yellow"
            if (state.humidity < desired.humidity_min or
                    state.humidity > desired.humidity_max):
                health = "yellow"

        zone_data["health"] = health
        zone_data["desired_state"] = desired.to_dict() if desired else None
        zones.append(zone_data)
    return zones


@app.get("/api/zones/{zone_id}")
def get_zone(zone_id: str) -> dict:
    """Single zone detail: current state + desired state + recent telemetry + trends."""
    store = getattr(app.state, "state_store", None)
    telem_store = getattr(app.state, "telemetry_store", None)
    if not store:
        return {"error": "Store not initialized"}

    state = store.get_zone_state(zone_id)
    desired = store.get_desired_state(zone_id)
    since = time.time() - 3600

    telemetry = []
    trends = {}
    if telem_store:
        readings = telem_store.query(zone_id, since, limit=200)
        telemetry = [r.to_dict() for r in readings]

        # Compute trends (min/max/avg per sensor type)
        by_type: dict[str, list[float]] = {}
        for r in readings:
            st = r.sensor_type.value if hasattr(r.sensor_type, "value") else str(r.sensor_type)
            by_type.setdefault(st, []).append(r.value)
        for st, values in by_type.items():
            trends[st] = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "count": len(values),
            }

    return {
        "zone_id": zone_id,
        "current_state": state.to_dict() if state else None,
        "desired_state": desired.to_dict() if desired else None,
        "recent_telemetry": telemetry,
        "trends": trends,
    }


@app.get("/api/zones/{zone_id}/telemetry")
def get_zone_telemetry(
    zone_id: str,
    since: float = Query(default=0.0),
    limit: int = Query(default=500, ge=1, le=5000),
    sensor_type: str | None = Query(default=None),
) -> list[dict]:
    """Raw telemetry for a zone. Optionally filter by sensor_type."""
    telem_store = getattr(app.state, "telemetry_store", None)
    if not telem_store:
        return []

    if since == 0.0:
        since = time.time() - 3600  # Default: last hour

    readings = telem_store.query(zone_id, since, limit)
    if sensor_type:
        readings = [r for r in readings
                    if (r.sensor_type.value if hasattr(r.sensor_type, "value")
                        else str(r.sensor_type)) == sensor_type]
    return [r.to_dict() for r in readings]


# ── Agent / Parliament Endpoints ─────────────────────────────────────────


@app.get("/api/decisions")
def list_decisions(
    limit: int = Query(default=50, ge=1, le=500),
    since: float = Query(default=0.0),
    agent_name: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    tier: int | None = Query(default=None),
) -> list[dict]:
    """Agent parliament decisions. Filter by agent, zone, tier."""
    agent_log = getattr(app.state, "agent_log", None)
    if not agent_log:
        return []

    decisions = agent_log.query(since, limit)
    result = []
    for d in decisions:
        d_dict = d.to_dict()
        if agent_name and d_dict.get("agent_name") != agent_name:
            continue
        if zone_id and d_dict.get("zone_id") != zone_id:
            continue
        if tier is not None and d_dict.get("tier") != tier:
            continue
        result.append(d_dict)
    return result


@app.get("/api/decisions/latest-resolution")
def get_latest_resolution() -> dict | None:
    """The most recent COORDINATOR consensus resolution."""
    agent_log = getattr(app.state, "agent_log", None)
    if not agent_log:
        return None

    decisions = agent_log.query(since=0.0, limit=200)
    for d in reversed(decisions):
        if d.agent_name == "COORDINATOR" and d.action == "CONSENSUS_RESOLUTION":
            return d.to_dict()
    return None


@app.get("/api/agents")
def list_agents() -> list[dict]:
    """List council member personas + legacy parliament agents."""
    from eden.application.council import COUNCIL_PERSONAS

    council_members = [
        {
            "name": p["name"],
            "domain": p["trait"],
            "color": _PERSONA_COLORS.get(p["name"], "#8B5CF6"),
            "icon": p["emoji"],
            "type": "council",
        }
        for p in COUNCIL_PERSONAS
    ]

    legacy_agents = [
        {"name": "SENTINEL", "domain": "Safety & Threats", "color": "#E53E3E", "icon": "shield", "type": "parliament"},
        {"name": "FLORA", "domain": "Plant Voice (per zone)", "color": "#38A169", "icon": "leaf", "type": "parliament"},
        {"name": "PATHFINDER", "domain": "Disease Detection", "color": "#8B6914", "icon": "microscope", "type": "parliament"},
        {"name": "TERRA", "domain": "Soil & Root Health", "color": "#6B4226", "icon": "soil", "type": "parliament"},
        {"name": "DEMETER", "domain": "Crops & Environment", "color": "#D69E2E", "icon": "wheat", "type": "parliament"},
        {"name": "ATMOS", "domain": "Atmosphere Control", "color": "#63B3ED", "icon": "cloud", "type": "parliament"},
        {"name": "AQUA", "domain": "Water & Resources", "color": "#3182CE", "icon": "droplet", "type": "parliament"},
        {"name": "HELIOS", "domain": "Energy & Light", "color": "#ECC94B", "icon": "sun", "type": "parliament"},
        {"name": "VITA", "domain": "Crew Nutrition", "color": "#ED64A6", "icon": "heart", "type": "parliament"},
        {"name": "HESTIA", "domain": "Morale & Food Culture", "color": "#9F7AEA", "icon": "home", "type": "parliament"},
        {"name": "ORACLE", "domain": "Forecasting", "color": "#5A67D8", "icon": "crystal-ball", "type": "parliament"},
        {"name": "CHRONOS", "domain": "Mission Planning", "color": "#A0AEC0", "icon": "clock", "type": "parliament"},
        {"name": "COORDINATOR", "domain": "Consensus Resolution", "color": "#FFFFFF", "icon": "gavel", "type": "parliament"},
    ]
    return council_members + legacy_agents


_PERSONA_COLORS = {
    "Lena": "#ef4444",    # Red — safety-first
    "Kai": "#f59e0b",     # Amber — optimization
    "Yara": "#22c55e",    # Green — plant biologist
    "Marcus": "#06b6d4",  # Cyan — resource hawk
    "Suki": "#a855f7",    # Purple — crew advocate
    "Niko": "#3b82f6",    # Blue — data-driven
    "Ren": "#64748b",     # Slate — mission planner
}


# ── Mars Conditions ──────────────────────────────────────────────────────


@app.get("/api/mars")
def get_mars() -> dict:
    """Current Mars conditions (updated each reconciliation cycle)."""
    # Read live from reconciler (updated every cycle)
    reconciler = getattr(app.state, "reconciler", None)
    mars = None
    if reconciler is not None:
        rc_mars = getattr(reconciler, "mars_conditions", None)
        # Only use if it's a real MarsConditions with to_dict (not a MagicMock)
        if rc_mars is not None and type(rc_mars).__name__ == "MarsConditions":
            mars = rc_mars
    # Fallback to static app.state
    if mars is None:
        mars = getattr(app.state, "mars_conditions", None)
    if mars is None:
        return {"error": "Mars conditions not yet available"}
    if hasattr(mars, "to_dict"):
        return mars.to_dict()
    return mars


# ── Nutrition ────────────────────────────────────────────────────────────


@app.get("/api/nutrition")
def get_nutrition() -> dict:
    """Crew nutritional status, deficiency risks, mission projection."""
    tracker = getattr(app.state, "nutrition", None)
    if not tracker:
        return {"error": "Nutrition tracker not initialized"}

    return {
        "status": tracker.get_nutritional_status(),
        "deficiency_risks": tracker.get_deficiency_risks(),
        "mission_projection": tracker.get_mission_projection(),
    }


# ── Flight Rules ─────────────────────────────────────────────────────────


@app.get("/api/flight-rules")
def list_flight_rules() -> dict:
    """All flight rules: active, candidates, shadow hits, lifecycle."""
    fr = getattr(app.state, "flight_rules", None)
    if not fr:
        return {"rules": [], "candidates": [], "managed": [], "count": 0}

    rules = []
    if hasattr(fr, "rules"):
        for rule in fr.rules:
            rules.append(rule.to_dict())

    candidates = []
    if hasattr(fr, "get_candidates"):
        for c in fr.get_candidates():
            candidates.append({
                **c.to_dict(),
                "shadow_hits": fr.get_shadow_hits().get(c.rule_id, 0),
            })

    managed = []
    if hasattr(fr, "get_managed_rules"):
        managed = fr.get_managed_rules()

    return {
        "rules": rules,
        "candidates": candidates,
        "managed": managed,
        "count": len(rules),
    }


@app.get("/api/retrospective")
def get_retrospective(
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    """Recent retrospective reports from the self-assessment system."""
    reconciler = getattr(app.state, "reconciler", None)
    if reconciler is None:
        return []
    retro = getattr(reconciler, "_retrospective", None)
    if retro is None:
        return []
    return retro.get_reports(limit=limit)


@app.post("/api/retrospective/trigger")
def trigger_retrospective() -> dict:
    """Manually trigger a retrospective analysis cycle."""
    reconciler = getattr(app.state, "reconciler", None)
    if reconciler is None:
        return {"error": "Reconciler not initialized"}
    retro = getattr(reconciler, "_retrospective", None)
    if retro is None:
        return {"error": "Retrospective not initialized"}

    decisions = retro.run()
    reports = retro.get_reports(limit=1)

    bus = getattr(app.state, "event_bus", None)
    if bus is not None:
        bus.publish("retrospective_triggered", {
            "decisions": len(decisions),
            "manual": True,
        })

    return {
        "decisions": [d.to_dict() for d in decisions],
        "report": reports[0] if reports else None,
    }


# ── Resources ────────────────────────────────────────────────────────────


@app.get("/api/resources")
def get_resources() -> dict:
    """Resource budgets: water, energy, gas exchange."""
    reconciler = getattr(app.state, "reconciler", None)
    result = {
        "water": None,
        "energy": None,
        "gas_exchange": None,
    }
    if reconciler:
        eb = getattr(reconciler, "_energy_budget", None)
        gb = getattr(reconciler, "_gas_exchange", None)
        rb = getattr(reconciler, "_resource_budget", None)
        if eb and hasattr(eb, "to_dict"):
            result["energy"] = eb.to_dict()
        if gb and hasattr(gb, "to_dict"):
            result["gas_exchange"] = gb.to_dict()
        if rb and hasattr(rb, "to_dict"):
            result["water"] = rb.to_dict()
    return result


# ── System Status ────────────────────────────────────────────────────────


@app.get("/api/status")
def get_status() -> dict:
    """System health overview — everything the dashboard header needs."""
    model = getattr(app.state, "model", None)
    model_available = model.is_available() if model else False
    event_bus = getattr(app.state, "event_bus", None)

    # Determine model tier
    model_tier = "none"
    if model_available and model:
        if hasattr(model, "_models"):
            for m in model._models:
                if m.is_available():
                    model_tier = type(m).__name__.replace("Adapter", "").lower()
                    break
        else:
            model_tier = type(model).__name__.replace("Adapter", "").lower()

    return {
        "reconciler_running": getattr(app.state, "reconciler_running", False),
        "model_available": model_available,
        "model_tier": model_tier,
        "mqtt_connected": getattr(app.state, "mqtt_connected", False),
        "zones_count": len(getattr(app.state, "zone_ids", [])),
        "uptime": time.time() - getattr(app.state, "start_time", time.time()),
        "event_bus_subscribers": event_bus.subscriber_count if event_bus else 0,
        "total_events": event_bus.event_count if event_bus else 0,
        "current_sol": getattr(app.state, "current_sol", 0),
    }


# ── Feedback ─────────────────────────────────────────────────────────────


@app.get("/api/feedback")
def get_feedback() -> list[dict]:
    """Closed-loop feedback — did previous cycle's actions improve conditions?"""
    reconciler = getattr(app.state, "reconciler", None)
    if reconciler is not None:
        return getattr(reconciler, "last_feedback", [])
    return []


# ── Chaos Injection ──────────────────────────────────────────────────────


@app.get("/api/state")
def get_combined_state() -> dict:
    """Combined state endpoint — everything the dashboard needs in one poll.

    Returns zones, recent decisions, system status, mars conditions, and nutrition.
    """
    from eden.domain.mars_transform import get_mars_conditions

    # Zones
    zones = []
    zone_ids = getattr(app.state, "zone_ids", [])
    for zone_id in zone_ids:
        state = app.state.state_store.get_zone_state(zone_id)
        if state is not None:
            zones.append(state.to_dict())

    # If no persisted zones yet, read directly from sensor adapter
    if not zones:
        sensor = getattr(app.state, "sensor", None)
        if sensor is not None:
            for zone_id in sensor.zone_ids:
                latest = sensor.get_latest(zone_id)
                if latest is not None:
                    zones.append(latest.to_dict())

    # Recent decisions (last 5 minutes)
    since = time.time() - 300
    decisions = app.state.agent_log.query(since, limit=50)

    # Status
    model = getattr(app.state, "model", None)
    model_available = model.is_available() if model else False

    # Determine model tier dynamically (same logic as /api/status)
    model_tier = "none"
    if model_available and model:
        if hasattr(model, "_models"):
            for m in model._models:
                if m.is_available():
                    model_tier = type(m).__name__.replace("Adapter", "").lower()
                    break
        else:
            model_tier = type(model).__name__.replace("Adapter", "").lower()

    # Mars conditions
    reconciler = getattr(app.state, "reconciler", None)
    sol = getattr(reconciler, "_current_sol", 247) if reconciler else 247
    mars = get_mars_conditions(sol)

    # Flight rules — serialized list
    fr_engine = getattr(app.state, "flight_rules", None)
    flight_rules_count = len(fr_engine.rules) if fr_engine and hasattr(fr_engine, "rules") else 0
    flight_rules_list: list[dict] = []
    if fr_engine and hasattr(fr_engine, "rules"):
        for r in fr_engine.rules:
            flight_rules_list.append({
                "id": r.rule_id,
                "rule": f"{r.sensor_type.value} {r.condition} {r.threshold} \u2192 {r.device.value} {r.action}",
                "status": "triggered" if r.rule_id in fr_engine._cooldowns else "armed",
                "priority": r.priority.value.upper(),
                "source": "Earth baseline",
                "count": 1 if r.rule_id in fr_engine._cooldowns else 0,
                "enabled": r.enabled,
            })

    # Candidate (learned) flight rules
    if fr_engine and hasattr(fr_engine, "get_candidates"):
        for r in fr_engine.get_candidates():
            flight_rules_list.append({
                "id": r.rule_id,
                "rule": f"{r.sensor_type.value} {r.condition} {r.threshold} \u2192 {r.device.value} {r.action}",
                "status": "proposed",
                "priority": r.priority.value.upper(),
                "source": "Learned",
                "count": 0,
                "enabled": False,
            })

    # Resources
    resource_tracker = getattr(app.state, "resource_tracker", None)
    resources = resource_tracker.get_state() if resource_tracker else {}

    # Nutrition
    nutrition_tracker = getattr(app.state, "nutrition", None)
    nutrition_data: dict = {}
    if nutrition_tracker:
        nutrition_data = {
            "status": nutrition_tracker.get_nutritional_status(),
            "deficiency_risks": nutrition_tracker.get_deficiency_risks(),
            "mission_projection": nutrition_tracker.get_mission_projection(),
        }

    # Crew (enriched with dashboard-matching metadata)
    crew_data: list[dict] = []
    if nutrition_tracker:
        crew_meta = {
            "Cmdr. Chen": {"role": "Commander", "emoji": "\U0001f469\u200d\U0001f680", "preference": "Spinach", "dietaryFlags": []},
            "Dr. Okafor": {"role": "Science Lead", "emoji": "\U0001f468\u200d\U0001f52c", "preference": "Lentil soup", "dietaryFlags": ["vegetarian"]},
            "Eng. Petrov": {"role": "Engineer", "emoji": "\U0001f468\u200d\U0001f680", "preference": "Potato", "dietaryFlags": []},
            "Sci. Tanaka": {"role": "Botanist", "emoji": "\U0001f469\u200d\U0001f52c", "preference": "Tomato", "dietaryFlags": []},
        }
        for m in nutrition_tracker.crew:
            meta = crew_meta.get(m.name, {})
            crew_data.append({
                "name": m.name,
                "role": meta.get("role", "Crew"),
                "emoji": meta.get("emoji", "\U0001f464"),
                "kcalTarget": m.daily_kcal_target,
                "kcalActual": m.current_kcal_intake,
                "protein": round(m.current_protein_intake / m.daily_protein_target * 100) if m.daily_protein_target > 0 else 0,
                "preference": meta.get("preference", ""),
                "dietaryFlags": meta.get("dietaryFlags", []),
            })

    return {
        "zones": zones,
        "decisions": [d.to_dict() for d in decisions],
        "status": {
            "reconciler_running": getattr(app.state, "reconciler_running", False),
            "model_available": model_available,
            "model_tier": model_tier,
            "mqtt_connected": getattr(app.state, "mqtt_connected", False),
            "zones_count": len(zones),
            "uptime": time.time() - getattr(app.state, "start_time", time.time()),
            "flight_rules_count": flight_rules_count,
        },
        "mars": mars.to_dict(),
        "sol": sol,
        "timestamp": time.time(),
        "resources": resources,
        "flight_rules": flight_rules_list,
        "nutrition": nutrition_data,
        "crew": crew_data,
    }


@app.post("/api/simulate/{scenario_type}")
def run_simulation_endpoint(
    scenario_type: str,
    n_runs: int = Query(default=50, ge=5, le=200),
    days: int = Query(default=14, ge=1, le=60),
) -> dict:
    """Run Monte Carlo simulation comparing strategies for a scenario.

    Scenario types: cme, water_failure, disease, dust_storm, nominal.
    """
    from eden.application.agent import run_simulation

    return run_simulation(
        scenario_type=scenario_type,
        n_runs=n_runs,
        simulation_days=days,
    )


@app.get("/api/debug/sensor")
def debug_sensor() -> dict:
    """Debug: inspect sensor adapter internal state."""
    sensor = getattr(app.state, "sensor", None)
    if sensor is None:
        return {"error": "no sensor"}
    return {
        "type": type(sensor).__name__,
        "has_inject": hasattr(sensor, "inject_event"),
        "fire_zones": list(getattr(sensor, "_fire_zones", [])),
        "dead_zones": list(getattr(sensor, "_dead_zones", [])),
        "zone_ids": list(getattr(sensor, "zone_ids", [])),
        "raw_state": {
            zid: dict(s) for zid, s in getattr(sensor, "_zones", {}).items()
        },
    }


@app.post("/api/chaos/{event_type}")
def trigger_chaos(event_type: str) -> dict:
    """Inject a failure event for demo/testing."""
    import time as _time

    logger.info("chaos_injection_requested", event_type=event_type)
    injected_zones: list[str] = []

    # Inject into sensor adapter (works for BOTH memory and MQTT modes)
    sensor = getattr(app.state, "sensor", None)
    if sensor is not None and hasattr(sensor, "inject_event"):
        # dust_storm and recover affect all zones
        if event_type in ("dust_storm", "recover"):
            zone_ids = list(getattr(sensor, "zone_ids", []))
            if event_type == "dust_storm":
                sensor.inject_event("", event_type)
            else:
                for zid in zone_ids:
                    sensor.inject_event(zid, event_type)
            injected_zones = zone_ids
        else:
            # Pick first zone for targeted events, or all for broad ones
            zone_ids = list(getattr(sensor, "zone_ids", []))
            if event_type in ("fire", "sensor_failure", "light_failure"):
                # Hit the first zone for drama
                target = zone_ids[0] if zone_ids else ""
                sensor.inject_event(target, event_type)
                injected_zones = [target]
            elif event_type == "water_line_blocked":
                target = zone_ids[0] if zone_ids else ""
                sensor.inject_event(target, event_type)
                injected_zones = [target]
            else:
                for zone_id in zone_ids:
                    sensor.inject_event(zone_id, event_type)
                injected_zones = zone_ids

    # Also inject into MQTT SimulatedSensors if available
    sim = getattr(app.state, "sim", None)
    if sim:
        sensor_event_map = {
            "fire": "fire",
            "sensor_failure": "sensor_failure",
            "dust_storm": "spike",
            "water_line_blocked": "drop",
            "light_failure": "light_failure",
        }
        sensor_event = sensor_event_map.get(event_type)
        if sensor_event:
            for zone_id in getattr(sim, "_zones", []):
                sim.inject_event(zone_id, sensor_event)

    event = {
        "event_type": event_type,
        "description": f"Chaos injection: {event_type}",
        "timestamp": _time.time(),
        "affected_zones": injected_zones,
    }

    bus = getattr(app.state, "event_bus", None)
    if bus is not None:
        bus.publish("chaos", event)

    logger.info("chaos_injection_complete", event_type=event_type, affected_zones=injected_zones)
    return event


# ── Crew Escalation Endpoints ──────────────────────────────────────────


@app.get("/api/escalations")
def get_escalations(
    status: str | None = Query(default=None),
) -> list[dict]:
    """List crew escalations, optionally filtered by status."""
    council = getattr(app.state, "agent_team", None)
    if council is None or not hasattr(council, "get_escalations"):
        return []
    return [e.to_dict() for e in council.get_escalations(status=status)]


@app.post("/api/escalations/{escalation_id}/acknowledge")
def acknowledge_escalation(escalation_id: str) -> dict:
    """Crew acknowledges an escalation (marks as seen)."""
    council = getattr(app.state, "agent_team", None)
    if council is None or not hasattr(council, "update_escalation"):
        return {"error": "Council not available"}
    ok = council.update_escalation(escalation_id, "acknowledged", by="crew")
    return {"ok": ok, "escalation_id": escalation_id, "status": "acknowledged"}


@app.post("/api/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: str) -> dict:
    """Crew resolves an escalation (hardware fixed, issue resolved)."""
    council = getattr(app.state, "agent_team", None)
    if council is None or not hasattr(council, "update_escalation"):
        return {"error": "Council not available"}
    ok = council.update_escalation(escalation_id, "resolved")
    return {"ok": ok, "escalation_id": escalation_id, "status": "resolved"}


@app.post("/api/escalations/{escalation_id}/dismiss")
def dismiss_escalation(escalation_id: str) -> dict:
    """Crew dismisses an escalation (false alarm)."""
    council = getattr(app.state, "agent_team", None)
    if council is None or not hasattr(council, "update_escalation"):
        return {"error": "Council not available"}
    ok = council.update_escalation(escalation_id, "dismissed")
    return {"ok": ok, "escalation_id": escalation_id, "status": "dismissed"}


# ── Event History ────────────────────────────────────────────────────────


@app.get("/api/events")
def get_events(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """Recent events from the EventBus history. Great for catching up."""
    bus = getattr(app.state, "event_bus", None)
    if not bus:
        return []
    return bus.get_history(event_type=event_type, limit=limit)


# ── SSE Real-Time Stream ────────────────────────────────────────────────


@app.get("/api/stream")
async def stream_events(
    types: str | None = Query(
        default=None,
        description="Comma-separated event types to filter (e.g., 'decision,telemetry,alert')",
    ),
) -> EventSourceResponse:
    """SSE stream of ALL real-time events.

    Event types:
    - cycle_start / cycle_complete — reconciliation loop heartbeat
    - zone_state — zone sensor data after Mars transform
    - flight_rule — flight rule triggered (Tier 0)
    - command — actuator command sent
    - telemetry — raw sensor readings persisted
    - delta — zone deviations from desired state
    - decision — any agent decision (all tiers)
    - agent_started — specialist begins analysis
    - agent_proposal — Round 1 proposal from a specialist
    - deliberation_start — Round 2 begins
    - deliberation_response — agent response in deliberation
    - coordinator_start — Round 3 begins
    - coordinator_resolution — final COORDINATOR consensus
    - feedback — closed-loop results (did actions work?)
    - alert — critical/high severity events
    - chaos — injected failure events
    - heartbeat — zone liveness
    - ping — keepalive (every 15s)

    Optional: ?types=decision,alert,chaos to filter
    """
    bus = getattr(app.state, "event_bus", None)
    if bus is None:
        async def empty():
            yield {
                "event": "error",
                "data": json.dumps({"error": "Event bus not initialized"}),
            }
        return EventSourceResponse(empty())

    type_filter = set(types.split(",")) if types else None
    sub_queue = bus.subscribe()
    logger.info("sse_stream_connected", type_filter=list(type_filter) if type_filter else "all")

    async def event_generator():
        try:
            while True:
                try:
                    # Poll the thread-safe queue from async context
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: sub_queue.get(timeout=15.0),
                    )

                    event_type = event.get("type", "message")

                    # Apply filter if specified
                    if type_filter and event_type not in type_filter:
                        continue

                    yield {
                        "event": event_type,
                        "data": json.dumps(event.get("data", event), default=str),
                        "id": str(event.get("seq", "")),
                    }
                except queue.Empty:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            bus.unsubscribe(sub_queue)

    return EventSourceResponse(event_generator())
