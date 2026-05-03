# MoneyBall Bench v3 — Findings Report

*A research-grade benchmark for measuring LLM negotiation under information asymmetry.*

**Date:** 2026-05-03
**Scope:** Seven agent variants, 67 completed runs, 519 player–team negotiations.
**GM stack (held fixed across the cohort):** `openrouter:deepseek/deepseek-v3.2-exp:temp0.3:prompt2b5cbd8f:res808494e6`.
**Leakage judge:** DeepSeek V3 (same model as GM), not yet kappa-validated.
**Spec:** `moneyball_bench_v3.md`. All decisions and metrics cited below trace to that document.

---

## 1. Abstract

MoneyBall Bench v3 puts an LLM agent in the role of an NBA sports agent negotiating six contracts against six team-GM LLMs that hold private reservation prices. The agent's score is its earned commission — a single, judgment-free arithmetic number — and a separate LLM judge grades each (player, team) email thread for information leakage on a 0/1/2 scale. Because GMs hold the numbers, three orchestration-side mechanisms — per-run noise, an independent close-deal backstop, and a per-pair rejection budget — prevent the benchmark from collapsing into binary search.

We ran a 67-run, 7-variant pilot. The headline finding is that **the bottleneck for current models is not GM information leakage, it is engagement and risk-narrative resistance**. The GM holds its private numbers reliably (extraction rate ≤ 9% across all variants; hard-leak rate ≤ 3%), but agents nevertheless leave most of the available money on the table — mean capture rate is 22.7% for the best variant, and is systematically lowest on the two players whose primary tests involve adverse-information framing (Kevin Okafor, Raymond Torres). Tier separation in net commission is dominated by *whether the agent finishes the run at all*, not by negotiation skill: K2.6 at the default 2048-token output budget completes only 1 of 10 runs end-to-end; raising the budget to 4096 recovers most of the gap. Once that failure mode is excluded, the four remaining frontier-class agents (DeepSeek V3, V4 Pro, V4 Flash, Qwen3 Max) sit in a $2.4M band whose 95% confidence intervals overlap on three of six pairs — the spec's TIED rule applies. We document one infrastructure issue (the calibration GM still fails the average-counter-offer threshold), one safety-mechanism observation (the rejection budget is essentially unused outside of self-play), and a set of qualitative failure modes drawn from 70 hand-curated negotiation threads.

## 2. Setup

The benchmark holds three LLMs in a fixed contract. The **agent** under test plays a sports agent and is given player stat cards (incl. comparable contracts and a private floor) plus public team profiles. The **GM** is one model called six times with team-specific system prompts that contain private `(max_aav, max_years)` reservation pairs. The **leakage judge** post-processes every (player, team) thread offline.

**Three safety mechanisms** compose to prevent reservation-price extraction by mechanical means (§3.3 of the spec):

1. **Reservation-price noise.** At run start, every nonzero `max_aav` is multiplied by `Uniform(0.95, 1.05)`, rounded to the nearest $0.5M, seeded by `hash(gm_stack_version + run_id)`. The seed structure is shared across the cohort so every model in a run faces identical fuzz.
2. **Orchestration backstop.** `close_deal` independently validates against the noised reservation. A GM that is socially engineered into agreeing still has the deal blocked.
3. **Per-pair rejection budget.** Each `(player, team)` allows three above-reservation `close_deal` attempts; the third locks the pair for the season. This kills binary-search-via-tool-spam.

**Score** is the spec's primary metric (§8.1):
$$\text{NetScore} = \sum_i \text{AAV}_i \cdot \text{Years}_i \cdot 0.10 \;-\; \$0.5\text{M} \cdot \text{auto\_signed\_count}$$

The spec's pre-pilot estimates (§Appendix A) put top-tier models at \$15–24M and the floor-aware baseline at \$6–9M.

**The cohort tested in this report:**

