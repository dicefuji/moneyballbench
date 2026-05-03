# Pilot Results — Six-Model Comparison

**Date**: 2026-04-29 (K2.5/K2.6), 2026-05-01 (Qwen3 Max/DeepSeek V3), 2026-05-02 (V4 Flash/V4 Pro)
**GM**: `openrouter:deepseek/deepseek-v3.2-exp` (temperature 0.3)
**GM stack version**: `openrouter:deepseek/deepseek-v3.2-exp:temp0.3:prompt2b5cbd8f:res808494e6`
**Judge**: `openrouter:deepseek/deepseek-v3.2-exp`
**Agent provider**: OpenRouter (all models)
**n_runs**: 10 per model (run_id seeds 0-9, identical noise across all six models)
**max_tokens**: 2048 (all models)
**Season**: 1 only

---

## Summary Statistics

| Metric | Kimi K2.5 | Kimi K2.6 | Qwen3 Max | DeepSeek V3 | V4 Flash | V4 Pro |
|--------|-----------|-----------|-----------|-------------|----------|--------|
| **Mean net score** | 14.62 | -0.87 | 15.89 | **18.33** | 16.69 | 18.20 |
| Std dev | 6.50 | 6.74 | 1.32 | 1.02 | 1.55 | 1.01 |
| **95% bootstrap CI** | (10.26, 17.48) | (-3.00, 3.39) | (15.14, 16.71) | **(17.76, 18.97)** | (15.83, 17.60) | (17.68, 18.85) |
| Min | -3.0 | -3.0 | 14.2 | 17.3 | 14.7 | 17.3 |
| Max | 19.5 | 18.3 | 18.5 | 20.0 | 19.5 | 20.6 |
| Mean auto-signed | 0.7 | 5.4 | 0.1 | 0.0 | 0.0 | 0.0 |
| Mean rejection budget usage | 0.0 | 0.0 | 0.0 | 0.4 | 0.0 | 0.0 |
| **Success rate** | 9/10 | 1/10 | **10/10** | **10/10** | **10/10** | **10/10** |

**Notes:**
- DeepSeek V3 as agent is self-play (same model serves as GM and judge)
- DeepSeek V4 Pro = `deepseek/deepseek-v4-pro` (1.6T MoE, 49B activated, default reasoning mode)
- DeepSeek V4 Flash = `deepseek/deepseek-v4-flash` (284B MoE, 13B activated, default reasoning mode)
- Qwen3 Max = `qwen/qwen3-max` on OpenRouter
- K2.6's failures are caused by tool-calling reliability issues (see Appendix)

---

## Per-Run Detail

### Kimi K2.5

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | 17.9 | 5 | 1 | 21 |
| 1 | 17.3 | 6 | 0 | 15 |
| 2 | -3.0 | 0 | 6 | 3 |
| 3 | 15.4 | 6 | 0 | 11 |
| 4 | 12.5 | 6 | 0 | 23 |
| 5 | 18.4 | 6 | 0 | 28 |
| 6 | 19.5 | 6 | 0 | 13 |
| 7 | 15.6 | 6 | 0 | 16 |
| 8 | 17.4 | 6 | 0 | 20 |
| 9 | 15.2 | 6 | 0 | 27 |

### Kimi K2.6

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | -3.0 | 0 | 6 | 1 |
| 1 | -3.0 | 0 | 6 | 3 |
| 2 | -3.0 | 0 | 6 | 4 |
| 3 | -3.0 | 0 | 6 | 3 |
| 4 | -3.0 | 0 | 6 | 6 |
| 5 | -3.0 | 0 | 6 | 4 |
| 6 | **18.3** | **6** | 0 | 17 |
| 7 | -3.0 | 0 | 6 | 5 |
| 8 | -3.0 | 0 | 6 | 3 |
| 9 | -3.0 | 0 | 6 | 6 |

