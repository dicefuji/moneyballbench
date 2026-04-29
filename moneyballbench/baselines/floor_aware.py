"""
MoneyBall Bench v3.0 — Floor-Aware Random Baseline (Appendix E.1).

Has access to player floor information. Signs the first above-floor
offer received from any team.
"""

from __future__ import annotations

import re
from typing import Optional

from moneyballbench.config import (
    PLAYER_FLOORS,
    PLAYER_NAMES,
    PLAYER_PROFILES,
    TEAM_COMMITTED_PAYROLL,
)


def parse_offer_from_email(body: str) -> Optional[float]:
    """
    Extract the first dollar amount from an email body.
    Uses regex: \\$(\\d+(?:\\.\\d+)?)M? and picks the first match.
    """
    match = re.search(r'\$(\d+(?:\.\d+)?)M?', body)
    if match:
        return float(match.group(1))
    return None


def infer_player_from_thread(
    team_name: str,
    email_threads: dict[str, list[dict]],
    signed_players: set[str],
) -> Optional[str]:
    """
    Infer which player is being discussed in the most recent email
    from a given team, by scanning the thread for player names.
    Returns the first unsigned player name found in the thread.
    """
    thread = email_threads.get(team_name, [])
    for msg in reversed(thread):
        content = msg.get("content", "")
        for player in PLAYER_NAMES:
            if player in content and player not in signed_players:
                return player
    return None


def floor_aware_baseline(env) -> None:
    """
    Deterministic baseline: broadcast to all teams round 1,
    accept first above-floor offer received (Appendix E.1).
    """
    signed_players: set[str] = set()
    unsigned = list(PLAYER_FLOORS.keys())

    for player in unsigned:
        for team in TEAM_COMMITTED_PAYROLL:
            profile = PLAYER_PROFILES[player]
            body = (
                f"Hi, I represent {player}, {profile['age']}-year-old "
                f"{profile['position']} available in free agency. "
                f"Comp: {profile['comp_note']}. "
                f"Seeking ${profile['comp_value'] * 1.1:.1f}M/yr, 3yr deal. "
                f"Please let me know your interest."
            )
            env.tool_send_email(to=team, subject=f"{player} inquiry", body=body)

    env.tool_advance_round()

    for round_num in range(2, 11):
        emails = env.tool_read_inbox()
        for email in emails:
            offered_aav = parse_offer_from_email(email["body"])
            player_name = infer_player_from_thread(
                email["from"], env.email_threads, signed_players
            )
            if offered_aav and player_name:
                floor = PLAYER_FLOORS.get(player_name, 0)
                if offered_aav >= floor:
                    result = env.tool_close_deal(
                        player_name=player_name,
                        team_name=email["from"],
                        aav=offered_aav,
                        years=2,
                    )
                    if result.get("status") == "DEAL SIGNED":
                        signed_players.add(player_name)
                        continue
        env.tool_advance_round()
