# MoneyBall Bench v3.0

Long-horizon, multi-turn LLM benchmark measuring negotiation performance under information asymmetry in a simulated NBA free agency environment.

## Overview

MoneyBall Bench measures a model's ability to negotiate sports contracts on behalf of six basketball players across a 10-round free agency window. The model acts as a player agent, communicating with six team GMs (powered by a neutral small LLM) via free-form email.

**Primary metric:** Net Commission Score = total commission earned minus auto-sign penalties.

**Key innovation (v3):** GMs hold reservation prices in their prompts. Information extraction is measured as a capability (via a leakage judge), not suppressed.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest -v

# Run calibration (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=your-key
python scripts/run_calibration.py

# Run pilot (3 models x 10 runs)
python scripts/run_pilot.py --models haiku-4-5 --n-runs 1

# Full leaderboard
python scripts/run_leaderboard.py --config config.yaml
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for live runs) | Anthropic API key for agent and GM calls |

## Project Structure

```
moneyballbench/
  config.py           # Player/team profiles, reservation prices, constants
  environment.py      # NBASimEnvironment — core simulation
  tools.py            # Tool definitions for agent
  prompts.py          # Agent and GM system prompts
  orchestration.py    # run_benchmark(), run_full_evaluation()
  noise.py            # Reservation price noise
  stats.py            # Bootstrap CI, standard deviation, power analysis
  leakage_judge.py    # Post-run leakage scoring
  baselines/          # Floor-aware and truly-naive baselines
  calibration/        # GM calibration probe agent
  analysis/           # Pre-registered statistical analysis
tests/                # Unit and integration tests
scripts/              # Run scripts (pilot, calibration, leaderboard)
results/              # Run outputs (gitignored)
```

## Scripts

- `scripts/run_calibration.py` — Verify GM behavior meets calibration thresholds
- `scripts/run_pilot.py` — 3 models x 10 runs validation
- `scripts/validate_judge.py` — Compute Cohen's kappa for leakage judge
- `scripts/run_leaderboard.py` — Full leaderboard run

All scripts support `--help` and `--dry-run`.

## License

MIT
