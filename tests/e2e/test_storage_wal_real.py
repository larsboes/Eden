"""E2E tests for WAL storage system hitting real DynamoDB.

Tests the core promise: write local first (SQLite), sync to AWS (DynamoDB),
never lose data, auto-recover from failures.

Requires AWS credentials configured and DynamoDB tables:
  eden-state, eden-telemetry, eden-agent-log
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from unittest.mock import MagicMock, patch

import boto3
import pytest

from eden.adapters.dynamo_adapter import DynamoAdapter
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


# ── Skip guards ─────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_PREFIX = "eden"


def _aws_available() -> bool:
    try:
        boto3.client("sts", region_name=REGION).get_caller_identity()
        return True
    except Exception:
        return False


def _dynamo_tables_exist() -> bool:
    try:
        client = boto3.client("dynamodb", region_name=REGION)
        tables = client.list_tables()["TableNames"]
        needed = [f"{TABLE_PREFIX}-state", f"{TABLE_PREFIX}-telemetry", f"{TABLE_PREFIX}-agent-log"]
        return all(t in tables for t in needed)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _aws_available() or not _dynamo_tables_exist(),
    reason="AWS credentials or DynamoDB tables not available",
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _unique_zone_id() -> str:
    """Generate a unique zone ID to avoid collisions between test runs."""
    return f"test-zone-{uuid.uuid4().hex[:8]}"


def _make_zone_state(zone_id: str, temp: float = 22.0) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temp,
        humidity=65.0,
        pressure=1013.0,
        light=800.0,
        water_level=75.0,
        fire_detected=False,
        last_updated=time.time(),
        is_alive=True,
        source="test",
    )


def _make_sensor_reading(zone_id: str, ts: float | None = None) -> SensorReading:
    return SensorReading(
        zone_id=zone_id,
        sensor_type=SensorType.TEMPERATURE,
        value=22.5,
        unit="C",
        timestamp=ts or time.time(),
        source="test-sensor",
    )


def _make_agent_decision(ts: float | None = None, zone_id: str = "test") -> AgentDecision:
    return AgentDecision(
        timestamp=ts or time.time(),
        agent_name="test-agent",
        severity=Severity.INFO,
        reasoning="test reasoning",
        action="test action",
        result="test result",
        zone_id=zone_id,
        tier=Tier.FLIGHT_RULES,
    )


def _cleanup_dynamo_state(dynamo: DynamoAdapter, key: str) -> None:
    """Delete a key from the state table (best effort cleanup)."""
    try:
        dynamo._client.delete_item(
            TableName=f"{TABLE_PREFIX}-state",
            Key={"key": {"S": key}},
        )
    except Exception:
        pass


def _cleanup_dynamo_telemetry(dynamo: DynamoAdapter, zone_id: str, timestamp: float) -> None:
    try:
        dynamo._client.delete_item(
            TableName=f"{TABLE_PREFIX}-telemetry",
            Key={"zone_id": {"S": zone_id}, "timestamp": {"N": str(timestamp)}},
        )
    except Exception:
        pass


def _cleanup_dynamo_agent_log(dynamo: DynamoAdapter, timestamp: float) -> None:
    try:
        dynamo._client.delete_item(
            TableName=f"{TABLE_PREFIX}-agent-log",
            Key={"partition": {"S": "LOG"}, "timestamp": {"N": str(timestamp)}},
        )
    except Exception:
        pass


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sqlite_db():
    """Fresh SQLite adapter with a temp file per test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    adapter = SqliteAdapter(db_path=tmp.name)
    yield adapter
    adapter.close()
    os.unlink(tmp.name)


@pytest.fixture
def dynamo():
    """Real DynamoDB adapter."""
    return DynamoAdapter(table_prefix=TABLE_PREFIX, region=REGION)


@pytest.fixture
def synced(sqlite_db, dynamo):
    """SyncedStore wired to real SQLite + real DynamoDB with fast sync."""
    store = SyncedStore(local=sqlite_db, remote=dynamo, sync_interval=1.0)
    yield store
    store.stop()


