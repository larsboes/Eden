#!/usr/bin/env python3
"""Read air temperature/humidity from KY-015 (DHT11) on GPIO25."""

from __future__ import annotations

import argparse
import sys

from sensorlib.dht_reader import read_dht


def main() -> int:
    parser = argparse.ArgumentParser(description="Read DHT11/KY-015 on GPIO25")
    parser.add_argument("--sensor", choices=("dht11", "dht22", "auto"), default="dht11")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()

    try:
        result = read_dht(sensor=args.sensor, retries=args.retries, delay_s=args.delay)
    except Exception as exc:
        print(f"Failed to read DHT sensor: {exc}", file=sys.stderr)
        return 1

    print(
        f"sensor={result['sensor']} temperature_c={result['temperature_c']:.1f} "
        f"humidity_pct={result['humidity_pct']:.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

