# Demo Scenario Data

## Files

| File | Purpose |
|------|---------|
| `demo-script.json` | Full 6-phase state machine for the 3-minute demo (NOMINAL → DETECTION → STOCKPILING → IMPACT → RECOVERY → MIRROR). Each phase has: dashboard state, system values, agent log entries, physical prop commands, background tint colors. |
| `demo-cme-event.json` | The actual NASA DONKI CME event used in the demo: `2026-01-24T09:23:00-CME-001`, speed 1,243 km/s, ETA 50.7h. Real data, real instruments (SOHO LASCO, STEREO A). |

## Usage

### Live mode
Dashboard consumes real-time data from agent/DynamoDB. Demo-script serves as the orchestration guide — what to trigger and when.

### Replay mode
Set `REPLAY_MODE=true`. Dashboard reads phases from `demo-script.json` sequentially. Agent log entries scroll in with timing. State transitions happen on a timer matching the demo pace. From the audience, looks identical to live.

## Demo Timeline

| Time | Phase | Key Moment |
|------|-------|------------|
| 0:00-0:30 | NOMINAL | "4 astronauts. 450 days. They can't bring a farmer. So we built one." |
| 0:30-1:00 | DETECTION | CME alert. Council convenes. ORACLE: Strategy C = 3% loss. |
| 1:00-1:30 | STOCKPILING | Water gauge climbing. Battery charging. "We have 50 hours." |
| 1:30-2:00 | IMPACT | Solar drops. LEDs dim. Fan stops. Triage with human cost. |
| 2:00-2:15 | RECOVERY | Solar returns. "Predicted 3% loss. Actual 2.7%." New flight rule proposed. |
| 2:15-3:00 | MIRROR | "Swap dust storm for drought. Same architecture. EDEN is ready now." |