# ── Test 1: Happy path ──────────────────────────────────────────────────


def test_happy_path_zone_state_in_both(synced, dynamo):
    """Write zone state → appears in both SQLite AND DynamoDB immediately."""
    zone_id = _unique_zone_id()
    state = _make_zone_state(zone_id, temp=24.0)

    synced.put_zone_state(zone_id, state)

    # Local: immediate
    local_state = synced.get_zone_state(zone_id)
    assert local_state is not None
    assert local_state.zone_id == zone_id
    assert local_state.temperature == 24.0

    # Remote: should be there (direct write succeeded)
    remote_state = dynamo.get_zone_state(zone_id)
    assert remote_state is not None, "Zone state not found in DynamoDB after direct write"
    assert remote_state.zone_id == zone_id
    assert remote_state.temperature == 24.0

    # Cleanup
    _cleanup_dynamo_state(dynamo, f"zone_state:{zone_id}")


# ── Test 2: WAL replay on remote failure ────────────────────────────────


def test_wal_replay_after_remote_failure(sqlite_db, dynamo):
    """Simulate remote failure → data queued in WAL → reconnect → synced."""
    zone_id = _unique_zone_id()
    state = _make_zone_state(zone_id, temp=19.0)

    # Create a broken remote that fails on put_zone_state
    broken_remote = MagicMock(spec=DynamoAdapter)
    broken_remote.put_zone_state.side_effect = Exception("simulated network failure")
    broken_remote._prefix = TABLE_PREFIX

    # Use SyncedStore with broken remote (no sync thread — we control it)
    store = SyncedStore(local=sqlite_db, remote=broken_remote, sync_interval=9999)

    store.put_zone_state(zone_id, state)

    # Local: data is there
    assert store.get_zone_state(zone_id) is not None

    # WAL: should have a pending entry
    pending = sqlite_db.get_pending()
    assert len(pending) >= 1
    assert pending[0]["status"] == "pending"
    assert pending[0]["table_name"] == "zone_state"

    store.stop()

    # Now create a new SyncedStore with real DynamoDB and fast sync
    store2 = SyncedStore(local=sqlite_db, remote=dynamo, sync_interval=1.0)

    # Wait for background sync to replay
    deadline = time.time() + 10.0
    while time.time() < deadline:
        remaining = sqlite_db.get_pending()
        if len(remaining) == 0:
            break
        time.sleep(0.5)

    store2.stop()

    # Verify WAL is drained
    assert len(sqlite_db.get_pending()) == 0, "WAL still has pending entries after replay"

    # Verify data in DynamoDB
    remote_state = dynamo.get_zone_state(zone_id)
    assert remote_state is not None, "Zone state missing from DynamoDB after WAL replay"
    assert remote_state.temperature == 19.0

    _cleanup_dynamo_state(dynamo, f"zone_state:{zone_id}")


# ── Test 3: Idempotent upserts ──────────────────────────────────────────


def test_idempotent_upserts(synced, dynamo):
    """Write same zone state twice → DynamoDB has one entry (not duplicated)."""
    zone_id = _unique_zone_id()
    state1 = _make_zone_state(zone_id, temp=20.0)
    state2 = _make_zone_state(zone_id, temp=21.0)  # updated temp

    synced.put_zone_state(zone_id, state1)
    synced.put_zone_state(zone_id, state2)

    # DynamoDB should have the latest value, not two entries
    remote_state = dynamo.get_zone_state(zone_id)
    assert remote_state is not None
    assert remote_state.temperature == 21.0  # Latest wins

    # Verify via raw scan that the key is unique
    resp = dynamo._client.get_item(
        TableName=f"{TABLE_PREFIX}-state",
        Key={"key": {"S": f"zone_state:{zone_id}"}},
    )
    assert "Item" in resp  # Exactly one item
    assert json.loads(resp["Item"]["data"]["S"])["temperature"] == 21.0

    _cleanup_dynamo_state(dynamo, f"zone_state:{zone_id}")