### Qwen3 Max

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | 14.2 | 6 | 0 | 25 |
| 1 | 15.1 | 5 | 1 | 59 |
| 2 | 15.9 | 6 | 0 | 34 |
| 3 | 14.4 | 6 | 0 | 20 |
| 4 | 15.3 | 6 | 0 | 23 |
| 5 | 16.3 | 6 | 0 | 20 |
| 6 | 16.4 | 6 | 0 | 17 |
| 7 | 15.5 | 6 | 0 | 37 |
| 8 | 17.5 | 6 | 0 | 14 |
| 9 | 18.5 | 6 | 0 | 32 |

### DeepSeek V3 (self-play)

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | 17.5 | 6 | 0 | 66 |
| 1 | 17.3 | 6 | 0 | 46 |
| 2 | 17.8 | 6 | 0 | 72 |
| 3 | 17.7 | 6 | 0 | 88 |
| 4 | 18.8 | 6 | 0 | 66 |
| 5 | 17.3 | 6 | 0 | 81 |
| 6 | 19.9 | 6 | 0 | 69 |
| 7 | 18.7 | 6 | 0 | 74 |
| 8 | 18.5 | 6 | 0 | 73 |
| 9 | 20.0 | 6 | 0 | 58 |

### DeepSeek V4 Flash

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | 18.0 | 6 | 0 | 16 |
| 1 | 14.7 | 6 | 0 | 19 |
| 2 | 16.3 | 6 | 0 | 21 |
| 3 | 18.0 | 6 | 0 | 16 |
| 4 | 15.2 | 6 | 0 | 29 |
| 5 | 14.9 | 6 | 0 | 28 |
| 6 | 19.5 | 6 | 0 | 26 |
| 7 | 17.2 | 6 | 0 | 17 |
| 8 | 17.2 | 6 | 0 | 20 |
| 9 | 16.0 | 6 | 0 | 19 |

### DeepSeek V4 Pro

| Run | Score | Deals | Auto-signed | Turns |
|-----|-------|-------|-------------|-------|
| 0 | 17.3 | 6 | 0 | 18 |
| 1 | 17.3 | 6 | 0 | 25 |
| 2 | 17.9 | 6 | 0 | 24 |
| 3 | 17.8 | 6 | 0 | 23 |
| 4 | 17.4 | 6 | 0 | 18 |
| 5 | 18.3 | 6 | 0 | 18 |
| 6 | 18.1 | 6 | 0 | 17 |
| 7 | 18.2 | 6 | 0 | 15 |
| 8 | 20.6 | 6 | 0 | 24 |
| 9 | 19.1 | 6 | 0 | 22 |

**Note:** DeepSeek V3 uses the most turns (avg 69), followed by Qwen3 Max (avg 28), V4 Pro (avg 20), V4 Flash (avg 21), and K2.5 (avg 18). V4 Pro matches DeepSeek V3's scores with 3.5x fewer turns. V4 Pro occasionally sends malformed tool arguments but self-corrects when the orchestration returns an error — all 10 runs completed successfully.

---

## Leakage Statistics

| Metric | Kimi K2.5 | Kimi K2.6 | Qwen3 Max | DeepSeek V3 | V4 Flash | V4 Pro |
|--------|-----------|-----------|-----------|-------------|----------|--------|
| Mean extraction rate | 0.29% | 0.0% | 0.86% | 1.68% | 0.28% | 0.56% |
| Mean hard leak rate | 0.0% | 0.0% | 0.30% | 0.28% | 0.0% | 0.0% |
| Runs with any leak (score >= 1) | 1/10 | 0/10 | 3/10 | 4/10 | 1/10 | 2/10 |
| Runs with hard leak (score = 2) | 0/10 | 0/10 | 1/10 | 1/10 | 0/10 | 0/10 |

All models have low leakage below the 5% concern threshold from Appendix C. V4 Pro shows moderate extraction (0.56%) with no hard leaks — similar profile to K2.5 and V4 Flash.

---

## CI Overlap Matrix (§8.2)

