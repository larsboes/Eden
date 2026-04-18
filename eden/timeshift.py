"""EDEN Simulation Engine — fast-forward historical data through the full EDEN pipeline.

Three modes:
1. GENERATE: Create virtual sensor data, run full pipeline, record to JSONL
   python scripts/simulate.py --mode mars --days 30 --output sim_mars.jsonl
   python scripts/simulate.py --mode earth --days 30 --output sim_earth.jsonl

2. RULES-ONLY: Flight rules only (no LLM), completes in seconds
   python scripts/simulate.py --mode mars --days 30 --no-llm --output sim_mars_rules.jsonl

3. REPLAY: Stream recorded JSONL to dashboard at Nx speed
   python scripts/simulate.py --replay sim_mars.jsonl --speed 100 --serve

Side-by-side Mars vs Earth comparison is the killer demo moment:
same architecture, same agents, same flight rules — different planet.
"""

from __future__ import annotations

import json
import math
import queue
import random
import threading
import time
from pathlib import Path

import structlog

from eden.domain.models import (
    ActuatorCommand,
    DeviceType,
    MarsConditions,
    ZoneState,
)
from eden.event_bus import EventBus

logger = structlog.get_logger(__name__)


# ── Zone Profiles ─────────────────────────────────────────────────────────

# Base values are intentionally at the EDGE of desired ranges so that
# diurnal cycles and random drift regularly push zones out of bounds,
# triggering flight rules AND the agent parliament (makes the demo alive).
ZONE_PROFILES = {
    "sim-alpha": {
        "crop": "Lettuce",
        "temp_base": 24.0,      # Desired: 18-24°C — right at the ceiling
        "humidity_base": 78.0,   # Desired: 55-75% — above ceiling
        "light_hours": 16,
        "water_consumption": 0.15,
    },
    "sim-beta": {
        "crop": "Tomato",
        "temp_base": 28.0,      # Desired: 20-27°C — above ceiling
        "humidity_base": 82.0,   # Desired: 60-80% — above ceiling
        "light_hours": 14,
        "water_consumption": 0.20,
    },
    "sim-gamma": {
        "crop": "Soybean",
        "temp_base": 31.0,      # Desired: 22-30°C — above ceiling
        "humidity_base": 55.0,   # Desired: 50-70% — near floor
        "light_hours": 14,
        "water_consumption": 0.12,
    },
}


# ── Scenario Timelines ───────────────────────────────────────────────────
# (day_start, day_end, event_dict)
# These create dramatic arcs that showcase the system's response capabilities.

MARS_SCENARIOS: list[tuple[int, int, dict]] = [
    (5, 7, {
        "event": "dust_storm", "dust_opacity": 0.6,
        "label": "Minor dust storm — solar output reduced 60%",
    }),
    (15, 15, {
        "event": "radiation",
        "label": "X-class solar flare — radiation alert triggered",
    }),
    (22, 25, {
        "event": "dust_storm", "dust_opacity": 0.85,
        "label": "Major dust storm — solar output reduced 85%, power rationing",
    }),
    (28, 28, {
        "event": "sensor_failure", "zone_id": "sim-beta",
        "label": "Sensor failure in tomato bay — PATHFINDER suspects disease",
    }),
]

EARTH_SCENARIOS: list[tuple[int, int, dict]] = [
    (5, 7, {
        "event": "cold_snap", "temp_delta": -8.0,
        "label": "Cold snap — frost risk, heaters activated",
    }),
    (13, 15, {
        "event": "heat_wave", "temp_delta": 7.0,
        "label": "Heat wave — ventilation maxed, ATMOS manages humidity",
    }),
    (16, 20, {
        "event": "overcast", "light_factor": 0.3,
        "label": "Overcast period — supplemental lighting needed",
    }),
    (21, 23, {
        "event": "rain", "humidity_delta": 15.0,
        "label": "Rain — humidity spike, PATHFINDER warns of fungal risk",
    }),
    (28, 30, {
        "event": "pest_pressure", "zone_id": "sim-alpha",
        "label": "Pest pressure on lettuce — biocontrol response",
    }),
]


