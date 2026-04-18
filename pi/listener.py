"""EDEN Pi Command Listener.

Subscribes to MQTT for actuator commands and controls hardware.
Implements guardian behavior: safe defaults if disconnected for >30s.

Usage:
    export MQTT_BROKER=<broker-ip>   # default: localhost
    export ZONE_ID=pi                # default: pi
    python listener.py

Topics subscribed:
    eden/{zone_id}/command   — actuator commands from EDEN agent
"""

from __future__ import annotations

import json
import os
import time
import threading

import paho.mqtt.client as mqtt

# ── Configuration ────────────────────────────────────────────────────────

BROKER_HOST = os.environ.get("MQTT_BROKER", "localhost")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "1883"))
ZONE_ID = os.environ.get("ZONE_ID", "pi")

TOPIC_COMMAND = f"eden/{ZONE_ID}/command"

# Guardian: if no command received for this many seconds, activate safe defaults
GUARDIAN_TIMEOUT = 30

# Valid devices and actions (from domain models)
VALID_DEVICES = {"fan", "light", "pump", "heater", "motor"}
VALID_ACTIONS = {"on", "off", "set"}
VALID_PRIORITIES = {"critical", "high", "medium", "low", "info"}


# ── Actuator Stubs ───────────────────────────────────────────────────────
# Replace these with real GPIO / relay control for your hardware.


def set_fan(action: str, value: float):
    """Control fan via relay/PWM. Stub: prints action."""
    print(f"  [FAN] {action} value={value}%")


def set_light(action: str, value: float):
    """Control grow light via relay/PWM. Stub: prints action."""
    print(f"  [LIGHT] {action} value={value}%")


def set_pump(action: str, value: float):
    """Control water pump via relay. Stub: prints action."""
    print(f"  [PUMP] {action}")


def set_heater(action: str, value: float):
    """Control heater via relay/PWM. Stub: prints action."""
    print(f"  [HEATER] {action} value={value}%")


def set_motor(action: str, value: float):
    """Control motor via GPIO. Stub: prints action."""
    print(f"  [MOTOR] {action} value={value}")


DEVICE_HANDLERS = {
    "fan": set_fan,
    "light": set_light,
    "pump": set_pump,
    "heater": set_heater,
    "motor": set_motor,
}


# ── Command Processing ──────────────────────────────────────────────────

# Track when we last received a valid command
_last_command_time = time.time()
_lock = threading.Lock()


def handle_command(payload: dict):
    """Parse and execute an actuator command."""
    global _last_command_time

    device = payload.get("device")
    action = payload.get("action")
    value = payload.get("value", 0.0)
    reason = payload.get("reason", "")
    priority = payload.get("priority", "info")
    command_id = payload.get("command_id", "unknown")

    # Validate
    if device not in VALID_DEVICES:
        print(f"  [REJECT] Unknown device: {device}")
        return
    if action not in VALID_ACTIONS:
        print(f"  [REJECT] Unknown action: {action}")
        return

    print(f"[CMD {command_id}] {device}.{action}({value}) priority={priority}")
    if reason:
        print(f"  reason: {reason}")

    # Route to device handler
    handler = DEVICE_HANDLERS[device]
    handler(action, value)

    with _lock:
        _last_command_time = time.time()


def activate_safe_defaults():
    """Guardian behavior: turn off non-essential devices when disconnected.

    Essential (kept running):
        - heater: prevent frost kill (flight rule FR-T-001)
    Non-essential (turned off):
        - fan, light, pump, motor
    """
    print("[GUARDIAN] No commands for 30s — activating safe defaults")
    set_fan("off", 0)
    set_light("off", 0)
    set_pump("off", 0)
    set_motor("off", 0)
    # Heater stays in its current state to prevent frost kill


# ── MQTT Callbacks ───────────────────────────────────────────────────────


def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[CONNECTED] Broker {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_COMMAND, qos=1)
        print(f"[SUBSCRIBED] {TOPIC_COMMAND}")
    else:
        print(f"[CONNECT FAILED] reason_code={reason_code}")


def on_disconnect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    print(f"[DISCONNECTED] reason_code={reason_code}, will auto-reconnect")


def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[ERROR] Malformed message on {message.topic}: {e}")
        return

    handle_command(payload)


# ── Guardian Thread ──────────────────────────────────────────────────────


def guardian_loop():
    """Background thread: check if we've lost contact and activate safe defaults."""
    guardian_active = False

    while True:
        time.sleep(5)
        with _lock:
            elapsed = time.time() - _last_command_time

        if elapsed > GUARDIAN_TIMEOUT and not guardian_active:
            activate_safe_defaults()
            guardian_active = True
        elif elapsed <= GUARDIAN_TIMEOUT and guardian_active:
            print("[GUARDIAN] Commands resumed — exiting safe mode")
            guardian_active = False


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    global _last_command_time

    print(f"[EDEN Pi Listener] zone={ZONE_ID}")
    print(f"[BROKER] {BROKER_HOST}:{BROKER_PORT}")
    print(f"[GUARDIAN] Safe defaults activate after {GUARDIAN_TIMEOUT}s without commands")

    _last_command_time = time.time()

    # Start guardian watchdog
    guardian = threading.Thread(target=guardian_loop, daemon=True)
    guardian.start()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping listener...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