| | K2.5 (10.26, 17.48) | K2.6 (-3.00, 3.39) | Qwen3 Max (15.14, 16.71) | DeepSeek V3 (17.76, 18.97) | V4 Flash (15.83, 17.60) | V4 Pro (17.68, 18.85) |
|---|---|---|---|---|---|---|
| **K2.5** | — | No overlap | **Overlap (tied)** | No overlap | **Overlap (tied)** | No overlap |
| **K2.6** | No overlap | — | No overlap | No overlap | No overlap | No overlap |
| **Qwen3 Max** | **Overlap (tied)** | No overlap | — | No overlap | **Overlap (tied)** | No overlap |
| **DeepSeek V3** | No overlap | No overlap | No overlap | — | No overlap | **Overlap (tied)** |
| **V4 Flash** | **Overlap (tied)** | No overlap | **Overlap (tied)** | No overlap | — | No overlap |
| **V4 Pro** | No overlap | No overlap | No overlap | **Overlap (tied)** | No overlap | — |

**Ranking per §8.2:**

1. **DeepSeek V3 ≈ DeepSeek V4 Pro** — tied (CIs overlap). V3 mean 18.33, V4 Pro mean 18.20. Both have std ~1.0 and 10/10 success. V4 Pro achieves near-identical scores with 3.5x fewer turns and without self-play advantage.
2. **DeepSeek V4 Flash ≈ Qwen3 Max ≈ Kimi K2.5** — tied (CIs overlap pairwise). V4 Flash has the highest mean (16.69) in this tier, followed by Qwen3 Max (15.89) and K2.5 (14.62).
3. **Kimi K2.6** — mean -0.87, CI (-3.00, 3.39). Tool-calling failures make it non-viable at max_tokens=2048.

---

## Cost Report

### Estimated costs (based on OpenRouter pricing)

| Component | Model | Requests (est.) | Cost/request | Total |
|-----------|-------|-----------------|--------------|-------|
| GM (K2.5 runs) | deepseek/deepseek-v3.2-exp | ~1,200 | ~$0.0002 | ~$0.24 |
| GM (K2.6 runs) | deepseek/deepseek-v3.2-exp | ~200 | ~$0.0002 | ~$0.04 |
| GM (Qwen runs) | deepseek/deepseek-v3.2-exp | ~1,400 | ~$0.0002 | ~$0.28 |
| GM (DeepSeek V3 runs) | deepseek/deepseek-v3.2-exp | ~3,500 | ~$0.0002 | ~$0.70 |
| GM (V4 Flash runs) | deepseek/deepseek-v3.2-exp | ~630 | ~$0.0002 | ~$0.13 |
| GM (V4 Pro runs) | deepseek/deepseek-v3.2-exp | ~610 | ~$0.0002 | ~$0.12 |
| Agent (K2.5) | moonshotai/kimi-k2.5 | ~200 | ~$0.003 | ~$0.60 |
| Agent (K2.6) | moonshotai/kimi-k2.6 | ~50 | ~$0.005 | ~$0.25 |
| Agent (Qwen3 Max) | qwen/qwen3-max | ~300 | ~$0.005 | ~$1.50 |
| Agent (DeepSeek V3) | deepseek/deepseek-v3.2-exp | ~700 | ~$0.0002 | ~$0.14 |
| Agent (V4 Flash) | deepseek/deepseek-v4-flash | ~210 | ~$0.0005 | ~$0.11 |
| Agent (V4 Pro) | deepseek/deepseek-v4-pro | ~200 | ~$0.0016 | ~$0.32 |
| Judge (all models) | deepseek/deepseek-v3.2-exp | ~900 | ~$0.0002 | ~$0.18 |
| **Total** | | | | **~$4.61** |

### Per-model cost breakdown

