# MoneyBall Bench v3.0

A benchmark for measuring LLM negotiation under information asymmetry.

An LLM agent negotiates NBA free-agency contracts for 6 fictional players against 6 team GMs (also LLMs). GMs hold private reservation prices the agent cannot see. The benchmark measures two things: **how much commission the agent earns** (arithmetic, no LLM judge) and **how much private information leaks** from GMs during negotiation (graded by a separate LLM judge).

Three safety mechanisms prevent the agent from brute-forcing reservation prices: per-run noise on all reservation values, an orchestration backstop that rejects above-ceiling deals regardless of what the GM verbally agreed to, and a per-pair rejection budget that locks a negotiation after 3 failed attempts.

## Quickstart

```bash
# 1. Install
git clone https://github.com/dicefuji/moneyballbench.git
cd moneyballbench
pip install -e ".[dev]"

# 2. Set your API key
export OPENROUTER_API_KEY="your-key-here"  # https://openrouter.ai/settings/keys

# 3. Run the benchmark on your model
python scripts/run_pilot.py --models your-provider/your-model --n-runs 10
```

Results are saved to `results/pilot_<timestamp>/` with per-run JSONs and a summary.

## What you need

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** (default) | [OpenRouter API key](https://openrouter.ai/settings/keys). Used for agent, GM, and judge by default. |
| `ANTHROPIC_API_KEY` | Optional | Required only if using `--agent-provider anthropic` or `--gm-provider anthropic`. |
| `OLLAMA_BASE_URL` | Optional | Required only if using `--gm-provider ollama`. Defaults to `http://localhost:11434`. |

## Running the benchmark

### Evaluate your model (most common)

```bash
# Run your model as the agent, 10 runs, DeepSeek V3 as GM (default)
python scripts/run_pilot.py --models your-provider/your-model --n-runs 10

# Run multiple models head-to-head
python scripts/run_pilot.py --models model-a model-b --n-runs 10

# Dry run (no API calls, validates config)
python scripts/run_pilot.py --dry-run
```

### Use a different GM

The GM model is a load-bearing benchmark component. Changing the GM changes the benchmark. Results are tagged with a `gm_stack_version` string so runs are always comparable.

```bash
# Use Anthropic as GM
python scripts/run_pilot.py --gm-provider anthropic --gm-model claude-sonnet-4-20250514 --models your-model

# Use a self-hosted Ollama model as GM
export OLLAMA_BASE_URL="http://localhost:11434"
python scripts/run_pilot.py --gm-provider ollama --gm-model llama3.1:70b --models your-model
```

### Full leaderboard run (with pre-registered analysis)

```bash
python scripts/run_leaderboard.py --models model-a model-b model-c --n-runs 10
```

This runs the benchmark and produces pre-registered statistical analysis (H1: commission gap, H2a-c: leakage correlations) per the spec.

### Calibrate the GM first (recommended)

Before running the benchmark, verify the GM behaves correctly:

```bash
# Quick calibration check
python scripts/run_calibration.py

# Compare multiple GM candidates
python scripts/run_calibration_bakeoff.py
```

Calibration verifies acceptance rates, counter-offer behavior, question-asking, and information containment.

## Understanding results

Each run produces a JSON with:

| Field | Description |
|---|---|
| `net_score` | Total commission earned minus auto-sign penalties. **The primary metric.** |
| `signed_deals` | List of deals closed, with AAV, years, and which team. |
| `auto_signed_count` | Players not signed by the agent, auto-signed at penalty rate. |
| `email_threads` | Full negotiation transcripts per team. |
| `gm_stack_version` | Fingerprint of the GM configuration for reproducibility. |
| `noised_reservation_prices` | The actual reservation prices used (after per-run noise). |

The leakage judge grades each (player, team) email thread on a 0/1/2 scale:
- **0**: No information leaked
- **1**: Soft leak (GM hinted at constraints)
- **2**: Hard leak (GM revealed specific numbers)

## Config file

All scripts accept `--config path/to/config.json` for batch runs:

```json
{
  "models": ["your-provider/your-model"],
  "gm_model": "deepseek/deepseek-v3.2-exp",
  "gm_provider": "openrouter",
  "agent_provider": "openrouter",
  "n_runs": 10
}
```

## Project structure

```
moneyballbench/
  config.py           # Player/team profiles, reservation prices, constants
  environment.py      # NBASimEnvironment — the deterministic game engine
  orchestration.py    # run_benchmark() — the main loop
  tools.py            # 7 agent tools (send_email, close_deal, etc.)
  prompts.py          # Agent + GM system prompts
  noise.py            # Per-run reservation price noise
  stats.py            # Bootstrap CI, power analysis
  leakage_judge.py    # Post-hoc leakage scoring
  gm_clients/         # GM providers (OpenRouter, Anthropic, Ollama)
  agent_clients/      # Agent providers (OpenRouter, Anthropic)
  baselines/          # Scripted reference agents (floor-aware, truly-naive)
  calibration/        # Calibration probe agent
  analysis/           # Pre-registered statistical tests

scripts/
  run_pilot.py              # Run N models x M runs
  run_leaderboard.py        # Full leaderboard with analysis
  run_calibration.py        # Verify GM behavior
  run_calibration_bakeoff.py # Compare GM candidates
  validate_judge.py         # Validate leakage judge

tests/                      # Test suite (pytest)
moneyball_bench_v3.md       # Full benchmark specification
```

## Running tests

```bash
pytest tests/ -v

# Skip tests that require live API calls
pytest tests/ -v -m "not requires_api"
```

## Specification

The full benchmark specification is in [`moneyball_bench_v3.md`](moneyball_bench_v3.md). It covers the league rules, player/team profiles, scoring system, leakage measurement, and pre-registered analysis plan.

## License

MIT
