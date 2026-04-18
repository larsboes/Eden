#!/usr/bin/env python3
"""Read water level from ADS1115."""

from __future__ import annotations

import argparse
import sys
import time

from sensorlib.water_reader import read_water_level


def main() -> int:
    parser = argparse.ArgumentParser(description="Read water level from ADS1115")
    parser.add_argument("--channel", type=int, choices=(0, 1, 2, 3), default=0)
    parser.add_argument("--address", type=lambda x: int(x, 0), default=0x48)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()

    if args.interval <= 0:
        print("--interval must be > 0", file=sys.stderr)
        return 2

    try:
        _ = read_water_level(channel=args.channel, address=args.address)
    except Exception as exc:
        print(f"ADC init failed: {exc}", file=sys.stderr)
        return 1

    print(f"ADS1115 ready at address 0x{args.address:02X}, channel A{args.channel}.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            values = read_water_level(channel=args.channel, address=args.address)
            print(
                f"raw={int(values['raw']):5d} voltage={float(values['voltage']):.4f}V "
                f"level_pct={float(values['level_pct']):6.2f}"
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