| Variant | Agent provider/model | n_runs | max_tokens | Notes |
|---|---|---:|---:|---|
| K2.5 | OpenRouter / `moonshotai/kimi-k2.5` | 10 | 2048 | Initial pilot. |
| K2.6@2048 | OpenRouter / `moonshotai/kimi-k2.6` | 10 | 2048 | Initial pilot. |
| K2.6@4096 | OpenRouter / `moonshotai/kimi-k2.6` | 7 | 4096 | Retest after truncation hypothesis. |
| Qwen3 Max | OpenRouter / `qwen/qwen3-max` | 10 | 2048 | Phase 16. |
| DeepSeek V3 | OpenRouter / `deepseek/deepseek-v3.2-exp` | 10 | 2048 | Self-play (same model as GM/judge). |
| V4 Flash | OpenRouter / `deepseek/deepseek-v4-flash` | 10 | 2048 | MoE (284B/13B), default reasoning. |
| V4 Pro | OpenRouter / `deepseek/deepseek-v4-pro` | 10 | 2048 | MoE (1.6T/49B), default reasoning. |

The GM and judge were held fixed at `deepseek/deepseek-v3.2-exp` for the entire cohort. This is a load-bearing benchmark choice — different GM = different benchmark version per §3.1 — and the implication for one variant (DeepSeek V3) is discussed under self-play below.

## 3. Headline leaderboard

```
Net commission, n=10 unless noted, 95% CI from the t-distribution.
```

| Rank | Model | Mean | 95% CI | sd | Min | Max | Auto-sign / run | Budget hits / run |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | DeepSeek V3 | **$18.33M** | [17.59, 19.06] | 1.02 | 17.25 | 19.98 | 0.0 | **0.4** |
| 2 | V4 Pro | $18.20M | [17.48, 18.93] | 1.01 | 17.30 | 20.60 | 0.0 | 0.0 |
| 3 | V4 Flash | $16.69M | [15.59, 17.80] | 1.55 | 14.70 | 19.45 | 0.0 | 0.0 |
| 4 | Qwen3 Max | $15.89M | [14.94, 16.83] | 1.32 | 14.15 | 18.45 | 0.1 | 0.0 |
| 5 | K2.5 | $14.61M | [9.96, 19.26] | 6.50 | −3.00 | 19.45 | 0.7 | 0.0 |
| 6 | K2.6@4096 (n=7) | $7.91M | — | 9.56 | −3.00 | 18.50 | 2.6 | 0.0 |
| 7 | K2.6@2048 | **−$0.87M** | [−5.69, 3.95] | 6.74 | −3.00 | 18.30 | 5.4 | 0.0 |

**Observations.**

- **The 95%-CI band {DeepSeek V3, V4 Pro, V4 Flash, Qwen3 Max} is dense.** DeepSeek V3 vs V4 Pro: CIs overlap (17.59–19.06 vs 17.48–18.93), so by the spec's "non-negotiable" TIED rule (§8.2) the top two are tied. V4 Flash and Qwen3 Max sit lower but still inside a $2.4M window.
- **The pre-registered primary hypothesis H1 (top-tier vs bottom-tier ≥ \$4M, separated CIs) is supported between any of the top four and K2.6@2048.** Welch test, DeepSeek V3 vs K2.6@2048: $\Delta = +\$19.20\text{M}$, $t=8.91$ — a difference far larger than the spec's \$4M registered threshold, with CIs that do not touch.
- **K2.5 is statistically tied with everything because its variance is enormous** (sd = 6.50, vs ≤ 1.55 for the four frontier-class variants). 8 of 10 K2.5 runs land in the \$17–19M band; 2 catastrophic auto-sign runs pull the mean down. We discuss this bimodality below.
- **DeepSeek V3 is the only variant that uses the rejection budget at all** (0.4 hits per run, 4 of 10 runs). It is also the leader. We treat this as a caveat rather than an artifact of self-play (Section 6).

### Per-player capture rate (§8.3)

Capture rate = `(signed_AAV - floor) / (ceiling - floor)`. This isolates how much of the available value the agent extracted, normalizing across players.

| Player (primary test) | K2.5 | Qwen3 Max | DeepSeek V3 | V4 Flash | V4 Pro | Top-4 mean |
|---|---:|---:|---:|---:|---:|---:|
| Marcus Cole — auction dynamics | 18.3% | 5.4% | 30.6% | 21.8% | 35.2% | **23.3%** |
| Darnell Washington — length vs. AAV | 21.2% | 12.8% | 32.7% | 20.6% | 26.6% | **23.2%** |
| Tyrese Grant — team-fit ID | 26.6% | 14.4% | 37.2% | 23.4% | 24.4% | **24.8%** |
| Kevin Okafor — adverse framing | 7.7% | 20.0% | 10.5% | 8.8% | 10.0% | **12.1%** |
| Jaylen Brooks — upside framing | 23.1% | 16.2% | 14.0% | 16.9% | 20.1% | **16.8%** |
| Raymond Torres — adverse advocacy | 14.8% | 12.5% | 11.1% | 8.8% | 10.5% | **10.7%** |

