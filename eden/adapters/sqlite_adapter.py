"""SQLite adapter — local source of truth with WAL tracking.

Implements StateStorePort, TelemetryStorePort, AgentLogPort.
Single file DB (eden.db). Thread-safe via explicit lock.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time

import structlog

from eden.domain.models import (
    AgentDecision,
    DesiredState,
    ManagedRule,
    SensorReading,
    ZoneState,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS zone_state (
    zone_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS desired_state (
    zone_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_zone_ts ON telemetry(zone_id, timestamp);
CREATE TABLE IF NOT EXISTS agent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_log_ts ON agent_log(timestamp);
CREATE TABLE IF NOT EXISTS sync_wal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    key TEXT NOT NULL,
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sync_wal_status ON sync_wal(status);
CREATE TABLE IF NOT EXISTS managed_rules (
    rule_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    lifecycle TEXT NOT NULL DEFAULT 'proposed',
    proposed_at REAL NOT NULL,
    promoted_at REAL,
    shadow_hits INTEGER NOT NULL DEFAULT 0,
    active_hits INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS retrospective (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_retrospective_ts ON retrospective(timestamp);
"""


logger = structlog.get_logger(__name__)


class SqliteAdapter:
    """Local-first storage. Source of truth for all EDEN data."""

    def __init__(self, db_path: str = "eden.db") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._conn.executescript(_SCHEMA)
        logger.info("sqlite_initialized", db_path=db_path)

    # ── StateStorePort ───────────────────────────────────────────────────

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM zone_state WHERE zone_id = ?", (zone_id,)
            ).fetchone()
        if row is None:
            return None
        return ZoneState.from_dict(json.loads(row["data"]))

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        data = json.dumps(state.to_dict())
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO zone_state (zone_id, data) VALUES (?, ?)",
                (zone_id, data),
            )
            self._conn.commit()

    def get_desired_state(self, zone_id: str) -> DesiredState | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM desired_state WHERE zone_id = ?", (zone_id,)
            ).fetchone()
        if row is None:
            return None
        return DesiredState.from_dict(json.loads(row["data"]))

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        data = json.dumps(state.to_dict())
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO desired_state (zone_id, data) VALUES (?, ?)",
                (zone_id, data),
            )
            self._conn.commit()

    # ── TelemetryStorePort ───────────────────────────────────────────────

    def append_telemetry(self, reading: SensorReading) -> None:
        data = json.dumps(reading.to_dict())
        with self._lock:
            self._conn.execute(
                "INSERT INTO telemetry (zone_id, timestamp, data) VALUES (?, ?, ?)",
                (reading.zone_id, reading.timestamp, data),
            )
            self._conn.commit()

    def query_telemetry(
        self, zone_id: str, since: float, limit: int
    ) -> list[SensorReading]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM telemetry WHERE zone_id = ? AND timestamp >= ? "
                "ORDER BY timestamp ASC LIMIT ?",
                (zone_id, since, limit),
            ).fetchall()
        return [SensorReading.from_dict(json.loads(r["data"])) for r in rows]

    # ── AgentLogPort ─────────────────────────────────────────────────────

    def append_agent_log(self, decision: AgentDecision) -> None:
        data = json.dumps(decision.to_dict())
        with self._lock:
            self._conn.execute(
                "INSERT INTO agent_log (timestamp, data) VALUES (?, ?)",
                (decision.timestamp, data),
            )
            self._conn.commit()

    def query_agent_log(self, since: float, limit: int) -> list[AgentDecision]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM agent_log WHERE timestamp >= ? "
                "ORDER BY timestamp ASC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [AgentDecision.from_dict(json.loads(r["data"])) for r in rows]

    # ── WAL tracking ─────────────────────────────────────────────────────

    def mark_pending(self, table: str, key: str, data_json: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO sync_wal (table_name, key, data, status, created_at) "
                "VALUES (?, ?, ?, 'pending', ?)",
                (table, key, data_json, time.time()),
            )
            self._conn.commit()

    def mark_synced(self, wal_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sync_wal SET status = 'synced' WHERE id = ?", (wal_id,)
            )
            self._conn.commit()

    def get_pending(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, table_name, key, data, status, created_at "
                "FROM sync_wal WHERE status = 'pending' ORDER BY id ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Managed Rules ─────────────────────────────────────────────────────

    def put_managed_rule(self, rule: ManagedRule) -> None:
        data = json.dumps(rule.to_dict())
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO managed_rules "
                "(rule_id, data, lifecycle, proposed_at, promoted_at, shadow_hits, active_hits) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    rule.rule.rule_id,
                    data,
                    rule.lifecycle.value,
                    rule.proposed_at,
                    rule.promoted_at,
                    rule.shadow_hits,
                    rule.active_hits,
                ),
            )
            self._conn.commit()

    def get_managed_rules(self, lifecycle: str | None = None) -> list[ManagedRule]:
        with self._lock:
            if lifecycle:
                rows = self._conn.execute(
                    "SELECT data FROM managed_rules WHERE lifecycle = ? ORDER BY proposed_at DESC",
                    (lifecycle,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT data FROM managed_rules ORDER BY proposed_at DESC"
                ).fetchall()
        return [ManagedRule.from_dict(json.loads(r["data"])) for r in rows]

    def get_managed_rule(self, rule_id: str) -> ManagedRule | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM managed_rules WHERE rule_id = ?", (rule_id,)
            ).fetchone()
        if row is None:
            return None
        return ManagedRule.from_dict(json.loads(row["data"]))

    def update_managed_rule_lifecycle(
        self, rule_id: str, lifecycle: str, **kwargs
    ) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM managed_rules WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            if row is None:
                return
            data = json.loads(row["data"])
            data["lifecycle"] = lifecycle
            for k, v in kwargs.items():
                if k in data:
                    data[k] = v
            self._conn.execute(
                "UPDATE managed_rules SET data = ?, lifecycle = ? WHERE rule_id = ?",
                (json.dumps(data), lifecycle, rule_id),
            )
            self._conn.commit()

    # ── Retrospective ─────────────────────────────────────────────────────

    def append_retrospective(self, report: dict) -> None:
        data = json.dumps(report)
        ts = report.get("timestamp", time.time())
        with self._lock:
            self._conn.execute(
                "INSERT INTO retrospective (timestamp, data) VALUES (?, ?)",
                (ts, data),
            )
            self._conn.commit()

    def query_retrospective(self, since: float = 0.0, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM retrospective WHERE timestamp >= ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ── Lifecycle ────────────────────────────────────────────────────────

    def close(self) -> None:
        logger.info("sqlite_closing")
        self._conn.close()
