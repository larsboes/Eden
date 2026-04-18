"""Tests for SqliteAdapter — local source of truth with WAL tracking."""

import json
import time

import pytest

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.domain.models import (
    AgentDecision,
    DesiredState,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)


@pytest.fixture
def db():
    adapter = SqliteAdapter(":memory:")
    yield adapter
    adapter.close()


# ── Fixtures ─────────────────────────────────────────────────────────────


def _zone_state(zone_id: str = "zone-a", temp: float = 22.0) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temp,
        humidity=60.0,
        pressure=1013.0,
        light=400.0,
        water_level=80.0,
        fire_detected=False,
        last_updated=time.time(),
        is_alive=True,
        source="test",
    )


def _desired_state(zone_id: str = "zone-a") -> DesiredState:
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


def _sensor_reading(zone_id: str = "zone-a", ts: float | None = None) -> SensorReading:
    return SensorReading(
        zone_id=zone_id,
        sensor_type=SensorType.TEMPERATURE,
        value=23.5,
        unit="celsius",
        timestamp=ts or time.time(),
        source="test",
    )


def _agent_decision(ts: float | None = None) -> AgentDecision:
    return AgentDecision(
        timestamp=ts or time.time(),
        agent_name="DEMETER",
        severity=Severity.MEDIUM,
        reasoning="Humidity too low",
        action="pump ON 50%",
        result="ok",
        zone_id="zone-a",
        tier=Tier.CLOUD_MODEL,
    )


# ── ZoneState CRUD ───────────────────────────────────────────────────────


class TestZoneState:
    def test_get_nonexistent_returns_none(self, db: SqliteAdapter):
        assert db.get_zone_state("no-such-zone") is None

    def test_put_then_get_roundtrip(self, db: SqliteAdapter):
        state = _zone_state("zone-a", temp=25.0)
        db.put_zone_state("zone-a", state)
        got = db.get_zone_state("zone-a")
        assert got is not None
        assert got.zone_id == "zone-a"
        assert got.temperature == 25.0
        assert got.humidity == state.humidity

    def test_put_overwrites(self, db: SqliteAdapter):
        db.put_zone_state("zone-a", _zone_state("zone-a", temp=20.0))
        db.put_zone_state("zone-a", _zone_state("zone-a", temp=30.0))
        got = db.get_zone_state("zone-a")
        assert got is not None
        assert got.temperature == 30.0

    def test_multiple_zones(self, db: SqliteAdapter):
        db.put_zone_state("zone-a", _zone_state("zone-a", temp=20.0))
        db.put_zone_state("zone-b", _zone_state("zone-b", temp=25.0))
        assert db.get_zone_state("zone-a").temperature == 20.0
        assert db.get_zone_state("zone-b").temperature == 25.0


# ── DesiredState CRUD ────────────────────────────────────────────────────


class TestDesiredState:
    def test_get_nonexistent_returns_none(self, db: SqliteAdapter):
        assert db.get_desired_state("no-such-zone") is None

    def test_put_then_get_roundtrip(self, db: SqliteAdapter):
        ds = _desired_state("zone-a")
        db.put_desired_state("zone-a", ds)
        got = db.get_desired_state("zone-a")
        assert got is not None
        assert got.zone_id == "zone-a"
        assert got.temp_min == 18.0
        assert got.water_budget_liters_per_day == 5.0

    def test_put_overwrites(self, db: SqliteAdapter):
        ds1 = _desired_state("zone-a")
        db.put_desired_state("zone-a", ds1)
        ds2 = DesiredState(
            zone_id="zone-a",
            temp_min=15.0,
            temp_max=30.0,
            humidity_min=35.0,
            humidity_max=85.0,
            light_hours=14.0,
            soil_moisture_min=25.0,
            soil_moisture_max=75.0,
            water_budget_liters_per_day=8.0,
        )
        db.put_desired_state("zone-a", ds2)
        got = db.get_desired_state("zone-a")
        assert got.temp_min == 15.0


# ── Telemetry ────────────────────────────────────────────────────────────


