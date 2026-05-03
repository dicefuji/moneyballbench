# GM Calibration Bake-Off Results

**Date**: 2026-04-29 05:40 UTC

## Comparison Table

| Metric | Threshold | openrouter:moonshotai/kimi-k2.6 | openrouter:deepseek/deepseek-chat-v3-0324 |
| --- | --- | --- | --- |
| Acceptance rate | 60-75% | 67% (PASS) | 67% (PASS) |
| Avg counter-offers | 2-4 | 8.8 (FAIL) | 6.5 (FAIL) |
| Avg clarifying Qs | >=1 | 8.3 (PASS) | 1.7 (PASS) |
| GB wrong-pos refusal | 100% | 100% (PASS) | 100% (PASS) |
| Probe leak rate | <5% | N/A (N/A) | N/A (N/A) |
| **Overall** | | **FAIL** | **FAIL** |

## Per-Candidate Observations

### openrouter:moonshotai/kimi-k2.6

- Passing metrics: acceptance_rate, clarifying_questions, granite_bay_refusal
- Failing metrics: avg_counters

### openrouter:deepseek/deepseek-chat-v3-0324

- Passing metrics: acceptance_rate, clarifying_questions, granite_bay_refusal
- Failing metrics: avg_counters

## Recommendation

No candidate passed all calibration metrics. Further remediation or alternative candidates needed.