"""Tests for pi/publisher.py — validates MQTT payloads and sensor stubs."""

from __future__ import annotations

import sys
import os

# Add pi/ to path so we can import publisher directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "pi"))

from publisher import (
    build_telemetry,
    build_heartbeat,
    read_temperature,
    read_humidity,
    read_pressure,
    read_light,
    read_water_level,
    read_fire,
)

# ── Expected sensor types (from domain models) ──────────────────────────

EXPECTED_SENSOR_KEYS = {"temperature", "humidity", "pressure", "light", "water_level", "fire"}

SENSOR_UNITS = {
    "temperature": "celsius",
    "humidity": "percent",
    "pressure": "hpa",
    "light": "lux",
    "water_level": "mm",
    "fire": "boolean",
}


# ── Telemetry Schema Tests ──────────────────────────────────────────────


def test_telemetry_has_required_fields():
    payload = build_telemetry()
    assert "zone_id" in payload
    assert "source" in payload
    assert "timestamp" in payload
    assert "sensors" in payload


def test_telemetry_zone_id_is_string():
    payload = build_telemetry()
    assert isinstance(payload["zone_id"], str)
    assert len(payload["zone_id"]) > 0


def test_telemetry_source_is_string():
    payload = build_telemetry()
    assert isinstance(payload["source"], str)
    assert len(payload["source"]) > 0


def test_telemetry_timestamp_is_float():
    payload = build_telemetry()
    assert isinstance(payload["timestamp"], float)
    assert payload["timestamp"] > 0


def test_telemetry_has_all_sensor_types():
    payload = build_telemetry()
    assert set(payload["sensors"].keys()) == EXPECTED_SENSOR_KEYS


def test_telemetry_sensor_values_have_value_and_unit():
    payload = build_telemetry()
    for sensor_type, reading in payload["sensors"].items():
        assert "value" in reading, f"{sensor_type} missing 'value'"
        assert "unit" in reading, f"{sensor_type} missing 'unit'"


def test_telemetry_sensor_units_match_contract():
    payload = build_telemetry()
    for sensor_type, expected_unit in SENSOR_UNITS.items():
        actual_unit = payload["sensors"][sensor_type]["unit"]
        assert actual_unit == expected_unit, (
            f"{sensor_type}: expected unit '{expected_unit}', got '{actual_unit}'"
        )


def test_telemetry_sensor_values_are_numeric():
    payload = build_telemetry()
    for sensor_type, reading in payload["sensors"].items():
        assert isinstance(reading["value"], (int, float)), (
            f"{sensor_type} value is not numeric: {reading['value']}"
        )


# ── Heartbeat Schema Tests ──────────────────────────────────────────────


def test_heartbeat_has_required_fields():
    payload = build_heartbeat()
    assert "zone_id" in payload
    assert "source" in payload
    assert "uptime_seconds" in payload
    assert "timestamp" in payload


def test_heartbeat_zone_id_is_string():
    payload = build_heartbeat()
    assert isinstance(payload["zone_id"], str)


def test_heartbeat_uptime_is_int():
    payload = build_heartbeat()
    assert isinstance(payload["uptime_seconds"], int)
    assert payload["uptime_seconds"] >= 0


def test_heartbeat_timestamp_is_float():
    payload = build_heartbeat()
    assert isinstance(payload["timestamp"], float)
    assert payload["timestamp"] > 0


# ── Sensor Stub Range Tests ─────────────────────────────────────────────


def test_temperature_in_valid_range():
    for _ in range(50):
        val = read_temperature()
        assert 0.0 <= val <= 50.0, f"Temperature out of range: {val}"


def test_humidity_in_valid_range():
    for _ in range(50):
        val = read_humidity()
        assert 0.0 <= val <= 100.0, f"Humidity out of range: {val}"


def test_pressure_in_valid_range():
    for _ in range(50):
        val = read_pressure()
        assert 900.0 <= val <= 1100.0, f"Pressure out of range: {val}"


def test_light_in_valid_range():
    for _ in range(50):
        val = read_light()
        assert 0.0 <= val <= 10000.0, f"Light out of range: {val}"


def test_water_level_in_valid_range():
    for _ in range(50):
        val = read_water_level()
        assert 0.0 <= val <= 300.0, f"Water level out of range: {val}"


def test_fire_is_binary():
    for _ in range(50):
        val = read_fire()
        assert val in (0, 1), f"Fire sensor not binary: {val}"