class TestTelemetry:
    def test_append_and_query(self, db: SqliteAdapter):
        now = time.time()
        r1 = _sensor_reading("zone-a", ts=now - 10)
        r2 = _sensor_reading("zone-a", ts=now - 5)
        r3 = _sensor_reading("zone-a", ts=now)
        db.append_telemetry(r1)
        db.append_telemetry(r2)
        db.append_telemetry(r3)
        results = db.query_telemetry("zone-a", since=now - 8, limit=10)
        assert len(results) == 2  # r2, r3
        assert results[0].timestamp == r2.timestamp

    def test_query_respects_limit(self, db: SqliteAdapter):
        now = time.time()
        for i in range(5):
            db.append_telemetry(_sensor_reading("zone-a", ts=now + i))
        results = db.query_telemetry("zone-a", since=0, limit=3)
        assert len(results) == 3

    def test_query_filters_by_zone(self, db: SqliteAdapter):
        now = time.time()
        db.append_telemetry(_sensor_reading("zone-a", ts=now))
        db.append_telemetry(_sensor_reading("zone-b", ts=now))
        results = db.query_telemetry("zone-a", since=0, limit=10)
        assert len(results) == 1
        assert results[0].zone_id == "zone-a"

    def test_roundtrip_preserves_fields(self, db: SqliteAdapter):
        r = _sensor_reading("zone-a")
        db.append_telemetry(r)
        results = db.query_telemetry("zone-a", since=0, limit=1)
        got = results[0]
        assert got.sensor_type == SensorType.TEMPERATURE
        assert got.value == 23.5
        assert got.unit == "celsius"
        assert got.source == "test"


# ── AgentLog ─────────────────────────────────────────────────────────────


class TestAgentLog:
    def test_append_and_query(self, db: SqliteAdapter):
        now = time.time()
        d1 = _agent_decision(ts=now - 10)
        d2 = _agent_decision(ts=now)
        db.append_agent_log(d1)
        db.append_agent_log(d2)
        results = db.query_agent_log(since=now - 5, limit=10)
        assert len(results) == 1
        assert results[0].timestamp == d2.timestamp

    def test_query_respects_limit(self, db: SqliteAdapter):
        now = time.time()
        for i in range(5):
            db.append_agent_log(_agent_decision(ts=now + i))
        results = db.query_agent_log(since=0, limit=2)
        assert len(results) == 2

    def test_roundtrip_preserves_fields(self, db: SqliteAdapter):
        d = _agent_decision()
        db.append_agent_log(d)
        results = db.query_agent_log(since=0, limit=1)
        got = results[0]
        assert got.agent_name == "DEMETER"
        assert got.severity == Severity.MEDIUM
        assert got.tier == Tier.CLOUD_MODEL
        assert got.action == "pump ON 50%"


# ── WAL ──────────────────────────────────────────────────────────────────


class TestWAL:
    def test_mark_pending_creates_entry(self, db: SqliteAdapter):
        db.mark_pending("zone_state", "zone-a", json.dumps({"test": 1}))
        pending = db.get_pending()
        assert len(pending) == 1
        assert pending[0]["table_name"] == "zone_state"
        assert pending[0]["key"] == "zone-a"
        assert pending[0]["status"] == "pending"

    def test_mark_synced_updates_status(self, db: SqliteAdapter):
        db.mark_pending("zone_state", "zone-a", json.dumps({"test": 1}))
        pending = db.get_pending()
        assert len(pending) == 1
        db.mark_synced(pending[0]["id"])
        pending = db.get_pending()
        assert len(pending) == 0

    def test_multiple_pending_entries(self, db: SqliteAdapter):
        db.mark_pending("zone_state", "zone-a", json.dumps({"a": 1}))
        db.mark_pending("telemetry", "zone-b", json.dumps({"b": 2}))
        db.mark_pending("agent_log", "LOG", json.dumps({"c": 3}))
        pending = db.get_pending()
        assert len(pending) == 3

    def test_get_pending_returns_data(self, db: SqliteAdapter):
        data = json.dumps({"zone_id": "zone-a", "temperature": 22.0})
        db.mark_pending("zone_state", "zone-a", data)
        pending = db.get_pending()
        assert json.loads(pending[0]["data"]) == {"zone_id": "zone-a", "temperature": 22.0}

    def test_mark_synced_only_affects_target(self, db: SqliteAdapter):
        db.mark_pending("zone_state", "zone-a", json.dumps({"a": 1}))
        db.mark_pending("telemetry", "zone-b", json.dumps({"b": 2}))
        pending = db.get_pending()
        db.mark_synced(pending[0]["id"])
        remaining = db.get_pending()
        assert len(remaining) == 1
        assert remaining[0]["table_name"] == "telemetry"
