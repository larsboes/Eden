"""Hardware adapter — polls the Pi sensor API over HTTP.

Drop-in replacement for MemorySensorAdapter + actuator.
Talks to Johannes's FastAPI service (sensor_api.py) on the Raspberry Pi.

Env vars:
    EDEN_USE_HARDWARE=true          # activate this adapter
    HARDWARE_API_URL=http://IP:8001 # Pi FastAPI base URL
    HARDWARE_ZONE_ID=zone1          # zone ID the Pi represents
    HARDWARE_POLL_INTERVAL=10       # seconds between polls
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import httpx
import structlog

from eden.domain.models import (
    ActuatorCommand,
    DeviceType,
    SensorReading,
    SensorType,
    ZoneState,
)

logger = structlog.get_logger(__name__)

# Pi reading field → (SensorType, unit)
_READING_MAP: dict[str, tuple[SensorType, str]] = {
    "temperature_c": (SensorType.TEMPERATURE, "celsius"),
    "humidity_pct": (SensorType.HUMIDITY, "percent"),
    "pressure_hpa": (SensorType.PRESSURE, "hpa"),
    "ambient_light_pct": (SensorType.LIGHT, "percent"),
    "water_level_pct": (SensorType.WATER_LEVEL, "percent"),
    "soil_moisture_pct": (SensorType.SOIL_MOISTURE, "percent"),
}


class HardwareAdapter:
    """Sensor + actuator adapter that talks to the Pi hardware API over HTTP.

    SensorPort interface:
        zone_ids, get_latest(zone_id), start(), stop(), subscribe(cb)

    ActuatorPort interface:
        send_command(ActuatorCommand) → bool
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        zone_id: str = "zone1",
        poll_interval: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._zone_id = zone_id
        self._poll_interval = poll_interval

        self._client = httpx.Client(base_url=self._base_url, timeout=10.0)
        self._zone_state: ZoneState | None = None
        self._raw_reading: dict | None = None  # full Pi reading for extra fields
        self._sensor_status: dict | None = None  # per-sensor ok/error
        self._lock = threading.Lock()
        self._subscribers: list[Callable[[SensorReading], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._consecutive_failures = 0

    # ── SensorPort interface ──────────────────────────────────────────

    @property
    def zone_ids(self) -> list[str]:
        with self._lock:
            if self._zone_state is not None:
                return [self._zone_id]
        return [self._zone_id]  # always report the zone even before first poll

    def get_latest(self, zone_id: str) -> ZoneState | None:
        if zone_id != self._zone_id:
            return None
        with self._lock:
            return self._zone_state

    def subscribe(self, callback: Callable[[SensorReading], None]) -> None:
        self._subscribers.append(callback)

    def start(self) -> None:
        """Start background polling thread."""
        if self._running:
            return
        # Do one immediate poll so zone_state is populated before reconciler starts
        self._poll_once()
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="hw-sensor-poll"
        )
        self._thread.start()
        logger.info(
            "hardware_adapter_started",
            base_url=self._base_url,
            zone_id=self._zone_id,
            poll_interval=self._poll_interval,
        )

    def stop(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._poll_interval * 2)
        self._thread = None
        self._client.close()

    # ── ActuatorPort interface ────────────────────────────────────────

    def send_command(self, command: ActuatorCommand) -> bool:
        """Translate an ActuatorCommand into an HTTP call to the Pi."""
        try:
            if command.device == DeviceType.LIGHT:
                return self._send_light(command)
            elif command.device == DeviceType.PUMP:
                return self._send_water(command)
            elif command.device == DeviceType.FAN:
                return self._send_fan(command)
            else:
                logger.warning(
                    "hardware_unsupported_device",
                    device=command.device.value,
                    action=command.action,
                )
                return False
        except Exception as e:
            logger.error("hardware_command_failed", device=command.device.value, error=str(e))
            return False

    # ── Extra: raw reading access for API/dashboard enrichment ────────

    def get_raw_reading(self) -> dict | None:
        """Return the full Pi reading dict (includes soil_moisture, ph, lux, etc.)."""
        with self._lock:
            return self._raw_reading

    def get_sensor_status(self) -> dict | None:
        """Return per-sensor ok/error status from the Pi."""
        with self._lock:
            return self._sensor_status

    # ── Chaos injection (pass-through for API compatibility) ──────────

    def inject_event(self, zone_id: str, event_type: str) -> None:
        """Hardware adapter doesn't support chaos injection — log and ignore."""
        logger.info(
            "hardware_chaos_ignored",
            zone_id=zone_id,
            event_type=event_type,
            reason="real hardware — chaos injection not supported",
        )

    # ── Internal: polling ─────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(self._poll_interval)
            self._poll_once()

    def _poll_once(self) -> None:
        """Fetch /sensors from the Pi and update local state."""
        try:
            resp = self._client.get("/sensors")
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self._consecutive_failures += 1
            if self._consecutive_failures <= 3 or self._consecutive_failures % 10 == 0:
                logger.warning(
                    "hardware_poll_failed",
                    error=str(e),
                    consecutive_failures=self._consecutive_failures,
                    url=f"{self._base_url}/sensors",
                )
            # Mark zone as dead after sustained failures
            if self._consecutive_failures >= 3:
                with self._lock:
                    if self._zone_state is not None:
                        self._zone_state.is_alive = False
            return

        if not data.get("ok"):
            logger.warning("hardware_api_not_ok", response=data)
            return

        self._consecutive_failures = 0
        reading = data.get("reading", {})
        sensors = data.get("sensors", {})
        now = time.time()

        # Build ZoneState from normalized Pi reading
        zone_state = ZoneState(
            zone_id=self._zone_id,
            temperature=_safe_float(reading.get("temperature_c")),
            humidity=_safe_float(reading.get("humidity_pct")),
            pressure=_safe_float(reading.get("pressure_hpa")),
            light=_safe_float(reading.get("ambient_light_pct")),
            water_level=_safe_float(reading.get("water_level_pct")),
            fire_detected=False,  # Pi has no fire sensor; would need camera CV
            last_updated=now,
            is_alive=True,
            source=f"hardware-{reading.get('temperature_source', 'pi')}",
        )

        with self._lock:
            self._zone_state = zone_state
            self._raw_reading = reading
            self._sensor_status = sensors

        # Build + fire SensorReading callbacks
        sensor_readings = self._extract_readings(reading, now)
        for cb in self._subscribers:
            for sr in sensor_readings:
                try:
                    cb(sr)
                except Exception as e:
                    logger.error("hardware_subscriber_error", error=str(e))

    def _extract_readings(self, reading: dict, timestamp: float) -> list[SensorReading]:
        """Convert Pi reading dict into SensorReading objects."""
        readings = []
        for field, (sensor_type, unit) in _READING_MAP.items():
            val = reading.get(field)
            if val is not None:
                source = reading.get(
                    f"{field.replace('_pct', '').replace('_c', '')}_source",
                    "pi-hardware",
                )
                readings.append(
                    SensorReading(
                        zone_id=self._zone_id,
                        sensor_type=sensor_type,
                        value=float(val),
                        unit=unit,
                        timestamp=timestamp,
                        source=source,
                    )
                )
        return readings

    # ── Internal: actuator HTTP calls ─────────────────────────────────

    def _send_light(self, cmd: ActuatorCommand) -> bool:
        """POST /light — control light relay."""
        action = cmd.action.lower()
        if action in ("on", "off", "toggle"):
            resp = self._client.post("/light", json={"action": action})
        elif action == "set":
            resp = self._client.post("/light", json={"on": cmd.value > 0})
        else:
            resp = self._client.post("/light", json={"action": action})
        resp.raise_for_status()
        result = resp.json()
        logger.info("hardware_light_command", action=action, result=result)
        return result.get("ok", False) or result.get("state_on") is not None

    def _send_water(self, cmd: ActuatorCommand) -> bool:
        """POST /water — pulse water pump."""
        duration_ms = int(cmd.value) if cmd.value > 0 else 1000
        resp = self._client.post("/water", json={"water_time": duration_ms})
        resp.raise_for_status()
        result = resp.json()
        logger.info("hardware_water_command", duration_ms=duration_ms, result=result)
        return result.get("ok", False)

    def _send_fan(self, cmd: ActuatorCommand) -> bool:
        """POST /control — fan via combined endpoint."""
        fan_on = cmd.action.lower() == "on" or cmd.value > 0
        resp = self._client.post("/control", json={"fan": fan_on})
        resp.raise_for_status()
        result = resp.json()
        logger.info("hardware_fan_command", fan_on=fan_on, result=result)
        return result.get("ok", False)


def _safe_float(val) -> float:
    """Convert a value to float, treating None as 0.0."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
