"""E2E tests: Mars transform physics validation + NASA data comparison.

Verifies that our Earth→Mars transforms produce physically realistic
conditions and align with real NASA InSight data ranges.
"""

from __future__ import annotations

import math

import pytest

from eden.adapters.nasa_adapter import FALLBACK_WEATHER, NasaAdapter
from eden.domain.mars_transform import (
    _DOME_COUPLING,
    _DOME_TARGET_C,
    _GREENHOUSE_PRESSURE_HPA,
    _MARS_EXTERIOR_AVG_C,
    _MARS_SOLAR_FACTOR,
    _MARS_SOLAR_IRRADIANCE_W,
    _MISSION_DAYS,
    _SEASONAL_AMPLITUDE_C,
    get_mars_conditions,
    inject_dust_storm,
    inject_radiation,
    transform_light,
    transform_pressure,
    transform_temperature,
)


# ── 1. Temperature transform ────────────────────────────────────────────


class TestTransformTemperature:
    def test_earth_25c_sol0_gives_near_22c(self):
        """Earth 25°C → dome should be ~22°C (insulated dome, slight earth influence)."""
        result = transform_temperature(25.0, sol=0)
        # At sol=0 seasonal=0, earth deviation = (25-22)*0.15 = 0.45
        assert 21.0 <= result <= 24.0, f"Dome temp {result}°C out of realistic range"
        # Exact: 22 + 0 + 0.45 = 22.45
        assert result == pytest.approx(22.45, abs=0.01)

    def test_dome_stays_habitable_range(self):
        """Dome temp must stay within habitable range for all reasonable inputs."""
        for earth_c in [15.0, 20.0, 25.0, 30.0, 35.0]:
            for sol in [0, 100, 225, 337, 450]:
                result = transform_temperature(earth_c, sol)
                assert 15.0 <= result <= 28.0, (
                    f"Dome temp {result}°C at earth={earth_c}, sol={sol} is not habitable"
                )

    def test_seasonal_variation_at_peak(self):
        """At sol=112 (quarter mission), seasonal component is at max."""
        peak_sol = _MISSION_DAYS // 4  # sin peaks at π/2
        result = transform_temperature(22.0, sol=peak_sol)
        # seasonal = 8 * sin(2π * 112/450) ≈ 8 * sin(1.564) ≈ 8 * ~1.0 = ~8
        # exterior = -60 + ~8 = -52; dome coupling = (8) * 0.05 = 0.4
        # earth deviation = 0 (earth_c == dome target)
        assert result > _DOME_TARGET_C, "Positive seasonal swing should warm dome slightly"

    def test_seasonal_variation_at_trough(self):
        """At 3/4 mission, seasonal is at minimum."""
        trough_sol = 3 * _MISSION_DAYS // 4
        result = transform_temperature(22.0, sol=trough_sol)
        assert result < _DOME_TARGET_C, "Negative seasonal swing should cool dome slightly"


# ── 2. Light transform ──────────────────────────────────────────────────


class TestTransformLight:
    def test_earth_1000lux_dust03(self):
        """Earth 1000 lux, dust 0.3 → ~301 lux (43% solar * 70% dust transmission)."""
        result = transform_light(1000.0, dust_opacity=0.3)
        assert result == pytest.approx(301.0, abs=0.1)

    def test_mars_light_always_less_than_earth(self):
        """Mars light should always be less than Earth light."""
        for lux in [500, 1000, 5000, 10000]:
            for dust in [0.0, 0.3, 0.5, 0.8]:
                result = transform_light(lux, dust)
                assert result < lux, f"Mars light {result} >= Earth {lux}"

    def test_light_scales_linearly_with_input(self):
        """Double the earth lux → double the mars lux."""
        r1 = transform_light(500.0, 0.3)
        r2 = transform_light(1000.0, 0.3)
        assert r2 == pytest.approx(2 * r1, abs=0.01)


# ── 3. Pressure transform ───────────────────────────────────────────────


class TestTransformPressure:
    def test_earth_1013_gives_700(self):
        """Earth 1013.25 hPa → greenhouse ~700 hPa."""
        result = transform_pressure(1013.25)
        assert result == pytest.approx(700.0, abs=0.1)

    def test_greenhouse_pressure_above_mars_ambient(self):
        """Greenhouse pressure must be far above Mars ambient 6.1 hPa."""
        result = transform_pressure(1013.25)
        assert result > 600, f"Greenhouse {result} hPa too close to Mars ambient 6.1 hPa"

    def test_greenhouse_pressure_below_earth(self):
        """Greenhouse pressure should be below Earth sea level."""
        result = transform_pressure(1013.25)
        assert result < 1013.25, "Greenhouse pressure shouldn't exceed Earth"


