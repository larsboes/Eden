#!/usr/bin/env python3
"""Read pressure from BMP280 over I2C."""

from __future__ import annotations

import argparse
import sys
import time

from sensorlib.bmp280_reader import read_bmp280


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read BMP280 pressure on I2C")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--address", type=lambda x: int(x, 0), default=0x76)
    parser.add_argument("--show-temp", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        _ = read_bmp280(address=args.address)
    except Exception as exc:
        print(f"Sensor init failed: {exc}", file=sys.stderr)
        return 1

    print("BMP280 ready on I2C.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            values = read_bmp280(address=args.address)
            pressure_hpa = values["pressure_hpa"]
            if args.show_temp:
                print(f"Pressure: {pressure_hpa:.1f} hPa | Temp: {values['temperature_c']:.2f} C")
            else:
                print(f"Pressure: {pressure_hpa:.1f} hPa")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

