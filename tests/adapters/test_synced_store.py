"""Tests for SyncedStore — WAL orchestrator wrapping local + remote."""

import json
import time
import threading
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.adapters.synced_store import SyncedStore
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
def local_db():
    adapter = SqliteAdapter(":memory:")
    yield adapter
    adapter.close()


@pytest.fixture
def mock_remote():
    remote = MagicMock()
    return remote


@pytest.fixture
def synced(local_db, mock_remote):
    store = SyncedStore(local=local_db, remote=mock_remote, sync_interval=0.1)
    yield store
    store.stop()


@pytest.fixture
def local_only(local_db):
    store = SyncedStore(local=local_db, remote=None)
    yield store
    store.stop()


# ── Helpers ──────────────────────────────────────────────────────────────


def _zone_state(zone_id: str = "zone-a") -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=22.0,
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


def _sensor_reading(zone_id: str = "zone-a") -> SensorReading:
    return SensorReading(
        zone_id=zone_id,
        sensor_type=SensorType.TEMPERATURE,
        value=23.5,
        unit="celsius",
        timestamp=time.time(),
        source="test",
    )


def _agent_decision() -> AgentDecision:
    return AgentDecision(
        timestamp=time.time(),
        agent_name="DEMETER",
        severity=Severity.MEDIUM,
        reasoning="Humidity too low",
        action="pump ON 50%",
        result="ok",
        zone_id="zone-a",
        tier=Tier.CLOUD_MODEL,
    )


# ── Writes go to local AND remote ───────────────────────────────────────


class TestWritesBothStores:
    def test_put_zone_state_writes_local_and_remote(self, synced, local_db, mock_remote):
        state = _zone_state("zone-a")
        synced.put_zone_state("zone-a", state)

        # Local has the data
        got = local_db.get_zone_state("zone-a")
        assert got is not None
        assert got.temperature == 22.0

        # Remote was called
        mock_remote.put_zone_state.assert_called_once_with("zone-a", state)

    def test_put_desired_state_writes_local_and_remote(self, synced, local_db, mock_remote):
        ds = _desired_state("zone-a")
        synced.put_desired_state("zone-a", ds)

        got = local_db.get_desired_state("zone-a")
        assert got is not None
        mock_remote.put_desired_state.assert_called_once_with("zone-a", ds)

    def test_append_telemetry_writes_local_and_remote(self, synced, local_db, mock_remote):
        reading = _sensor_reading("zone-a")
        synced.append_telemetry(reading)

        results = local_db.query_telemetry("zone-a", since=0, limit=10)
        assert len(results) == 1
        mock_remote.append_telemetry.assert_called_once_with(reading)

    def test_append_agent_log_writes_local_and_remote(self, synced, local_db, mock_remote):
        decision = _agent_decision()
        synced.append_agent_log(decision)

        results = local_db.query_agent_log(since=0, limit=10)
        assert len(results) == 1
        mock_remote.append_agent_log.assert_called_once_with(decision)


# ── Writes go to local only when remote is None ─────────────────────────


class TestLocalOnlyMode:
    def test_put_zone_state_local_only(self, local_only, local_db):
        state = _zone_state("zone-a")
        local_only.put_zone_state("zone-a", state)
        got = local_db.get_zone_state("zone-a")
        assert got is not None
        assert got.temperature == 22.0

    def test_append_telemetry_local_only(self, local_only, local_db):
        reading = _sensor_reading("zone-a")
        local_only.append_telemetry(reading)
        results = local_db.query_telemetry("zone-a", since=0, limit=10)
        assert len(results) == 1

    def test_no_sync_thread_when_no_remote(self, local_only):
        # The sync thread should not be started
        assert local_only._sync_thread is None


# ── Reads always come from local ─────────────────────────────────────────


class TestReadsFromLocal:
    def test_get_zone_state_reads_local(self, synced, local_db, mock_remote):
        state = _zone_state("zone-a")
        local_db.put_zone_state("zone-a", state)
        got = synced.get_zone_state("zone-a")
        assert got is not None
        assert got.temperature == 22.0
        # Remote get should NOT be called
        mock_remote.get_zone_state.assert_not_called()

    def test_get_desired_state_reads_local(self, synced, local_db, mock_remote):
        ds = _desired_state("zone-a")
        local_db.put_desired_state("zone-a", ds)
        got = synced.get_desired_state("zone-a")
        assert got is not None
        mock_remote.get_desired_state.assert_not_called()

    def test_query_telemetry_reads_local(self, synced, local_db, mock_remote):
        reading = _sensor_reading("zone-a")
        local_db.append_telemetry(reading)
        results = synced.query_telemetry("zone-a", since=0, limit=10)
        assert len(results) == 1
        mock_remote.query_telemetry.assert_not_called()

    def test_query_agent_log_reads_local(self, synced, local_db, mock_remote):
        decision = _agent_decision()
        local_db.append_agent_log(decision)
        results = synced.query_agent_log(since=0, limit=10)
        assert len(results) == 1
        mock_remote.query_agent_log.assert_not_called()


# ── Failed remote creates pending WAL entry ──────────────────────────────


class TestFailedRemoteCreatesWAL:
    def test_failed_remote_write_creates_pending(self, synced, local_db, mock_remote):
        mock_remote.put_zone_state.side_effect = Exception("Connection timeout")
        state = _zone_state("zone-a")
        synced.put_zone_state("zone-a", state)

        # Local write succeeded
        got = local_db.get_zone_state("zone-a")
        assert got is not None

        # WAL has a pending entry
        pending = local_db.get_pending()
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"

    def test_failed_telemetry_creates_pending(self, synced, local_db, mock_remote):
        mock_remote.append_telemetry.side_effect = Exception("Network error")
        reading = _sensor_reading("zone-a")
        synced.append_telemetry(reading)

        results = local_db.query_telemetry("zone-a", since=0, limit=10)
        assert len(results) == 1
        pending = local_db.get_pending()
        assert len(pending) == 1

    def test_failed_agent_log_creates_pending(self, synced, local_db, mock_remote):
        mock_remote.append_agent_log.side_effect = Exception("Network error")
        decision = _agent_decision()
        synced.append_agent_log(decision)

        results = local_db.query_agent_log(since=0, limit=10)
        assert len(results) == 1
        pending = local_db.get_pending()
        assert len(pending) == 1


# ── Background sync replays pending entries ──────────────────────────────


class TestBackgroundSync:
    def test_sync_replays_pending(self, local_db, mock_remote):
        # Set up: write with failing remote
        mock_remote.put_zone_state.side_effect = Exception("down")
        store = SyncedStore(local=local_db, remote=mock_remote, sync_interval=0.1)

        state = _zone_state("zone-a")
        store.put_zone_state("zone-a", state)

        # Confirm pending
        assert len(local_db.get_pending()) == 1

        # Fix remote
        mock_remote.put_zone_state.side_effect = None
        mock_remote.write_raw = MagicMock()

        # Wait for background sync to replay
        time.sleep(0.4)

        # Pending should be cleared
        assert len(local_db.get_pending()) == 0
        mock_remote.write_raw.assert_called()

        store.stop()

    def test_successful_write_no_pending(self, synced, local_db, mock_remote):
        """Successful remote writes should not leave pending entries."""
        state = _zone_state("zone-a")
        synced.put_zone_state("zone-a", state)
        pending = local_db.get_pending()
        assert len(pending) == 0
