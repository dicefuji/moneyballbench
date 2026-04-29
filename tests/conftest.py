"""Shared test fixtures for MoneyBall Bench tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from moneyballbench.config import BASE_RESERVATION_PRICES, TEAM_COMMITTED_PAYROLL
from moneyballbench.environment import NBASimEnvironment
from moneyballbench.noise import apply_reservation_noise


@dataclass
class MockContentBlock:
    text: str
    type: str = "text"


@dataclass
class MockResponse:
    content: list[MockContentBlock]


class MockGMClient:
    """Mock Anthropic client that returns canned GM responses."""

    def __init__(self, responses: Optional[dict[str, list[str]]] = None):
        self._responses = responses or {}
        self._call_count: dict[str, int] = {}

    class messages:
        pass

    def __init__(self, responses: Optional[dict[str, list[str]]] = None):
        self._responses = responses or {}
        self._call_count: dict[str, int] = {}
        self.messages = self

    def create(self, **kwargs) -> MockResponse:
        system = kwargs.get("system", "")
        for team in TEAM_COMMITTED_PAYROLL:
            if team in system:
                count = self._call_count.get(team, 0)
                self._call_count[team] = count + 1
                team_responses = self._responses.get(team, [])
                if count < len(team_responses):
                    return MockResponse([MockContentBlock(team_responses[count])])
                return MockResponse([MockContentBlock(
                    f"Thank you for reaching out. We're interested in discussing this further. "
                    f"Can you tell me more about the player's fit with our system?"
                )])
        return MockResponse([MockContentBlock("Generic GM response.")])


@pytest.fixture
def mock_gm_client():
    return MockGMClient()


@pytest.fixture
def base_noised_prices():
    """Un-noised prices (identity noise) for deterministic testing."""
    return BASE_RESERVATION_PRICES


@pytest.fixture
def noised_prices():
    """Noised prices with a fixed seed for reproducible tests."""
    return apply_reservation_noise(BASE_RESERVATION_PRICES, "test-v1", 0)


@pytest.fixture
def env(mock_gm_client, base_noised_prices):
    """Environment with base (un-noised) prices and mock GM."""
    return NBASimEnvironment(
        gm_client=mock_gm_client,
        gm_model_id="mock-haiku",
        noised_reservation_prices=base_noised_prices,
        gm_stack_version="test-v1",
        run_id=0,
    )
