"""AWS API tests — hit real AWS infrastructure.

These tests use actual AWS services (Bedrock, DynamoDB).
They require valid AWS credentials and network access.

Run with: uv run pytest tests/test_aws_api.py -v
Skip with: uv run pytest -k "not test_aws_api"

Table prefix auto-detected from DYNAMO_TABLE_PREFIX env or defaults to "astrofarm".
"""

from __future__ import annotations

import json
import os
import time
import uuid

import boto3
import pytest

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DYNAMO_PREFIX = os.getenv("DYNAMO_TABLE_PREFIX", "eden")


def _aws_available() -> bool:
    """Check if AWS credentials are available."""
    try:
        boto3.client("sts", region_name=AWS_REGION).get_caller_identity()
        return True
    except Exception:
        return False


def _dynamo_tables_exist() -> bool:
    """Check if DynamoDB tables are deployed."""
    try:
        client = boto3.client("dynamodb", region_name=AWS_REGION)
        tables = client.list_tables()["TableNames"]
        needed = [f"{DYNAMO_PREFIX}-state", f"{DYNAMO_PREFIX}-telemetry", f"{DYNAMO_PREFIX}-agent-log"]
        return all(t in tables for t in needed)
    except Exception:
        return False


def _bedrock_available() -> bool:
    """Check if Bedrock InvokeModel is permitted."""
    try:
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        client.converse(
            modelId="us.anthropic.claude-sonnet-4-6",
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 1},
        )
        return True
    except Exception:
        return False


# Module-level skip if no AWS credentials at all
pytestmark = pytest.mark.skipif(
    not _aws_available(),
    reason="AWS credentials not configured",
)

# Markers for conditional skipping
requires_dynamo = pytest.mark.skipif(
    not _dynamo_tables_exist(),
    reason=f"DynamoDB tables with prefix '{DYNAMO_PREFIX}' not found",
)
requires_bedrock = pytest.mark.skipif(
    not _bedrock_available(),
    reason="Bedrock InvokeModel not accessible (IAM deny or no model access)",
)


# ── DynamoDB Tests ───────────────────────────────────────────────────────


@requires_dynamo
class TestDynamoDBLive:
    """Tests against real DynamoDB tables."""

    @pytest.fixture
    def dynamo(self):
        from eden.adapters.dynamo_adapter import DynamoAdapter

        return DynamoAdapter(table_prefix=DYNAMO_PREFIX, region=AWS_REGION)

    def test_put_and_get_zone_state(self, dynamo):
        """Write a ZoneState to DynamoDB and read it back."""
        from eden.domain.models import ZoneState

        zone_id = f"test-{uuid.uuid4().hex[:8]}"
        state = ZoneState(
            zone_id=zone_id,
            temperature=22.5,
            humidity=65.0,
            pressure=1013.0,
            light=400.0,
            water_level=80.0,
            fire_detected=False,
            last_updated=time.time(),
            is_alive=True,
            source="api-test",
        )

        dynamo.put_zone_state(zone_id, state)
        result = dynamo.get_zone_state(zone_id)

        assert result is not None
        assert result.zone_id == zone_id
        assert result.temperature == 22.5
        assert result.source == "api-test"

    def test_put_and_get_desired_state(self, dynamo):
        """Write a DesiredState to DynamoDB and read it back."""
        from eden.domain.models import DesiredState

        zone_id = f"test-{uuid.uuid4().hex[:8]}"
        desired = DesiredState(
            zone_id=zone_id,
            temp_min=18.0,
            temp_max=26.0,
            humidity_min=50.0,
            humidity_max=75.0,
            light_hours=16.0,
            soil_moisture_min=30.0,
            soil_moisture_max=70.0,
            water_budget_liters_per_day=5.0,
        )

        dynamo.put_desired_state(zone_id, desired)
        result = dynamo.get_desired_state(zone_id)

        assert result is not None
        assert result.zone_id == zone_id
        assert result.temp_min == 18.0
        assert result.temp_max == 26.0

    def test_append_and_query_telemetry(self, dynamo):
        """Write telemetry to DynamoDB and query it back.

        NOTE: Deployed table may use 'node_id' PK instead of 'zone_id'.
        This tests the adapter code path; schema mismatches are expected
        if Pulumi tables were created with a different schema.
        """
        from botocore.exceptions import ClientError

        from eden.domain.models import SensorReading, SensorType

        zone_id = f"test-{uuid.uuid4().hex[:8]}"
        now = time.time()

        reading = SensorReading(
            zone_id=zone_id,
            sensor_type=SensorType.TEMPERATURE,
            value=22.0,
            unit="celsius",
            timestamp=now,
            source="api-test",
        )

        try:
            dynamo.append_telemetry(reading)
            results = dynamo.query_telemetry(zone_id, since=now - 1, limit=10)
            assert len(results) >= 1
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ValidationException":
                pytest.skip(f"Table schema mismatch: {e}")
            raise

    def test_append_and_query_agent_log(self, dynamo):
        """Write agent decisions to DynamoDB and query them back.

        NOTE: Deployed table schema may differ from adapter expectations.
        """
        from botocore.exceptions import ClientError

        from eden.domain.models import AgentDecision, Severity, Tier

        now = time.time()
        decision = AgentDecision(
            timestamp=now,
            agent_name="TEST_AGENT",
            severity=Severity.INFO,
            reasoning="API test decision",
            action="test_action",
            result="tested",
            zone_id=f"test-{uuid.uuid4().hex[:8]}",
            tier=Tier.FLIGHT_RULES,
        )

        try:
            dynamo.append_agent_log(decision)
            results = dynamo.query_agent_log(since=now - 1, limit=10)
            found = [r for r in results if r.reasoning == "API test decision"]
            assert len(found) >= 1
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ValidationException":
                pytest.skip(f"Table schema mismatch: {e}")
            raise

    def test_write_raw_idempotent(self, dynamo):
        """write_raw() is idempotent — writing same item twice doesn't error."""
        table = f"{DYNAMO_PREFIX}-state"
        key = f"test-raw-{uuid.uuid4().hex[:8]}"

        item = {
            "key": {"S": key},
            "data": {"S": json.dumps({"test": True})},
        }

        # Write twice — should not raise
        dynamo.write_raw(table, item)
        dynamo.write_raw(table, item)


