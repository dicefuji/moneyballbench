#!/usr/bin/env python3
"""
MoneyBall Bench v3.0 — Calibration Run Script.

Runs the probe agent against all six GMs (no real agent, just probe),
measures the four calibration metrics from Appendix C, reports pass/fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.calibration.probe_agent import run_calibration_probe
from moneyballbench.config import BASE_RESERVATION_PRICES
from moneyballbench.environment import NBASimEnvironment
from moneyballbench.noise import apply_reservation_noise


DEFAULT_GM_MODEL = "claude-haiku-4-5-20250514"


def main():
    parser = argparse.ArgumentParser(
        description="Run GM calibration using the probe agent (Appendix C)"
    )
    parser.add_argument(
        "--gm-model", default=DEFAULT_GM_MODEL,
        help="GM model ID (default: claude-haiku-4-5-20250514)"
    )
    parser.add_argument(
        "--gm-stack-version", default="v3.0-calibration",
        help="GM stack version string for noise seeding"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: results/calibration_<timestamp>)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Exercise code path without making API calls"
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to JSON config file (overrides CLI args)"
    )
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        args.gm_model = config.get("gm_model", args.gm_model)
        args.gm_stack_version = config.get("gm_stack_version", args.gm_stack_version)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = REPO_ROOT / "results" / f"calibration_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("DRY RUN — no API calls will be made")
        from tests.conftest import MockGMClient
        gm_client = MockGMClient()
    else:
        import anthropic
        gm_client = anthropic.Anthropic()

    noised_prices = apply_reservation_noise(
        BASE_RESERVATION_PRICES,
        args.gm_stack_version,
        run_id=0,
    )

    env = NBASimEnvironment(
        gm_client=gm_client,
        gm_model_id=args.gm_model,
        noised_reservation_prices=noised_prices,
        gm_stack_version=args.gm_stack_version,
        run_id=0,
    )

    print("Running calibration probe agent...")
    metrics = run_calibration_probe(env)

    result_file = output_dir / "calibration_result.json"
    with open(result_file, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"\nCalibration Results:")
    print(f"  Acceptance rate:         {metrics['acceptance_rate']:.2%} "
          f"({metrics['pass_fail']['acceptance_rate']})")
    print(f"  Avg counters:            {metrics['avg_counter_offers_before_accept']:.1f} "
          f"({metrics['pass_fail']['avg_counters']})")
    print(f"  Avg clarifying Qs:       {metrics['avg_clarifying_questions']:.1f} "
          f"({metrics['pass_fail']['clarifying_questions']})")
    print(f"  GB wrong-pos refusal:    {metrics['granite_bay_wrong_position_refusal_rate']:.0%} "
          f"({metrics['pass_fail']['granite_bay_refusal']})")
    print(f"  Overall:                 {'PASS' if metrics['overall_pass'] else 'FAIL'}")
    print(f"\nResults saved to {result_file}")

    if not metrics["overall_pass"]:
        print("\nCALIBRATION FAILED — see Appendix C for remediation steps.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
