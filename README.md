# MoneyBall Bench v3.0

Research-grade benchmark for measuring LLM negotiation performance under information asymmetry.

## Overview

MoneyBall Bench simulates NBA free-agency negotiations where an LLM agent acts as a sports agent negotiating contracts for 6 fictional players with 6 fictional team GMs (also LLMs). The benchmark measures both negotiation skill and information extraction capability under asymmetric information conditions.

Key features:
- **Information asymmetry**: GMs hold private reservation prices; the agent must negotiate without knowing limits
- **Three safety mechanisms**: per-run noise, orchestration backstop, rejection budget
- **Leakage measurement**: automated judge scores GM information leakage
- **Pre-registered analysis**: H1 (commission gap), H2a-c (leakage correlations)
- **Multi-provider GM backends**: Anthropic, OpenRouter, Ollama — swap GM model via config

## Setup

```bash
# Clone and install
git clone <repo-url>
cd moneyballbench
pip install -e ".[dev]"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for Anthropic GM/agent) | Anthropic API key |
| `OPENROUTER_API_KEY` | For OpenRouter GM | OpenRouter API key (https://openrouter.ai/settings/keys) |
| `OLLAMA_BASE_URL` | For Ollama GM | Ollama endpoint (default: `http://localhost:11434`) |

## GM Provider Configuration

The GM model is a load-bearing benchmark component. Per §3.1, the GM stack version is published with every leaderboard entry. Different GM models = different benchmark versions.

### Available Providers

**Anthropic** (default):
```bash
python scripts/run_calibration.py --gm-provider anthropic --gm-model claude-sonnet-4-20250514
```

**OpenRouter** (Kimi K2.5, DeepSeek V3, etc.):
```bash
export OPENROUTER_API_KEY="your-key-here"
python scripts/run_calibration.py --gm-provider openrouter --gm-model moonshotai/kimi-k2.5
```

**Ollama** (self-hosted):
```bash
export OLLAMA_BASE_URL="http://localhost:11434"  # default
python scripts/run_calibration.py --gm-provider ollama --gm-model llama3.1:70b
```

### GM Stack Version Format

Every result includes a reproducible GM stack version string:
```
{provider}:{model_id}:temp{temp}:prompt{sha8}:res{sha8}
```
Example: `anthropic:claude-sonnet-4-20250514:temp0.3:prompt9f3a2b1c:resd4e7f902`

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

# Live run against Sonnet 4 GM
python scripts/run_calibration.py --gm-model claude-sonnet-4-20250514

# With OpenRouter provider
python scripts/run_calibration.py --gm-provider openrouter --gm-model moonshotai/kimi-k2.5
```

Pass/fail thresholds:
- GM acceptance rate: 60-75%
- Average counter-offers before acceptance: 2-4
- Clarifying question rate: >= 1 per negotiation
- Granite Bay wrong-position refusal: 100%

### Calibration Bake-Off

Compares multiple GM candidates head-to-head using identical noise seeds.

```bash
# Dry run
python scripts/run_calibration_bakeoff.py --dry-run

# Full bake-off (default candidates: Sonnet 4, Kimi K2.5, DeepSeek V3)
python scripts/run_calibration_bakeoff.py

# Custom candidates
python scripts/run_calibration_bakeoff.py --candidates '[["anthropic","claude-sonnet-4-20250514"],["openrouter","moonshotai/kimi-k2.5"]]'

# Skip leakage judge (faster)
python scripts/run_calibration_bakeoff.py --skip-leakage
```

Captures 5 metrics per candidate:
1. Acceptance rate (60-75%)
2. Counter-offer count (2-4)
3. Clarifying question rate (>=1)
4. Granite Bay wrong-position refusal (100%)
5. Probe-induced leak rate (<5%)

Results are written to `results/calibration_bakeoff_<timestamp>/` and `BAKEOFF_RESULTS.md`.

### Pilot Run

Runs models x N runs for initial validation.

```bash
# Dry run
python scripts/run_pilot.py --dry-run

# Single model, 1 run
python scripts/run_pilot.py --models claude-sonnet-4-20250514 --n-runs 1

# With custom GM provider
python scripts/run_pilot.py --gm-provider openrouter --gm-model moonshotai/kimi-k2.5
```

### Full Leaderboard

Configurable model list with pre-registered analysis.

```bash
# Dry run
python scripts/run_leaderboard.py --dry-run

# Full run with analysis
python scripts/run_leaderboard.py --models model-a model-b model-c --n-runs 10

# With custom GM
python scripts/run_leaderboard.py --gm-provider anthropic --gm-model claude-sonnet-4-20250514
```

### Judge Validation

Validates leakage judge against hand-graded threads.

```bash
python scripts/validate_judge.py --csv results/graded_threads.csv
```

## Config File Format

All scripts accept `--config path/to/config.json`:

```json
{
  "models": ["claude-sonnet-4-20250514"],
  "gm_model": "claude-sonnet-4-20250514",
  "gm_provider": "anthropic",
  "n_runs": 10,
  "gm_stack_version": "v3.0-leaderboard"
}
```

## Output Structure

Results are saved to `results/` with timestamped directories:

```
results/
├── pilot_20250101_120000/
│   ├── claude-sonnet-4-20250514.json
│   └── summary.json
├── calibration_20250101_120000/
│   └── calibration_result.json
├── calibration_bakeoff_20250101_120000/
│   ├── anthropic_claude-sonnet-4-20250514.json
│   ├── openrouter_moonshotai_kimi-k2.5.json
│   ├── openrouter_deepseek_deepseek-chat-v3-0324.json
│   ├── all_results.json
│   └── summary.md
└── leaderboard_20250101_120000/
    ├── results.json
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
├── gm_clients/
│   ├── base.py            # GMClient abstract base class
│   ├── anthropic_client.py # Anthropic SDK wrapper
│   ├── openrouter_client.py # OpenRouter API wrapper
│   ├── ollama_client.py   # Ollama HTTP wrapper
│   └── __init__.py        # make_gm_client() factory + build_gm_stack_version()
├── baselines/
│   ├── floor_aware.py     # Floor-Aware Baseline (Appendix E.1)
│   └── truly_naive.py     # Truly-Naive Baseline (Appendix E.2)
├── calibration/
│   └── probe_agent.py     # Calibration Probe (Appendix C)
└── analysis/
    └── preregistered.py   # H1, H2a, H2b, H2c (Appendix F)
```

## GM Selection Rationale

The GM model selection is based on measured calibration performance, not assumption. See `CALIBRATION_NOTES.md` for the full remediation history and `BAKEOFF_RESULTS.md` for head-to-head comparison data.

The capability that matters most for the GM role is **instruction following**: holding private numbers, deflecting direct questions, asking clarifying questions, and never quoting maximums. Coding ability and reasoning depth are irrelevant for this role.

## Spec Reference

Full specification: `moneyball_bench_v3.md`

See `QUESTIONS.md` for interpretive decisions and spec ambiguities.
