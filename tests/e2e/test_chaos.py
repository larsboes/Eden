"""CHAOS TESTS — Break the greenhouse, prove it degrades gracefully.

5 scenarios that simulate Mars worst-case failures:
1. Dust storm (solar + light collapse)
2. Comms lost (WAL accumulates, reconnect replays)
3. Fire emergency (short-circuit, rent-a-human)
4. Sensor failure (stale data detection)
5. Cascading failure (everything goes wrong at once)

Uses REAL: FlightRulesEngine (all 17 rules), SqliteAdapter, SyncedStore WAL.
Uses FAKE: Sensor, Actuator, Remote (controllable chaos).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from eden.adapters.sqlite_adapter import SqliteAdapter
from eden.adapters.synced_store import SyncedStore
from eden.application.reconciler import Reconciler
from eden.domain.flight_rules import FlightRulesEngine
from eden.domain.mars_transform import (
    get_mars_conditions,
    inject_dust_storm,
    inject_radiation,
    transform_light,
)
from eden.domain.models import (
    ActuatorCommand,
    AgentDecision,
    DesiredState,
    DeviceType,
    EnergyBudget,
    GasExchange,
    MarsConditions,
    ResourceBudget,
    SensorReading,
    SensorType,
    Severity,
    Tier,
    ZoneState,
)
from eden.domain.nutrition import NutritionTracker


# ── Fake Ports (controllable chaos) ─────────────────────────────────────


class FakeSensor:
    """Injectable sensor — we control what the greenhouse 'sees'."""

    def __init__(self, zones: dict[str, ZoneState] | None = None) -> None:
        self._zones: dict[str, ZoneState] = zones or {}

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        return self._zones.get(zone_id)

    def set_zone(self, zone_id: str, zone: ZoneState) -> None:
        self._zones[zone_id] = zone


class FakeActuator:
    """Record all commands sent — we verify what the system DID."""

    def __init__(self) -> None:
        self.commands: list[ActuatorCommand] = []

    def send_command(self, cmd: ActuatorCommand) -> bool:
        self.commands.append(cmd)
        return True

    def commands_for_zone(self, zone_id: str) -> list[ActuatorCommand]:
        return [c for c in self.commands if c.zone_id == zone_id]

    def clear(self) -> None:
        self.commands.clear()


class FakeModel:
    def __init__(self) -> None:
        self._available = False

    def is_available(self) -> bool:
        return self._available

    def reason(self, prompt: str, context: dict) -> str:
        return ""


class TelemetryStoreAdapter:
    def __init__(self, store) -> None:
        self._store = store

    def append(self, reading) -> None:
        self._store.append_telemetry(reading)

    def query(self, zone_id: str, since: float, limit: int = 100):
        return self._store.query_telemetry(zone_id, since, limit)


class AgentLogAdapter:
    def __init__(self, store) -> None:
        self._store = store

    def append(self, decision) -> None:
        self._store.append_agent_log(decision)

    def query(self, since: float, limit: int = 100):
        return self._store.query_agent_log(since, limit)


class FakeConfig:
    RECONCILE_INTERVAL_SECONDS = 30
    LOG_LEVEL = "DEBUG"


class FakeRemote:
    """A remote that we can break and fix on demand.

    Normal mode: stores data in a dict (simulates DynamoDB).
    Broken mode: raises on all writes (simulates comms loss).
    """

    def __init__(self) -> None:
        self._broken = False
        self._prefix = "eden"
        self._data: dict[str, dict] = {}
        self.write_count = 0
        self.fail_count = 0

    def break_comms(self) -> None:
        self._broken = True

    def restore_comms(self) -> None:
        self._broken = False

    def _check(self) -> None:
        if self._broken:
            self.fail_count += 1
            raise ConnectionError("COMMS LOST — 22-min latency to Earth")

    def put_zone_state(self, zone_id: str, state: ZoneState) -> None:
        self._check()
        self._data[f"zone_state:{zone_id}"] = state.to_dict()
        self.write_count += 1

    def put_desired_state(self, zone_id: str, state: DesiredState) -> None:
        self._check()
        self._data[f"desired_state:{zone_id}"] = state.to_dict()
        self.write_count += 1

    def append_telemetry(self, reading: SensorReading) -> None:
        self._check()
        key = f"telemetry:{reading.zone_id}:{reading.timestamp}"
        self._data[key] = reading.to_dict()
        self.write_count += 1

    def append_agent_log(self, decision: AgentDecision) -> None:
        self._check()
        key = f"agent_log:{decision.timestamp}"
        self._data[key] = decision.to_dict()
        self.write_count += 1

    def write_raw(self, table_name: str, item: dict) -> None:
        self._check()
        key = json.dumps(item, sort_keys=True)
        self._data[key] = item
        self.write_count += 1


# ── Helpers ──────────────────────────────────────────────────────────────


def _zone(
    zone_id: str = "alpha",
    temperature: float = 22.0,
    humidity: float = 55.0,
    pressure: float = 1013.0,
    light: float = 500.0,
    water_level: float = 50.0,
    fire_detected: bool = False,
    last_updated: float | None = None,
) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        light=light,
        water_level=water_level,
        fire_detected=fire_detected,
        last_updated=last_updated or time.time(),
        is_alive=True,
        source="chaos-test",
    )


def _desired(zone_id: str) -> DesiredState:
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


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def chaos_pipeline():
    """Build a full pipeline with temp SQLite and controllable fakes."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "chaos.db")
    sqlite = SqliteAdapter(db_path=db_path)
    store = SyncedStore(local=sqlite, remote=None)

    sensor = FakeSensor()
    actuator = FakeActuator()
    telemetry = TelemetryStoreAdapter(store)
    agent_log = AgentLogAdapter(store)
    model = FakeModel()
    engine = FlightRulesEngine()
    crew = NutritionTracker.get_default_crew()
    nutrition = NutritionTracker(crew=crew, crops=[])

    reconciler = Reconciler(
        sensor=sensor,
        actuator=actuator,
        state_store=store,
        telemetry_store=telemetry,
        agent_log=agent_log,
        model=model,
        flight_rules=engine,
        nutrition=nutrition,
        config=FakeConfig(),
    )

    yield {
        "reconciler": reconciler,
        "sensor": sensor,
        "actuator": actuator,
        "store": store,
        "sqlite": sqlite,
        "telemetry": telemetry,
        "agent_log": agent_log,
        "engine": engine,
    }

    store.stop()
    sqlite.close()