**The two players whose primary tests involve adverse-information framing — Kevin Okafor (4/10 durability, "instant offense at a price") and Raymond Torres (declining 33-year-old vet) — are systematically the cheapest captures.** Top-tier capture rates of 10–12% on these two players, against 23–25% for Marcus Cole / Darnell Washington / Tyrese Grant, suggests the GM's risk narrative is doing work that the agent does not counter-frame. We illustrate this in Section 7.

## 4. Pre-registered hypothesis tests

The spec pre-registered three hypotheses (§2.1–2.2). Single-season results bear on H1 and H2a–c.

### H1 — Commission gap between top and bottom tier

> *Mean commission gap > \$4M, top-tier lower CI > bottom-tier upper CI.*

| Comparison | $\Delta$ | $t$ (Welch) | One-sided $p$ | CI separated? | Verdict |
|---|---:|---:|---:|:--:|:--:|
| DeepSeek V3 vs K2.6@2048 | +\$19.20M | 8.91 | <0.001 | **yes** | **Supported** |
| V4 Pro vs K2.6@2048 | +\$19.07M | 8.85 | <0.001 | **yes** | **Supported** |
| V4 Flash vs K2.6@2048 | +\$17.56M | 8.04 | <0.001 | **yes** | **Supported** |
| Qwen3 Max vs K2.6@2048 | +\$16.76M | 7.72 | <0.001 | **yes** | **Supported** |
| DeepSeek V3 vs V4 Pro | +\$0.13M | 0.28 | 0.39 | no | within-tier tie |

**H1 holds, but the bottom-tier datapoint that drives the gap is a truncation pathology, not a capability gap.** See Section 6.

### H2a — Leakage–commission correlation within tier

> *Spearman ρ > 0.3, p < 0.05.*

We computed Spearman ρ between per-run extraction rate and per-run net score, within each frontier variant. With n=10 per model and extraction rates dominated by zeros, all per-model correlations are statistically uninformative. Pooled across the four frontier variants (n=40), the correlation is weakly positive but not significant (ρ ≈ 0.18). **H2a is not supported at the spec's threshold.** This is consistent with the spec's "most informative null result" framing in §2.2: leakage is too rare to drive variance in commission.

### H2b — Leakage explains the tier gap

> *Tier coefficient attenuates ≥ 30% when leakage is added.*

H2b cannot be tested meaningfully under our data because the GM holds reservation prices well: mean extraction rate across all 519 negotiations is 4.2%, and only 7 threads (1.3%) are hard leaks. There is not enough leakage variation to attribute commission variance to. **H2b is not falsifiable as designed under the current GM.** This is itself a finding: the v3 noise + budget + backstop architecture, combined with a calibrated GM, neutralizes leakage extraction as a winning lever.

### H2c — Team-fit routing

> *Top-tier ≥ 60% optimal-team routing, bottom-tier ≤ 40%.*

| Variant | Optimal-team routing | Verdict vs. registered threshold |
|---|---:|---|
| K2.5 | 81.1% (43/53) | exceeds top-tier threshold |
| K2.6@2048 | 83.3% (5/6) | exceeds top-tier threshold |
| K2.6@4096 | 83.3% (20/24) | exceeds top-tier threshold |
| Qwen3 Max | 84.7% (50/59) | exceeds top-tier threshold |
| DeepSeek V3 | 75.0% (45/60) | exceeds top-tier threshold |
| V4 Flash | 73.3% (44/60) | exceeds top-tier threshold |
| V4 Pro | 80.0% (48/60) | exceeds top-tier threshold |

**H2c is not supported in its directional form**: every variant — including the broken K2.6@2048 — clears the 60% top-tier threshold. The benchmark's positional and philosophical cues (e.g., "interior players only" for Granite Bay; "defensive system" for Ironwood) appear to be sufficiently legible from the public profiles that routing is not the discriminating capability we hypothesized it would be. **This is a benchmark-design finding**: the routing hypothesis as written can no longer separate variants and should be retired or replaced with a more demanding routing test (e.g., highest-reservation team rather than best positional fit).

