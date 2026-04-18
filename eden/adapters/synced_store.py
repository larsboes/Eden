"""SyncedStore — WAL orchestrator wrapping local SQLite + remote DynamoDB.

ALL writes go to local first (ACID, <1ms), then try remote.
ALL reads come from local (always fast, always available).
Background daemon thread replays pending WAL entries every N seconds.
If remote is None → purely local mode, no sync thread started.
"""

from __future__ import annotations

import json
import structlog
import threading
import time

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.domain.models import (
    AgentDecision,
    DesiredState,
    SensorReading,
    ZoneState,
)

logger = structlog.get_logger(__name__)

# Map WAL table_name → DynamoDB table suffix for replay
_TABLE_MAP = {
    "zone_state": "state",
    "desired_state": "state",
    "telemetry": "telemetry",
    "agent_log": "agent-log",
}


class SyncedStore:
    """Local-first store with async DynamoDB replication via WAL."""

    def __init__(
        self,
        local: SqliteAdapter,
        remote: object | None,
        sync_interval: float = 5.0,
    ) -> None:
        self.local = local
        self.remote = remote
        self._sync_interval = sync_interval
        self._stop_event = threading.Event()
        self._sync_thread: threading.Thread | None = None

        if self.remote is not None:
            self._sync_thread = threading.Thread(
                target=self._sync_loop, daemon=True, name="wal-sync"
            )
            self._sync_thread.start()

    # ── StateStorePort ───────────────────────────────────────────────────

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        return self.local.get_zone_state(zone_id)

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self.local.put_zone_state(zone_id, state)
        data_json = json.dumps(state.to_dict())
        self._try_remote(
            lambda: self.remote.put_zone_state(zone_id, state),
            "zone_state",
            f"zone_state:{zone_id}",
            data_json,
        )

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        return self.local.get_desired_state(zone_id)

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self.local.put_desired_state(zone_id, state)
        data_json = json.dumps(state.to_dict())
        self._try_remote(
            lambda: self.remote.put_desired_state(zone_id, state),
            "desired_state",
            f"desired_state:{zone_id}",
            data_json,
        )

    # ── TelemetryStorePort ───────────────────────────────────────────────

    def append_telemetry(self, reading: SensorReading) -> None:
        self.local.append_telemetry(reading)
        data_json = json.dumps(reading.to_dict())
        self._try_remote(
            lambda: self.remote.append_telemetry(reading),
            "telemetry",
            f"{reading.zone_id}:{reading.timestamp}",
            data_json,
        )

    def query_telemetry(
        self, zone_id: str, since: float, limit: int
    ) -> list[SensorReading]:
        return self.local.query_telemetry(zone_id, since, limit)

    # ── AgentLogPort ─────────────────────────────────────────────────────

    def append_agent_log(self, decision: AgentDecision) -> None:
        self.local.append_agent_log(decision)
        data_json = json.dumps(decision.to_dict())
        self._try_remote(
            lambda: self.remote.append_agent_log(decision),
            "agent_log",
            f"LOG:{decision.timestamp}",
            data_json,
        )

    def query_agent_log(self, since: float, limit: int) -> list[AgentDecision]:
        return self.local.query_agent_log(since, limit)

    # ── Internal: try remote, WAL on failure ─────────────────────────────

    def _try_remote(
        self,
        remote_fn: callable,
        table: str,
        key: str,
        data_json: str,
    ) -> None:
        if self.remote is None:
            return
        try:
            remote_fn()
        except Exception:
            logger.debug("Remote write failed for %s/%s, queued in WAL", table, key)
            self.local.mark_pending(table, key, data_json)

    # ── Background sync loop ─────────────────────────────────────────────

    def _sync_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self._sync_interval)
            if self._stop_event.is_set():
                break
            self._replay_pending()

    def _replay_pending(self) -> None:
        pending = self.local.get_pending()
        if not pending:
            return

        prefix = getattr(self.remote, "_prefix", "eden")
        for entry in pending:
            table_suffix = _TABLE_MAP.get(entry["table_name"], entry["table_name"])
            dynamo_table = f"{prefix}-{table_suffix}"
            data = json.loads(entry["data"])

            # Build DynamoDB item based on table type
            item = self._build_dynamo_item(entry["table_name"], entry["key"], data)

            try:
                self.remote.write_raw(dynamo_table, item)
                self.local.mark_synced(entry["id"])
                logger.debug("Synced WAL entry %d to %s", entry["id"], dynamo_table)
            except Exception:
                logger.debug(
                    "WAL replay failed for entry %d, will retry", entry["id"]
                )
                break  # Stop replaying on first failure to preserve order

    @staticmethod
    def _build_dynamo_item(table_name: str, key: str, data: dict) -> dict:
        """Build a DynamoDB-formatted item for WAL replay."""
        if table_name in ("zone_state", "desired_state"):
            return {
                "key": {"S": key},
                "data": {"S": json.dumps(data)},
            }
        elif table_name == "telemetry":
            return {
                "zone_id": {"S": data.get("zone_id", "")},
                "timestamp": {"N": str(data.get("timestamp", 0))},
                "data": {"S": json.dumps(data)},
            }
        elif table_name == "agent_log":
            return {
                "partition": {"S": "LOG"},
                "timestamp": {"N": str(data.get("timestamp", 0))},
                "data": {"S": json.dumps(data)},
            }
        # Fallback
        return {"key": {"S": key}, "data": {"S": json.dumps(data)}}

    # ── Lifecycle ────────────────────────────────────────────────────────

    def stop(self) -> None:
        self._stop_event.set()
        if self._sync_thread is not None:
            self._sync_thread.join(timeout=2.0)
