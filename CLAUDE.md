# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

MoneyBall Bench v3.0 is a research-grade benchmark measuring LLM negotiation performance under information asymmetry. An agent LLM plays a sports agent negotiating contracts for 6 fictional NBA players against 6 fictional team GMs (also LLMs), with the GMs holding private reservation prices the agent must extract through dialogue.

The canonical specification is `moneyball_bench_v3.md`. Section references (e.g. §7.4, Appendix C) in code comments point into that spec — when changing observable behavior, cross-check the spec.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run tests (markers: requires_api for live-API tests)
pytest tests/ -v
pytest tests/ -v -m "not requires_api"        # skip live-API tests
pytest tests/test_orchestration.py::test_name # single test

# Calibration (verifies GM behavior before any leaderboard run)
python scripts/run_calibration.py --dry-run
python scripts/run_calibration.py             # uses DeepSeek V3 GM by default

# Multi-GM bake-off (head-to-head GM candidate comparison)
python scripts/run_calibration_bakeoff.py

# Pilot / full leaderboard
python scripts/run_pilot.py --models <model> --n-runs <n>
python scripts/run_leaderboard.py --models <model-a> <model-b> --n-runs 10

# Leakage judge validation
python scripts/validate_judge.py --csv results/graded_threads.csv
```

Scripts accept `--config path.json` for batch parameter sets. Required env vars: `OPENROUTER_API_KEY` (production default), `ANTHROPIC_API_KEY` (Anthropic provider), `OLLAMA_BASE_URL` (Ollama).

## Architecture

The system has three swappable LLM roles and a deterministic environment that mediates between them.

### The three LLM roles

1. **Agent** — the model under evaluation. Plays the sports agent. Sees player stat cards and public team profiles; must extract reservation info via email and close deals.
2. **GM** — one per team (6 total). All six are the *same model and prompt* but with team-specific system prompts and private reservation prices. **The GM stack is a load-bearing benchmark component**: changing GM model = different benchmark version. Every result is tagged with a `gm_stack_version` of the form `{provider}:{model_id}:temp{T}:prompt{sha8}:res{sha8}` (built by `gm_clients/__init__.py:build_gm_stack_version`).
3. **Leakage Judge** — separate model that grades each `(player, team)` email thread 0/1/2 for information leakage (Appendix D, `leakage_judge.py`).

GM and Agent providers are independent and configurable per run. Factories: `make_gm_client()` in `moneyballbench/gm_clients/__init__.py`, `make_agent_client()` in `moneyballbench/agent_clients/__init__.py`. Supported GM providers: `anthropic`, `openrouter`, `ollama`. Supported agent providers: `anthropic`, `openrouter`.

### The orchestration loop

`orchestration.py:run_benchmark()` is the single source of truth for one benchmark run. It:

1. Applies per-run multiplicative noise to reservation prices via `noise.apply_reservation_noise()` (seeded by `hash(gm_stack_version + run_id)` so all models in a cohort face identical fuzz).
2. Builds an `NBASimEnvironment` (deterministic, holds all hidden state).
3. Runs an Anthropic-style tool-use loop (`messages.create` → `tool_use` blocks → `tool_result` → repeat) up to `MAX_TURNS = 300`.
4. Returns the structured result dict matching the §7.4 schema.

The agent client interface is the Anthropic SDK shape: `client.messages.create(model, max_tokens, system, tools, messages)` returning `resp.stop_reason` and `resp.content` with `.type in {"text", "tool_use"}`. The OpenRouter agent client (`agent_clients/openrouter_agent.py`) adapts OpenRouter's API to this shape — preserve that contract when adding new agent providers.

### NBASimEnvironment — the deterministic core

`environment.py:NBASimEnvironment` owns all state the agent can affect: signed deals, email threads (one per team), inbox, rejection budgets, locked pairs, committed payroll. The agent only sees this state via 7 tools (`tools.py`):

- `send_email`, `read_inbox` — async-style email between agent and GMs (GM call happens inside `send_email`)
- `view_player_profile`, `view_team_cap_sheet` — cheap reads of public info
- `check_commission_tracker` — running score
- `close_deal` — the only way to actually sign (validates floor, cap, max_aav, max_years; enforces rejection budget)
- `advance_round` — moves the 10-round clock forward; round 10 triggers `_close_window` and auto-signs

`close_deal` is where three safety mechanisms compose: per-(player, team) **rejection budget** (3 above-ceiling attempts then locked), the **orchestration backstop** (rejects above noised `max_aav` even if GM verbally agreed), and **noise** (seeded fuzz on reservation prices). The Granite Bay Bulls have a hard "interior players only" rule enforced by string-matching the email body in `send_email` — auto-stub responses when wrong-position players are mentioned.

Key invariant: the agent is *not* trusted to refuse out-of-bounds deals. The environment is the truth source; GM agreement is informational only.

### Static data lives in config.py

`config.py` holds player profiles, public team profiles, base reservation prices, salary cap, max salary, auto-sign penalty, etc. — all per the spec (§4, §5, §7.2). When changing benchmark parameters, change them here and expect to update tests and possibly `gm_stack_version` bookkeeping.

### Pre-registered analysis

`analysis/preregistered.py` implements H1 (commission gap) and H2a/b/c (leakage correlations) from Appendix F with fixed decision rules (e.g. H1: p<0.05 AND CI separation). Don't change these statistical tests casually — they are the published methodology.

### Baselines and the calibration probe

`baselines/floor_aware.py` and `baselines/truly_naive.py` are scripted (non-LLM) reference agents for context (Appendix E). `calibration/probe_agent.py` is a deterministic scripted agent used *only* to verify GM behavior before leaderboard runs (Appendix C); it is **not** a baseline for scoring. Calibration thresholds are defined in `scripts/run_calibration.py`.

## Output layout

Results are written to `results/<run-type>_<timestamp>/`. JSON schemas:
- `pilot_*/` — `<model>.json` per model, plus `summary.json`
- `calibration_*/` — `calibration_result.json`
- `calibration_bakeoff_*/` — per-candidate JSON, `all_results.json`, `summary.md`
- `leaderboard_*/` — `results.json`, `analysis.json`, `leaderboard.json`

Result dicts always include `gm_stack_version` and `noised_reservation_prices` for reproducibility.

## Testing notes

`tests/conftest.py` provides a `MockGMClient` that returns canned/generic GM responses keyed by team-name match against the system prompt. Use this for environment/orchestration tests; reserve live API calls for tests marked `@pytest.mark.requires_api`. The `env` fixture builds an `NBASimEnvironment` with `BASE_RESERVATION_PRICES` (un-noised) for deterministic assertions.

## When making changes

- **Spec-anchored code**: most modules cite section numbers from `moneyball_bench_v3.md`. Treat that doc as authoritative for observable benchmark behavior.
- **GM stack version is a fingerprint**: any change that affects GM behavior (prompt wording, temperature, reservation prices, model) must flow through `build_gm_stack_version` so results remain comparable.
- **Don't bypass the rejection budget or backstop** in the environment — they are part of the published benchmark mechanics, not implementation details.
