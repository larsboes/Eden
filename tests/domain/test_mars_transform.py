"""Tests for Mars environment transform functions — TDD first."""

from eden.domain.mars_transform import (
    get_mars_conditions,
    inject_dust_storm,
    inject_radiation,
    transform_light,
    transform_pressure,
    transform_temperature,
)
from eden.domain.models import MarsConditions


# ── transform_temperature ────────────────────────────────────────────────


class TestTransformTemperature:
    def test_returns_reasonable_dome_temp(self):
        """Dome temp should be around 22°C, not wildly off."""
        result = transform_temperature(22.0, sol=100)
        assert 15.0 <= result <= 30.0

    def test_sol_zero(self):
        result = transform_temperature(22.0, sol=0)
        assert 15.0 <= result <= 30.0

    def test_sol_450(self):
        result = transform_temperature(22.0, sol=450)
        assert 15.0 <= result <= 30.0

    def test_different_earth_temps_affect_output(self):
        """Higher Earth input should trend higher."""
        low = transform_temperature(10.0, sol=100)
        high = transform_temperature(35.0, sol=100)
        assert high > low

    def test_seasonal_variation_exists(self):
        """Different sols should produce different temps (seasonal effect)."""
        temps = {transform_temperature(22.0, sol=s) for s in range(0, 450, 50)}
        # Should not all be identical — at least 2 distinct values
        assert len(temps) > 1


# ── transform_pressure ───────────────────────────────────────────────────


class TestTransformPressure:
    def test_scales_earth_to_mars_greenhouse(self):
        """Earth 1013.25 hPa should map to ~700 hPa greenhouse."""
        result = transform_pressure(1013.25)
        assert 680.0 <= result <= 720.0

    def test_proportional_scaling(self):
        """Half Earth pressure → half Mars greenhouse pressure."""
        full = transform_pressure(1013.25)
        half = transform_pressure(1013.25 / 2)
        assert abs(half - full / 2) < 20.0  # allow fluctuation

    def test_zero_pressure(self):
        result = transform_pressure(0.0)
        assert result >= 0.0


# ── transform_light ──────────────────────────────────────────────────────


class TestTransformLight:
    def test_reduces_by_mars_factor(self):
        """1000 lux on Earth with no dust → ~430 lux on Mars."""
        result = transform_light(1000.0, dust_opacity=0.0)
        assert 420.0 <= result <= 440.0

    def test_full_dust_blocks_all_light(self):
        """dust_opacity=1.0 → zero light."""
        result = transform_light(1000.0, dust_opacity=1.0)
        assert result == 0.0

    def test_partial_dust(self):
        """dust_opacity=0.5 → half of Mars light."""
        clear = transform_light(1000.0, dust_opacity=0.0)
        dusty = transform_light(1000.0, dust_opacity=0.5)
        assert abs(dusty - clear * 0.5) < 1.0

    def test_zero_earth_light(self):
        result = transform_light(0.0, dust_opacity=0.3)
        assert result == 0.0

    def test_dust_opacity_zero(self):
        result = transform_light(500.0, dust_opacity=0.0)
        assert result > 0.0


# ── get_mars_conditions ──────────────────────────────────────────────────


class TestGetMarsConditions:
    def test_returns_mars_conditions_type(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert isinstance(result, MarsConditions)

    def test_sol_stored(self):
        result = get_mars_conditions(sol=42, dust_opacity=0.3)
        assert result.sol == 42

    def test_dust_opacity_stored(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.5)
        assert result.dust_opacity == 0.5

    def test_default_no_storm(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert result.storm_active is False

    def test_default_no_radiation(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert result.radiation_alert is False

    def test_exterior_temp_cold(self):
        """Mars exterior averages -60°C."""
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert -80.0 <= result.exterior_temp <= -40.0

    def test_dome_temp_livable(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert 15.0 <= result.dome_temp <= 30.0

    def test_pressure_around_700(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        assert 680.0 <= result.pressure_hpa <= 720.0

    def test_solar_irradiance_reduced_by_dust(self):
        clear = get_mars_conditions(sol=100, dust_opacity=0.0)
        dusty = get_mars_conditions(sol=100, dust_opacity=0.5)
        assert dusty.solar_irradiance < clear.solar_irradiance

    def test_default_dust_opacity(self):
        """Default dust_opacity should be 0.3."""
        result = get_mars_conditions(sol=100)
        assert result.dust_opacity == 0.3

    def test_to_dict_works(self):
        result = get_mars_conditions(sol=100, dust_opacity=0.3)
        d = result.to_dict()
        assert "exterior_temp" in d
        assert "sol" in d


# ── inject_dust_storm ────────────────────────────────────────────────────


class TestInjectDustStorm:
    def test_returns_mars_conditions(self):
        result = inject_dust_storm(sol=200)
        assert isinstance(result, MarsConditions)

    def test_storm_active(self):
        result = inject_dust_storm(sol=200)
        assert result.storm_active is True

    def test_high_dust_opacity(self):
        result = inject_dust_storm(sol=200)
        assert result.dust_opacity >= 0.8

    def test_solar_irradiance_reduced(self):
        normal = get_mars_conditions(sol=200, dust_opacity=0.3)
        storm = inject_dust_storm(sol=200)
        assert storm.solar_irradiance < normal.solar_irradiance

    def test_exterior_temp_drops(self):
        normal = get_mars_conditions(sol=200, dust_opacity=0.3)
        storm = inject_dust_storm(sol=200)
        assert storm.exterior_temp < normal.exterior_temp

    def test_sol_preserved(self):
        result = inject_dust_storm(sol=300)
        assert result.sol == 300


# ── inject_radiation ─────────────────────────────────────────────────────


class TestInjectRadiation:
    def test_returns_mars_conditions(self):
        result = inject_radiation(sol=150)
        assert isinstance(result, MarsConditions)

    def test_radiation_alert_set(self):
        result = inject_radiation(sol=150)
        assert result.radiation_alert is True

    def test_storm_not_active(self):
        """Radiation event != dust storm."""
        result = inject_radiation(sol=150)
        assert result.storm_active is False

    def test_sol_preserved(self):
        result = inject_radiation(sol=250)
        assert result.sol == 250

    def test_conditions_otherwise_normal(self):
        """Radiation event shouldn't wildly change other conditions."""
        result = inject_radiation(sol=100)
        assert -80.0 <= result.exterior_temp <= -40.0
        assert 15.0 <= result.dome_temp <= 30.0
