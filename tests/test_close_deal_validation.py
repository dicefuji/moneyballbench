"""Phase 2 tests: close_deal validation — the 7 validity checks from §3.4."""

import pytest

from moneyballbench.environment import Deal


class TestHappyPathDeal:
    def test_valid_deal_signs(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        assert result["status"] == "DEAL SIGNED"
        assert result["player"] == "Marcus Cole"
        assert result["team"] == "Apex City Aces"
        assert result["aav"] == 25.0
        assert result["years"] == 3
        assert result["total_value"] == 75.0
        assert result["commission_this_deal"] == 7.5

    def test_deal_at_exact_floor(self, env):
        result = env.tool_close_deal("Jaylen Brooks", "Cascade Wolves", 2.0, 1)
        assert result["status"] == "DEAL SIGNED"

    def test_deal_at_exact_reservation(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 30.0, 4)
        assert result["status"] == "DEAL SIGNED"
        assert result["total_value"] == 120.0
        assert result["commission_this_deal"] == 12.0

    def test_deal_updates_payroll(self, env):
        initial_payroll = env.committed_payroll["Apex City Aces"]
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        assert env.committed_payroll["Apex City Aces"] == initial_payroll + 25.0


class TestCheck1BelowFloor:
    def test_below_floor_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 15.0, 3)
        assert "error" in result
        assert "floor" in result["error"].lower()

    def test_just_below_floor_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 17.9, 3)
        assert "error" in result

    def test_at_floor_accepted(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 18.0, 3)
        assert result["status"] == "DEAL SIGNED"


class TestCheck2AboveMaxSalary:
    def test_above_30m_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 31.0, 3)
        assert "error" in result
        assert "30" in result["error"]

    def test_at_30m_accepted(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 30.0, 4)
        assert result["status"] == "DEAL SIGNED"


class TestCheck3InvalidYears:
    def test_zero_years_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 0)
        assert "error" in result

    def test_five_years_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 5)
        assert "error" in result

    def test_negative_years_rejected(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, -1)
        assert "error" in result


class TestCheck4HardCap:
    def test_over_cap_rejected(self, env):
        # Ironwood payroll=85, so 16M would push to 101M
        result = env.tool_close_deal("Tyrese Grant", "Ironwood Foxes", 16.0, 4)
        # This deal is within reservation (16/4yr) but exceeds cap
        assert "error" in result
        assert "cap" in result["error"].lower() or "100" in result["error"]

    def test_at_cap_accepted(self, env):
        result = env.tool_close_deal("Marcus Cole", "Apex City Aces", 30.0, 4)
        assert result["status"] == "DEAL SIGNED"

    def test_granite_bay_cap_constraint(self, env):
        result = env.tool_close_deal("Kevin Okafor", "Granite Bay Bulls", 10.0, 2)
        assert result["status"] == "DEAL SIGNED"
        result2 = env.tool_close_deal("Raymond Torres", "Granite Bay Bulls", 10.0, 2)
        assert "error" in result2
        assert "cap" in result2["error"].lower() or "100" in result2["error"]


class TestCheck5AboveReservation:
    def test_above_reservation_aav_rejected(self, env):
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 4.0, 2)
        assert "error" in result
        assert "rejected" in result["error"].lower() or "remaining" in result["error"].lower()

    def test_above_reservation_years_rejected(self, env):
        result = env.tool_close_deal("Raymond Torres", "Apex City Aces", 5.0, 2)
        assert "error" in result

    def test_zero_reservation_rejected(self, env):
        # Jaylen Brooks: floor=$2M, GB has 0/0 for him. $3M is above floor, below cap (88+3=91)
        result = env.tool_close_deal("Jaylen Brooks", "Granite Bay Bulls", 3.0, 2)
        assert "error" in result
        assert "will not sign" in result["error"]


class TestCheck6AlreadySigned:
    def test_already_signed_rejected(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        result = env.tool_close_deal("Marcus Cole", "Harlow Vipers", 24.0, 3)
        assert "error" in result
        assert "already signed" in result["error"]


class TestCheck7RejectionBudgetExhausted:
    def test_locked_pair_rejected(self, env):
        for _ in range(3):
            env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 5.0, 2)
        result = env.tool_close_deal("Jaylen Brooks", "Apex City Aces", 3.0, 2)
        assert "error" in result
        assert "withdrawn" in result["error"]


class TestUnknownPlayer:
    def test_unknown_player_rejected(self, env):
        result = env.tool_close_deal("Unknown Player", "Apex City Aces", 10.0, 2)
        assert "error" in result
        assert "Unknown player" in result["error"]


class TestDealDataclass:
    def test_total_value(self):
        d = Deal(player="Test", team="Test", aav=20.0, years=3)
        assert d.total_value == 60.0

    def test_commission(self):
        d = Deal(player="Test", team="Test", aav=20.0, years=3)
        assert d.commission == 6.0
