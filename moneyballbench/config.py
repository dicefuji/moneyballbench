"""
MoneyBall Bench v3.0 — Configuration and static data.

All player profiles, team profiles, reservation prices, and constants
are defined here exactly as specified in the benchmark spec (§4, §5, §7.2).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants (§3.2, §3.5)
# ---------------------------------------------------------------------------

SALARY_CAP = 100.0          # $100M hard cap
MIN_SALARY = 1.0            # $1M/year minimum
MAX_SALARY = 30.0           # $30M/year maximum
MAX_CONTRACT_YEARS = 4
MIN_CONTRACT_YEARS = 1
AUTO_SIGN_PENALTY = 0.5     # $0.5M per auto-signed player
MAX_ROUNDS = 10
COMMISSION_RATE = 0.10       # 10% of total contract value
AUTO_SIGN_AAV = 1.0          # $1M/1yr auto-sign deal
AUTO_SIGN_YEARS = 1

# ---------------------------------------------------------------------------
# Player Profiles (§4)
# ---------------------------------------------------------------------------

PLAYER_PROFILES: dict[str, dict] = {
    "Marcus Cole": {
        "name": "Marcus Cole",
        "position": "SG",
        "age": 24,
        "scoring": 9,
        "playmaking": 7,
        "defense": 6,
        "durability": 9,
        "floor": 18.0,
        "comp_value": 22.0,
        "ceiling": 30.0,
        "comp_note": (
            "Jordan Hayes (9/10 scoring, 8/10 durability, age 25) signed "
            "4yr/$88M ($22M AAV) with Apex City last offseason."
        ),
        "primary_test": (
            "Auction dynamics. Multiple teams want this player. Does the "
            "model run competitive bidding or accept the first strong offer?"
        ),
    },
    "Darnell Washington": {
        "name": "Darnell Washington",
        "position": "PG",
        "age": 31,
        "scoring": 6,
        "playmaking": 9,
        "defense": 5,
        "durability": 7,
        "floor": 10.0,
        "comp_value": 14.0,
        "ceiling": 18.0,
        "comp_note": (
            "Marcus Bell (8/10 playmaking, age 30) signed 2yr/$26M "
            "($13M AAV) last offseason."
        ),
        "primary_test": (
            "Length vs. AAV trade-off. Win-now teams resist long deals for "
            "31-year-olds. Does the model optimize AAV (short deal) vs. "
            "total contract value (long deal)?"
        ),
    },
    "Tyrese Grant": {
        "name": "Tyrese Grant",
        "position": "SF",
        "age": 27,
        "scoring": 6,
        "playmaking": 5,
        "defense": 9,
        "durability": 8,
        "floor": 8.0,
        "comp_value": 12.0,
        "ceiling": 16.0,
        "comp_note": (
            "Andre Thompson (9/10 defense, age 26) signed 3yr/$33M "
            "($11M AAV) last offseason."
        ),
        "primary_test": (
            "Team-fit identification. Defensive value is highly "
            "team-dependent. Does the agent identify and target the "
            "defense-first team rather than broadcasting generically?"
        ),
    },
    "Kevin Okafor": {
        "name": "Kevin Okafor",
        "position": "PF",
        "age": 29,
        "scoring": 9,
        "playmaking": 6,
        "defense": 5,
        "durability": 4,
        "floor": 7.0,
        "comp_value": 15.0,
        "ceiling": 22.0,
        "comp_note": (
            "Devon Miles (9/10 scoring, 8/10 durability, age 28) signed "
            "3yr/$45M ($15M AAV) last offseason. Miles had significantly "
            "better injury history."
        ),
        "primary_test": (
            "Adverse information framing. Large gap between raw scoring "
            "value and injury-risk discount. Does the model construct "
            "risk-reward narratives that close the gap?"
        ),
    },
    "Jaylen Brooks": {
        "name": "Jaylen Brooks",
        "position": "PG",
        "age": 22,
        "scoring": 5,
        "playmaking": 6,
        "defense": 5,
        "durability": 8,
        "floor": 2.0,
        "comp_value": 4.0,
        "ceiling": 8.0,
        "comp_note": (
            "Chris Yates (similar profile, age 21) signed 2yr/$6M "
            "($3M AAV) last offseason."
        ),
        "primary_test": (
            "Upside narrative framing. Modest current stats but youth "
            "creates a premium for rebuilding teams. Does the agent route "
            "to the right team type and frame the player as a lottery ticket?"
        ),
    },
    "Raymond Torres": {
        "name": "Raymond Torres",
        "position": "C",
        "age": 33,
        "scoring": 5,
        "playmaking": 4,
        "defense": 6,
        "durability": 6,
        "floor": 3.0,
        "comp_value": 7.0,
        "ceiling": 10.0,
        "comp_note": (
            "Leon Foster (7/10 defense, age 32) signed 1yr/$5M last "
            "offseason."
        ),
        "primary_test": (
            "Adverse advocacy. Declining stats, teams know it. Does the "
            "model frame intangibles (experience, locker room leadership) "
            "to extract above-comp value?"
        ),
    },
}

# ---------------------------------------------------------------------------
# Player Floors (§7.2)
# ---------------------------------------------------------------------------

PLAYER_FLOORS: dict[str, float] = {
    "Marcus Cole": 18.0,
    "Darnell Washington": 10.0,
    "Tyrese Grant": 8.0,
    "Kevin Okafor": 7.0,
    "Jaylen Brooks": 2.0,
    "Raymond Torres": 3.0,
}

# ---------------------------------------------------------------------------
# Team Public Profiles (§5.1 — visible to agent)
# ---------------------------------------------------------------------------

TEAM_PUBLIC_PROFILES: dict[str, dict] = {
    "Apex City Aces": {
        "name": "Apex City Aces",
        "cap_situation": "Moderate (~$30M available)",
        "record": "58-24",
        "philosophy": (
            "Win now, will pay premium for proven talent"
        ),
        "needs": "SG depth (critical), PF scoring (secondary)",
        "deal_preference": (
            "2-3yr; will do 4yr for franchise talent"
        ),
    },
    "Harlow Vipers": {
        "name": "Harlow Vipers",
        "cap_situation": "Moderate (~$25M available)",
        "record": "52-30",
        "philosophy": "Star-driven culture",
        "needs": "PG (critical), SF (secondary)",
        "deal_preference": (
            "Long deals for cornerstones, 2-3yr for role players"
        ),
    },
    "Eastgate Titans": {
        "name": "Eastgate Titans",
        "cap_situation": "Moderate-tight (~$18M available)",
        "record": "44-38",
        "philosophy": "Data-driven, value-focused",
        "needs": "Best value at any position",
        "deal_preference": "2-3yr",
    },
    "Ironwood Foxes": {
        "name": "Ironwood Foxes",
        "cap_situation": "Tight (~$15M available)",
        "record": "47-35",
        "philosophy": "Defensive efficiency above all",
        "needs": (
            "Defensive specialist (critical), efficient scorer (secondary)"
        ),
        "deal_preference": (
            "3-4yr for system fits, 1yr for uncertain fits"
        ),
    },
    "Cascade Wolves": {
        "name": "Cascade Wolves",
        "cap_situation": "Flexible (~$35M available)",
        "record": "28-54",
        "philosophy": (
            "Full rebuild, buying future upside"
        ),
        "needs": (
            "Young players at all positions, strong preference for under-25"
        ),
        "deal_preference": (
            "Long deals (3-4yr) for youth; max 1yr for veterans over 30"
        ),
    },
    "Granite Bay Bulls": {
        "name": "Granite Bay Bulls",
        "cap_situation": "Very tight (~$12M available)",
        "record": "38-44",
        "philosophy": (
            "Interior scoring only - will not engage on guards or "
            "small forwards"
        ),
        "needs": "PF or C ONLY",
        "deal_preference": "2-3yr preferred",
    },
}

# ---------------------------------------------------------------------------
# Team Names (convenience list)
# ---------------------------------------------------------------------------

TEAM_NAMES: list[str] = [
    "Apex City Aces",
    "Harlow Vipers",
    "Eastgate Titans",
    "Ironwood Foxes",
    "Cascade Wolves",
    "Granite Bay Bulls",
]

PLAYER_NAMES: list[str] = [
    "Marcus Cole",
    "Darnell Washington",
    "Tyrese Grant",
    "Kevin Okafor",
    "Jaylen Brooks",
    "Raymond Torres",
]

# ---------------------------------------------------------------------------
# Base Reservation Prices (§7.2 — stored in config AND in GM prompts)
# ---------------------------------------------------------------------------

BASE_RESERVATION_PRICES: dict[str, dict[str, dict]] = {
    "Apex City Aces": {
        "Marcus Cole":        {"max_aav": 30.0, "max_years": 4},
        "Darnell Washington": {"max_aav": 16.0, "max_years": 2},
        "Tyrese Grant":       {"max_aav": 11.0, "max_years": 3},
        "Kevin Okafor":       {"max_aav": 18.0, "max_years": 2},
        "Jaylen Brooks":      {"max_aav":  3.0, "max_years": 2},
        "Raymond Torres":     {"max_aav":  5.0, "max_years": 1},
    },
    "Harlow Vipers": {
        "Marcus Cole":        {"max_aav": 26.0, "max_years": 4},
        "Darnell Washington": {"max_aav": 18.0, "max_years": 3},
        "Tyrese Grant":       {"max_aav": 14.0, "max_years": 3},
        "Kevin Okafor":       {"max_aav": 14.0, "max_years": 2},
        "Jaylen Brooks":      {"max_aav":  5.0, "max_years": 3},
        "Raymond Torres":     {"max_aav":  4.0, "max_years": 1},
    },
    "Eastgate Titans": {
        "Marcus Cole":        {"max_aav": 22.0, "max_years": 3},
        "Darnell Washington": {"max_aav": 14.0, "max_years": 2},
        "Tyrese Grant":       {"max_aav": 13.0, "max_years": 3},
        "Kevin Okafor":       {"max_aav": 12.0, "max_years": 2},
        "Jaylen Brooks":      {"max_aav":  4.0, "max_years": 2},
        "Raymond Torres":     {"max_aav":  7.0, "max_years": 2},
    },
    "Ironwood Foxes": {
        "Marcus Cole":        {"max_aav": 20.0, "max_years": 3},
        "Darnell Washington": {"max_aav": 12.0, "max_years": 2},
        "Tyrese Grant":       {"max_aav": 16.0, "max_years": 4},
        "Kevin Okafor":       {"max_aav":  8.0, "max_years": 1},
        "Jaylen Brooks":      {"max_aav":  4.0, "max_years": 2},
        "Raymond Torres":     {"max_aav":  5.0, "max_years": 1},
    },
    "Cascade Wolves": {
        "Marcus Cole":        {"max_aav": 28.0, "max_years": 4},
        "Darnell Washington": {"max_aav":  8.0, "max_years": 1},
        "Tyrese Grant":       {"max_aav": 10.0, "max_years": 3},
        "Kevin Okafor":       {"max_aav": 10.0, "max_years": 2},
        "Jaylen Brooks":      {"max_aav":  8.0, "max_years": 4},
        "Raymond Torres":     {"max_aav":  3.0, "max_years": 1},
    },
    "Granite Bay Bulls": {
        "Marcus Cole":        {"max_aav":  0.0, "max_years": 0},
        "Darnell Washington": {"max_aav":  0.0, "max_years": 0},
        "Tyrese Grant":       {"max_aav":  0.0, "max_years": 0},
        "Kevin Okafor":       {"max_aav": 10.0, "max_years": 2},
        "Jaylen Brooks":      {"max_aav":  0.0, "max_years": 0},
        "Raymond Torres":     {"max_aav": 10.0, "max_years": 2},
    },
}

# ---------------------------------------------------------------------------
# Team Committed Payroll (§7.2)
# ---------------------------------------------------------------------------

TEAM_COMMITTED_PAYROLL: dict[str, float] = {
    "Apex City Aces":    70.0,
    "Harlow Vipers":     75.0,
    "Eastgate Titans":   82.0,
    "Ironwood Foxes":    85.0,
    "Cascade Wolves":    65.0,
    "Granite Bay Bulls": 88.0,
}

# ---------------------------------------------------------------------------
# Granite Bay non-interior players (§7.3)
# ---------------------------------------------------------------------------

GRANITE_BAY_NON_INTERIOR: list[str] = [
    "Marcus Cole",
    "Darnell Washington",
    "Tyrese Grant",
    "Jaylen Brooks",
]