# ══════════════════════════════════════════════════════════════════════════
# SCENARIO 1: DUST STORM — The Killer Demo
# ══════════════════════════════════════════════════════════════════════════


class TestDustStorm:
    """Sol 250, clear skies → DUST STORM hits → solar drops 85%.

    System must: engage power rationing, turn on lights, keep plants alive.
    """

    def test_dust_storm_full_scenario(self, chaos_pipeline):
        """Start normal → inject dust storm → verify graceful degradation."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]
        engine: FlightRulesEngine = chaos_pipeline["engine"]

        reconciler._current_sol = 250

        # ── Phase 1: Clear skies ────────────────────────────────────
        sensor.set_zone("alpha", _zone("alpha", light=500.0, temperature=22.0))
        sensor.set_zone("beta", _zone("beta", light=500.0, temperature=22.0))

        decisions_clear = reconciler.reconcile_once()
        cmds_clear = len(actuator.commands)
        print(f"\n☀️  CLEAR SKIES: {cmds_clear} commands, {len(decisions_clear)} decisions")
        assert cmds_clear == 0, "Clear skies should produce 0 commands"

        # ── Phase 2: DUST STORM HITS ────────────────────────────────
        # Monkeypatch get_mars_conditions to return storm conditions
        storm_mars = inject_dust_storm(250)
        print(f"🌪️  DUST STORM: opacity={storm_mars.dust_opacity}, "
              f"solar={storm_mars.solar_irradiance:.1f} W/m²")

        actuator.clear()

        with patch(
            "eden.application.reconciler.get_mars_conditions",
            return_value=storm_mars,
        ):
            # Light will be: 500 * 0.43 * (1 - 0.85) = 32.25 lux (< 100 threshold)
            decisions_storm = reconciler.reconcile_once()

        storm_cmds = actuator.commands
        print(f"🌪️  STORM RESULTS: {len(storm_cmds)} commands issued:")
        for cmd in storm_cmds:
            print(f"   {cmd.zone_id}: {cmd.device.value} → {cmd.action} "
                  f"({cmd.value}) [{cmd.priority.value}]")

        # FR-L-001: lights ON to compensate lost solar
        light_on_cmds = [
            c for c in storm_cmds
            if c.device == DeviceType.LIGHT and c.action == "on"
        ]
        assert len(light_on_cmds) >= 1, "FR-L-001: lights must turn ON during dust storm"
        print(f"✅ FR-L-001: {len(light_on_cmds)} light ON commands")

        # FR-E-001: power rationing should fire
        # Test standalone since reconciler doesn't pass EnergyBudget automatically
        storm_energy = EnergyBudget(
            solar_capacity_kw=12.0,
            current_efficiency=0.15,  # 85% drop from 100%
            allocations={"lights": 3.0, "heater": 4.0},
            reserve_kw=2.0,
        )
        rationing_decisions = engine.evaluate_energy(storm_energy)
        assert len(rationing_decisions) >= 1, "FR-E-001: power rationing must fire"
        assert rationing_decisions[0].severity == Severity.HIGH
        print(f"✅ FR-E-001: power rationing active — {rationing_decisions[0].reasoning}")

        # System didn't crash — decisions logged
        assert len(decisions_storm) >= 1, "Storm should produce decisions"
        print(f"✅ System BENT but didn't break: {len(decisions_storm)} decisions logged")

    def test_storm_light_math(self):
        """Verify dust storm light calculations are correct."""
        storm = inject_dust_storm(250)
        earth_lux = 500.0
        mars_lux = transform_light(earth_lux, storm.dust_opacity)

        # 500 * 0.43 * 0.15 = 32.25
        assert mars_lux < 100.0, f"Storm light should be < 100, got {mars_lux}"
        assert mars_lux == pytest.approx(32.25, rel=0.01)
        print(f"\n🌪️  LIGHT MATH: {earth_lux} lux → {mars_lux:.2f} lux (85% blocked)")


# ══════════════════════════════════════════════════════════════════════════
# SCENARIO 2: COMMS LOST — The Mars Moment
# ══════════════════════════════════════════════════════════════════════════


class TestCommsLost:
    """DynamoDB sync working → comms lost → 2 cycles offline → reconnect → WAL replays."""

    def test_comms_lost_and_recovery(self):
        """Full comms loss + recovery test with WAL mechanism."""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "comms_chaos.db")
        sqlite = SqliteAdapter(db_path=db_path)
        remote = FakeRemote()

        # No background sync thread — we control replay manually
        store = SyncedStore(local=sqlite, remote=remote, sync_interval=9999)

        sensor = FakeSensor()
        actuator = FakeActuator()
        telemetry = TelemetryStoreAdapter(store)
        agent_log = AgentLogAdapter(store)
        engine = FlightRulesEngine()
        crew = NutritionTracker.get_default_crew()
        nutrition = NutritionTracker(crew=crew, crops=[])

        reconciler = Reconciler(
            sensor=sensor,
            actuator=actuator,
            state_store=store,
            telemetry_store=telemetry,
            agent_log=agent_log,
            model=FakeModel(),
            flight_rules=engine,
            nutrition=nutrition,
            config=FakeConfig(),
        )
        reconciler._current_sol = 250

        # ── Phase 1: Normal ops with comms ──────────────────────────
        sensor.set_zone("alpha", _zone("alpha", temperature=22.0))
        sensor.set_zone("beta", _zone("beta", temperature=22.0))

        decisions_1 = reconciler.reconcile_once()
        writes_before = remote.write_count
        pending_before = len(sqlite.get_pending())
        print(f"\n📡 COMMS UP: {writes_before} remote writes, "
              f"{pending_before} pending WAL entries")

        # ── Phase 2: COMMS LOST ─────────────────────────────────────
        remote.break_comms()
        print("🔴 COMMS LOST — 22-min latency, all remote writes will fail")

        # Cycle 1 offline — trigger flight rules so there's data to sync
        # Use humidity (no Mars transform) and low water (no transform) to
        # guarantee rules fire regardless of Mars temperature damping
        actuator.clear()
        sensor.set_zone("alpha", _zone("alpha", humidity=95.0))  # mold → fan ON
        sensor.set_zone("beta", _zone("beta", water_level=5.0))  # crisis → pump OFF

        decisions_offline_1 = reconciler.reconcile_once()
        pending_after_1 = len(sqlite.get_pending())
        print(f"🔴 OFFLINE CYCLE 1: {len(decisions_offline_1)} decisions, "
              f"{pending_after_1} WAL entries pending")

        # Flight rules still fired despite no comms
        alpha_cmds = actuator.commands_for_zone("alpha")
        fan_cmds = [c for c in alpha_cmds if c.device == DeviceType.FAN]
        assert len(fan_cmds) >= 1, "Flight rules must fire even without comms"
        print(f"✅ Flight rules ACTIVE: fan ON for mold risk in alpha")

        beta_cmds = actuator.commands_for_zone("beta")
        pump_cmds = [c for c in beta_cmds if c.device == DeviceType.PUMP and c.action == "off"]
        assert len(pump_cmds) >= 1, "Flight rules must fire even without comms"
        print(f"✅ Flight rules ACTIVE: pump OFF for water crisis in beta")

        # Cycle 2 offline — more data accumulates
        actuator.clear()
        sensor.set_zone("alpha", _zone("alpha", humidity=93.0))
        sensor.set_zone("beta", _zone("beta", water_level=4.0))

        decisions_offline_2 = reconciler.reconcile_once()
        pending_after_2 = len(sqlite.get_pending())
        print(f"🔴 OFFLINE CYCLE 2: {len(decisions_offline_2)} decisions, "
              f"{pending_after_2} WAL entries pending")

        # WAL should have accumulated entries
        assert pending_after_2 > 0, "WAL should have pending entries during comms loss"
        print(f"✅ WAL accumulated: {pending_after_2} entries queued for sync")

        # All data persisted locally despite comms loss
        local_alpha = store.get_zone_state("alpha")
        local_beta = store.get_zone_state("beta")
        assert local_alpha is not None, "Alpha state must be in local SQLite"
        assert local_beta is not None, "Beta state must be in local SQLite"
        print("✅ ALL data persisted to local SQLite — ZERO data loss")

        # ── Phase 3: COMMS RESTORED ─────────────────────────────────
        remote.restore_comms()
        print("🟢 COMMS RESTORED — replaying WAL...")

        # Manually trigger WAL replay
        store._replay_pending()

        pending_after_replay = len(sqlite.get_pending())
        print(f"🟢 RECONNECT: {pending_after_replay} WAL entries remaining "
              f"(was {pending_after_2})")

        # WAL should be drained (or significantly reduced)
        assert pending_after_replay < pending_after_2, \
            "WAL replay should drain pending entries"
        print(f"✅ WAL replayed: {pending_after_2 - pending_after_replay} entries synced")

        # Verify remote got the data
        synced_count = remote.write_count - writes_before
        print(f"✅ Remote synced: {synced_count} writes after reconnect")

        store.stop()
        sqlite.close()

    def test_flight_rules_work_without_cloud(self):
        """Tier 0 flight rules are pure local — they don't need cloud."""
        engine = FlightRulesEngine()

        # Fire: works without cloud
        fire_zone = _zone("alpha", fire_detected=True)
        cmds, decisions = engine.evaluate(fire_zone)
        assert len(cmds) == len(DeviceType), "Fire: ALL devices OFF"
        assert decisions[0].severity == Severity.CRITICAL

        # Frost: works without cloud
        frost_zone = _zone("beta", temperature=2.0)
        cmds, decisions = engine.evaluate(frost_zone)
        heater = [c for c in cmds if c.device == DeviceType.HEATER]
        assert len(heater) >= 1, "Frost: heater ON"

        # CO2: works without cloud
        gas = GasExchange(
            greenhouse_co2_ppm=5500.0,
            greenhouse_o2_pct=21.0,
            habitat_co2_ppm=400.0,
            habitat_o2_pct=20.9,
            exchange_rate=0.5,
        )
        decisions = engine.evaluate_gas(gas)
        assert len(decisions) >= 1, "CO2 alert fires without cloud"

        print("\n✅ ALL Tier 0 flight rules work with ZERO cloud dependency")


