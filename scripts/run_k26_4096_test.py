#!/usr/bin/env python3
"""
K2.6 retest with max_tokens=4096 to check if token truncation
explains the 90% failure rate observed in the Phase 14 pilot.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

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
AGENT_MODEL = "moonshotai/kimi-k2.6"
N_RUNS = 10

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = REPO_ROOT / "results" / f"k26_4096_retest_{timestamp}"


def run_single(agent_client, gm_client, gm_stack_version: str, run_id: int) -> dict:
    """Run a single benchmark with retry on transient errors."""
    for attempt in range(3):
        try:
            result = run_benchmark(
                agent_model_id=AGENT_MODEL,
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
                    "agent_model": AGENT_MODEL,
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

    gm_client = make_gm_client(GM_PROVIDER, GM_MODEL)
    agent_client = make_agent_client(AGENT_PROVIDER)

    gm_stack_version = build_gm_stack_version(
        gm_client, 0.3, GM_SYSTEM_PROMPT_TEMPLATE, BASE_RESERVATION_PRICES
    )
    print(f"GM stack version: {gm_stack_version}")
    print(f"Agent: {AGENT_MODEL} | max_tokens: 4096 (was 2048)")
    print(f"Output: {OUTPUT_DIR}")

    # Patch orchestration to use max_tokens=4096
    import moneyballbench.orchestration as orch
    original_run = orch.run_benchmark

    results = []
    for run_id in range(N_RUNS):
        print(f"  Run {run_id + 1}/{N_RUNS}...", end="", flush=True)
        start = time.time()

        # Monkey-patch the agent_client.messages.create to use 4096
        original_create = agent_client.messages.create
        def patched_create(*args, **kwargs):
            kwargs['max_tokens'] = 4096
            return original_create(*args, **kwargs)
        agent_client.messages.create = patched_create

        result = run_single(agent_client, gm_client, gm_stack_version, run_id)

        # Restore
        agent_client.messages.create = original_create

        elapsed = time.time() - start
        score = result.get("net_score", 0.0)
        deals = len(result.get("signed_deals", []))
        error = result.get("error")
        if error:
            print(f" ERROR ({elapsed:.0f}s): {error[:80]}")
        else:
            print(f" score={score:.1f} deals={deals} ({elapsed:.0f}s)")
        results.append(result)

        # Save incrementally
        with open(OUTPUT_DIR / f"k26_4096_run{run_id}.json", "w") as f:
            json.dump(result, f, indent=2, default=str)

    # Summary
    scores = [r["net_score"] for r in results]
    ci_lo, ci_hi = bootstrap_ci(scores, n_bootstrap=2000)
    auto_signed = [r.get("auto_signed_count", 0) for r in results]
    successful = sum(1 for r in results if len(r.get("signed_deals", [])) > 0)

    print(f"\n{'='*60}")
    print(f"K2.6 @ max_tokens=4096 Results:")
    print(f"  Mean score: {sum(scores)/len(scores):.2f}")
    print(f"  Std: {std_dev(scores):.2f}")
    print(f"  95% CI: ({ci_lo:.2f}, {ci_hi:.2f})")
    print(f"  Min: {min(scores):.1f} Max: {max(scores):.1f}")
    print(f"  Successful runs: {successful}/{N_RUNS}")
    print(f"  Mean auto-signed: {sum(auto_signed)/len(auto_signed):.1f}")
    print(f"{'='*60}")

    # Compare with original
    print(f"\nComparison with original K2.6 @ max_tokens=2048:")
    print(f"  Original: mean=-0.87, std=6.74, CI=(-3.00, 3.39), 1/10 successful")
    print(f"  4096:     mean={sum(scores)/len(scores):.2f}, std={std_dev(scores):.2f}, CI=({ci_lo:.2f}, {ci_hi:.2f}), {successful}/10 successful")

    summary = {
        "config": {
            "agent_model": AGENT_MODEL,
            "gm_model": GM_MODEL,
            "max_tokens": 4096,
            "n_runs": N_RUNS,
            "gm_stack_version": gm_stack_version,
        },
        "results": {
            "mean_score": sum(scores) / len(scores),
            "std": std_dev(scores),
            "ci_95": [ci_lo, ci_hi],
            "min": min(scores),
            "max": max(scores),
            "successful_runs": successful,
            "mean_auto_signed": sum(auto_signed) / len(auto_signed),
        },
        "per_run": [
            {
                "run_id": i,
                "score": r["net_score"],
                "deals": len(r.get("signed_deals", [])),
                "auto_signed": r.get("auto_signed_count", 0),
                "turns": r.get("turns_used", 0),
                "error": r.get("error"),
            }
            for i, r in enumerate(results)
        ],
    }
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
