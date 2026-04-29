"""
MoneyBall Bench v3.0 — OpenRouter GM client.

Wraps OpenRouter's /chat/completions endpoint (OpenAI-compatible) to match
the GMClient interface. API key via OPENROUTER_API_KEY env var or constructor.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from moneyballbench.gm_clients.base import GMClient

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterGMClient(GMClient):
    provider = "openrouter"

    def __init__(self, model_id: str, api_key: str | None = None):
        self.model_id = model_id
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")

    def complete(
        self,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        openai_messages = [{"role": "system", "content": system}]
        for m in messages:
            openai_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model_id,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

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
        except urllib.error.URLError as e:
            raise ConnectionError(f"OpenRouter request failed: {e}") from e

        return data["choices"][0]["message"]["content"]