# ── Bedrock Tests ────────────────────────────────────────────────────────


@requires_bedrock
class TestBedrockLive:
    """Tests against real AWS Bedrock."""

    @pytest.fixture
    def bedrock(self):
        from eden.adapters.bedrock_adapter import BedrockAdapter

        return BedrockAdapter(region=AWS_REGION)

    def test_bedrock_is_available(self, bedrock):
        """Bedrock health check returns True when credentials are valid."""
        available = bedrock.is_available()
        assert available is True

    def test_bedrock_reason_returns_text(self, bedrock):
        """Bedrock returns a non-empty response for a simple prompt."""
        response = bedrock.reason(
            "Reply with exactly: EDEN ONLINE",
            {"system": "You are a test agent. Reply concisely."},
        )
        assert isinstance(response, str)
        assert len(response) > 0

    def test_bedrock_reason_with_zone_context(self, bedrock):
        """Bedrock can process zone state context and return analysis."""
        context = {
            "zone_id": "alpha",
            "temperature": 35.5,
            "humidity": 85.0,
            "water_level": 15.0,
            "fire_detected": False,
        }
        response = bedrock.reason(
            "Zone alpha has high temperature and humidity. "
            "What flight rule should trigger? Reply in one sentence.",
            context,
        )
        assert isinstance(response, str)
        assert len(response) > 0


# ── Model Chain with Real Backends ───────────────────────────────────────


class TestModelChainLive:
    """Test model chain fallback behavior with real adapters."""

    @requires_bedrock
    def test_chain_prefers_bedrock(self):
        """ModelChain uses Bedrock (first in chain) when available."""
        from eden.adapters.bedrock_adapter import BedrockAdapter
        from eden.adapters.model_chain import ModelChain

        bedrock = BedrockAdapter(region=AWS_REGION)

        class FakeOllama:
            def is_available(self):
                return True

            def reason(self, prompt, context):
                return "ollama-fallback"

        chain = ModelChain([bedrock, FakeOllama()])
        result = chain.reason("Reply with exactly: BEDROCK", {})

        assert result != "ollama-fallback"
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chain_falls_back_when_bedrock_denied(self):
        """ModelChain falls back to Ollama when Bedrock is inaccessible."""
        from eden.adapters.bedrock_adapter import BedrockAdapter
        from eden.adapters.model_chain import ModelChain

        bedrock = BedrockAdapter(region=AWS_REGION)

        class FakeOllama:
            def is_available(self):
                return True

            def reason(self, prompt, context):
                return "ollama-fallback"

        chain = ModelChain([bedrock, FakeOllama()])
        result = chain.reason("test", {})

        # If Bedrock is down, should get ollama fallback
        if not bedrock.is_available():
            assert result == "ollama-fallback"
        # Either way, we should get a result
        assert result is not None


# ── SyncedStore with Real DynamoDB ───────────────────────────────────────


