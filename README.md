# MoneyBall Bench v3.0

Research-grade benchmark for measuring LLM negotiation performance under information asymmetry.

## Overview

MoneyBall Bench simulates NBA free-agency negotiations where an LLM agent acts as a sports agent negotiating contracts for 6 fictional players with 6 fictional team GMs (also LLMs). The benchmark measures both negotiation skill and information extraction capability under asymmetric information conditions.

Key features:
- **Information asymmetry**: GMs hold private reservation prices; the agent must negotiate without knowing limits
- **Three safety mechanisms**: per-run noise, orchestration backstop, rejection budget
- **Leakage measurement**: automated judge scores GM information leakage
- **Pre-registered analysis**: H1 (commission gap), H2a-c (leakage correlations)

## Setup

```bash
# Clone and install
git clone <repo-url>
cd moneyballbench
pip install -e ".[dev]"

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Running Tests

```bash
pytest tests/ -v
```

## Scripts

### Calibration (run first)

Verifies GM behavior before leaderboard runs using the deterministic probe agent (Appendix C).

```bash
# Dry run (no API calls)
python scripts/run_calibration.py --dry-run

# Live run against Haiku 4.5 GM
python scripts/run_calibration.py --gm-model claude-haiku-4-5-20250514

# Custom output directory
python scripts/run_calibration.py --output-dir results/my_calibration
```

Pass/fail thresholds:
- GM acceptance rate: 60-75%
- Average counter-offers before acceptance: 2-4
- Clarifying question rate: >= 1 per negotiation
- Granite Bay wrong-position refusal: 100%

### Pilot Run

Runs 3 models x N runs for initial validation.

```bash
# Dry run
python scripts/run_pilot.py --dry-run

# Single model, 1 run
python scripts/run_pilot.py --models claude-haiku-4-5-20250514 --n-runs 1

# Full pilot (3 models x 10 runs)
python scripts/run_pilot.py

# Custom models
python scripts/run_pilot.py --models model-a model-b --n-runs 5

# Using config file
python scripts/run_pilot.py --config my_config.json
```

### Full Leaderboard

Configurable model list with pre-registered analysis.

```bash
# Dry run
python scripts/run_leaderboard.py --dry-run

# Full run with analysis
python scripts/run_leaderboard.py --models model-a model-b model-c --n-runs 10

# Specify tier assignment for analysis
python scripts/run_leaderboard.py --top-tier model-c --bottom-tier model-a
```

### Judge Validation

Validates leakage judge against hand-graded threads.

```bash
# Dry run with stub CSV
python scripts/validate_judge.py --csv results/graded_threads_stub.csv --dry-run

# Live validation
python scripts/validate_judge.py --csv results/graded_threads.csv
```

## Config File Format

All scripts accept `--config path/to/config.json`:

```json
{
  "models": ["claude-haiku-4-5-20250514", "claude-sonnet-4-6-20250514"],
  "gm_model": "claude-haiku-4-5-20250514",
  "n_runs": 10,
  "gm_stack_version": "v3.0-leaderboard"
}
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for live runs) | Anthropic API key |

## Output Structure

Results are saved to `results/` with timestamped directories:

```
results/
├── pilot_20250101_120000/
│   ├── claude-haiku-4-5-20250514.json
│   ├── claude-sonnet-4-6-20250514.json
│   ├── claude-opus-4-7-20250514.json
│   └── summary.json
├── calibration_20250101_120000/
│   └── calibration_result.json
└── leaderboard_20250101_120000/
    ├── claude-haiku-4-5-20250514.json
    ├── ...
    ├── analysis.json
    └── leaderboard.json
```

## Project Structure

```
moneyballbench/
├── config.py              # Player/team profiles, reservation prices, constants
├── environment.py         # NBASimEnvironment with all tool methods
├── tools.py               # 7 tool definitions (§7.1)
├── prompts.py             # Agent + GM system prompts (§6)
├── orchestration.py       # run_benchmark(), run_full_evaluation()
├── noise.py               # apply_reservation_noise()
├── stats.py               # bootstrap_ci(), std_dev(), power_analysis_min_n()
├── leakage_judge.py       # Leakage scoring (Appendix D)
├── baselines/
│   ├── floor_aware.py     # Floor-Aware Baseline (Appendix E.1)
│   └── truly_naive.py     # Truly-Naive Baseline (Appendix E.2)
├── calibration/
│   └── probe_agent.py     # Calibration Probe (Appendix C)
└── analysis/
    └── preregistered.py   # H1, H2a, H2b, H2c (Appendix F)
```

## Spec Reference

Full specification: `moneyball_bench_v3.md`

See `QUESTIONS.md` for interpretive decisions and spec ambiguities.
