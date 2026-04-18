"""Earth → Mars sensor transforms — PURE FUNCTIONS.

ZERO external imports. Only stdlib + domain models. THIS IS THE LAW.
"""

from __future__ import annotations

import math

from eden.domain.models import MarsConditions

# ── Constants ────────────────────────────────────────────────────────────

_MARS_EXTERIOR_AVG_C = -60.0  # Average Mars surface temp
_DOME_TARGET_C = 22.0  # Greenhouse dome target temp
_EARTH_PRESSURE_HPA = 1013.25
_GREENHOUSE_PRESSURE_HPA = 700.0  # Pressurized greenhouse
_MARS_SOLAR_FACTOR = 0.43  # Mars gets ~43% of Earth's solar irradiance
_MARS_SOLAR_IRRADIANCE_W = 590.0  # W/m² at Mars distance (avg)
_MISSION_DAYS = 450
_SEASONAL_AMPLITUDE_C = 8.0  # Seasonal temp swing on exterior
_DOME_COUPLING = 0.05  # How much exterior affects dome temp


# ── Pure transform functions ─────────────────────────────────────────────


def transform_temperature(earth_c: float, sol: int) -> float:
    """Transform Earth temperature reading to Mars dome temperature.

    Mars exterior averages -60°C. The dome maintains ~22°C but is
    slightly affected by exterior conditions and seasonal variation.
    """
    # Seasonal variation: sinusoidal over the mission
    seasonal = _SEASONAL_AMPLITUDE_C * math.sin(2 * math.pi * sol / _MISSION_DAYS)
    exterior = _MARS_EXTERIOR_AVG_C + seasonal

    # Dome temp: target + small coupling to exterior + Earth-input deviation
    earth_deviation = (earth_c - _DOME_TARGET_C) * 0.15  # Earth input influence
    dome_temp = _DOME_TARGET_C + (exterior - _MARS_EXTERIOR_AVG_C) * _DOME_COUPLING + earth_deviation

    return dome_temp


def transform_pressure(earth_hpa: float) -> float:
    """Scale Earth pressure to Mars greenhouse pressure (~700 hPa)."""
    scale = _GREENHOUSE_PRESSURE_HPA / _EARTH_PRESSURE_HPA
    return earth_hpa * scale


def transform_light(earth_lux: float, dust_opacity: float) -> float:
    """Reduce Earth light by Mars distance factor and dust.

    Mars gets ~43% of Earth's solar irradiance, further reduced by dust.
    dust_opacity: 0.0 (clear) to 1.0 (total blackout).
    """
    return earth_lux * _MARS_SOLAR_FACTOR * (1.0 - dust_opacity)


def get_mars_conditions(sol: int, dust_opacity: float = 0.3) -> MarsConditions:
    """Build full MarsConditions for a given sol.

    Returns a snapshot of Mars environmental conditions including
    exterior temp, dome temp, pressure, solar irradiance, and flags.
    """
    seasonal = _SEASONAL_AMPLITUDE_C * math.sin(2 * math.pi * sol / _MISSION_DAYS)
    exterior_temp = _MARS_EXTERIOR_AVG_C + seasonal
    dome_temp = _DOME_TARGET_C + (exterior_temp - _MARS_EXTERIOR_AVG_C) * _DOME_COUPLING
    pressure_hpa = _GREENHOUSE_PRESSURE_HPA
    solar_irradiance = _MARS_SOLAR_IRRADIANCE_W * (1.0 - dust_opacity)

    return MarsConditions(
        exterior_temp=exterior_temp,
        dome_temp=dome_temp,
        pressure_hpa=pressure_hpa,
        solar_irradiance=solar_irradiance,
        dust_opacity=dust_opacity,
        sol=sol,
        storm_active=False,
        radiation_alert=False,
    )