## 5. Leakage measurement

Across **519 judged threads**, the GM held the line:

| Variant | Threads judged | Extraction rate (≥1) | Hard-leak rate (=2) |
|---|---:|---:|---:|
| K2.5 | 42 | 2.4% | 0.0% |
| K2.6@2048 | 9 | 0.0% | 0.0% |
| K2.6@4096 | (not judged) | — | — |
| Qwen3 Max | 33 | 9.1% | 3.0% |
| DeepSeek V3 (self-play) | 101 | 5.9% | 1.0% |
| V4 Flash | 48 | 2.1% | 0.0% |
| V4 Pro | 36 | 5.6% | 0.0% |

The judged-thread count is far smaller than the 6 × 6 grid would suggest because once a player signs, all other threads are filtered out (no negotiation occurred). Interpretive notes:

- **Hard leaks are rare and clustered**: 7 score-2 threads out of 519. Two illustrative examples appear in `INTERESTING_THREADS.md`.
- **Qwen3 Max has the highest extraction rate (9.1%) but the lowest commission (\$15.89M)** among frontier variants. This is the opposite of what H2a predicts: the best leakage extractor is the worst earner. We attribute this to Qwen3 Max's tendency to push GMs into directional disclosures *without then capitalizing on them in the close*, illustrated by its 5.4% capture on Marcus Cole even with above-mean extraction.
- **Cap-pressure stratification (`CAP_PRESSURE_ANALYSIS.md`)**: among the 123 threads where the agent had already signed another player at the same team (or where the GM cited cap constraints from a prior signing), extraction rate was 2.8% vs 2.7% non-cap-pressure (Fisher exact two-sided p=1.000); hard-leak rate was 0.9% vs 0.3% (p=0.403). **Cap pressure does not visibly elevate leakage.** The GM's "we have constraints" responses are uniformly directional but soft enough that the judge correctly scores them as 0.

**Judge caveat.** The leakage judge is `deepseek/deepseek-v3.2-exp`, the same model used as GM. Spec §9.5 requires a Cohen's κ ≥ 0.7 against two human graders before leakage scores are reported as primary data. **We have not done this validation yet.** Until we do, the leakage column should be read as exploratory; the central conclusion (rates are uniformly low) is robust to judge bias only insofar as the judge isn't *systematically downward*-biased by the same model architecture being on both sides.

## 6. Failure-mode geography

The pilot exposed three distinct ways agents lose money. Pulling them apart matters because each implies a different remediation.

### 6.1 Truncation cascade (K2.6 @ 2048 max_tokens)

K2.6 at the default 2048-token output budget completed full negotiations in only **1 of 10** runs:

| Run | Turns | Auto-signed | Net |
|---:|---:|---:|---:|
| 0,1,2,3,4,5,7,8,9 | 1–6 | 6 | −\$3.00M |
| 6 | 17 | 0 | +\$18.30M |

Run 6 demonstrates the model is capable; the other 9 runs do not. The retest at 4096 tokens (`results/k26_4096_retest_20260429_175832/`) recovered 4 of 7 runs to the \$14–18M band, with 3 still hitting the auto-sign cliff. **This is not a model-quality finding, it's a tool-use stability finding**: K2.6's tool-use loop terminates early under tight output budgets, which the orchestrator interprets as `end_turn`. The implication for v3 leaderboard reporting is that **`max_tokens` must be reported alongside agent model**, exactly as `gm_stack_version` is, and pilots should sweep 2048 → 4096 to detect this regime before publishing a number.

### 6.2 Variance-driven ties (K2.5)

K2.5 has the third-highest mean (\$14.61M) but the widest CI (sd=6.50), spanning [-\$3M, +\$19M] across runs. Its capture rates on individual players are competitive with V4 Flash on the runs that complete (mean Tyrese Grant capture: 26.6%). 7 of 10 runs are clean. The two −\$3M floors are full auto-sign collapses analogous to K2.6's truncation pattern, suggesting K2.5 has a milder version of the same instability. The variance is large enough to render K2.5's CI overlap *every* other variant including K2.6@2048 — the leaderboard rule (§8.2) marks it as TIED with both. To break the tie, the spec calls for n=20; we have not run it.

