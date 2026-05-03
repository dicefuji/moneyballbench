# Cap-Pressure Stratification Analysis

**Generated:** 2026-05-03 14:39 UTC

## Summary

Across all models, 123 cap-pressure threads had an extraction rate of 2.8% compared to 2.7% for 396 non-cap-pressure threads (gap: +0.1pp, Fisher's p=1.000). Hard-leak rate was 0.9% for cap-pressure threads vs 0.3% for non-cap-pressure threads (gap: +0.7pp, Fisher's p=0.403).

## Analysis 1: Leakage by cap-pressure status, per model

| Model | n_cp (judged) | ext_rate_cp | ext_rate_non_cp | ext_gap | hard_rate_cp | hard_rate_non_cp | hard_gap | fisher_p (ext) | fisher_p (hard) |
|-------|--------------|-------------|-----------------|---------|-------------|-----------------|---------|---------------|----------------|
| DeepSeek V3 | 38 (38) | 5.3% | 4.8% | +0.5pp | 2.6% | 0.0% | +2.6pp | 1.000 | 0.311 |
| K2.5 | 17 (16) | 0.0% | 1.6% | -1.6pp | 0.0% | 0.0% | +0.0pp | 1.000 | 1.000 |
| K2.6@2048 | 3 (3) | 0.0% | 0.0% | +0.0pp | 0.0% | 0.0% | +0.0pp | 1.000 | 1.000 |
| K2.6@4096 | 14 (0) | 0.0% | 0.0% | +0.0pp | 0.0% | 0.0% | +0.0pp | 1.000 | 1.000 |
| Qwen3 Max | 11 (11) | 0.0% | 5.1% | -5.1pp | 0.0% | 1.7% | -1.7pp | 1.000 | 1.000 |
| V4 Flash | 22 (22) | 0.0% | 1.5% | -1.5pp | 0.0% | 0.0% | +0.0pp | 1.000 | 1.000 |
| V4 Pro | 18 (18) | 5.6% | 1.4% | +4.2pp | 0.0% | 0.0% | +0.0pp | 0.362 | 1.000 |

## Analysis 2: Cap-pressure prevalence per model

| Model | Total runs | Multi-sign attempt runs | Cap rejection runs | Successful multi-sign runs | Top multi-sign team |
|-------|-----------|------------------------|-------------------|--------------------------|-------------------|
| DeepSeek V3 | 10 | 4 | 2 | 4 | Apex City Aces (1x) |
| K2.5 | 10 | 6 | 0 | 6 | Apex City Aces (3x) |
| K2.6@2048 | 10 | 1 | 0 | 1 | Granite Bay Bulls (1x) |
| K2.6@4096 | 7 | 4 | 0 | 4 | Harlow Vipers (2x) |
| Qwen3 Max | 10 | 4 | 0 | 4 | Apex City Aces (3x) |
| V4 Flash | 10 | 6 | 0 | 6 | Granite Bay Bulls (5x) |
| V4 Pro | 10 | 5 | 0 | 5 | Granite Bay Bulls (4x) |

## Analysis 3: Pooled view

| Group | n (judged) | Extraction rate | Hard-leak rate |
|-------|-----------|----------------|---------------|
| Cap-pressure | 123 (108) | 2.8% | 0.9% |
| Non-cap-pressure | 396 (367) | 2.7% | 0.3% |
| **Gap** | | **+0.1pp** | **+0.7pp** |

**Fisher's exact test (extraction, two-sided):** p = 1.000

Contingency table (extraction):

| | Cap-pressure | Non-cap-pressure |
|---|---|---|
| Leaked (score >= 1) | 3 | 10 |
| Not leaked | 105 | 357 |

**Fisher's exact test (hard leak, two-sided):** p = 0.403

Contingency table (hard leak):

| | Cap-pressure | Non-cap-pressure |
|---|---|---|
| Hard leaked (score = 2) | 1 | 1 |
| Not hard leaked | 107 | 366 |

## Methodology notes

- **Cap-pressure thread definition:** as in `CAP_PRESSURE_THREADS.md`. A thread qualifies if (a) the agent signed 2+ players at the same team in the same run (multi-signing cap conflict), or (b) the GM explicitly references cap constraints after a prior signing at the same team.
- **Statistical test:** Fisher's exact test, two-sided, on the 2x2 contingency table (leaked/not-leaked x cap-pressure/non-cap-pressure).
- **Judge model:** DeepSeek V3 (`deepseek/deepseek-v3.2-exp`). Not kappa-validated.
- **Thread identification:** Player names detected in email exchange text. League notice broadcasts filtered out.
- **Data sources:** `results/pilot_20260429_063208/`, `results/k26_4096_retest_20260429_175832/`, `results/pilot_extended_20260501_033846/`, `results/pilot_v4flash_20260502_184050/`, `results/pilot_v4pro_20260502_230557/`
- **Models in scope:** K2.5, K2.6@2048, K2.6@4096, Qwen3 Max, DeepSeek V3, V4 Flash, V4 Pro (7 model variants across 70 runs).
- **Judged threads only:** Extraction and hard-leak rates computed only over threads with a judge score. Unjudged threads (e.g., K2.6@4096 runs) are excluded from rate calculations but included in cap-pressure classification counts.
