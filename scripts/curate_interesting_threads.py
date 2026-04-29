#!/usr/bin/env python3
"""
Curate the most interesting negotiation threads from pilot data.

Scans all pilot run results, computes per-thread metrics, applies
category-specific selection rules, and writes INTERESTING_THREADS.md.
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

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_runs(pilot_dir: Path, k26_retest_dir: Path | None = None):
    """Load all run result JSONs. Returns list of (model_short, token_cap, run_id, data)."""
    runs = []
    for i in range(10):
        for model in ["moonshotai_kimi-k2.5", "moonshotai_kimi-k2.6"]:
            f = pilot_dir / f"{model}_run{i}.json"
            if f.exists():
                short = "K2.5" if "k2.5" in model else "K2.6"
                runs.append((short, "2048", i, json.loads(f.read_text())))
    if k26_retest_dir and k26_retest_dir.exists():
        for i in range(20):
            f = k26_retest_dir / f"k26_4096_run{i}.json"
            if f.exists():
                runs.append(("K2.6", "4096", i, json.loads(f.read_text())))
    return runs


def load_judge(pilot_dir: Path):
    """Load judge results into lookup: (model_short, token_cap, run_id, player, team) -> dict.

    Judge data only covers the original pilot runs (all at 2048 tokens),
    so we key with token_cap='2048' to avoid collisions with K2.6@4096
    retest threads that share the same run_id values.
    """
    jpath = pilot_dir / "judge_results.json"
    if not jpath.exists():
        return {}
    judge = json.loads(jpath.read_text())
    lookup = {}
    for model_key, run_list in judge.items():
        short = "K2.5" if "k2.5" in model_key else "K2.6"
        for run_entry in run_list:
            rid = run_entry["run_id"]
            for ts in run_entry.get("thread_scores", []):
                lookup[(short, "2048", rid, ts["player"], ts["team"])] = ts
    return lookup


# ---------------------------------------------------------------------------
# Thread enumeration
# ---------------------------------------------------------------------------

def enumerate_threads(runs, judge_lookup):
    """Build list of all (player, team) thread records with computed metrics."""
    threads = []
    for model, tokens, run_id, result in runs:
        noised = result.get("noised_reservation_prices", {})
        signed_deals = result.get("signed_deals", [])
        auto_signed_players = result.get("unsigned_players", [])
        email_threads = result.get("email_threads", {})
        rej_log = result.get("rejection_budget_log", {})
        turns_used = result.get("turns_used", 0)

        deal_by_pt = {(d["player"], d["team"]): d for d in signed_deals}

        for team, msgs in email_threads.items():
            thread_text = " ".join(str(m.get("content", "")) for m in msgs)
            players_in_thread = [p for p in PLAYER_NAMES if p in thread_text]

            # Also include players mentioned in deals with this team
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

                jentry = judge_lookup.get((model, tokens, run_id, player, team), {})

                threads.append({
                    "model": model,
                    "tokens": tokens,
                    "run_id": run_id,
                    "player": player,
                    "team": team,
                    "n_msgs": len(msgs),
                    "msgs": msgs,
                    "deal": deal,
                    "is_auto": is_auto,
                    "capture": capture,
                    "res_aav": res_aav,
                    "res_years": res_years,
                    "best_team": best_team,
                    "best_aav": best_aav,
                    "routing_correct": team == best_team,
                    "judge_score": jentry.get("score"),
                    "judge_evidence": jentry.get("evidence", ""),
                    "judge_reasoning": jentry.get("reasoning", ""),
                    "rej_count": rej_log.get(f"{player}|{team}", 0),
                    "turns_used": turns_used,
                })
    return threads


# ---------------------------------------------------------------------------
# Category selection
# ---------------------------------------------------------------------------

def _diverse_pick(ranked, n=2):
    """Pick up to n items, preferring one per model. Falls back to same model if needed."""
    selected = []
    # First pass: one per model
    for t in ranked:
        if len(selected) >= n:
            break
        if t["n_msgs"] <= 2:
            continue
        models_so_far = {s["model"] for s in selected}
        if t["model"] not in models_so_far:
            selected.append(t)
    # Second pass: fill remaining slots from any model
    if len(selected) < n:
        for t in ranked:
            if len(selected) >= n:
                break
            if t in selected or t["n_msgs"] <= 2:
                continue
            selected.append(t)
    return selected


def select_high_capture(threads):
    dealt = [t for t in threads if t["deal"] and not t["is_auto"] and t["capture"]]
    ranked = sorted(dealt, key=lambda t: (-t["capture"], -t["n_msgs"]))
    return _diverse_pick(ranked, 2)


def select_low_capture(threads):
    dealt = [t for t in threads if t["deal"] and not t["is_auto"] and t["capture"]]
    ranked = sorted(dealt, key=lambda t: (t["capture"], -t["n_msgs"]))
    return _diverse_pick(ranked, 2)


def select_hard_leak(threads):
    hard = [t for t in threads if t["judge_score"] == 2]
    return sorted(hard, key=lambda t: -len(t["judge_evidence"]))[:2]


def select_soft_leak(threads):
    soft = [t for t in threads if t["judge_score"] == 1]
    return sorted(soft, key=lambda t: -len(t["judge_evidence"]))[:1]


def select_rejection_budget(threads):
    rej = sorted([t for t in threads if t["rej_count"] > 0], key=lambda t: -t["rej_count"])
    selected = []
    # One with max rejections + lockout, one with 2 rejections then success
    for t in rej:
        if t["rej_count"] >= 3 and not any(s["rej_count"] >= 3 for s in selected):
            selected.append(t)
        elif t["rej_count"] == 2 and t["deal"] and not any(s.get("_is_success_after_rej") for s in selected):
            t["_is_success_after_rej"] = True
            selected.append(t)
        if len(selected) >= 2:
            break
    return selected


def select_length_outlier(threads):
    completed = [t for t in threads if t["deal"] and not t["is_auto"] and t["n_msgs"] > 0]
    ranked = sorted(completed, key=lambda t: -t["n_msgs"])
    return ranked[:1]


def select_routing_mistake(threads):
    dealt = [t for t in threads if t["deal"] and not t["is_auto"] and not t["routing_correct"] and t["best_aav"] > 0]
    # Pick the one with largest money-left-on-table
    ranked = sorted(dealt, key=lambda t: -(t["best_aav"] - t["res_aav"]))
    return ranked[:1]


def select_k26_truncation(threads, runs):
    """Select one K2.6@2048 run that shows truncation failure mode."""
    # Prefer a run that partially engaged (has some msgs) but failed
    # Over a run with 0 msgs (less interesting to read)
    k26_fail_runs = [
        (model, tokens, rid, r) for model, tokens, rid, r in runs
        if model == "K2.6" and tokens == "2048" and len(r.get("signed_deals", [])) == 0
    ]
    # Sort by total msgs descending (more content = more interesting)
    k26_fail_runs.sort(key=lambda x: -sum(len(m) for m in x[3].get("email_threads", {}).values()))

    if not k26_fail_runs:
        return []

    # Pick the one with most partial engagement
    _, _, rid, r = k26_fail_runs[0]
    return [{
        "model": "K2.6",
        "tokens": "2048",
        "run_id": rid,
        "player": "(full run)",
        "team": "(all teams)",
        "n_msgs": sum(len(m) for m in r.get("email_threads", {}).values()),
        "msgs": None,  # Will handle specially
        "deal": None,
        "is_auto": False,
        "capture": None,
        "res_aav": 0,
        "res_years": 0,
        "best_team": None,
        "best_aav": 0,
        "routing_correct": True,
        "judge_score": None,
        "judge_evidence": "",
        "judge_reasoning": "",
        "rej_count": 0,
        "turns_used": r.get("turns_used", 0),
        "_full_run": r,
    }]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_thread_messages(msgs):
    """Render email messages as verbatim markdown."""
    lines = []
    for m in msgs:
        role = m.get("role", "unknown")
        label = "**Agent:**" if role == "user" else "**GM:**"
        lines.append(f"{label}\n")
        lines.append(str(m.get("content", "")) + "\n")
        lines.append("---\n")
    return "\n".join(lines)


def render_thread_entry(t, category):
    """Render a single curated thread entry."""
    model_label = f"{t['model']}@{t['tokens']}"
    player = t["player"]
    team = t["team"]
    run_id = t["run_id"]

    lines = [f"## [{category}] -- {player} vs {team} -- {model_label}/run{run_id}\n"]

    lines.append(f"**Why interesting:** {t.get('_why', 'Strongest example in this category.')}\n")

    # Key stats
    lines.append("**Key stats:**\n")
    lines.append(f"- Run ID: {run_id}")
    lines.append(f"- Agent model: {model_label}")
    if t["capture"] is not None:
        lines.append(f"- Capture rate (this player): {t['capture']:.1f}%")
    else:
        lines.append("- Capture rate (this player): N/A")

    if t["deal"]:
        d = t["deal"]
        lines.append(f"- Final deal: signed, ${d['aav']}M AAV x {d['years']}yr (${d['total_value']}M total)")
    elif t["is_auto"]:
        lines.append("- Final deal: auto-signed ($1M/1yr penalty)")
    else:
        lines.append("- Final deal: no deal")

    lines.append(f"- Thread length: {t['n_msgs']} messages")

    if t["judge_score"] is not None:
        ev = f' (judge evidence: "{t["judge_evidence"]}")' if t["judge_score"] >= 1 and t["judge_evidence"] != "none" else ""
        lines.append(f"- Leakage judge score: {t['judge_score']}{ev}")
    else:
        lines.append("- Leakage judge score: not judged")

    lines.append(f"- Rejection budget used: {t['rej_count']}/3")
    lines.append(f"- Noised reservation price for this team-player: ${t['res_aav']}M, max {t['res_years']} years")
    lines.append(f"- Highest noised reservation price across teams: ${t['best_aav']}M at {t['best_team']}")
    lines.append("")

    # Full thread
    lines.append("**Full thread:**\n")
    if t.get("_full_run"):
        # K2.6 truncation: show all team threads
        r = t["_full_run"]
        et = r.get("email_threads", {})
        for team_name, msgs in et.items():
            if msgs:
                lines.append(f"### {team_name} ({len(msgs)} messages)\n")
                lines.append(render_thread_messages(msgs))
            else:
                lines.append(f"### {team_name}\n")
                lines.append("*No messages — agent never contacted this team.*\n")
    elif t["msgs"]:
        lines.append(render_thread_messages(t["msgs"]))
    else:
        lines.append("*No messages in this thread.*\n")

    return "\n".join(lines)


def generate_markdown(selections, total_threads, total_dealt, methodology_notes):
    """Generate the full INTERESTING_THREADS.md."""
    lines = []
    lines.append("# Interesting Negotiation Threads from Pilot\n")
    lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n")

    # Methodology section
    lines.append("## Selection Methodology\n")
    lines.append(f"**Total population:** {total_threads} player-team threads across all pilot runs "
                 f"(K2.5@2048 n=10, K2.6@2048 n=10, K2.6@4096 n=7).\n")
    lines.append(f"**Threads with negotiated deals:** {total_dealt} (excludes auto-signs and failed runs "
                 "where agent never engaged tools).\n")

    for note in methodology_notes:
        lines.append(f"- {note}")
    lines.append("")

    # Curated threads
    count = sum(len(v) for v in selections.values())
    lines.append(f"## Curated Threads ({count} total)\n")

    for category, threads in selections.items():
        if not threads:
            lines.append(f"### {category}\n")
            lines.append("*No candidates found in this category. See methodology notes above.*\n")
            continue
        for t in threads:
            lines.append(render_thread_entry(t, category))
            lines.append("\n---\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pilot_dir = REPO_ROOT / "results" / "pilot_20260429_063208"
    k26_dir = REPO_ROOT / "results" / "k26_4096_retest_20260429_175832"

    if not pilot_dir.exists():
        print(f"Pilot directory not found: {pilot_dir}")
        sys.exit(1)

    runs = load_runs(pilot_dir, k26_dir)
    judge_lookup = load_judge(pilot_dir)
    threads = enumerate_threads(runs, judge_lookup)

    total_threads = len(threads)
    dealt = [t for t in threads if t["deal"] and not t["is_auto"]]
    total_dealt = len(dealt)

    print(f"Total player-team threads: {total_threads}")
    print(f"Threads with negotiated deals: {total_dealt}")

    # Run selections
    high_cap = select_high_capture(threads)
    for t in high_cap:
        t["_why"] = (
            f"Highest capture rate in category ({t['capture']:.1f}%) — "
            f"agent extracted ${t['deal']['aav']}M against a ${t['res_aav']}M reservation."
        )

    low_cap = select_low_capture(threads)
    for t in low_cap:
        t["_why"] = (
            f"Lowest capture rate among completed deals ({t['capture']:.1f}%) — "
            f"agent settled for ${t['deal']['aav']}M against a ${t['res_aav']}M reservation."
        )

    hard_leak = select_hard_leak(threads)
    for t in hard_leak:
        t["_why"] = f"Judge scored this thread 2 (hard leak)."

    soft_leak = select_soft_leak(threads)
    for t in soft_leak:
        t["_why"] = f"Judge scored this thread 1 (soft leak) with evidence quote."

    rej_budget = select_rejection_budget(threads)
    for t in rej_budget:
        if t["rej_count"] >= 3:
            t["_why"] = f"Agent hit {t['rej_count']} rejections — maximum budget pressure."
        else:
            t["_why"] = f"Agent hit {t['rej_count']} rejections then closed successfully."

    length_outlier = select_length_outlier(threads)
    for t in length_outlier:
        t["_why"] = f"Longest completed thread at {t['n_msgs']} messages."

    routing = select_routing_mistake(threads)
    for t in routing:
        gap = t["best_aav"] - t["res_aav"]
        t["_why"] = (
            f"Routing mistake — signed at {t['team']} (res ${t['res_aav']}M) instead of "
            f"{t['best_team']} (res ${t['best_aav']}M), leaving ${gap:.1f}M of reservation headroom on the table."
        )

    k26_trunc = select_k26_truncation(threads, runs)
    for t in k26_trunc:
        t["_why"] = (
            f"K2.6@2048 truncation failure — agent partially engaged "
            f"({t['n_msgs']} messages, {t['turns_used']} turns) but never closed any deals."
        )

    selections = {
        "High Capture Rate": high_cap,
        "Low Capture Rate": low_cap,
        "Hard Leak (Judge Score 2)": hard_leak,
        "Soft Leak (Judge Score 1)": soft_leak,
        "Rejection Budget Pressure": rej_budget,
        "Length Outlier": length_outlier,
        "Routing Mistake": routing,
        "K2.6 Truncation Crash": k26_trunc,
    }

    # Print summary
    for cat, sel in selections.items():
        if sel:
            for t in sel:
                print(f"  [{cat}] {t['model']}@{t['tokens']} run{t['run_id']}: {t['player']} -> {t['team']}")
        else:
            print(f"  [{cat}] NO CANDIDATES")

    methodology_notes = [
        "**Ranking criteria per category:**",
        "  - *High capture rate:* Sorted by capture rate (deal AAV / reservation max AAV) descending. "
        "Tiebreaker: prefer threads with more messages (longer negotiation is more interesting to read). "
        "Diversity rule: one K2.5 thread and one K2.6 thread if both have candidates.",
        "  - *Low capture rate:* Sorted by capture rate ascending. Same tiebreaker and diversity rule. "
        "Excluded auto-signs (which have no negotiation to read).",
        "  - *Hard leak (score 2):* Sorted by judge evidence length descending (longer evidence = more detailed finding). "
        "Target: 2 threads on different players if available.",
        "  - *Soft leak (score 1):* Sorted by judge evidence length descending. Target: 1 thread with clearest evidence quote.",
        "  - *Rejection budget pressure:* Sorted by rejection count descending. "
        "Target: one thread with 3 rejections (lockout) and one with 2 rejections followed by a successful deal.",
        "  - *Length outlier:* Sorted by message count descending among completed-deal threads. Picked the single longest.",
        "  - *Routing mistake:* Among deals where agent signed at a team other than the highest-reservation team, "
        "sorted by reservation gap (best_team_res - actual_team_res) descending. Picked the largest money-left-on-table case.",
        "  - *K2.6 truncation crash:* Among K2.6@2048 failed runs (0 deals), picked the run with the most partial "
        "engagement (most total messages) to show the failure mode mid-negotiation, not just a blank run.",
        "",
        "**Exclusions:**",
        "  - Threads with <= 2 messages were excluded from capture-rate categories (too short to be interesting).",
        "  - Auto-signed players were excluded from capture-rate calculations (no negotiation occurred).",
        "  - K2.6@2048 runs with 0 messages were not selected for the truncation category "
        "(a run with partial engagement is more informative than a blank failure).",
    ]

    md = generate_markdown(selections, total_threads, total_dealt, methodology_notes)

    out_path = REPO_ROOT / "INTERESTING_THREADS.md"
    out_path.write_text(md)
    print(f"\nWrote {out_path} ({len(md)} chars)")


if __name__ == "__main__":
    main()
