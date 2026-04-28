"""
MoneyBall Bench v3.0 — Calibration Probe Agent (Appendix C).

Deterministic scripted agent used exclusively to verify GM behavior
before leaderboard runs. Not a baseline for scoring purposes.
"""

from __future__ import annotations

from typing import Optional

from moneyballbench.baselines.floor_aware import parse_offer_from_email
from moneyballbench.config import (
    PLAYER_FLOORS,
    PLAYER_NAMES,
    PLAYER_PROFILES,
    TEAM_COMMITTED_PAYROLL,
)


def run_calibration_probe(env) -> dict:
    """
    Run the calibration probe agent against the environment.
    Returns structured metrics for pass/fail evaluation.
    """
    asks: dict[str, float] = {}
    negotiations: dict[tuple[str, str], dict] = {}
    signed_players: set[str] = set()

    # --------------------------------------------------------------- #
    # Round 1: broadcast templated emails to all teams for all players #
    # --------------------------------------------------------------- #
    for player in PLAYER_NAMES:
        profile = PLAYER_PROFILES[player]
        ask_aav = round(profile["comp_value"] * 1.10 * 2) / 2
        asks[player] = ask_aav

        for team in TEAM_COMMITTED_PAYROLL:
            body = (
                f"Hi,\n\n"
                f"I'm reaching out regarding {player}, {profile['age']}-year-old "
                f"{profile['position']} available in free agency this offseason.\n\n"
                f"Quick stats: {profile['scoring']}/10 scoring, "
                f"{profile['playmaking']}/10 playmaking, "
                f"{profile['defense']}/10 defense, "
                f"{profile['durability']}/10 durability.\n\n"
                f"Comparable contract: {profile['comp_note']}\n\n"
                f"I'm targeting ${ask_aav}M/year on a 4-year deal. "
                f"What's your level of interest and would you like to discuss further?\n\n"
                f"Best,\nAgent"
            )
            env.tool_send_email(
                to=team,
                subject=f"{player} — available in free agency",
                body=body,
            )
            negotiations[(player, team)] = {
                "status": "open",
                "exchanges": 0,
                "counters_before_accept": 0,
                "clarifying_questions": 0,
                "declined": False,
                "accepted_aav": None,
            }

    env.tool_advance_round()

    # --------------------------------------------------------------- #
    # Round 2: read inbox, respond per Appendix C rules               #
    # --------------------------------------------------------------- #
    emails = env.tool_read_inbox()
    for email in emails:
        team = email["from"]
        body_text = email["body"]
        offered_aav = parse_offer_from_email(body_text)

        for player in PLAYER_NAMES:
            if player.lower() in body_text.lower() or player.lower() in email.get("subject", "").lower():
                key = (player, team)
                if key not in negotiations or negotiations[key]["status"] != "open":
                    continue
                negotiations[key]["exchanges"] += 1

                if _is_decline(body_text):
                    negotiations[key]["status"] = "declined"
                    negotiations[key]["declined"] = True
                    break

                if _is_clarifying_question(body_text, offered_aav):
                    negotiations[key]["clarifying_questions"] += 1
                    reply_body = (
                        f"{player} has shown excellent consistency this season and "
                        f"would be a strong fit with your team's system. "
                        f"I'm still targeting ${asks[player]}M/year on a 4-year deal."
                    )
                    env.tool_send_email(to=team, subject=f"Re: {player}", body=reply_body)
                    break

                if offered_aav and offered_aav >= PLAYER_FLOORS.get(player, 0):
                    negotiations[key]["counters_before_accept"] += 1
                    mid = round((offered_aav + asks[player]) / 2 * 2) / 2
                    reply_body = (
                        f"Thanks for the counter. I think ${mid}M/year on a 3-year deal "
                        f"gets us closer. Would that work for your side?"
                    )
                    env.tool_send_email(to=team, subject=f"Re: {player}", body=reply_body)
                break

    env.tool_advance_round()

    # --------------------------------------------------------------- #
    # Rounds 3–4: midpoint countering                                  #
    # --------------------------------------------------------------- #
    for round_num in range(3, 5):
        emails = env.tool_read_inbox()
        for email in emails:
            team = email["from"]
            body_text = email["body"]
            offered_aav = parse_offer_from_email(body_text)

            for player in PLAYER_NAMES:
                if player.lower() in body_text.lower() or player.lower() in email.get("subject", "").lower():
                    key = (player, team)
                    if key not in negotiations or negotiations[key]["status"] != "open":
                        continue
                    if player in signed_players:
                        continue
                    negotiations[key]["exchanges"] += 1

                    if offered_aav:
                        negotiations[key]["counters_before_accept"] += 1
                        if abs(offered_aav - asks[player]) / asks[player] <= 0.05:
                            result = env.tool_close_deal(
                                player_name=player,
                                team_name=team,
                                aav=offered_aav,
                                years=3,
                            )
                            if result.get("status") == "DEAL SIGNED":
                                negotiations[key]["status"] = "signed"
                                negotiations[key]["accepted_aav"] = offered_aav
                                signed_players.add(player)
                        else:
                            mid = round((offered_aav + asks[player]) / 2 * 2) / 2
                            reply_body = (
                                f"I appreciate the movement. ${mid}M/year on a 3-year deal "
                                f"would work for us. Can you make that happen?"
                            )
                            env.tool_send_email(
                                to=team, subject=f"Re: {player}", body=reply_body
                            )
                    break

        env.tool_advance_round()

    # --------------------------------------------------------------- #
    # Rounds 5–10: accept any above-floor offer                        #
    # --------------------------------------------------------------- #
    for round_num in range(5, 11):
        emails = env.tool_read_inbox()
        for email in emails:
            team = email["from"]
            body_text = email["body"]
            offered_aav = parse_offer_from_email(body_text)

            for player in PLAYER_NAMES:
                if player.lower() in body_text.lower() or player.lower() in email.get("subject", "").lower():
                    key = (player, team)
                    if key not in negotiations or negotiations[key]["status"] != "open":
                        continue
                    if player in signed_players:
                        continue
                    negotiations[key]["exchanges"] += 1

                    if offered_aav and offered_aav >= PLAYER_FLOORS.get(player, 0):
                        result = env.tool_close_deal(
                            player_name=player,
                            team_name=team,
                            aav=offered_aav,
                            years=3,
                        )
                        if result.get("status") == "DEAL SIGNED":
                            negotiations[key]["status"] = "signed"
                            negotiations[key]["accepted_aav"] = offered_aav
                            signed_players.add(player)
                    break

        env.tool_advance_round()

    return _compute_metrics(negotiations)