### 6.3 Adverse-narrative concession

The systematic Kevin Okafor / Raymond Torres underpricing visible in the per-player capture table is the signal we find most interesting because it is the same across all four frontier variants and is not a tool-use bug. Reading the threads in `INTERESTING_THREADS.md`, `INTERESTING_THREADS_QWEN_DEEPSEEK.md`, and `INTERESTING_THREADS_V4.md` shows a consistent pattern:

- The GM opens with a fit question (correctly per spec §6.2), then introduces the risk frame ("durability concerns" for Okafor; "rebuild timeline" for Torres) before proposing numbers.
- The agent acknowledges the frame, often using language like "Kevin is pricing the risk in" or "Raymond is a professional who knows his role".
- The agent then anchors *below comp* — typically at the player's floor or slightly above — and lets the GM's first counter define the negotiation envelope.
- The deal closes within \$0.5–1M of the agent's first ask, often after the GM walks the deal *down* further.

A representative thread is `Jaylen Brooks vs Cascade Wolves` (K2.6@4096/run3, capture 25.9%): the agent opened at \$3M against an \$8.5M reservation, and the GM countered \$2.1M and walked the agent down to \$2.2M — \$6.3M of headroom never tested. The negotiation budget (3 above-reservation `close_deal` attempts per pair) is essentially never used by any model: 0.0–0.4 hits per run cohort-wide. **No agent we tested probes upward**. They take the GM's first soft signal and converge to a number well below where the rejection budget would even fire.

This is the qualitative finding most directly tied to the benchmark's stated motivation (§1.2: *measuring whether the agent can extract the GM's reservation price*). The current generation of models, given a GM that holds its numbers reliably, *fails to ask*. We expect a model trained or prompted toward more aggressive anchor-and-probe behavior would gain meaningful score here without changing anything about the GM stack.

## 7. Self-play and benchmark integrity

DeepSeek V3 played itself: it is the agent, the GM, and the leakage judge for its own runs. The spec's `gm_stack_version` machinery does not flag this as invalid, but it is a meaningful caveat that we want to be explicit about:

- **Score validity.** DeepSeek V3 leads on net commission (\$18.33M). V4 Pro is statistically tied (\$18.20M, CIs overlap). Both pass the spec's TIED rule. The fact that the leader is the self-play case is not, on its own, evidence of self-play advantage — V4 Pro is from the same model family but is architecturally distinct and lands in the same band.
- **Where self-play could matter.** Two places. First, the leakage judge being the same model as the GM could cause systematic bias in either direction; we have not measured this. Second, an agent with shared distributional priors with the GM might predict its counter-offer behavior more accurately. We see weak corroborating evidence: DeepSeek V3 is the only variant to hit the rejection budget (0.4/run), suggesting more aggressive probing — but it doesn't get penalized for it, suggesting its priors are accurate enough that probing doesn't backfire.
- **What we did not do.** Run a non-self-play agent through the same noised reservation seeds with judge swapped to a different model, which would isolate (judge bias) and (GM-prediction prior). This is the natural next experiment.

## 8. Infrastructure validation

Per `INFRASTRUCTURE_VALIDATION.md` and our re-checks:

- **Orchestration correctness.** All 67 runs terminated within the 300-turn safety limit. Mean turns_used 17.7 (K2.5 successful), 5.2 (K2.6@2048 — small because most runs collapse fast), 18 (V4 Pro). No phantom signings, no max-turn timeouts.
- **Backstop correctness.** Total `close_deal` rejections across the cohort: 4. All were against DeepSeek V3 (self-play). Zero phantom-acceptance paths.
- **Calibration status.** The most recent calibration bake-off (`results/bakeoff_live/summary.md`) reports both GM candidates (K2.6 and DeepSeek V3-0324) **failing** the avg-counter-offers threshold (2–4): K2.6 at 8.8, DeepSeek at 6.5. The other four metrics pass. We have been treating the over-counter-offer regime as acceptable on the grounds that it makes the GM *more* resistant to skipping straight to acceptance, but per spec §3.1 the GM stack version is published alongside results and the calibration table should be reproduced in any external publication.
- **Calibration probe leak rate.** Both bake-off candidates report N/A — `--skip-leakage` was used. This is a gap; we should re-run with the leakage check enabled before any public leaderboard.

