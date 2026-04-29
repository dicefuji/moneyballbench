# Pilot Results — Kimi K2.5 vs K2.6

**Date**: 2026-04-29 UTC
**GM**: `openrouter:deepseek/deepseek-v3.2-exp` (temperature 0.3)
**GM stack version**: `openrouter:deepseek/deepseek-v3.2-exp:temp0.3:prompt2b5cbd8f:res808494e6`
**Agent provider**: OpenRouter
**n_runs**: 10 per model (run_id seeds 0-9, identical noise across models)
**Season**: 1 only

---

## Summary Statistics

| Metric | Kimi K2.5 | Kimi K2.6 |
|--------|-----------|-----------|
| **Mean net score** | **14.62** | -0.87 |
| Std dev | 6.50 | 6.74 |
| **95% bootstrap CI** | **(10.26, 17.48)** | (-3.00, 3.39) |
| Min | -3.0 | -3.0 |
| Max | 19.5 | 18.3 |
| Mean auto-signed | 0.7 | 5.4 |
| Mean rejection budget usage | 0.0 | 0.0 |
| Successful runs (deals > 0) | 9/10 | 1/10 |

**CIs do NOT overlap** → K2.5 ranked above K2.6 per §8.2.

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

---

## Leakage Statistics

| Metric | Kimi K2.5 | Kimi K2.6 |
|--------|-----------|-----------|
| Mean extraction rate | 0.29% (1 thread in 10 runs) | 0.0% |
| Mean hard leak rate | 0.0% | 0.0% |
| Runs with any leak (score ≥ 1) | 1/10 | 0/10 |
| Runs with hard leak (score = 2) | 0/10 | 0/10 |

Leakage is near-zero for both models. The single extraction event in K2.5 run 0 was a score-1 directional hint (not a hard leak). The DeepSeek V3 GM shows excellent information containment.

---

## CI Overlap Check (§8.2)

| | K2.5 CI | K2.6 CI | Overlap? |
|---|---------|---------|----------|
| Net score | (10.26, 17.48) | (-3.00, 3.39) | **No** |

**Result**: K2.5 is ranked above K2.6. The gap is large (~15.5 points) and statistically significant.

---

## Sample Observations

### K2.5 Run 0 (score=17.9, 5 deals)

- Agent engages all 6 teams with targeted pitches referencing player stats and team needs
- Negotiations are multi-turn with counter-offers and clarifying exchanges
- 5/6 players signed; 1 auto-signed (likely ran out of rounds for one player)
- Agent uses `view_player_profile` and `view_team_cap_sheet` tools to inform negotiations
- Email threads average ~10-15 messages per team

### K2.5 Run 6 (score=19.5, 6 deals — best run)

- All 6 players signed through active negotiation
- Agent efficiently matched players to team needs
- 13 turns total — the most efficient successful run

### K2.6 Run 6 (score=18.3, 6 deals — only successful K2.6 run)

- When K2.6 does engage, performance matches K2.5 (18.3 vs avg 16.1 for K2.5 successful runs)
- Email threads similar depth: 6-15 messages per team
- This demonstrates K2.6's capability is not the issue — reliability is

### K2.6 Run 0 (score=-3.0, 0 deals — typical failure)

- Agent exits after 1 turn with no emails sent (0 messages in all threads)
- The model appears to end_turn without using any tools
- This pattern repeats in 9/10 K2.6 runs
- Hypothesis: K2.6's instruction-following for tool use is unreliable — it often decides to end its turn rather than use the provided tools

---

## Failure Mode Analysis

### K2.5 Run 2 (score=-3.0, 0 deals)

- Only 3 turns used, agent ended turn very early
- One-off failure in an otherwise reliable model (9/10 success rate)
- Possible cause: agent's first response was end_turn without tool engagement

### K2.6 Systematic Failure (9/10 runs)

- K2.6 consistently ends turns within 1-6 turns without sending emails or engaging tools
- Typical pattern: model returns end_turn with text content but no tool_use blocks
- Occasionally makes a few tool calls but abandons the negotiation early
- Run 6 (the sole success) shows K2.6 CAN negotiate effectively when it engages
- This is a **tool-calling reliability issue**, not a negotiation capability issue
- K2.6 uses reasoning tokens (~1100/response) which may interfere with tool calling decisions