# ── Virtual Sensors ───────────────────────────────────────────────────────


class VirtualSensors:
    """Deterministic sensor data generator that evolves over simulated time.

    Produces realistic patterns:
    - Diurnal temperature cycle (day/night)
    - Mean-reverting random walk
    - Gradual resource consumption with auto-refill
    - Closed-loop actuator effects (fan ON → temp drops)
    - Scenario event overrides (dust storms, sensor failures, etc.)
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._sim_time = 0.0
        self._state: dict[str, dict[str, float | bool]] = {}
        self._commands_pending: dict[str, list[ActuatorCommand]] = {}

        for zone_id, prof in ZONE_PROFILES.items():
            self._state[zone_id] = {
                "temperature": prof["temp_base"] + self._rng.gauss(0, 1),
                "humidity": prof["humidity_base"] + self._rng.gauss(0, 2),
                "pressure": 1013.0 + self._rng.gauss(0, 0.5),
                "light": 400.0,
                "water_level": 80.0 + self._rng.uniform(-5, 5),
                "fire_detected": False,
            }
            self._commands_pending[zone_id] = []

    @property
    def zone_ids(self) -> list[str]:
        return list(ZONE_PROFILES.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        s = self._state.get(zone_id)
        if s is None:
            return None
        return ZoneState(
            zone_id=zone_id,
            temperature=round(s["temperature"], 2),
            humidity=round(s["humidity"], 2),
            pressure=round(s["pressure"], 2),
            light=round(max(0, s["light"]), 2),
            water_level=round(s["water_level"], 2),
            fire_detected=bool(s["fire_detected"]),
            last_updated=self._sim_time,
            is_alive=True,
            source="sim-virtual",
        )

    def send_command(self, cmd: ActuatorCommand) -> bool:
        """Accept an actuator command — effects applied next advance() cycle."""
        if cmd.zone_id in self._commands_pending:
            self._commands_pending[cmd.zone_id].append(cmd)
        return True

    def advance(
        self,
        sim_time: float,
        hour_of_day: float,
        dt_hours: float,
        scenario: dict | None = None,
    ) -> None:
        """Advance all zones by dt_hours with optional scenario overlay."""
        self._sim_time = sim_time

        for zone_id, state in self._state.items():
            prof = ZONE_PROFILES[zone_id]
            state["fire_detected"] = False

            # ── Temperature: diurnal cycle + wide random walk ──
            # Wide swing ensures zones regularly breach desired ranges
            diurnal = 4.0 * math.sin(2 * math.pi * (hour_of_day - 14) / 24)
            target = prof["temp_base"] + diurnal
            state["temperature"] += (target - state["temperature"]) * 0.25
            state["temperature"] += self._rng.gauss(0, 1.2)

            # ── Humidity: inversely correlated with temperature ──
            temp_effect = -(state["temperature"] - prof["temp_base"]) * 2.0
            target_h = prof["humidity_base"] + temp_effect
            state["humidity"] += (target_h - state["humidity"]) * 0.2
            state["humidity"] += self._rng.gauss(0, 2.5)

            # ── Light: on/off schedule ──
            if 6 <= hour_of_day <= (6 + prof["light_hours"]):
                state["light"] = 400.0 + self._rng.gauss(0, 15)
            else:
                state["light"] = 5.0 + abs(self._rng.gauss(0, 2))

            # ── Water: gradual consumption with auto-refill ──
            state["water_level"] -= dt_hours * prof["water_consumption"]
            state["water_level"] += self._rng.gauss(0, 0.05)
            if state["water_level"] < 25:
                state["water_level"] = 75.0 + self._rng.uniform(-5, 5)

            # ── Pressure: very stable ──
            state["pressure"] = 1013.0 + self._rng.gauss(0, 0.3)

            # ── Apply actuator effects (closed-loop) ──
            for cmd in self._commands_pending.get(zone_id, []):
                pwr = cmd.value / 100.0
                if cmd.device == DeviceType.FAN and cmd.action == "on":
                    state["temperature"] -= 0.8 * pwr
                    state["humidity"] -= 1.5 * pwr
                elif cmd.device == DeviceType.HEATER and cmd.action == "on":
                    state["temperature"] += 1.0 * pwr
                elif cmd.device == DeviceType.PUMP and cmd.action == "on":
                    state["water_level"] += 3.0 * pwr
                    state["humidity"] += 1.0 * pwr
                elif cmd.device == DeviceType.LIGHT and cmd.action == "on":
                    state["light"] += 150.0 * pwr
            self._commands_pending[zone_id] = []

            # ── Apply scenario overrides ──
            if scenario:
                self._apply_scenario(zone_id, state, scenario)

            # ── Clamp to physical limits ──
            state["temperature"] = max(-10, min(50, state["temperature"]))
            state["humidity"] = max(10, min(99, state["humidity"]))
            state["light"] = max(0, min(1200, state["light"]))
            state["water_level"] = max(0, min(100, state["water_level"]))
            state["pressure"] = max(900, min(1100, state["pressure"]))

    def _apply_scenario(
        self, zone_id: str, state: dict, scenario: dict,
    ) -> None:
        """Apply scenario event to a zone's state."""
        evt = scenario.get("event")
        target_zone = scenario.get("zone_id")

        if evt == "dust_storm":
            opacity = scenario.get("dust_opacity", 0.6)
            state["light"] *= (1 - opacity)
            state["temperature"] -= opacity * 3

        elif evt == "radiation":
            pass  # Flag only — no direct sensor effect

        elif evt == "sensor_failure":
            if target_zone is None or target_zone == zone_id:
                state["temperature"] = 0.0
                state["humidity"] = 0.0
                state["light"] = 0.0

        elif evt == "fire":
            if target_zone is None or target_zone == zone_id:
                state["fire_detected"] = True

        elif evt == "cold_snap":
            state["temperature"] += scenario.get("temp_delta", -5.0)

        elif evt == "heat_wave":
            state["temperature"] += scenario.get("temp_delta", 5.0)

        elif evt == "overcast":
            state["light"] *= scenario.get("light_factor", 0.3)

        elif evt == "rain":
            state["humidity"] += scenario.get("humidity_delta", 10.0)

        elif evt == "pest_pressure":
            if target_zone is None or target_zone == zone_id:
                state["humidity"] += 5.0
                state["water_level"] -= 2.0


