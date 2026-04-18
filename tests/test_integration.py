"""Integration tests for EDEN composition root.

Tests full-cycle wiring: sensor → flight rules → actuator,
WAL sync, model chain fallback, and graceful shutdown.
"""

from __future__ import annotations

import signal
import threading
import time

import pytest

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.adapters.synced_store import SyncedStore
from eden.adapters.model_chain import ModelChain
from eden.application.reconciler import Reconciler
from eden.config import Settings
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.models import (
    ActuatorCommand,
    DesiredState,
    Severity,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Helpers ──────────────────────────────────────────────────────────────


class FakeSensor:
    """Minimal SensorPort that returns pre-set zones."""

    def __init__(self, zones: dict[str, ZoneState]) -> None:
        self._zones = zones

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def subscribe(self, callback) -> None:
        pass


class FakeActuator:
    """Minimal ActuatorPort that records commands."""

    def __init__(self) -> None:
        self.commands: list[ActuatorCommand] = []

    def send_command(self, command: ActuatorCommand) -> bool:
        self.commands.append(command)
        return True


class FakeModel:
    """Minimal ModelPort that returns canned responses."""

    def __init__(self, available: bool = True, response: str = "test response") -> None:
        self._available = available
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    def reason(self, prompt: str, context: dict) -> str:
        self.calls.append((prompt, context))
        return self._response

    def is_available(self) -> bool:
        return self._available


class FakeRemote:
    """Minimal DynamoDB-like remote that can be toggled to fail."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self._prefix = "eden"
        self.writes: list[dict] = []

    def put_zone_state(self, zone_id, state):
        if self.should_fail:
            raise ConnectionError("Remote unavailable")
        self.writes.append({"type": "zone_state", "zone_id": zone_id})

    def put_desired_state(self, zone_id, state):
        if self.should_fail:
            raise ConnectionError("Remote unavailable")
        self.writes.append({"type": "desired_state", "zone_id": zone_id})

    def append_telemetry(self, reading):
        if self.should_fail:
            raise ConnectionError("Remote unavailable")
        self.writes.append({"type": "telemetry"})

    def append_agent_log(self, decision):
        if self.should_fail:
            raise ConnectionError("Remote unavailable")
        self.writes.append({"type": "agent_log"})

    def write_raw(self, table_name, item):
        if self.should_fail:
            raise ConnectionError("Remote unavailable")
        self.writes.append({"type": "raw", "table": table_name, "item": item})


def _make_config(**overrides) -> Settings:
    """Build a Settings with fast intervals for testing."""
    config = Settings()
    config.RECONCILE_INTERVAL_SECONDS = 1
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


def _make_zone(zone_id: str = "alpha", **overrides) -> ZoneState:
    """Build a ZoneState with sensible defaults."""
    defaults = dict(
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
    defaults.update(overrides)
    return ZoneState(**defaults)


# ── Port adapters (imported from __main__) ───────────────────────────────

from eden.__main__ import TelemetryStoreAdapter, AgentLogAdapter, SensorAdapter


# ── Test: Full cycle (sensor → flight rules → actuator) ─────────────────


class TestFullCycle:
    """Integration: simulated sensor → mars transform → flight rules → actuator."""

    def test_frost_triggers_heater(self, tmp_path):
        """Earth temp -100C → Mars dome ~3.7C → FR-T-001 triggers heater."""
        zone = _make_zone(temperature=-100.0)
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)
        config = _make_config()

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=config,
        )

        decisions = reconciler.reconcile_once()

        # Flight rules should have fired
        assert len(actuator.commands) > 0
        heater_cmds = [c for c in actuator.commands if c.device.value == "heater"]
        assert len(heater_cmds) > 0
        assert heater_cmds[0].action == "on"

    def test_fire_triggers_emergency_shutdown(self, tmp_path):
        """Fire detected → all devices OFF."""
        zone = _make_zone(fire_detected=True)
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        decisions = reconciler.reconcile_once()

        # Fire should shut down all 5 device types
        assert len(actuator.commands) == 5
        assert all(c.action == "off" for c in actuator.commands)
        # Should have critical decision
        critical = [d for d in decisions if d.severity == Severity.CRITICAL]
        assert len(critical) > 0

    def test_normal_conditions_no_commands(self, tmp_path):
        """Normal conditions within desired range → no flight rule triggers."""
        zone = _make_zone(temperature=22.0, humidity=60.0)
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        decisions = reconciler.reconcile_once()
        assert len(actuator.commands) == 0

    def test_telemetry_persisted_after_cycle(self, tmp_path):
        """Reconcile persists telemetry readings to the store."""
        zone = _make_zone()
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        reconciler.reconcile_once()

        # Should have telemetry in SQLite (5 sensor types)
        readings = sqlite.query_telemetry("alpha", since=0.0, limit=100)
        assert len(readings) == 5

    def test_zone_state_persisted(self, tmp_path):
        """Reconcile persists zone state to the store."""
        zone = _make_zone()
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        reconciler.reconcile_once()

        stored = store.get_zone_state("alpha")
        assert stored is not None
        assert stored.zone_id == "alpha"

    def test_model_invoked_when_deltas_exist(self, tmp_path):
        """Model is called when zone deviates from desired state."""
        zone = _make_zone(temperature=-10.0)  # Will transform to ~17.2C on Mars
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        # Set desired state so there's a delta
        desired = DesiredState(
            zone_id="alpha",
            temp_min=20.0,
            temp_max=25.0,
            humidity_min=50.0,
            humidity_max=70.0,
            light_hours=16.0,
            soil_moisture_min=30.0,
            soil_moisture_max=70.0,
            water_budget_liters_per_day=5.0,
        )
        store.put_desired_state("alpha", desired)

        model = FakeModel(available=True, response="adjust heater")

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=model,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        decisions = reconciler.reconcile_once()

        # Model should have been invoked
        assert len(model.calls) > 0
        # Should have a model decision in the result
        model_decisions = [d for d in decisions if d.agent_name == "MODEL"]
        assert len(model_decisions) > 0

    def test_multiple_zones(self, tmp_path):
        """Reconciler processes all zones in a single cycle."""
        zones = {
            "alpha": _make_zone(zone_id="alpha", temperature=22.0),
            "beta": _make_zone(zone_id="beta", temperature=-100.0),  # triggers frost
        }
        sensor = FakeSensor(zones)
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(),
        )

        reconciler.reconcile_once()

        # Beta should trigger heater, alpha should not
        beta_cmds = [c for c in actuator.commands if c.zone_id == "beta"]
        alpha_cmds = [c for c in actuator.commands if c.zone_id == "alpha"]
        assert len(beta_cmds) > 0
        assert len(alpha_cmds) == 0


# ── Test: WAL sync ──────────────────────────────────────────────────────


class TestWALSync:
    """Integration: write local → verify pending → mock DynamoDB sync → verify synced."""

    def test_failed_remote_creates_wal_entry(self, tmp_path):
        """When remote fails, writes are queued in WAL."""
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        remote = FakeRemote(should_fail=True)
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=999)

        zone = _make_zone()
        store.put_zone_state("alpha", zone)

        pending = sqlite.get_pending()
        assert len(pending) > 0
        assert pending[0]["table_name"] == "zone_state"
        assert pending[0]["status"] == "pending"

        store.stop()

    def test_local_always_readable_when_remote_fails(self, tmp_path):
        """Local reads work even when remote is down."""
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        remote = FakeRemote(should_fail=True)
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=999)

        zone = _make_zone()
        store.put_zone_state("alpha", zone)

        # Should read from local despite remote failure
        result = store.get_zone_state("alpha")
        assert result is not None
        assert result.zone_id == "alpha"

        store.stop()

    def test_wal_replay_syncs_pending(self, tmp_path):
        """Background sync replays pending WAL entries when remote recovers."""
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        remote = FakeRemote(should_fail=True)
        # Very short sync interval for testing
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=0.1)

        zone = _make_zone()
        store.put_zone_state("alpha", zone)

        # Verify pending entry exists
        pending = sqlite.get_pending()
        assert len(pending) > 0

        # "Fix" the remote
        remote.should_fail = False

        # Wait for background sync to run
        time.sleep(0.5)

        # Check that pending entries are now synced
        still_pending = sqlite.get_pending()
        assert len(still_pending) == 0

        store.stop()

    def test_telemetry_wal_on_remote_failure(self, tmp_path):
        """Telemetry writes create WAL entries when remote fails."""
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        remote = FakeRemote(should_fail=True)
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=999)

        from eden.domain.models import SensorReading, SensorType

        reading = SensorReading(
            zone_id="alpha",
            sensor_type=SensorType.TEMPERATURE,
            value=22.0,
            unit="celsius",
            timestamp=time.time(),
            source="test",
        )
        store.append_telemetry(reading)

        pending = sqlite.get_pending()
        assert len(pending) > 0
        assert pending[0]["table_name"] == "telemetry"

        store.stop()


# ── Test: Model chain fallback ──────────────────────────────────────────


class TestModelChainFallback:
    """Integration: model chain tries each model in priority order."""

    def test_first_available_model_used(self):
        """When first model is available, second is not called."""
        bedrock = FakeModel(available=True, response="bedrock says hi")
        ollama = FakeModel(available=True, response="ollama says hi")
        chain = ModelChain([bedrock, ollama])

        result = chain.reason("test prompt", {})

        assert result == "bedrock says hi"
        assert len(bedrock.calls) == 1
        assert len(ollama.calls) == 0

    def test_fallback_to_second_model(self):
        """When first model unavailable, falls back to second."""
        bedrock = FakeModel(available=False)
        ollama = FakeModel(available=True, response="ollama fallback")
        chain = ModelChain([bedrock, ollama])

        result = chain.reason("test prompt", {})

        assert result == "ollama fallback"
        assert len(bedrock.calls) == 0
        assert len(ollama.calls) == 1

    def test_all_models_down_returns_none(self):
        """When all models unavailable, returns None."""
        bedrock = FakeModel(available=False)
        ollama = FakeModel(available=False)
        chain = ModelChain([bedrock, ollama])

        result = chain.reason("test prompt", {})

        assert result is None

    def test_chain_is_available_when_any_model_up(self):
        """Chain reports available if any model is up."""
        bedrock = FakeModel(available=False)
        ollama = FakeModel(available=True)
        chain = ModelChain([bedrock, ollama])

        assert chain.is_available() is True

    def test_chain_unavailable_when_all_down(self):
        """Chain reports unavailable when all models are down."""
        bedrock = FakeModel(available=False)
        ollama = FakeModel(available=False)
        chain = ModelChain([bedrock, ollama])

        assert chain.is_available() is False

    def test_exception_in_first_falls_through(self):
        """If first model raises during reason(), chain tries next."""

        class FailingModel:
            def is_available(self):
                return True

            def reason(self, prompt, context):
                raise RuntimeError("Bedrock exploded")

        failing = FailingModel()
        ollama = FakeModel(available=True, response="caught by ollama")
        chain = ModelChain([failing, ollama])

        result = chain.reason("test", {})
        assert result == "caught by ollama"


# ── Test: Graceful shutdown ─────────────────────────────────────────────


class TestGracefulShutdown:
    """Integration: reconciler stops cleanly when stop() is called."""

    def test_reconciler_stops_on_signal(self, tmp_path):
        """Reconciler run() exits when stop() is called from another thread."""
        zone = _make_zone()
        sensor = FakeSensor({"alpha": zone})
        actuator = FakeActuator()
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=TelemetryStoreAdapter(store),
            agent_log=AgentLogAdapter(store),
            model=None,
            flight_rules=FlightRulesEngine(),
            nutrition=NutritionTracker(
                crew=NutritionTracker.get_default_crew(), crops=[]
            ),
            config=_make_config(RECONCILE_INTERVAL_SECONDS=1),
        )

        # Run in background thread
        thread = threading.Thread(target=reconciler.run, daemon=True)
        thread.start()

        # Give it time to start
        time.sleep(0.3)

        # Signal stop
        reconciler.stop()

        # Should exit within a reasonable time
        thread.join(timeout=3.0)
        assert not thread.is_alive(), "Reconciler did not stop within timeout"

    def test_synced_store_stops_cleanly(self, tmp_path):
        """SyncedStore background sync thread stops on stop()."""
        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        remote = FakeRemote()
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=0.1)

        # Let it run briefly
        time.sleep(0.3)

        store.stop()

        # The thread should be dead
        assert store._sync_thread is not None
        assert not store._sync_thread.is_alive()


# ── Test: Port adapter wiring ───────────────────────────────────────────


class TestPortAdapters:
    """Verify that thin adapters correctly bridge port interfaces."""

    def test_telemetry_adapter_append(self, tmp_path):
        """TelemetryStoreAdapter.append() delegates to store.append_telemetry()."""
        from eden.domain.models import SensorReading, SensorType

        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)
        adapter = TelemetryStoreAdapter(store)

        reading = SensorReading(
            zone_id="alpha",
            sensor_type=SensorType.TEMPERATURE,
            value=22.0,
            unit="celsius",
            timestamp=time.time(),
            source="test",
        )
        adapter.append(reading)

        # Verify it was persisted via the adapter
        results = adapter.query("alpha", since=0.0, limit=10)
        assert len(results) == 1
        assert results[0].value == 22.0

    def test_agent_log_adapter_append(self, tmp_path):
        """AgentLogAdapter.append() delegates to store.append_agent_log()."""
        from eden.domain.models import AgentDecision, Severity, Tier

        sqlite = SqliteAdapter(db_path=str(tmp_path / "test.db"))
        store = SyncedStore(local=sqlite, remote=None)
        adapter = AgentLogAdapter(store)

        decision = AgentDecision(
            timestamp=time.time(),
            agent_name="TEST",
            severity=Severity.INFO,
            reasoning="test reasoning",
            action="test action",
            result="test",
            zone_id="alpha",
            tier=Tier.FLIGHT_RULES,
        )
        adapter.append(decision)

        results = adapter.query(since=0.0, limit=10)
        assert len(results) == 1
        assert results[0].agent_name == "TEST"


# ── Test: Build app (composition root) ──────────────────────────────────


class TestBuildApp:
    """Verify the build_app() function wires components correctly."""

    def test_build_app_returns_all_components(self, tmp_path, monkeypatch):
        """build_app() returns a dict with all expected components."""
        # Avoid connecting to real MQTT / AWS / Ollama
        monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
        monkeypatch.setenv("MQTT_BROKER_PORT", "1883")
        monkeypatch.setenv("EDEN_SIMULATE", "true")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")

        from eden.__main__ import build_app

        # Patch out MQTT connection (it would fail without broker)
        import paho.mqtt.client as mqtt_module

        original_connect = mqtt_module.Client.connect

        def fake_connect(self, *args, **kwargs):
            pass

        monkeypatch.setattr(mqtt_module.Client, "connect", fake_connect)

        config = _make_config()
        components = build_app(config)

        assert "reconciler" in components
        assert "store" in components
        assert "telemetry_store" in components
        assert "agent_log" in components
        assert "sensor" in components
        assert "flight_rules" in components
        assert "nutrition" in components
        assert "config" in components

        # Clean up
        components["store"].stop()
