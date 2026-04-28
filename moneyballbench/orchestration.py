"""
MoneyBall Bench v3.0 — Orchestration loop.

Implements run_benchmark() and run_full_evaluation() exactly as §7.4.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from moneyballbench.config import (
    BASE_RESERVATION_PRICES,
    PLAYER_PROFILES,
    TEAM_PUBLIC_PROFILES,
    PLAYER_NAMES,
    TEAM_NAMES,
)
from moneyballbench.environment import NBASimEnvironment
from moneyballbench.noise import apply_reservation_noise
from moneyballbench.prompts import AGENT_SYSTEM_PROMPT
from moneyballbench.stats import bootstrap_ci, std_dev
from moneyballbench.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

MAX_TURNS = 300


def build_initial_context(season: int = 1) -> str:
    """
    Build the initial context message for the agent containing all
    player profiles and team public profiles.
    """
    lines = [f"# Free Agency Season {season} — Your Client Portfolio\n"]

    for name in PLAYER_NAMES:
        p = PLAYER_PROFILES[name]
        lines.append(f"## {p['name']} — {p['position']}, Age {p['age']}")
        lines.append(f"- Scoring: {p['scoring']}/10")
        lines.append(f"- Playmaking: {p['playmaking']}/10")
        lines.append(f"- Defense: {p['defense']}/10")
        lines.append(f"- Durability: {p['durability']}/10")
        lines.append(f"- Floor salary: ${p['floor']}M/yr")
        lines.append(f"- Comparable contract: {p['comp_note']}")
        lines.append("")

    lines.append("# Available Teams\n")

    for name in TEAM_NAMES:
        t = TEAM_PUBLIC_PROFILES[name]
        lines.append(f"## {t['name']}")
        lines.append(f"- Cap situation: {t['cap_situation']}")
        lines.append(f"- Record: {t['record']}")
        lines.append(f"- Philosophy: {t['philosophy']}")
        lines.append(f"- Needs: {t['needs']}")
        lines.append(f"- Deal preference: {t['deal_preference']}")
        lines.append("")

    lines.append(
        "Review your clients and the teams, then begin negotiations. "
        "You have 10 rounds to sign all 6 players."
    )
    return "\n".join(lines)


def run_benchmark(
    agent_model_id: str,
    agent_client,
    gm_client,
    gm_model_id: str,
    gm_stack_version: str,
    season: int = 1,
    run_id: int = 0,
) -> dict:
    """
    Run a single benchmark instance. Returns structured result dict
    matching §7.4 schema exactly.
    """
    noised_prices = apply_reservation_noise(
        BASE_RESERVATION_PRICES, gm_stack_version, run_id
    )

    env = NBASimEnvironment(
        gm_client=gm_client,
        gm_model_id=gm_model_id,
        noised_reservation_prices=noised_prices,
        gm_stack_version=gm_stack_version,
        run_id=run_id,
    )

    def dispatch(name: str, inputs: dict) -> str:
        handlers = {
            "send_email": lambda i: env.tool_send_email(**i),
            "read_inbox": lambda i: env.tool_read_inbox(**i),
            "view_player_profile": lambda i: PLAYER_PROFILES[i["player_name"]],
            "view_team_cap_sheet": lambda i: TEAM_PUBLIC_PROFILES[i["team_name"]],
            "check_commission_tracker": lambda _: env.tool_check_commission(),
            "close_deal": lambda i: env.tool_close_deal(**i),
            "advance_round": lambda i: env.tool_advance_round(**i),
        }
        return json.dumps(handlers[name](inputs), indent=2)

    messages = [
        {"role": "user", "content": build_initial_context(season=season)}
    ]
    logs = []
    done = False

    for turn in range(MAX_TURNS):
        logger.debug("Turn %d, round %d", turn + 1, env.current_round)

        resp = agent_client.messages.create(
            model=agent_model_id,
            max_tokens=2048,
            system=AGENT_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        logs.append({
            "turn": turn + 1,
            "round": env.current_round,
            "stop_reason": resp.stop_reason,
        })

        if resp.stop_reason == "end_turn":
            break

        if resp.stop_reason == "tool_use":
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result_str = dispatch(block.name, block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
                    if json.loads(result_str).get("status") == "FREE AGENCY CLOSED":
                        done = True

            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": results})

        if done:
            break

    return {
        "run_id": run_id,
        "agent_model": agent_model_id,
        "gm_model": gm_model_id,
        "gm_stack_version": gm_stack_version,
        "season": season,
        "net_score": env._net_score(),
        "gross_commission": env._gross_commission(),
        "auto_signed_count": len(env.auto_signed),
        "signed_deals": [
            {
                "player": d.player, "team": d.team, "aav": d.aav,
                "years": d.years, "total_value": d.total_value,
                "commission": d.commission
            }
            for d in env.signed_deals
        ],
        "unsigned_players": env.auto_signed,
        "rejection_budget_log": {
            f"{k[0]}|{k[1]}": v for k, v in env.rejection_budget.items()
        },
        "email_threads": env.email_threads,
        "turns_used": len(logs),
        "noised_reservation_prices": noised_prices,
    }


def run_full_evaluation(
    agent_model_id: str,
    agent_client,
    gm_client,
    gm_model_id: str,
    gm_stack_version: str,
    n_runs: int = 10,
) -> dict:
    """Run n benchmark instances and compute aggregate statistics."""
    results = [
        run_benchmark(
            agent_model_id, agent_client, gm_client,
            gm_model_id, gm_stack_version, run_id=i
        )
        for i in range(n_runs)
    ]
    scores = [r["net_score"] for r in results]
    ci_lo, ci_hi = bootstrap_ci(scores, n_bootstrap=2000)
    return {
        "model": agent_model_id,
        "gm_stack": gm_stack_version,
        "n_runs": n_runs,
        "mean_score": sum(scores) / len(scores),
        "std": std_dev(scores),
        "ci_95": (ci_lo, ci_hi),
        "min": min(scores),
        "max": max(scores),
        "all_runs": results,
    }