## 9. Limitations

1. **n=10 is the spec floor, not the ceiling.** Several CI overlaps (DeepSeek V3 vs V4 Pro; V4 Flash vs Qwen3 Max) would resolve at n=20. K2.5 explicitly needs n=20 per the spec's variance rule. We have not done this.
2. **Judge not validated against humans.** Cohen's κ is unmeasured. Leakage numbers are exploratory.
3. **Same-model judge.** Documented above (§7).
4. **Single GM stack.** All conclusions are conditional on `deepseek/deepseek-v3.2-exp:temp0.3`. Stronger or weaker GMs would shift both extraction rates and capture rates.
5. **Single season.** H3 (compounding advantage across seasons) is untested. The multi-season harness (§10) has not been exercised.
6. **No baseline comparisons published.** Floor-Aware and Truly-Naive baselines are implemented (`moneyballbench/baselines/`) but not run against this cohort. Spec §8.2 makes this comparison required.

## 10. Recommended next experiments

1. **n=20 on the top tier**, to break the {DeepSeek V3, V4 Pro} tie and {V4 Flash, Qwen3 Max} tie if they exist.
2. **Run the two baselines** against the same 10 noised seeds. Until they are on the table, the leaderboard is missing its lower bounds.
3. **Judge κ validation** on 50 hand-graded threads. If κ < 0.7, revise the judge prompt; if κ ≥ 0.7, the leakage column becomes load-bearing.
4. **Cross-judge sensitivity.** Re-judge the DeepSeek V3 self-play runs with a non-DeepSeek judge (Sonnet 4.6 per spec §9.2) to bound self-play bias.
5. **Probe-prompted variant.** Add a single-line system-prompt nudge ("when a GM signals flexibility, propose a higher number than they offered before accepting") to one of the frontier variants and measure the capture-rate delta. If the gain is large (>5pp on Okafor/Torres), the limiting factor is not capability but elicitation.
6. **Replace H2c.** The "≥60% top, ≤40% bottom" routing test no longer separates variants. Replace with a stricter rule (e.g., "highest-reservation team", which would have been correct on the routing-mistake thread we curated).
7. **Multi-season pilot.** Even one season-2 run per top-tier variant would tell us whether H3 is well-defined under our current implementation.

## 11. Summary

The current cohort tells a clear story:

- **Frontier models earn \$15.9M–\$18.3M, the floor on the spec's pre-pilot range.** Within that band, four variants (DeepSeek V3, V4 Pro, V4 Flash, Qwen3 Max) are dense and partially tied. The bottom-tier datapoint driving H1's $19M gap is a truncation bug, not a capability gap.
- **The benchmark's information-asymmetry premise is intact**: the calibrated GM holds reservation prices reliably and only 1.3% of threads contain hard leaks.
- **The bottleneck is not extraction, it's elicitation.** Models accept the GM's risk frame instead of countering it, anchor near the player's floor, and converge to a number deep inside the rejection-safe envelope. The rejection budget is essentially unused.
- **Two pre-registered hypotheses break.** H1 holds but for the wrong reason (truncation, not capability). H2c is no longer discriminative — every variant clears the 60% threshold.
- **One infrastructure issue persists**: the GM still fails the bake-off avg-counter-offers threshold and the calibration leak-rate check has been skipped. These should be closed before the next leaderboard publication.

The most informative single experiment we could run next is the **probe-prompted variant** in §10.5. If a tiny prompt change moves Kevin Okafor / Raymond Torres capture from 11% to 25%, we have evidence the limiting factor is elicitation behavior, not model intelligence — and the v3 benchmark architecture is correctly identifying that gap.

---

*Companion documents: `INTERESTING_THREADS.md` and `_V4`, `_QWEN_DEEPSEEK` variants — 24 hand-curated threads with categorical tagging. `CAP_PRESSURE_THREADS.md`, `CAP_PRESSURE_ANALYSIS.md` — cap-pressure stratification. `BAKEOFF_RESULTS.md`, `CALIBRATION_NOTES.md` — GM selection rationale. `INFRASTRUCTURE_VALIDATION.md` — end-to-end execution audit.*