# ── 4. Dust storm injection ─────────────────────────────────────────────


class TestDustStorm:
    def test_dust_opacity_085(self):
        """Dust storm sets opacity to 0.85."""
        conditions = inject_dust_storm(sol=100)
        assert conditions.dust_opacity == 0.85

    def test_storm_active_flag(self):
        conditions = inject_dust_storm(sol=100)
        assert conditions.storm_active is True

    def test_solar_drops_significantly(self):
        """Solar irradiance should drop ~85% during dust storm."""
        normal = get_mars_conditions(sol=100, dust_opacity=0.3)
        storm = inject_dust_storm(sol=100)
        assert storm.solar_irradiance < normal.solar_irradiance * 0.5
        # Exact: 590 * 0.15 = 88.5
        assert storm.solar_irradiance == pytest.approx(88.5, abs=0.1)

    def test_exterior_temp_drops_during_storm(self):
        """Exterior temp drops extra 15°C during dust storm (dust blocks sunlight)."""
        normal = get_mars_conditions(sol=100, dust_opacity=0.3)
        storm = inject_dust_storm(sol=100)
        assert storm.exterior_temp < normal.exterior_temp - 10


# ── 5. Radiation event ──────────────────────────────────────────────────


class TestRadiation:
    def test_radiation_alert_flag(self):
        conditions = inject_radiation(sol=100)
        assert conditions.radiation_alert is True
        assert conditions.storm_active is False

    def test_other_conditions_normal(self):
        """Radiation event should not change physical conditions."""
        normal = get_mars_conditions(sol=100, dust_opacity=0.3)
        radiation = inject_radiation(sol=100)
        assert radiation.dome_temp == pytest.approx(normal.dome_temp, abs=0.01)
        assert radiation.pressure_hpa == pytest.approx(normal.pressure_hpa, abs=0.01)
        assert radiation.solar_irradiance == pytest.approx(normal.solar_irradiance, abs=0.01)
        assert radiation.exterior_temp == pytest.approx(normal.exterior_temp, abs=0.01)


# ── 6. Full sol cycle ───────────────────────────────────────────────────


class TestSolCycle:
    SOL_CHECKPOINTS = [0, 100, 225, 450]

    def test_seasonal_variation_visible(self):
        """Exterior temp should vary across sol checkpoints (seasonal sinusoidal)."""
        temps = [get_mars_conditions(sol).exterior_temp for sol in self.SOL_CHECKPOINTS]
        # Not all the same — seasonal variation should be visible
        assert max(temps) - min(temps) > 1.0, (
            f"Seasonal variation too small: {temps}"
        )

    def test_dome_temp_stable_across_sols(self):
        """Dome temp should remain relatively stable despite exterior variation."""
        dome_temps = [get_mars_conditions(sol).dome_temp for sol in self.SOL_CHECKPOINTS]
        spread = max(dome_temps) - min(dome_temps)
        assert spread < 2.0, f"Dome temp spread {spread}°C is too large for insulated dome"

    def test_sol_0_and_450_match(self):
        """Sol 0 and sol 450 should produce the same conditions (full cycle)."""
        c0 = get_mars_conditions(0)
        c450 = get_mars_conditions(450)
        assert c0.exterior_temp == pytest.approx(c450.exterior_temp, abs=0.01)
        assert c0.dome_temp == pytest.approx(c450.dome_temp, abs=0.01)

    def test_pressure_constant_across_sols(self):
        """Greenhouse pressure should not change with sol (it's pressurized)."""
        pressures = [get_mars_conditions(sol).pressure_hpa for sol in self.SOL_CHECKPOINTS]
        assert all(p == _GREENHOUSE_PRESSURE_HPA for p in pressures)


# ── 7. Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    def test_dust_opacity_zero_perfectly_clear(self):
        """dust_opacity=0: no dust attenuation, full Mars solar."""
        result = transform_light(1000.0, dust_opacity=0.0)
        assert result == pytest.approx(430.0, abs=0.1)  # 1000 * 0.43

    def test_dust_opacity_one_total_blackout(self):
        """dust_opacity=1: total blackout, zero light."""
        result = transform_light(1000.0, dust_opacity=1.0)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_get_mars_conditions_clear_sky(self):
        conditions = get_mars_conditions(sol=50, dust_opacity=0.0)
        assert conditions.solar_irradiance == pytest.approx(_MARS_SOLAR_IRRADIANCE_W, abs=0.1)

    def test_get_mars_conditions_total_blackout(self):
        conditions = get_mars_conditions(sol=50, dust_opacity=1.0)
        assert conditions.solar_irradiance == pytest.approx(0.0, abs=0.01)

    def test_zero_earth_lux(self):
        """Zero earth input → zero mars output regardless of dust."""
        assert transform_light(0.0, 0.3) == 0.0

    def test_negative_temperature_input(self):
        """Sub-zero Earth reading still produces reasonable dome temp."""
        result = transform_temperature(-10.0, sol=0)
        # earth_deviation = (-10 - 22) * 0.15 = -4.8, dome = 22 - 4.8 = 17.2
        assert 10.0 <= result <= 22.0


