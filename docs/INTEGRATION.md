# EDEN Pi Integration Guide

Connect your Raspberry Pi sensors and actuators to the EDEN Martian greenhouse agent via MQTT.

---

## Connection

| Parameter | Value |
|-----------|-------|
| Broker | Mosquitto on EC2 |
| Host | `MQTT_BROKER` env var (EC2 public IP) |
| Port | `1883` |
| Auth | None (local network) |
| Protocol | MQTT v5 (`paho-mqtt` 2.x) |

```python
import paho.mqtt.client as mqtt

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="rpi-01",
)
client.connect(os.environ["MQTT_BROKER"], 1883, keepalive=60)
client.loop_start()
```

Your zone ID defaults to `"pi"` — configurable via `ZONE_ID` env var.

---

## What to Publish

### Telemetry — `eden/{zone_id}/telemetry`

Publish a full sensor batch **every 10 seconds**.

```json
{
  "zone_id": "pi",
  "source": "rpi-01",
  "timestamp": 1710812345.123,
  "sensors": {
    "temperature": { "value": 23.5, "unit": "celsius" },
    "humidity":    { "value": 65.2, "unit": "percent" },
    "pressure":    { "value": 1013.25, "unit": "hpa" },
    "light":       { "value": 450.0, "unit": "lux" },
    "water_level": { "value": 85.0, "unit": "mm" },
    "fire":        { "value": 0, "unit": "boolean" }
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `zone_id` | string | Your zone (default `"pi"`) |
| `source` | string | Device ID (e.g. `"rpi-01"`) |
| `timestamp` | float | Unix epoch seconds (`time.time()`) |
| `sensors` | object | Keys must match `SensorType` enum exactly |
| `sensors.*.value` | float | Sensor reading. `fire`: 0 = no fire, 1 = fire detected |
| `sensors.*.unit` | string | One of: `celsius`, `percent`, `hpa`, `lux`, `mm`, `boolean` |

### Heartbeat — `eden/{zone_id}/heartbeat`

Publish a liveness signal **every 5 seconds**.

```json
{
  "zone_id": "pi",
  "source": "rpi-01",
  "uptime_seconds": 3600,
  "timestamp": 1710812345.123
}
```

| Field | Type | Notes |
|-------|------|-------|
| `zone_id` | string | Your zone |
| `source` | string | Device ID |
| `uptime_seconds` | int | Seconds since Pi boot |
| `timestamp` | float | Unix epoch seconds |

If the agent doesn't receive a heartbeat for **30+ seconds**, the zone is marked as **dead**.

### Camera — `eden/{zone_id}/camera`

Publish on demand (e.g. every 60s or on agent request).

```json
{
  "zone_id": "pi",
  "source": "rpi-01",
  "timestamp": 1710812345.123,
  "format": "jpeg",
  "encoding": "base64",
  "data": "/9j/4AAQSkZJRg..."
}
```

---

## What to Subscribe To

### Commands — `eden/{zone_id}/command`

Subscribe to `eden/pi/command` (or your zone ID). The EDEN agent publishes actuator commands here.

```json
{
  "command_id": "cmd-a1b2c3",
  "zone_id": "pi",
  "device": "fan",
  "action": "on",
  "value": 75.0,
  "reason": "Temperature above target",
  "priority": "medium",
  "timestamp": 1710812350.456
}
```

| Field | Type | Valid values |
|-------|------|-------------|
| `command_id` | string | Unique ID (`cmd-{uuid}`) |
| `zone_id` | string | Target zone |
| `device` | string | `fan`, `light`, `pump`, `heater`, `motor` |
| `action` | string | `on`, `off`, `set` |
| `value` | float | 0–100 (percentage / intensity) |
| `reason` | string | Human-readable explanation from agent |
| `priority` | string | `critical`, `high`, `medium`, `low`, `info` |
| `timestamp` | float | Unix epoch seconds |

### Routing Commands to Hardware

```python
def handle_command(payload):
    device = payload["device"]
    action = payload["action"]
    value  = payload["value"]

    if device == "fan":
        if action == "on":  set_fan_pwm(value)
        elif action == "off": set_fan_pwm(0)
    elif device == "pump":
        if action == "on":  relay_on(PUMP_PIN)
        elif action == "off": relay_off(PUMP_PIN)
    elif device == "heater":
        if action == "on":  relay_on(HEATER_PIN)
        elif action == "off": relay_off(HEATER_PIN)
    elif device == "light":
        if action == "set": set_led_brightness(value)
        elif action == "off": set_led_brightness(0)
    elif device == "motor":
        if action == "set": set_servo_angle(value)
        elif action == "off": set_servo_angle(0)
