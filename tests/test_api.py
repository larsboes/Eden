"""Tests for EDEN Dashboard API."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from eden.api import app
from eden.event_bus import EventBus
from eden.domain.models import (
    AgentDecision,
    CropProfile,
    DesiredState,
    MarsConditions,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Fixtures ─────────────────────────────────────────────────────────────

def _make_zone(zone_id: str = "alpha") -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=22.0,
        humidity=65.0,
        pressure=700.0,
        light=450.0,
        water_level=80.0,
        fire_detected=False,
        last_updated=time.time(),
        is_alive=True,
        source="simulated",
    )


def _make_desired(zone_id: str = "alpha") -> DesiredState:
    return DesiredState(
        zone_id=zone_id,
        temp_min=18.0,
        temp_max=26.0,
        humidity_min=50.0,
        humidity_max=80.0,
        light_hours=16.0,
        soil_moisture_min=40.0,
        soil_moisture_max=70.0,
        water_budget_liters_per_day=5.0,
    )


def _make_decision() -> AgentDecision:
    return AgentDecision(
        timestamp=time.time(),
        agent_name="DEMETER",
        severity=Severity.MEDIUM,
        reasoning="Temperature trending high",
        action="increase_fan_speed",
        result="proposed",
        zone_id="alpha",
        tier=Tier.CLOUD_MODEL,
    )


def _make_reading(zone_id: str = "alpha") -> SensorReading:
    return SensorReading(
        zone_id=zone_id,
        sensor_type=SensorType.TEMPERATURE,
        value=22.5,
        unit="C",
        timestamp=time.time(),
        source="simulated",
    )


def _make_nutrition() -> NutritionTracker:
    crew = NutritionTracker.get_default_crew()
    crops = [
        CropProfile("Lettuce", "alpha", 150.0, 13.0, 30, 3.5, 15.0, 24.0, 50.0, 80.0),
        CropProfile("Tomato", "beta", 180.0, 9.0, 80, 5.0, 18.0, 27.0, 60.0, 80.0),
    ]
    return NutritionTracker(crew, crops)


def _make_mars() -> MarsConditions:
    return MarsConditions(
        exterior_temp=-60.0,
        dome_temp=20.0,
        pressure_hpa=6.1,
        solar_irradiance=590.0,
        dust_opacity=0.3,
        sol=247,
        storm_active=False,
        radiation_alert=False,
    )


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with mocked ports."""
    zone = _make_zone()
    desired = _make_desired()
    decision = _make_decision()
    reading = _make_reading()

    state_store = MagicMock()
    state_store.get_zone_state.return_value = zone
    state_store.get_desired_state.return_value = desired

    telemetry_store = MagicMock()
    telemetry_store.query.return_value = [reading]

    agent_log = MagicMock()
    agent_log.query.return_value = [decision]

    model = MagicMock()
    model.is_available.return_value = True

    app.state.state_store = state_store
    app.state.telemetry_store = telemetry_store
    app.state.agent_log = agent_log
    app.state.nutrition = _make_nutrition()
    app.state.mars_conditions = _make_mars()
    app.state.model = model
    app.state.zone_ids = ["alpha", "beta"]
    app.state.reconciler_running = True
    app.state.model_tier = "cloud"
    app.state.mqtt_connected = True
    app.state.start_time = time.time() - 120.0
    app.state.event_bus = EventBus()
    app.state.flight_rules = MagicMock()
    app.state.flight_rules._rules = []
    app.state.reconciler = MagicMock()
    app.state.reconciler.last_feedback = []
    app.state.sim = None
    app.state.current_sol = 247

    return TestClient(app)


# ── Zone endpoints ───────────────────────────────────────────────────────


