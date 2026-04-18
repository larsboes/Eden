"""Strands SDK adapter — wraps EDEN specialists into Strands Agent instances.

Uses strands.Agent + BedrockModel to create proper agentic wrappers around
our 12-specialist parliament.  Integrates both local @tool functions and
MCP tools from multiple MCP clients (Syngenta KB + NASA APIs).
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class StrandsAgentFactory:
    """Factory for creating Strands Agent instances for each EDEN specialist.

    Wraps each of our 12 specialists into proper Strands Agent instances,
    combining local tool functions with MCP tools from Syngenta KB + NASA.

    When running inside AgentCore Runtime, accepts a runtime_context to
    propagate auth headers to MCP Gateway connections.
    """

    def __init__(
        self,
        mcp_client: Any | None = None,
        mcp_clients: list[Any] | None = None,
        runtime_context: Any | None = None,
    ) -> None:
        """
        Args:
            mcp_client: Single MCP adapter (backwards-compatible).
            mcp_clients: List of MCP adapters (Syngenta, NASA, etc.).
                         If both are provided, mcp_client is prepended.
            runtime_context: AgentCore Runtime context (provides auth headers,
                             session ID). Pass when running inside Runtime.
        """
        self._mcp_clients: list[Any] = []
        if mcp_client is not None:
            self._mcp_clients.append(mcp_client)
        if mcp_clients:
            self._mcp_clients.extend(mcp_clients)
        self._runtime_context = runtime_context

    # Backwards-compatible property
    @property
    def _mcp_client(self) -> Any | None:
        return self._mcp_clients[0] if self._mcp_clients else None

    def create_specialist(
        self,
        name: str,
        system_prompt: str,
        tools: list,
        model: Any,
    ) -> Any:
        """Create a Strands Agent for a named specialist.

        Args:
            name: Agent name (e.g. "DEMETER", "SENTINEL").
            system_prompt: The specialist's system prompt.
            tools: List of local @tool-decorated functions.
            model: A BedrockModel (or compatible) instance.

        Returns:
            A strands.Agent instance ready for invocation.
        """
        from strands import Agent

        all_tools = list(tools)

        # Add MCP tools from all connected MCP clients
        mcp_tools = self._get_mcp_tools()
        all_tools.extend(mcp_tools)

        agent = Agent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
            callback_handler=None,  # Suppress stdout — server-side agents
            name=name,
        )
        logger.info("Created Strands agent '%s' with %d tools (%d local + %d MCP)",
                     name, len(all_tools), len(tools), len(mcp_tools))
        return agent

    def create_flora(
        self,
        zone_id: str,
        crop_name: str,
        tools: list,
        model: Any,
    ) -> Any:
        """Create a FLORA agent instance for a specific zone.

        FLORA agents speak AS the plant — first person.  Each zone gets
        its own FLORA instance with zone-specific context baked in.

        Args:
            zone_id: The zone this FLORA represents (e.g. "alpha").
            crop_name: The crop in this zone (e.g. "Tomato").
            tools: List of local @tool-decorated functions.
            model: A BedrockModel (or compatible) instance.

        Returns:
            A strands.Agent instance for this zone's FLORA.
        """
        from eden.application.agent import FLORA_PROMPT

        prompt = (
            FLORA_PROMPT
            .replace("{{zone_id}}", zone_id)
            .replace("{{crop_name}}", crop_name)
        )

        return self.create_specialist(
            name=f"FLORA-{zone_id}",
            system_prompt=prompt,
            tools=tools,
            model=model,
        )

    def create_bedrock_model(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-6",
        region_name: str = "us-west-2",
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> Any:
        """Create a Strands BedrockModel instance.

        Falls back to None if strands is not installed, allowing the caller
        to use the raw boto3 BedrockAdapter instead.
        """
        try:
            from strands.models.bedrock import BedrockModel
            return BedrockModel(
                model_id=model_id,
                region_name=region_name,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except ImportError:
            logger.warning("strands.models.bedrock not available — use raw BedrockAdapter")
            return None

    def _get_mcp_tools(self) -> list:
        """Get MCP tools from all connected MCP adapters."""
        all_tools: list = []
        for client in self._mcp_clients:
            try:
                if hasattr(client, "list_tools") and client.is_available():
                    all_tools.extend(client.list_tools())
            except Exception:
                logger.debug("Failed to get MCP tools from %s", type(client).__name__, exc_info=True)
        return all_tools
