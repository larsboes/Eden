"""DynamoDB adapter — remote replica for Earth-side dashboard.

Implements StateStorePort, TelemetryStorePort, AgentLogPort.
Uses boto3 directly, no ORM. All writes are idempotent PutItem upserts.
"""

from __future__ import annotations

import json
from decimal import Decimal

import boto3

from eden.domain.models import (
    AgentDecision,
    DesiredState,
    SensorReading,
    ZoneState,
)


def _to_dynamo_s(val: str) -> dict:
    return {"S": val}


def _to_dynamo_n(val: float | int) -> dict:
    return {"N": str(val)}


def _from_dynamo_item(item: dict) -> dict:
    """Extract the 'data' field JSON from a DynamoDB item."""
    return json.loads(item["data"]["S"])


class DynamoAdapter:
    """Remote DynamoDB store. Eventually consistent replica of local SQLite."""

    def __init__(
        self, table_prefix: str = "eden", region: str = "us-west-2"
    ) -> None:
        self._prefix = table_prefix
        self._client = boto3.client("dynamodb", region_name=region)
        self._state_table = f"{table_prefix}-state"
        self._telemetry_table = f"{table_prefix}-telemetry"
        self._agent_log_table = f"{table_prefix}-agent-log"

    # ── StateStorePort ───────────────────────────────────────────────────

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        resp = self._client.get_item(
            TableName=self._state_table,
            Key={"key": _to_dynamo_s(f"zone_state:{zone_id}")},
        )
        item = resp.get("Item")
        if not item:
            return None
        return ZoneState.from_dict(_from_dynamo_item(item))

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self._client.put_item(
            TableName=self._state_table,
            Item={
                "key": _to_dynamo_s(f"zone_state:{zone_id}"),
                "data": _to_dynamo_s(json.dumps(state.to_dict())),
            },
        )

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        resp = self._client.get_item(
            TableName=self._state_table,
            Key={"key": _to_dynamo_s(f"desired_state:{zone_id}")},
        )
        item = resp.get("Item")
        if not item:
            return None
        return DesiredState.from_dict(_from_dynamo_item(item))

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self._client.put_item(
            TableName=self._state_table,
            Item={
                "key": _to_dynamo_s(f"desired_state:{zone_id}"),
                "data": _to_dynamo_s(json.dumps(state.to_dict())),
            },
        )

    # ── TelemetryStorePort ───────────────────────────────────────────────

    def append_telemetry(self, reading: SensorReading) -> None:
        self._client.put_item(
            TableName=self._telemetry_table,
            Item={
                "zone_id": _to_dynamo_s(reading.zone_id),
                "timestamp": _to_dynamo_n(reading.timestamp),
                "data": _to_dynamo_s(json.dumps(reading.to_dict())),
            },
        )

    def query_telemetry(
        self, zone_id: str, since: float, limit: int
    ) -> list[SensorReading]:
        resp = self._client.query(
            TableName=self._telemetry_table,
            KeyConditionExpression="zone_id = :zid AND #ts >= :since",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={
                ":zid": _to_dynamo_s(zone_id),
                ":since": _to_dynamo_n(since),
            },
            Limit=limit,
            ScanIndexForward=True,
        )
        return [
            SensorReading.from_dict(_from_dynamo_item(item))
            for item in resp.get("Items", [])
        ]

    # ── AgentLogPort ─────────────────────────────────────────────────────

    def append_agent_log(self, decision: AgentDecision) -> None:
        self._client.put_item(
            TableName=self._agent_log_table,
            Item={
                "partition": _to_dynamo_s("LOG"),
                "timestamp": _to_dynamo_n(decision.timestamp),
                "data": _to_dynamo_s(json.dumps(decision.to_dict())),
            },
        )

    def query_agent_log(self, since: float, limit: int) -> list[AgentDecision]:
        resp = self._client.query(
            TableName=self._agent_log_table,
            KeyConditionExpression="#pk = :pk AND #ts >= :since",
            ExpressionAttributeNames={"#pk": "partition", "#ts": "timestamp"},
            ExpressionAttributeValues={
                ":pk": _to_dynamo_s("LOG"),
                ":since": _to_dynamo_n(since),
            },
            Limit=limit,
            ScanIndexForward=True,
        )
        return [
            AgentDecision.from_dict(_from_dynamo_item(item))
            for item in resp.get("Items", [])
        ]

    # ── WAL replay endpoint ──────────────────────────────────────────────

    def write_raw(self, table_name: str, item: dict) -> None:
        """Direct PutItem for WAL sync replay. Idempotent by PK."""
        self._client.put_item(TableName=table_name, Item=item)