def test_list_zones(client: TestClient) -> None:
    resp = client.get("/api/zones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["zone_id"] == "alpha"
    assert "temperature" in data[0]
    assert "humidity" in data[0]
    assert "fire_detected" in data[0]
    assert "is_alive" in data[0]
    assert "health" in data[0]  # New field
    assert data[0]["health"] == "green"


def test_get_zone_detail(client: TestClient) -> None:
    resp = client.get("/api/zones/alpha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_id"] == "alpha"
    assert data["current_state"] is not None
    assert data["desired_state"] is not None
    assert isinstance(data["recent_telemetry"], list)
    assert len(data["recent_telemetry"]) == 1
    assert data["recent_telemetry"][0]["sensor_type"] == "temperature"
    assert "trends" in data


def test_get_zone_not_found(client: TestClient) -> None:
    app.state.state_store.get_zone_state.return_value = None
    app.state.state_store.get_desired_state.return_value = None
    app.state.telemetry_store.query.return_value = []
    resp = client.get("/api/zones/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_state"] is None
    assert data["desired_state"] is None


def test_get_zone_telemetry(client: TestClient) -> None:
    resp = client.get("/api/zones/alpha/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── Decisions endpoint ───────────────────────────────────────────────────


def test_list_decisions(client: TestClient) -> None:
    resp = client.get("/api/decisions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    d = data[0]
    assert d["agent_name"] == "DEMETER"
    assert d["severity"] == "medium"
    assert d["zone_id"] == "alpha"
    assert d["tier"] == 2  # Tier.CLOUD_MODEL


def test_list_decisions_with_params(client: TestClient) -> None:
    resp = client.get("/api/decisions?limit=10&since=1000.0")
    assert resp.status_code == 200
    app.state.agent_log.query.assert_called_with(1000.0, 10)


def test_list_decisions_filter_agent(client: TestClient) -> None:
    resp = client.get("/api/decisions?agent_name=SENTINEL")
    assert resp.status_code == 200
    data = resp.json()
    # DEMETER decision should be filtered out
    assert len(data) == 0


def test_latest_resolution(client: TestClient) -> None:
    resp = client.get("/api/decisions/latest-resolution")
    assert resp.status_code == 200
    # No COORDINATOR decision in mock, should return null
    data = resp.json()
    assert data is None


# ── Agents endpoint ──────────────────────────────────────────────────────


def test_list_agents(client: TestClient) -> None:
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 13  # 12 specialists + COORDINATOR
    names = {a["name"] for a in data}
    assert "SENTINEL" in names
    assert "FLORA" in names
    assert "COORDINATOR" in names
    # Check color and domain exist
    sentinel = next(a for a in data if a["name"] == "SENTINEL")
    assert sentinel["color"] == "#E53E3E"
    assert sentinel["domain"] == "Safety & Threats"


# ── Nutrition endpoint ───────────────────────────────────────────────────


def test_get_nutrition(client: TestClient) -> None:
    resp = client.get("/api/nutrition")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "deficiency_risks" in data
    assert "mission_projection" in data
    assert data["status"]["sol"] == 0
    assert len(data["status"]["crew"]) == 4
    assert data["status"]["crew"][0]["name"] == "Cmdr. Chen"


# ── Mars endpoint ────────────────────────────────────────────────────────


def test_get_mars(client: TestClient) -> None:
    resp = client.get("/api/mars")
    assert resp.status_code == 200
    data = resp.json()
    assert data["exterior_temp"] == -60.0
    assert data["sol"] == 247
    assert data["storm_active"] is False
    assert data["dust_opacity"] == 0.3


def test_get_mars_not_available(client: TestClient) -> None:
    app.state.mars_conditions = None
    resp = client.get("/api/mars")
    assert resp.status_code == 200
    assert "error" in resp.json()


# ── Flight Rules endpoint ────────────────────────────────────────────────


def test_get_flight_rules(client: TestClient) -> None:
    resp = client.get("/api/flight-rules")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules" in data
    assert "count" in data


# ── Resources endpoint ───────────────────────────────────────────────────


def test_get_resources(client: TestClient) -> None:
    resp = client.get("/api/resources")
    assert resp.status_code == 200
    data = resp.json()
    assert "water" in data
    assert "energy" in data
    assert "gas_exchange" in data


# ── Status endpoint ──────────────────────────────────────────────────────


def test_get_status(client: TestClient) -> None:
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reconciler_running"] is True
    assert data["model_available"] is True
    assert data["mqtt_connected"] is True
    assert data["zones_count"] == 2
    assert data["uptime"] >= 0
    assert "event_bus_subscribers" in data
    assert "total_events" in data
    assert "current_sol" in data


# ── Feedback endpoint ────────────────────────────────────────────────────


def test_get_feedback(client: TestClient) -> None:
    resp = client.get("/api/feedback")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Chaos endpoint ───────────────────────────────────────────────────────


def test_chaos_dust_storm(client: TestClient) -> None:
    resp = client.post("/api/chaos/dust_storm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "dust_storm"
    assert data["dust_opacity"] == 0.85


def test_chaos_water_line(client: TestClient) -> None:
    resp = client.post("/api/chaos/water_line_blocked")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "water_line_blocked"


def test_chaos_unknown_event(client: TestClient) -> None:
    resp = client.post("/api/chaos/alien_invasion")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "alien_invasion"
    assert data["status"] == "unknown_event"


# ── Events endpoint ─────────────────────────────────────────────────────


def test_get_events(client: TestClient) -> None:
    bus = app.state.event_bus
    bus.publish("test_event", {"key": "value"})
    resp = client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[-1]["type"] == "test_event"


def test_get_events_filtered(client: TestClient) -> None:
    bus = app.state.event_bus
    bus.publish("keep", {"a": 1})
    bus.publish("skip", {"b": 2})
    resp = client.get("/api/events?event_type=keep")
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["type"] == "keep" for e in data)


# ── SSE stream ───────────────────────────────────────────────────────────


def test_stream_endpoint_exists(client: TestClient) -> None:
    """Verify SSE endpoint is registered and routable."""
    routes = [r.path for r in app.routes]
    assert "/api/stream" in routes


def test_chaos_publishes_to_bus(client: TestClient) -> None:
    bus: EventBus = app.state.event_bus
    q = bus.subscribe()
    client.post("/api/chaos/dust_storm")
    assert not q.empty()
    event = q.get_nowait()
    assert event["type"] == "chaos"
    assert event["data"]["event_type"] == "dust_storm"


# ── EventBus unit tests ─────────────────────────────────────────────────


def test_event_bus_pub_sub() -> None:
    bus = EventBus()
    q = bus.subscribe()
    bus.publish("test", {"data": "hello"})
    assert not q.empty()
    event = q.get_nowait()
    assert event["type"] == "test"
    assert event["data"]["data"] == "hello"


def test_event_bus_unsubscribe() -> None:
    bus = EventBus()
    q = bus.subscribe()
    bus.unsubscribe(q)
    bus.publish("test", {"data": "hello"})
    assert q.empty()


def test_event_bus_history() -> None:
    bus = EventBus()
    bus.publish("a", {"x": 1})
    bus.publish("b", {"x": 2})
    bus.publish("a", {"x": 3})

    all_history = bus.get_history()
    assert len(all_history) == 3

    a_history = bus.get_history(event_type="a")
    assert len(a_history) == 2


def test_event_bus_subscriber_count() -> None:
    bus = EventBus()
    assert bus.subscriber_count == 0
    q1 = bus.subscribe()
    assert bus.subscriber_count == 1
    q2 = bus.subscribe()
    assert bus.subscriber_count == 2
    bus.unsubscribe(q1)
    assert bus.subscriber_count == 1
