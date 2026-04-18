"""Tests for SimulatedSensors — fake sensor data publisher."""

import json
import time
import threading
from unittest.mock import MagicMock, call

import pytest

from eden.domain.models import SensorType


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_mqtt_client():
    """Mock paho MQTT client that captures published messages."""
    client = MagicMock()
    client.is_connected.return_value = True
    client.publish.return_value = MagicMock(rc=0)
    return client


@pytest.fixture
def simulator(mock_mqtt_client):
    from eden.adapters.simulated_sensors import SimulatedSensors

    return SimulatedSensors(
        mqtt_client=mock_mqtt_client,
        zones=["sim-alpha", "sim-beta", "sim-gamma"],
        interval=0.1,  # Fast for testing
    )


def _get_published_payloads(mock_mqtt_client, topic_filter: str = "telemetry") -> list[dict]:
    """Extract published JSON payloads matching a topic filter."""
    payloads = []
    for c in mock_mqtt_client.publish.call_args_list:
        topic = c[0][0]
        if topic_filter in topic:
            try:
                payloads.append(json.loads(c[0][1]))
            except (json.JSONDecodeError, IndexError):
                pass
    return payloads


# ── Telemetry Format ─────────────────────────────────────────────────────


class TestTelemetryFormat:
    def test_generates_valid_telemetry_json(self, simulator, mock_mqtt_client):
        """Published telemetry should match the MQTT contract schema."""
        from eden.adapters.simulated_sensors import SimulatedSensors

        # Generate one batch directly
        simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        assert len(payloads) == 3  # one per zone

        for payload in payloads:
            assert "zone_id" in payload
            assert "source" in payload
            assert "timestamp" in payload
            assert "sensors" in payload

            sensors = payload["sensors"]
            assert "temperature" in sensors
            assert "humidity" in sensors
            assert "pressure" in sensors
            assert "light" in sensors
            assert "water_level" in sensors
            assert "fire" in sensors

            for sensor_name, sensor_data in sensors.items():
                assert "value" in sensor_data
                assert "unit" in sensor_data

    def test_publishes_to_correct_topics(self, simulator, mock_mqtt_client):
        """Telemetry should be published to eden/{zone_id}/telemetry."""
        simulator._publish_telemetry()

        topics = [c[0][0] for c in mock_mqtt_client.publish.call_args_list]
        assert "eden/sim-alpha/telemetry" in topics
        assert "eden/sim-beta/telemetry" in topics
        assert "eden/sim-gamma/telemetry" in topics


# ── Value Ranges ─────────────────────────────────────────────────────────


class TestValueRanges:
    def test_temperature_in_realistic_range(self, simulator, mock_mqtt_client):
        """Temperature should be within Mars greenhouse range (~15-30°C)."""
        for _ in range(20):
            simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        for p in payloads:
            temp = p["sensors"]["temperature"]["value"]
            assert 5.0 <= temp <= 40.0, f"Temperature {temp} out of realistic range"

    def test_humidity_in_realistic_range(self, simulator, mock_mqtt_client):
        """Humidity should be within 20-100%."""
        for _ in range(20):
            simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        for p in payloads:
            hum = p["sensors"]["humidity"]["value"]
            assert 20.0 <= hum <= 100.0, f"Humidity {hum} out of range"

    def test_pressure_in_realistic_range(self, simulator, mock_mqtt_client):
        """Pressure should be around 1013 ± reasonable range."""
        for _ in range(20):
            simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        for p in payloads:
            press = p["sensors"]["pressure"]["value"]
            assert 980.0 <= press <= 1050.0, f"Pressure {press} out of range"

    def test_light_in_realistic_range(self, simulator, mock_mqtt_client):
        """Light should be 0-800 lux."""
        for _ in range(20):
            simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        for p in payloads:
            light = p["sensors"]["light"]["value"]
            assert 0.0 <= light <= 800.0, f"Light {light} out of range"

    def test_water_level_in_realistic_range(self, simulator, mock_mqtt_client):
        """Water level should be 20-100mm."""
        for _ in range(20):
            simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        for p in payloads:
            water = p["sensors"]["water_level"]["value"]
            assert 20.0 <= water <= 100.0, f"Water {water} out of range"


