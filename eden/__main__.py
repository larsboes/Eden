"""EDEN entry point — composition root that wires all concrete adapters.

The ONLY file that knows about concrete adapter classes.
Runs both the reconciler loop AND the FastAPI server in the same process.

Entry point: python -m eden
"""

from __future__ import annotations

import logging
import os
import re
import signal
import sys
import threading
import time

import structlog

from eden.config import Settings
from eden.logging_config import configure_logging


# ── Port adapters (bridge adapter method names to port interfaces) ───────


class TelemetryStoreAdapter:
    """Adapts SyncedStore to TelemetryStorePort interface."""

    def __init__(self, store) -> None:
        self._store = store

    def append(self, reading) -> None:
        self._store.append_telemetry(reading)

    def query(self, zone_id: str, since: float, limit: int = 100):
        return self._store.query_telemetry(zone_id, since, limit)


class AgentLogAdapter:
    """Adapts SyncedStore to AgentLogPort interface."""

    def __init__(self, store) -> None:
        self._store = store

    def append(self, decision) -> None:
        self._store.append_agent_log(decision)

    def query(self, since: float, limit: int = 100):
        return self._store.query_agent_log(since, limit)


class SensorAdapter:
    """Wraps MqttAdapter to expose zone_ids property for the reconciler."""

    def __init__(self, mqtt_adapter) -> None:
        self._mqtt = mqtt_adapter

    @property
    def zone_ids(self) -> list[str]:
        return list(self._mqtt._zones.keys())

    def get_latest(self, zone_id: str):
        return self._mqtt.get_latest(zone_id)

    def start(self) -> None:
        self._mqtt.start()

    def stop(self) -> None:
        self._mqtt.stop()

    def subscribe(self, callback) -> None:
        self._mqtt.subscribe(callback)


class _NullActuator:
    """No-op actuator when MQTT is unavailable."""

    def send_command(self, cmd) -> None:
        pass


# ── Syngenta KB enrichment helper ─────────────────────────────────────────


def _parse_range(text: str, keyword: str) -> tuple[float, float] | None:
    """Try to extract a numeric range for a keyword from KB text.

    Looks for patterns like "temperature: 18-24°C" or "optimal temp 18 to 24".
    """
    patterns = [
        rf"{keyword}\s*[:\-]?\s*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)",
        rf"(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*°?\s*[CF]?\s*{keyword}",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1)), float(m.group(2))
            except (ValueError, IndexError):
                pass
    return None


def _enrich_desired_from_syngenta(
    syngenta_kb,
    defaults: dict,
    crops: list,
    logger,
) -> dict:
    """Query Syngenta KB for each crop and try to extract optimal ranges.

    Returns enriched DesiredState dict. Falls back to defaults if KB is
    unavailable or responses can't be parsed.
    """
    from eden.domain.models import DesiredState

    if syngenta_kb is None or not syngenta_kb.is_available():
        return defaults

    enriched = dict(defaults)
    crop_map = {c.zone_id: c.name for c in crops}

    for zone_id, crop_name in crop_map.items():
        try:
            resp = syngenta_kb.check_crop_profile(crop_name)
            result_text = str(resp.get("result", ""))
            if not result_text or "unavailable" in result_text.lower():
                continue

            logger.info("syngenta_kb_response", crop=crop_name, zone_id=zone_id, response_preview=result_text[:200])

            base = defaults[zone_id]

            # Try to extract ranges from KB response
            temp_range = _parse_range(result_text, "temp")
            humidity_range = _parse_range(result_text, "humid")

            if temp_range or humidity_range:
                enriched[zone_id] = DesiredState(
                    zone_id=zone_id,
                    temp_min=temp_range[0] if temp_range else base.temp_min,
                    temp_max=temp_range[1] if temp_range else base.temp_max,
                    humidity_min=humidity_range[0] if humidity_range else base.humidity_min,
                    humidity_max=humidity_range[1] if humidity_range else base.humidity_max,
                    light_hours=base.light_hours,
                    soil_moisture_min=base.soil_moisture_min,
                    soil_moisture_max=base.soil_moisture_max,
                    water_budget_liters_per_day=base.water_budget_liters_per_day,
                )
                logger.info(
                    "desired_state_enriched",
                    zone_id=zone_id,
                    temp_min=enriched[zone_id].temp_min,
                    temp_max=enriched[zone_id].temp_max,
                    humidity_min=enriched[zone_id].humidity_min,
                    humidity_max=enriched[zone_id].humidity_max,
                )
        except Exception:
            logger.warning("syngenta_enrichment_failed", zone_id=zone_id, exc_info=True)

    return enriched


