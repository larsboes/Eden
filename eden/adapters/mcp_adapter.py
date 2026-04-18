"""MCP adapters — Syngenta KB (HTTP) + NASA APIs (stdio subprocess).

Local-first pattern: cache responses in memory, fall back gracefully when
gateways are unreachable.  Both adapters share the same cache/fallback logic
via _BaseMCPAdapter.
"""

from __future__ import annotations

import hashlib
import structlog
import os
import time
from typing import Any

logger = structlog.get_logger(__name__)

# Cache TTL — how long a cached KB response stays valid (seconds)
_CACHE_TTL = 300  # 5 minutes


# ── Base MCP Adapter ─────────────────────────────────────────────────────


class _BaseMCPAdapter:
    """Shared cache + fallback logic for all MCP adapters."""

    def __init__(self, source_name: str) -> None:
        self._source_name = source_name
        self._client: Any | None = None
        self._cache: dict[str, tuple[float, dict]] = {}
        self._available = False
        self._tools: list | None = None

    # ── Public interface ──────────────────────────────────────────────

    def list_tools(self) -> list:
        if self._tools is not None:
            return self._tools
        return []

    def is_available(self) -> bool:
        return self._available and self._client is not None

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.__exit__(None, None, None)
            except Exception:
                logger.debug("Error during MCP client disconnect", exc_info=True)
            finally:
                self._client = None
                self._available = False
                self._tools = None

    def query(self, query: str) -> dict:
        cache_key = self._cache_key(query)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if not self._available or self._client is None:
            return self._fallback_response(query)

        try:
            result = self._call_tool("search_knowledge_base", {"query": query})
            response = {"query": query, "source": self._source_name, "result": result}
            self._put_cached(cache_key, response)
            return response
        except Exception:
            logger.warning("MCP query failed for: %s", query, exc_info=True)
            return self._fallback_response(query)

    # ── Cache helpers ─────────────────────────────────────────────────

    def _cache_key(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> dict | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, result = entry
        if time.time() - ts > _CACHE_TTL:
            del self._cache[key]
            return None
        return result

    def _put_cached(self, key: str, result: dict) -> None:
        self._cache[key] = (time.time(), result)

    # ── Internal ──────────────────────────────────────────────────────

    def _extract_tool_name(self, tool) -> str | None:
        """Extract tool name from MCPAgentTool, dict, or any tool object."""
        # Try common attribute names
        for attr in ("name", "tool_name", "function_name"):
            val = getattr(tool, attr, None)
            if val and isinstance(val, str):
                return val
        # Try dict access
        if isinstance(tool, dict):
            return tool.get("name") or tool.get("tool_name")
        # Try nested: tool.tool.name (Strands MCPAgentTool wraps MCP Tool)
        inner = getattr(tool, "tool", None)
        if inner:
            inner_name = getattr(inner, "name", None)
            if inner_name and isinstance(inner_name, str):
                return inner_name
        # Try tool_spec.name
        spec = getattr(tool, "tool_spec", None)
        if spec:
            spec_name = getattr(spec, "name", None) or (spec.get("name") if isinstance(spec, dict) else None)
            if spec_name and isinstance(spec_name, str):
                return spec_name
        return None

    def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        if self._client is None:
            raise RuntimeError("MCP client not connected")
        tools = self.list_tools()

        # Log all tool names for debugging
        all_names = [self._extract_tool_name(t) or "?" for t in tools]
        logger.debug("MCP tools available: %s (looking for %s)", all_names, tool_name)

        resolved_name: str | None = None

        # Try exact match first
        for tool in tools:
            name = self._extract_tool_name(tool)
            if name and name == tool_name:
                resolved_name = name
                break

        # Try substring match (e.g., "search_knowledge_base" in tool name)
        if resolved_name is None:
            for tool in tools:
                name = self._extract_tool_name(tool)
                if name and tool_name in name:
                    resolved_name = name
                    break

        # Try keyword overlap
        if resolved_name is None:
            keywords = {"search", "knowledge", "query", "retrieve", "kb", "ask", "crop", "mars"}
            for tool in tools:
                name = self._extract_tool_name(tool)
                if name and any(kw in name.lower() for kw in keywords):
                    logger.info("MCP tool match by keyword: %s (wanted %s)", name, tool_name)
                    resolved_name = name
                    break

        # Last resort: use the first available tool
        if resolved_name is None and tools:
            first_name = self._extract_tool_name(tools[0])
            if first_name:
                logger.info("MCP fallback to first tool: %s (wanted %s)", first_name, tool_name)
                resolved_name = first_name

        if resolved_name is None:
            resolved_name = tool_name

        # Strands MCPClient.call_tool_sync(tool_use_id, name, arguments)
        return self._client.call_tool_sync("eden_call", resolved_name, arguments)

    def _fallback_response(self, query: str) -> dict:
        return {
            "query": query,
            "source": f"{self._source_name}_offline",
            "result": "MCP gateway unavailable — using local knowledge only",
            "available": False,
        }


class SyngentaKBAdapter(_BaseMCPAdapter):
    """Syngenta MCP Knowledge Base via AgentCore Gateway (HTTP).

    Uses MCPClient + streamablehttp_client to connect.
    When AGENTCORE_GATEWAY_ENDPOINT is set, routes through our own Gateway
    instead of the default Syngenta URL.
    """

    def __init__(
        self,
        gateway_url: str,
        auth_token: str | None = None,
    ) -> None:
        super().__init__(source_name="syngenta_mcp")
        # If AgentCore Gateway is deployed, use it as the MCP endpoint
        agentcore_url = os.getenv("AGENTCORE_GATEWAY_ENDPOINT", "")
        if agentcore_url:
            logger.info("Using AgentCore Gateway endpoint: %s", agentcore_url)
            self._gateway_url = agentcore_url
        else:
            self._gateway_url = gateway_url
        self._auth_token = auth_token

    def connect(self) -> None:
        """Establish MCP client connection to the Syngenta KB gateway."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from strands.tools.mcp.mcp_client import MCPClient

            headers = {}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

            self._client = MCPClient(lambda: streamablehttp_client(
                url=self._gateway_url,
                headers=headers,
            ))
            self._client.__enter__()
            self._tools = self._client.list_tools_sync()
            self._available = True
            tool_names = [self._extract_tool_name(t) or "?" for t in self._tools]
            logger.info("Connected to Syngenta MCP KB at %s (%d tools: %s)",
                        self._gateway_url, len(self._tools), tool_names)
        except Exception:
            logger.warning("Failed to connect to Syngenta MCP KB — running in offline mode")
            self._available = False
            self._client = None
            self._tools = None

    # ── Domain-specific query methods ─────────────────────────────────

    def check_crop_profile(self, crop_name: str) -> dict:
        """Query crop profiles domain."""
        q = f"crop profile optimal growing conditions for {crop_name}"
        return self.query(q)

    def check_stress_response(self, symptom: str) -> dict:
        """Query plant stress domain."""
        q = f"plant stress response diagnosis treatment for {symptom}"
        return self.query(q)

    def check_nutritional_strategy(self, query: str) -> dict:
        """Query nutrition domain."""
        q = f"crop nutritional strategy fertilization {query}"
        return self.query(q)

    def check_greenhouse_scenarios(self, scenario: str) -> dict:
        """Query operational scenarios domain."""
        q = f"greenhouse operational scenario {scenario}"
        return self.query(q)

    def query_simulation_params(self, crop_name: str) -> dict:
        """Query KB for crop simulation parameters (GDD, stress thresholds, transpiration).

        Returns raw KB response. Numerical extraction happens in the overlay step.
        Queries 3 KB domains: Crop Profiles, Plant Stress, CEA Principles.
        """
        queries = [
            (
                f"What are the optimal growing conditions, base temperature for "
                f"Growing Degree Day calculation, total thermal time to maturity, "
                f"harvest index, and water use efficiency for {crop_name} "
                f"in controlled environment agriculture?"
            ),
            (
                f"What are the temperature, water, and radiation stress thresholds "
                f"for {crop_name} at different growth stages? "
                f"Include BBCH scale stage sensitivity."
            ),
            (
                f"What is the daily transpiration rate for {crop_name} by growth stage "
                f"in a hydroponic or aeroponic greenhouse system?"
            ),
        ]
        results = []
        for q in queries:
            results.append(self.query(q))
        return {
            "crop_name": crop_name,
            "source": "syngenta_mcp",
            "crop_profile": results[0],
            "stress_thresholds": results[1],
            "transpiration": results[2],
        }


# ── NASA MCP Adapter ─────────────────────────────────────────────────────


class NasaMCPAdapter(_BaseMCPAdapter):
    """NASA APIs via MCP stdio subprocess (@programcomputer/nasa-mcp-server).

    Exposes 20+ NASA tools including InSight weather, DONKI solar events,
    Mars Rover photos, POWER climate/energy, NEO asteroids, FIRMS fire detection.

    Falls back to the existing NasaAdapter HTTP client when MCP is unavailable.
    """

    def __init__(
        self,
        api_key: str,
        command: str = "npx",
        args: list[str] | None = None,
    ) -> None:
        super().__init__(source_name="nasa_mcp")
        self._api_key = api_key
        self._command = command
        self._args = args or ["-y", "@programcomputer/nasa-mcp-server@latest"]

    def connect(self) -> None:
        """Launch NASA MCP server as a stdio subprocess and connect."""
        try:
            from mcp.client.stdio import StdioServerParameters, stdio_client
            from strands.tools.mcp.mcp_client import MCPClient

            server_params = StdioServerParameters(
                command=self._command,
                args=self._args,
                env={**os.environ, "NASA_API_KEY": self._api_key, "DOTENV_DEBUG": "false", "DEBUG": ""},
            )

            self._client = MCPClient(lambda: stdio_client(server_params))
            self._client.__enter__()
            self._tools = self._client.list_tools_sync()
            self._available = True
            logger.info("Connected to NASA MCP server (%d tools)", len(self._tools))
        except Exception:
            logger.warning("Failed to connect to NASA MCP server — running in offline mode")
            self._available = False
            self._client = None
            self._tools = None

    # ── Domain-specific query methods ─────────────────────────────────

    def get_mars_weather(self) -> dict:
        """Query InSight Mars weather via MCP tool."""
        return self.query("Mars InSight weather temperature pressure wind")

    def get_solar_events(self) -> dict:
        """Query DONKI for solar flare / space weather events."""
        return self.query("DONKI solar flare coronal mass ejection space weather")

    def get_mars_rover_photos(self, rover: str = "curiosity") -> dict:
        """Get Mars Rover photos."""
        return self.query(f"Mars Rover {rover} latest photos")

    def get_power_data(self, lat: float = 4.5, lon: float = 137.4) -> dict:
        """Get NASA POWER climate/energy data (relevant for HELIOS agent)."""
        return self.query(f"NASA POWER solar irradiance energy data lat {lat} lon {lon}")

    def get_neo_data(self) -> dict:
        """Get near-Earth object / asteroid data."""
        return self.query("near earth object asteroid close approach")

    def get_fire_data(self) -> dict:
        """Get FIRMS fire detection data (relevant for SENTINEL agent)."""
        return self.query("FIRMS active fire detection thermal anomaly")
