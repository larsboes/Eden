"""Tests for NASA API adapter — InSight weather + DONKI solar events."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from eden.adapters.nasa_adapter import FALLBACK_WEATHER, NasaAdapter


@pytest.fixture
def adapter():
    return NasaAdapter(api_key="TEST_KEY", timeout=5)


# ── get_mars_weather ─────────────────────────────────────────────────────


class TestGetMarsWeather:
    def test_successful_api_call(self, adapter):
        """Mock a successful InSight response and verify parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sol_keys": ["1000"],
            "1000": {
                "AT": {"av": -63.0, "mn": -95.1, "mx": -14.2},
                "PRE": {"av": 6.3, "mn": 5.9, "mx": 6.7},
                "HWS": {"av": 4.8},
                "Season": "winter",
            },
        }

        with patch("eden.adapters.nasa_adapter.requests.get", return_value=mock_response):
            result = adapter.get_mars_weather()

        assert result["sol"] == 1000
        assert result["temperature"]["avg"] == -63.0
        assert result["pressure"]["avg"] == 6.3
        assert result["wind_speed"]["avg"] == 4.8
        assert result["season"] == "winter"

    def test_correct_url_construction(self, adapter):
        """Verify the API key and params are included in the URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sol_keys": []}

        with patch("eden.adapters.nasa_adapter.requests.get", return_value=mock_response) as mock_get:
            adapter.get_mars_weather()
            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            assert "api_key=TEST_KEY" in url
            assert "insight_weather" in url

    def test_connection_error_returns_fallback(self, adapter):
        """ConnectionError should return fallback data, never crash."""
        with patch("eden.adapters.nasa_adapter.requests.get", side_effect=requests.ConnectionError):
            result = adapter.get_mars_weather()

        assert result == FALLBACK_WEATHER

    def test_timeout_returns_fallback(self, adapter):
        """Timeout should return fallback data, never crash."""
        with patch("eden.adapters.nasa_adapter.requests.get", side_effect=requests.Timeout):
            result = adapter.get_mars_weather()

        assert result == FALLBACK_WEATHER

    def test_empty_sol_keys_returns_fallback(self, adapter):
        """If API returns no sol data, use fallback."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sol_keys": []}

        with patch("eden.adapters.nasa_adapter.requests.get", return_value=mock_response):
            result = adapter.get_mars_weather()

        assert result == FALLBACK_WEATHER

    def test_fallback_data_structure(self):
        """Verify fallback data has all expected keys."""
        assert "sol" in FALLBACK_WEATHER
        assert "temperature" in FALLBACK_WEATHER
        assert "pressure" in FALLBACK_WEATHER
        assert "wind_speed" in FALLBACK_WEATHER
        assert "season" in FALLBACK_WEATHER
        assert "avg" in FALLBACK_WEATHER["temperature"]
        assert "min" in FALLBACK_WEATHER["temperature"]
        assert "max" in FALLBACK_WEATHER["temperature"]


# ── get_solar_events ─────────────────────────────────────────────────────


class TestGetSolarEvents:
    def test_successful_api_call(self, adapter):
        """Mock a successful DONKI response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "flrID": "2026-03-15T12:00:00-FLR-001",
                "classType": "M1.2",
                "beginTime": "2026-03-15T12:00Z",
            },
        ]

        with patch("eden.adapters.nasa_adapter.requests.get", return_value=mock_response):
            result = adapter.get_solar_events(days_back=7)

        assert len(result) == 1
        assert result[0]["classType"] == "M1.2"

    def test_correct_url_construction(self, adapter):
        """Verify API key and date params are in the URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("eden.adapters.nasa_adapter.requests.get", return_value=mock_response) as mock_get:
            adapter.get_solar_events(days_back=7)
            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            assert "api_key=TEST_KEY" in url
            assert "DONKI/FLR" in url
            assert "startDate=" in url
            assert "endDate=" in url

    def test_connection_error_returns_empty_list(self, adapter):
        """ConnectionError should return empty list, never crash."""
        with patch("eden.adapters.nasa_adapter.requests.get", side_effect=requests.ConnectionError):
            result = adapter.get_solar_events()

        assert result == []

    def test_timeout_returns_empty_list(self, adapter):
        """Timeout should return empty list, never crash."""
        with patch("eden.adapters.nasa_adapter.requests.get", side_effect=requests.Timeout):
            result = adapter.get_solar_events()

        assert result == []


# ── get_mars_conditions_from_nasa ────────────────────────────────────────


class TestGetMarsConditionsFromNasa:
    def test_combines_weather_and_solar(self, adapter):
        """Verify combined output merges both sources."""
        weather = FALLBACK_WEATHER.copy()
        solar = [{"classType": "X1.0"}]

        with patch.object(adapter, "get_mars_weather", return_value=weather), \
             patch.object(adapter, "get_solar_events", return_value=solar):
            result = adapter.get_mars_conditions_from_nasa()

        assert result["weather"] == weather
        assert result["solar_events"] == solar

    def test_both_sources_fail_gracefully(self, adapter):
        """Even if both APIs fail, we get structured data back."""
        with patch.object(adapter, "get_mars_weather", return_value=FALLBACK_WEATHER), \
             patch.object(adapter, "get_solar_events", return_value=[]):
            result = adapter.get_mars_conditions_from_nasa()

        assert "weather" in result
        assert "solar_events" in result
        assert isinstance(result["solar_events"], list)