# ── Earth Conditions ──────────────────────────────────────────────────────


def get_earth_conditions(day: int, hour: float = 12.0) -> MarsConditions:
    """Generate Earth-like conditions using MarsConditions dataclass.

    Reuses MarsConditions so the entire pipeline works unchanged.
    The sol field stores Earth day number.
    """
    # Seasonal temperature (northern hemisphere temperate)
    seasonal = 12.0 * math.sin(2 * math.pi * (day - 80) / 365)
    exterior_temp = 15.0 + seasonal
    # Diurnal exterior variation
    diurnal = 5.0 * math.sin(2 * math.pi * (hour - 14) / 24)
    exterior_temp += diurnal

    dome_temp = 22.0 + (exterior_temp - 15.0) * 0.03

    return MarsConditions(
        exterior_temp=exterior_temp,
        dome_temp=dome_temp,
        pressure_hpa=1013.25,
        solar_irradiance=1000.0,
        dust_opacity=0.0,
        sol=day,
        storm_active=False,
        radiation_alert=False,
    )


def apply_earth_transform(zone: ZoneState, conditions: MarsConditions) -> ZoneState:
    """Earth transform — mostly identity, slight exterior coupling."""
    temp_influence = (conditions.exterior_temp - 15.0) * 0.02
    return ZoneState(
        zone_id=zone.zone_id,
        temperature=zone.temperature + temp_influence,
        humidity=zone.humidity,
        pressure=zone.pressure,
        light=zone.light,
        water_level=zone.water_level,
        fire_detected=zone.fire_detected,
        last_updated=zone.last_updated,
        is_alive=zone.is_alive,
        source=zone.source,
    )


# ── Event Recorder ────────────────────────────────────────────────────────


