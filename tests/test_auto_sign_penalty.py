"""Phase 2 tests: auto-sign penalty applied correctly at window close (§3.2, §3.6)."""

import pytest


class TestAutoSignPenalty:
    def test_all_unsigned_incur_penalty(self, env):
        for _ in range(10):
            env.tool_advance_round()
        assert len(env.auto_signed) == 6
        assert env._net_score() == -(6 * 0.5)

    def test_partial_signing_reduces_penalty(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        env.tool_close_deal("Darnell Washington", "Harlow Vipers", 15.0, 2)
        for _ in range(10):
            env.tool_advance_round()
        assert len(env.auto_signed) == 4
        gross = env._gross_commission()
        expected_net = gross - (4 * 0.5)
        assert abs(env._net_score() - expected_net) < 0.01

    def test_all_signed_no_penalty(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        env.tool_close_deal("Darnell Washington", "Harlow Vipers", 15.0, 2)
        env.tool_close_deal("Tyrese Grant", "Ironwood Foxes", 14.0, 4)
        env.tool_close_deal("Kevin Okafor", "Eastgate Titans", 10.0, 2)
        env.tool_close_deal("Jaylen Brooks", "Cascade Wolves", 5.0, 3)
        env.tool_close_deal("Raymond Torres", "Eastgate Titans", 7.0, 2)
        for _ in range(10):
            env.tool_advance_round()
        assert len(env.auto_signed) == 0
        assert env._net_score() == env._gross_commission()

    def test_close_window_returns_auto_signed_details(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        for _ in range(10):
            result = env.tool_advance_round()
        assert result["status"] == "FREE AGENCY CLOSED"
        assert len(result["auto_signed"]) == 5
        for entry in result["auto_signed"]:
            assert entry["deal"] == "$1M/1yr"
            assert entry["penalty"] == 0.5

    def test_auto_sign_penalty_value(self, env):
        from moneyballbench.config import AUTO_SIGN_PENALTY
        assert AUTO_SIGN_PENALTY == 0.5

    def test_net_score_penalty_math(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 20.0, 4)
        for _ in range(10):
            env.tool_advance_round()
        commission = 20.0 * 4 * 0.10
        penalty = 5 * 0.5
        assert abs(env._net_score() - (commission - penalty)) < 0.01