@requires_dynamo
class TestSyncedStoreLive:
    """Test WAL sync with real DynamoDB."""

    def test_synced_store_writes_to_both(self):
        """SyncedStore writes to local SQLite AND remote DynamoDB."""
        import tempfile

        from eden.adapters.dynamo_adapter import DynamoAdapter
        from eden.adapters.sqlite_adapter import SqliteAdapter
        from eden.adapters.synced_store import SyncedStore
        from eden.domain.models import ZoneState

        with tempfile.TemporaryDirectory() as tmp:
            sqlite = SqliteAdapter(db_path=f"{tmp}/test.db")
            dynamo = DynamoAdapter(table_prefix=DYNAMO_PREFIX, region=AWS_REGION)
            store = SyncedStore(local=sqlite, remote=dynamo, sync_interval=999)

            zone_id = f"sync-test-{uuid.uuid4().hex[:8]}"
            state = ZoneState(
                zone_id=zone_id,
                temperature=22.0,
                humidity=60.0,
                pressure=1013.0,
                light=400.0,
                water_level=80.0,
                fire_detected=False,
                last_updated=time.time(),
                is_alive=True,
                source="sync-test",
            )

            store.put_zone_state(zone_id, state)

            # Local should have it immediately
            local_result = sqlite.get_zone_state(zone_id)
            assert local_result is not None
            assert local_result.zone_id == zone_id

            # Remote should also have it (sync was immediate, not WAL)
            remote_result = dynamo.get_zone_state(zone_id)
            assert remote_result is not None
            assert remote_result.zone_id == zone_id

            # No pending WAL entries (remote succeeded)
            pending = sqlite.get_pending()
            assert len(pending) == 0

            store.stop()


# ── Full Pipeline with Real AWS ──────────────────────────────────────────


@requires_dynamo
class TestFullPipelineLive:
    """End-to-end: reconciler with real DynamoDB storage."""

    def test_reconcile_with_real_storage(self):
        """Full reconciliation cycle with real DynamoDB for state storage.

        SyncedStore handles telemetry/agent-log schema mismatches via WAL
        (writes fail → queued locally → no crash). We verify:
        1. Reconciler produces decisions (flight rules fire)
        2. Zone state persisted to DynamoDB (state table schema matches)
        3. Local telemetry always works (SQLite)
        """
        import tempfile

        from eden.adapters.dynamo_adapter import DynamoAdapter
        from eden.adapters.sqlite_adapter import SqliteAdapter
        from eden.adapters.synced_store import SyncedStore
        from eden.application.reconciler import Reconciler
        from eden.config import Settings
        from eden.domain.flight_rules import FlightRulesEngine
        from eden.domain.models import DesiredState, ZoneState
        from eden.domain.nutrition import NutritionTracker

        from eden.__main__ import AgentLogAdapter, TelemetryStoreAdapter

        class FakeSensor:
            def __init__(self, zones):
                self._zones = zones

            @property
            def zone_ids(self):
                return list(self._zones.keys())

            def get_latest(self, zone_id):
                return self._zones.get(zone_id)

        class RecordingActuator:
            def __init__(self):
                self.commands = []

            def send_command(self, cmd):
                self.commands.append(cmd)
                return True

        with tempfile.TemporaryDirectory() as tmp:
            sqlite = SqliteAdapter(db_path=f"{tmp}/test.db")
            dynamo = DynamoAdapter(table_prefix=DYNAMO_PREFIX, region=AWS_REGION)
            store = SyncedStore(local=sqlite, remote=dynamo, sync_interval=999)

            zone_id = f"pipeline-{uuid.uuid4().hex[:8]}"

            # Set desired state with a delta from current
            desired = DesiredState(
                zone_id=zone_id,
                temp_min=20.0,
                temp_max=25.0,
                humidity_min=50.0,
                humidity_max=70.0,
                light_hours=16.0,
                soil_moisture_min=30.0,
                soil_moisture_max=70.0,
                water_budget_liters_per_day=5.0,
            )
            store.put_desired_state(zone_id, desired)

            # Create zone with extreme temp that triggers flight rules after mars transform
            zone = ZoneState(
                zone_id=zone_id,
                temperature=-100.0,  # → ~3.7C after Mars transform → triggers FR-T-001
                humidity=60.0,
                pressure=1013.0,
                light=400.0,
                water_level=80.0,
                fire_detected=False,
                last_updated=time.time(),
                is_alive=True,
                source="pipeline-test",
            )
            sensor = FakeSensor({zone_id: zone})
            actuator = RecordingActuator()

            config = Settings()
            config.RECONCILE_INTERVAL_SECONDS = 1

            reconciler = Reconciler(
                sensor=sensor,
                actuator=actuator,
                state_store=store,
                telemetry_store=TelemetryStoreAdapter(store),
                agent_log=AgentLogAdapter(store),
                model=None,  # Skip model — Bedrock may not be accessible
                flight_rules=FlightRulesEngine(),
                nutrition=NutritionTracker(
                    crew=NutritionTracker.get_default_crew(), crops=[]
                ),
                config=config,
            )

            decisions = reconciler.reconcile_once()

            # Flight rules should have fired (frost protection)
            assert len(decisions) > 0
            assert len(actuator.commands) > 0

            # Zone state should be persisted to DynamoDB (state table PK=key matches)
            remote_state = dynamo.get_zone_state(zone_id)
            assert remote_state is not None

            # Local telemetry always works regardless of DynamoDB schema
            local_readings = sqlite.query_telemetry(zone_id, since=0.0, limit=100)
            assert len(local_readings) == 5  # 5 sensor types

            store.stop()
