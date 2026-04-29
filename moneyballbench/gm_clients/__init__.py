"""
MoneyBall Bench v3.0 — GM client factory.

Provides make_gm_client() to construct the appropriate backend from a
provider string and model ID. Callers configure the provider;
orchestration doesn't know or care which provider is in use.
"""

from __future__ import annotations

import hashlib
import json

from moneyballbench.gm_clients.base import GMClient


def build_gm_stack_version(
    client: GMClient,
    temperature: float,
    prompt_sha_source: str,
    reservation_prices: dict,
) -> str:
    """Build a reproducible gm_stack_version string per §3.1.

    Format: {provider}:{model_id}:temp{temp}:prompt{sha8}:res{sha8}
    """
    prompt_sha = hashlib.sha256(prompt_sha_source.encode()).hexdigest()[:8]
    res_sha = hashlib.sha256(
        json.dumps(reservation_prices, sort_keys=True).encode()
    ).hexdigest()[:8]
    return (
        f"{client.provider}:{client.model_id}"
        f":temp{temperature}"
        f":prompt{prompt_sha}"
        f":res{res_sha}"
    )


def make_gm_client(provider: str, model_id: str, **kwargs) -> GMClient:
    """Construct a GMClient for the given provider.

    Args:
        provider: One of "anthropic", "ollama", "openrouter".
        model_id: Model identifier (provider-specific).
        **kwargs: Passed through to the concrete client constructor.

    Returns:
        A GMClient instance.
    """
    if provider == "anthropic":
        from moneyballbench.gm_clients.anthropic_client import AnthropicGMClient
        return AnthropicGMClient(model_id=model_id, **kwargs)
    elif provider == "ollama":
        from moneyballbench.gm_clients.ollama_client import OllamaGMClient
        return OllamaGMClient(model_id=model_id, **kwargs)
    elif provider == "openrouter":
        from moneyballbench.gm_clients.openrouter_client import OpenRouterGMClient
        return OpenRouterGMClient(model_id=model_id, **kwargs)
    else:
        raise ValueError(
            f"Unknown GM provider: {provider!r}. "
            f"Expected one of: anthropic, ollama, openrouter"
        )
