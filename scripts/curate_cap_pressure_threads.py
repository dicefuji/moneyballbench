#!/usr/bin/env python3
"""
Curate cap-pressure threads from all pilot data.

Scans all pilot runs (K2.5, K2.6, K2.6@4096, Qwen3 Max, DeepSeek V3,
V4 Flash, V4 Pro) and identifies threads where cap pressure was a factor —
either through multi-signing at the same team or GM cap-mentions after a
prior signing.

Produces CAP_PRESSURE_THREADS.md with every qualifying thread, verbatim.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.config import PLAYER_PROFILES

PLAYER_NAMES = list(PLAYER_PROFILES.keys())

# Cap-pressure keyword patterns for GM messages
CAP_KEYWORDS = [
    r"remaining\s+cap",
    r"remaining\s+space",
    r"cap\s+space",
    r"cap\s+situation",
    r"cap\s+constraints?",
    r"cap\s+room",
    r"cap\s+flexibility",
    r"cap\s+issue",
    r"cap\s+picture",
    r"given\s+our\s+cap",
    r"after\s+the\s+\w+\s+signing",
    r"after\s+signing",
    r"cannot\s+accommodate",
    r"can't\s+accommodate",
    r"hard\s+cap",
    r"don't\s+have\s+room",
    r"no\s+room",
    r"budget\s+constraints?",
    r"budget\s+pressures?",
    r"meaningful\s+constraints?",
    r"tight\s+cap",
    r"very\s+tight",
    r"cap\s+pressures?",
]
CAP_PATTERN = re.compile("|".join(CAP_KEYWORDS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

PILOT_SOURCES = [
    {
        "dir": REPO_ROOT / "results" / "pilot_20260429_063208",
        "models": {
            "moonshotai/kimi-k2.5": {
                "prefix": "moonshotai_kimi-k2.5",
                "short": "K2.5",
                "token_cap": "2048",
                "n_runs": 10,
            },
            "moonshotai/kimi-k2.6": {
                "prefix": "moonshotai_kimi-k2.6",
                "short": "K2.6",
                "token_cap": "2048",
                "n_runs": 10,
            },
        },
    },
    {
        "dir": REPO_ROOT / "results" / "k26_4096_retest_20260429_175832",
        "models": {
            "moonshotai/kimi-k2.6-4096": {
                "prefix": "k26_4096",
                "short": "K2.6",
                "token_cap": "4096",
                "n_runs": 10,
            },
        },
    },
    {
        "dir": REPO_ROOT / "results" / "pilot_extended_20260501_033846",
        "models": {
            "qwen/qwen3-max": {
                "prefix": "qwen_qwen3-max",
                "short": "Qwen3 Max",
                "token_cap": "2048",
                "n_runs": 10,
            },
            "deepseek/deepseek-v3.2-exp": {
                "prefix": "deepseek_deepseek-v3.2-exp",
                "short": "DeepSeek V3",
                "token_cap": "2048",
                "n_runs": 10,
            },
        },
    },
    {
        "dir": REPO_ROOT / "results" / "pilot_v4flash_20260502_184050",
        "models": {
            "deepseek/deepseek-v4-flash": {
                "prefix": "deepseek_deepseek-v4-flash",
                "short": "V4 Flash",
                "token_cap": "2048",
                "n_runs": 10,
            },
        },
    },
    {
        "dir": REPO_ROOT / "results" / "pilot_v4pro_20260502_230557",
        "models": {
            "deepseek/deepseek-v4-pro": {
                "prefix": "deepseek_deepseek-v4-pro",
                "short": "V4 Pro",
                "token_cap": "2048",
                "n_runs": 10,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_runs():
    """Load all run JSONs across pilot directories.

    Returns list of (model_id, model_short, token_cap, run_id, data, pilot_dir).
    """
    runs = []
    for source in PILOT_SOURCES:
        pilot_dir = source["dir"]
        if not pilot_dir.exists():
            continue
        for model_id, cfg in source["models"].items():
            for i in range(cfg["n_runs"]):
                f = pilot_dir / f"{cfg['prefix']}_run{i}.json"
                if f.exists():
                    runs.append((
                        model_id, cfg["short"], cfg["token_cap"],
                        i, json.loads(f.read_text()), pilot_dir,
                    ))
    return runs


def load_all_judge_lookups():
    """Load judge results from all pilot directories.

    Returns lookup: (model_short, token_cap, run_id, player, team) -> dict.
    """
    lookup = {}

    # Original pilot (K2.5/K2.6 @ 2048)
    jpath = REPO_ROOT / "results" / "pilot_20260429_063208" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        for model_key, run_list in judge.items():
            short = "K2.5" if "k2.5" in model_key else "K2.6"
            for entry in run_list:
                rid = entry.get("run_id", 0)
                for ts in entry.get("thread_scores", []):
                    lookup[(short, "2048", rid, ts["player"], ts["team"])] = ts

    # Extended pilot (Qwen/DeepSeek)
    jpath = REPO_ROOT / "results" / "pilot_extended_20260501_033846" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        model_short_map = {
            "qwen/qwen3-max": "Qwen3 Max",
            "deepseek/deepseek-v3.2-exp": "DeepSeek V3",
        }
        for model_key, run_list in judge.items():
            short = model_short_map.get(model_key, model_key)
            for entry in run_list:
                rid = entry.get("run_id", 0)
                for ts in entry.get("thread_scores", []):
                    lookup[(short, "2048", rid, ts["player"], ts["team"])] = ts

    # V4 Flash judge
    jpath = REPO_ROOT / "results" / "pilot_v4flash_20260502_184050" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        for entry in judge:
            rid = entry.get("run_id", 0)
            for ts in entry.get("thread_scores", []):
                lookup[("V4 Flash", "2048", rid, ts["player"], ts["team"])] = ts

    # V4 Pro judge
    jpath = REPO_ROOT / "results" / "pilot_v4pro_20260502_230557" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        for entry in judge:
            rid = entry.get("run_id", 0)
            for ts in entry.get("thread_scores", []):
                lookup[("V4 Pro", "2048", rid, ts["player"], ts["team"])] = ts

    return lookup


# ---------------------------------------------------------------------------
# Cap-pressure detection
# ---------------------------------------------------------------------------


def _other_deals_at_team(signed_deals, team, player):
    """Get other deals signed at this team by different players.

    Deals signed at the same team don't generate league notices in that
    team's thread, so we can't use signing_order to determine chronological
    ordering. Instead, we treat any deal at this team by a different player
    as a potential "prior" deal for cap-mention detection. The GM's own
    language (e.g., "after the Okafor signing") confirms the temporal
    relationship within the thread text.
    """
    return [
        d for d in signed_deals
        if d["team"] == team and d["player"] != player
    ]


def _check_gm_cap_mentions(msgs, prior_deals_at_team):
    """Check if GM messages mention cap constraints referencing prior signings.

    Returns list of (msg_index, keyword_match) for qualifying mentions.
    """
    if not prior_deals_at_team:
        return []

    prior_names = {d["player"] for d in prior_deals_at_team}
    mentions = []

    for i, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        content = str(m.get("content", ""))
        match = CAP_PATTERN.search(content)
        if match:
            # Check if this is a generic "meaningful constraints" early in
            # negotiation vs a genuine cap-pressure reference.
            # We qualify if any prior deal name is mentioned OR if the
            # language implies post-signing constraint.
            names_mentioned = any(name in content for name in prior_names)
            post_signing_ref = bool(re.search(
                r"after\s+(the\s+)?(signing|deal)|remaining\s+(cap|space|room)|"
                r"cannot\s+accommodate|can't\s+accommodate|no\s+room|"
                r"cap\s+space\s+after|given\s+our\s+remaining",
                content, re.IGNORECASE,
            ))
            if names_mentioned or post_signing_ref:
                mentions.append((i, match.group()))

    return mentions


def find_cap_pressure_threads(runs, judge_lookup):
    """Find all threads where cap pressure was a factor.

    Returns list of qualifying thread records.
    """
    results = []

    for model_id, model_short, token_cap, run_id, data, pilot_dir in runs:
        signed_deals = data.get("signed_deals", [])
        email_threads = data.get("email_threads", {})
        noised = data.get("noised_reservation_prices", {})
        auto_signed = data.get("unsigned_players", [])

        # Build per-team deal counts
        team_deals = {}
        for d in signed_deals:
            team_deals.setdefault(d["team"], []).append(d)

        # Teams with multiple signings (Trigger 1 candidates)
        multi_sign_teams = {t for t, ds in team_deals.items() if len(ds) >= 2}

        for team, msgs in email_threads.items():
            neg_msgs = [
                m for m in msgs
                if not str(m.get("content", "")).startswith("[LEAGUE NOTICE]")
            ]
            neg_text = " ".join(str(m.get("content", "")) for m in neg_msgs)
            players_in_thread = [p for p in PLAYER_NAMES if p in neg_text]

            # Also include players with deals at this team
            for d in signed_deals:
                if d["team"] == team and d["player"] not in players_in_thread:
                    players_in_thread.append(d["player"])

            for player in players_in_thread:
                deal = next(
                    (d for d in signed_deals
                     if d["player"] == player and d["team"] == team),
                    None,
                )
                is_auto = player in auto_signed and deal is None

                other_deals = _other_deals_at_team(
                    signed_deals, team, player,
                )

                triggers = []

                # Trigger 1: Multi-signing cap conflict
                if team in multi_sign_teams and deal is not None and other_deals:
                    triggers.append("Multi-signing cap conflict")

                # Trigger 2: GM cap-mention after prior signing
                cap_mentions = _check_gm_cap_mentions(neg_msgs, other_deals)
                if cap_mentions:
                    triggers.append("GM cap-mention after prior signing")

                if not triggers:
                    continue

                res = noised.get(team, {}).get(player, {})
                res_aav = res.get("max_aav", 0)
                res_years = res.get("max_years", 0)

                capture = None
                if deal and res_aav > 0:
                    capture = deal["aav"] / res_aav * 100

                jentry = judge_lookup.get(
                    (model_short, token_cap, run_id, player, team), {},
                )

                results.append({
                    "model_id": model_id,
                    "model_short": model_short,
                    "token_cap": token_cap,
                    "run_id": run_id,
                    "player": player,
                    "team": team,
                    "triggers": triggers,
                    "prior_deals": other_deals,
                    "deal": deal,
                    "is_auto": is_auto,
                    "capture": capture,
                    "res_aav": res_aav,
                    "res_years": res_years,
                    "judge_score": jentry.get("score"),
                    "judge_evidence": jentry.get("evidence", ""),
                    "n_msgs": len(neg_msgs),
                    "msgs": neg_msgs,
                    "cap_mentions": cap_mentions if cap_mentions else [],
                })

    return results


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_thread(t):
    """Render a single qualifying thread entry."""
    lines = []

    trigger_str = " | ".join(t["triggers"])
    model_label = f"{t['model_short']}@{t['token_cap']}" if t["token_cap"] != "2048" or t["model_short"] == "K2.6" else t["model_short"]
    if t["model_short"] == "K2.6" and t["token_cap"] == "2048":
        model_label = "K2.6@2048"

    lines.append(f"## {t['player']} vs {t['team']} — {model_label}/Run {t['run_id']}")
    lines.append("")
    lines.append(f"**Trigger:** {trigger_str}")
    lines.append("")

    # Deal description
    deal_desc = "no deal"
    if t["is_auto"]:
        deal_desc = "auto-signed"
    elif t["deal"]:
        d = t["deal"]
        deal_desc = f"signed, ${d['aav']}M AAV / {d['years']}yr (${d['total_value']}M total)"

    # Prior deals
    prior_str = "none"
    if t["prior_deals"]:
        prior_parts = []
        for pd in t["prior_deals"]:
            prior_parts.append(f"{pd['player']} (${pd['aav']}M/{pd['years']}yr)")
        prior_str = ", ".join(prior_parts)

    judge_line = f"{t['judge_score'] if t['judge_score'] is not None else 'not judged'}"
    if (t["judge_score"] or 0) >= 1:
        judge_line += f' (judge evidence: "{t["judge_evidence"]}")'

    lines.append("**Key stats:**")
    lines.append(f"- Run ID: {t['run_id']}")
    lines.append(f"- Agent model: {t['model_id']} @ max_tokens={t['token_cap']}")
    lines.append(f"- Prior deals signed at this team in this run: {prior_str}")
    lines.append(f"- This thread's outcome: {deal_desc}")
    if t["capture"] is not None:
        lines.append(f"- Capture rate (this thread): {t['capture']:.1f}%")
    else:
        lines.append("- Capture rate (this thread): N/A")
    lines.append(f"- Leakage judge score: {judge_line}")
    lines.append(f"- Noised reservation price for this team-player: ${t['res_aav']}M, max {t['res_years']} years")
    lines.append("")

    lines.append("**Full thread:**")
    lines.append("")
    for msg in t["msgs"]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        sender = "Agent" if role == "user" else "GM"
        lines.append(f"**{sender}:**")
        lines.append("")
        lines.append(content)
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    runs = load_all_runs()
    judge_lookup = load_all_judge_lookups()
    qualifying = find_cap_pressure_threads(runs, judge_lookup)

    # Sort by model, then run_id, then team, then player
    qualifying.sort(key=lambda x: (x["model_short"], x["token_cap"], x["run_id"], x["team"], x["player"]))

    # Inventory
    by_model = {}
    by_trigger = {"Multi-signing cap conflict": 0, "GM cap-mention after prior signing": 0}
    for t in qualifying:
        label = f"{t['model_short']}@{t['token_cap']}" if t["token_cap"] != "2048" or t["model_short"] in ("K2.6",) else t["model_short"]
        if t["model_short"] == "K2.6" and t["token_cap"] == "2048":
            label = "K2.6@2048"
        by_model[label] = by_model.get(label, 0) + 1
        for trig in t["triggers"]:
            by_trigger[trig] = by_trigger.get(trig, 0) + 1

    parts = [
        "# Cap-Pressure Threads — All Pilot Data",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Source data:** `results/pilot_20260429_063208/`, `results/k26_4096_retest_20260429_175832/`, `results/pilot_extended_20260501_033846/`, `results/pilot_v4flash_20260502_184050/`, `results/pilot_v4pro_20260502_230557/`",
        "",
        "## Inventory",
        "",
        f"**Total qualifying threads:** {len(qualifying)}",
        "",
        "**Breakdown by model:**",
    ]
    for model, count in sorted(by_model.items()):
        parts.append(f"- {model}: {count}")

    parts.append("")
    parts.append("**Breakdown by trigger:**")
    for trigger, count in sorted(by_trigger.items()):
        parts.append(f"- {trigger}: {count}")

    parts.append("")
    parts.append("**Qualification criteria:**")
    parts.append("")
    parts.append("1. **Multi-signing cap conflict:** The agent signed two or more players at the same team in the same run. Both players' threads at that team qualify.")
    parts.append("2. **GM cap-mention after prior signing:** A GM message contains cap-pressure language (e.g., \"remaining cap space,\" \"after the [name] signing,\" \"cannot accommodate\") AND at least one other player was signed at this team earlier in the run. Generic \"meaningful constraints\" language without post-signing context does not qualify.")
    parts.append("")
    parts.append("A thread may qualify under both triggers simultaneously.")
    parts.append("")
    parts.append("---")
    parts.append("")

    for t in qualifying:
        parts.append(render_thread(t))

    md = "\n".join(parts)
    out = REPO_ROOT / "CAP_PRESSURE_THREADS.md"
    out.write_text(md)
    print(f"Wrote {out} ({len(md)} chars)")
    print(f"Total qualifying threads: {len(qualifying)}")
    for model, count in sorted(by_model.items()):
        print(f"  {model}: {count}")
    for trigger, count in sorted(by_trigger.items()):
        print(f"  {trigger}: {count}")


if __name__ == "__main__":
    main()
