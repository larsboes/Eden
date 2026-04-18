"""Tests for MqttAdapter — SensorPort + ActuatorPort implementation."""

import json
import threading
import time
from unittest.mock import MagicMock, patch, call

import pytest

from eden.domain.models import (
    ActuatorCommand,
    DeviceType,
    SensorReading,
    SensorType,
    Severity,
    ZoneState,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_mqtt_client():
    """Create a mock paho MQTT client."""
    with patch("eden.adapters.mqtt_adapter.mqtt.Client") as MockClient:
        client = MockClient.return_value
        client.is_connected.return_value = True
        client.connect.return_value = 0
        client.subscribe.return_value = (0, 1)
        client.publish.return_value = MagicMock(rc=0)
        client.loop_start.return_value = None
        client.loop_stop.return_value = None
        client.disconnect.return_value = None
        yield client


@pytest.fixture
def adapter(mock_mqtt_client):
    from eden.adapters.mqtt_adapter import MqttAdapter

    return MqttAdapter(broker_host="localhost", broker_port=1883, client_id="test")


def _make_telemetry_payload(zone_id: str = "pi", source: str = "rpi-01") -> dict:
    return {
        "zone_id": zone_id,
        "source": source,
        "timestamp": 1710812345.123,
        "sensors": {
            "temperature": {"value": 23.5, "unit": "celsius"},
            "humidity": {"value": 65.2, "unit": "percent"},
            "pressure": {"value": 1013.25, "unit": "hpa"},
            "light": {"value": 450.0, "unit": "lux"},
            "water_level": {"value": 85.0, "unit": "mm"},
            "fire": {"value": 0, "unit": "boolean"},
        },
    }


def _make_mqtt_message(topic: str, payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.topic = topic
    msg.payload = json.dumps(payload).encode("utf-8")
    return msg


# ── Telemetry Parsing ────────────────────────────────────────────────────


class TestTelemetryParsing:
    def test_valid_telemetry_updates_zone_state(self, adapter, mock_mqtt_client):
        """Valid telemetry JSON should update the in-memory zone state dict."""
        payload = _make_telemetry_payload("zone-a")
        msg = _make_mqtt_message("eden/zone-a/telemetry", payload)

        adapter._on_message(mock_mqtt_client, None, msg)

        state = adapter.get_latest("zone-a")
        assert state is not None
        assert isinstance(state, ZoneState)
        assert state.zone_id == "zone-a"
        assert state.temperature == 23.5
        assert state.humidity == 65.2
        assert state.pressure == 1013.25
        assert state.light == 450.0
        assert state.water_level == 85.0
        assert state.fire_detected is False
        assert state.source == "rpi-01"
        assert state.is_alive is True

    def test_fire_detected_flag(self, adapter, mock_mqtt_client):
        """Fire sensor value > 0 should set fire_detected=True."""
        payload = _make_telemetry_payload()
        payload["sensors"]["fire"]["value"] = 1
        msg = _make_mqtt_message("eden/pi/telemetry", payload)

        adapter._on_message(mock_mqtt_client, None, msg)

        state = adapter.get_latest("pi")
        assert state.fire_detected is True

    def test_multiple_zones_tracked_separately(self, adapter, mock_mqtt_client):
        """Each zone_id should have its own ZoneState entry."""
        for zone in ["alpha", "beta", "gamma"]:
            payload = _make_telemetry_payload(zone)
            payload["sensors"]["temperature"]["value"] = {"alpha": 20, "beta": 25, "gamma": 30}[zone]
            msg = _make_mqtt_message(f"eden/{zone}/telemetry", payload)
            adapter._on_message(mock_mqtt_client, None, msg)

        assert adapter.get_latest("alpha").temperature == 20
        assert adapter.get_latest("beta").temperature == 25
        assert adapter.get_latest("gamma").temperature == 30


# ── Invalid / Malformed Messages ─────────────────────────────────────────


class TestMalformedMessages:
    def test_invalid_json_is_dropped(self, adapter, mock_mqtt_client):
        """Malformed JSON should be dropped without crashing."""
        msg = MagicMock()
        msg.topic = "eden/pi/telemetry"
        msg.payload = b"not json at all {{"

        adapter._on_message(mock_mqtt_client, None, msg)

        assert adapter.get_latest("pi") is None

    def test_missing_sensors_key_is_dropped(self, adapter, mock_mqtt_client):
        """Payload without 'sensors' key should be dropped."""
        payload = {"zone_id": "pi", "source": "rpi-01", "timestamp": 123.0}
        msg = _make_mqtt_message("eden/pi/telemetry", payload)

        adapter._on_message(mock_mqtt_client, None, msg)

        assert adapter.get_latest("pi") is None

    def test_missing_sensor_field_uses_default(self, adapter, mock_mqtt_client):
        """Missing individual sensor should default to 0.0."""
        payload = {
            "zone_id": "pi",
            "source": "rpi-01",
            "timestamp": 123.0,
            "sensors": {
                "temperature": {"value": 22.0, "unit": "celsius"},
                # humidity missing
            },
        }
        msg = _make_mqtt_message("eden/pi/telemetry", payload)

        adapter._on_message(mock_mqtt_client, None, msg)

        state = adapter.get_latest("pi")
        assert state is not None
        assert state.temperature == 22.0
        assert state.humidity == 0.0

    def test_empty_payload_is_dropped(self, adapter, mock_mqtt_client):
        """Empty payload should be dropped."""
        msg = MagicMock()
        msg.topic = "eden/pi/telemetry"
        msg.payload = b""

        adapter._on_message(mock_mqtt_client, None, msg)

        assert adapter.get_latest("pi") is None


# ── get_latest ───────────────────────────────────────────────────────────


class TestGetLatest:
    def test_returns_none_for_unknown_zone(self, adapter):
        """get_latest should return None for zones we haven't seen."""
        assert adapter.get_latest("nonexistent") is None

    def test_returns_most_recent_state(self, adapter, mock_mqtt_client):
        """get_latest should return the most recently received state."""
        payload1 = _make_telemetry_payload("pi")
        payload1["sensors"]["temperature"]["value"] = 20.0
        payload1["timestamp"] = 100.0
        msg1 = _make_mqtt_message("eden/pi/telemetry", payload1)
        adapter._on_message(mock_mqtt_client, None, msg1)

        payload2 = _make_telemetry_payload("pi")
        payload2["sensors"]["temperature"]["value"] = 30.0
        payload2["timestamp"] = 200.0
        msg2 = _make_mqtt_message("eden/pi/telemetry", payload2)
        adapter._on_message(mock_mqtt_client, None, msg2)

        state = adapter.get_latest("pi")
        assert state.temperature == 30.0


# ── send_command ─────────────────────────────────────────────────────────


class TestSendCommand:
    def test_publishes_correct_json(self, adapter, mock_mqtt_client):
        """send_command should publish correctly formatted JSON to the right topic."""
        cmd = ActuatorCommand(
            command_id="cmd-abc",
            zone_id="pi",
            device=DeviceType.FAN,
            action="on",
            value=75.0,
            reason="Temp above target",
            priority=Severity.MEDIUM,
            timestamp=1710812350.456,
        )

        result = adapter.send_command(cmd)

        assert result is True
        mock_mqtt_client.publish.assert_called_once()
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "eden/pi/command"

        published = json.loads(call_args[0][1])
        assert published["command_id"] == "cmd-abc"
        assert published["zone_id"] == "pi"
        assert published["device"] == "fan"
        assert published["action"] == "on"
        assert published["value"] == 75.0
        assert published["priority"] == "medium"

    def test_send_command_returns_false_on_failure(self, adapter, mock_mqtt_client):
        """send_command should return False if publish fails."""
        mock_mqtt_client.publish.return_value = MagicMock(rc=1)

        cmd = ActuatorCommand(
            command_id="cmd-fail",
            zone_id="pi",
            device=DeviceType.PUMP,
            action="off",
            value=0.0,
            reason="test",
            priority=Severity.LOW,
            timestamp=123.0,
        )

        result = adapter.send_command(cmd)
        assert result is False


# ── Subscriber Callbacks ─────────────────────────────────────────────────


class TestSubscribeCallbacks:
    def test_callback_fires_on_new_reading(self, adapter, mock_mqtt_client):
        """Registered callbacks should fire with SensorReading objects on new telemetry."""
        received = []
        adapter.subscribe(lambda reading: received.append(reading))

        payload = _make_telemetry_payload("pi")
        msg = _make_mqtt_message("eden/pi/telemetry", payload)
        adapter._on_message(mock_mqtt_client, None, msg)

        assert len(received) > 0
        assert all(isinstance(r, SensorReading) for r in received)

    def test_multiple_callbacks_all_fire(self, adapter, mock_mqtt_client):
        """Multiple subscribers should all receive readings."""
        received_a = []
        received_b = []
        adapter.subscribe(lambda r: received_a.append(r))
        adapter.subscribe(lambda r: received_b.append(r))

        payload = _make_telemetry_payload("pi")
        msg = _make_mqtt_message("eden/pi/telemetry", payload)
        adapter._on_message(mock_mqtt_client, None, msg)

        assert len(received_a) > 0
        assert len(received_b) > 0

    def test_callback_exception_does_not_crash(self, adapter, mock_mqtt_client):
        """A failing callback should not crash the message handler."""

        def bad_callback(reading):
            raise RuntimeError("callback exploded")

        adapter.subscribe(bad_callback)

        payload = _make_telemetry_payload("pi")
        msg = _make_mqtt_message("eden/pi/telemetry", payload)

        # Should not raise
        adapter._on_message(mock_mqtt_client, None, msg)

        # Zone state should still be updated
        assert adapter.get_latest("pi") is not None


# ── Thread Safety ────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_writes_dont_corrupt_state(self, adapter, mock_mqtt_client):
        """Concurrent telemetry updates should not corrupt the zone state dict."""
        errors = []

        def writer(zone_id: str, n: int):
            try:
                for i in range(n):
                    payload = _make_telemetry_payload(zone_id)
                    payload["sensors"]["temperature"]["value"] = float(i)
                    payload["timestamp"] = float(i)
                    msg = _make_mqtt_message(f"eden/{zone_id}/telemetry", payload)
                    adapter._on_message(mock_mqtt_client, None, msg)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(f"zone-{i}", 50))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All 5 zones should exist
        for i in range(5):
            assert adapter.get_latest(f"zone-{i}") is not None


# ── Heartbeat ────────────────────────────────────────────────────────────


class TestHeartbeat:
    def test_heartbeat_updates_is_alive(self, adapter, mock_mqtt_client):
        """Heartbeat messages should mark the zone as alive."""
        # First add a zone via telemetry
        payload = _make_telemetry_payload("pi")
        msg = _make_mqtt_message("eden/pi/telemetry", payload)
        adapter._on_message(mock_mqtt_client, None, msg)

        # Then send heartbeat
        hb = {"zone_id": "pi", "source": "rpi-01", "uptime_seconds": 3600, "timestamp": 9999.0}
        msg = _make_mqtt_message("eden/pi/heartbeat", hb)
        adapter._on_message(mock_mqtt_client, None, msg)

        state = adapter.get_latest("pi")
        assert state.is_alive is True


# ── Lifecycle ────────────────────────────────────────────────────────────


class TestLifecycle:
    def test_start_connects_and_subscribes(self, adapter, mock_mqtt_client):
        """start() should connect to the broker and subscribe to topics."""
        adapter.start()

        mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
        mock_mqtt_client.loop_start.assert_called_once()

        # Simulate broker calling back on_connect (subscriptions happen there)
        adapter._on_connect(mock_mqtt_client, None, {}, 0, None)
        assert mock_mqtt_client.subscribe.call_count >= 2  # telemetry + heartbeat

    def test_stop_disconnects(self, adapter, mock_mqtt_client):
        """stop() should disconnect from the broker."""
        adapter.start()
        adapter.stop()

        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