class EventRecorder:
    """Records all EventBus events to a JSONL file for replay."""

    def __init__(self, output_path: Path, event_bus: EventBus) -> None:
        self._path = output_path
        self._bus = event_bus
        self._file = open(output_path, "w")
        self._count = 0
        self._queue = event_bus.subscribe(max_size=10000)
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._drain, daemon=True, name="event-recorder",
        )
        self._thread.start()

    def _drain(self) -> None:
        while self._running:
            try:
                event = self._queue.get(timeout=0.5)
                self._file.write(json.dumps(event, default=str) + "\n")
                self._count += 1
            except queue.Empty:
                pass
            except Exception:
                logger.debug("Recorder write error", exc_info=True)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        # Drain remaining
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                self._file.write(json.dumps(event, default=str) + "\n")
                self._count += 1
            except queue.Empty:
                break
        self._file.flush()
        self._file.close()
        self._bus.unsubscribe(self._queue)
        logger.info("Recorded %d events to %s", self._count, self._path)

    @property
    def event_count(self) -> int:
        return self._count


# ── Simulation Engine ─────────────────────────────────────────────────────


class SimulationEngine:
    """Drives the EDEN pipeline through simulated time.

    Reuses the real Reconciler, FlightRulesEngine, NutritionTracker, and
    optionally the full agent parliament (Strands SDK + Bedrock).
    Virtual sensors replace MQTT — deterministic, seedable, closed-loop.

    For Earth mode: injects Earth conditions and identity transform.
    For Mars mode: uses standard Mars transform with scenario events.
    """

    def __init__(
        self,
        mode: str = "mars",
        days: int = 30,
        cycles_per_day: int = 4,
        use_llm: bool = True,
        seed: int = 42,
        output: Path | None = None,
        start_sol: int = 0,
        inject: list[tuple[int, dict]] | None = None,
    ) -> None:
        self.mode = mode
        self.days = days
        self.cycles_per_day = cycles_per_day
        self.use_llm = use_llm
        self.seed = seed
        self.output = output or Path(f"sim_{mode}_{days}d.jsonl")
        self.start_sol = start_sol
        self.custom_events = inject or []  # [(day_offset, event_dict), ...]
        self.event_bus: EventBus | None = None
        self.sensors: VirtualSensors | None = None
        self.recorder: EventRecorder | None = None

    def run(self) -> Path:
        """Run the full simulation and return path to JSONL output."""
        logger.info(
            "=== EDEN %s Simulation: %d days, %d cycles/day, LLM=%s, seed=%d ===",
            self.mode.upper(), self.days, self.cycles_per_day,
            self.use_llm, self.seed,
        )

        self.event_bus = EventBus(history_size=5000)
        self.sensors = VirtualSensors(seed=self.seed)
        self.recorder = EventRecorder(self.output, self.event_bus)
        self.recorder.start()

        # Live console logger — prints agent events as they stream
        self._start_console_logger()

        # ── Storage (in-memory, no persistence needed) ──
        from eden.adapters.sqlite_adapter import SqliteAdapter
        from eden.adapters.synced_store import SyncedStore

        sqlite = SqliteAdapter(db_path=":memory:")
        store = SyncedStore(local=sqlite, remote=None)

        from eden.__main__ import AgentLogAdapter, TelemetryStoreAdapter

        telemetry_store = TelemetryStoreAdapter(store)
        agent_log = AgentLogAdapter(store)

        # ── Domain ──
        from eden.domain.flight_rules import FlightRulesEngine
        from eden.domain.models import CropProfile, DesiredState
        from eden.domain.nutrition import NutritionTracker
        from eden.domain.resources import ResourceTracker

        flight_rules = FlightRulesEngine()
        resource_tracker = ResourceTracker()
        default_crops = [
            CropProfile("Lettuce", "sim-alpha", 150, 13, 30, 3.5, 15, 24, 50, 80),
            CropProfile("Tomato", "sim-beta", 180, 9, 80, 5.0, 18, 27, 60, 80),
            CropProfile("Soybean", "sim-gamma", 446, 36, 90, 2.5, 20, 30, 50, 70),
        ]
        nutrition = NutritionTracker(
            crew=NutritionTracker.get_default_crew(), crops=default_crops,
        )

        # Seed desired states
        for zone_id, ds in {
            "sim-alpha": DesiredState("sim-alpha", 18, 24, 55, 75, 16, 40, 70, 5.0),
            "sim-beta": DesiredState("sim-beta", 20, 27, 60, 80, 14, 45, 70, 4.0),
            "sim-gamma": DesiredState("sim-gamma", 22, 30, 50, 70, 14, 40, 65, 3.0),
        }.items():
            store.put_desired_state(zone_id, ds)

        # ── Model chain (optional) ──
        model_chain = None
        agent_team = None
        if self.use_llm:
            model_chain, agent_team = self._setup_llm(
                default_crops, self.sensors, store, telemetry_store,
                agent_log, nutrition,
            )

        # ── Build reconciler with injectable transforms ──
        from eden.application.reconciler import Reconciler
        from eden.config import Settings

        config = Settings()
        config.RECONCILE_INTERVAL_SECONDS = 0

        # Earth vs Mars: different conditions + transform functions
        conditions_fn = None
        transform_fn = None
        if self.mode == "earth":
            conditions_fn = lambda sol: get_earth_conditions(sol)
            transform_fn = apply_earth_transform

        reconciler = Reconciler(
            sensor=self.sensors,
            actuator=self.sensors,
            state_store=store,
            telemetry_store=telemetry_store,
            agent_log=agent_log,
            model=model_chain,
            flight_rules=flight_rules,
            nutrition=nutrition,
            resource_tracker=resource_tracker,
            config=config,
            event_bus=self.event_bus,
            agent_team=agent_team,
            conditions_fn=conditions_fn,
            transform_fn=transform_fn,
        )

        # ── NASA real data (enriches Mars conditions with real weather) ──
        nasa_adapter = None
        if self.mode == "mars":
            try:
                from eden.adapters.nasa_adapter import NasaAdapter
                from eden.config import Settings as _S
                nasa_adapter = NasaAdapter(api_key=_S().NASA_API_KEY)
                logger.info("NASA adapter wired — real Mars weather + solar data")
            except Exception:
                logger.info("NASA adapter unavailable — using computed Mars conditions")

        # ── Scenario timeline (built-in + custom injected events) ──
        scenarios = list(MARS_SCENARIOS if self.mode == "mars" else EARTH_SCENARIOS)
        for day_offset, event_dict in self.custom_events:
            scenarios.append((day_offset, day_offset, event_dict))
        scenarios.sort(key=lambda s: s[0])

        # ── Run simulation loop ──
        total_cycles = self.days * self.cycles_per_day
        dt_hours = 24.0 / self.cycles_per_day
        wall_start = time.time()

        self.event_bus.publish("simulation_start", {
            "mode": self.mode,
            "days": self.days,
            "start_sol": self.start_sol,
            "cycles_per_day": self.cycles_per_day,
            "total_cycles": total_cycles,
            "use_llm": self.use_llm,
            "seed": self.seed,
            "scenarios": [s[2].get("label", s[2].get("event", "")) for s in scenarios],
            "custom_events": len(self.custom_events),
        })

        for cycle in range(total_cycles):
            day = cycle // self.cycles_per_day
            cycle_in_day = cycle % self.cycles_per_day
            hour_of_day = cycle_in_day * dt_hours
            sim_time = cycle * dt_hours * 3600
            # Absolute sol/day = start_sol + relative day
            abs_sol = self.start_sol + day

            # Active scenario for this day (relative)
            active_scenario = None
            for s_start, s_end, s_data in scenarios:
                if s_start <= day <= s_end:
                    active_scenario = s_data
                    break

            # Advance virtual sensors
            self.sensors.advance(
                sim_time=sim_time,
                hour_of_day=hour_of_day,
                dt_hours=dt_hours,
                scenario=active_scenario,
            )

            # Emit scenario event
            if active_scenario and cycle_in_day == 0:
                self.event_bus.publish("scenario_event", {
                    "day": day,
                    "sol": abs_sol,
                    "hour": hour_of_day,
                    "mode": self.mode,
                    **active_scenario,
                })

            # Set sol/day (absolute)
            reconciler._current_sol = abs_sol

            # Wire NASA real data for Mars mode
            if nasa_adapter is not None:
                reconciler._nasa_adapter = nasa_adapter

            # Run full reconciliation cycle
            try:
                decisions = reconciler.reconcile_once()

                # Log progress at end of each day
                if (cycle + 1) % self.cycles_per_day == 0:
                    elapsed = time.time() - wall_start
                    scenario_label = active_scenario.get("label", "nominal") if active_scenario else "nominal"
                    sol_label = f"Sol {abs_sol}" if self.mode == "mars" else f"Day {abs_sol}"
                    logger.info(
                        "%s (day %d/%d) — %d decisions — %s [%.1fs elapsed]",
                        sol_label, day + 1, self.days, len(decisions),
                        scenario_label, elapsed,
                    )
            except Exception:
                logger.exception("Simulation cycle %d (day %d) failed", cycle, day)

        # ── Finalize ──
        self.event_bus.publish("simulation_complete", {
            "mode": self.mode,
            "days": self.days,
            "total_cycles": total_cycles,
            "elapsed_seconds": time.time() - wall_start,
            "events_recorded": self.recorder.event_count,
        })

        time.sleep(1)  # Let recorder drain
        self.recorder.stop()
        sqlite.close()

        logger.info(
            "=== Simulation complete: %s %d days, %d events → %s (%.1fs) ===",
            self.mode.upper(), self.days, self.recorder.event_count,
            self.output, time.time() - wall_start,
        )
        return self.output

    def _start_console_logger(self) -> None:
        """Subscribe to EventBus and print agent events to console in real-time."""
        q = self.event_bus.subscribe(max_size=5000)

        # Event types worth printing live
        _LOUD_EVENTS = {
            "round1_start", "agent_started", "agent_proposal",
            "agent_token", "agent_tool_call", "agent_complete",
            "deliberation_start", "deliberation_response",
            "coordinator_start", "coordinator_resolution",
            "parliament_start", "parliament_skipped",
            "scenario_event", "flight_rule", "alert", "command",
            "strands_agent_complete", "agent_error",
        }
        _bus = self.event_bus

        def _drain():
            import sys
            while True:
                try:
                    event = q.get(timeout=1.0)
                    etype = event.get("type", "")
                    data = event.get("data", {})

                    sim_log = structlog.get_logger("eden.sim.console")

                    if etype == "agent_token":
                        token = data.get("token", "")
                        if token:
                            sys.stdout.write(token)
                            sys.stdout.flush()

                    elif etype == "agent_started":
                        sim_log.info("agent_thinking", agent=data.get("agent_name", "?"), zone_id=data.get("zone_id", ""))

                    elif etype == "agent_tool_call":
                        sim_log.info("agent_tool_call", agent=data.get("agent_name", "?"), tool=data.get("tool_name", "?"))

                    elif etype == "agent_complete":
                        sim_log.info("agent_complete", agent=data.get("agent_name", "?"), chars=len(data.get("full_text", "")))

                    elif etype == "agent_proposal":
                        sim_log.info("agent_proposal", agent=data.get("agent_name", "?"), severity=data.get("severity", ""), action=data.get("action", "")[:120])

                    elif etype == "coordinator_resolution":
                        sim_log.info("coordinator_resolution", reasoning=data.get("reasoning", "")[:300])

                    elif etype == "scenario_event":
                        sim_log.warning("scenario_event", label=data.get("label", data.get("event", "?")))

                    elif etype == "alert":
                        sim_log.warning("sim_alert", zone_id=data.get("zone_id", "?"), severity=data.get("severity", "?"), rule=data.get("rule", data.get("reasoning", "?"))[:100])

                    elif etype == "parliament_start":
                        sim_log.info("parliament_convening", zones=data.get("zones_with_deltas", []))

                    elif etype == "round1_start":
                        sim_log.info("round1_start", agent_count=data.get("agent_count", "?"))

                    elif etype == "deliberation_start":
                        sim_log.info("round2_deliberation")

                    elif etype == "coordinator_start":
                        sim_log.info("round3_coordinator_synthesizing")

                except queue.Empty:
                    pass
                except Exception:
                    pass

        t = threading.Thread(target=_drain, daemon=True, name="console-logger")
        t.start()

    def _setup_llm(
        self,
        crops,
        sensors,
        store,
        telemetry_store,
        agent_log,
        nutrition,
    ):
        """Initialize LLM model chain + agent parliament. Returns (model, team) or (None, None)."""
        try:
            from eden.adapters.bedrock_adapter import BedrockAdapter
            from eden.adapters.model_chain import ModelChain
            from eden.application.agent import AgentTeam

            bedrock = BedrockAdapter(region="us-west-2")
            model_chain = ModelChain([bedrock])

            zone_crops = {c.zone_id: c.name for c in crops}
            agent_team = AgentTeam(
                model=model_chain,
                sensor=sensors,
                actuator=sensors,
                state_store=store,
                telemetry_store=telemetry_store,
                agent_log=agent_log,
                nutrition=nutrition,
                zone_crops=zone_crops,
                event_bus=self.event_bus,
            )
            agent_team.enable_strands()
            logger.info("Agent parliament enabled for simulation")
            return model_chain, agent_team
        except Exception:
            logger.warning(
                "LLM unavailable — running rules-only simulation", exc_info=True,
            )
            return None, None


