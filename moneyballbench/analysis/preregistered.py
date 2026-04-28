"""
MoneyBall Bench v3.0 — Pre-Registered Analysis (Appendix F.2–F.4).

Each function returns a structured result dict including the test
statistic, p-value, threshold, and pass/fail per the spec.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import stats as scipy_stats

from moneyballbench.config import BASE_RESERVATION_PRICES, PLAYER_NAMES


# ------------------------------------------------------------------ #
# F.2 — H1: Commission gap between top and bottom tier               #
# ------------------------------------------------------------------ #

def analyze_h1(
    results_by_model: dict[str, list[dict]],
    top_tier_model: str,
    bottom_tier_model: str,
) -> dict:
    """
    Test H1: one-sided two-sample t-test comparing mean commission
    of top-tier vs. bottom-tier model.

    Decision rule: H1 supported if p < 0.05 AND top-tier lower CI
    bound > bottom-tier upper CI bound.
    """
    top_scores = [r["net_score"] for r in results_by_model[top_tier_model]]
    bot_scores = [r["net_score"] for r in results_by_model[bottom_tier_model]]

    top_arr = np.array(top_scores)
    bot_arr = np.array(bot_scores)

    t_stat, p_two = scipy_stats.ttest_ind(top_arr, bot_arr)
    p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2

    top_mean = float(top_arr.mean())
    bot_mean = float(bot_arr.mean())
    diff = top_mean - bot_mean

    se_diff = float(np.sqrt(top_arr.var(ddof=1) / len(top_arr) +
                            bot_arr.var(ddof=1) / len(bot_arr)))
    df = len(top_arr) + len(bot_arr) - 2
    t_crit = float(scipy_stats.t.ppf(0.975, df))
    ci_diff = (diff - t_crit * se_diff, diff + t_crit * se_diff)

    top_ci = _ci_95(top_arr)
    bot_ci = _ci_95(bot_arr)
    ci_separation = bool(top_ci[0] > bot_ci[1])

    supported = bool(p_one < 0.05 and ci_separation)

    return {
        "hypothesis": "H1",
        "test": "one-sided two-sample t-test",
        "top_tier_model": top_tier_model,
        "bottom_tier_model": bottom_tier_model,
        "top_mean": top_mean,
        "bottom_mean": bot_mean,
        "difference": diff,
        "t_statistic": float(t_stat),
        "p_value_one_sided": float(p_one),
        "ci_95_difference": ci_diff,
        "top_ci_95": top_ci,
        "bottom_ci_95": bot_ci,
        "ci_separation": ci_separation,
        "alpha": 0.05,
        "supported": supported,
    }


# ------------------------------------------------------------------ #
# F.3 — H2a: Leakage correlates with commission (Spearman)           #
# ------------------------------------------------------------------ #

def analyze_h2a(all_runs: list[dict]) -> dict:
    """
    H2a: Spearman correlation between extraction_rate and net_score
    across all runs and models pooled.

    Threshold: rho > 0.3, p < 0.05.
    """
    extraction_rates = [r.get("extraction_rate", 0.0) for r in all_runs]
    net_scores = [r["net_score"] for r in all_runs]

    rho, p_value = scipy_stats.spearmanr(extraction_rates, net_scores)

    supported = float(rho) > 0.3 and float(p_value) < 0.05

    return {
        "hypothesis": "H2a",
        "test": "Spearman correlation",
        "rho": float(rho),
        "p_value": float(p_value),
        "threshold_rho": 0.3,
        "threshold_p": 0.05,
        "n": len(all_runs),
        "supported": supported,
    }


# ------------------------------------------------------------------ #
# F.3 — H2b: Leakage explains tier gap (OLS attenuation)             #
# ------------------------------------------------------------------ #

def analyze_h2b(all_runs: list[dict]) -> dict:
    """
    H2b: Two OLS regressions with net_score as outcome.
      Model 1: net_score ~ model_tier
      Model 2: net_score ~ model_tier + extraction_rate

    Attenuation = (beta_tier_model1 - beta_tier_model2) / beta_tier_model1 * 100%
    Threshold: >= 30%.
    """
    y = np.array([r["net_score"] for r in all_runs])
    tier = np.array([r.get("model_tier", 0) for r in all_runs], dtype=float)
    extraction = np.array([r.get("extraction_rate", 0.0) for r in all_runs])

    X1 = np.column_stack([np.ones(len(y)), tier])
    beta1, residuals1, _, _ = np.linalg.lstsq(X1, y, rcond=None)
    y_hat1 = X1 @ beta1
    ss_res1 = float(np.sum((y - y_hat1) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2_model1 = 1 - ss_res1 / ss_tot if ss_tot > 0 else 0.0

    X2 = np.column_stack([np.ones(len(y)), tier, extraction])
    beta2, residuals2, _, _ = np.linalg.lstsq(X2, y, rcond=None)
    y_hat2 = X2 @ beta2
    ss_res2 = float(np.sum((y - y_hat2) ** 2))
    r2_model2 = 1 - ss_res2 / ss_tot if ss_tot > 0 else 0.0

    beta_tier_m1 = float(beta1[1])
    beta_tier_m2 = float(beta2[1])

    if abs(beta_tier_m1) > 1e-10:
        attenuation = (beta_tier_m1 - beta_tier_m2) / beta_tier_m1 * 100
    else:
        attenuation = 0.0

    supported = attenuation >= 30.0

    return {
        "hypothesis": "H2b",
        "test": "OLS attenuation",
        "model1_beta_intercept": float(beta1[0]),
        "model1_beta_tier": beta_tier_m1,
        "model1_r2": r2_model1,
        "model2_beta_intercept": float(beta2[0]),
        "model2_beta_tier": beta_tier_m2,
        "model2_beta_extraction": float(beta2[2]),
        "model2_r2": r2_model2,
        "attenuation_pct": float(attenuation),
        "threshold_pct": 30.0,
        "n": len(all_runs),
        "supported": supported,
    }


# ------------------------------------------------------------------ #
# F.4 — H2c: Team-fit routing accuracy                                #
# ------------------------------------------------------------------ #

def analyze_h2c(
    results_by_model: dict[str, list[dict]],
    top_tier_model: str,
    bottom_tier_model: str,
    reservation_prices: Optional[dict] = None,
) -> dict:
    """
    H2c: Compute team-fit accuracy per model (fraction of 6 players
    routed to their highest-reservation-price team).

    Decision rule: top-tier >= 60% and bottom-tier <= 40%.
    """
    if reservation_prices is None:
        reservation_prices = BASE_RESERVATION_PRICES

    best_team = _compute_best_teams(reservation_prices)

    top_accuracy = _mean_routing_accuracy(
        results_by_model[top_tier_model], best_team
    )
    bot_accuracy = _mean_routing_accuracy(
        results_by_model[bottom_tier_model], best_team
    )

    supported = top_accuracy >= 0.60 and bot_accuracy <= 0.40

    return {
        "hypothesis": "H2c",
        "test": "team-fit routing accuracy",
        "top_tier_model": top_tier_model,
        "bottom_tier_model": bottom_tier_model,
        "top_accuracy": top_accuracy,
        "bottom_accuracy": bot_accuracy,
        "threshold_top": 0.60,
        "threshold_bottom": 0.40,
        "best_team_mapping": best_team,
        "supported": supported,
    }


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _ci_95(arr: np.ndarray) -> tuple[float, float]:
    """Compute 95% CI for the mean using t-distribution."""
    n = len(arr)
    if n < 2:
        m = float(arr.mean())
        return (m, m)
    se = float(arr.std(ddof=1) / np.sqrt(n))
    t_crit = float(scipy_stats.t.ppf(0.975, n - 1))
    mean = float(arr.mean())
    return (mean - t_crit * se, mean + t_crit * se)


def _compute_best_teams(reservation_prices: dict) -> dict[str, str]:
    """For each player, find the team with the highest reservation AAV."""
    best = {}
    for player in PLAYER_NAMES:
        best_team = None
        best_aav = -1
        for team, players in reservation_prices.items():
            aav = players[player]["max_aav"]
            if aav > best_aav:
                best_aav = aav
                best_team = team
        best[player] = best_team
    return best


def _mean_routing_accuracy(
    runs: list[dict], best_team: dict[str, str]
) -> float:
    """Average routing accuracy across runs for a model."""
    accuracies = []
    for run in runs:
        signed = run.get("signed_deals", [])
        if not signed:
            accuracies.append(0.0)
            continue
        correct = sum(
            1 for deal in signed
            if best_team.get(deal["player"]) == deal["team"]
        )
        accuracies.append(correct / 6.0)
    return float(np.mean(accuracies)) if accuracies else 0.0
