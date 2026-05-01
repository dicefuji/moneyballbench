#!/usr/bin/env python3
"""
Phase 16 pilot runner — Qwen3 Max and DeepSeek V3 agents with DeepSeek V3 GM.

Extends the v1 pilot (K2.5/K2.6) with two additional agent models.
Uses identical noise seeds (0-9) for cross-model comparability.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from moneyballbench.agent_clients import make_agent_client
from moneyballbench.gm_clients import make_gm_client, build_gm_stack_version
from moneyballbench.orchestration import run_benchmark
from moneyballbench.config import BASE_RESERVATION_PRICES
from moneyballbench.prompts import GM_SYSTEM_PROMPT_TEMPLATE
from moneyballbench.stats import bootstrap_ci, std_dev

GM_PROVIDER = "openrouter"
GM_MODEL = "deepseek/deepseek-v3.2-exp"
AGENT_PROVIDER = "openrouter"
AGENT_MODELS = [
    "qwen/qwen3-max",
    "deepseek/deepseek-v3.2-exp",  # self-play: same model as GM/judge
]
N_RUNS = 10

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = REPO_ROOT / "results" / f"pilot_extended_{timestamp}"


def run_single(agent_client, gm_client, agent_model: str, gm_stack_version: str, run_id: int) -> dict:
    """Run a single benchmark with retry on transient errors."""
    for attempt in range(3):
        try:
            result = run_benchmark(
                agent_model_id=agent_model,
                agent_client=agent_client,
                gm_client=gm_client,
                gm_model_id=GM_MODEL,
                gm_stack_version=gm_stack_version,
                run_id=run_id,
            )
            return result
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                return {
                    "run_id": run_id,
                    "agent_model": agent_model,
                    "gm_model": GM_MODEL,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "net_score": -3.0,
                    "gross_commission": 0.0,
                    "auto_signed_count": 6,
                    "signed_deals": [],
                    "unsigned_players": ["Marcus Cole", "Darnell Washington", "Tyrese Grant", "Kevin Okafor", "Jaylen Brooks", "Raymond Torres"],
                    "rejection_budget_log": {},
                    "email_threads": {},
                    "turns_used": 0,
                    "noised_reservation_prices": {},
                }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write run metadata
    metadata = {
        "phase": 16,
        "description": "Extended pilot — Qwen3 Max and DeepSeek V3 agents",
        "gm_provider": GM_PROVIDER,
        "gm_model": GM_MODEL,
        "agent_provider": AGENT_PROVIDER,
        "agent_models": AGENT_MODELS,
        "n_runs": N_RUNS,
        "run_id_seeds": list(range(N_RUNS)),
        "max_tokens": 2048,
        "timestamp": timestamp,
        "notes": {
            "qwen3_max": "qwen/qwen3-max — current-generation Qwen agent-capable model on OpenRouter. Optimized for tool calling and RAG.",
            "deepseek_self_play": "deepseek/deepseek-v3.2-exp — same model used as GM and judge. This is intentional self-play to measure behavior when agent and GM share architecture.",
        },
    }
    with open(OUTPUT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    gm_client = make_gm_client(GM_PROVIDER, GM_MODEL)
    agent_client = make_agent_client(AGENT_PROVIDER)

    gm_stack_version = build_gm_stack_version(
        gm_client, 0.3, GM_SYSTEM_PROMPT_TEMPLATE, BASE_RESERVATION_PRICES
    )
    print(f"GM stack version: {gm_stack_version}")
    print(f"Output directory: {OUTPUT_DIR}")

    all_model_results = {}

    for agent_model in AGENT_MODELS:
        print(f"\n{'='*60}")
        print(f"Agent: {agent_model} | GM: {GM_MODEL} | Runs: {N_RUNS}")
        if agent_model == GM_MODEL:
            print(f"*** SELF-PLAY: agent model == GM model ***")
        print(f"{'='*60}")

        model_results = []
        for run_id in range(N_RUNS):
            print(f"  Run {run_id + 1}/{N_RUNS}...", end="", flush=True)
            start = time.time()
            result = run_single(agent_client, gm_client, agent_model, gm_stack_version, run_id)
            elapsed = time.time() - start
            score = result.get("net_score", 0.0)
            deals = len(result.get("signed_deals", []))
            error = result.get("error")
            if error:
                print(f" ERROR ({elapsed:.0f}s): {error[:80]}")
            else:
                print(f" score={score:.1f} deals={deals} ({elapsed:.0f}s)")
            model_results.append(result)

            # Save incrementally
            model_short = agent_model.replace("/", "_")
            model_file = OUTPUT_DIR / f"{model_short}_run{run_id}.json"
            with open(model_file, "w") as f:
                json.dump(result, f, indent=2, default=str)

        all_model_results[agent_model] = model_results

        # Summary stats
        scores = [r["net_score"] for r in model_results]
        ci_lo, ci_hi = bootstrap_ci(scores, n_bootstrap=2000)
        auto_signed = [r.get("auto_signed_count", 0) for r in model_results]
        budget_usage = []
        for r in model_results:
            budget = r.get("rejection_budget_log", {})
            total_rejections = sum(budget.values()) if isinstance(budget, dict) else 0
            budget_usage.append(total_rejections)

        success_count = sum(1 for r in model_results if "error" not in r and r.get("net_score", -3.0) > -3.0)

        summary = {
            "model": agent_model,
            "n_runs": N_RUNS,
            "mean_score": sum(scores) / len(scores),
            "std": std_dev(scores),
            "ci_95": (ci_lo, ci_hi),
            "min": min(scores),
            "max": max(scores),
            "mean_auto_signed": sum(auto_signed) / len(auto_signed),
            "mean_budget_usage": sum(budget_usage) / len(budget_usage),
            "errors": sum(1 for r in model_results if "error" in r),
            "success_rate": f"{success_count}/{N_RUNS}",
        }
        all_model_results[f"{agent_model}_summary"] = summary
        print(f"\n  Summary: mean={summary['mean_score']:.2f} std={summary['std']:.2f} "
              f"CI=({ci_lo:.2f}, {ci_hi:.2f}) success={success_count}/{N_RUNS}")

    # Save combined results
    combined_file = OUTPUT_DIR / "all_results.json"
    with open(combined_file, "w") as f:
        json.dump(all_model_results, f, indent=2, default=str)

    print(f"\nAll results saved to {OUTPUT_DIR}")
    print(f"\nNow running leakage judge...")

    # Run leakage judge
    from moneyballbench.leakage_judge import score_run
    judge_results = {}
    for agent_model in AGENT_MODELS:
        print(f"\n  Judging {agent_model}...")
        model_judge = []
        for i, result in enumerate(all_model_results[agent_model]):
            if "error" in result:
                model_judge.append({"run_id": i, "error": "skipped (run error)"})
                continue
            try:
                lr = score_run(result)
                model_judge.append({"run_id": i, **lr})
                print(f"    Run {i}: extraction={lr['extraction_rate']:.1%} hard_leak={lr['hard_leak_rate']:.1%}")
            except Exception as e:
                print(f"    Run {i}: judge error: {e}")
                model_judge.append({"run_id": i, "error": str(e)})
        judge_results[agent_model] = model_judge

    judge_file = OUTPUT_DIR / "judge_results.json"
    with open(judge_file, "w") as f:
        json.dump(judge_results, f, indent=2, default=str)

    print(f"\nJudge results saved to {judge_file}")
    print(f"\nPhase 16 pilot complete! Results in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
