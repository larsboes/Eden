"""EDEN configuration — loads from environment variables / .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if it exists
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Runtime settings populated from environment variables."""

    def __init__(self) -> None:
        self.MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.EDEN_SIMULATE: bool = os.getenv("EDEN_SIMULATE", "true").lower() == "true"
        self.AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")
        self.DYNAMO_TABLE_PREFIX: str = os.getenv("DYNAMO_TABLE_PREFIX", "eden")
        self.OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.RECONCILE_INTERVAL_SECONDS: int = int(
            os.getenv("RECONCILE_INTERVAL_SECONDS", "30")
        )
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        # Syngenta MCP Knowledge Base
        self.SYNGENTA_MCP_GATEWAY_URL: str = os.getenv(
            "SYNGENTA_MCP_GATEWAY_URL",
            "https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp",
        )
        self.SYNGENTA_MCP_AUTH_TOKEN: str | None = os.getenv("SYNGENTA_MCP_AUTH_TOKEN")

        # NASA MCP server (stdio subprocess)
        self.NASA_API_KEY: str = os.getenv("NASA_API_KEY", "DEMO_KEY")
        self.NASA_MCP_COMMAND: str = os.getenv("NASA_MCP_COMMAND", "npx")
        self.NASA_MCP_ARGS: str = os.getenv(
            "NASA_MCP_ARGS", "-y,@programcomputer/nasa-mcp-server@latest"
        )

        # Hardware (Pi sensor API)
        self.HARDWARE_API_URL: str = os.getenv("HARDWARE_API_URL", "http://127.0.0.1:8001")
        self.HARDWARE_ZONE_ID: str = os.getenv("HARDWARE_ZONE_ID", "zone1")
        self.HARDWARE_POLL_INTERVAL: float = float(os.getenv("HARDWARE_POLL_INTERVAL", "10"))

        # AgentCore Gateway + Runtime (set after deploy-agentcore.sh)
        self.AGENTCORE_GATEWAY_ID: str = os.getenv("AGENTCORE_GATEWAY_ID", "")
        self.AGENTCORE_GATEWAY_ENDPOINT: str = os.getenv("AGENTCORE_GATEWAY_ENDPOINT", "")
        self.AGENTCORE_RUNTIME_ENDPOINT: str = os.getenv("AGENTCORE_RUNTIME_ENDPOINT", "")