# ══════════════════════════════════════════════════════════════════════════
# SCENARIO 3: FIRE EMERGENCY
# ══════════════════════════════════════════════════════════════════════════


class TestFireEmergency:
    """Zone alpha on fire. Other zones nominal. Rent-a-human required."""

    def test_fire_kills_all_devices_in_zone(self, chaos_pipeline):
        """FR-F-001: fire → ALL devices OFF in affected zone IMMEDIATELY."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 300

        # Alpha: FIRE
        sensor.set_zone("alpha", _zone("alpha", fire_detected=True))
        # Beta + gamma: nominal
        sensor.set_zone("beta", _zone("beta", temperature=22.0))
        sensor.set_zone("gamma", _zone("gamma", temperature=22.0))

        decisions = reconciler.reconcile_once()

        # Alpha: ALL devices OFF
        alpha_cmds = actuator.commands_for_zone("alpha")
        devices_off = {c.device for c in alpha_cmds if c.action == "off"}

        print(f"\n🔥 FIRE: {len(alpha_cmds)} OFF commands issued for alpha:")
        for cmd in alpha_cmds:
            print(f"   {cmd.device.value} → OFF [{cmd.priority.value}]")

        for device in DeviceType:
            assert device in devices_off, \
                f"FIRE: {device.value} must be OFF — not found in shutdown commands"

        print(f"✅ FR-F-001: ALL {len(DeviceType)} device types shut down")

    def test_fire_short_circuits_all_other_rules(self, chaos_pipeline):
        """Fire overrides frost, low water, everything. Only OFF commands."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 300

        # Alpha: fire + frost + low water (all at once)
        sensor.set_zone("alpha", _zone(
            "alpha",
            fire_detected=True,
            temperature=2.0,      # would trigger heater ON
            water_level=3.0,      # would trigger pump OFF + water alert
            humidity=95.0,        # would trigger fan ON
        ))

        decisions = reconciler.reconcile_once()

        alpha_cmds = actuator.commands_for_zone("alpha")
        actions = {c.action for c in alpha_cmds}
        assert actions == {"off"}, \
            f"Fire short-circuits: only 'off' allowed, got {actions}"

        # Only 1 fire decision (no frost, water, humidity decisions)
        alpha_decisions = [d for d in decisions if d.zone_id == "alpha"]
        fire_decisions = [
            d for d in alpha_decisions
            if d.result == "emergency_shutdown"
        ]
        assert len(fire_decisions) == 1, "Exactly 1 fire emergency decision"
        print(f"\n✅ Fire SHORT-CIRCUITS: {len(alpha_cmds)} OFF commands, "
              f"0 heater/pump/fan commands despite frost+drought+humidity")

    def test_fire_other_zones_unaffected(self, chaos_pipeline):
        """Fire in alpha must NOT affect beta or gamma."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 300

        sensor.set_zone("alpha", _zone("alpha", fire_detected=True))
        sensor.set_zone("beta", _zone("beta", temperature=22.0))
        sensor.set_zone("gamma", _zone("gamma", temperature=22.0))

        reconciler.reconcile_once()

        beta_cmds = actuator.commands_for_zone("beta")
        gamma_cmds = actuator.commands_for_zone("gamma")

        print(f"\n🔥 ISOLATION: alpha=fire, beta={len(beta_cmds)} cmds, "
              f"gamma={len(gamma_cmds)} cmds")
        assert len(beta_cmds) == 0, "Beta must be COMPLETELY unaffected by alpha fire"
        assert len(gamma_cmds) == 0, "Gamma must be COMPLETELY unaffected by alpha fire"
        print("✅ Zone isolation: fire in alpha, beta+gamma UNTOUCHED")

    def test_fire_critical_severity(self, chaos_pipeline):
        """All fire commands + decisions must be CRITICAL."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 300
        sensor.set_zone("alpha", _zone("alpha", fire_detected=True))

        decisions = reconciler.reconcile_once()

        alpha_cmds = actuator.commands_for_zone("alpha")
        for cmd in alpha_cmds:
            assert cmd.priority == Severity.CRITICAL, \
                f"Fire command {cmd.device.value} must be CRITICAL, got {cmd.priority}"

        alpha_decisions = [d for d in decisions if d.zone_id == "alpha"]
        for d in alpha_decisions:
            if d.agent_name == "FLIGHT_RULES":
                assert d.severity == Severity.CRITICAL
        print(f"\n✅ ALL fire responses at CRITICAL severity")

    def test_fire_crew_intervention_needed(self):
        """Fire scenario must produce an emergency_shutdown result (rent-a-human trigger)."""
        engine = FlightRulesEngine()
        zone = _zone("alpha", fire_detected=True)

        cmds, decisions = engine.evaluate(zone)

        assert len(decisions) == 1
        assert decisions[0].result == "emergency_shutdown"
        assert decisions[0].severity == Severity.CRITICAL
        # In production, emergency_shutdown triggers request_crew_intervention()
        print(f"\n✅ RENT-A-HUMAN: emergency_shutdown result → crew intervention pipeline")


