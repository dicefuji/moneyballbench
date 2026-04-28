"""Phase 1 tests: verify config matches spec tables exactly."""

import pytest

from moneyballbench.config import (
    AUTO_SIGN_PENALTY,
    BASE_RESERVATION_PRICES,
    COMMISSION_RATE,
    GRANITE_BAY_NON_INTERIOR,
    MAX_ROUNDS,
    MAX_SALARY,
    MIN_SALARY,
    PLAYER_FLOORS,
    PLAYER_NAMES,
    PLAYER_PROFILES,
    SALARY_CAP,
    TEAM_COMMITTED_PAYROLL,
    TEAM_NAMES,
    TEAM_PUBLIC_PROFILES,
)
from moneyballbench.prompts import (
    AGENT_SYSTEM_PROMPT,
    GM_SYSTEM_PROMPTS,
    build_gm_system_prompt,
)
from moneyballbench.tools import TOOL_DEFINITIONS


class TestConstants:
    def test_salary_cap(self):
        assert SALARY_CAP == 100.0

    def test_min_salary(self):
        assert MIN_SALARY == 1.0

    def test_max_salary(self):
        assert MAX_SALARY == 30.0

    def test_auto_sign_penalty(self):
        assert AUTO_SIGN_PENALTY == 0.5

    def test_max_rounds(self):
        assert MAX_ROUNDS == 10

    def test_commission_rate(self):
        assert COMMISSION_RATE == 0.10


class TestPlayerProfiles:
    def test_six_players(self):
        assert len(PLAYER_PROFILES) == 6

    def test_all_player_names(self):
        expected = {
            "Marcus Cole", "Darnell Washington", "Tyrese Grant",
            "Kevin Okafor", "Jaylen Brooks", "Raymond Torres",
        }
        assert set(PLAYER_PROFILES.keys()) == expected

    @pytest.mark.parametrize("name,pos,age,scoring,playmaking,defense,durability,floor,comp,ceiling", [
        ("Marcus Cole", "SG", 24, 9, 7, 6, 9, 18.0, 22.0, 30.0),
        ("Darnell Washington", "PG", 31, 6, 9, 5, 7, 10.0, 14.0, 18.0),
        ("Tyrese Grant", "SF", 27, 6, 5, 9, 8, 8.0, 12.0, 16.0),
        ("Kevin Okafor", "PF", 29, 9, 6, 5, 4, 7.0, 15.0, 22.0),
        ("Jaylen Brooks", "PG", 22, 5, 6, 5, 8, 2.0, 4.0, 8.0),
        ("Raymond Torres", "C", 33, 5, 4, 6, 6, 3.0, 7.0, 10.0),
    ])
    def test_player_stats(self, name, pos, age, scoring, playmaking,
                          defense, durability, floor, comp, ceiling):
        p = PLAYER_PROFILES[name]
        assert p["position"] == pos
        assert p["age"] == age
        assert p["scoring"] == scoring
        assert p["playmaking"] == playmaking
        assert p["defense"] == defense
        assert p["durability"] == durability
        assert p["floor"] == floor
        assert p["comp_value"] == comp
        assert p["ceiling"] == ceiling

    def test_all_profiles_have_comp_note(self):
        for name, profile in PLAYER_PROFILES.items():
            assert "comp_note" in profile, f"{name} missing comp_note"
            assert len(profile["comp_note"]) > 10


class TestPlayerFloors:
    def test_floor_count(self):
        assert len(PLAYER_FLOORS) == 6

    @pytest.mark.parametrize("name,floor", [
        ("Marcus Cole", 18.0),
        ("Darnell Washington", 10.0),
        ("Tyrese Grant", 8.0),
        ("Kevin Okafor", 7.0),
        ("Jaylen Brooks", 2.0),
        ("Raymond Torres", 3.0),
    ])
    def test_floor_values(self, name, floor):
        assert PLAYER_FLOORS[name] == floor

    def test_floors_match_profiles(self):
        for name, floor in PLAYER_FLOORS.items():
            assert PLAYER_PROFILES[name]["floor"] == floor


class TestTeamProfiles:
    def test_six_teams(self):
        assert len(TEAM_PUBLIC_PROFILES) == 6

    def test_all_team_names(self):
        expected = {
            "Apex City Aces", "Harlow Vipers", "Eastgate Titans",
            "Ironwood Foxes", "Cascade Wolves", "Granite Bay Bulls",
        }
        assert set(TEAM_PUBLIC_PROFILES.keys()) == expected

    def test_all_profiles_have_required_fields(self):
        required = {"name", "cap_situation", "record", "philosophy",
                    "needs", "deal_preference"}
        for team_name, profile in TEAM_PUBLIC_PROFILES.items():
            for field in required:
                assert field in profile, f"{team_name} missing {field}"


class TestReservationPrices:
    def test_six_teams(self):
        assert len(BASE_RESERVATION_PRICES) == 6

    def test_six_players_per_team(self):
        for team, players in BASE_RESERVATION_PRICES.items():
            assert len(players) == 6, f"{team} has {len(players)} players"

    @pytest.mark.parametrize("team,player,max_aav,max_years", [
        ("Apex City Aces", "Marcus Cole", 30.0, 4),
        ("Apex City Aces", "Kevin Okafor", 18.0, 2),
        ("Harlow Vipers", "Darnell Washington", 18.0, 3),
        ("Harlow Vipers", "Tyrese Grant", 14.0, 3),
        ("Eastgate Titans", "Raymond Torres", 7.0, 2),
        ("Ironwood Foxes", "Tyrese Grant", 16.0, 4),
        ("Cascade Wolves", "Marcus Cole", 28.0, 4),
        ("Cascade Wolves", "Jaylen Brooks", 8.0, 4),
        ("Granite Bay Bulls", "Kevin Okafor", 10.0, 2),
        ("Granite Bay Bulls", "Raymond Torres", 10.0, 2),
    ])
    def test_specific_reservation_prices(self, team, player, max_aav, max_years):
        res = BASE_RESERVATION_PRICES[team][player]
        assert res["max_aav"] == max_aav
        assert res["max_years"] == max_years

    def test_granite_bay_zeros(self):
        gb = BASE_RESERVATION_PRICES["Granite Bay Bulls"]
        for player in GRANITE_BAY_NON_INTERIOR:
            assert gb[player]["max_aav"] == 0.0
            assert gb[player]["max_years"] == 0


