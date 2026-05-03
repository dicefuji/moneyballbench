# GM Calibration Bake-Off Results

**Date**: 2026-04-29 01:08 UTC

## Comparison Table

| Metric | Threshold | anthropic:claude-sonnet-4-20250514 | openrouter:moonshotai/kimi-k2.5 | openrouter:deepseek/deepseek-chat-v3-0324 |
| --- | --- | --- | --- | --- |
| Acceptance rate | 60-75% | 0% (DRY_RUN) | 0% (DRY_RUN) | 0% (DRY_RUN) |
| Avg counter-offers | 2-4 | 0.0 (DRY_RUN) | 0.0 (DRY_RUN) | 0.0 (DRY_RUN) |
| Avg clarifying Qs | >=1 | 0.0 (DRY_RUN) | 0.0 (DRY_RUN) | 0.0 (DRY_RUN) |
| GB wrong-pos refusal | 100% | 100% (DRY_RUN) | 100% (DRY_RUN) | 100% (DRY_RUN) |
| Probe leak rate | <5% | 0.0% (DRY_RUN) | 0.0% (DRY_RUN) | 0.0% (DRY_RUN) |
| **Overall** | | **FAIL** | **FAIL** | **FAIL** |

## Per-Candidate Observations

### anthropic:claude-sonnet-4-20250514

- Failing metrics: acceptance_rate, avg_counters, clarifying_questions, granite_bay_refusal, probe_leak_rate

### openrouter:moonshotai/kimi-k2.5

- Failing metrics: acceptance_rate, avg_counters, clarifying_questions, granite_bay_refusal, probe_leak_rate

### openrouter:deepseek/deepseek-chat-v3-0324

- Failing metrics: acceptance_rate, avg_counters, clarifying_questions, granite_bay_refusal, probe_leak_rate

## Recommendation

No candidate passed all calibration metrics. Further remediation or alternative candidates needed.