```

---

## Sensor Mapping

Map your hardware to the EDEN `SensorType` enum:

| Sensor | Hardware | SensorType | Unit | Typical Range |
|--------|----------|------------|------|---------------|
| Temperature | DHT22 | `temperature` | `celsius` | 0–50 |
| Humidity | DHT22 | `humidity` | `percent` | 20–90 |
| Air pressure | BMP280 | `pressure` | `hpa` | 900–1100 |
| Brightness | LDR / BH1750 | `light` | `lux` | 0–10000 |
| Water level | Ultrasonic (HC-SR04) | `water_level` | `mm` | 0–300 |
| Fire detection | Flame sensor | `fire` | `boolean` | 0 or 1 |
| Camera | Pi Camera Module | — (separate topic) | jpeg/base64 | — |

**Actuators:**

| Device | Hardware | DeviceType | Actions |
|--------|----------|------------|---------|
| Fan | DC fan via relay/PWM | `fan` | on/off/set (0–100%) |
| Grow light | LED strip via relay/PWM | `light` | on/off/set (0–100%) |
| Water pump | Peristaltic pump via relay | `pump` | on/off |
| Heater | Heating mat via relay | `heater` | on/off/set (0–100%) |
| Motor | Servo/stepper via GPIO | `motor` | on/off/set (angle/speed) |

---

## Quick Start

```bash
cd pi/

# 1. Install dependencies
pip install -r requirements.txt

# 2. Set broker address
export MQTT_BROKER=<EC2_IP>

# 3. Optionally set zone ID (defaults to "pi")
export ZONE_ID=pi

# 4. Run the sensor publisher (telemetry + heartbeat)
python publisher.py

# 5. In another terminal, run the command listener
python listener.py
```

---

## Testing Without Hardware

Set `EDEN_SIMULATE=true` on the EDEN server (this is the default). The server will publish simulated sensor data to all zones, so you can:

1. Test your `listener.py` against simulated commands without any real sensors
2. Verify your command routing logic works
3. See the full agent parliament react to fake data

```bash
# On the server
export EDEN_SIMULATE=true
python -m eden
```

Johannes can point `listener.py` at the simulated broker and receive real agent commands to test actuator routing.

---

## Guardian Behavior (Offline Safety)

If your Pi loses connection to the EDEN agent (no commands received for 30 seconds):

1. **Turn off** non-essential devices (fan, pump, motor, light)
2. **Keep heater on** — frost protection is critical on Mars
3. **Log the disconnect** — timestamp + last known state

```python
import time

last_command_time = time.time()

def on_command(payload):
    global last_command_time
    last_command_time = time.time()
    handle_command(payload)

def guardian_check():
    """Call this in your main loop."""
    if time.time() - last_command_time > 30:
        relay_off(FAN_PIN)
        relay_off(PUMP_PIN)
        relay_off(MOTOR_PIN)
        # Keep heater ON — frost kills plants
        logging.warning("No commands for 30s — guardian mode active, heater kept on")
```

---

## Architecture

```
┌──────────────────┐       MQTT (1883)       ┌──────────────────┐
│   Raspberry Pi   │ ◄─────────────────────► │   EC2 (Mosquitto)│
│                  │                          │                  │
│  publisher.py    │──► eden/pi/telemetry ──►│  mqtt_adapter.py │
│  publisher.py    │──► eden/pi/heartbeat ──►│  (EDEN agent)    │
│  listener.py     │◄── eden/pi/command  ◄───│                  │
└──────────────────┘                          └──────────────────┘
```

The Pi is a **Zone** (like a Kubernetes Node). Each plant is a **Pod**. The EDEN agent is the **Controller** that reconciles actual vs desired state every 30 seconds.