def enrich_from_nasa(
    base: MarsConditions,
    nasa_weather: dict | None = None,
    solar_events: list | None = None,
) -> MarsConditions:
    """Enrich computed MarsConditions with real NASA data. PURE FUNCTION.

    Uses real InSight exterior temp, derives dust from wind speed,
    and sets radiation_alert from DONKI solar flare class.
    Returns base unchanged if no NASA data is available.
    """
    exterior_temp = base.exterior_temp
    dust_opacity = base.dust_opacity
    storm_active = base.storm_active
    radiation_alert = base.radiation_alert

    if nasa_weather:
        # Real exterior temp from InSight
        temp_data = nasa_weather.get("temperature", {})
        if "avg" in temp_data and temp_data["avg"] is not None:
            exterior_temp = temp_data["avg"]

        # Derive dust opacity from wind speed (higher wind → more dust)
        wind_data = nasa_weather.get("wind_speed", {})
        wind_avg = wind_data.get("avg", 0) or 0
        if wind_avg > 0:
            # Mars wind > 15 m/s triggers dust storm territory
            dust_opacity = min(0.95, max(base.dust_opacity, wind_avg / 30.0))
            storm_active = storm_active or wind_avg > 15.0

    if solar_events:
        for event in solar_events:
            class_type = str(event.get("classType", ""))
            if class_type.startswith("X"):
                radiation_alert = True
                break
            if class_type.startswith("M"):
                try:
                    if float(class_type[1:]) >= 5.0:
                        radiation_alert = True
                        break
                except (ValueError, IndexError):
                    pass

    # Recompute derived values from (potentially updated) inputs
    dome_temp = _DOME_TARGET_C + (exterior_temp - _MARS_EXTERIOR_AVG_C) * _DOME_COUPLING
    solar_irradiance = _MARS_SOLAR_IRRADIANCE_W * (1.0 - dust_opacity)

    return MarsConditions(
        exterior_temp=exterior_temp,
        dome_temp=dome_temp,
        pressure_hpa=base.pressure_hpa,
        solar_irradiance=solar_irradiance,
        dust_opacity=dust_opacity,
        sol=base.sol,
        storm_active=storm_active,
        radiation_alert=radiation_alert,
    )


def inject_dust_storm(sol: int) -> MarsConditions:
    """Override conditions for a dust storm scenario.

    High dust opacity, reduced solar, storm flag active,
    exterior temp drops further due to dust blocking sunlight.
    """
    dust_opacity = 0.85
    seasonal = _SEASONAL_AMPLITUDE_C * math.sin(2 * math.pi * sol / _MISSION_DAYS)
    exterior_temp = _MARS_EXTERIOR_AVG_C + seasonal - 15.0  # Extra cold during storm
    dome_temp = _DOME_TARGET_C + (exterior_temp - _MARS_EXTERIOR_AVG_C) * _DOME_COUPLING
    solar_irradiance = _MARS_SOLAR_IRRADIANCE_W * (1.0 - dust_opacity)

    return MarsConditions(
        exterior_temp=exterior_temp,
        dome_temp=dome_temp,
        pressure_hpa=_GREENHOUSE_PRESSURE_HPA,
        solar_irradiance=solar_irradiance,
        dust_opacity=dust_opacity,
        sol=sol,
        storm_active=True,
        radiation_alert=False,
    )


def inject_radiation(sol: int) -> MarsConditions:
    """Override conditions for a radiation event.

    Radiation alert set, other conditions remain normal.
    """
    conditions = get_mars_conditions(sol, dust_opacity=0.3)
    # Reconstruct with radiation_alert=True (frozen dataclass)
    return MarsConditions(
        exterior_temp=conditions.exterior_temp,
        dome_temp=conditions.dome_temp,
        pressure_hpa=conditions.pressure_hpa,
        solar_irradiance=conditions.solar_irradiance,
        dust_opacity=conditions.dust_opacity,
        sol=conditions.sol,
        storm_active=False,
        radiation_alert=True,
    )
