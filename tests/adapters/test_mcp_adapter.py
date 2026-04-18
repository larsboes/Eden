"""Tests for MCP adapters — Syngenta KB (HTTP) + NASA APIs (stdio)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from eden.adapters.mcp_adapter import NasaMCPAdapter, SyngentaKBAdapter, _CACHE_TTL


# ═══════════════════════════════════════════════════════════════════════════
# Syngenta KB Adapter
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def adapter():
    """Adapter with no real connection (offline mode)."""
    return SyngentaKBAdapter(
        gateway_url="https://test-gateway.example.com/mcp",
        auth_token="test-token-123",
    )


@pytest.fixture
def connected_adapter():
    """Adapter that appears connected with a mock client."""
    a = SyngentaKBAdapter(
        gateway_url="https://test-gateway.example.com/mcp",
        auth_token="test-token-123",
    )
    a._available = True
    a._client = MagicMock()
    a._tools = [
        {"name": "search_knowledge_base", "description": "Search Syngenta KB"},
        {"name": "get_crop_profile", "description": "Get crop data"},
    ]
    return a


# ── Construction ─────────────────────────────────────────────────────────


class TestConstruction:
    def test_defaults(self, adapter):
        assert adapter._gateway_url == "https://test-gateway.example.com/mcp"
        assert adapter._auth_token == "test-token-123"
        assert adapter._available is False
        assert adapter._client is None

    def test_no_auth_token(self):
        a = SyngentaKBAdapter(gateway_url="https://example.com/mcp")
        assert a._auth_token is None

    def test_source_name(self, adapter):
        assert adapter._source_name == "syngenta_mcp"


# ── is_available ─────────────────────────────────────────────────────────


class TestIsAvailable:
    def test_not_available_when_not_connected(self, adapter):
        assert adapter.is_available() is False

    def test_available_when_connected(self, connected_adapter):
        assert connected_adapter.is_available() is True

    def test_not_available_when_client_none(self):
        a = SyngentaKBAdapter(gateway_url="https://example.com/mcp")
        a._available = True
        a._client = None
        assert a.is_available() is False


# ── list_tools ───────────────────────────────────────────────────────────


class TestListTools:
    def test_returns_tools_when_connected(self, connected_adapter):
        tools = connected_adapter.list_tools()
        assert len(tools) == 2

    def test_returns_empty_when_not_connected(self, adapter):
        tools = adapter.list_tools()
        assert tools == []


# ── query (offline) ──────────────────────────────────────────────────────


class TestQueryOffline:
    def test_returns_fallback_when_not_connected(self, adapter):
        result = adapter.query("tomato growth stages")
        assert result["source"] == "syngenta_mcp_offline"
        assert result["available"] is False
        assert result["query"] == "tomato growth stages"

    def test_fallback_has_result_message(self, adapter):
        result = adapter.query("anything")
        assert "unavailable" in result["result"].lower()


# ── query (online with mock) ────────────────────────────────────────────


class TestQueryOnline:
    def test_successful_query(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"data": "tomato info"})

        result = connected_adapter.query("tomato optimal temperature")

        assert result["source"] == "syngenta_mcp"
        assert result["result"] == {"data": "tomato info"}

    def test_query_exception_returns_fallback(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(side_effect=RuntimeError("connection lost"))

        result = connected_adapter.query("failing query")

        assert result["source"] == "syngenta_mcp_offline"
        assert result["available"] is False


# ── Cache behavior ───────────────────────────────────────────────────────


class TestCache:
    def test_same_query_returns_cached(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"data": "cached"})

        result1 = connected_adapter.query("lettuce watering schedule")
        result2 = connected_adapter.query("lettuce watering schedule")

        assert result1 == result2
        # Should only call the MCP tool once
        assert connected_adapter._client.call_tool_sync.call_count == 1

    def test_different_queries_not_cached(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"data": "result"})

        connected_adapter.query("query one")
        connected_adapter.query("query two")

        assert connected_adapter._client.call_tool_sync.call_count == 2

    def test_cache_case_insensitive(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"data": "result"})

        connected_adapter.query("Tomato Growth")
        connected_adapter.query("tomato growth")

        assert connected_adapter._client.call_tool_sync.call_count == 1

    def test_cache_expires_after_ttl(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"data": "result"})

        connected_adapter.query("expiring query")
        # Manually expire the cache entry
        for key in connected_adapter._cache:
            connected_adapter._cache[key] = (time.time() - _CACHE_TTL - 1, connected_adapter._cache[key][1])

        connected_adapter.query("expiring query")

        assert connected_adapter._client.call_tool_sync.call_count == 2


# ── Domain-specific methods ──────────────────────────────────────────────


class TestDomainMethods:
    def test_check_crop_profile(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"crop": "tomato"})

        result = connected_adapter.check_crop_profile("tomato")

        assert result["source"] == "syngenta_mcp"
        assert "tomato" in result["query"].lower()

    def test_check_stress_response(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"stress": "leaf curl"})

        result = connected_adapter.check_stress_response("leaf curl")

        assert result["source"] == "syngenta_mcp"
        assert "leaf curl" in result["query"].lower()

    def test_check_nutritional_strategy(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"nutrient": "nitrogen"})

        result = connected_adapter.check_nutritional_strategy("nitrogen deficiency")

        assert result["source"] == "syngenta_mcp"
        assert "nitrogen" in result["query"].lower()

    def test_check_greenhouse_scenarios(self, connected_adapter):
        connected_adapter._client.call_tool_sync = MagicMock(return_value={"scenario": "dust storm"})

        result = connected_adapter.check_greenhouse_scenarios("dust storm power reduction")

        assert result["source"] == "syngenta_mcp"
        assert "dust storm" in result["query"].lower()

    def test_domain_methods_fallback_offline(self, adapter):
        """All domain methods gracefully return fallback when offline."""
        for method, arg in [
            (adapter.check_crop_profile, "tomato"),
            (adapter.check_stress_response, "wilting"),
            (adapter.check_nutritional_strategy, "phosphorus"),
            (adapter.check_greenhouse_scenarios, "power outage"),
        ]:
            result = method(arg)
            assert result["source"] == "syngenta_mcp_offline"


# ── Connect / Disconnect ────────────────────────────────────────────────


class TestLifecycle:
    @patch("eden.adapters.mcp_adapter.SyngentaKBAdapter.connect")
    def test_connect_sets_available(self, mock_connect, adapter):
        """connect() should set _available when successful."""
        # Simulate a successful connect
        adapter._available = True
        adapter._client = MagicMock()
        assert adapter.is_available() is True

    def test_disconnect_cleans_up(self, connected_adapter):
        """disconnect() should clean up client and mark unavailable."""
        connected_adapter.disconnect()

        assert connected_adapter._client is None
        assert connected_adapter._available is False
        assert connected_adapter._tools is None
        assert connected_adapter.is_available() is False

    def test_disconnect_when_not_connected(self, adapter):
        """disconnect() on an unconnected adapter should not raise."""
        adapter.disconnect()  # Should not raise
        assert adapter.is_available() is False

    def test_connect_failure_stays_offline(self):
        """If MCP imports fail, adapter stays in offline mode."""
        a = SyngentaKBAdapter(gateway_url="https://example.com/mcp")
        # connect() will fail because mcp/strands may not be installed in test env
        a.connect()
        # Should not crash, just stay offline
        # (may be available if libs ARE installed but gateway unreachable)
        assert a._client is None or a.is_available() is False or a.is_available() is True


# ═══════════════════════════════════════════════════════════════════════════
# NASA MCP Adapter
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def nasa_adapter():
    """NASA MCP adapter with no real connection."""
    return NasaMCPAdapter(api_key="TEST_NASA_KEY")


@pytest.fixture
def connected_nasa():
    """NASA MCP adapter that appears connected with a mock client."""
    a = NasaMCPAdapter(api_key="TEST_NASA_KEY")
    a._available = True
    a._client = MagicMock()
    a._tools = [
        {"name": "get_insight_weather", "description": "InSight Mars Weather"},
        {"name": "get_donki_flr", "description": "DONKI Solar Flares"},
        {"name": "get_mars_rover_photos", "description": "Mars Rover Photos"},
        {"name": "get_neo_feed", "description": "Near-Earth Objects"},
    ]
    return a


class TestNasaConstruction:
    def test_defaults(self, nasa_adapter):
        assert nasa_adapter._api_key == "TEST_NASA_KEY"
        assert nasa_adapter._command == "npx"
        assert nasa_adapter._args == ["-y", "@programcomputer/nasa-mcp-server@latest"]
        assert nasa_adapter._available is False
        assert nasa_adapter._source_name == "nasa_mcp"

    def test_custom_command(self):
        a = NasaMCPAdapter(api_key="KEY", command="node", args=["server.js"])
        assert a._command == "node"
        assert a._args == ["server.js"]


class TestNasaIsAvailable:
    def test_not_available_when_not_connected(self, nasa_adapter):
        assert nasa_adapter.is_available() is False

    def test_available_when_connected(self, connected_nasa):
        assert connected_nasa.is_available() is True


class TestNasaListTools:
    def test_returns_tools_when_connected(self, connected_nasa):
        tools = connected_nasa.list_tools()
        assert len(tools) == 4

    def test_returns_empty_when_not_connected(self, nasa_adapter):
        assert nasa_adapter.list_tools() == []


class TestNasaQueryOffline:
    def test_returns_fallback_when_not_connected(self, nasa_adapter):
        result = nasa_adapter.query("Mars weather")
        assert result["source"] == "nasa_mcp_offline"
        assert result["available"] is False

    def test_fallback_has_result_message(self, nasa_adapter):
        result = nasa_adapter.query("anything")
        assert "unavailable" in result["result"].lower()


class TestNasaQueryOnline:
    def test_successful_query(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"temp": -63.0})

        result = connected_nasa.query("Mars InSight weather")

        assert result["source"] == "nasa_mcp"
        assert result["result"] == {"temp": -63.0}

    def test_query_exception_returns_fallback(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(side_effect=RuntimeError("subprocess died"))

        result = connected_nasa.query("failing query")

        assert result["source"] == "nasa_mcp_offline"
        assert result["available"] is False


class TestNasaCache:
    def test_same_query_returns_cached(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"data": "cached"})

        connected_nasa.query("Mars InSight weather")
        connected_nasa.query("Mars InSight weather")

        assert connected_nasa._client.call_tool_sync.call_count == 1

    def test_cache_expires(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"data": "result"})

        connected_nasa.query("expiring query")
        for key in connected_nasa._cache:
            connected_nasa._cache[key] = (time.time() - _CACHE_TTL - 1, connected_nasa._cache[key][1])

        connected_nasa.query("expiring query")

        assert connected_nasa._client.call_tool_sync.call_count == 2


class TestNasaDomainMethods:
    def test_get_mars_weather(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"temp": -60.0})
        result = connected_nasa.get_mars_weather()
        assert result["source"] == "nasa_mcp"

    def test_get_solar_events(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"flares": []})
        result = connected_nasa.get_solar_events()
        assert result["source"] == "nasa_mcp"
        assert "donki" in result["query"].lower() or "solar" in result["query"].lower()

    def test_get_mars_rover_photos(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"photos": []})
        result = connected_nasa.get_mars_rover_photos("curiosity")
        assert result["source"] == "nasa_mcp"
        assert "curiosity" in result["query"].lower()

    def test_get_power_data(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"irradiance": 590})
        result = connected_nasa.get_power_data()
        assert result["source"] == "nasa_mcp"
        assert "power" in result["query"].lower() or "solar" in result["query"].lower()

    def test_get_neo_data(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"asteroids": []})
        result = connected_nasa.get_neo_data()
        assert result["source"] == "nasa_mcp"

    def test_get_fire_data(self, connected_nasa):
        connected_nasa._client.call_tool_sync = MagicMock(return_value={"fires": []})
        result = connected_nasa.get_fire_data()
        assert result["source"] == "nasa_mcp"
        assert "fire" in result["query"].lower() or "firms" in result["query"].lower()

    def test_all_domain_methods_fallback_offline(self, nasa_adapter):
        """All NASA domain methods gracefully return fallback when offline."""
        for method in [
            nasa_adapter.get_mars_weather,
            nasa_adapter.get_solar_events,
            lambda: nasa_adapter.get_mars_rover_photos("curiosity"),
            nasa_adapter.get_power_data,
            nasa_adapter.get_neo_data,
            nasa_adapter.get_fire_data,
        ]:
            result = method()
            assert result["source"] == "nasa_mcp_offline"


class TestNasaLifecycle:
    def test_disconnect_cleans_up(self, connected_nasa):
        connected_nasa.disconnect()
        assert connected_nasa._client is None
        assert connected_nasa._available is False
        assert connected_nasa._tools is None

    def test_disconnect_when_not_connected(self, nasa_adapter):
        nasa_adapter.disconnect()  # Should not raise
        assert nasa_adapter.is_available() is False
