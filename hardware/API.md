### Core Endpoints

#### `GET /health`

Purpose: quick liveness + dependency check.

Response shape:

```json
{
  "ok": true,
  "service": "sensor-api",
  "timestamp": "2026-03-20T00:00:00.000000+00:00",
  "sensors": {
    "pressure": { "status": "ok", "data": { "...": "..." } },
    "temperature_humidity": { "status": "ok|error", "data": { "...": "..." } },
    "ambient_light": { "status": "ok|error", "data": { "...": "..." } },
    "outside_light": { "status": "ok|error", "data": { "...": "..." } },
    "water_level": { "status": "ok|error", "data": { "...": "..." } },
    "soil_moisture": { "status": "ok|error", "data": { "...": "..." } }
  }
}
```

Notes:
- `ok` is true if at least one sensor is readable.
- Use this endpoint for startup/readiness checks.

#### `GET /sensors`

Purpose: primary telemetry payload for dashboard and agents.

Response shape:

```json
{
  "ok": true,
  "timestamp": "2026-03-20T00:00:00.000000+00:00",
  "reading": {
    "zone_id": "zone1",
    "timestamp": "2026-03-20T00:00:00.000000+00:00",
    "temperature_c": 22.5,
    "temperature_source": "KY-015 (DHT11)|BMP280 (fallback)",
    "humidity_pct": 40.0,
    "humidity_source": "KY-015 (DHT11)",
    "pressure_hpa": 944.7,
    "pressure_source": "BMP280",
    "ambient_light_pct": 51.0,
    "outside_light_pct": 27.7,
    "light_lux": 277.1,
    "water_level_pct": 19.4,
    "soil_moisture_pct": 1.2,
    "light_raw": 26366,
    "light_voltage": 1.616,
    "outside_light_raw": 12927,
    "outside_light_voltage": 0.762,
    "water_raw": 6095,
    "water_voltage": 0.000,
    "soil_raw": 1,
    "soil_voltage": 3.295,
    "water_level_cm": 1.9,
    "ph": 6.0
  },
  "sensors": {
    "pressure": { "status": "ok|error", "data": { "...": "..." } },
    "temperature_humidity": { "status": "ok|error", "error": "..." },
    "ambient_light": { "status": "ok|error", "data": { "...": "..." } },
    "outside_light": { "status": "ok|error", "data": { "...": "..." } },
    "water_level": { "status": "ok|error", "data": { "...": "..." } },
    "soil_moisture": { "status": "ok|error", "data": { "...": "..." } }
  }
}
```

Usage rules:
- Read **`reading`** for normalized values.
- Inspect **`sensors.*.status`** for per-sensor reliability.
- Treat `null` values as unavailable; do not coerce to zero in analytics pipelines.
- `light_lux` is derived from outside sunlight sensor (A2) and used for light automation decisions.

#### `GET /camera`

Purpose: request-time still image capture, base64 encoded.

Response shape:

```json
{
  "ok": true,
  "timestamp": "2026-03-20T00:00:00.000000+00:00",
  "mime_type": "image/jpeg",
  "image_base64": "<very_long_base64_string>"
}
```

Failure shape:

```json
{
  "ok": false,
  "timestamp": "2026-03-20T00:00:00.000000+00:00",
  "error": "..."
}
```

Notes:
- This captures a new frame per call (not a stream).
- Large payload; avoid high-frequency polling.

### Actuator Command Endpoints (Web API)

These actuator commands are exposed by the Next.js service (same host as dashboard), not by FastAPI.

- **Base URL (local dev)**: `http://127.0.0.1:3000`
- **Base URL (prod)**: your deployed web service host

#### `GET /api/light`

Purpose: read physical light relay status.

Response shape:

```json
{
  "ok": true,
  "pin": 26,
  "active_low": true,
  "action": "status",
  "state_on": false
}
```

#### `POST /api/light`

Purpose: control light relay (GPIO26).

Request options:
- `{ "on": true }` or `{ "on": false }`
- `{ "action": "on" | "off" | "toggle" | "status" }`

Example:

```bash
curl -sS -X POST http://127.0.0.1:3000/api/light \
  -H "Content-Type: application/json" \
  -d '{"action":"toggle"}'
```

#### `POST /api/water`

Purpose: pulse water pump relay (GPIO27 by default).

Request:
- No body -> default pulse `1000ms`
- Optional body -> `{ "water_time": <milliseconds> }`

Examples:

```bash
# Default 1 second
curl -sS -X POST http://127.0.0.1:3000/api/water

# Custom 1500 ms
curl -sS -X POST http://127.0.0.1:3000/api/water \
  -H "Content-Type: application/json" \
  -d '{"water_time":1500}'
```

Response shape:

```json
{
  "ok": true,
  "pin": 27,
  "duration_ms": 1000,
  "active_low": false,
  "started_state_on": true,
  "ended_state_on": false
}
```

#### `POST /api/control` (combined control endpoint)

Purpose: control relays from one endpoint.

Accepted fields:
- `fan: boolean`
- `leds: boolean` (light relay)
- `pump: boolean` (pulse action; if true, pulses water relay)
- `water_time: number` optional pulse duration in ms (used when `pump=true`)

Example:

```bash
curl -sS -X POST http://127.0.0.1:3000/api/control \
  -H "Content-Type: application/json" \
  -d '{"pump":true,"water_time":1200}'
```

### Actuator Command Endpoints (FastAPI, Python-Authoritative)

For hardware control in the AWS bridge path, use FastAPI endpoints directly.

- **Base URL**: `http://127.0.0.1:8001`

#### `GET /light`

Purpose: read physical light relay status (GPIO26, active-low).

#### `POST /light`

Purpose: control light relay from Python FastAPI.

Request options:
- `{ "on": true }` or `{ "on": false }`
- `{ "action": "on" | "off" | "toggle" | "status" }`

Example:

```bash
curl -sS -X POST http://127.0.0.1:8001/light \
  -H "Content-Type: application/json" \
  -d '{"action":"toggle"}'
```

#### `POST /water`

Purpose: pulse water pump relay (GPIO27, active-high).

Request:
- No body -> default pulse `1000ms`
- Optional body -> `{ "water_time": <milliseconds> }` clamped to `50..120000`

Example:

```bash
curl -sS -X POST http://127.0.0.1:8001/water \
  -H "Content-Type: application/json" \
  -d '{"water_time":1200}'
```

#### `POST /control`

Purpose: combined actuator endpoint used by the standalone AWS bridge.

Accepted fields:
- `leds: boolean` (light relay state)
- `pump: boolean` (if true, issue a pulse on GPIO27)
- `water_time: number` optional pulse duration in ms

Example:

```bash
curl -sS -X POST http://127.0.0.1:8001/control \
  -H "Content-Type: application/json" \
  -d '{"leds":true,"pump":true,"water_time":1500}'
```