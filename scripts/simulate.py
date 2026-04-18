#!/usr/bin/env python3
"""EDEN Simulation CLI — fast-forward greenhouse operations on Mars or Earth.

Examples:
  # 30-day Mars simulation with full agent parliament (real Bedrock + Strands SDK)
  python scripts/simulate.py --mode mars --days 30 --output sim_mars.jsonl

  # 30-day Earth simulation (same architecture, different planet!)
  python scripts/simulate.py --mode earth --days 30 --output sim_earth.jsonl

  # Rules-only mode (no LLM, completes in seconds — shows Tier 0 safety floor)
  python scripts/simulate.py --mode mars --days 30 --no-llm --output sim_mars_fast.jsonl

  # Start from Sol 200 (mid-mission) with custom crisis injection
  python scripts/simulate.py --mode mars --days 10 --start-sol 200 \\
      --inject "dust_storm:3" --inject "fire:sim-beta:7" --inject "radiation:5"

  # Replay recorded simulation at 100x speed with live dashboard
  python scripts/simulate.py --replay sim_mars.jsonl --speed 100 --serve

  # Quick 7-day test
  python scripts/simulate.py --mode mars --days 7 --cycles-per-day 2 --no-llm

Crisis injection format: EVENT_TYPE[:ZONE_ID]:DAY_OFFSET
  Supported events: dust_storm, fire, sensor_failure, radiation, cold_snap,
                    heat_wave, overcast, rain, pest_pressure, water_line_blocked
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_inject(inject_str: str) -> tuple[int, dict]:
    """Parse an inject string like 'dust_storm:3' or 'fire:sim-beta:7' into (day, event_dict)."""
    parts = inject_str.split(":")
    if len(parts) < 2:
        raise ValueError(
            f"Invalid inject format: '{inject_str}'. "
            "Expected EVENT_TYPE:DAY or EVENT_TYPE:ZONE_ID:DAY"
        )

    event_type = parts[0]
    if len(parts) == 2:
        # EVENT_TYPE:DAY
        day = int(parts[1])
        zone_id = None
    else:
        # EVENT_TYPE:ZONE_ID:DAY
        zone_id = parts[1]
        day = int(parts[2])

    # Build event dict based on type
    event_dict: dict = {"event": event_type, "label": f"Injected: {event_type}"}
    if zone_id:
        event_dict["zone_id"] = zone_id

    # Type-specific defaults
    if event_type == "dust_storm":
        event_dict["dust_opacity"] = 0.75
        event_dict["label"] = f"Injected dust storm (day {day})"
    elif event_type == "fire":
        event_dict["label"] = f"Injected fire in {zone_id or 'random zone'} (day {day})"
    elif event_type == "radiation":
        event_dict["label"] = f"Injected radiation event (day {day})"
    elif event_type == "sensor_failure":
        event_dict["label"] = f"Injected sensor failure in {zone_id or 'random zone'} (day {day})"
    elif event_type == "cold_snap":
        event_dict["temp_delta"] = -8.0
        event_dict["label"] = f"Injected cold snap (day {day})"
    elif event_type == "heat_wave":
        event_dict["temp_delta"] = 7.0
        event_dict["label"] = f"Injected heat wave (day {day})"
    elif event_type == "overcast":
        event_dict["light_factor"] = 0.3
        event_dict["label"] = f"Injected overcast (day {day})"
    elif event_type == "rain":
        event_dict["humidity_delta"] = 15.0
        event_dict["label"] = f"Injected rain (day {day})"
    elif event_type == "pest_pressure":
        event_dict["label"] = f"Injected pest pressure in {zone_id or 'all zones'} (day {day})"
    elif event_type == "water_line_blocked":
        event_dict["label"] = f"Injected water line blocked (day {day})"

    return (day, event_dict)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EDEN Simulation — fast-forward greenhouse on Mars or Earth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    parser.add_argument(
        "--mode", choices=["mars", "earth"], default="mars",
        help="Planet mode (default: mars)",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of days/sols to simulate (default: 30)",
    )
    parser.add_argument(
        "--cycles-per-day", type=int, default=4,
        help="Reconciliation cycles per simulated day (default: 4 = every 6h)",
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Flight rules only — no LLM calls (fast, completes in seconds)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible sensor data (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSONL file path (default: sim_{mode}_{days}d.jsonl)",
    )
    parser.add_argument(
        "--start-sol", type=int, default=0,
        help="Starting sol/day number (default: 0). E.g., --start-sol 200 for mid-mission",
    )
    parser.add_argument(
        "--inject", action="append", default=[],
        help=(
            "Inject crisis event: EVENT_TYPE[:ZONE_ID]:DAY_OFFSET. "
            "Can be used multiple times. E.g., --inject dust_storm:5 --inject fire:sim-beta:12"
        ),
    )

    # Replay mode
    parser.add_argument(
        "--replay", type=str, default=None,
        help="Replay a recorded JSONL file instead of generating",
    )
    parser.add_argument(
        "--speed", type=float, default=100.0,
        help="Replay speed multiplier (default: 100x)",
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="Start API server during replay so dashboard can connect",
    )

    # General
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.replay:
        # ── Replay mode ──
        from eden.timeshift import replay

        replay(
            jsonl_path=Path(args.replay),
            speed=args.speed,
            serve=args.serve,
        )
    else:
        # ── Generate mode ──
        from eden.timeshift import SimulationEngine

        # Parse custom crisis injections
        custom_events = []
        for inject_str in args.inject:
            try:
                custom_events.append(parse_inject(inject_str))
            except ValueError as e:
                parser.error(str(e))

        if custom_events:
            logging.getLogger("eden.timeshift").info(
                "Custom crisis injections: %s",
                [f"{e[1]['event']} on day {e[0]}" for e in custom_events],
            )

        output = Path(args.output) if args.output else None
        engine = SimulationEngine(
            mode=args.mode,
            days=args.days,
            cycles_per_day=args.cycles_per_day,
            use_llm=not args.no_llm,
            seed=args.seed,
            output=output,
            start_sol=args.start_sol,
            inject=custom_events,
        )
        result_path = engine.run()
        print(f"\nSimulation output: {result_path}")
        print(f"Replay with: python scripts/simulate.py --replay {result_path} --speed 100 --serve")


if __name__ == "__main__":
    main()