# ── App builder ──────────────────────────────────────────────────────────


def build_app(config: Settings | None = None) -> dict:
    """Wire all components and return them as a dict. Testable composition."""
    if config is None:
        config = Settings()

    configure_logging(log_level=config.LOG_LEVEL)
    logger = structlog.get_logger("eden")

    # ── EventBus ──────────────────────────────────────────────────────
    from eden.event_bus import EventBus

    event_bus = EventBus(history_size=500)
    logger.info("event_bus_initialized", history_size=500)

    # ── Storage ──────────────────────────────────────────────────────
    from eden.adapters.sqlite_adapter import SqliteAdapter
    from eden.adapters.synced_store import SyncedStore

    sqlite = SqliteAdapter(db_path="eden.db")

    dynamo = None
    try:
        from eden.adapters.dynamo_adapter import DynamoAdapter

        dynamo = DynamoAdapter(
            table_prefix=config.DYNAMO_TABLE_PREFIX,
            region=config.AWS_REGION,
        )
        logger.info("dynamo_adapter_initialized", region=config.AWS_REGION, prefix=config.DYNAMO_TABLE_PREFIX)
    except Exception:
        logger.info("dynamo_unavailable", mode="local-only")

    store = SyncedStore(local=sqlite, remote=dynamo)
    telemetry_store = TelemetryStoreAdapter(store)
    agent_log = AgentLogAdapter(store)

    # ── Models ───────────────────────────────────────────────────────
    from eden.adapters.model_chain import ModelChain

    models = []
    try:
        from eden.adapters.bedrock_adapter import BedrockAdapter

        bedrock = BedrockAdapter(region=config.AWS_REGION)
        models.append(bedrock)
        logger.info("bedrock_adapter_initialized", region=config.AWS_REGION)
    except Exception:
        logger.info("bedrock_unavailable")

    try:
        from eden.adapters.ollama_adapter import OllamaAdapter

        ollama = OllamaAdapter(host=config.OLLAMA_HOST, model=config.OLLAMA_MODEL)
        models.append(ollama)
        logger.info("ollama_adapter_initialized", host=config.OLLAMA_HOST, model=config.OLLAMA_MODEL)
    except Exception:
        logger.info("ollama_unavailable")

    model_chain = ModelChain(models) if models else None

    # ── Sensor adapter ─────────────────────────────────────────────────
    #   EDEN_USE_HARDWARE=true  → real Pi sensors via HTTP
    #   EDEN_USE_MQTT=true      → MQTT broker + optional sim
    #   default                 → in-memory simulated zones
    from eden.adapters.memory_sensor import MemorySensorAdapter

    mqtt_adapter = None
    hw_adapter = None
    sim = None
    use_hardware = os.getenv("EDEN_USE_HARDWARE", "false").lower() == "true"
    use_mqtt = os.getenv("EDEN_USE_MQTT", "false").lower() == "true"

    if use_hardware:
        try:
            from eden.adapters.hardware_adapter import HardwareAdapter

            hw_adapter = HardwareAdapter(
                base_url=config.HARDWARE_API_URL,
                zone_id=config.HARDWARE_ZONE_ID,
                poll_interval=config.HARDWARE_POLL_INTERVAL,
            )
            sensor = hw_adapter  # HardwareAdapter has zone_ids, get_latest, start, stop
            logger.info(
                "hardware_sensor_initialized",
                url=config.HARDWARE_API_URL,
                zone_id=config.HARDWARE_ZONE_ID,
                poll_interval=config.HARDWARE_POLL_INTERVAL,
            )
        except Exception:
            logger.warning("hardware_adapter_unavailable", fallback="memory_sensor")
            sensor = MemorySensorAdapter()
    elif use_mqtt:
        try:
            from eden.adapters.mqtt_adapter import MqttAdapter

            mqtt_adapter = MqttAdapter(
                broker_host=config.MQTT_BROKER_HOST,
                broker_port=config.MQTT_BROKER_PORT,
            )
            sensor = SensorAdapter(mqtt_adapter)

            if config.EDEN_SIMULATE:
                from eden.adapters.simulated_sensors import SimulatedSensors

                sim = SimulatedSensors(mqtt_client=mqtt_adapter._client)
            logger.info("mqtt_sensor_initialized", host=config.MQTT_BROKER_HOST, port=config.MQTT_BROKER_PORT)
        except Exception:
            logger.info("mqtt_unavailable", fallback="memory_sensor")
            sensor = MemorySensorAdapter()
    else:
        sensor = MemorySensorAdapter()
        logger.info("memory_sensor_initialized", zones=len(sensor.zone_ids))

    # ── Domain ───────────────────────────────────────────────────────
    from eden.domain.flight_rules import FlightRulesEngine
    from eden.domain.models import CropProfile, DesiredState
    from eden.domain.nutrition import NutritionTracker
    from eden.domain.resources import ResourceTracker

    flight_rules = FlightRulesEngine()

    # Default crops per zone — 4 zones, 8 crops, matching dashboard layout
    # Zone IDs match MemorySensorAdapter: zone-protein, zone-carb, zone-vitamin, zone-support
    default_crops = [
        # Zone A: PROTEIN — Soybean + Lentil
        CropProfile("Soybean", "zone-protein", 446.0, 36.5, 90, 3.0, 20.0, 30.0, 50.0, 70.0),
        CropProfile("Lentil", "zone-protein", 353.0, 25.8, 90, 1.0, 18.0, 28.0, 50.0, 75.0),
        # Zone B: CARB — Potato + Wheat
        CropProfile("Potato", "zone-carb", 77.0, 2.0, 80, 4.0, 15.0, 22.0, 55.0, 75.0),
        CropProfile("Wheat", "zone-carb", 339.0, 13.2, 120, 0.5, 15.0, 25.0, 50.0, 70.0),
        # Zone C: VITAMIN — Tomato + Spinach
        CropProfile("Tomato", "zone-vitamin", 18.0, 0.9, 70, 8.0, 18.0, 27.0, 60.0, 80.0),
        CropProfile("Spinach", "zone-vitamin", 23.0, 2.9, 45, 2.0, 15.0, 22.0, 50.0, 75.0),
        # Zone D: SUPPORT — Basil + Microgreens
        CropProfile("Basil", "zone-support", 23.0, 3.2, 40, 1.5, 20.0, 28.0, 55.0, 80.0),
        CropProfile("Microgreens", "zone-support", 31.0, 3.0, 14, 2.0, 18.0, 25.0, 50.0, 75.0),
    ]
    zone_crops: dict[str, list[str]] = {}
    for c in default_crops:
        zone_crops.setdefault(c.zone_id, []).append(c.name)

    crew = NutritionTracker.get_default_crew()
    nutrition = NutritionTracker(crew=crew, crops=default_crops)
    resource_tracker = ResourceTracker()

    # Seed desired states for 4 zones — matches MemorySensorAdapter zone IDs
    _default_desired = {
        "zone-protein": DesiredState("zone-protein", temp_min=20.0, temp_max=28.0,
                                     humidity_min=50.0, humidity_max=70.0, light_hours=16.0,
                                     soil_moisture_min=40.0, soil_moisture_max=70.0,
                                     water_budget_liters_per_day=5.0),
        "zone-carb": DesiredState("zone-carb", temp_min=15.0, temp_max=25.0,
                                  humidity_min=55.0, humidity_max=75.0, light_hours=14.0,
                                  soil_moisture_min=45.0, soil_moisture_max=70.0,
                                  water_budget_liters_per_day=6.0),
        "zone-vitamin": DesiredState("zone-vitamin", temp_min=18.0, temp_max=27.0,
                                     humidity_min=40.0, humidity_max=80.0, light_hours=16.0,
                                     soil_moisture_min=50.0, soil_moisture_max=75.0,
                                     water_budget_liters_per_day=5.0),
        "zone-support": DesiredState("zone-support", temp_min=20.0, temp_max=26.0,
                                     humidity_min=55.0, humidity_max=80.0, light_hours=12.0,
                                     soil_moisture_min=45.0, soil_moisture_max=70.0,
                                     water_budget_liters_per_day=3.0),
    }
    # When using hardware, seed desired state for the Pi zone as well
    if use_hardware:
        hw_zone = config.HARDWARE_ZONE_ID
        if hw_zone not in _default_desired:
            _default_desired[hw_zone] = DesiredState(
                hw_zone, temp_min=18.0, temp_max=28.0,
                humidity_min=40.0, humidity_max=75.0, light_hours=16.0,
                soil_moisture_min=30.0, soil_moisture_max=70.0,
                water_budget_liters_per_day=5.0,
            )

    for zone_id, desired in _default_desired.items():
        store.put_desired_state(zone_id, desired)
    logger.info("desired_states_seeded", zone_count=len(_default_desired))

    # ── MCP Adapters (Syngenta KB + NASA) ──────────────────────────
    from eden.adapters.mcp_adapter import NasaMCPAdapter, SyngentaKBAdapter

    agentcore_url = config.AGENTCORE_GATEWAY_ENDPOINT
    if agentcore_url:
        logger.info("agentcore_gateway_detected", url=agentcore_url)

    syngenta_kb = SyngentaKBAdapter(
        gateway_url=config.SYNGENTA_MCP_GATEWAY_URL,
        auth_token=config.SYNGENTA_MCP_AUTH_TOKEN,
    )
    try:
        syngenta_kb.connect()
        if syngenta_kb.is_available():
            logger.info("syngenta_kb_connected", tools=len(syngenta_kb.list_tools()))
        else:
            logger.info("syngenta_kb_offline", fallback="local_knowledge")
    except Exception:
        logger.info("syngenta_kb_connection_failed", fallback="local_knowledge")

    nasa_mcp = NasaMCPAdapter(api_key=config.NASA_API_KEY)
    try:
        nasa_mcp.connect()
        if nasa_mcp.is_available():
            logger.info("nasa_mcp_connected", tools=len(nasa_mcp.list_tools()))
        else:
            logger.info("nasa_mcp_offline", fallback="local_knowledge")
    except Exception:
        logger.info("nasa_mcp_connection_failed", fallback="local_knowledge")

    # ── Council (replaces 12-agent parliament with consensus quorum) ──
    from eden.application.council import Council

    agent_team = None  # Same variable name so reconciler works unchanged
    if model_chain:
        agent_team = Council(
            model=model_chain,
            sensor=sensor,
            actuator=hw_adapter or mqtt_adapter,
            state_store=store,
            telemetry_store=telemetry_store,
            agent_log=agent_log,
            nutrition=nutrition,
            zone_crops=zone_crops,
            event_bus=event_bus,
            syngenta_kb=syngenta_kb if syngenta_kb.is_available() else None,
            nasa_mcp=nasa_mcp if nasa_mcp.is_available() else None,
            quorum_size=int(os.getenv("EDEN_QUORUM_SIZE", "5")),
            temperature=float(os.getenv("EDEN_COUNCIL_TEMP", "0.8")),
        )
        # Enable Strands SDK for real tool calling (BedrockModel + @tool)
        if agent_team.enable_strands():
            logger.info("council_initialized", backend="strands_sdk", quorum=agent_team._quorum_size, temperature=agent_team._temperature)
        else:
            logger.info("council_initialized", backend="model_reason_fallback")

    # ── External APIs (HTTP — feeds reconciler Mars conditions) ─────
    from eden.adapters.nasa_adapter import NasaAdapter

    nasa = NasaAdapter(api_key=config.NASA_API_KEY)

    # ── Syngenta KB -> enrich DesiredState at startup ─────────────────
    _enriched = _enrich_desired_from_syngenta(
        syngenta_kb, _default_desired, default_crops, logger,
    )
    for zone_id, desired in _enriched.items():
        store.put_desired_state(zone_id, desired)
    enriched_count = sum(1 for z in _default_desired if _enriched[z] is not _default_desired[z])
    if enriched_count:
        logger.info("desired_states_enriched", source="syngenta_kb", zones_enriched=enriched_count)

    # ── Application ──────────────────────────────────────────────────
    from eden.application.reconciler import Reconciler

    reconciler = Reconciler(
        sensor=sensor,
        actuator=hw_adapter or mqtt_adapter or _NullActuator(),
        state_store=store,
        telemetry_store=telemetry_store,
        agent_log=agent_log,
        model=model_chain,
        flight_rules=flight_rules,
        nutrition=nutrition,
        resource_tracker=resource_tracker,
        config=config,
        event_bus=event_bus,
        agent_team=agent_team,
        nasa_adapter=nasa,
    )

    return {
        "config": config,
        "event_bus": event_bus,
        "sqlite": sqlite,
        "store": store,
        "telemetry_store": telemetry_store,
        "agent_log": agent_log,
        "model": model_chain,
        "mqtt": mqtt_adapter,
        "hardware": hw_adapter,
        "sensor": sensor,
        "sim": sim,
        "flight_rules": flight_rules,
        "nutrition": nutrition,
        "resource_tracker": resource_tracker,
        "reconciler": reconciler,
        "nasa": nasa,
        "syngenta_kb": syngenta_kb,
        "nasa_mcp": nasa_mcp,
    }