---

## Power Analysis

| Parameter | Value |
|-----------|-------|
| Pooled within-model std | 6.62 |
| Target effect size | $2M |
| Required power | 80% |
| Alpha | 0.05 |
| **n needed** | **136 per model** |
| n=10 sufficient? | **No** |

For a $2M mean difference with 80% power, n=136 runs per model would be needed. However, the K2.5 vs K2.6 gap (~15.5 points) is so large that n=10 is more than sufficient to detect it — the CIs don't overlap even at n=10.

For future leaderboard comparisons between models with similar performance levels, n=136+ would be needed to detect small ($2M) differences.

---

## Cost Report

### Estimated costs (based on OpenRouter pricing)

| Component | Model | Requests (est.) | Cost/request | Total |
|-----------|-------|-----------------|--------------|-------|
| GM (K2.5 runs) | deepseek/deepseek-v3.2-exp | ~1,200 | ~$0.0002 | ~$0.24 |
| GM (K2.6 runs) | deepseek/deepseek-v3.2-exp | ~200 | ~$0.0002 | ~$0.04 |
| Agent (K2.5) | moonshotai/kimi-k2.5 | ~200 | ~$0.003 | ~$0.60 |
| Agent (K2.6) | moonshotai/kimi-k2.6 | ~50 | ~$0.005 | ~$0.25 |
| Judge (all) | deepseek/deepseek-v3.2-exp | ~300 | ~$0.0002 | ~$0.06 |
| **Total** | | | | **~$1.19** |

Notes:
- K2.6 used fewer requests because most runs ended very early (1-6 turns)
- K2.5 reasoning tokens add cost overhead vs non-reasoning models
- The judge is very cheap since DeepSeek V3 is the judge model
- A full 136-run scale-up with K2.5 would cost ~$8-10 for the agent alone

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

1. **Token limits are a significant factor.** Doubling `max_tokens` improved K2.6's success rate from 10% to 57%. The `finish_reason=length` warning confirmed truncation was occurring even at 4096 tokens in 3/7 runs.

2. **Token limits are not the only factor.** Even at 4096, K2.6 still fails 43% of runs. Some failures show truncation warnings; others show malformed tool arguments (`tool_send_email() missing required positional arguments`). K2.6's reasoning token overhead (~1100 tokens) leaves less budget for tool call generation, and the model occasionally generates structurally invalid tool calls.

3. **When K2.6 succeeds, it performs well.** Successful K2.6 runs (mean=16.1 at 4096) are comparable to K2.5's successful runs (mean=16.6 at 2048). The capability gap is small; the reliability gap is large.

4. **K2.5 remains the better choice.** Even with a doubled token budget, K2.6's CI (1.90, 14.37) still barely overlaps K2.5's CI (10.26, 17.48), and K2.5 achieves 90% reliability at half the token cost.

### Recommendation

If K2.6 must be used, set `max_tokens=8192` or higher to further reduce truncation failures. However, K2.5 achieves better reliability at `max_tokens=2048` and is the recommended agent model for scale-up.

---

## Conclusion

**Kimi K2.5 is the clear pilot winner** with a mean net score of 14.62 (CI: 10.26-17.48) vs K2.6's -0.87 (CI: -3.00-3.39) at `max_tokens=2048`. The CIs do not overlap.

K2.6's failures are partially explained by token truncation — increasing `max_tokens` from 2048 to 4096 improved success rate from 10% to 57% — but K2.6 still underperforms K2.5 in reliability (57% vs 90%) even with doubled token budget. K2.6's reasoning token overhead (~1100 tokens/response) competes with tool call generation for the token budget.

When K2.6 succeeds, its negotiation quality matches K2.5 (mean 16.1 vs 16.6 for successful runs). The issue is reliability, not capability.

**Recommendation**: Use K2.5 as the primary agent model for scale-up. K2.6 is not suitable for benchmarking at standard token limits due to reasoning token overhead causing truncation and unreliable tool engagement.
