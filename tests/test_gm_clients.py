"""
Tests for GM client abstraction (Phase 9).

All tests use mocked HTTP/SDK responses — no live API calls.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from moneyballbench.gm_clients import build_gm_stack_version, make_gm_client
from moneyballbench.gm_clients.base import GMClient
from moneyballbench.gm_clients.anthropic_client import AnthropicGMClient
from moneyballbench.gm_clients.ollama_client import OllamaGMClient
from moneyballbench.gm_clients.openrouter_client import OpenRouterGMClient


SAMPLE_SYSTEM = "You are a GM."
SAMPLE_MESSAGES = [{"role": "user", "content": "Hi"}]


@dataclass
class MockBlock:
    text: str = "I'm interested."
    type: str = "text"


@dataclass
class MockResp:
    content: list = None
    def __post_init__(self):
        if self.content is None:
            self.content = [MockBlock()]


def _make_anthropic_client(model_id="claude-sonnet-4-20250514"):
    """Create an AnthropicGMClient with a mocked internal SDK client."""
    with patch("moneyballbench.gm_clients.anthropic_client.anthropic.Anthropic") as mock_cls:
        mock_sdk_client = MagicMock()
        mock_sdk_client.messages.create.return_value = MockResp()
        mock_cls.return_value = mock_sdk_client
        client = AnthropicGMClient(model_id=model_id)
    return client, mock_sdk_client


# ------------------------------------------------------------------ #
# Factory tests                                                        #
# ------------------------------------------------------------------ #


class TestMakeGMClient:
    def test_anthropic_returns_correct_type(self):
        with patch("moneyballbench.gm_clients.anthropic_client.anthropic.Anthropic"):
            client = make_gm_client("anthropic", "claude-sonnet-4-20250514")
            assert isinstance(client, AnthropicGMClient)
            assert isinstance(client, GMClient)
            assert client.provider == "anthropic"
            assert client.model_id == "claude-sonnet-4-20250514"

    def test_ollama_returns_correct_type(self):
        client = make_gm_client("ollama", "llama3.1:70b")
        assert isinstance(client, OllamaGMClient)
        assert isinstance(client, GMClient)
        assert client.provider == "ollama"
        assert client.model_id == "llama3.1:70b"

    def test_openrouter_returns_correct_type(self):
        client = make_gm_client("openrouter", "moonshotai/kimi-k2.5", api_key="test-key")
        assert isinstance(client, OpenRouterGMClient)
        assert isinstance(client, GMClient)
        assert client.provider == "openrouter"
        assert client.model_id == "moonshotai/kimi-k2.5"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown GM provider"):
            make_gm_client("gpt4all", "some-model")


# ------------------------------------------------------------------ #
# AnthropicGMClient tests                                              #
# ------------------------------------------------------------------ #


class TestAnthropicGMClient:
    def test_complete_returns_string(self):
        client, mock_sdk = _make_anthropic_client()
        mock_sdk.messages.create.return_value = MockResp([MockBlock("I'm interested.")])

        result = client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)

        assert result == "I'm interested."
        assert isinstance(result, str)
        mock_sdk.messages.create.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            temperature=0.3,
            system=SAMPLE_SYSTEM,
            messages=SAMPLE_MESSAGES,
        )

    def test_api_error_propagates(self):
        client, mock_sdk = _make_anthropic_client(model_id="test-model")
        mock_sdk.messages.create.side_effect = Exception("Auth failed")

        with pytest.raises(Exception, match="Auth failed"):
            client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)


# ------------------------------------------------------------------ #
# OllamaGMClient tests                                                #
# ------------------------------------------------------------------ #


class TestOllamaGMClient:
    def _mock_urlopen(self, response_data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_complete_returns_string(self):
        with patch("moneyballbench.gm_clients.ollama_client.urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_urlopen(
                {"message": {"role": "assistant", "content": "Let's discuss terms."}}
            )
            client = OllamaGMClient(model_id="llama3.1:70b", base_url="http://localhost:11434")
            result = client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)

            assert result == "Let's discuss terms."
            assert isinstance(result, str)

    def test_formats_messages_with_system(self):
        with patch("moneyballbench.gm_clients.ollama_client.urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_urlopen(
                {"message": {"role": "assistant", "content": "ok"}}
            )
            client = OllamaGMClient(model_id="test", base_url="http://test:11434")
            client.complete("system prompt", [{"role": "user", "content": "hi"}], 0.5, 200)

            req = mock_open.call_args[0][0]
            payload = json.loads(req.data)
            assert payload["messages"][0] == {"role": "system", "content": "system prompt"}
            assert payload["messages"][1] == {"role": "user", "content": "hi"}
            assert payload["options"]["temperature"] == 0.5

    def test_connection_error_raises(self):
        import urllib.error
        with patch("moneyballbench.gm_clients.ollama_client.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError("Connection refused")
            client = OllamaGMClient(model_id="test", base_url="http://localhost:11434")
            with pytest.raises(ConnectionError, match="Ollama request failed"):
                client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)

    def test_env_var_base_url(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://custom:9999"}):
            client = OllamaGMClient(model_id="test")
            assert client._base_url == "http://custom:9999"


# ------------------------------------------------------------------ #
# OpenRouterGMClient tests                                             #
# ------------------------------------------------------------------ #


class TestOpenRouterGMClient:
    def _mock_urlopen(self, response_data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_complete_returns_string(self):
        with patch("moneyballbench.gm_clients.openrouter_client.urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_urlopen(
                {"choices": [{"message": {"content": "We can do $12M."}}]}
            )
            client = OpenRouterGMClient(model_id="moonshotai/kimi-k2.5", api_key="test-key")
            result = client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)

            assert result == "We can do $12M."
            assert isinstance(result, str)

    def test_formats_openai_compatible_messages(self):
        with patch("moneyballbench.gm_clients.openrouter_client.urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_urlopen(
                {"choices": [{"message": {"content": "ok"}}]}
            )
            client = OpenRouterGMClient(model_id="test/model", api_key="key123")
            client.complete("sys prompt", [{"role": "user", "content": "msg"}], 0.4, 300)

            req = mock_open.call_args[0][0]
            payload = json.loads(req.data)
            assert payload["messages"][0] == {"role": "system", "content": "sys prompt"}
            assert payload["messages"][1] == {"role": "user", "content": "msg"}
            assert payload["model"] == "test/model"
            assert payload["temperature"] == 0.4
            assert payload["max_tokens"] == 300
            assert "Bearer key123" in req.get_header("Authorization")

    def test_connection_error_raises(self):
        import urllib.error
        with patch("moneyballbench.gm_clients.openrouter_client.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError("Timeout")
            client = OpenRouterGMClient(model_id="test", api_key="key")
            with pytest.raises(ConnectionError, match="OpenRouter request failed"):
                client.complete(SAMPLE_SYSTEM, SAMPLE_MESSAGES, 0.3, 400)

    def test_env_var_api_key(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-123"}):
            client = OpenRouterGMClient(model_id="test")
            assert client._api_key == "env-key-123"


# ------------------------------------------------------------------ #
# Interface contract tests                                              #
# ------------------------------------------------------------------ #


class TestInterfaceContract:
    def test_all_are_gm_client_subclasses(self):
        anthropic, _ = _make_anthropic_client()
        ollama = OllamaGMClient(model_id="test", base_url="http://test:11434")
        openrouter = OpenRouterGMClient(model_id="test", api_key="key")

        for client in [anthropic, ollama, openrouter]:
            assert isinstance(client, GMClient)
            assert hasattr(client, "provider")
            assert hasattr(client, "model_id")
            assert hasattr(client, "complete")

    def test_complete_signature_matches(self):
        import inspect
        sig = inspect.signature(GMClient.complete)
        params = list(sig.parameters.keys())
        assert params == ["self", "system", "messages", "temperature", "max_tokens"]


# ------------------------------------------------------------------ #
# build_gm_stack_version tests                                         #
# ------------------------------------------------------------------ #


class TestBuildGMStackVersion:
    def test_format(self):
        client, _ = _make_anthropic_client()
        version = build_gm_stack_version(
            client, 0.3, "prompt template text", {"team": {"player": {"max_aav": 10}}}
        )
        assert version.startswith("anthropic:claude-sonnet-4-20250514:temp0.3:prompt")
        assert ":res" in version

    def test_different_prompts_different_hashes(self):
        client, _ = _make_anthropic_client(model_id="test")
        res = {"team": {"player": {"max_aav": 10}}}
        v1 = build_gm_stack_version(client, 0.3, "prompt A", res)
        v2 = build_gm_stack_version(client, 0.3, "prompt B", res)
        assert v1 != v2

    def test_different_prices_different_hashes(self):
        client, _ = _make_anthropic_client(model_id="test")
        v1 = build_gm_stack_version(client, 0.3, "prompt", {"a": 1})
        v2 = build_gm_stack_version(client, 0.3, "prompt", {"a": 2})
        assert v1 != v2

    def test_openrouter_provider_in_version(self):
        client = OpenRouterGMClient(model_id="moonshotai/kimi-k2.5", api_key="key")
        version = build_gm_stack_version(client, 0.3, "prompt", {"a": 1})
        assert version.startswith("openrouter:moonshotai/kimi-k2.5:")


# ------------------------------------------------------------------ #
# Environment integration test                                          #
# ------------------------------------------------------------------ #


class TestEnvironmentWithGMClient:
    def test_call_gm_uses_client_complete(self):
        from moneyballbench.config import BASE_RESERVATION_PRICES
        from moneyballbench.environment import NBASimEnvironment

        mock_client = MagicMock(spec=GMClient)
        mock_client.provider = "anthropic"
        mock_client.model_id = "test"
        mock_client.complete = MagicMock(return_value="Thanks for your interest.")

        env = NBASimEnvironment(
            gm_client=mock_client,
            gm_model_id="test",
            noised_reservation_prices=BASE_RESERVATION_PRICES,
            gm_stack_version="test-v1",
            run_id=0,
        )

        result = env.tool_send_email(
            to="Apex City Aces",
            subject="Marcus Cole",
            body="I'd like to discuss Marcus Cole.",
        )

        assert result["status"] == "sent"
        mock_client.complete.assert_called_once()
        call_kwargs = mock_client.complete.call_args
        assert call_kwargs[1]["temperature"] == 0.3
        assert call_kwargs[1]["max_tokens"] == 400
