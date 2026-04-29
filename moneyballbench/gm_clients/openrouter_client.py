"""
MoneyBall Bench v3.0 — OpenRouter GM client.

Wraps OpenRouter's /chat/completions endpoint (OpenAI-compatible) to match
the GMClient interface. API key via OPENROUTER_API_KEY env var or constructor.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

from moneyballbench.gm_clients.base import GMClient

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0


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
                message = data["choices"][0]["message"]
                content = message.get("content")
                if content is None:
                    # Reasoning models (e.g. Kimi K2.5) put output in reasoning field
                    reasoning = message.get("reasoning", "")
                    if reasoning:
                        content = reasoning
                    else:
                        content = ""
                return content
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 402, 502, 503):
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenRouter %d (attempt %d/%d), retrying in %.1fs",
                        e.code, attempt + 1, MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                    continue
                raise ConnectionError(
                    f"OpenRouter request failed: HTTP Error {e.code}: {e.reason}"
                ) from e
            except urllib.error.URLError as e:
                last_error = e
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "OpenRouter connection error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, MAX_RETRIES, backoff, e,
                )
                time.sleep(backoff)
                continue

        raise ConnectionError(
            f"OpenRouter request failed after {MAX_RETRIES} retries: {last_error}"
        )
