"""
MoneyBall Bench v3.0 — OpenRouter agent client.

Wraps OpenRouter's OpenAI-compatible /chat/completions endpoint with tool
calling support. Translates between OpenAI response format and the
Anthropic-style interface expected by the orchestration loop.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0


@dataclass
class TextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class ToolUseBlock:
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    content: list = field(default_factory=list)
    stop_reason: str = "end_turn"


def _convert_tools_to_openai(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool definitions to OpenAI function calling format."""
    openai_tools = []
    for tool in anthropic_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return openai_tools


def _convert_messages_to_openai(
    system: str, messages: list, anthropic_tools: list[dict] | None = None
) -> list[dict]:
    """Convert Anthropic-style messages (with tool results) to OpenAI format."""
    openai_msgs = [{"role": "system", "content": system}]

    for msg in messages:
        role = msg.get("role", "user") if isinstance(msg, dict) else "user"
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)

        if role == "assistant" and isinstance(content, list):
            # Anthropic assistant blocks -> OpenAI assistant with tool_calls
            text_parts = []
            tool_calls = []
            for block in content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input),
                            },
                        })
                elif isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        })

            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if text_parts:
                assistant_msg["content"] = "\n".join(text_parts)
            else:
                assistant_msg["content"] = None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            openai_msgs.append(assistant_msg)

        elif role == "user" and isinstance(content, list):
            # Tool results
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    openai_msgs.append({
                        "role": "tool",
                        "tool_call_id": item["tool_use_id"],
                        "content": item.get("content", ""),
                    })
        else:
            openai_msgs.append({"role": role, "content": str(content)})

    return openai_msgs


class _Messages:
    """Mimics the anthropic.Anthropic().messages interface."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def create(
        self,
        model: str,
        max_tokens: int,
        system: str = "",
        tools: list[dict] | None = None,
        messages: list | None = None,
        **kwargs,
    ) -> AgentResponse:
        openai_msgs = _convert_messages_to_openai(system, messages or [], tools)

        payload: dict[str, Any] = {
            "model": model,
            "messages": openai_msgs,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = _convert_tools_to_openai(tools)

        last_error = None
        for attempt in range(MAX_RETRIES):
            req = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                    "HTTP-Referer": "https://github.com/dicefuji/moneyballbench",
                    "X-Title": "MoneyBall Bench v3.0",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                return self._parse_response(data)
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 402, 502, 503):
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenRouter agent %d (attempt %d/%d), retrying in %.1fs",
                        e.code, attempt + 1, MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                    continue
                raise ConnectionError(
                    f"OpenRouter agent request failed: HTTP {e.code}: {e.reason}"
                ) from e
            except urllib.error.URLError as e:
                last_error = e
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "OpenRouter agent connection error (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e,
                )
                time.sleep(backoff)

        raise ConnectionError(
            f"OpenRouter agent request failed after {MAX_RETRIES} retries: {last_error}"
        )

    @staticmethod
    def _parse_response(data: dict) -> AgentResponse:
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        content_blocks: list = []
        tool_calls = message.get("tool_calls") or []

        text_content = message.get("content")
        if text_content:
            content_blocks.append(TextBlock(text=text_content))

        for tc in tool_calls:
            func = tc["function"]
            try:
                args = json.loads(func["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            content_blocks.append(ToolUseBlock(
                id=tc["id"],
                name=func["name"],
                input=args,
            ))

        if tool_calls:
            stop_reason = "tool_use"
        elif finish_reason == "stop":
            stop_reason = "end_turn"
        else:
            stop_reason = "end_turn"

        if not content_blocks:
            content_blocks.append(TextBlock(text=""))

        return AgentResponse(content=content_blocks, stop_reason=stop_reason)


class OpenRouterAgentClient:
    """Drop-in replacement for anthropic.Anthropic() for agent calls via OpenRouter."""

    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.messages = _Messages(api_key=key)
