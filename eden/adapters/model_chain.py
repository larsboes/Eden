"""Tiered model fallback chain — implements ModelPort."""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eden.domain.ports import ModelPort

logger = structlog.get_logger(__name__)


class ModelChain:
    """Try models in priority order. First available wins.

    Usage: ModelChain([BedrockAdapter(), OllamaAdapter()])
    """

    def __init__(self, models: list[ModelPort]):
        self._models = models

    def reason(self, prompt: str, context: dict) -> str | None:
        for model in self._models:
            if not model.is_available():
                continue
            try:
                return model.reason(prompt, context)
            except Exception:
                logger.exception("Model %s failed during reason(), trying next", type(model).__name__)
                continue
        return None

    def is_available(self) -> bool:
        return any(m.is_available() for m in self._models)
