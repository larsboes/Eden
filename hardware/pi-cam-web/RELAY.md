# AstroFarm — RELAY

Coordination handoff for the team (Lars, PJ, Johannes, Bryan).  
Coordinator agent runs in the lead tmux window.

## Repo layout

- `app/` — Next.js dashboard (sensors, control, camera, Earth link)
- `app/api/` — sensors, control, telemetry, iot/publish, agent/suggestions (AWS dummy)
- `lib/` — mock sensors, control state, telemetry log, IoT/agent dummies
- `RELAY.md` — this file

## Handoff notes

- **AWS**: All cloud endpoints are dummies (telemetry logged to `.data/telemetry.jsonl`, agent returns canned suggestions). Replace with real IoT Core + Bedrock when ready.
- **Hardware**: Sensor values are mocked; wire DHT22, soil, BH1750, pH, HC-SR04 and switch to real reads.
- **Camera**: `/api/stream` uses `rpicam-vid`; enable camera in raspi-config if needed.
- **22-min latency**: Use "Simulate 22 min latency" + "Get suggestion" in the Earth link panel to demo Mars delay.
