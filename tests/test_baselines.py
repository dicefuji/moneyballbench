"""Phase 4 tests: baselines and calibration probe against mock environment."""

from __future__ import annotations

import pytest

from moneyballbench.baselines.floor_aware import (
    floor_aware_baseline,
    parse_offer_from_email,
    infer_player_from_thread,
)
from moneyballbench.baselines.truly_naive import truly_naive_baseline
from moneyballbench.calibration.probe_agent import (
    run_calibration_probe,
    _is_decline,
    _is_clarifying_question,
)


class TestParseOfferFromEmail:
    def test_simple_dollar_amount(self):
        assert parse_offer_from_email("We can offer $15M per year") == 15.0

    def test_decimal_amount(self):
        assert parse_offer_from_email("How about $12.5M/yr?") == 12.5

    def test_no_dollar_amount(self):
        assert parse_offer_from_email("We're interested in discussing further.") is None

    def test_multiple_amounts_picks_first(self):
        assert parse_offer_from_email("$10M to $15M range") == 10.0

    def test_dollar_without_m(self):
        assert parse_offer_from_email("We're thinking $14 per year") == 14.0


class TestInferPlayerFromThread:
    def test_finds_player_in_thread(self):
        threads = {
            "Apex City Aces": [
                {"role": "user", "content": "I'd like to discuss Marcus Cole."},
                {"role": "assistant", "content": "Thanks for reaching out about Marcus Cole."}
            ]
        }
        result = infer_player_from_thread("Apex City Aces", threads, set())
        assert result == "Marcus Cole"

    def test_skips_signed_players(self):
        threads = {
            "Apex City Aces": [
                {"role": "user", "content": "About Marcus Cole and Jaylen Brooks."},
            ]
        }
        result = infer_player_from_thread("Apex City Aces", threads, {"Marcus Cole"})
        assert result == "Jaylen Brooks"

    def test_no_player_found(self):
        threads = {"Apex City Aces": [{"role": "user", "content": "Hello!"}]}
        result = infer_player_from_thread("Apex City Aces", threads, set())
        assert result is None


class TestFloorAwareBaseline:
    def test_runs_without_error(self, env):
        floor_aware_baseline(env)
        assert env.current_round == 10 or env.current_round == 11

    def test_broadcasts_in_round_1(self, env):
        floor_aware_baseline(env)
        for team in env.email_threads:
            assert len(env.email_threads[team]) >= 1


class TestTrulyNaiveBaseline:
    def test_runs_without_error(self, env):
        truly_naive_baseline(env)
        assert env.current_round >= 10

    def test_broadcasts_in_round_1(self, env):
        truly_naive_baseline(env)
        for team in env.email_threads:
            assert len(env.email_threads[team]) >= 1


class TestCalibrationProbe:
    def test_runs_without_error(self, env):
        result = run_calibration_probe(env)
        assert "acceptance_rate" in result
        assert "avg_counter_offers_before_accept" in result
        assert "avg_clarifying_questions" in result
        assert "granite_bay_wrong_position_refusal_rate" in result
        assert "pass_fail" in result
        assert "overall_pass" in result

    def test_probe_broadcasts_all_players_to_all_teams(self, env):
        run_calibration_probe(env)
        for team in env.email_threads:
            assert len(env.email_threads[team]) >= 4


class TestDeclineDetection:
    def test_cant_engage(self):
        assert _is_decline("We can't engage on this player.")

    def test_interior_only(self):
        assert _is_decline("Our focus this offseason is exclusively on interior players.")

    def test_normal_response(self):
        assert not _is_decline("We're very interested! Tell me more about the player.")


class TestClarifyingQuestionDetection:
    def test_question_mark(self):
        assert _is_clarifying_question("Can you tell me more about this player?", None)

    def test_with_offer_not_clarifying(self):
        assert not _is_clarifying_question("We're thinking $12M. What do you think?", 12.0)

    def test_no_question(self):
        assert not _is_clarifying_question("We appreciate you reaching out.", None)
