"""Greenhouse resource tracking with realistic drift simulation.

PURE PYTHON. Zero external imports. Only stdlib. THIS IS THE LAW.
"""

from __future__ import annotations

import random


class ResourceTracker:
    """Tracks water, battery, solar, desal, O2 for the greenhouse."""

    # (sigma, lower_clamp, upper uses max from _resources)
    _DRIFT: dict[str, tuple[float, float]] = {
        "water": (2.0, 100.0),
        "battery": (0.8, 20.0),
        "solar": (1.0, 30.0),
        "desal": (2.0, 36.0),
        "o2": (0.1, 10.0),
    }

    def __init__(self) -> None:
        self._resources: dict[str, dict] = {
            "water": {"current": 340.0, "max": 600.0, "unit": "L", "label": "Clean Water Reserve"},
            "battery": {"current": 78.0, "max": 100.0, "unit": "%", "label": "Battery Charge"},
            "solar": {"current": 100.0, "max": 100.0, "unit": "%", "label": "Solar Output"},
            "desal": {"current": 120.0, "max": 120.0, "unit": "L/sol", "label": "Desalination Rate"},
            "o2": {"current": 14.2, "max": 20.0, "unit": "%", "label": "O\u2082 Contribution"},
        }

    def tick(self) -> None:
        """Advance one reconciler cycle -- apply random drift to all resources."""
        for key, res in self._resources.items():
            sigma, lower = self._DRIFT[key]
            res["current"] = max(lower, min(res["max"], res["current"] + random.gauss(0, sigma)))

    def get_state(self) -> dict:
        """Return current resource state with computed rate descriptions."""
        out: dict[str, dict] = {}
        for key, res in self._resources.items():
            out[key] = {
                "current": round(res["current"], 1),
                "max": res["max"],
                "unit": res["unit"],
                "rate": self._rate_description(key, res["current"]),
                "label": res["label"],
            }
        return out

    # ── Rate description logic ────────────────────────────────────────

    @staticmethod
    def _rate_description(key: str, current: float) -> str:
        """Compute a human-readable rate string based on current level."""
        if key == "water":
            if current > 500:
                return "Reserves high"
            if current > 300:
                return "+20 L/sol surplus"
            if current > 200:
                return "Adequate"
            return "LOW \u2014 rationing"

        if key == "battery":
            if current > 90:
                return "Fully charged"
            if current > 50:
                return "Cycling nominal"
            if current > 30:
                return "Draining"
            return "CRITICAL"

        if key == "solar":
            if current > 90:
                return "kW output nominal"
            if current > 60:
                return "Partial output"
            if current > 40:
                return "Degraded"
            return "STORM \u2014 minimal"

        if key == "desal":
            if current > 100:
                return "Nominal capacity"
            if current > 60:
                return "Reduced capacity"
            return "Emergency only"

        if key == "o2":
            if current > 13:
                return "Greenhouse O\u2082 nominal"
            if current > 11:
                return "Reduced \u2014 lights dimmed"
            return "CRITICAL"

        return ""
