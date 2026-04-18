"""Simulated sensors — background thread publishing fake sensor data to MQTT.

Zones: sim-alpha, sim-beta, sim-gamma (default).
Realistic fluctuations with gradual drift, occasional anomalies,
and injectable failure events.
"""

from __future__ import annotations

import json
import structlog
import random
import threading
import time

import paho.mqtt.client as mqtt

logger = structlog.get_logger(__name__)

# Base values and drift ranges per sensor
# Drift is intentionally wide so zones regularly exceed desired ranges,
# triggering flight rules and the agent parliament (makes the demo alive).
_SENSOR_PROFILES = {
    "temperature": {"base": 24.0, "drift": 6.0, "unit": "celsius"},
    "humidity": {"base": 65.0, "drift": 15.0, "unit": "percent"},
    "pressure": {"base": 1013.0, "drift": 5.0, "unit": "hpa"},
    "light": {"base": 400.0, "drift": 150.0, "unit": "lux"},
    "water_level": {"base": 70.0, "drift": 20.0, "unit": "mm"},
}


class SimulatedSensors:
    """Publishes fake sensor data to MQTT for testing without real hardware."""

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        zones: list[str] | None = None,
        interval: float = 10.0,
    ) -> None:
        self._client = mqtt_client
        self._zones = zones or ["sim-alpha", "sim-beta", "sim-gamma"]
        self._interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._start_time = time.time()

        # Per-zone current values (gradual drift state)
        self._state: dict[str, dict[str, float]] = {}
        for zone in self._zones:
            self._state[zone] = {
                k: v["base"] + random.uniform(-v["drift"] * 0.5, v["drift"] * 0.5)
                for k, v in _SENSOR_PROFILES.items()
            }

        # Per-zone pending events (one-shot)
        self._pending_events: dict[str, str | None] = {z: None for z in self._zones}

    # ── Public API ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background publishing thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sim-sensors")
        self._thread.start()
        logger.info("Simulated sensors started for zones: %s", self._zones)

    def stop(self) -> None:
        """Stop the background publishing thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval * 2)
        self._thread = None

    def inject_event(self, zone_id: str, event_type: str) -> None:
        """Inject a one-shot anomaly event for a zone.

        Supported events: spike, sensor_failure, fire, comms_lost, drop
        """
        if zone_id in self._pending_events:
            self._pending_events[zone_id] = event_type
            logger.info("Injected event '%s' for zone '%s'", event_type, zone_id)

    # ── Internal ──────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Background loop: publish telemetry + heartbeats."""
        heartbeat_counter = 0
        while self._running:
            self._publish_telemetry()
            heartbeat_counter += 1
            # Heartbeats at ~2x telemetry rate (every 5s if interval=10s)
            if heartbeat_counter % 2 == 0 or self._interval < 1.0:
                self._publish_heartbeats()
            time.sleep(self._interval)

    def _publish_telemetry(self) -> None:
        """Publish one telemetry batch for all zones."""
        for zone_id in self._zones:
            event = self._pending_events.get(zone_id)
            self._pending_events[zone_id] = None  # Clear one-shot event

            sensors = self._generate_sensors(zone_id, event)
            payload = {
                "zone_id": zone_id,
                "source": f"sim-{zone_id}",
                "timestamp": time.time(),
                "sensors": sensors,
            }
            topic = f"eden/{zone_id}/telemetry"
            self._client.publish(topic, json.dumps(payload))

    def _publish_heartbeats(self) -> None:
        """Publish heartbeat for all zones."""
        now = time.time()
        for zone_id in self._zones:
            payload = {
                "zone_id": zone_id,
                "source": f"sim-{zone_id}",
                "uptime_seconds": int(now - self._start_time),
                "timestamp": now,
            }
            topic = f"eden/{zone_id}/heartbeat"
            self._client.publish(topic, json.dumps(payload))

    def _generate_sensors(self, zone_id: str, event: str | None) -> dict:
        """Generate sensor readings with drift, optional anomaly."""
        state = self._state[zone_id]

        # Handle injected events
        if event == "sensor_failure":
            return {
                k: {"value": 0.0, "unit": v["unit"]}
                for k, v in _SENSOR_PROFILES.items()
            } | {"fire": {"value": 0, "unit": "boolean"}}

        if event == "fire":
            # Normal readings but fire detected
            self._drift(state)
            sensors = self._state_to_sensors(state)
            sensors["fire"] = {"value": 1, "unit": "boolean"}
            return sensors

        if event == "spike":
            # Temperature spike
            self._drift(state)
            state["temperature"] = random.uniform(35.0, 40.0)
            sensors = self._state_to_sensors(state)
            sensors["fire"] = {"value": 0, "unit": "boolean"}
            return sensors

        if event == "drop":
            state["temperature"] = random.uniform(5.0, 10.0)
            sensors = self._state_to_sensors(state)
            sensors["fire"] = {"value": 0, "unit": "boolean"}
            return sensors

        if event == "light_failure":
            # Light sensor reads 0 (cable disconnected) — other sensors normal
            self._drift(state)
            sensors = self._state_to_sensors(state)
            sensors["light"] = {"value": 0.0, "unit": "lux"}
            sensors["fire"] = {"value": 0, "unit": "boolean"}
            return sensors

        # Normal operation: gradual drift
        self._drift(state)
        sensors = self._state_to_sensors(state)
        sensors["fire"] = {"value": 0, "unit": "boolean"}
        return sensors

    def _drift(self, state: dict[str, float]) -> None:
        """Apply small random drift to sensor values, clamped to realistic ranges."""
        for key, profile in _SENSOR_PROFILES.items():
            step = random.gauss(0, profile["drift"] * 0.1)
            state[key] += step
            # Clamp to base ± 2*drift
            lo = profile["base"] - 2 * profile["drift"]
            hi = profile["base"] + 2 * profile["drift"]
            state[key] = max(lo, min(hi, state[key]))

    def _state_to_sensors(self, state: dict[str, float]) -> dict:
        """Convert internal state dict to MQTT sensor payload format."""
        return {
            k: {"value": round(state[k], 2), "unit": _SENSOR_PROFILES[k]["unit"]}
            for k in _SENSOR_PROFILES
        }
