"""Tests for DynamoAdapter — remote DynamoDB replica (mocked boto3)."""

import time
from unittest.mock import MagicMock, patch

import pytest

from eden.adapters.dynamo_adapter import DynamoAdapter
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
def mock_dynamo():
    with patch("eden.adapters.dynamo_adapter.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.get_item.return_value = {}  # default: no item
        adapter = DynamoAdapter(table_prefix="eden", region="us-west-2")
        yield adapter, mock_client


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


# ── StateStorePort ───────────────────────────────────────────────────────


class TestStateStore:
    def test_put_zone_state_calls_put_item(self, mock_dynamo):
        adapter, client = mock_dynamo
        state = _zone_state("zone-a")
        adapter.put_zone_state("zone-a", state)

        client.put_item.assert_called_once()
        call_kwargs = client.put_item.call_args[1]
        assert call_kwargs["TableName"] == "eden-state"
        assert call_kwargs["Item"]["key"]["S"] == "zone_state:zone-a"

    def test_get_zone_state_calls_get_item(self, mock_dynamo):
        adapter, client = mock_dynamo
        client.get_item.return_value = {}
        result = adapter.get_zone_state("zone-a")
        assert result is None
        client.get_item.assert_called_once()

    def test_put_desired_state_calls_put_item(self, mock_dynamo):
        adapter, client = mock_dynamo
        ds = _desired_state("zone-a")
        adapter.put_desired_state("zone-a", ds)

        client.put_item.assert_called_once()
        call_kwargs = client.put_item.call_args[1]
        assert call_kwargs["TableName"] == "eden-state"
        assert call_kwargs["Item"]["key"]["S"] == "desired_state:zone-a"

    def test_get_desired_state_returns_none_when_missing(self, mock_dynamo):
        adapter, client = mock_dynamo
        client.get_item.return_value = {}
        result = adapter.get_desired_state("zone-a")
        assert result is None


# ── TelemetryStorePort ───────────────────────────────────────────────────


class TestTelemetryStore:
    def test_append_calls_put_item(self, mock_dynamo):
        adapter, client = mock_dynamo
        reading = _sensor_reading("zone-a")
        adapter.append_telemetry(reading)

        client.put_item.assert_called_once()
        call_kwargs = client.put_item.call_args[1]
        assert call_kwargs["TableName"] == "eden-telemetry"
        assert call_kwargs["Item"]["zone_id"]["S"] == "zone-a"
        assert "timestamp" in call_kwargs["Item"]

    def test_query_calls_query(self, mock_dynamo):
        adapter, client = mock_dynamo
        client.query.return_value = {"Items": []}
        results = adapter.query_telemetry("zone-a", since=0, limit=10)
        assert results == []
        client.query.assert_called_once()


# ── AgentLogPort ─────────────────────────────────────────────────────────


class TestAgentLog:
    def test_append_calls_put_item(self, mock_dynamo):
        adapter, client = mock_dynamo
        decision = _agent_decision()
        adapter.append_agent_log(decision)

        client.put_item.assert_called_once()
        call_kwargs = client.put_item.call_args[1]
        assert call_kwargs["TableName"] == "eden-agent-log"
        assert call_kwargs["Item"]["partition"]["S"] == "LOG"

    def test_query_calls_query(self, mock_dynamo):
        adapter, client = mock_dynamo
        client.query.return_value = {"Items": []}
        results = adapter.query_agent_log(since=0, limit=10)
        assert results == []
        client.query.assert_called_once()


# ── write_raw ────────────────────────────────────────────────────────────


class TestWriteRaw:
    def test_write_raw_puts_item_directly(self, mock_dynamo):
        adapter, client = mock_dynamo
        item = {"key": {"S": "test-key"}, "data": {"S": '{"hello": "world"}'}}
        adapter.write_raw("eden-state", item)

        client.put_item.assert_called_once_with(TableName="eden-state", Item=item)

    def test_write_raw_to_telemetry_table(self, mock_dynamo):
        adapter, client = mock_dynamo
        item = {
            "zone_id": {"S": "zone-a"},
            "timestamp": {"N": "1234567890.123"},
            "data": {"S": "{}"},
        }
        adapter.write_raw("eden-telemetry", item)
        client.put_item.assert_called_once_with(TableName="eden-telemetry", Item=item)