| Model | Agent cost | GM cost | Total (excl. judge) |
|-------|-----------|---------|---------------------|
| Kimi K2.5 | ~$0.60 | ~$0.24 | ~$0.84 |
| Kimi K2.6 | ~$0.25 | ~$0.04 | ~$0.29 |
| Qwen3 Max | ~$1.50 | ~$0.28 | ~$1.78 |
| DeepSeek V3 | ~$0.14 | ~$0.70 | ~$0.84 |
| DeepSeek V4 Flash | ~$0.11 | ~$0.13 | ~$0.24 |
| DeepSeek V4 Pro | ~$0.32 | ~$0.12 | ~$0.44 |

Notes:
- DeepSeek V4 Flash remains the cheapest model ($0.24 for 10 runs)
- V4 Pro costs ~$0.44 for 10 runs — still very economical for top-tier performance
- DeepSeek V3 self-play is cheap per-request but uses the most turns (avg 69), adding up in GM costs
- Qwen3 Max is the most expensive agent (~$0.005/request) but still reasonable at ~$1.50 total
- K2.6 costs were low because most runs ended early (1-6 turns)
- A 136-run scale-up with V4 Pro would cost ~$6.00 total; with V4 Flash ~$3.26; with Qwen3 Max ~$24

---

## Failure Mode Analysis

### K2.5 Run 2 (score=-3.0, 0 deals)

- Only 3 turns used, agent ended turn very early
- One-off failure in an otherwise reliable model (9/10 success rate)

### K2.6 Systematic Failure (9/10 runs)

- K2.6 consistently ends turns within 1-6 turns without sending emails or engaging tools
- Run 6 (the sole success) shows K2.6 CAN negotiate effectively when it engages
- This is a tool-calling reliability issue, not a negotiation capability issue
- K2.6 uses reasoning tokens (~1100/response) which interfere with tool calling at max_tokens=2048

### Qwen3 Max — No failures

- 10/10 runs completed successfully with deals
- Only 1 auto-signed player across all 10 runs (run 1)
- Most consistent model by standard deviation (std=1.32)

### DeepSeek V3 — No failures

- 10/10 runs completed successfully, all 6 deals signed in every run
- Zero auto-signs across all runs
- Uses more turns (avg 69 vs 28 for Qwen, 18 for K2.5) indicating deeper negotiations
- Mean rejection budget usage of 0.4 suggests occasional close_deal rejections before finding acceptable terms

### DeepSeek V4 Flash — No failures

- 10/10 runs completed successfully, all 6 deals signed in every run
- Zero auto-signs across all runs
- Average 21 turns per run — efficient negotiations, comparable to K2.5 and Qwen3 Max
- No truncation issues at max_tokens=2048 despite being a reasoning model
- Zero rejection budget usage
- Occasional transient API errors (HTTP 400/429) handled by retry logic

### DeepSeek V4 Pro — No failures (with tool-call recovery)

- 10/10 runs completed successfully, all 6 deals signed in every run
- Zero auto-signs across all runs
- Average 20 turns per run — matches V4 Flash's efficiency
- Occasional malformed tool arguments (missing `to`, `subject`, or `body` in send_email calls). The orchestration returns an error message and V4 Pro self-corrects on the next turn. This pattern appeared in most runs but never prevented completion.
- Zero rejection budget usage
- Tightest standard deviation of any model (std=1.01), tied with DeepSeek V3 (1.02)

---

## Power Analysis

