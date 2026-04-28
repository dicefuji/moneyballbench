"""
MoneyBall Bench v3.0 — Truly-Naive Baseline (Appendix E.2).

No access to floor information. Accepts the first numerical offer
received, even if below floor. Some deals will be blocked, requiring
retry. Re-broadcasts failed players in subsequent rounds.
"""

from __future__ import annotations

import re
from typing import Optional

from moneyballbench.config import (
    PLAYER_NAMES,
    PLAYER_PROFILES,
    TEAM_COMMITTED_PAYROLL,
)
from moneyballbench.baselines.floor_aware import (
    parse_offer_from_email,
    infer_player_from_thread,
)


def truly_naive_baseline(env) -> None:
    """
    Truly-naive: accepts first offer received regardless of floor.
    Blocked deals require re-broadcast in subsequent rounds (Appendix E.2).
    """
    signed_players: set[str] = set()
    failed_players: set[str] = set()

    def _broadcast(players: list[str]) -> None:
        for player in players:
            if player in signed_players:
                continue
            for team in TEAM_COMMITTED_PAYROLL:
                profile = PLAYER_PROFILES[player]
                body = (
                    f"Hi, I represent {player}, {profile['age']}-year-old "
                    f"{profile['position']} available in free agency. "
                    f"Comp: {profile['comp_note']}. "
                    f"Seeking ${profile['comp_value'] * 1.1:.1f}M/yr, 3yr deal. "
                    f"Please let me know your interest."
                )
                env.tool_send_email(
                    to=team, subject=f"{player} inquiry", body=body
                )

    _broadcast(list(PLAYER_NAMES))
    env.tool_advance_round()

    for round_num in range(2, 11):
        if failed_players - signed_players:
            _broadcast(list(failed_players - signed_players))

        emails = env.tool_read_inbox()
        for email in emails:
            offered_aav = parse_offer_from_email(email["body"])
            player_name = infer_player_from_thread(
                email["from"], env.email_threads, signed_players
            )
            if offered_aav and player_name and player_name not in signed_players:
                result = env.tool_close_deal(
                    player_name=player_name,
                    team_name=email["from"],
                    aav=offered_aav,
                    years=2,
                )
                if result.get("status") == "DEAL SIGNED":
                    signed_players.add(player_name)
                elif "error" in result:
                    failed_players.add(player_name)

        env.tool_advance_round()