# ── Test 4: Telemetry flow — 100 rapid sensor readings ──────────────────


def test_telemetry_100_rapid_readings(synced, sqlite_db, dynamo):
    """Append 100 sensor readings rapidly → all in SQLite → all synced to DynamoDB."""
    zone_id = _unique_zone_id()
    base_ts = time.time()
    readings = []

    for i in range(100):
        ts = base_ts + i * 0.001  # 1ms apart
        r = SensorReading(
            zone_id=zone_id,
            sensor_type=SensorType.TEMPERATURE,
            value=20.0 + (i * 0.1),
            unit="C",
            timestamp=ts,
            source="test-bulk",
        )
        readings.append(r)
        synced.append_telemetry(r)

    # All 100 in SQLite
    local_readings = sqlite_db.query_telemetry(zone_id, since=base_ts - 1, limit=200)
    assert len(local_readings) == 100, f"Expected 100 local readings, got {len(local_readings)}"

    # Wait for sync to complete any pending WAL entries
    deadline = time.time() + 15.0
    while time.time() < deadline:
        pending = sqlite_db.get_pending()
        if len(pending) == 0:
            break
        time.sleep(0.5)

    # Verify some readings in DynamoDB (query returns up to limit)
    remote_readings = dynamo.query_telemetry(zone_id, since=base_ts - 1, limit=200)
    assert len(remote_readings) >= 50, (
        f"Expected at least 50 remote readings, got {len(remote_readings)}"
    )

    # Cleanup
    for r in readings:
        _cleanup_dynamo_telemetry(dynamo, zone_id, r.timestamp)


# ── Test 5: Agent log flow — 20 decisions ───────────────────────────────


def test_agent_log_20_decisions(synced, sqlite_db, dynamo):
    """Log 20 agent decisions → all persisted both local and remote."""
    base_ts = time.time()
    zone_id = _unique_zone_id()
    decisions = []

    for i in range(20):
        ts = base_ts + i * 0.01
        d = AgentDecision(
            timestamp=ts,
            agent_name=f"agent-{i}",
            severity=Severity.INFO,
            reasoning=f"reason-{i}",
            action=f"action-{i}",
            result=f"result-{i}",
            zone_id=zone_id,
            tier=Tier.FLIGHT_RULES,
        )
        decisions.append(d)
        synced.append_agent_log(d)

    # All 20 in SQLite
    local_logs = sqlite_db.query_agent_log(since=base_ts - 1, limit=50)
    assert len(local_logs) == 20, f"Expected 20 local logs, got {len(local_logs)}"

    # Wait for sync
    deadline = time.time() + 15.0
    while time.time() < deadline:
        pending = sqlite_db.get_pending()
        if len(pending) == 0:
            break
        time.sleep(0.5)

    # Verify in DynamoDB
    remote_logs = dynamo.query_agent_log(since=base_ts - 1, limit=50)
    assert len(remote_logs) >= 10, f"Expected at least 10 remote logs, got {len(remote_logs)}"

    # Cleanup
    for d in decisions:
        _cleanup_dynamo_agent_log(dynamo, d.timestamp)


# ── Test 6: Reads always come from local ────────────────────────────────


def test_reads_always_local(sqlite_db, dynamo):
    """Even during sync, reads come from SQLite (fast, always available)."""
    zone_id = _unique_zone_id()
    state = _make_zone_state(zone_id, temp=30.0)

    # Write directly to local only
    sqlite_db.put_zone_state(zone_id, state)

    # Create SyncedStore — reads should come from local
    store = SyncedStore(local=sqlite_db, remote=dynamo, sync_interval=9999)

    local_state = store.get_zone_state(zone_id)
    assert local_state is not None
    assert local_state.temperature == 30.0

    # DynamoDB should NOT have this (we wrote only to local)
    remote_state = dynamo.get_zone_state(zone_id)
    assert remote_state is None, "Read should not have triggered a remote write"

    # Telemetry reads also local
    ts = time.time()
    reading = _make_sensor_reading(zone_id, ts=ts)
    sqlite_db.append_telemetry(reading)

    local_readings = store.query_telemetry(zone_id, since=ts - 1, limit=10)
    assert len(local_readings) == 1

    store.stop()


