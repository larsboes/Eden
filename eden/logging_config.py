"""EDEN Structured Logging — enterprise-grade observability via structlog.

Provides:
- Beautiful colorful console output for development (padded columns, colors, icons)
- JSON output for production (log aggregation, CloudWatch, ELK)
- Contextvars-based context propagation (cycle_id, request_id, zone_id)
- stdlib integration (uvicorn, boto3, etc. also get formatted)
- Exception formatting with full tracebacks

Usage:
    from eden.logging_config import configure_logging
    configure_logging(log_level="INFO", json_output=False)

    import structlog
    logger = structlog.get_logger()
    logger.info("event_name", key="value", metric=42)
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


# ── Custom EDEN Console Renderer ─────────────────────────────────────────


class EdenConsoleRenderer:
    """Beautiful padded console renderer with EDEN branding and level icons.

    Output format:
      2026-03-20T00:28:57 [INFO ] 🌱 eden.reconciler  │ reconcile_cycle_start  zones=4 sol=247
      2026-03-20T00:28:57 [WARN ] ⚠️  eden.flight_rules │ fire_detected          zone_id=zone-protein
      2026-03-20T00:28:57 [ERROR] 🔥 eden.council      │ council_member_failed  member=Lena
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_CYAN = "\033[96m"

    LEVEL_STYLES = {
        "debug":    (f"\033[2m[DEBUG]\033[0m", "  ", DIM),
        "info":     (f"\033[32m[INFO ]\033[0m", "🌱", GREEN),
        "warning":  (f"\033[33m[WARN ]\033[0m", "⚠️ ", YELLOW),
        "warn":     (f"\033[33m[WARN ]\033[0m", "⚠️ ", YELLOW),
        "error":    (f"\033[31m[ERROR]\033[0m", "🔥", RED),
        "critical": (f"\033[1;31m[CRIT ]\033[0m", "💀", BRIGHT_RED),
    }

    LOGGER_WIDTH = 28
    EVENT_WIDTH = 32

    def __init__(self, colors: bool = True) -> None:
        self._colors = colors

    def __call__(self, logger, method_name, event_dict):
        level = event_dict.pop("level", method_name)
        timestamp = event_dict.pop("timestamp", "")
        logger_name = event_dict.pop("logger", "eden")
        event = event_dict.pop("event", "")

        # Shorten logger name: eden.application.reconciler → eden.reconciler
        short_name = logger_name
        for prefix in ("eden.application.", "eden.adapters.", "eden.domain."):
            if short_name.startswith(prefix):
                short_name = "eden." + short_name[len(prefix):]
                break

        if self._colors:
            level_badge, icon, color = self.LEVEL_STYLES.get(
                level, (f"[{level.upper():5s}]", "  ", self.WHITE),
            )

            # Timestamp (dimmed)
            ts = f"{self.DIM}{timestamp[:19]}{self.RESET}" if timestamp else ""

            # Logger name (cyan, padded)
            padded_logger = f"{self.CYAN}{short_name:<{self.LOGGER_WIDTH}s}{self.RESET}"

            # Event name (bold, padded)
            padded_event = f"{self.BOLD}{color}{event:<{self.EVENT_WIDTH}s}{self.RESET}"

            # Key=value pairs (dimmed keys, bright values)
            kv_parts = []
            for key, value in event_dict.items():
                if key.startswith("_"):
                    continue
                kv_parts.append(
                    f"{self.DIM}{key}={self.RESET}{color}{value}{self.RESET}"
                )
            kv_str = "  ".join(kv_parts)

            sep = f"{self.DIM}│{self.RESET}"
            return f"{ts} {level_badge} {icon} {padded_logger}{sep} {padded_event} {kv_str}"
        else:
            # No-color fallback
            padded_logger = f"{short_name:<{self.LOGGER_WIDTH}s}"
            padded_event = f"{event:<{self.EVENT_WIDTH}s}"
            kv_parts = [f"{k}={v}" for k, v in event_dict.items() if not k.startswith("_")]
            kv_str = "  ".join(kv_parts)
            return f"{timestamp[:19]} [{level.upper():5s}] {padded_logger}│ {padded_event} {kv_str}"


# ── Configure ────────────────────────────────────────────────────────────


def configure_logging(
    log_level: str = "INFO",
    json_output: bool | None = None,
) -> None:
    """Configure structlog + stdlib logging integration.

    Args:
        log_level: Python log level name (DEBUG, INFO, WARNING, ERROR).
        json_output: Force JSON (True) or console (False). If None, auto-detect:
                     JSON when EDEN_LOG_JSON=true or no TTY on stdout.
    """
    if json_output is None:
        json_output = (
            os.getenv("EDEN_LOG_JSON", "false").lower() == "true"
            or not sys.stdout.isatty()
        )

    level = getattr(logging, log_level.upper(), logging.INFO)

    # ── Shared processors (run for BOTH structlog and stdlib loggers) ──
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # ── Renderer ──
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = EdenConsoleRenderer(colors=sys.stdout.isatty())

    # ── Configure structlog ──
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ── Configure stdlib root logger with structlog formatter ──
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # ── Quiet noisy third-party loggers ──
    for noisy in (
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "botocore",
        "urllib3",
        "strands",
    ):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))
