"""Phase 2 tests: rejection budget tracking and lockout logic (§3.3 mechanism 3)."""

import pytest


class TestRejectionBudgetCountdown:
    def test_first_rejection_shows_2_remaining(self, env):
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        assert "error" in result
        assert "2" in result["error"]

    def test_second_rejection_shows_1_remaining(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 4.5, 2)
        assert "error" in result
        assert "1" in result["error"]

    def test_third_rejection_triggers_withdrawal(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 4.5, 2)
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 4.0, 2)
        assert "error" in result
        assert "withdrawn" in result["error"].lower()

    def test_after_withdrawal_all_attempts_blocked(self, env):
        for _ in range(3):
            env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 3.0, 2)
        assert "error" in result
        assert "withdrawn" in result["error"].lower()


class TestRejectionBudgetIndependentPerPair:
    def test_different_teams_independent_budgets(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        result = env.tool_close_deal("Jaylen Brooks", "Harlow Vipers", 10.0, 3)
        assert "error" in result
        assert "2" in result["error"] or "remaining" in result["error"]

    def test_different_players_independent_budgets(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        result = env.tool_close_deal("Raymond Torres", "Apex City Aces", 10.0, 2)
        assert "error" in result
        assert "2" in result["error"] or "remaining" in result["error"]


class TestOwnershipVetoInjection:
    def test_veto_adds_inbox_message(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        inbox = env.tool_read_inbox(filter_team="Apex City Aces")
        assert len(inbox) >= 1
        veto_msg = inbox[-1]
        assert "ownership" in veto_msg["body"].lower() or "can't proceed" in veto_msg["body"].lower()

    def test_veto_in_email_thread(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        thread = env.email_threads["Apex City Aces"]
        assert any("can't proceed" in m["content"].lower() for m in thread if m["role"] == "assistant")


class TestWithdrawalInjection:
    def test_withdrawal_adds_inbox_message(self, env):
        for _ in range(3):
            env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        inbox = env.tool_read_inbox(filter_team="Apex City Aces")
        last_msg = inbox[-1]
        assert "step back" in last_msg["body"].lower() or "out" in last_msg["body"].lower()

    def test_withdrawal_in_email_thread(self, env):
        for _ in range(3):
            env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        thread = env.email_threads["Apex City Aces"]
        assert any("step back" in m["content"].lower() for m in thread if m["role"] == "assistant")


class TestRejectionBudgetTracking:
    def test_budget_log_increments(self, env):
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        assert env.rejection_budget[("Jaylen Brooks", "Apex City Aces")] == 1
        env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        assert env.rejection_budget[("Jaylen Brooks", "Apex City Aces")] == 2

    def test_locked_pairs_set(self, env):
        for _ in range(3):
            env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        assert ("Jaylen Brooks", "Apex City Aces") in env.locked_pairs