# ── Inject Events ────────────────────────────────────────────────────────


class TestInjectEvents:
    def test_spike_event_changes_values(self, simulator, mock_mqtt_client):
        """inject_event('spike') should produce abnormal sensor values."""
        simulator.inject_event("sim-alpha", "spike")
        simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        alpha_payloads = [p for p in payloads if p["zone_id"] == "sim-alpha"]
        assert len(alpha_payloads) == 1
        # Spike should push temperature high
        temp = alpha_payloads[0]["sensors"]["temperature"]["value"]
        assert temp > 30.0, f"Spike should push temperature high, got {temp}"

    def test_sensor_failure_event(self, simulator, mock_mqtt_client):
        """inject_event('sensor_failure') should set values to 0 or flag."""
        simulator.inject_event("sim-beta", "sensor_failure")
        simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        beta_payloads = [p for p in payloads if p["zone_id"] == "sim-beta"]
        assert len(beta_payloads) == 1
        # Sensor failure: values should be 0
        for sensor_name in ["temperature", "humidity", "pressure", "light", "water_level"]:
            assert beta_payloads[0]["sensors"][sensor_name]["value"] == 0.0

    def test_fire_event(self, simulator, mock_mqtt_client):
        """inject_event('fire') should set fire sensor to 1."""
        simulator.inject_event("sim-gamma", "fire")
        simulator._publish_telemetry()

        payloads = _get_published_payloads(mock_mqtt_client)
        gamma_payloads = [p for p in payloads if p["zone_id"] == "sim-gamma"]
        assert len(gamma_payloads) == 1
        assert gamma_payloads[0]["sensors"]["fire"]["value"] == 1

    def test_event_clears_after_one_publish(self, simulator, mock_mqtt_client):
        """Injected events should be one-shot — cleared after publishing."""
        simulator.inject_event("sim-alpha", "fire")
        simulator._publish_telemetry()
        mock_mqtt_client.publish.reset_mock()

        simulator._publish_telemetry()
        payloads = _get_published_payloads(mock_mqtt_client)
        alpha_payloads = [p for p in payloads if p["zone_id"] == "sim-alpha"]
        assert alpha_payloads[0]["sensors"]["fire"]["value"] == 0


# ── Heartbeat ────────────────────────────────────────────────────────────


class TestHeartbeat:
    def test_publishes_heartbeat(self, simulator, mock_mqtt_client):
        """Heartbeat should be published to eden/{zone_id}/heartbeat."""
        simulator._publish_heartbeats()

        topics = [c[0][0] for c in mock_mqtt_client.publish.call_args_list]
        assert "eden/sim-alpha/heartbeat" in topics
        assert "eden/sim-beta/heartbeat" in topics
        assert "eden/sim-gamma/heartbeat" in topics

    def test_heartbeat_format(self, simulator, mock_mqtt_client):
        """Heartbeat payload should have required fields."""
        simulator._publish_heartbeats()

        for c in mock_mqtt_client.publish.call_args_list:
            topic = c[0][0]
            if "heartbeat" in topic:
                payload = json.loads(c[0][1])
                assert "zone_id" in payload
                assert "source" in payload
                assert "uptime_seconds" in payload
                assert "timestamp" in payload


# ── Lifecycle ────────────────────────────────────────────────────────────


class TestLifecycle:
    def test_start_stop(self, simulator, mock_mqtt_client):
        """start() and stop() should manage the background thread."""
        simulator.start()
        assert simulator._running is True

        # Let it tick once
        time.sleep(0.25)

        simulator.stop()
        assert simulator._running is False

        # Should have published at least once
        assert mock_mqtt_client.publish.call_count > 0

    def test_stop_is_idempotent(self, simulator, mock_mqtt_client):
        """Calling stop() without start() should not crash."""
        simulator.stop()  # Should not raise

    def test_double_start_is_safe(self, simulator, mock_mqtt_client):
        """Calling start() twice should not create duplicate threads."""
        simulator.start()
        simulator.start()  # Should not create a second thread

        time.sleep(0.15)
        simulator.stop()
