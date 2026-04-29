#!/usr/bin/env python3
"""
MoneyBall Bench v3.0 — Leakage Judge Validation Harness (§9.5).

Loads 50 hand-graded threads from a CSV, runs the judge on each,
and computes Cohen's kappa for judge vs. researcher_A, judge vs.
researcher_B, and researcher_A vs. researcher_B.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

try:
    from scipy.stats import cohen_kappa_score
except ImportError:
    cohen_kappa_score = None


def load_graded_threads(csv_path: str) -> list[dict]:
    """
    Load hand-graded threads from CSV.

    Expected columns:
        thread_id, player, team, researcher_a_score, researcher_b_score,
        gm_messages_json
    """
    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "thread_id": row["thread_id"],
                "player": row["player"],
                "team": row["team"],
                "researcher_a": int(row["researcher_a_score"]),
                "researcher_b": int(row["researcher_b_score"]),
                "gm_messages": json.loads(row["gm_messages_json"]),
            })
    return rows


def compute_kappa(scores_a: list[int], scores_b: list[int]) -> float:
    """Compute Cohen's kappa between two score lists."""
    if cohen_kappa_score is None:
        raise ImportError("scipy is required for Cohen's kappa computation")
    return float(cohen_kappa_score(scores_a, scores_b))


def run_validation(
    csv_path: str,
    judge_client=None,
    judge_model: str = "claude-sonnet-4-6-20250514",
    dry_run: bool = False,
) -> dict:
    """
    Run the full validation procedure.

    Returns dict with kappa values and pass/fail status.
    """
    threads = load_graded_threads(csv_path)

    researcher_a = [t["researcher_a"] for t in threads]
    researcher_b = [t["researcher_b"] for t in threads]

    if dry_run:
        judge_scores = [0] * len(threads)
    else:
        from moneyballbench.leakage_judge import score_thread
        judge_scores = []
        for t in threads:
            result = score_thread(t["gm_messages"], judge_client, judge_model)
            judge_scores.append(result["score"])

    kappa_judge_a = compute_kappa(judge_scores, researcher_a)
    kappa_judge_b = compute_kappa(judge_scores, researcher_b)
    kappa_a_b = compute_kappa(researcher_a, researcher_b)

    pass_threshold = 0.7
    return {
        "kappa_judge_vs_researcher_a": kappa_judge_a,
        "kappa_judge_vs_researcher_b": kappa_judge_b,
        "kappa_researcher_a_vs_b": kappa_a_b,
        "pass_threshold": pass_threshold,
        "judge_passes_vs_a": kappa_judge_a >= pass_threshold,
        "judge_passes_vs_b": kappa_judge_b >= pass_threshold,
        "overall_pass": (
            kappa_judge_a >= pass_threshold and kappa_judge_b >= pass_threshold
        ),
        "n_threads": len(threads),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate leakage judge against hand-graded threads"
    )
    parser.add_argument(
        "--csv", required=True, help="Path to hand-graded threads CSV"
    )
    parser.add_argument(
        "--judge-model", default="claude-sonnet-4-6-20250514",
        help="Model ID for the leakage judge"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without API calls (uses score=0 for all threads)"
    )
    args = parser.parse_args()

    judge_client = None
    if not args.dry_run:
        import anthropic
        judge_client = anthropic.Anthropic()

    result = run_validation(
        csv_path=args.csv,
        judge_client=judge_client,
        judge_model=args.judge_model,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, indent=2))
    if not result["overall_pass"]:
        print("\nWARNING: Judge does not meet kappa >= 0.7 threshold.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