# ── Replay ────────────────────────────────────────────────────────────────


def replay(
    jsonl_path: Path,
    speed: float = 100.0,
    serve: bool = False,
) -> None:
    """Replay recorded events from JSONL at Nx speed.

    If serve=True, starts the API server so dashboard can connect via SSE.
    No LLM calls. No sensors. No reconciler. Pure event replay.
    """
    event_bus = EventBus(history_size=5000)

    events: list[dict] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if not events:
        logger.error("No events found in %s", jsonl_path)
        return

    logger.info(
        "Loaded %d events from %s — replaying at %.0fx speed",
        len(events), jsonl_path, speed,
    )

    if serve:
        _start_replay_api(event_bus)

    # Replay with timing
    event_bus.publish("replay_start", {
        "source": str(jsonl_path),
        "event_count": len(events),
        "speed": speed,
    })

    first_ts = events[0].get("timestamp", 0)
    replay_start = time.time()

    for i, event in enumerate(events):
        event_ts = event.get("timestamp", 0)
        relative_time = event_ts - first_ts

        # Wait for correct replay time
        target_real_time = replay_start + (relative_time / speed)
        wait = target_real_time - time.time()
        if wait > 0.001:
            time.sleep(wait)

        event_bus.publish(
            event.get("type", "unknown"),
            event.get("data", {}),
        )

        if (i + 1) % 100 == 0:
            elapsed = time.time() - replay_start
            sim_elapsed = relative_time
            effective = sim_elapsed / elapsed if elapsed > 0 else 0
            logger.info(
                "Replay: %d/%d events (sim: %.0fs, real: %.1fs, ~%.0fx)",
                i + 1, len(events), sim_elapsed, elapsed, effective,
            )

    event_bus.publish("replay_complete", {
        "events_replayed": len(events),
        "elapsed_seconds": time.time() - replay_start,
    })
    logger.info("Replay complete: %d events in %.1fs", len(events), time.time() - replay_start)

    if serve:
        logger.info("API server running on :8000 — press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def _start_replay_api(event_bus: EventBus) -> None:
    """Start the FastAPI server for replay mode."""
    from eden.api import app

    app.state.event_bus = event_bus
    app.state.state_store = None
    app.state.telemetry_store = None
    app.state.agent_log = None
    app.state.model = None
    app.state.nutrition = None
    app.state.flight_rules = None
    app.state.reconciler = None
    app.state.sim = None
    app.state.start_time = time.time()
    app.state.reconciler_running = True
    app.state.mqtt_connected = False
    app.state.current_sol = 0
    app.state.zone_ids = []

    def run_api():
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

    api_thread = threading.Thread(target=run_api, daemon=True, name="api-replay")
    api_thread.start()
    logger.info("API server started on :8000 for replay SSE streaming")
    time.sleep(1)
