from __future__ import annotations

from .ads1115_reader import read_ads1115_channel


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def level_pct_from_voltage(voltage: float) -> float:
    return _clamp((voltage / 3.3) * 100.0, 0.0, 100.0)


def level_pct_from_raw(raw: int, dry_raw: int, wet_raw: int) -> float:
    if dry_raw == wet_raw:
        return 0.0
    pct = ((raw - dry_raw) / float(wet_raw - dry_raw)) * 100.0
    return _clamp(pct, 0.0, 100.0)


def read_water_level(
    channel: int = 0,
    address: int = 0x48,
    dry_raw: int | None = None,
    wet_raw: int | None = None,
) -> dict[str, float | int]:
    raw, voltage = read_ads1115_channel(channel=channel, address=address)
    if dry_raw is not None and wet_raw is not None:
        level_pct = level_pct_from_raw(raw=raw, dry_raw=dry_raw, wet_raw=wet_raw)
    else:
        level_pct = level_pct_from_voltage(voltage=voltage)
    return {
        "raw": raw,
        "voltage": voltage,
        "level_pct": level_pct,
    }

