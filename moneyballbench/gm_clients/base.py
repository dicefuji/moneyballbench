"""
MoneyBall Bench v3.0 — Abstract GM client interface.

All GM backends implement the GMClient protocol: a single `complete` method
that takes a system prompt, message history, temperature, and max_tokens,
and returns the GM's text response as a string.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class GMClient(ABC):
    """Duck-typed base class for GM backends."""

    provider: str
    model_id: str

    @abstractmethod
    def complete(
        self,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return the GM's text response given a system prompt and message history."""
        ...
