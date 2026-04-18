from __future__ import annotations

from .ads1115_reader import read_ads1115_channel


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def moisture_pct_from_voltage(voltage: float) -> float:
    # In this setup, wetter probe => lower voltage.
    return _clamp((1.0 - (voltage / 3.3)) * 100.0, 0.0, 100.0)


def moisture_pct_from_raw(raw: int, dry_raw: int | None, wet_raw: int | None) -> float:
    if dry_raw is None or wet_raw is None:
        return _clamp((raw / 32767.0) * 100.0, 0.0, 100.0)
    if dry_raw == wet_raw:
        return 0.0
    pct = ((raw - dry_raw) / float(wet_raw - dry_raw)) * 100.0
    return _clamp(pct, 0.0, 100.0)


def read_hl69(
    channel: int = 1,
    address: int = 0x48,
    dry_raw: int | None = None,
    wet_raw: int | None = None,
) -> dict[str, float | int]:
    raw, voltage = read_ads1115_channel(channel=channel, address=address)
    if dry_raw is not None and wet_raw is not None:
        moisture_pct = moisture_pct_from_raw(raw=raw, dry_raw=dry_raw, wet_raw=wet_raw)
    else:
        moisture_pct = moisture_pct_from_voltage(voltage=voltage)
    return {
        "raw": raw,
        "voltage": voltage,
        "moisture_pct": moisture_pct,
    }

