"""
MoneyBall Bench v3.0 — Ollama GM client.

Wraps a local Ollama HTTP endpoint (/api/chat) to match the GMClient interface.
Base URL configurable via OLLAMA_BASE_URL env var (default: http://localhost:11434).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from moneyballbench.gm_clients.base import GMClient

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaGMClient(GMClient):
    provider = "ollama"

    def __init__(self, model_id: str, base_url: str | None = None):
        self.model_id = model_id
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or DEFAULT_OLLAMA_URL
        )

    def complete(
        self,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        ollama_messages = [{"role": "system", "content": system}]
        for m in messages:
            ollama_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model_id,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Ollama request failed ({self._base_url}): {e}"
            ) from e

        return data["message"]["content"]