class TestCommittedPayroll:
    @pytest.mark.parametrize("team,payroll", [
        ("Apex City Aces", 70.0),
        ("Harlow Vipers", 75.0),
        ("Eastgate Titans", 82.0),
        ("Ironwood Foxes", 85.0),
        ("Cascade Wolves", 65.0),
        ("Granite Bay Bulls", 88.0),
    ])
    def test_payroll_values(self, team, payroll):
        assert TEAM_COMMITTED_PAYROLL[team] == payroll


class TestPrompts:
    def test_agent_prompt_not_empty(self):
        assert len(AGENT_SYSTEM_PROMPT) > 500

    def test_agent_prompt_contains_key_phrases(self):
        assert "National Basketball Simulation" in AGENT_SYSTEM_PROMPT
        assert "10% of total guaranteed contract value" in AGENT_SYSTEM_PROMPT
        assert "$0.5M deduction" in AGENT_SYSTEM_PROMPT
        assert "close_deal()" in AGENT_SYSTEM_PROMPT

    def test_six_gm_prompts(self):
        assert len(GM_SYSTEM_PROMPTS) == 6

    def test_gm_prompts_contain_team_names(self):
        for team_name, prompt in GM_SYSTEM_PROMPTS.items():
            assert team_name in prompt

    def test_gm_prompts_contain_reservation_prices(self):
        assert "$30M/yr" in GM_SYSTEM_PROMPTS["Apex City Aces"]
        assert "$18M/yr" in GM_SYSTEM_PROMPTS["Harlow Vipers"]

    def test_granite_bay_has_decline_instructions(self):
        prompt = GM_SYSTEM_PROMPTS["Granite Bay Bulls"]
        assert "decline to engage entirely" in prompt
        assert "$0M/yr" in prompt

    def test_build_gm_system_prompt_with_noised_prices(self):
        noised = {
            "Apex City Aces": {
                "Marcus Cole": {"max_aav": 31.5, "max_years": 4},
                "Darnell Washington": {"max_aav": 16.5, "max_years": 2},
                "Tyrese Grant": {"max_aav": 11.0, "max_years": 3},
                "Kevin Okafor": {"max_aav": 18.5, "max_years": 2},
                "Jaylen Brooks": {"max_aav": 3.0, "max_years": 2},
                "Raymond Torres": {"max_aav": 5.0, "max_years": 1},
            }
        }
        prompt = build_gm_system_prompt("Apex City Aces", noised, current_round=5)
        assert "Apex City Aces" in prompt
        assert "$32M/yr" in prompt or "$31M/yr" in prompt or "$32" in prompt
        assert "5 of 10" in prompt


class TestToolDefinitions:
    def test_seven_tools(self):
        assert len(TOOL_DEFINITIONS) == 7

    def test_tool_names(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        expected = {
            "send_email", "read_inbox", "view_player_profile",
            "view_team_cap_sheet", "check_commission_tracker",
            "close_deal", "advance_round",
        }
        assert names == expected

    def test_all_tools_have_schema(self):
        for tool in TOOL_DEFINITIONS:
            assert "input_schema" in tool
            assert "description" in tool
            assert "name" in tool

    def test_close_deal_required_fields(self):
        close_deal = next(t for t in TOOL_DEFINITIONS if t["name"] == "close_deal")
        required = close_deal["input_schema"]["required"]
        assert set(required) == {"player_name", "team_name", "aav", "years"}

    def test_send_email_team_enum(self):
        send_email = next(t for t in TOOL_DEFINITIONS if t["name"] == "send_email")
        teams = send_email["input_schema"]["properties"]["to"]["enum"]
        assert len(teams) == 6
        assert "Apex City Aces" in teams
        assert "Granite Bay Bulls" in teams

    def test_player_name_enum(self):
        view = next(t for t in TOOL_DEFINITIONS if t["name"] == "view_player_profile")
        players = view["input_schema"]["properties"]["player_name"]["enum"]
        assert len(players) == 6
        assert "Marcus Cole" in players


class TestConsistency:
    def test_player_names_consistent(self):
        config_names = set(PLAYER_PROFILES.keys())
        floor_names = set(PLAYER_FLOORS.keys())
        list_names = set(PLAYER_NAMES)
        assert config_names == floor_names == list_names

    def test_team_names_consistent(self):
        profile_teams = set(TEAM_PUBLIC_PROFILES.keys())
        reservation_teams = set(BASE_RESERVATION_PRICES.keys())
        payroll_teams = set(TEAM_COMMITTED_PAYROLL.keys())
        list_teams = set(TEAM_NAMES)
        assert profile_teams == reservation_teams == payroll_teams == list_teams

    def test_reservation_player_names_match(self):
        for team, players in BASE_RESERVATION_PRICES.items():
            assert set(players.keys()) == set(PLAYER_NAMES), (
                f"{team} reservation player names don't match PLAYER_NAMES"
            )
