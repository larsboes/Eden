# EDEN Pi Integration — MQTT Contract

Pi connects to a Mosquitto MQTT broker running on the EC2 habitat server.
It publishes sensor data and receives actuator commands from the EDEN agent.

## Connection

| Parameter | Value |
|-----------|-------|
| Broker host | `MQTT_BROKER` env var (default `localhost`) |
| Port | `1883` |
| Auth | None (local network) |
| Protocol | MQTT v5 (paho-mqtt 2.x) |

## Topics

| Topic | Direction | Interval | Description |
|-------|-----------|----------|-------------|
| `eden/{zone_id}/telemetry` | Pi → Agent | Every 10s | Full sensor batch |
| `eden/{zone_id}/command` | Agent → Pi | On demand | Actuator command |
| `eden/{zone_id}/heartbeat` | Pi → Agent | Every 5s | Liveness signal |
| `eden/{zone_id}/camera` | Pi → Agent | On demand | Base64-encoded JPEG frame |

The Pi uses `zone_id = "pi"` by default (configurable via `ZONE_ID` env var).

---

## JSON Schemas

### Telemetry (`eden/{zone_id}/telemetry`)

Published by the Pi every 10 seconds with a batch of all sensor readings.

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
| `zone_id` | string | Identifies the greenhouse zone |
| `source` | string | Device identifier (e.g. `rpi-01`) |
| `timestamp` | float | Unix epoch seconds |
| `sensors` | object | Keys match `SensorType` enum: `temperature`, `humidity`, `pressure`, `light`, `water_level`, `fire` |
| `sensors.*.value` | float | Sensor reading (`fire`: 0 = no fire, 1 = fire detected) |
| `sensors.*.unit` | string | One of: `celsius`, `percent`, `hpa`, `lux`, `mm`, `boolean` |

### Command (`eden/{zone_id}/command`)

Received by the Pi. Each message is one actuator command.

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
| `command_id` | string | Unique ID (e.g. `cmd-{uuid}`) |
| `zone_id` | string | Target zone |
| `device` | string | `fan`, `light`, `pump`, `heater`, `motor` |
| `action` | string | `on`, `off`, `set` |
| `value` | float | 0–100 (percentage / intensity) |
| `reason` | string | Human-readable explanation from agent |
| `priority` | string | `critical`, `high`, `medium`, `low`, `info` |
| `timestamp` | float | Unix epoch seconds |

### Heartbeat (`eden/{zone_id}/heartbeat`)

Published by the Pi every 5 seconds. If the agent doesn't receive a heartbeat
for 30+ seconds, the zone is marked as dead.

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
| `zone_id` | string | Zone identifier |
| `source` | string | Device identifier |
| `uptime_seconds` | int | Seconds since Pi boot |
| `timestamp` | float | Unix epoch seconds |

### Camera (`eden/{zone_id}/camera`)

Published on demand (e.g. every 60s or on agent request).

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

## Sensors

| Sensor | Hardware | SensorType | Unit | Typical Range |
|--------|----------|------------|------|---------------|
| Temperature | DHT22 | `temperature` | celsius | 0–50 |
| Humidity | DHT22 | `humidity` | percent | 20–90 |
| Air pressure | BMP280 | `pressure` | hpa | 900–1100 |
| Brightness | LDR / BH1750 | `light` | lux | 0–10000 |
| Water level | Ultrasonic (HC-SR04) | `water_level` | mm | 0–300 |
| Fire detection | Flame sensor | `fire` | boolean | 0 or 1 |
| Camera | Pi Camera Module | — | jpeg/base64 | — |

## Actuators

| Device | Hardware | DeviceType | Actions |
|--------|----------|------------|---------|
| Fan | DC fan via relay/PWM | `fan` | on/off/set (0–100%) |
| Grow light | LED strip via relay/PWM | `light` | on/off/set (0–100%) |
| Water pump | Peristaltic pump via relay | `pump` | on/off |
| Heater | Heating mat via relay | `heater` | on/off/set (0–100%) |
| Motor | Servo/stepper via GPIO | `motor` | on/off/set (angle/speed) |

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set broker address (defaults to localhost)
export MQTT_BROKER=<ec2-ip-or-hostname>

# 3. Optionally set zone ID (defaults to "pi")
export ZONE_ID=pi

# 4. Run the sensor publisher (publishes telemetry + heartbeat)
python publisher.py

# 5. In another terminal, run the command listener
python listener.py
```

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
