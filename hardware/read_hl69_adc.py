#!/usr/bin/env python3
"""Read HL-69 soil moisture from ADS1115."""

from __future__ import annotations

import argparse
import sys
import time

from sensorlib.hl69_reader import read_hl69


def main() -> int:
    parser = argparse.ArgumentParser(description="Read HL-69 moisture from ADS1115")
    parser.add_argument("--channel", type=int, choices=(0, 1, 2, 3), default=1)
    parser.add_argument("--address", type=lambda x: int(x, 0), default=0x48)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--dry-raw", type=int, default=None)
    parser.add_argument("--wet-raw", type=int, default=None)
    args = parser.parse_args()

    if args.interval <= 0:
        print("--interval must be > 0", file=sys.stderr)
        return 2
    if (args.dry_raw is None) ^ (args.wet_raw is None):
        print("Provide both --dry-raw and --wet-raw, or neither.", file=sys.stderr)
        return 2

    try:
        _ = read_hl69(
            channel=args.channel,
            address=args.address,
            dry_raw=args.dry_raw,
            wet_raw=args.wet_raw,
        )
    except Exception as exc:
        print(f"ADC init failed: {exc}", file=sys.stderr)
        return 1

    print(f"ADS1115 ready at address 0x{args.address:02X}, channel A{args.channel}.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            values = read_hl69(
                channel=args.channel,
                address=args.address,
                dry_raw=args.dry_raw,
                wet_raw=args.wet_raw,
            )
            print(
                f"raw={int(values['raw']):5d} voltage={float(values['voltage']):.4f}V "
                f"moisture_pct={float(values['moisture_pct']):6.2f}"
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

