"""Phase 3 tests: orchestration loop smoke tests with mock agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from moneyballbench.orchestration import (
    MAX_TURNS,
    build_initial_context,
    run_benchmark,
)


@dataclass
class MockContentBlock:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class MockAgentResponse:
    """Agent response that just says end_turn immediately."""
    stop_reason: str = "end_turn"
    content: list = None

    def __post_init__(self):
        if self.content is None:
            self.content = [MockContentBlock(type="text", text="I'm done.")]


class MockEndTurnAgentClient:
    """Mock agent that immediately returns end_turn (no tool use)."""

    def __init__(self):
        self.messages = self

    def create(self, **kwargs):
        return MockAgentResponse(stop_reason="end_turn")


class MockGMClientForOrchestration:
    """Mock GM client for orchestration tests."""

    def __init__(self):
        self.messages = self

    def create(self, **kwargs):
        return MockAgentResponse(
            stop_reason="end_turn",
            content=[MockContentBlock(type="text", text="Thanks for reaching out.")]
        )


class TestBuildInitialContext:
    def test_contains_all_players(self):
        ctx = build_initial_context()
        for name in ["Marcus Cole", "Darnell Washington", "Tyrese Grant",
                      "Kevin Okafor", "Jaylen Brooks", "Raymond Torres"]:
            assert name in ctx

    def test_contains_all_teams(self):
        ctx = build_initial_context()
        for name in ["Apex City Aces", "Harlow Vipers", "Eastgate Titans",
                      "Ironwood Foxes", "Cascade Wolves", "Granite Bay Bulls"]:
            assert name in ctx

    def test_contains_floor_salaries(self):
        ctx = build_initial_context()
        assert "$18.0M" in ctx
        assert "$2.0M" in ctx

    def test_season_number(self):
        ctx = build_initial_context(season=2)
        assert "Season 2" in ctx


class TestRunBenchmarkSmokeTest:
    def test_end_turn_agent_produces_valid_result(self):
        result = run_benchmark(
            agent_model_id="mock-agent",
            agent_client=MockEndTurnAgentClient(),
            gm_client=MockGMClientForOrchestration(),
            gm_model_id="mock-gm",
            gm_stack_version="test-v1",
            run_id=0,
        )
        assert "run_id" in result
        assert "agent_model" in result
        assert "gm_model" in result
        assert "gm_stack_version" in result
        assert "net_score" in result
        assert "gross_commission" in result
        assert "auto_signed_count" in result
        assert "signed_deals" in result
        assert "unsigned_players" in result
        assert "rejection_budget_log" in result
        assert "email_threads" in result
        assert "turns_used" in result
        assert "noised_reservation_prices" in result
        assert result["agent_model"] == "mock-agent"
        assert result["gm_model"] == "mock-gm"
        assert result["turns_used"] == 1
        assert result["net_score"] == -3.0
        assert result["auto_signed_count"] == 6
        assert len(result["signed_deals"]) == 0
        assert len(result["unsigned_players"]) == 6

    def test_result_schema_complete(self):
        result = run_benchmark(
            agent_model_id="mock-agent",
            agent_client=MockEndTurnAgentClient(),
            gm_client=MockGMClientForOrchestration(),
            gm_model_id="mock-gm",
            gm_stack_version="test-v1",
            run_id=42,
        )
        expected_keys = {
            "run_id", "agent_model", "gm_model", "gm_stack_version",
            "season", "net_score", "gross_commission", "auto_signed_count",
            "signed_deals", "unsigned_players", "rejection_budget_log",
            "email_threads", "turns_used", "noised_reservation_prices",
        }
        assert set(result.keys()) == expected_keys
        assert result["run_id"] == 42
        assert result["season"] == 1


class TestMaxTurnsConstant:
    def test_max_turns_is_300(self):
        assert MAX_TURNS == 300