# ── 8. NASA adapter comparison ───────────────────────────────────────────


class TestNasaComparison:
    """Compare our transforms against NASA InSight data ranges.

    Uses fallback data as ground truth since InSight API may be offline.
    Real Mars data: temp avg -60°C, pressure avg 6.1 hPa (ambient).
    """

    def test_exterior_temp_in_nasa_range(self):
        """Our exterior temp should fall within NASA InSight observed range."""
        nasa_min = FALLBACK_WEATHER["temperature"]["min"]  # -95
        nasa_max = FALLBACK_WEATHER["temperature"]["max"]  # -10
        for sol in [0, 50, 112, 225, 337, 450]:
            conditions = get_mars_conditions(sol)
            assert nasa_min <= conditions.exterior_temp <= nasa_max, (
                f"Sol {sol}: exterior {conditions.exterior_temp}°C outside NASA range "
                f"[{nasa_min}, {nasa_max}]"
            )

    def test_exterior_temp_avg_near_nasa_avg(self):
        """Average exterior temp across mission should be near NASA avg -60°C."""
        temps = [get_mars_conditions(sol).exterior_temp for sol in range(0, 451, 10)]
        avg = sum(temps) / len(temps)
        nasa_avg = FALLBACK_WEATHER["temperature"]["avg"]  # -60
        assert abs(avg - nasa_avg) < 2.0, (
            f"Mission avg exterior {avg:.1f}°C too far from NASA avg {nasa_avg}°C"
        )

    def test_greenhouse_pressure_vs_mars_ambient(self):
        """Greenhouse pressure >> Mars ambient (6.1 hPa from NASA)."""
        mars_ambient = FALLBACK_WEATHER["pressure"]["avg"]  # 6.1
        greenhouse = get_mars_conditions(sol=100).pressure_hpa
        assert greenhouse > mars_ambient * 100, (
            f"Greenhouse {greenhouse} hPa not much above Mars ambient {mars_ambient} hPa"
        )

    def test_nasa_adapter_never_crashes(self):
        """NASA adapter should return data (real or fallback) without crashing."""
        adapter = NasaAdapter(api_key="DEMO_KEY", timeout=3)
        weather = adapter.get_mars_weather()
        assert "temperature" in weather
        assert "pressure" in weather
        assert weather["temperature"]["unit"] == "celsius"

    def test_nasa_adapter_solar_events_returns_list(self):
        """Solar events should always return a list."""
        adapter = NasaAdapter(api_key="DEMO_KEY", timeout=3)
        events = adapter.get_solar_events()
        assert isinstance(events, list)

    def test_nasa_combined_endpoint(self):
        """Combined endpoint returns both weather and solar data."""
        adapter = NasaAdapter(api_key="DEMO_KEY", timeout=3)
        combined = adapter.get_mars_conditions_from_nasa()
        assert "weather" in combined
        assert "solar_events" in combined


# ── 9. Physics sanity checks ────────────────────────────────────────────


class TestPhysicsSanity:
    """Cross-cutting physics checks that span multiple transforms."""

    def test_dust_storm_reduces_light_more_than_normal(self):
        """Dust storm conditions should always produce less light than normal."""
        for sol in [0, 100, 225, 450]:
            normal = get_mars_conditions(sol, dust_opacity=0.3)
            storm = inject_dust_storm(sol)
            assert storm.solar_irradiance < normal.solar_irradiance

    def test_dome_temp_always_above_exterior(self):
        """Dome temp must always be above exterior (it's heated!)."""
        for sol in range(0, 451, 25):
            conditions = get_mars_conditions(sol)
            assert conditions.dome_temp > conditions.exterior_temp + 50, (
                f"Sol {sol}: dome {conditions.dome_temp}°C not enough above "
                f"exterior {conditions.exterior_temp}°C"
            )

    def test_mars_solar_irradiance_within_known_bounds(self):
        """Mars solar irradiance should be 0–590 W/m² (clear sky max)."""
        for dust in [0.0, 0.1, 0.3, 0.5, 0.85, 1.0]:
            conditions = get_mars_conditions(sol=100, dust_opacity=dust)
            assert 0.0 <= conditions.solar_irradiance <= _MARS_SOLAR_IRRADIANCE_W + 1