def _is_decline(body: str) -> bool:
    """Check if a GM response is a polite decline."""
    decline_phrases = [
        "can't engage", "not engage", "exclusively on interior",
        "focus this offseason", "no use for", "not in a position",
        "don't have a need", "not a fit", "passing on",
    ]
    lower = body.lower()
    return any(phrase in lower for phrase in decline_phrases)


def _is_clarifying_question(body: str, offered_aav: Optional[float]) -> bool:
    """Check if a GM response is a clarifying question (no counter-offer)."""
    if offered_aav is not None:
        return False
    question_indicators = ["?", "tell me more", "how does", "what role", "can you"]
    lower = body.lower()
    return any(ind in lower for ind in question_indicators)


def _compute_metrics(negotiations: dict) -> dict:
    """
    Compute calibration metrics per Appendix C thresholds.
    """
    total_above_floor_offers = 0
    total_accepted = 0
    counter_counts = []
    clarifying_counts = []
    granite_bay_wrong_position_total = 0
    granite_bay_wrong_position_declined = 0

    for (player, team), neg in negotiations.items():
        if neg["declined"]:
            if team == "Granite Bay Bulls":
                from moneyballbench.config import GRANITE_BAY_NON_INTERIOR
                if player in GRANITE_BAY_NON_INTERIOR:
                    granite_bay_wrong_position_total += 1
                    granite_bay_wrong_position_declined += 1
            continue

        if neg["exchanges"] > 0:
            total_above_floor_offers += 1
            clarifying_counts.append(neg["clarifying_questions"])

        if neg["status"] == "signed":
            total_accepted += 1
            counter_counts.append(neg["counters_before_accept"])

    if team == "Granite Bay Bulls":
        from moneyballbench.config import GRANITE_BAY_NON_INTERIOR
        for player in GRANITE_BAY_NON_INTERIOR:
            key = (player, "Granite Bay Bulls")
            if key in negotiations:
                granite_bay_wrong_position_total += 1
                if negotiations[key].get("declined"):
                    granite_bay_wrong_position_declined += 1

    acceptance_rate = (
        total_accepted / total_above_floor_offers
        if total_above_floor_offers > 0 else 0.0
    )
    avg_counters = (
        sum(counter_counts) / len(counter_counts)
        if counter_counts else 0.0
    )
    avg_clarifying = (
        sum(clarifying_counts) / len(clarifying_counts)
        if clarifying_counts else 0.0
    )
    gb_refusal_rate = (
        granite_bay_wrong_position_declined / granite_bay_wrong_position_total
        if granite_bay_wrong_position_total > 0 else 1.0
    )

    results = {
        "acceptance_rate": acceptance_rate,
        "avg_counter_offers_before_accept": avg_counters,
        "avg_clarifying_questions": avg_clarifying,
        "granite_bay_wrong_position_refusal_rate": gb_refusal_rate,
        "pass_fail": {
            "acceptance_rate": "PASS" if 0.60 <= acceptance_rate <= 0.75 else "FAIL",
            "avg_counters": "PASS" if 2 <= avg_counters <= 4 else "FAIL",
            "clarifying_questions": "PASS" if avg_clarifying >= 1.0 else "FAIL",
            "granite_bay_refusal": "PASS" if gb_refusal_rate == 1.0 else "FAIL",
        },
        "raw": {
            "total_negotiations": len(negotiations),
            "total_accepted": total_accepted,
            "total_above_floor_offers": total_above_floor_offers,
            "counter_counts": counter_counts,
            "clarifying_counts": clarifying_counts,
        },
    }
    results["overall_pass"] = all(
        v == "PASS" for v in results["pass_fail"].values()
    )
    return results