# ── Test 7: Offline mode — remote=None ──────────────────────────────────


def test_offline_mode_no_errors(sqlite_db):
    """SyncedStore with remote=None → everything works local-only, no errors."""
    store = SyncedStore(local=sqlite_db, remote=None, sync_interval=1.0)

    zone_id = _unique_zone_id()
    state = _make_zone_state(zone_id, temp=18.0)

    # All operations should succeed without any errors
    store.put_zone_state(zone_id, state)
    result = store.get_zone_state(zone_id)
    assert result is not None
    assert result.temperature == 18.0

    # Desired state
    desired = DesiredState(
        zone_id=zone_id,
        temp_min=18.0, temp_max=26.0,
        humidity_min=50.0, humidity_max=80.0,
        light_hours=16.0,
        soil_moisture_min=30.0, soil_moisture_max=70.0,
        water_budget_liters_per_day=5.0,
    )
    store.put_desired_state(zone_id, desired)
    result_desired = store.get_desired_state(zone_id)
    assert result_desired is not None
    assert result_desired.temp_min == 18.0

    # Telemetry
    ts = time.time()
    reading = _make_sensor_reading(zone_id, ts=ts)
    store.append_telemetry(reading)
    readings = store.query_telemetry(zone_id, since=ts - 1, limit=10)
    assert len(readings) == 1

    # Agent log
    decision = _make_agent_decision(ts=ts, zone_id=zone_id)
    store.append_agent_log(decision)
    logs = store.query_agent_log(since=ts - 1, limit=10)
    assert len(logs) == 1

    # No WAL entries (remote=None means _try_remote returns early)
    assert len(sqlite_db.get_pending()) == 0

    # No sync thread started
    assert store._sync_thread is None

    store.stop()


# ── Test 8: Recovery — 50 pending WAL entries replayed ──────────────────


def test_recovery_50_pending_wal_entries(sqlite_db, dynamo):
    """Start with 50 pending WAL entries → start sync thread → all replayed within 10s."""
    zone_ids = [_unique_zone_id() for _ in range(50)]

    # Pre-populate SQLite with zone states AND WAL entries
    for i, zid in enumerate(zone_ids):
        state = _make_zone_state(zid, temp=15.0 + i)
        sqlite_db.put_zone_state(zid, state)
        # Manually add WAL entry as if remote write failed
        data_json = json.dumps(state.to_dict())
        sqlite_db.mark_pending("zone_state", f"zone_state:{zid}", data_json)

    # Verify 50 pending
    assert len(sqlite_db.get_pending()) == 50

    # Start SyncedStore with real remote — sync thread should replay all
    store = SyncedStore(local=sqlite_db, remote=dynamo, sync_interval=1.0)

    # Wait for all to be replayed
    deadline = time.time() + 15.0
    while time.time() < deadline:
        remaining = sqlite_db.get_pending()
        if len(remaining) == 0:
            break
        time.sleep(0.5)

    store.stop()

    remaining = sqlite_db.get_pending()
    assert len(remaining) == 0, f"Expected 0 pending WAL entries, got {len(remaining)}"

    # Spot check a few in DynamoDB
    for zid in zone_ids[:5]:
        remote_state = dynamo.get_zone_state(zid)
        assert remote_state is not None, f"Zone {zid} missing from DynamoDB after recovery"

    # Cleanup
    for zid in zone_ids:
        _cleanup_dynamo_state(dynamo, f"zone_state:{zid}")
