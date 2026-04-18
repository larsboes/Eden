from __future__ import annotations

import time

import adafruit_dht
import board


def _read_once(sensor_type: str, retries: int, delay_s: float) -> tuple[float, float] | None:
    sensor_cls = adafruit_dht.DHT11 if sensor_type == "dht11" else adafruit_dht.DHT22
    dht = sensor_cls(board.D25, use_pulseio=False)
    try:
        for _ in range(retries):
            try:
                temperature_c = dht.temperature
                humidity = dht.humidity
                if temperature_c is not None and humidity is not None:
                    return float(temperature_c), float(humidity)
            except RuntimeError:
                pass
            time.sleep(delay_s)
    finally:
        dht.exit()
    return None


def read_dht(sensor: str = "dht11", retries: int = 3, delay_s: float = 0.25) -> dict[str, float | str]:
    # KY-015 is DHT11; keep support for dht22/auto for flexibility.
    if sensor not in ("dht11", "dht22", "auto"):
        raise ValueError("sensor must be one of dht11, dht22, auto")

    order = ["dht11", "dht22"] if sensor == "auto" else [sensor]
    for sensor_type in order:
        result = _read_once(sensor_type=sensor_type, retries=retries, delay_s=delay_s)
        if result is not None:
            temperature_c, humidity_pct = result
            return {
                "sensor": sensor_type.upper(),
                "temperature_c": temperature_c,
                "humidity_pct": humidity_pct,
            }

    raise RuntimeError("Failed to read DHT sensor from GPIO25.")

