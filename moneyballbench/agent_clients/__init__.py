"""
MoneyBall Bench v3.0 — Agent client abstractions.

Provides a unified interface for agent models across providers.
The orchestration loop expects an object with:
    agent_client.messages.create(model, max_tokens, system, tools, messages) -> resp
where resp has .stop_reason, .content (list of blocks).
"""

from __future__ import annotations

from moneyballbench.agent_clients.openrouter_agent import OpenRouterAgentClient


def make_agent_client(provider: str, **kwargs):
    """Factory for agent clients.

    Args:
        provider: "anthropic" or "openrouter"
    """
    if provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(**kwargs)
    elif provider == "openrouter":
        return OpenRouterAgentClient(**kwargs)
    else:
        raise ValueError(f"Unknown agent provider: {provider}")
