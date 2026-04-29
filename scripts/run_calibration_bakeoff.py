#!/usr/bin/env python3
"""
MoneyBall Bench v3.0 — GM Calibration Bake-Off Script.

Runs the calibration probe against multiple GM candidates and compares
results. Uses identical noise seeds across candidates to isolate GM
behavioral differences.

Captures 5 metrics per candidate:
  1. Acceptance rate (60-75%)
  2. Counter-offer count (2-4)
  3. Clarifying question rate (>=1)
  4. Granite Bay wrong-position refusal (100%)
  5. Probe-induced leak rate (<5%)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.calibration.probe_agent import run_calibration_probe
from moneyballbench.config import BASE_RESERVATION_PRICES
from moneyballbench.environment import NBASimEnvironment
from moneyballbench.gm_clients import make_gm_client
from moneyballbench.noise import apply_reservation_noise

# Default GM candidates for the bake-off
DEFAULT_CANDIDATES = [
    ("anthropic", "claude-sonnet-4-20250514"),
    ("openrouter", "moonshotai/kimi-k2.6"),
    ("openrouter", "deepseek/deepseek-chat-v3-0324"),
]

LEAK_RATE_THRESHOLD = 0.05


def run_single_candidate(
    provider: str,
    model_id: str,
    gm_stack_version: str,
    run_id: int,
    noised_prices: dict,
    run_leakage: bool = True,
) -> dict:
    """Run calibration probe against a single GM candidate."""
    gm_client = make_gm_client(provider, model_id)

    env = NBASimEnvironment(
        gm_client=gm_client,
        gm_model_id=model_id,
        noised_reservation_prices=noised_prices,
        gm_stack_version=gm_stack_version,
        run_id=run_id,
    )

    metrics = run_calibration_probe(env)

    # Add 5th metric: probe-induced leak rate via leakage judge
    leak_result = None
    if run_leakage:
        try:
            from moneyballbench.leakage_judge import score_run

            run_result = {"email_threads": env.email_threads}
            leak_result = score_run(run_result)
            metrics["probe_leak_rate"] = leak_result["extraction_rate"]
            metrics["pass_fail"]["probe_leak_rate"] = (
                "PASS" if leak_result["extraction_rate"] < LEAK_RATE_THRESHOLD else "FAIL"
            )
            metrics["overall_pass"] = all(
                v == "PASS" for v in metrics["pass_fail"].values()
            )
        except Exception as e:
            metrics["probe_leak_rate"] = None
            metrics["pass_fail"]["probe_leak_rate"] = f"ERROR: {e}"
            metrics["leak_error"] = str(e)
            metrics["overall_pass"] = False

    return {
        "provider": provider,
        "model_id": model_id,
        "metrics": metrics,
        "leak_details": leak_result,
    }


def generate_summary_md(results: list[dict], output_dir: Path) -> str:
    """Generate summary markdown for the bake-off results."""
    lines = [
        "# GM Calibration Bake-Off Results",
        "",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Comparison Table",
        "",
        "| Metric | Threshold |",
    ]

    # Build header with candidate names
    header_extra = ""
    separator_extra = ""
    for r in results:
        name = f"{r['provider']}:{r['model_id']}"
        header_extra += f" {name} |"
        separator_extra += " --- |"

    lines[-1] = f"| Metric | Threshold |{header_extra}"
    lines.append(f"| --- | --- |{separator_extra}")

    metrics_spec = [
        ("Acceptance rate", "60-75%", "acceptance_rate", lambda v: f"{v:.0%}" if v is not None else "N/A"),
        ("Avg counter-offers", "4-6", "avg_counter_offers_before_accept", lambda v: f"{v:.1f}" if v is not None else "N/A"),
        ("Avg clarifying Qs", ">=1", "avg_clarifying_questions", lambda v: f"{v:.1f}" if v is not None else "N/A"),
        ("GB wrong-pos refusal", "100%", "granite_bay_wrong_position_refusal_rate", lambda v: f"{v:.0%}" if v is not None else "N/A"),
        ("Probe leak rate", "<5%", "probe_leak_rate", lambda v: f"{v:.1%}" if v is not None else "N/A"),
    ]

    pf_keys = [
        "acceptance_rate",
        "avg_counters",
        "clarifying_questions",
        "granite_bay_refusal",
        "probe_leak_rate",
    ]

    for (label, threshold, key, fmt), pf_key in zip(metrics_spec, pf_keys):
        row = f"| {label} | {threshold} |"
        for r in results:
            m = r["metrics"]
            val = m.get(key)
            pf = m.get("pass_fail", {}).get(pf_key, "N/A")
            row += f" {fmt(val)} ({pf}) |"
        lines.append(row)

    # Overall pass/fail
    row = "| **Overall** | |"
    for r in results:
        overall = "PASS" if r["metrics"].get("overall_pass") else "FAIL"
        row += f" **{overall}** |"
    lines.append(row)

    lines.extend(["", "## Per-Candidate Observations", ""])
    for r in results:
        name = f"{r['provider']}:{r['model_id']}"
        lines.append(f"### {name}")
        lines.append("")

        m = r["metrics"]
        passing = [k for k, v in m.get("pass_fail", {}).items() if v == "PASS"]
        failing = [k for k, v in m.get("pass_fail", {}).items() if v != "PASS"]

        if passing:
            lines.append(f"- Passing metrics: {', '.join(passing)}")
        if failing:
            lines.append(f"- Failing metrics: {', '.join(failing)}")

        if r.get("leak_details"):
            ld = r["leak_details"]
            lines.append(f"- Leakage: {ld['extraction_rate']:.1%} extraction rate, "
                        f"{ld['hard_leak_rate']:.1%} hard leak rate "
                        f"({ld['total_threads_scored']} threads scored)")

        if m.get("leak_error"):
            lines.append(f"- Leakage judge error: {m['leak_error']}")

        lines.append("")

    # Recommendation
    lines.extend(["## Recommendation", ""])
    passing_candidates = [r for r in results if r["metrics"].get("overall_pass")]
    if len(passing_candidates) == 0:
        lines.append("No candidate passed all calibration metrics. Further remediation "
                     "or alternative candidates needed.")
    elif len(passing_candidates) == 1:
        c = passing_candidates[0]
        lines.append(f"**Recommended production GM**: `{c['provider']}:{c['model_id']}`")
        lines.append("")
        lines.append("This is the only candidate that passes all calibration metrics. "
                     "Use this as the production GM stack.")
    else:
        names = [f"`{c['provider']}:{c['model_id']}`" for c in passing_candidates]
        lines.append(f"**Multiple candidates passed**: {', '.join(names)}")
        lines.append("")
        lines.append("Per spec: run both as separate published GM stacks. This gives "
                     "cross-stack rank stability as a validity check on the benchmark itself.")
        lines.append("")
        lines.append("To set up parallel publication, run the leaderboard against each "
                     "GM stack independently and compare rank orderings.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run GM calibration bake-off across multiple candidates"
    )
    parser.add_argument(
        "--candidates", default=None,
        help="JSON array of [provider, model_id] pairs (default: built-in list)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: results/calibration_bakeoff_<timestamp>)"
    )
    parser.add_argument(
        "--run-id", type=int, default=42,
        help="Shared run_id seed for noise (default: 42)"
    )
    parser.add_argument(
        "--skip-leakage", action="store_true",
        help="Skip the leakage judge (5th metric)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Exercise code path without making API calls"
    )
    args = parser.parse_args()

    if args.candidates:
        candidates = json.loads(args.candidates)
    else:
        candidates = DEFAULT_CANDIDATES

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = REPO_ROOT / "results" / f"calibration_bakeoff_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use same noise seed for all candidates
    gm_stack_version = "v3.0-bakeoff"
    noised_prices = apply_reservation_noise(
        BASE_RESERVATION_PRICES,
        gm_stack_version,
        run_id=args.run_id,
    )

    results = []
    for provider, model_id in candidates:
        print(f"\n{'='*60}")
        print(f"Running candidate: {provider}:{model_id}")
        print(f"{'='*60}")

        if args.dry_run:
            print("DRY RUN — skipping actual API calls")
            results.append({
                "provider": provider,
                "model_id": model_id,
                "metrics": {
                    "acceptance_rate": 0.0,
                    "avg_counter_offers_before_accept": 0.0,
                    "avg_clarifying_questions": 0.0,
                    "granite_bay_wrong_position_refusal_rate": 1.0,
                    "probe_leak_rate": 0.0,
                    "pass_fail": {
                        "acceptance_rate": "DRY_RUN",
                        "avg_counters": "DRY_RUN",
                        "clarifying_questions": "DRY_RUN",
                        "granite_bay_refusal": "DRY_RUN",
                        "probe_leak_rate": "DRY_RUN",
                    },
                    "overall_pass": False,
                },
                "leak_details": None,
            })
            continue

        try:
            result = run_single_candidate(
                provider=provider,
                model_id=model_id,
                gm_stack_version=gm_stack_version,
                run_id=args.run_id,
                noised_prices=noised_prices,
                run_leakage=not args.skip_leakage,
            )
            results.append(result)

            # Save per-candidate result
            safe_name = f"{provider}_{model_id.replace('/', '_')}"
            with open(output_dir / f"{safe_name}.json", "w") as f:
                json.dump(result, f, indent=2, default=str)

            m = result["metrics"]
            print(f"\n  Acceptance rate:      {m['acceptance_rate']:.2%} ({m['pass_fail']['acceptance_rate']})")
            print(f"  Avg counters:         {m['avg_counter_offers_before_accept']:.1f} ({m['pass_fail']['avg_counters']})")
            print(f"  Avg clarifying Qs:    {m['avg_clarifying_questions']:.1f} ({m['pass_fail']['clarifying_questions']})")
            print(f"  GB refusal:           {m['granite_bay_wrong_position_refusal_rate']:.0%} ({m['pass_fail']['granite_bay_refusal']})")
            if m.get("probe_leak_rate") is not None:
                print(f"  Probe leak rate:      {m['probe_leak_rate']:.1%} ({m['pass_fail']['probe_leak_rate']})")
            print(f"  Overall:              {'PASS' if m['overall_pass'] else 'FAIL'}")

        except Exception as e:
            print(f"\n  ERROR: {e}")
            results.append({
                "provider": provider,
                "model_id": model_id,
                "metrics": {
                    "error": str(e),
                    "overall_pass": False,
                    "pass_fail": {},
                },
                "leak_details": None,
            })

    # Generate summary
    summary_md = generate_summary_md(results, output_dir)
    with open(output_dir / "summary.md", "w") as f:
        f.write(summary_md)

    # Save all results
    with open(output_dir / "all_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Bake-off complete. Results in {output_dir}")
    print(f"{'='*60}")

    # Also write BAKEOFF_RESULTS.md at repo root
    bakeoff_path = REPO_ROOT / "BAKEOFF_RESULTS.md"
    with open(bakeoff_path, "w") as f:
        f.write(summary_md)
    print(f"Summary written to {bakeoff_path}")

    passing = [r for r in results if r["metrics"].get("overall_pass")]
    if not passing:
        print("\nNo candidates passed all metrics.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
