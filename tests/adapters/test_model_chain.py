"""Tests for model chain — Bedrock, Ollama, and tiered fallback."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from eden.adapters.bedrock_adapter import BedrockAdapter
from eden.adapters.model_chain import ModelChain
from eden.adapters.ollama_adapter import OllamaAdapter


# ── Mock ModelPort ───────────────────────────────────────────────────────


class MockModel:
    """Fake ModelPort for unit tests."""

    def __init__(self, available: bool, response: str = "ok"):
        self._available = available
        self._response = response
        self.reason_called = False

    def reason(self, prompt: str, context: dict) -> str:
        self.reason_called = True
        return self._response

    def is_available(self) -> bool:
        return self._available


# ── ModelChain tests ─────────────────────────────────────────────────────


class TestModelChain:
    def test_uses_first_model_when_available(self):
        m1 = MockModel(available=True, response="from-first")
        m2 = MockModel(available=True, response="from-second")
        chain = ModelChain([m1, m2])

        result = chain.reason("test", {})

        assert result == "from-first"
        assert m1.reason_called
        assert not m2.reason_called

    def test_falls_back_to_second_when_first_down(self):
        m1 = MockModel(available=False)
        m2 = MockModel(available=True, response="from-second")
        chain = ModelChain([m1, m2])

        result = chain.reason("test", {})

        assert result == "from-second"
        assert not m1.reason_called
        assert m2.reason_called

    def test_returns_none_when_all_down(self):
        m1 = MockModel(available=False)
        m2 = MockModel(available=False)
        chain = ModelChain([m1, m2])

        result = chain.reason("test", {})

        assert result is None

    def test_is_available_true_when_any_available(self):
        m1 = MockModel(available=False)
        m2 = MockModel(available=True)
        chain = ModelChain([m1, m2])

        assert chain.is_available() is True

    def test_is_available_false_when_none_available(self):
        m1 = MockModel(available=False)
        m2 = MockModel(available=False)
        chain = ModelChain([m1, m2])

        assert chain.is_available() is False

    def test_handles_reason_exception_gracefully(self):
        """If a model says it's available but reason() throws, skip to next."""
        m1 = MockModel(available=True)
        m1.reason = MagicMock(side_effect=Exception("boom"))
        m2 = MockModel(available=True, response="fallback")
        chain = ModelChain([m1, m2])

        result = chain.reason("test", {})

        assert result == "fallback"


# ── BedrockAdapter tests ────────────────────────────────────────────────


class TestBedrockAdapter:
    def test_caches_unavailability_for_60s(self):
        adapter = BedrockAdapter()
        with patch.object(adapter, "_check_available", return_value=False):
            assert adapter.is_available() is False
            # Second call within 60s should use cache, not call _check_available again
            adapter._check_available = MagicMock(side_effect=AssertionError("should not be called"))
            assert adapter.is_available() is False

    def test_rechecks_after_cache_expires(self):
        adapter = BedrockAdapter()
        with patch.object(adapter, "_check_available", return_value=False):
            adapter.is_available()

        # Expire the cache
        adapter._last_check_time = time.time() - 61

        with patch.object(adapter, "_check_available", return_value=True):
            assert adapter.is_available() is True

    @patch("boto3.client")
    def test_reason_returns_response(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "hello from bedrock"}]}}
        }

        adapter = BedrockAdapter()
        adapter._client = mock_client
        result = adapter.reason("test prompt", {"zone": "alpha"})

        assert result == "hello from bedrock"

    @patch("boto3.client")
    def test_reason_returns_empty_on_error(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.converse.side_effect = Exception("connection refused")

        adapter = BedrockAdapter()
        adapter._client = mock_client
        result = adapter.reason("test", {})

        assert result == ""


# ── OllamaAdapter tests ─────────────────────────────────────────────────


class TestOllamaAdapter:
    @patch("requests.get")
    def test_is_available_true(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        adapter = OllamaAdapter()

        assert adapter.is_available() is True

    @patch("requests.get")
    def test_is_available_false_on_connection_error(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        adapter = OllamaAdapter()

        assert adapter.is_available() is False

    @patch("requests.post")
    def test_reason_returns_response(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "hello from ollama"},
        )
        adapter = OllamaAdapter()
        result = adapter.reason("test prompt", {"zone": "alpha"})

        assert result == "hello from ollama"

    @patch("requests.post")
    def test_reason_returns_empty_on_error(self, mock_post):
        mock_post.side_effect = Exception("connection refused")
        adapter = OllamaAdapter()
        result = adapter.reason("test", {})

        assert result == ""
