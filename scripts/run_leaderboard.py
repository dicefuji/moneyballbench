#!/usr/bin/env python3
"""
MoneyBall Bench v3.0 — Full Leaderboard Run Script.

Configurable model list and n-runs. Runs each model through the
full evaluation pipeline and saves structured results.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.orchestration import run_full_evaluation
from moneyballbench.analysis.preregistered import (
    analyze_h1,
    analyze_h2a,
    analyze_h2b,
    analyze_h2c,
)


DEFAULT_MODELS = [
    "claude-haiku-4-5-20250514",
    "claude-sonnet-4-6-20250514",
    "claude-opus-4-7-20250514",
]
DEFAULT_GM_MODEL = "claude-haiku-4-5-20250514"
DEFAULT_N_RUNS = 10


def main():
    parser = argparse.ArgumentParser(
        description="Run MoneyBall Bench v3.0 full leaderboard"
    )
    parser.add_argument(
        "--models", nargs="+", default=DEFAULT_MODELS,
        help="Model IDs to evaluate"
    )
    parser.add_argument(
        "--gm-model", default=DEFAULT_GM_MODEL,
        help="GM model ID"
    )
    parser.add_argument(
        "--n-runs", type=int, default=DEFAULT_N_RUNS,
        help="Number of runs per model (default: 10)"
    )
    parser.add_argument(
        "--gm-stack-version", default="v3.0-leaderboard",
        help="GM stack version string for noise seeding"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: results/leaderboard_<timestamp>)"
    )
    parser.add_argument(
        "--top-tier", default=None,
        help="Top-tier model for H1/H2c (default: last model in list)"
    )
    parser.add_argument(
        "--bottom-tier", default=None,
        help="Bottom-tier model for H1/H2c (default: first model in list)"
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
        args.models = config.get("models", args.models)
        args.gm_model = config.get("gm_model", args.gm_model)
        args.n_runs = config.get("n_runs", args.n_runs)
        args.gm_stack_version = config.get("gm_stack_version", args.gm_stack_version)
        args.top_tier = config.get("top_tier", args.top_tier)
        args.bottom_tier = config.get("bottom_tier", args.bottom_tier)

    top_tier = args.top_tier or args.models[-1]
    bottom_tier = args.bottom_tier or args.models[0]

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = REPO_ROOT / "results" / f"leaderboard_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("DRY RUN — no API calls will be made")
        from tests.conftest import MockGMClient
        from dataclasses import dataclass

        @dataclass
        class MockContentBlock:
            type: str = "text"
            text: str = "I'll end my turn now."

        @dataclass
        class MockAgentResponse:
            content: list = None
            stop_reason: str = "end_turn"
            def __post_init__(self):
                if self.content is None:
                    self.content = [MockContentBlock()]

        class MockAgentClient:
            class messages:
                @staticmethod
                def create(**kwargs):
                    return MockAgentResponse()

        agent_client = MockAgentClient()
        gm_client = MockGMClient()
    else:
        import anthropic
        agent_client = anthropic.Anthropic()
        gm_client = anthropic.Anthropic()

    results_by_model = {}
    all_runs = []
    tier_map = {m: i for i, m in enumerate(args.models)}

    for model in args.models:
        print(f"\n{'='*60}")
        print(f"Evaluating {model} × {args.n_runs} runs")
        print(f"{'='*60}")

        eval_result = run_full_evaluation(
            agent_model_id=model,
            agent_client=agent_client,
            gm_client=gm_client,
            gm_model_id=args.gm_model,
            gm_stack_version=args.gm_stack_version,
            n_runs=args.n_runs,
        )
        results_by_model[model] = eval_result["all_runs"]

        for run in eval_result["all_runs"]:
            run["model_tier"] = tier_map[model]
            all_runs.append(run)

        model_file = output_dir / f"{model.replace('/', '_')}.json"
        with open(model_file, "w") as f:
            json.dump(eval_result, f, indent=2, default=str)
        print(f"  Mean: {eval_result['mean_score']:.2f}, Std: {eval_result['std']:.2f}")

    print(f"\n{'='*60}")
    print("Running pre-registered analyses...")
    print(f"{'='*60}")

    analyses = {}
    if top_tier in results_by_model and bottom_tier in results_by_model:
        analyses["H1"] = analyze_h1(results_by_model, top_tier, bottom_tier)
        print(f"  H1 (commission gap): {'SUPPORTED' if analyses['H1']['supported'] else 'NOT SUPPORTED'}")

    analyses["H2a"] = analyze_h2a(all_runs)
    print(f"  H2a (leakage-score correlation): rho={analyses['H2a']['rho']:.3f}, "
          f"{'SUPPORTED' if analyses['H2a']['supported'] else 'NOT SUPPORTED'}")

    analyses["H2b"] = analyze_h2b(all_runs)
    print(f"  H2b (attenuation): {analyses['H2b']['attenuation_pct']:.1f}%, "
          f"{'SUPPORTED' if analyses['H2b']['supported'] else 'NOT SUPPORTED'}")

    if top_tier in results_by_model and bottom_tier in results_by_model:
        analyses["H2c"] = analyze_h2c(results_by_model, top_tier, bottom_tier)
        print(f"  H2c (team-fit): top={analyses['H2c']['top_accuracy']:.2f}, "
              f"bot={analyses['H2c']['bottom_accuracy']:.2f}, "
              f"{'SUPPORTED' if analyses['H2c']['supported'] else 'NOT SUPPORTED'}")

    analysis_file = output_dir / "analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analyses, f, indent=2, default=str)

    leaderboard = []
    for model, runs in results_by_model.items():
        scores = [r["net_score"] for r in runs]
        leaderboard.append({
            "model": model,
            "mean_score": sum(scores) / len(scores),
            "n_runs": len(runs),
        })
    leaderboard.sort(key=lambda x: x["mean_score"], reverse=True)

    lb_file = output_dir / "leaderboard.json"
    with open(lb_file, "w") as f:
        json.dump(leaderboard, f, indent=2)

    print(f"\nLeaderboard:")
    for i, entry in enumerate(leaderboard, 1):
        print(f"  {i}. {entry['model']}: {entry['mean_score']:.2f}M")

    print(f"\nResults saved to {output_dir}")


if __name__ == "__main__":
    main()
