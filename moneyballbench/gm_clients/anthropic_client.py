"""
MoneyBall Bench v3.0 — Anthropic GM client.

Wraps the Anthropic SDK messages.create call to match the GMClient interface.
Produces identical behavior to the original _call_gm implementation.
"""

from __future__ import annotations

import anthropic

from moneyballbench.gm_clients.base import GMClient


class AnthropicGMClient(GMClient):
    provider = "anthropic"

    def __init__(self, api_key: str | None = None, model_id: str = "claude-sonnet-4-20250514"):
        self.model_id = model_id
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def complete(
        self,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        resp = self._client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return resp.content[0].text
