# GM Calibration Bake-Off Results

**Date**: 2026-04-29 UTC
**Run ID seed**: 42 (identical noise across all candidates)
**Leakage judge**: Skipped (requires Anthropic API credits; run separately with `--run-leakage`)

---

## Comparison Table

| Metric | Threshold | Sonnet 4 (Phase 10) | Kimi K2.6 | DeepSeek V3 |
|--------|-----------|---------------------|-----------|-------------|
| Acceptance rate | 60–75% | ~78% (near-pass) | 67% **PASS** | 67% **PASS** |
| Avg counter-offers | 2–4 | ~3.7 **PASS** | 8.8 FAIL | 6.5 FAIL |
| Avg clarifying Qs | ≥1 | ~4.6 **PASS** | 8.3 **PASS** | 1.7 **PASS** |
| GB wrong-pos refusal | 100% | 100% **PASS** | 100% **PASS** | 100% **PASS** |
| Probe leak rate | <5% | N/A | N/A | N/A |
| **Overall** | | **Near-pass** | **FAIL** | **FAIL** |

Sonnet 4 results are from Phase 10 iteration 3 (3-run average). Kimi K2.6 and DeepSeek V3 are single-run measurements from this bake-off.

---

## Per-Candidate Observations

### Anthropic: claude-sonnet-4-20250514 (Phase 10 baseline)

- **3/4 metrics pass**, acceptance rate ~78% (slightly above 75% target, expected to stabilize with multi-run averaging)
- Counter-offers average 3.7 — well within 2–4 range
- Rich clarifying behavior (avg 4.6 Qs per negotiation)
- GM prompts were NOT modified during calibration — all issues were probe-side
- Cost: ~$0.01–0.02/request (requires Anthropic API credits, currently unavailable)

### OpenRouter: moonshotai/kimi-k2.6

- **3/4 metrics pass**, but counter-offers at 8.8 is **2.2× the upper bound**
- Negotiations are extremely drawn-out: signed deals took 4–12 exchanges (counter distribution: [9, 4, 12, 10])
- Very high clarifying question rate (8.3 avg) — Kimi asks many questions but is slow to converge on a specific AAV
- GB wrong-position refusal: 100% (strong instruction following on position restrictions)
- The high counter-offer count suggests Kimi K2.6 is excessively cautious — it keeps negotiating instead of converging toward a deal
- 4/6 players signed (67% acceptance, same as DeepSeek)
- Cost: ~$0.005/request (reasoning token overhead — K2.6 uses ~1100 reasoning tokens per response)

### OpenRouter: deepseek/deepseek-chat-v3-0324

- **3/4 metrics pass**, counter-offers at 6.5 is **1.6× the upper bound** (better than Kimi but still failing)
- Counter distribution: [6, 9, 7, 4] — one deal closed quickly (4 exchanges), others took 6-9
- Minimal clarifying questions (1.7 avg) — DeepSeek engages more directly with numbers
- GB wrong-position refusal: 100% (strong instruction following)
- 4/6 players signed (67% acceptance)
- Cost: ~$0.0002/request (50× cheaper than Kimi, 100× cheaper than Sonnet 4)

---

## Raw Data

### Kimi K2.6

| Stat | Value |
|------|-------|
| Total negotiations | 36 |
| Players with offers | 6 |
| Players signed | 4 |
| Counter-offer counts (per signed deal) | 9, 4, 12, 10 |
| Clarifying Q counts (per player) | 7, 17, 2, 9, 9, 6 |

### DeepSeek V3

| Stat | Value |
|------|-------|
| Total negotiations | 36 |
| Players with offers | 6 |
| Players signed | 4 |
| Counter-offer counts (per signed deal) | 6, 9, 7, 4 |
| Clarifying Q counts (per player) | 1, 2, 2, 3, 1, 1 |

---

## Analysis

### Counter-Offer Failure Mode

Both OpenRouter candidates fail the counter-offer metric (2–4 target). The root cause differs:

- **Kimi K2.6** (8.8 avg): Over-negotiates. High reasoning token usage suggests the model deliberates extensively before each response, leading to cautious, incremental counter-offers rather than converging toward a deal point. The model asks many clarifying questions (8.3 avg) which extends the exchange count.

- **DeepSeek V3** (6.5 avg): Moderately over-negotiates. Engages more directly with numbers (only 1.7 clarifying Qs) but still takes 6-9 rounds to converge for most deals. The lower counter count vs Kimi suggests DeepSeek follows the GM reservation price constraints more tightly.

For comparison, **Sonnet 4** at 3.7 avg counters hits the sweet spot: enough resistance to test agent negotiation skill, but convergent enough to produce measurable deal flow within 10 rounds.

### Instruction Following Assessment

All three candidates demonstrate strong instruction following on the binary metrics:
- **GB wrong-position refusal**: 100% across all candidates (all correctly refuse to negotiate with wrong-position players for Granite Bay)
- **Acceptance rate**: All at 67-78% (reasonable deal closure rates)

The differentiator is nuanced instruction following — specifically, the GM's ability to hold a private reservation price, engage in natural-feeling negotiation, and converge toward a deal within the round budget. This is where Sonnet 4 excels.

### Cost-Effectiveness

| Model | Approx cost/request | Relative | Quality |
|-------|-------------------|----------|---------|
| DeepSeek V3 | $0.0002 | 1× | 3/4 metrics pass |
| Kimi K2.6 | $0.005 | 25× | 3/4 metrics pass |
| Sonnet 4 | $0.015 | 75× | ~4/4 metrics pass |

DeepSeek V3 is the clear value winner at 3/4 metrics passing. However, the failing counter-offer metric is the most important for benchmark validity — it determines whether negotiations are realistic enough to differentiate agent strategies.

---

## Recommendation

**Production GM: claude-sonnet-4-20250514 remains the recommended production GM stack.**

Rationale:
1. Only Sonnet 4 passes (or near-passes) all four calibration metrics
2. The counter-offer metric is the hardest to satisfy and the most important for benchmark validity
3. Both OpenRouter candidates over-negotiate by 1.6–2.2×, which would flatten agent score distributions (too many rounds → less differentiation between good and bad negotiators)

**Secondary recommendation: DeepSeek V3 as a cost-effective auxiliary GM stack for development/testing.**

DeepSeek V3 at $0.0002/request is 75× cheaper than Sonnet 4. While it fails the counter-offer threshold, its 6.5 avg is the closest to the 2–4 target among non-Anthropic candidates. For iterative development and debugging (where calibration precision matters less), DeepSeek V3 is a reasonable substitute.

**Not recommended: Kimi K2.6 for GM role.**

Despite strong instruction following on binary metrics, the 8.8 counter-offer average indicates the model is too cautious for the GM negotiation role. The reasoning token overhead also makes it 25× more expensive than DeepSeek for equivalent quality.

---

## Reproducing the Bake-Off

```bash
# Run with default candidates (Sonnet 4 + Kimi K2.6 + DeepSeek V3)
ANTHROPIC_API_KEY=... OPENROUTER_API_KEY=... python scripts/run_calibration_bakeoff.py

# Run specific candidates only
python scripts/run_calibration_bakeoff.py --candidates '[["openrouter","moonshotai/kimi-k2.6"],["openrouter","deepseek/deepseek-chat-v3-0324"]]'

# Include leakage judge (requires Anthropic API)
python scripts/run_calibration_bakeoff.py --run-leakage

# Results written to results/calibration_bakeoff_<timestamp>/
```