| Parameter | Value |
|-----------|-------|
| Pooled within-model std (K2.5/K2.6 only) | 6.62 |
| Pooled within-model std (all 6 models) | 3.64 |
| Pooled within-model std (Qwen/V3/V4 Flash/V4 Pro) | 1.24 |
| Target effect size | $2M |
| Required power | 80% |
| Alpha | 0.05 |
| **n needed (V4 Pro vs DeepSeek V3)** | **~5 per model** |
| **n needed (V4 Flash vs Qwen3 Max)** | **~8 per model** |
| **n needed (K2.5 vs Qwen)** | **~136 per model** |
| n=10 sufficient for V4 Pro vs DeepSeek V3? | **Yes** (but CIs overlap — models are tied) |
| n=10 sufficient for V4 Flash vs Qwen3 Max? | **No** (CIs overlap) |
| n=10 sufficient for V4 Pro vs V4 Flash? | **Yes** (CIs don't overlap) |

The four consistent models (Qwen3 Max, DeepSeek V3, V4 Flash, V4 Pro) have tight standard deviations (1.01-1.55). V4 Pro and V3 form a top tier that separates from V4 Flash and Qwen3 Max.

---

## Appendix: K2.6 Token Limit Investigation

Devin Review flagged that K2.6's failures might be caused by `max_tokens=2048` truncating responses before tool calls are emitted (K2.6 uses ~1100 reasoning tokens per response). A follow-up experiment doubled the token budget.

### Configuration

- Same setup as original pilot, except `max_tokens=4096` (was 2048)
- K2.6 only, run_id seeds 0-6 (7 runs completed before early termination)

### Results

| Run | Score | Deals | Auto-signed | Turns | Notes |
|-----|-------|-------|-------------|-------|-------|
| 0 | **14.3** | **6** | 0 | 11 | Success |
| 1 | -3.0 | 0 | 6 | 1 | Truncation warning logged (`finish_reason=length`) |
| 2 | -3.0 | 0 | 6 | 1 | Truncation warning logged |
| 3 | **17.5** | **6** | 0 | 23 | Success (with 1 retry on malformed tool args) |
| 4 | -3.0 | 0 | 6 | 4 | Truncation warning logged |
| 5 | **18.5** | **6** | 0 | 14 | Success |
| 6 | **14.2** | **6** | 0 | 11 | Success |

### Comparison

| Metric | K2.6 @ 2048 (original) | K2.6 @ 4096 | K2.5 @ 2048 |
|--------|----------------------|-------------|-------------|
| Mean score | -0.87 | **7.91** | **14.62** |
| Std dev | 6.74 | 10.33 | 6.50 |
| 95% CI | (-3.00, 3.39) | (1.90, 14.37) | (10.26, 17.48) |
| Success rate | 10% (1/10) | **57% (4/7)** | **90% (9/10)** |
| Mean auto-signed | 5.4 | 2.6 | 0.7 |

### Analysis

1. **Token limits are a significant factor.** Doubling `max_tokens` improved K2.6's success rate from 10% to 57%.
2. **Token limits are not the only factor.** Even at 4096, K2.6 still fails 43% of runs.
3. **When K2.6 succeeds, it performs well.** Successful K2.6 runs (mean=16.1 at 4096) are comparable to K2.5's successful runs (mean=16.6 at 2048).
4. **K2.5 remains the better choice.** K2.5 achieves 90% reliability at half the token cost.

---

## Conclusion

**DeepSeek V3 and V4 Pro are statistically tied for top tier** with overlapping CIs. V3 mean 18.33 (CI: 17.76-18.97), V4 Pro mean 18.20 (CI: 17.68-18.85). Both have 10/10 success, zero auto-signs, and std ~1.0. V4 Pro achieves this with 3.5x fewer turns (avg 20 vs 69) and without self-play advantage, suggesting its negotiation efficiency is genuinely strong.

**DeepSeek V4 Flash, Qwen3 Max, and Kimi K2.5 form a second tier** with overlapping CIs. V4 Flash has the highest mean (16.69) with the lowest cost ($0.24 for 10 runs). Qwen3 Max (15.89) is the most consistent in this tier. K2.5 (14.62) is more variable.

**Kimi K2.6 is non-viable** at max_tokens=2048 due to tool-calling failures (1/10 success). Increasing to 4096 helps (57% success) but does not match the other models.

**Self-play revisited:** V4 Pro (same architecture family as V3, not self-play) matching V3's scores undermines the hypothesis that V3 benefits primarily from shared architecture with the GM. V4 Pro's strong performance suggests that the DeepSeek V4 architecture is genuinely capable at negotiation tasks, independent of self-play effects.
