"""In-memory sensor adapter — produces zone data without MQTT.

Holds 4 zones matching the dashboard's PROTEIN/CARB/VITAMIN/SUPPORT layout.
Drifts values realistically so the reconciler has data to work with.
Supports chaos injection to trigger flight rules + parliament.
"""

from __future__ import annotations

import random
import time

import structlog

from eden.domain.models import ZoneState

logger = structlog.get_logger(__name__)

# Zone configs matching dashboard mock data
_ZONE_CONFIGS = {
    "zone-protein": {"temp": 22.3, "humidity": 63.0, "light": 400.0, "pressure": 1013.0, "water": 72.0},
    "zone-carb": {"temp": 20.1, "humidity": 58.0, "light": 380.0, "pressure": 1013.0, "water": 68.0},
    "zone-vitamin": {"temp": 23.8, "humidity": 42.0, "light": 450.0, "pressure": 1013.0, "water": 75.0},
    "zone-support": {"temp": 21.5, "humidity": 68.0, "light": 320.0, "pressure": 1013.0, "water": 70.0},
}

_DRIFT = {"temp": 1.5, "humidity": 5.0, "light": 50.0, "pressure": 2.0, "water": 5.0}


class MemorySensorAdapter:
    """Sensor adapter that keeps zone states in memory with realistic drift."""

    def __init__(self) -> None:
        self._zones: dict[str, dict[str, float]] = {}
        self._fire_zones: set[str] = set()
        self._dead_zones: set[str] = set()
        for zone_id, base in _ZONE_CONFIGS.items():
            self._zones[zone_id] = dict(base)

    @property
    def zone_ids(self) -> list[str]:
        return list(self._zones.keys())

    def get_latest(self, zone_id: str) -> ZoneState | None:
        state = self._zones.get(zone_id)
        if state is None:
            return None

        # Apply drift (small random walk) — only clamp to base range if NOT in chaos
        base = _ZONE_CONFIGS[zone_id]
        in_chaos = (
            zone_id in self._fire_zones
            or zone_id in self._dead_zones
            or any(abs(state[k] - base[k]) > _DRIFT[k] * 2 for k in _DRIFT)
        )
        for key, drift in _DRIFT.items():
            state[key] += random.gauss(0, drift * 0.05)
            if not in_chaos:
                state[key] = max(base[key] - drift, min(base[key] + drift, state[key]))

        return ZoneState(
            zone_id=zone_id,
            temperature=round(state["temp"], 1),
            humidity=round(max(0, state["humidity"]), 1),
            pressure=round(state["pressure"], 1),
            light=round(max(0, state["light"]), 1),
            water_level=round(max(0, state["water"]), 1),
            fire_detected=zone_id in self._fire_zones,
            last_updated=time.time(),
            is_alive=zone_id not in self._dead_zones,
            source="memory-sim",
        )

    def inject_event(self, zone_id: str, event_type: str) -> None:
        """Push a zone's values out of range to trigger flight rules + parliament."""
        logger.info("chaos_event_injected", zone_id=zone_id or "all", event_type=event_type)
        # dust_storm affects ALL zones
        if event_type == "dust_storm":
            for zid, st in self._zones.items():
                b = _ZONE_CONFIGS[zid]
                st["light"] = b["light"] * 0.15          # 85% light loss
                st["temp"] = b["temp"] - 8.0              # severe cooling
                st["humidity"] = b["humidity"] + 20.0     # condensation
            return

        state = self._zones.get(zone_id)
        if state is None:
            return
        base = _ZONE_CONFIGS[zone_id]

        if event_type == "fire":
            state["temp"] = 42.0                          # way above FR-T-002 (>35°C)
            state["humidity"] = max(10.0, base["humidity"] - 30.0)
            self._fire_zones.add(zone_id)
        elif event_type in ("water_line_blocked", "water_block"):
            state["water"] = 5.0                          # below FR-W-001 (<10mm)
            state["humidity"] = max(15.0, base["humidity"] - 25.0)
        elif event_type == "sensor_failure":
            state["temp"] = 0.0
            state["light"] = 0.0
            state["humidity"] = 0.0
            self._dead_zones.add(zone_id)
        elif event_type == "light_failure":
            state["light"] = 0.0                          # triggers FR-L-001 (<100 lux)
        elif event_type == "spike":
            state["temp"] = 38.0                          # above FR-T-002
        elif event_type == "drop":
            state["temp"] = 3.0                           # below FR-T-001 (<5°C)
        elif event_type == "recover":
            for key, val in base.items():
                state[key] = val
            self._fire_zones.discard(zone_id)
            self._dead_zones.discard(zone_id)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
