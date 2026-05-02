#!/usr/bin/env python3
"""
Curate interesting negotiation threads from Phase 16 pilot data
(Qwen3 Max and DeepSeek V3 agent runs).

Produces INTERESTING_THREADS_QWEN_DEEPSEEK.md with up to 12 curated
threads organized by model, then by category.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.config import PLAYER_PROFILES

PLAYER_NAMES = list(PLAYER_PROFILES.keys())

RESULTS_DIR = REPO_ROOT / "results" / "pilot_extended_20260501_033846"

MODEL_CONFIG = {
    "qwen/qwen3-max": {
        "file_prefix": "qwen_qwen3-max",
        "short": "Qwen3 Max",
        "token_cap": "2048",
    },
    "deepseek/deepseek-v3.2-exp": {
        "file_prefix": "deepseek_deepseek-v3.2-exp",
        "short": "DeepSeek V3",
        "token_cap": "2048",
    },
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_runs():
    """Load all run JSONs. Returns list of (model_id, model_short, run_id, data)."""
    runs = []
    for model_id, cfg in MODEL_CONFIG.items():
        for i in range(10):
            f = RESULTS_DIR / f"{cfg['file_prefix']}_run{i}.json"
            if f.exists():
                runs.append((model_id, cfg["short"], cfg["token_cap"], i, json.loads(f.read_text())))
    return runs


def load_judge():
    """Load judge results. Returns lookup: (model_id, run_id, player, team) -> dict."""
    jpath = RESULTS_DIR / "judge_results.json"
    if not jpath.exists():
        return {}
    judge = json.loads(jpath.read_text())
    lookup = {}
    for model_key, run_list in judge.items():
        for run_entry in run_list:
            rid = run_entry.get("run_id", 0)
            for ts in run_entry.get("thread_scores", []):
                lookup[(model_key, rid, ts["player"], ts["team"])] = ts
    return lookup


# ---------------------------------------------------------------------------
# Thread enumeration
# ---------------------------------------------------------------------------

def enumerate_threads(runs, judge_lookup):
    """Build list of all (player, team) thread records with computed metrics."""
    threads = []
    for model_id, model_short, token_cap, run_id, result in runs:
        noised = result.get("noised_reservation_prices", {})
        signed_deals = result.get("signed_deals", [])
        auto_signed_players = result.get("unsigned_players", [])
        email_threads = result.get("email_threads", {})
        rej_log = result.get("rejection_budget_log", {})
        turns_used = result.get("turns_used", 0)

        deal_by_pt = {(d["player"], d["team"]): d for d in signed_deals}

        for team, msgs in email_threads.items():
            # Filter league notices
            negotiation_msgs = [
                m for m in msgs
                if not str(m.get("content", "")).startswith("[LEAGUE NOTICE]")
            ]
            negotiation_text = " ".join(
                str(m.get("content", "")) for m in negotiation_msgs
            )
            players_in_thread = [p for p in PLAYER_NAMES if p in negotiation_text]

            for d in signed_deals:
                if d["team"] == team and d["player"] not in players_in_thread:
                    players_in_thread.append(d["player"])

            for player in players_in_thread:
                deal = deal_by_pt.get((player, team))
                is_auto = player in auto_signed_players and deal is None

                res = noised.get(team, {}).get(player, {})
                res_aav = res.get("max_aav", 0)
                res_years = res.get("max_years", 0)

                best_team, best_aav = None, 0
                for t, pdict in noised.items():
                    if player in pdict and pdict[player]["max_aav"] > best_aav:
                        best_aav = pdict[player]["max_aav"]
                        best_team = t

                capture = None
                if deal and res_aav > 0:
                    capture = deal["aav"] / res_aav * 100

                jentry = judge_lookup.get((model_id, run_id, player, team), {})

                threads.append({
                    "model_id": model_id,
                    "model_short": model_short,
                    "token_cap": token_cap,
                    "run_id": run_id,
                    "player": player,
                    "team": team,
                    "n_msgs": len(negotiation_msgs),
                    "msgs": negotiation_msgs,
                    "deal": deal,
                    "is_auto": is_auto,
                    "capture": capture,
                    "res_aav": res_aav,
                    "res_years": res_years,
                    "best_team": best_team,
                    "best_aav": best_aav,
                    "routing_correct": team == best_team,
                    "routing_gap": best_aav - res_aav if deal and not (team == best_team) else 0,
                    "judge_score": jentry.get("score"),
                    "judge_evidence": jentry.get("evidence", ""),
                    "judge_reasoning": jentry.get("reasoning", ""),
                    "rej_count": rej_log.get(f"{player}|{team}", rej_log.get(f"{player}:{team}", 0)),
                    "turns_used": turns_used,
                })
    return threads


# ---------------------------------------------------------------------------
# Category selection (per model)
# ---------------------------------------------------------------------------

def _thread_key(t):
    """Unique key for a thread to track already-selected entries."""
    return (t["run_id"], t["player"], t["team"])


def _pick_not_selected(ranked, already):
    """Pick the first thread from ranked list not already selected."""
    for t in ranked:
        if _thread_key(t) not in already:
            return t
    return ranked[0] if ranked else None


def select_threads_for_model(threads, model_id, is_self_play=False):
    """Select up to 6 threads for a model based on category criteria."""
    model_threads = [t for t in threads if t["model_id"] == model_id and t["n_msgs"] >= 2]
    completed = [t for t in model_threads if t["capture"] is not None and not t["is_auto"]]
    selections = []
    already = set()

    # 1. High capture rate — highest capture, prefer longer threads as tiebreaker
    high_cap = sorted(completed, key=lambda x: (-x["capture"], -x["n_msgs"]))
    if high_cap:
        pick = high_cap[0]
        if pick["n_msgs"] < 4 and len(high_cap) > 1:
            pick = high_cap[1]
        selections.append(("High capture rate", pick))
        already.add(_thread_key(pick))

    # 2. Low capture rate — lowest capture, exclude auto-signs, prefer longer threads
    low_cap = sorted(completed, key=lambda x: (x["capture"], -x["n_msgs"]))
    pick = _pick_not_selected(low_cap, already)
    if pick:
        if pick["n_msgs"] < 4:
            alt = _pick_not_selected([t for t in low_cap if t["n_msgs"] >= 4], already)
            if alt:
                pick = alt
        selections.append(("Low capture rate", pick))
        already.add(_thread_key(pick))

    # 3. Likely leakage — highest judge score, then longest evidence
    leaked = sorted(
        [t for t in model_threads if (t["judge_score"] or 0) >= 1],
        key=lambda x: (-x["judge_score"], -len(x["judge_evidence"])),
    )
    pick = _pick_not_selected(leaked, already)
    if pick:
        selections.append(("Likely leakage", pick))
        already.add(_thread_key(pick))

    # 4. Rejection budget pressure — highest rej_count
    by_rej = sorted(
        [t for t in model_threads if t["rej_count"] >= 2],
        key=lambda x: -x["rej_count"],
    )
    pick = _pick_not_selected(by_rej, already)
    if pick:
        selections.append(("Rejection budget pressure", pick))
        already.add(_thread_key(pick))
    else:
        selections.append(("Rejection budget pressure", None))

    # 5. Routing mistake (Qwen) or skip for DeepSeek
    routing = sorted(
        [t for t in completed if t["routing_gap"] > 0],
        key=lambda x: -x["routing_gap"],
    )
    if not is_self_play:
        pick = _pick_not_selected(routing, already)
        if pick:
            selections.append(("Routing mistake", pick))
            already.add(_thread_key(pick))
        else:
            selections.append(("Routing mistake", None))

    # 6. Length outlier — longest thread
    by_len = sorted(model_threads, key=lambda x: -x["n_msgs"])
    pick = _pick_not_selected(by_len, already)
    if pick:
        selections.append(("Length outlier", pick))
        already.add(_thread_key(pick))

    # Self-play observation (DeepSeek only)
    if is_self_play:
        candidates = sorted(
            [t for t in completed if _thread_key(t) not in already],
            key=lambda x: (-x["n_msgs"], -x["capture"]),
        )
        if candidates:
            selections.append(("Self-play observation", candidates[0]))
        elif routing:
            pick = _pick_not_selected(routing, already)
            if pick:
                selections.append(("Self-play observation", pick))

    return selections


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_thread_entry(category, thread, model_label):
    """Render a single thread entry in markdown."""
    t = thread
    lines = []

    deal_desc = "no deal"
    if t["is_auto"]:
        deal_desc = "auto-signed"
    elif t["deal"]:
        d = t["deal"]
        deal_desc = f"signed, ${d['aav']}M AAV / {d['years']}yr (${d['total_value']}M total)"

    judge_line = f"{t['judge_score'] if t['judge_score'] is not None else 'not judged'}"
    if (t["judge_score"] or 0) >= 1:
        judge_line += f' (judge evidence: "{t["judge_evidence"]}")'

    lines.append(f"## [{model_label} — {category}] — {t['player']} vs {t['team']} — Run ID {t['run_id']}")
    lines.append("")

    # Why interesting
    why_map = {
        "High capture rate": f"Highest capture rate among {model_label} completed deals.",
        "Low capture rate": f"Lowest capture rate among {model_label} completed deals (excluding auto-signs).",
        "Likely leakage": f"{'Hard leak (judge score 2)' if t['judge_score'] == 2 else 'Soft leak (judge score 1)'} — strongest leakage signal in {model_label} runs.",
        "Rejection budget pressure": f"Highest rejection budget usage ({t['rej_count']}/3) among {model_label} threads.",
        "Routing mistake": f"Agent signed at a team with ${t['routing_gap']:.1f}M lower reservation than the best available team.",
        "Length outlier": f"Longest negotiation thread among {model_label} runs ({t['n_msgs']} messages).",
        "Self-play observation": f"Notable same-model negotiation thread — DeepSeek V3 as both agent and GM ({t['n_msgs']} messages).",
    }
    lines.append(f"**Why interesting:** {why_map.get(category, category)}")
    lines.append("")

    lines.append("**Key stats:**")
    lines.append(f"- Run ID: {t['run_id']}")
    lines.append(f"- Agent model: {t['model_id']} @ max_tokens={t['token_cap']}")
    lines.append(f"- Capture rate (this player): {t['capture']:.1f}%" if t["capture"] is not None else "- Capture rate: N/A (no deal at this team)")
    lines.append(f"- Final deal: {deal_desc}")
    lines.append(f"- Thread length: {t['n_msgs']} messages")
    lines.append(f"- Leakage judge score: {judge_line}")
    lines.append(f"- Rejection budget used: {t['rej_count']}/3")
    lines.append(f"- Noised reservation price for this team-player: ${t['res_aav']}M, max {t['res_years']} years")
    lines.append(f"- Highest noised reservation price across teams: ${t['best_aav']}M at {t['best_team']}")
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


def build_methodology(all_threads):
    """Build the selection methodology section."""
    qwen_threads = [t for t in all_threads if t["model_short"] == "Qwen3 Max"]
    ds_threads = [t for t in all_threads if t["model_short"] == "DeepSeek V3"]
    qwen_completed = [t for t in qwen_threads if t["capture"] is not None and not t["is_auto"]]
    ds_completed = [t for t in ds_threads if t["capture"] is not None and not t["is_auto"]]

    lines = [
        "## Selection Methodology",
        "",
        "### Population",
        "",
        f"- **Qwen3 Max:** {len(qwen_threads)} total (player, team) threads across 10 runs; {len(qwen_completed)} with completed deals at the thread's team",
        f"- **DeepSeek V3:** {len(ds_threads)} total (player, team) threads across 10 runs; {len(ds_completed)} with completed deals at the thread's team",
        "",
        "### Thread identification",
        "",
        "- Threads identified by detecting player names in email exchange text (league notices filtered out)",
        "- Only messages that are not `[LEAGUE NOTICE]` broadcasts are counted toward thread length",
        "- Capture rate = (deal AAV / noised reservation max AAV) × 100%",
        "",
        "### Per-category ranking criteria",
        "",
        "- **High capture rate:** Sorted by capture rate descending. Tiebreaker: longer thread (more messages). Skipped if thread < 4 messages (trivial accept).",
        "- **Low capture rate:** Sorted by capture rate ascending, excluding auto-signs. Tiebreaker: longer thread. Skipped if < 4 messages.",
        "- **Likely leakage:** Sorted by judge score descending (2 > 1), then by evidence string length. Score-2 threads prioritized over score-1.",
        "- **Rejection budget pressure:** Sorted by rejection count descending. Category skipped if no threads reached ≥2 rejections.",
        "- **Routing mistake (Qwen only):** Sorted by reservation gap (best team AAV minus signed team AAV) descending.",
        "- **Length outlier:** Longest thread by message count, excluding any thread already selected in a prior category.",
        "- **Self-play observation (DeepSeek only):** Longest completed-deal thread not already selected, to capture distinctive same-model negotiation dynamics.",
        "",
        "### Exclusions",
        "",
        "- Auto-signed players excluded from capture rate rankings (no negotiation occurred)",
        "- League notice messages excluded from thread text and message counts",
        "- Threads with < 2 negotiation messages excluded from all categories",
        "- Duplicate (same player/team from same run) already selected in a prior category excluded from subsequent categories",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def main():
    runs = load_runs()
    judge_lookup = load_judge()
    all_threads = enumerate_threads(runs, judge_lookup)

    # Select per model
    qwen_selections = select_threads_for_model(all_threads, "qwen/qwen3-max", is_self_play=False)
    ds_selections = select_threads_for_model(all_threads, "deepseek/deepseek-v3.2-exp", is_self_play=True)

    # Build markdown
    parts = [
        "# Interesting Threads — Qwen3 Max & DeepSeek V3 (Phase 16 Pilot)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "**Source data:** `results/pilot_extended_20260501_033846/`",
        "**GM:** `openrouter:deepseek/deepseek-v3.2-exp` (temperature 0.3)",
        "**Judge:** `openrouter:deepseek/deepseek-v3.2-exp`",
        "",
        "---",
        "",
        build_methodology(all_threads),
        "# Qwen3 Max (`qwen/qwen3-max`)",
        "",
    ]

    qwen_count = 0
    for category, thread in qwen_selections:
        if thread is None:
            parts.append(f"## [Qwen3 Max — {category}]")
            parts.append("")
            parts.append("**No candidates.** No threads met the criteria for this category.")
            parts.append("")
            parts.append("---")
            parts.append("")
        else:
            parts.append(render_thread_entry(category, thread, "Qwen3 Max"))
            qwen_count += 1

    parts.append("# DeepSeek V3 — Self-Play (`deepseek/deepseek-v3.2-exp`)")
    parts.append("")

    ds_count = 0
    for category, thread in ds_selections:
        if thread is None:
            parts.append(f"## [DeepSeek V3 — {category}]")
            parts.append("")
            parts.append("**No candidates.** No threads met the criteria for this category.")
            parts.append("")
            parts.append("---")
            parts.append("")
        else:
            parts.append(render_thread_entry(category, thread, "DeepSeek V3"))
            ds_count += 1

    md = "\n".join(parts)
    out = REPO_ROOT / "INTERESTING_THREADS_QWEN_DEEPSEEK.md"
    out.write_text(md)
    print(f"Wrote {out} ({len(md)} chars)")
    print(f"Qwen3 Max: {qwen_count} threads curated")
    print(f"DeepSeek V3: {ds_count} threads curated")
    print(f"Total: {qwen_count + ds_count} threads")


if __name__ == "__main__":
    main()