def wire_api(components: dict) -> None:
    """Wire all components into the FastAPI app.state for the API to use."""
    from eden.api import app

    app.state.event_bus = components["event_bus"]
    app.state.state_store = components["store"]
    app.state.telemetry_store = components["telemetry_store"]
    app.state.agent_log = components["agent_log"]
    app.state.model = components["model"]
    app.state.nutrition = components["nutrition"]
    app.state.flight_rules = components["flight_rules"]
    app.state.reconciler = components["reconciler"]
    app.state.resource_tracker = components["resource_tracker"]
    app.state.sensor = components["sensor"]
    app.state.sim = components["sim"]
    app.state.start_time = time.time()
    app.state.reconciler_running = False
    app.state.mqtt_connected = False
    app.state.current_sol = 0

    # Zone IDs are dynamic — property-like access via sensor adapter
    sensor = components["sensor"]

    class _ZoneIds:
        """Proxy that always returns current zone IDs from the sensor adapter."""
        def __iter__(self):
            return iter(sensor.zone_ids)
        def __len__(self):
            return len(sensor.zone_ids)

    app.state.zone_ids = _ZoneIds()


# ── Entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Build app, start services, run reconciler + API server."""
    components = build_app()
    logger = structlog.get_logger("eden")

    # Wire API state
    wire_api(components)

    shutdown_event = threading.Event()

    def shutdown(sig, frame):
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()
        components["reconciler"].stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start sensor adapter (hardware, MQTT, or memory)
    try:
        components["sensor"].start()
        if components["hardware"]:
            logger.info("hardware_sensor_started", url=components["config"].HARDWARE_API_URL)
        else:
            logger.info("sensor_started")
        from eden.api import app
        app.state.mqtt_connected = components["mqtt"] is not None
    except Exception:
        logger.warning("sensor_start_failed")

    # Start simulated sensors (only for MQTT mode)
    if components["sim"]:
        components["sim"].start()
        logger.info("simulated_sensors_started")

    # Start reconciler in background thread
    def run_reconciler():
        from eden.api import app
        app.state.reconciler_running = True
        try:
            components["reconciler"].run()
        finally:
            app.state.reconciler_running = False

    reconciler_thread = threading.Thread(
        target=run_reconciler,
        daemon=True,
        name="reconciler",
    )
    reconciler_thread.start()
    logger.info("reconciler_thread_started")

    # Run API server in main thread
    api_port = int(os.getenv("EDEN_API_PORT", "8000"))
    api_host = os.getenv("EDEN_API_HOST", "0.0.0.0")
    logger.info("api_server_starting", host=api_host, port=api_port)

    try:
        import uvicorn
        from eden.api import app

        uvicorn.run(
            app,
            host=api_host,
            port=api_port,
            log_level="info",
            access_log=False,
        )
    except ImportError:
        logger.warning("uvicorn_unavailable", mode="reconciler_only")
        # Fallback: just wait for the reconciler thread
        try:
            while not shutdown_event.is_set():
                shutdown_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            pass

    # Cleanup
    logger.info("shutdown_started")
    components["reconciler"].stop()
    if components["sim"]:
        components["sim"].stop()
    try:
        components["sensor"].stop()
    except Exception:
        pass
    # Disconnect MCP adapters
    for mcp_key in ("syngenta_kb", "nasa_mcp"):
        try:
            components[mcp_key].disconnect()
        except Exception:
            pass
    components["store"].stop()
    components["sqlite"].close()
    logger.info("eden_offline")


if __name__ == "__main__":
    main()
