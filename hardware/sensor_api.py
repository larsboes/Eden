#!/usr/bin/env python3
"""FastAPI service exposing hardware sensor readings on localhost."""

from __future__ import annotations

import base64
import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI

from sensorlib.bmp280_reader import read_bmp280
from sensorlib.dht_reader import read_dht
from sensorlib.hl69_reader import read_hl69
from sensorlib.light_reader import read_light_level
from sensorlib.outside_light_reader import read_outside_light
from sensorlib.water_reader import read_water_level

app = FastAPI(title="Pi Sensor API", version="1.0.0")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_with_status(func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        data = func()
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover
        return {"status": "error", "error": str(exc)}


def capture_camera_base64() -> str:
    result = subprocess.run(
        [
            "rpicam-jpeg",
            "--nopreview",
            "--width",
            "1280",
            "--height",
            "720",
            "--quality",
            "90",
            "--timeout",
            "1",
            "-o",
            "-",
        ],
        check=True,
        capture_output=True,
    )
    return base64.b64encode(result.stdout).decode("ascii")


def run_relay_action(*, pin: int, action: str, active_low: bool) -> dict[str, Any]:
    cmd = [
        "python3",
        "/home/pi/relay_gpio26.py",
        action,
        "--pin",
        str(pin),
    ]
    if active_low:
        cmd.append("--active-low")
    else:
        cmd.append("--active-high")
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        raise RuntimeError(stderr or stdout or f"relay command failed ({result.returncode})")
    if not stdout:
        raise RuntimeError("relay command returned empty output")
    parsed = json.loads(stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("relay command returned invalid JSON payload")
    return parsed


def set_light_on(value: bool) -> dict[str, Any]:
    return run_relay_action(pin=26, action="on" if value else "off", active_low=True)


def toggle_light() -> dict[str, Any]:
    return run_relay_action(pin=26, action="toggle", active_low=True)


def get_light_status() -> dict[str, Any]:
    return run_relay_action(pin=26, action="status", active_low=True)


def pulse_water(duration_ms: int) -> dict[str, Any]:
    started = run_relay_action(pin=27, action="on", active_low=False)
    try:
        time.sleep(duration_ms / 1000.0)
    finally:
        ended = run_relay_action(pin=27, action="off", active_low=False)
    return {
        "ok": True,
        "pin": 27,
        "duration_ms": duration_ms,
        "active_low": False,
        "started_state_on": started.get("state_on"),
        "ended_state_on": ended.get("state_on"),
    }


def normalize_water_time(value: Any) -> int:
    default_ms = 1000
    min_ms = 50
    max_ms = 120000
    if not isinstance(value, (int, float)):
        return default_ms
    if isinstance(value, bool):
        return default_ms
    rounded = int(round(float(value)))
    return max(min_ms, min(max_ms, rounded))


def build_payload() -> dict[str, Any]:
    timestamp = now_iso()
    sensors = {
        "pressure": read_with_status(lambda: read_bmp280(address=0x76)),
        "temperature_humidity": read_with_status(lambda: read_dht(sensor="dht11", retries=3, delay_s=0.25)),
        "ambient_light": read_with_status(lambda: read_light_level(channel=3, address=0x48)),
        "outside_light": read_with_status(lambda: read_outside_light(channel=2, address=0x48)),
        "water_level": read_with_status(lambda: read_water_level(channel=0, address=0x48)),
        "soil_moisture": read_with_status(
            lambda: read_hl69(channel=1, address=0x48)
        ),
    }

    reading: dict[str, Any] = {
        "zone_id": "zone1",
        "timestamp": timestamp,
        "temperature_c": None,
        "temperature_source": None,
        "humidity_pct": None,
        "humidity_source": None,
        "pressure_hpa": None,
        "pressure_source": None,
        "ambient_light_pct": None,
        "outside_light_pct": None,
        "water_level_pct": None,
        "soil_moisture_pct": None,
        "light_raw": None,
        "light_voltage": None,
        "outside_light_raw": None,
        "outside_light_voltage": None,
        "water_raw": None,
        "water_voltage": None,
        "soil_raw": None,
        "soil_voltage": None,
        # Compatibility aliases used by control/UI rules:
        "light_lux": None,
        "water_level_cm": None,
        "ph": 6.0,
    }

    dht = sensors["temperature_humidity"]
    if dht["status"] == "ok":
        reading["temperature_c"] = dht["data"]["temperature_c"]
        reading["humidity_pct"] = dht["data"]["humidity_pct"]
        reading["temperature_source"] = "KY-015 (DHT11)"
        reading["humidity_source"] = "KY-015 (DHT11)"

    pressure = sensors["pressure"]
    if pressure["status"] == "ok":
        reading["pressure_hpa"] = pressure["data"]["pressure_hpa"]
        reading["pressure_source"] = "BMP280"
        # Temperature fallback only when DHT is unavailable.
        if reading["temperature_c"] is None:
            reading["temperature_c"] = pressure["data"]["temperature_c"]
            reading["temperature_source"] = "BMP280 (fallback)"

    ambient_light = sensors["ambient_light"]
    if ambient_light["status"] == "ok":
        reading["ambient_light_pct"] = ambient_light["data"]["level_pct"]
        reading["light_raw"] = ambient_light["data"]["raw"]
        reading["light_voltage"] = ambient_light["data"]["voltage"]

    outside_light = sensors["outside_light"]
    if outside_light["status"] == "ok":
        reading["outside_light_pct"] = outside_light["data"]["level_pct"]
        reading["outside_light_raw"] = outside_light["data"]["raw"]
        reading["outside_light_voltage"] = outside_light["data"]["voltage"]
        # Relay light switching uses this lux-like field.
        reading["light_lux"] = outside_light["data"]["lux"]
    elif ambient_light["status"] == "ok":
        # Fallback so light automation still works if KY-054 is unavailable.
        reading["light_lux"] = float(ambient_light["data"]["level_pct"]) * 10.0

    water = sensors["water_level"]
    if water["status"] == "ok":
        reading["water_level_pct"] = water["data"]["level_pct"]
        reading["water_raw"] = water["data"]["raw"]
        reading["water_voltage"] = water["data"]["voltage"]
        reading["water_level_cm"] = float(water["data"]["level_pct"]) / 10.0

    soil = sensors["soil_moisture"]
    if soil["status"] == "ok":
        reading["soil_moisture_pct"] = soil["data"]["moisture_pct"]
        reading["soil_raw"] = soil["data"]["raw"]
        reading["soil_voltage"] = soil["data"]["voltage"]

    return {
        "ok": True,
        "timestamp": timestamp,
        "reading": reading,
        "sensors": sensors,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    sensors = {
        "pressure": read_with_status(lambda: read_bmp280(address=0x76)),
        "temperature_humidity": read_with_status(lambda: read_dht(sensor="dht11", retries=1, delay_s=0.2)),
        "ambient_light": read_with_status(lambda: read_light_level(channel=3, address=0x48)),
        "outside_light": read_with_status(lambda: read_outside_light(channel=2, address=0x48)),
        "water_level": read_with_status(lambda: read_water_level(channel=0, address=0x48)),
        "soil_moisture": read_with_status(
            lambda: read_hl69(channel=1, address=0x48)
        ),
    }
    return {
        "ok": any(v["status"] == "ok" for v in sensors.values()),
        "service": "sensor-api",
        "timestamp": now_iso(),
        "sensors": sensors,
    }


@app.get("/sensors")
def sensors() -> dict[str, Any]:
    return build_payload()


@app.get("/camera")
def camera() -> dict[str, Any]:
    try:
        image_b64 = capture_camera_base64()
        return {
            "ok": True,
            "timestamp": now_iso(),
            "mime_type": "image/jpeg",
            "image_base64": image_b64,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "timestamp": now_iso(),
            "error": str(exc),
        }


@app.get("/light")
def light_status() -> dict[str, Any]:
    try:
        return get_light_status()
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


@app.post("/light")
def light_control(body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = body or {}
    try:
        if isinstance(payload.get("on"), bool):
            return set_light_on(bool(payload["on"]))

        action = payload.get("action")
        if action == "on":
            return set_light_on(True)
        if action == "off":
            return set_light_on(False)
        if action == "toggle":
            return toggle_light()
        if action == "status":
            return get_light_status()

        return {
            "ok": False,
            "error": "Provide {'on': boolean} or {'action': 'on'|'off'|'toggle'|'status'}",
        }
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


@app.post("/water")
def water_control(body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = body or {}
    try:
        duration_ms = normalize_water_time(payload.get("water_time"))
        return pulse_water(duration_ms)
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


@app.post("/control")
def control(body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = body or {}
    result: dict[str, Any] = {"ok": True}
    try:
        if isinstance(payload.get("leds"), bool):
            result["leds"] = set_light_on(bool(payload["leds"]))
        if payload.get("pump") is True:
            duration_ms = normalize_water_time(payload.get("water_time"))
            result["pump"] = pulse_water(duration_ms)
        if "leds" not in result and "pump" not in result:
            result["note"] = "No actuator field provided. Use leds:boolean and/or pump:true."
        return result
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}

