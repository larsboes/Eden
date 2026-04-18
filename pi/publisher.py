"""EDEN Pi Sensor Publisher.

Reads sensor hardware and publishes telemetry + heartbeat to MQTT.

Usage:
    export MQTT_BROKER=<broker-ip>   # default: localhost
    export ZONE_ID=pi                # default: pi
    python publisher.py

Topics published:
    eden/{zone_id}/telemetry   — every 10s, full sensor batch
    eden/{zone_id}/heartbeat   — every 5s, liveness signal
"""

from __future__ import annotations

import json
import os
import time
import random
import threading

import paho.mqtt.client as mqtt

# ── Configuration ────────────────────────────────────────────────────────

BROKER_HOST = os.environ.get("MQTT_BROKER", "localhost")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "1883"))
ZONE_ID = os.environ.get("ZONE_ID", "pi")
SOURCE = os.environ.get("SOURCE_ID", "rpi-01")

TELEMETRY_INTERVAL = 10  # seconds
HEARTBEAT_INTERVAL = 5   # seconds

TOPIC_TELEMETRY = f"eden/{ZONE_ID}/telemetry"
TOPIC_HEARTBEAT = f"eden/{ZONE_ID}/heartbeat"


# ── Sensor Stubs ─────────────────────────────────────────────────────────
# Replace these with real GPIO / I2C reads for your hardware.


def read_temperature() -> float:
    """Read temperature in Celsius from DHT22. Stub: returns simulated value."""
    return round(random.uniform(18.0, 32.0), 1)


def read_humidity() -> float:
    """Read relative humidity (%) from DHT22. Stub: returns simulated value."""
    return round(random.uniform(40.0, 80.0), 1)


def read_pressure() -> float:
    """Read atmospheric pressure (hPa) from BMP280. Stub: returns simulated value."""
    return round(random.uniform(990.0, 1030.0), 2)


def read_light() -> float:
    """Read light level (lux) from BH1750 / LDR. Stub: returns simulated value."""
    return round(random.uniform(100.0, 2000.0), 1)


def read_water_level() -> float:
    """Read water level (mm) from ultrasonic sensor. Stub: returns simulated value."""
    return round(random.uniform(20.0, 200.0), 1)


def read_fire() -> int:
    """Read flame sensor. Stub: returns 0 (no fire) most of the time."""
    return 1 if random.random() < 0.005 else 0


# ── Payload Builders ─────────────────────────────────────────────────────


def build_telemetry() -> dict:
    """Build a telemetry payload from all sensors."""
    return {
        "zone_id": ZONE_ID,
        "source": SOURCE,
        "timestamp": time.time(),
        "sensors": {
            "temperature": {"value": read_temperature(), "unit": "celsius"},
            "humidity": {"value": read_humidity(), "unit": "percent"},
            "pressure": {"value": read_pressure(), "unit": "hpa"},
            "light": {"value": read_light(), "unit": "lux"},
            "water_level": {"value": read_water_level(), "unit": "mm"},
            "fire": {"value": read_fire(), "unit": "boolean"},
        },
    }


_boot_time = time.time()


def build_heartbeat() -> dict:
    """Build a heartbeat payload."""
    return {
        "zone_id": ZONE_ID,
        "source": SOURCE,
        "uptime_seconds": int(time.time() - _boot_time),
        "timestamp": time.time(),
    }


# ── MQTT Client ──────────────────────────────────────────────────────────


def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[CONNECTED] Broker {BROKER_HOST}:{BROKER_PORT}")
    else:
        print(f"[CONNECT FAILED] reason_code={reason_code}")


def on_disconnect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    print(f"[DISCONNECTED] reason_code={reason_code}, will auto-reconnect")


def publish_loop(client: mqtt.Client):
    """Main loop: publish telemetry every 10s, heartbeat every 5s."""
    last_telemetry = 0.0
    last_heartbeat = 0.0

    print(f"[PUBLISHING] telemetry → {TOPIC_TELEMETRY} (every {TELEMETRY_INTERVAL}s)")
    print(f"[PUBLISHING] heartbeat → {TOPIC_HEARTBEAT} (every {HEARTBEAT_INTERVAL}s)")

    while True:
        now = time.time()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            payload = build_heartbeat()
            client.publish(TOPIC_HEARTBEAT, json.dumps(payload), qos=1)
            last_heartbeat = now

        if now - last_telemetry >= TELEMETRY_INTERVAL:
            payload = build_telemetry()
            client.publish(TOPIC_TELEMETRY, json.dumps(payload), qos=1)
            print(f"[TELEMETRY] temp={payload['sensors']['temperature']['value']}°C "
                  f"humidity={payload['sensors']['humidity']['value']}% "
                  f"fire={payload['sensors']['fire']['value']}")
            last_telemetry = now

        time.sleep(0.5)


def main():
    print(f"[EDEN Pi Publisher] zone={ZONE_ID} source={SOURCE}")
    print(f"[BROKER] {BROKER_HOST}:{BROKER_PORT}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    try:
        publish_loop(client)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping publisher...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
