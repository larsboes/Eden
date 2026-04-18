"""Ollama local LLM adapter (Tier 1) — implements ModelPort."""

from __future__ import annotations

import json
import structlog

import requests

logger = structlog.get_logger(__name__)


class OllamaAdapter:
    """Tier 1 local LLM via Ollama REST API."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
    ):
        self._host = host.rstrip("/")
        self._model = model

    # ── ModelPort ────────────────────────────────────────────────────

    def reason(self, prompt: str, context: dict) -> str:
        try:
            system_text = json.dumps(context) if context else ""
            full_prompt = f"{system_text}\n\n{prompt}" if system_text else prompt
            resp = requests.post(
                f"{self._host}/api/generate",
                json={"model": self._model, "prompt": full_prompt, "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception:
            logger.exception("Ollama reason() failed")
            return ""

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self._host}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
