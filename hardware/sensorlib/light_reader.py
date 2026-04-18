from __future__ import annotations

from .ads1115_reader import read_ads1115_channel


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def read_light_level(channel: int = 3, address: int = 0x48) -> dict[str, float | int]:
    raw, voltage = read_ads1115_channel(channel=channel, address=address)
    # In this wiring, brighter light yields lower voltage.
    level_pct = _clamp((1.0 - (voltage / 3.3)) * 100.0, 0.0, 100.0)
    return {
        "raw": raw,
        "voltage": voltage,
        "level_pct": level_pct,
    }

