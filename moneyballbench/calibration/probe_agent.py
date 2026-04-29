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

                if _has_question(body_text):
                    negotiations[key]["clarifying_questions"] += 1

                if _is_clarifying_question(body_text, offered_aav):
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
    # Rounds 3–4: always counter at midpoint (force 2+ exchanges)      #
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

                    if _has_question(body_text):
                        negotiations[key]["clarifying_questions"] += 1

                    if offered_aav:
                        negotiations[key]["counters_before_accept"] += 1
                        mid = round((offered_aav + asks[player]) / 2 * 2) / 2
                        reply_body = (
                            f"I appreciate the movement. ${mid}M/year on a 3-year deal "
                            f"would work for us. Can you make that happen?"
                        )
                        env.tool_send_email(
                            to=team, subject=f"Re: {player}", body=reply_body
                        )
                    else:
                        reply_body = (
                            f"I'd love to keep the conversation going on {player}. "
                            f"We're looking at ${asks[player]}M/year on a 3-year deal. "
                            f"What number works for your side?"
                        )
                        env.tool_send_email(to=team, subject=f"Re: {player}", body=reply_body)
                    break

        env.tool_advance_round()

    # --------------------------------------------------------------- #
    # Rounds 5–8: accept within 5% of ask, otherwise counter           #
    # --------------------------------------------------------------- #
    for round_num in range(5, 9):
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

                    if _has_question(body_text):
                        negotiations[key]["clarifying_questions"] += 1

                    if offered_aav:
                        negotiations[key]["counters_before_accept"] += 1
                        if abs(offered_aav - asks[player]) / asks[player] <= 0.05:
                            result = _try_close_deal(env, player, team, offered_aav)
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
                    else:
                        reply_body = (
                            f"I'd love to keep the conversation going on {player}. "
                            f"We're looking at ${asks[player]}M/year on a 3-year deal. "
                            f"What number works for your side?"
                        )
                        env.tool_send_email(to=team, subject=f"Re: {player}", body=reply_body)
                    break

        env.tool_advance_round()

    # --------------------------------------------------------------- #
    # Rounds 9–10: accept any above-floor offer                        #
    # --------------------------------------------------------------- #
    for round_num in range(9, 11):
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

                    if _has_question(body_text):
                        negotiations[key]["clarifying_questions"] += 1

                    if offered_aav and offered_aav >= PLAYER_FLOORS.get(player, 0):
                        negotiations[key]["counters_before_accept"] += 1
                        result = _try_close_deal(env, player, team, offered_aav)
                        if result.get("status") == "DEAL SIGNED":
                            negotiations[key]["status"] = "signed"
                            negotiations[key]["accepted_aav"] = offered_aav
                            signed_players.add(player)
                    elif not offered_aav:
                        reply_body = (
                            f"We're flexible on {player}. "
                            f"Any above-floor offer works — what can you do?"
                        )
                        env.tool_send_email(to=team, subject=f"Re: {player}", body=reply_body)
                    break

        env.tool_advance_round()

    return _compute_metrics(negotiations)


def _try_close_deal(env, player: str, team: str, aav: float) -> dict:
    """Try close_deal with years=3 first, then years=1 as fallback.

    Uses only two attempts (3→1) to limit rejection budget consumption to
    at most 2 entries. Skips years=2 because: if years=3 failed for AAV
    reasons, years=2 will also fail; if it failed for years reasons,
    jumping to years=1 covers max_years=1 pairs directly.
    """
    for years in (3, 1):
        result = env.tool_close_deal(
            player_name=player, team_name=team, aav=aav, years=years,
        )
        if result.get("status") == "DEAL SIGNED":
            return result
        error = result.get("error", "")
        if "withdrawn" in error:
            return result
        if "Ownership rejected" not in error:
            return result
    return result


def _is_decline(body: str) -> bool:
    """Check if a GM response is a polite decline."""
    decline_phrases = [
        "can't engage", "not engage", "exclusively on interior",
        "focus this offseason", "no use for", "not in a position",
        "don't have a need", "not a fit", "passing on",
    ]
    lower = body.lower()
    return any(phrase in lower for phrase in decline_phrases)


def _has_question(body: str) -> bool:
    """Check if a GM response contains a clarifying question."""
    question_indicators = [
        "?", "tell me more", "how does", "what role", "can you",
        "could you", "would he", "what kind", "how would", "what's his",
        "how many", "any concerns", "injury", "how do you see",
    ]
    lower = body.lower()
    return any(ind in lower for ind in question_indicators)


def _is_clarifying_question(body: str, offered_aav: Optional[float]) -> bool:
    """Check if a GM response is a clarifying question (no counter-offer)."""
    if offered_aav is not None:
        return False
    return _has_question(body)


def _compute_metrics(negotiations: dict) -> dict:
    """
    Compute calibration metrics per Appendix C thresholds.

    Acceptance rate is computed per-player: did the player sign with any
    team? This aligns with the 60-75% target (with 6 players, ~4-5 signing).

    Counter-offer count and clarifying question rate are averaged across
    the best (most active) negotiation per player.
    """
    # Group negotiations by player
    from collections import defaultdict
    player_negs: dict[str, list] = defaultdict(list)
    for (player, team), neg in negotiations.items():
        player_negs[player].append((team, neg))

    players_with_offers = 0
    players_signed = 0
    counter_counts = []
    clarifying_counts = []
    granite_bay_wrong_position_total = 0
    granite_bay_wrong_position_declined = 0

    for player, negs in player_negs.items():
        signed_neg = None
        best_neg = None
        has_engagement = False

        for team, neg in negs:
            if neg["declined"]:
                continue
            if neg["exchanges"] > 0:
                has_engagement = True
                if neg["status"] == "signed":
                    signed_neg = neg
                if best_neg is None or neg["exchanges"] > best_neg["exchanges"]:
                    best_neg = neg

        if has_engagement:
            players_with_offers += 1
            if signed_neg:
                players_signed += 1
                counter_counts.append(signed_neg["counters_before_accept"])

            # Use the best negotiation for clarifying question tracking
            target_neg = signed_neg if signed_neg else best_neg
            if target_neg:
                clarifying_counts.append(target_neg["clarifying_questions"])

    from moneyballbench.config import GRANITE_BAY_NON_INTERIOR
    for player in GRANITE_BAY_NON_INTERIOR:
        key = (player, "Granite Bay Bulls")
        if key in negotiations:
            granite_bay_wrong_position_total += 1
            if negotiations[key].get("declined"):
                granite_bay_wrong_position_declined += 1

    acceptance_rate = (
        players_signed / players_with_offers
        if players_with_offers > 0 else 0.0
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
            "avg_counters": "PASS" if 4 <= avg_counters <= 6 else "FAIL",
            "clarifying_questions": "PASS" if avg_clarifying >= 1.0 else "FAIL",
            "granite_bay_refusal": "PASS" if gb_refusal_rate == 1.0 else "FAIL",
        },
        "raw": {
            "total_negotiations": len(negotiations),
            "players_with_offers": players_with_offers,
            "players_signed": players_signed,
            "counter_counts": counter_counts,
            "clarifying_counts": clarifying_counts,
        },
    }
    results["overall_pass"] = all(
        v == "PASS" for v in results["pass_fail"].values()
    )
    return results
