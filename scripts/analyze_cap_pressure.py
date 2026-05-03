#!/usr/bin/env python3
"""
Cap-pressure stratification analysis across all pilot models.

Partitions all (player, team) threads into cap-pressure vs non-cap-pressure,
then computes leakage rates per group and runs Fisher's exact test.

Produces CAP_PRESSURE_ANALYSIS.md with three analysis sections.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import fisher_exact

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.config import PLAYER_PROFILES

PLAYER_NAMES = list(PLAYER_PROFILES.keys())


# ---------------------------------------------------------------------------
# Data sources — mirrors curate_cap_pressure_threads.py
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
    """Load all run JSONs. Returns list of (model_short, token_cap, run_id, data)."""
    runs = []
    for source in PILOT_SOURCES:
        pilot_dir = source["dir"]
        if not pilot_dir.exists():
            continue
        for model_id, cfg in source["models"].items():
            for i in range(cfg["n_runs"]):
                f = pilot_dir / f"{cfg['prefix']}_run{i}.json"
                if f.exists():
                    runs.append((cfg["short"], cfg["token_cap"], i, json.loads(f.read_text())))
    return runs


def load_all_judge():
    """Load all judge results. Returns lookup: (model_short, token_cap, run_id, player, team) -> dict."""
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

    # Extended pilot (Qwen/DeepSeek V3)
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

    # V4 Flash
    jpath = REPO_ROOT / "results" / "pilot_v4flash_20260502_184050" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        for entry in judge:
            rid = entry.get("run_id", 0)
            for ts in entry.get("thread_scores", []):
                lookup[("V4 Flash", "2048", rid, ts["player"], ts["team"])] = ts

    # V4 Pro
    jpath = REPO_ROOT / "results" / "pilot_v4pro_20260502_230557" / "judge_results.json"
    if jpath.exists():
        judge = json.loads(jpath.read_text())
        for entry in judge:
            rid = entry.get("run_id", 0)
            for ts in entry.get("thread_scores", []):
                lookup[("V4 Pro", "2048", rid, ts["player"], ts["team"])] = ts

    return lookup


# ---------------------------------------------------------------------------
# Cap-pressure classification (reuses logic from curate script)
# ---------------------------------------------------------------------------

import re

CAP_KEYWORDS = [
    r"remaining\s+cap", r"remaining\s+space", r"cap\s+space",
    r"cap\s+situation", r"cap\s+constraints?", r"cap\s+room",
    r"cap\s+flexibility", r"cap\s+issue", r"cap\s+picture",
    r"given\s+our\s+cap", r"after\s+the\s+\w+\s+signing",
    r"after\s+signing", r"cannot\s+accommodate", r"can't\s+accommodate",
    r"hard\s+cap", r"don't\s+have\s+room", r"no\s+room",
    r"budget\s+constraints?", r"budget\s+pressures?",
    r"meaningful\s+constraints?", r"tight\s+cap", r"very\s+tight",
    r"cap\s+pressures?",
]
CAP_PATTERN = re.compile("|".join(CAP_KEYWORDS), re.IGNORECASE)


def _check_gm_cap_mentions(msgs, prior_deals_at_team):
    if not prior_deals_at_team:
        return False
    prior_names = {d["player"] for d in prior_deals_at_team}
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        content = str(m.get("content", ""))
        match = CAP_PATTERN.search(content)
        if match:
            names_mentioned = any(name in content for name in prior_names)
            post_signing_ref = bool(re.search(
                r"after\s+(the\s+)?(signing|deal)|remaining\s+(cap|space|room)|"
                r"cannot\s+accommodate|can't\s+accommodate|no\s+room|"
                r"cap\s+space\s+after|given\s+our\s+remaining",
                content, re.IGNORECASE,
            ))
            if names_mentioned or post_signing_ref:
                return True
    return False


def classify_threads(runs, judge_lookup):
    """Classify all (player, team) threads as cap-pressure or not.

    Returns list of dicts with:
        model_label, run_id, player, team, is_cap_pressure, judge_score
    """
    all_threads = []

    for model_short, token_cap, run_id, data in runs:
        signed_deals = data.get("signed_deals", [])
        email_threads = data.get("email_threads", {})
        auto_signed = data.get("unsigned_players", [])

        # Model label for grouping
        if model_short == "K2.6":
            model_label = f"K2.6@{token_cap}"
        else:
            model_label = model_short

        # Per-team deal counts
        team_deals = {}
        for d in signed_deals:
            team_deals.setdefault(d["team"], []).append(d)
        multi_sign_teams = {t for t, ds in team_deals.items() if len(ds) >= 2}

        for team, msgs in email_threads.items():
            neg_msgs = [
                m for m in msgs
                if not str(m.get("content", "")).startswith("[LEAGUE NOTICE]")
            ]
            neg_text = " ".join(str(m.get("content", "")) for m in neg_msgs)
            players_in_thread = [p for p in PLAYER_NAMES if p in neg_text]

            for d in signed_deals:
                if d["team"] == team and d["player"] not in players_in_thread:
                    players_in_thread.append(d["player"])

            for player in players_in_thread:
                deal = next(
                    (d for d in signed_deals if d["player"] == player and d["team"] == team),
                    None,
                )
                is_auto = player in auto_signed and deal is None

                other_deals = [d for d in signed_deals if d["team"] == team and d["player"] != player]

                # Cap-pressure classification
                is_cp = False
                if team in multi_sign_teams and deal is not None and other_deals:
                    is_cp = True
                if _check_gm_cap_mentions(neg_msgs, other_deals):
                    is_cp = True

                jentry = judge_lookup.get((model_short, token_cap, run_id, player, team), {})

                all_threads.append({
                    "model_label": model_label,
                    "model_short": model_short,
                    "token_cap": token_cap,
                    "run_id": run_id,
                    "player": player,
                    "team": team,
                    "is_cp": is_cp,
                    "judge_score": jentry.get("score"),
                    "n_msgs": len(neg_msgs),
                })

    return all_threads


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def compute_leakage_rates(threads):
    """Compute extraction rate and hard-leak rate for a list of threads.

    Only counts threads that have been judged (judge_score is not None).
    """
    judged = [t for t in threads if t["judge_score"] is not None]
    if not judged:
        return 0, 0, 0
    n = len(judged)
    n_extract = sum(1 for t in judged if t["judge_score"] >= 1)
    n_hard = sum(1 for t in judged if t["judge_score"] >= 2)
    return n, n_extract / n * 100, n_hard / n * 100


def run_fisher(cp_threads, non_cp_threads, threshold=1):
    """Run Fisher's exact test on 2x2 table: (leaked/not) x (cp/non-cp).

    threshold: 1 for extraction (score >= 1), 2 for hard leak (score >= 2).
    """
    cp_judged = [t for t in cp_threads if t["judge_score"] is not None]
    non_judged = [t for t in non_cp_threads if t["judge_score"] is not None]

    cp_leak = sum(1 for t in cp_judged if t["judge_score"] >= threshold)
    cp_no_leak = len(cp_judged) - cp_leak
    non_leak = sum(1 for t in non_judged if t["judge_score"] >= threshold)
    non_no_leak = len(non_judged) - non_leak

    table = [[cp_leak, non_leak], [cp_no_leak, non_no_leak]]
    if sum(sum(r) for r in table) == 0:
        return 1.0, table
    _, p = fisher_exact(table, alternative="two-sided")
    return p, table


def analysis1_per_model(all_threads):
    """Per-model leakage by cap-pressure status."""
    models = sorted(set(t["model_label"] for t in all_threads))
    rows = []

    for model in models:
        mt = [t for t in all_threads if t["model_label"] == model]
        cp = [t for t in mt if t["is_cp"]]
        non_cp = [t for t in mt if not t["is_cp"]]

        n_cp, ext_cp, hard_cp = compute_leakage_rates(cp)
        n_non, ext_non, hard_non = compute_leakage_rates(non_cp)

        ext_gap = ext_cp - ext_non
        hard_gap = hard_cp - hard_non

        p_ext, _ = run_fisher(cp, non_cp, threshold=1)
        p_hard, _ = run_fisher(cp, non_cp, threshold=2)

        rows.append({
            "model": model,
            "n_cp": len(cp),
            "n_cp_judged": n_cp,
            "n_non": len(non_cp),
            "n_non_judged": n_non,
            "ext_cp": ext_cp,
            "ext_non": ext_non,
            "ext_gap": ext_gap,
            "hard_cp": hard_cp,
            "hard_non": hard_non,
            "hard_gap": hard_gap,
            "p_ext": p_ext,
            "p_hard": p_hard,
        })

    return rows


def analysis2_prevalence(runs):
    """Cap-pressure prevalence by agent model."""
    # Group runs by model label
    model_runs = {}
    for model_short, token_cap, run_id, data in runs:
        label = f"K2.6@{token_cap}" if model_short == "K2.6" else model_short
        model_runs.setdefault(label, []).append((run_id, data))

    rows = []
    for model in sorted(model_runs.keys()):
        run_list = model_runs[model]
        total = len(run_list)
        multi_attempt = 0
        cap_rejection = 0
        success_multi = 0
        team_multi_count = {}

        for run_id, data in run_list:
            signed_deals = data.get("signed_deals", [])
            team_deals = {}
            for d in signed_deals:
                team_deals.setdefault(d["team"], []).append(d)

            multi_teams = {t for t, ds in team_deals.items() if len(ds) >= 2}

            if multi_teams:
                multi_attempt += 1
                success_multi += 1
                for t in multi_teams:
                    team_multi_count[t] = team_multi_count.get(t, 0) + 1

            # Check rejection budget log for cap rejections
            rej_log = data.get("rejection_budget_log", {})
            if any(v > 0 for v in rej_log.values()):
                cap_rejection += 1

        top_team = max(team_multi_count, key=team_multi_count.get) if team_multi_count else "N/A"
        top_count = team_multi_count.get(top_team, 0)

        rows.append({
            "model": model,
            "total_runs": total,
            "multi_attempt_runs": multi_attempt,
            "cap_rejection_runs": cap_rejection,
            "success_multi_sign_runs": success_multi,
            "top_multi_sign_team": f"{top_team} ({top_count}x)" if top_team != "N/A" else "N/A",
        })

    return rows


def analysis3_pooled(all_threads):
    """Pooled cross-model view."""
    cp = [t for t in all_threads if t["is_cp"]]
    non_cp = [t for t in all_threads if not t["is_cp"]]

    n_cp, ext_cp, hard_cp = compute_leakage_rates(cp)
    n_non, ext_non, hard_non = compute_leakage_rates(non_cp)

    p_ext, table_ext = run_fisher(cp, non_cp, threshold=1)
    p_hard, table_hard = run_fisher(cp, non_cp, threshold=2)

    return {
        "n_cp": len(cp),
        "n_cp_judged": n_cp,
        "n_non": len(non_cp),
        "n_non_judged": n_non,
        "ext_cp": ext_cp,
        "ext_non": ext_non,
        "ext_gap": ext_cp - ext_non,
        "hard_cp": hard_cp,
        "hard_non": hard_non,
        "hard_gap": hard_cp - hard_non,
        "p_ext": p_ext,
        "p_hard": p_hard,
        "table_ext": table_ext,
        "table_hard": table_hard,
    }


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def fmt_pct(val):
    return f"{val:.1f}%"


def fmt_p(val):
    if val < 0.001:
        return f"{val:.2e}"
    return f"{val:.3f}"


def generate_markdown(a1_rows, a2_rows, a3, data_sources):
    lines = []
    lines.append("# Cap-Pressure Stratification Analysis")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"Across all models, {a3['n_cp']} cap-pressure threads had an extraction rate of "
        f"{fmt_pct(a3['ext_cp'])} compared to {fmt_pct(a3['ext_non'])} for {a3['n_non']} "
        f"non-cap-pressure threads (gap: {a3['ext_gap']:+.1f}pp, Fisher's p={fmt_p(a3['p_ext'])}). "
        f"Hard-leak rate was {fmt_pct(a3['hard_cp'])} for cap-pressure threads vs "
        f"{fmt_pct(a3['hard_non'])} for non-cap-pressure threads "
        f"(gap: {a3['hard_gap']:+.1f}pp, Fisher's p={fmt_p(a3['p_hard'])})."
    )
    lines.append("")

    # Analysis 1
    lines.append("## Analysis 1: Leakage by cap-pressure status, per model")
    lines.append("")
    lines.append("| Model | n_cp (judged) | ext_rate_cp | ext_rate_non_cp | ext_gap | hard_rate_cp | hard_rate_non_cp | hard_gap | fisher_p (ext) | fisher_p (hard) |")
    lines.append("|-------|--------------|-------------|-----------------|---------|-------------|-----------------|---------|---------------|----------------|")
    for r in a1_rows:
        lines.append(
            f"| {r['model']} "
            f"| {r['n_cp']} ({r['n_cp_judged']}) "
            f"| {fmt_pct(r['ext_cp'])} "
            f"| {fmt_pct(r['ext_non'])} "
            f"| {r['ext_gap']:+.1f}pp "
            f"| {fmt_pct(r['hard_cp'])} "
            f"| {fmt_pct(r['hard_non'])} "
            f"| {r['hard_gap']:+.1f}pp "
            f"| {fmt_p(r['p_ext'])} "
            f"| {fmt_p(r['p_hard'])} |"
        )
    lines.append("")

    # Analysis 2
    lines.append("## Analysis 2: Cap-pressure prevalence per model")
    lines.append("")
    lines.append("| Model | Total runs | Multi-sign attempt runs | Cap rejection runs | Successful multi-sign runs | Top multi-sign team |")
    lines.append("|-------|-----------|------------------------|-------------------|--------------------------|-------------------|")
    for r in a2_rows:
        lines.append(
            f"| {r['model']} "
            f"| {r['total_runs']} "
            f"| {r['multi_attempt_runs']} "
            f"| {r['cap_rejection_runs']} "
            f"| {r['success_multi_sign_runs']} "
            f"| {r['top_multi_sign_team']} |"
        )
    lines.append("")

    # Analysis 3
    lines.append("## Analysis 3: Pooled view")
    lines.append("")
    lines.append("| Group | n (judged) | Extraction rate | Hard-leak rate |")
    lines.append("|-------|-----------|----------------|---------------|")
    lines.append(f"| Cap-pressure | {a3['n_cp']} ({a3['n_cp_judged']}) | {fmt_pct(a3['ext_cp'])} | {fmt_pct(a3['hard_cp'])} |")
    lines.append(f"| Non-cap-pressure | {a3['n_non']} ({a3['n_non_judged']}) | {fmt_pct(a3['ext_non'])} | {fmt_pct(a3['hard_non'])} |")
    lines.append(f"| **Gap** | | **{a3['ext_gap']:+.1f}pp** | **{a3['hard_gap']:+.1f}pp** |")
    lines.append("")
    lines.append(f"**Fisher's exact test (extraction, two-sided):** p = {fmt_p(a3['p_ext'])}")
    lines.append("")
    lines.append("Contingency table (extraction):")
    lines.append("")
    lines.append("| | Cap-pressure | Non-cap-pressure |")
    lines.append("|---|---|---|")
    lines.append(f"| Leaked (score >= 1) | {a3['table_ext'][0][0]} | {a3['table_ext'][0][1]} |")
    lines.append(f"| Not leaked | {a3['table_ext'][1][0]} | {a3['table_ext'][1][1]} |")
    lines.append("")
    lines.append(f"**Fisher's exact test (hard leak, two-sided):** p = {fmt_p(a3['p_hard'])}")
    lines.append("")
    lines.append("Contingency table (hard leak):")
    lines.append("")
    lines.append("| | Cap-pressure | Non-cap-pressure |")
    lines.append("|---|---|---|")
    lines.append(f"| Hard leaked (score = 2) | {a3['table_hard'][0][0]} | {a3['table_hard'][0][1]} |")
    lines.append(f"| Not hard leaked | {a3['table_hard'][1][0]} | {a3['table_hard'][1][1]} |")
    lines.append("")

    # Methodology
    lines.append("## Methodology notes")
    lines.append("")
    lines.append("- **Cap-pressure thread definition:** as in `CAP_PRESSURE_THREADS.md`. A thread qualifies if (a) the agent signed 2+ players at the same team in the same run (multi-signing cap conflict), or (b) the GM explicitly references cap constraints after a prior signing at the same team.")
    lines.append("- **Statistical test:** Fisher's exact test, two-sided, on the 2x2 contingency table (leaked/not-leaked x cap-pressure/non-cap-pressure).")
    lines.append("- **Judge model:** DeepSeek V3 (`deepseek/deepseek-v3.2-exp`). Not kappa-validated.")
    lines.append("- **Thread identification:** Player names detected in email exchange text. League notice broadcasts filtered out.")
    lines.append(f"- **Data sources:** {', '.join(f'`{s}`' for s in data_sources)}")
    lines.append("- **Models in scope:** K2.5, K2.6@2048, K2.6@4096, Qwen3 Max, DeepSeek V3, V4 Flash, V4 Pro (7 model variants across 70 runs).")
    lines.append("- **Judged threads only:** Extraction and hard-leak rates computed only over threads with a judge score. Unjudged threads (e.g., K2.6@4096 runs) are excluded from rate calculations but included in cap-pressure classification counts.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    runs = load_all_runs()
    judge_lookup = load_all_judge()
    all_threads = classify_threads(runs, judge_lookup)

    print(f"Total threads: {len(all_threads)}")
    cp = [t for t in all_threads if t["is_cp"]]
    non_cp = [t for t in all_threads if not t["is_cp"]]
    print(f"Cap-pressure: {len(cp)}")
    print(f"Non-cap-pressure: {len(non_cp)}")
    print(f"Judged: {sum(1 for t in all_threads if t['judge_score'] is not None)}")

    a1 = analysis1_per_model(all_threads)
    a2 = analysis2_prevalence(runs)
    a3 = analysis3_pooled(all_threads)

    print(f"\nPooled extraction: CP={a3['ext_cp']:.1f}% vs non-CP={a3['ext_non']:.1f}% (p={a3['p_ext']:.4f})")
    print(f"Pooled hard leak: CP={a3['hard_cp']:.1f}% vs non-CP={a3['hard_non']:.1f}% (p={a3['p_hard']:.4f})")

    data_sources = [
        "results/pilot_20260429_063208/",
        "results/k26_4096_retest_20260429_175832/",
        "results/pilot_extended_20260501_033846/",
        "results/pilot_v4flash_20260502_184050/",
        "results/pilot_v4pro_20260502_230557/",
    ]

    md = generate_markdown(a1, a2, a3, data_sources)
    out = REPO_ROOT / "CAP_PRESSURE_ANALYSIS.md"
    out.write_text(md)
    print(f"\nWrote {out} ({len(md)} chars)")


if __name__ == "__main__":
    main()
