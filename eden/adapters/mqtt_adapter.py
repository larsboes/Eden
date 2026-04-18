"""MQTT adapter — implements SensorPort + ActuatorPort.

Thread-safe, auto-reconnect, validates JSON, never crashes on bad input.
"""

from __future__ import annotations

import json
import structlog
import threading
from typing import Callable

import paho.mqtt.client as mqtt

from eden.domain.models import (
    ActuatorCommand,
    SensorReading,
    SensorType,
    ZoneState,
)

logger = structlog.get_logger(__name__)

# Sensor key → (SensorType enum, unit string)
_SENSOR_MAP: dict[str, tuple[SensorType, str]] = {
    "temperature": (SensorType.TEMPERATURE, "celsius"),
    "humidity": (SensorType.HUMIDITY, "percent"),
    "pressure": (SensorType.PRESSURE, "hpa"),
    "light": (SensorType.LIGHT, "lux"),
    "water_level": (SensorType.WATER_LEVEL, "mm"),
    "fire": (SensorType.FIRE, "boolean"),
}


class MqttAdapter:
    """MQTT-based SensorPort + ActuatorPort implementation.

    Subscribes to eden/+/telemetry and eden/+/heartbeat.
    Publishes to eden/{zone_id}/command.
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        client_id: str = "eden-agent",
    ) -> None:
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        self._client.on_message = self._on_message
        self._client.on_connect = self._on_connect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._zones: dict[str, ZoneState] = {}
        self._lock = threading.Lock()
        self._subscribers: list[Callable[[SensorReading], None]] = []

    # ── SensorPort interface ──────────────────────────────────────────

    def start(self) -> None:
        """Connect to MQTT broker and start the network loop."""
        self._client.connect(self._broker_host, self._broker_port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        """Disconnect from MQTT broker."""
        self._client.loop_stop()
        self._client.disconnect()

    def get_latest(self, zone_id: str) -> ZoneState | None:
        """Return the most recent ZoneState for a zone, or None."""
        with self._lock:
            return self._zones.get(zone_id)

    def subscribe(self, callback: Callable[[SensorReading], None]) -> None:
        """Register a callback that fires on each new SensorReading."""
        self._subscribers.append(callback)

    # ── ActuatorPort interface ────────────────────────────────────────

    def send_command(self, command: ActuatorCommand) -> bool:
        """Publish an actuator command to MQTT. Returns True on success."""
        topic = f"eden/{command.zone_id}/command"
        payload = json.dumps(command.to_dict())
        result = self._client.publish(topic, payload)
        if result.rc != 0:
            logger.error("Failed to publish command to %s (rc=%d)", topic, result.rc)
            return False
        return True

    # ── Internal callbacks ────────────────────────────────────────────

    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties) -> None:
        """Subscribe to topics on (re)connect."""
        if reason_code == 0:
            client.subscribe("eden/+/telemetry")
            client.subscribe("eden/+/heartbeat")
            logger.info("Connected to MQTT broker, subscribed to topics")
        else:
            logger.error("MQTT connect failed with reason_code=%s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata, msg) -> None:
        """Parse incoming MQTT messages. Never raises."""
        try:
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 3:
                return

            zone_id = topic_parts[1]
            msg_type = topic_parts[2]

            payload = json.loads(msg.payload.decode("utf-8"))

            if msg_type == "telemetry":
                self._handle_telemetry(zone_id, payload)
            elif msg_type == "heartbeat":
                self._handle_heartbeat(zone_id, payload)

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Malformed MQTT message on %s: %s", msg.topic, e)
        except Exception as e:
            logger.error("Unexpected error processing MQTT message: %s", e)

    def _handle_telemetry(self, zone_id: str, payload: dict) -> None:
        """Parse telemetry payload into ZoneState + fire subscriber callbacks."""
        if "sensors" not in payload:
            logger.warning("Telemetry from %s missing 'sensors' key, dropping", zone_id)
            return

        sensors = payload["sensors"]
        timestamp = payload.get("timestamp", 0.0)
        source = payload.get("source", "unknown")

        state = ZoneState(
            zone_id=zone_id,
            temperature=sensors.get("temperature", {}).get("value", 0.0),
            humidity=sensors.get("humidity", {}).get("value", 0.0),
            pressure=sensors.get("pressure", {}).get("value", 0.0),
            light=sensors.get("light", {}).get("value", 0.0),
            water_level=sensors.get("water_level", {}).get("value", 0.0),
            fire_detected=bool(sensors.get("fire", {}).get("value", 0)),
            last_updated=timestamp,
            is_alive=True,
            source=source,
        )

        with self._lock:
            self._zones[zone_id] = state

        # Build individual SensorReading objects and fire callbacks
        readings = self._extract_readings(zone_id, sensors, timestamp, source)
        for callback in self._subscribers:
            for reading in readings:
                try:
                    callback(reading)
                except Exception as e:
                    logger.error("Subscriber callback error: %s", e)

    def _handle_heartbeat(self, zone_id: str, payload: dict) -> None:
        """Update zone liveness from heartbeat."""
        with self._lock:
            if zone_id in self._zones:
                self._zones[zone_id].is_alive = True
                self._zones[zone_id].last_updated = payload.get(
                    "timestamp", self._zones[zone_id].last_updated
                )

    def _extract_readings(
        self,
        zone_id: str,
        sensors: dict,
        timestamp: float,
        source: str,
    ) -> list[SensorReading]:
        """Convert sensor dict into a list of SensorReading objects."""
        readings = []
        for key, (sensor_type, unit) in _SENSOR_MAP.items():
            if key in sensors:
                readings.append(
                    SensorReading(
                        zone_id=zone_id,
                        sensor_type=sensor_type,
                        value=float(sensors[key].get("value", 0.0)),
                        unit=unit,
                        timestamp=timestamp,
                        source=source,
                    )
                )
        return readings