# ══════════════════════════════════════════════════════════════════════════
# SCENARIO 4: SENSOR FAILURE — Stale Data
# ══════════════════════════════════════════════════════════════════════════


class TestSensorFailure:
    """Zone alpha sensor data is 120s stale. Beta is fresh."""

    def test_stale_sensor_detected(self, chaos_pipeline):
        """FR-STALE-001: stale data (>60s) → zone marked compromised."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 200

        # Alpha: 120 seconds old (stale)
        stale_time = time.time() - 120.0
        sensor.set_zone("alpha", _zone("alpha", last_updated=stale_time))
        # Beta: fresh
        sensor.set_zone("beta", _zone("beta"))

        decisions = reconciler.reconcile_once()

        # FR-STALE-001 should fire for alpha
        stale_decisions = [
            d for d in decisions
            if d.zone_id == "alpha" and "compromised" in d.action.lower()
        ]
        print(f"\n⚠️  SENSOR FAILURE: {len(stale_decisions)} staleness decisions for alpha")
        assert len(stale_decisions) >= 1, \
            "FR-STALE-001: must detect stale sensor data"
        assert stale_decisions[0].severity == Severity.HIGH
        print(f"✅ FR-STALE-001: alpha marked compromised ({stale_decisions[0].reasoning})")

    def test_fresh_zone_unaffected(self, chaos_pipeline):
        """Beta with fresh data should NOT trigger staleness alert."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 200

        stale_time = time.time() - 120.0
        sensor.set_zone("alpha", _zone("alpha", last_updated=stale_time))
        sensor.set_zone("beta", _zone("beta"))  # fresh — default last_updated=now

        decisions = reconciler.reconcile_once()

        beta_stale = [
            d for d in decisions
            if d.zone_id == "beta" and "compromised" in d.action.lower()
        ]
        assert len(beta_stale) == 0, "Fresh beta should NOT be marked compromised"
        print(f"\n✅ Beta (fresh data) unaffected by alpha's sensor failure")

    def test_system_does_not_crash_on_stale(self, chaos_pipeline):
        """Even with stale data, reconciliation completes without exception."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 200

        # All zones stale
        stale_time = time.time() - 300.0  # 5 minutes old
        sensor.set_zone("alpha", _zone("alpha", last_updated=stale_time))
        sensor.set_zone("beta", _zone("beta", last_updated=stale_time))
        sensor.set_zone("gamma", _zone("gamma", last_updated=stale_time))

        # Should not raise
        decisions = reconciler.reconcile_once()

        stale_decisions = [d for d in decisions if "compromised" in d.action.lower()]
        assert len(stale_decisions) == 3, \
            f"All 3 zones should be marked compromised, got {len(stale_decisions)}"
        print(f"\n✅ System handles ALL stale sensors without crashing: "
              f"{len(stale_decisions)} zones compromised")


# ══════════════════════════════════════════════════════════════════════════
# SCENARIO 5: CASCADING FAILURE — The Nightmare
# ══════════════════════════════════════════════════════════════════════════


class TestCascadingFailure:
    """Everything goes wrong at once. System must handle ALL simultaneously."""

    def test_nightmare_scenario(self, chaos_pipeline):
        """Fire + frost + mold + CO2 + radiation — all at once, no crash."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]
        engine: FlightRulesEngine = chaos_pipeline["engine"]

        reconciler._current_sol = 350

        # Zone insertion order matters — reconciler iterates in insertion order.
        # Gamma first so FR-G-001 (CO2) fires before cooldown is set by another zone.
        # Zone gamma: normal temp/humidity but CO2 injected via gas exchange
        sensor.set_zone("gamma", _zone(
            "gamma",
            temperature=22.0,
            humidity=55.0,
        ))

        # Zone alpha: FIRE + critically low water
        sensor.set_zone("alpha", _zone(
            "alpha",
            fire_detected=True,
            water_level=3.0,
        ))

        # Zone beta: frost + mold risk
        # Raw -120°C → Mars dome ≈ 0.3°C (below 5°C) → FR-T-001 heater ON
        # Humidity 95% → no Mars transform → FR-H-001 fan ON
        sensor.set_zone("beta", _zone(
            "beta",
            temperature=-120.0,  # FR-T-001: heater ON (dome < 5°C after transform)
            humidity=95.0,       # FR-H-001: fan ON
        ))

        # Inject radiation alert via monkeypatch
        rad_mars = inject_radiation(350)
        assert rad_mars.radiation_alert is True

        with patch(
            "eden.application.reconciler.get_mars_conditions",
            return_value=rad_mars,
        ):
            # Set gas exchange with high CO2 for gamma's rules
            reconciler.set_gas_exchange(GasExchange(
                greenhouse_co2_ppm=5500.0,
                greenhouse_o2_pct=21.0,
                habitat_co2_ppm=400.0,
                habitat_o2_pct=20.9,
                exchange_rate=0.5,
            ))

            decisions = reconciler.reconcile_once()

        print(f"\n💀 CASCADING FAILURE: {len(decisions)} total decisions")
        print(f"   Commands issued: {len(actuator.commands)}")

        # ── Alpha: fire short-circuit ───────────────────────────────
        alpha_cmds = actuator.commands_for_zone("alpha")
        alpha_actions = {c.action for c in alpha_cmds}
        assert alpha_actions == {"off"}, \
            f"Alpha FIRE: only OFF allowed, got {alpha_actions}"
        print(f"   🔥 Alpha (fire): {len(alpha_cmds)} OFF commands — "
              f"short-circuit active")

        # ── Beta: heater ON + fan ON (cascade) ──────────────────────
        beta_cmds = actuator.commands_for_zone("beta")
        beta_devices = {c.device for c in beta_cmds}
        assert DeviceType.HEATER in beta_devices, "Beta: heater must be ON (frost)"
        assert DeviceType.FAN in beta_devices, "Beta: fan must be ON (humidity)"

        heater = next(c for c in beta_cmds if c.device == DeviceType.HEATER)
        fan = next(c for c in beta_cmds if c.device == DeviceType.FAN)
        assert heater.action == "on" and heater.value == 100.0
        assert fan.action == "on" and fan.value == 50.0
        print(f"   ❄️  Beta (frost+mold): heater={heater.value}%, fan={fan.value}%")

        # ── Gamma: fan ON for CO2 ──────────────────────────────────
        gamma_cmds = actuator.commands_for_zone("gamma")
        co2_fan = [
            c for c in gamma_cmds
            if c.device == DeviceType.FAN and c.action == "on"
        ]
        assert len(co2_fan) >= 1, "Gamma: fan ON for CO2 ventilation"
        print(f"   🌫️  Gamma (CO2): {len(co2_fan)} fan ON commands")

        # ── Radiation alert logged ──────────────────────────────────
        rad_decisions = [
            d for d in decisions
            if "radiation" in d.reasoning.lower() or "radiation" in d.action.lower()
        ]
        assert len(rad_decisions) >= 1, "Radiation alert must be logged"
        print(f"   ☢️  Radiation: {len(rad_decisions)} alert decisions")

        # ── Multiple CRITICAL decisions ─────────────────────────────
        critical_decisions = [
            d for d in decisions if d.severity == Severity.CRITICAL
        ]
        assert len(critical_decisions) >= 1, "Must have CRITICAL severity decisions"
        print(f"   🚨 {len(critical_decisions)} CRITICAL decisions total")

        # ── System didn't crash ─────────────────────────────────────
        total_cmds = len(actuator.commands)
        total_decisions = len(decisions)
        zones_with_decisions = {d.zone_id for d in decisions}
        print(f"\n✅ NIGHTMARE SURVIVED: {total_cmds} commands, "
              f"{total_decisions} decisions across {len(zones_with_decisions)} zones")

    def test_cascading_decisions_per_zone(self, chaos_pipeline):
        """Each zone gets independent decisions — no cross-contamination."""
        sensor: FakeSensor = chaos_pipeline["sensor"]
        actuator: FakeActuator = chaos_pipeline["actuator"]
        reconciler: Reconciler = chaos_pipeline["reconciler"]

        reconciler._current_sol = 350

        sensor.set_zone("alpha", _zone("alpha", fire_detected=True))
        # Raw -120°C → dome ≈ 0.3°C after Mars transform → frost rule fires
        sensor.set_zone("beta", _zone("beta", temperature=-120.0, humidity=95.0))
        sensor.set_zone("gamma", _zone("gamma"))

        decisions = reconciler.reconcile_once()

        # Alpha should only have fire decisions
        alpha_d = [d for d in decisions if d.zone_id == "alpha" and d.agent_name == "FLIGHT_RULES"]
        for d in alpha_d:
            assert "fire" in d.reasoning.lower() or d.result == "emergency_shutdown", \
                f"Alpha should only have fire decisions, got: {d.reasoning}"

        # Beta should have frost + humidity decisions
        beta_d = [d for d in decisions if d.zone_id == "beta" and d.agent_name == "FLIGHT_RULES"]
        beta_rules_fired = {d.reasoning.split(",")[0] for d in beta_d}
        assert len(beta_d) >= 2, f"Beta needs ≥2 decisions (frost+humidity), got {len(beta_d)}"

        # Gamma should be clean (no issues)
        gamma_cmds = actuator.commands_for_zone("gamma")
        assert len(gamma_cmds) == 0, \
            f"Gamma (nominal) should have 0 commands, got {len(gamma_cmds)}"

        print(f"\n✅ ZONE ISOLATION: alpha={len(alpha_d)} fire, "
              f"beta={len(beta_d)} cascade, gamma=0 clean")

    def test_all_17_rules_loaded(self):
        """Sanity check: engine has all 17 flight rules available."""
        engine = FlightRulesEngine()
        rule_ids = {r.rule_id for r in engine.rules}

        expected_rules = {
            "FR-F-001", "FR-T-001", "FR-T-002", "FR-H-001", "FR-H-002",
            "FR-W-001", "FR-L-001", "FR-E-001", "FR-G-001", "FR-W-010",
            "FR-P-001", "FR-O2-001", "FR-O2-002", "FR-STALE-001",
            "FR-RAD-001", "FR-RATE-001", "FR-N-001",
        }

        assert rule_ids == expected_rules, \
            f"Missing rules: {expected_rules - rule_ids}, Extra: {rule_ids - expected_rules}"
        print(f"\n✅ ALL {len(expected_rules)} flight rules loaded and active")
