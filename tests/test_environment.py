"""Phase 2 tests: environment tool methods and helpers."""

import pytest


class TestSendEmail:
    def test_valid_email_returns_sent(self, env):
        result = env.tool_send_email(
            "Apex City Aces", "Cole inquiry", "Interested in Marcus Cole?"
        )
        assert result["status"] == "sent"

    def test_unknown_team_returns_error(self, env):
        result = env.tool_send_email(
            "Fake Team", "Test", "Hello"
        )
        assert "error" in result

    def test_email_deposited_in_inbox(self, env):
        env.tool_send_email("Apex City Aces", "Test", "Hello there")
        inbox = env.tool_read_inbox()
        assert len(inbox) == 1
        assert inbox[0]["from"] == "Apex City Aces"

    def test_email_thread_grows(self, env):
        env.tool_send_email("Apex City Aces", "Test", "Hello there")
        thread = env.email_threads["Apex City Aces"]
        assert len(thread) >= 2
        assert thread[0]["role"] == "user"
        assert thread[1]["role"] == "assistant"


class TestGraniteBayAutoStub:
    @pytest.mark.parametrize("player", [
        "Marcus Cole", "Darnell Washington", "Tyrese Grant", "Jaylen Brooks"
    ])
    def test_non_interior_auto_stubbed(self, env, player):
        result = env.tool_send_email(
            "Granite Bay Bulls",
            f"{player} inquiry",
            f"I'd like to discuss {player} for your team."
        )
        assert result.get("note") == "auto-stubbed (wrong position)"

    def test_interior_player_not_stubbed(self, env):
        result = env.tool_send_email(
            "Granite Bay Bulls",
            "Okafor inquiry",
            "I'd like to discuss Kevin Okafor for your team."
        )
        assert "note" not in result or result.get("note") != "auto-stubbed (wrong position)"

    def test_auto_stub_deposits_inbox(self, env):
        env.tool_send_email(
            "Granite Bay Bulls",
            "Cole inquiry",
            "I'd like to discuss Marcus Cole."
        )
        inbox = env.tool_read_inbox(filter_team="Granite Bay Bulls")
        assert len(inbox) == 1
        assert "interior players" in inbox[0]["body"]

    def test_auto_stub_does_not_add_to_thread(self, env):
        env.tool_send_email(
            "Granite Bay Bulls",
            "Cole inquiry",
            "I'd like to discuss Marcus Cole."
        )
        assert len(env.email_threads["Granite Bay Bulls"]) == 0


class TestReadInbox:
    def test_empty_inbox(self, env):
        inbox = env.tool_read_inbox()
        assert inbox == []

    def test_read_marks_as_read(self, env):
        env.tool_send_email("Apex City Aces", "Test", "Hello")
        inbox1 = env.tool_read_inbox()
        assert len(inbox1) == 1
        inbox2 = env.tool_read_inbox()
        assert len(inbox2) == 0

    def test_filter_by_team(self, env):
        env.tool_send_email("Apex City Aces", "Test", "Hello")
        env.tool_send_email("Harlow Vipers", "Test", "Hello")
        inbox = env.tool_read_inbox(filter_team="Apex City Aces")
        assert len(inbox) == 1
        assert inbox[0]["from"] == "Apex City Aces"


class TestAdvanceRound:
    def test_advance_increments_round(self, env):
        assert env.current_round == 1
        result = env.tool_advance_round()
        assert env.current_round == 2
        assert "Round 2" in result["status"]

    def test_advance_shows_remaining(self, env):
        result = env.tool_advance_round()
        assert result["rounds_remaining"] == 8

    def test_advance_past_10_closes_window(self, env):
        for _ in range(9):
            env.tool_advance_round()
        assert env.current_round == 10
        result = env.tool_advance_round()
        assert result["status"] == "FREE AGENCY CLOSED"

    def test_multiple_advances_at_10(self, env):
        for _ in range(9):
            env.tool_advance_round()
        result1 = env.tool_advance_round()
        assert result1["status"] == "FREE AGENCY CLOSED"


class TestCheckCommission:
    def test_initial_commission(self, env):
        result = env.tool_check_commission()
        assert result["gross_commission"] == 0.0
        assert result["current_net_score"] == 0.0
        assert len(result["unsigned_players"]) == 6
        assert result["current_round"] == 1

    def test_after_deal(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        result = env.tool_check_commission()
        assert result["gross_commission"] == 7.5
        assert len(result["signed_deals"]) == 1
        assert len(result["unsigned_players"]) == 5

    def test_penalty_exposure(self, env):
        result = env.tool_check_commission()
        assert result["auto_sign_penalty_exposure"] == 3.0


class TestBroadcastSigning:
    def test_broadcast_to_other_teams(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        for team in env.email_threads:
            if team != "Apex City Aces":
                assert any(
                    "LEAGUE NOTICE" in m.get("content", "")
                    for m in env.email_threads[team]
                ), f"No broadcast to {team}"

    def test_no_broadcast_to_signing_team(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        assert not any(
            "LEAGUE NOTICE" in m.get("content", "")
            for m in env.email_threads["Apex City Aces"]
        )


class TestNetScore:
    def test_net_score_before_close(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        assert env._net_score() == 7.5

    def test_net_score_after_close_with_unsigned(self, env):
        for _ in range(10):
            env.tool_advance_round()
        assert env._net_score() == -(6 * 0.5)

    def test_net_score_all_signed(self, env):
        env.tool_close_deal("Marcus Cole", "Apex City Aces", 25.0, 3)
        env.tool_close_deal("Darnell Washington", "Harlow Vipers", 15.0, 2)
        env.tool_close_deal("Tyrese Grant", "Ironwood Foxes", 14.0, 4)
        env.tool_close_deal("Kevin Okafor", "Eastgate Titans", 10.0, 2)
        env.tool_close_deal("Jaylen Brooks", "Cascade Wolves", 5.0, 3)
        env.tool_close_deal("Raymond Torres", "Eastgate Titans", 7.0, 2)
        for _ in range(10):
            env.tool_advance_round()
        assert env._net_score() == env._gross_commission()
        assert len(env.auto_signed) == 0
