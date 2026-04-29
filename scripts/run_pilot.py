#!/usr/bin/env python3
"""
MoneyBall Bench v3.0 — Pilot Run Script.

Runs N models × M runs each. Saves results to results/pilot_<timestamp>/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.agent_clients import make_agent_client
from moneyballbench.gm_clients import make_gm_client
from moneyballbench.orchestration import run_full_evaluation
from moneyballbench.stats import bootstrap_ci, std_dev

DEFAULT_MODELS = [
    "moonshotai/kimi-k2.5",
    "moonshotai/kimi-k2.6",
]
DEFAULT_GM_MODEL = "deepseek/deepseek-v3.2-exp"
DEFAULT_GM_PROVIDER = "openrouter"
DEFAULT_N_RUNS = 10


def main():
    parser = argparse.ArgumentParser(
        description="Run MoneyBall Bench v3.0 pilot: N models × M runs"
    )
    parser.add_argument(
        "--models", nargs="+", default=DEFAULT_MODELS,
        help="Model IDs to evaluate"
    )
    parser.add_argument(
        "--gm-model", default=DEFAULT_GM_MODEL,
        help="GM model ID (default: deepseek/deepseek-v3.2-exp)"
    )
    parser.add_argument(
        "--gm-provider", default=DEFAULT_GM_PROVIDER,
        help="GM provider: anthropic, ollama, openrouter (default: openrouter)"
    )
    parser.add_argument(
        "--agent-provider", default="openrouter",
        help="Agent provider: anthropic, openrouter (default: openrouter)"
    )
    parser.add_argument(
        "--n-runs", type=int, default=DEFAULT_N_RUNS,
        help="Number of runs per model (default: 10)"
    )
    parser.add_argument(
        "--gm-stack-version", default="v3.0-pilot",
        help="GM stack version string for noise seeding"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: results/pilot_<timestamp>)"
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
        args.gm_provider = config.get("gm_provider", args.gm_provider)
        args.n_runs = config.get("n_runs", args.n_runs)
        args.gm_stack_version = config.get("gm_stack_version", args.gm_stack_version)
        args.agent_provider = config.get("agent_provider", args.agent_provider)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = REPO_ROOT / "results" / f"pilot_{timestamp}"
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
        agent_client = make_agent_client(args.agent_provider)
        gm_client = make_gm_client(args.gm_provider, args.gm_model)

    all_results = {}
    for model in args.models:
        print(f"\n{'='*60}")
        print(f"Running {model} × {args.n_runs} runs")
        print(f"{'='*60}")

        eval_result = run_full_evaluation(
            agent_model_id=model,
            agent_client=agent_client,
            gm_client=gm_client,
            gm_model_id=args.gm_model,
            gm_stack_version=args.gm_stack_version,
            n_runs=args.n_runs,
        )
        all_results[model] = eval_result

        model_file = output_dir / f"{model.replace('/', '_')}.json"
        with open(model_file, "w") as f:
            json.dump(eval_result, f, indent=2, default=str)
        print(f"  Mean score: {eval_result['mean_score']:.2f}")
        print(f"  Std: {eval_result['std']:.2f}")
        print(f"  95% CI: {eval_result['ci_95']}")
        print(f"  Saved to {model_file}")

    summary_file = output_dir / "summary.json"
    summary = {
        "models": args.models,
        "gm_model": args.gm_model,
        "gm_provider": args.gm_provider,
        "n_runs": args.n_runs,
        "gm_stack_version": args.gm_stack_version,
        "results": {
            m: {
                "mean_score": r["mean_score"],
                "std": r["std"],
                "ci_95": r["ci_95"],
            }
            for m, r in all_results.items()
        },
    }
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {summary_file}")


if __name__ == "__main__":
    main()
