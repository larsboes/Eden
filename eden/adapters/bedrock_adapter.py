"""Bedrock LLM adapter (Tier 2) — implements ModelPort."""

from __future__ import annotations

import json
import structlog
import time

import boto3
from botocore.config import Config

logger = structlog.get_logger(__name__)

_CACHE_TTL = 60  # seconds to cache unavailability
_BOTO_CONFIG = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={"max_attempts": 1},
    max_pool_connections=50,
)


class BedrockAdapter:
    """Tier 2 cloud LLM via AWS Bedrock Converse API."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-6",
        region: str = "us-west-2",
        max_tokens: int = 512,
    ):
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._client = boto3.client(
            "bedrock-runtime", region_name=region, config=_BOTO_CONFIG,
        )
        self._last_check_time: float = 0
        self._last_available: bool = False

    # ── ModelPort ────────────────────────────────────────────────────

    def reason(self, prompt: str, context: dict) -> str:
        try:
            system_text = json.dumps(context) if context else "No additional context."
            resp = self._client.converse(
                modelId=self._model_id,
                system=[{"text": system_text}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self._max_tokens},
            )
            return resp["output"]["message"]["content"][0]["text"]
        except Exception:
            logger.exception("Bedrock reason() failed")
            return ""

    def is_available(self) -> bool:
        now = time.time()
        if (now - self._last_check_time) < _CACHE_TTL:
            return self._last_available

        available = self._check_available()
        self._last_check_time = now
        self._last_available = available
        return available

    # ── Internal ─────────────────────────────────────────────────────

    def _check_available(self) -> bool:
        try:
            self._client.converse(
                modelId=self._model_id,
                messages=[{"role": "user", "content": [{"text": "ping"}]}],
                inferenceConfig={"maxTokens": 1},
            )
            return True
        except Exception:
            logger.debug("Bedrock health check failed")
            return False
