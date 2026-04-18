"""AgentCore Runtime entry point — deploys EDEN agent to managed runtime.

This is the 4-line pattern from Lab 04: wrap our existing agent logic
behind the BedrockAgentCoreApp entrypoint so it can be served on port 8080
with /invocations + /ping endpoints.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# ── Lazy imports to keep cold start fast ──────────────────────────────

def _create_app():
    """Create the BedrockAgentCoreApp with our agent wired in."""
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    @app.entrypoint
    async def invoke(payload: dict, context=None):
        """Handle an invocation from AgentCore Runtime.

        Payload shape:
            {"prompt": "...", "zone_id": "alpha", "session_id": "..."}
        """
        import traceback

        mcp_client = None
        try:
            from strands import Agent
            from strands.models.bedrock import BedrockModel
            from strands.tools.mcp.mcp_client import MCPClient
            from mcp.client.streamable_http import streamablehttp_client

            from eden.config import Settings

            settings = Settings()
            user_input = payload.get("prompt", "")
            session_id = getattr(context, "session_id", None) or payload.get("session_id", "")

            # Propagate auth header from the runtime request
            auth_header = ""
            if context and hasattr(context, "request_headers"):
                auth_header = (context.request_headers or {}).get("Authorization", "")

            # Build model
            model = BedrockModel(
                model_id=os.getenv(
                    "BEDROCK_MODEL_ID",
                    "us.anthropic.claude-sonnet-4-20250514-v1:0",
                ),
                region_name=settings.AWS_REGION,
            )

            # Gather tools: local tools + MCP gateway tools
            tools = _get_local_tools(settings)

            gateway_url = os.getenv("AGENTCORE_GATEWAY_ENDPOINT", "")
            if gateway_url and auth_header:
                try:
                    mcp_client = MCPClient(lambda: streamablehttp_client(
                        url=gateway_url,
                        headers={"Authorization": auth_header},
                    ))
                    mcp_client.__enter__()
                    mcp_tools = mcp_client.list_tools_sync()
                    tools.extend(mcp_tools)
                    logger.info("Loaded %d MCP tools from gateway", len(mcp_tools))
                except Exception:
                    logger.warning("Failed to connect to MCP gateway — using local tools only",
                                   exc_info=True)

            # System prompt
            system_prompt = _get_system_prompt(session_id)

            agent = Agent(
                model=model,
                tools=tools,
                system_prompt=system_prompt,
            )
            response = agent(user_input)
            content = response.message.get("content", [])
            text = content[0]["text"] if content else str(response)
            return {"response": text, "session_id": session_id}
        except Exception as exc:
            error_detail = traceback.format_exc()
            logger.error("Invocation failed: %s", error_detail)
            return {"error": str(exc), "traceback": error_detail}
        finally:
            if mcp_client is not None:
                try:
                    mcp_client.__exit__(None, None, None)
                except Exception:
                    pass

    return app


def _get_local_tools(settings) -> list:
    """Load local @tool functions for the greenhouse agent."""
    from strands.tools import tool

    @tool
    def read_sensors() -> dict:
        """Read current sensor telemetry from all greenhouse zones."""
        from eden.adapters.simulated_sensors import SimulatedSensorAdapter
        adapter = SimulatedSensorAdapter()
        return adapter.read_all()

    @tool
    def set_actuator(device: str, action: str, value: float) -> str:
        """Command a greenhouse actuator (pump, light, fan, heater).

        Args:
            device: Actuator name (e.g. 'pump_alpha', 'light_beta').
            action: Action to take ('on', 'off', 'set').
            value: Numeric value for the action (0.0-1.0 for intensity).
        """
        logger.info("Actuator command: %s %s %.2f", device, action, value)
        return f"OK: {device} {action} {value}"

    @tool
    def get_nutritional_status() -> dict:
        """Check if crop output meets 4 astronauts' dietary needs for 450 days."""
        from eden.domain.nutrition import NutritionModel
        model = NutritionModel()
        return model.get_status()

    return [read_sensors, set_actuator, get_nutritional_status]


def _get_system_prompt(session_id: str) -> str:
    """Return the EDEN agent system prompt."""
    return (
        "You are EDEN, an autonomous AI agent managing a Martian greenhouse. "
        "You monitor temperature, humidity, light, and water across multiple growing zones. "
        "You detect plant stress, manage nutrients and water recycling, and optimize growth. "
        "There is a 22-minute communication delay to Earth — you must act autonomously. "
        "You serve 4 astronauts on a 450-day Mars mission. "
        f"Session: {session_id}"
    )


# ── App creation ──────────────────────────────────────────────────────

try:
    app = _create_app()
except ImportError:
    # If bedrock_agentcore is not installed, create a stub for local dev
    logger.warning("bedrock-agentcore not installed — runtime_entry.py is a no-op locally")
    app = None

if __name__ == "__main__":
    if app is not None:
        app.run()
    else:
        print("ERROR: bedrock-agentcore package required. Install with:")
        print("  pip install bedrock-agentcore")
