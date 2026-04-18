"""NASA API adapter — InSight weather + DONKI solar events.

NEVER crashes. Always returns data (real or fallback).
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime, timedelta

import requests

logger = structlog.get_logger(__name__)

FALLBACK_WEATHER: dict = {
    "sol": 1000,
    "temperature": {"avg": -60.0, "min": -95.0, "max": -10.0, "unit": "celsius"},
    "pressure": {"avg": 6.1, "min": 5.8, "max": 6.4, "unit": "hpa"},
    "wind_speed": {"avg": 5.5, "unit": "m/s"},
    "season": "winter",
}

INSIGHT_URL = "https://api.nasa.gov/insight_weather/"
DONKI_FLR_URL = "https://api.nasa.gov/DONKI/FLR"


class NasaAdapter:
    """HTTP client for NASA InSight weather + DONKI solar events."""

    def __init__(self, api_key: str = "DEMO_KEY", timeout: int = 5) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def get_mars_weather(self) -> dict:
        """Query InSight API for temperature, pressure, wind data.

        Falls back to hardcoded realistic data if API is unreachable.
        """
        try:
            url = f"{INSIGHT_URL}?api_key={self.api_key}&feedtype=json&ver=1.0"
            resp = requests.get(url, timeout=self.timeout)
            data = resp.json()

            sol_keys = data.get("sol_keys", [])
            if not sol_keys:
                return FALLBACK_WEATHER

            latest_sol = sol_keys[-1]
            sol_data = data[latest_sol]

            return {
                "sol": int(latest_sol),
                "temperature": {
                    "avg": sol_data.get("AT", {}).get("av", FALLBACK_WEATHER["temperature"]["avg"]),
                    "min": sol_data.get("AT", {}).get("mn", FALLBACK_WEATHER["temperature"]["min"]),
                    "max": sol_data.get("AT", {}).get("mx", FALLBACK_WEATHER["temperature"]["max"]),
                    "unit": "celsius",
                },
                "pressure": {
                    "avg": sol_data.get("PRE", {}).get("av", FALLBACK_WEATHER["pressure"]["avg"]),
                    "min": sol_data.get("PRE", {}).get("mn", FALLBACK_WEATHER["pressure"]["min"]),
                    "max": sol_data.get("PRE", {}).get("mx", FALLBACK_WEATHER["pressure"]["max"]),
                    "unit": "hpa",
                },
                "wind_speed": {
                    "avg": sol_data.get("HWS", {}).get("av", FALLBACK_WEATHER["wind_speed"]["avg"]),
                    "unit": "m/s",
                },
                "season": sol_data.get("Season", FALLBACK_WEATHER["season"]),
            }
        except (requests.ConnectionError, requests.Timeout):
            logger.warning("NASA InSight API unreachable — using fallback weather data")
            return FALLBACK_WEATHER
        except Exception:
            logger.warning("NASA InSight API error — using fallback weather data", exc_info=True)
            return FALLBACK_WEATHER

    def get_solar_events(self, days_back: int = 7) -> list[dict]:
        """Query DONKI for solar flare events.

        Falls back to empty list if API is unreachable.
        """
        try:
            end = datetime.now(UTC)
            start = end - timedelta(days=days_back)
            url = (
                f"{DONKI_FLR_URL}"
                f"?startDate={start.strftime('%Y-%m-%d')}"
                f"&endDate={end.strftime('%Y-%m-%d')}"
                f"&api_key={self.api_key}"
            )
            resp = requests.get(url, timeout=self.timeout)
            data = resp.json()
            return data if isinstance(data, list) else []
        except (requests.ConnectionError, requests.Timeout):
            logger.warning("NASA DONKI API unreachable — returning empty solar events")
            return []
        except Exception:
            logger.warning("NASA DONKI API error — returning empty solar events", exc_info=True)
            return []

    def get_mars_conditions_from_nasa(self) -> dict:
        """Combined weather + solar data for agent context."""
        return {
            "weather": self.get_mars_weather(),
            "solar_events": self.get_solar_events(),
        }
