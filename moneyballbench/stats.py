"""
MoneyBall Bench v3.0 — Statistical utilities.

Bootstrap confidence intervals, standard deviation, and power analysis
as required by §8.2.
"""

from __future__ import annotations

import math
import random

import numpy as np
from scipy import stats as scipy_stats


def bootstrap_ci(
    scores: list[float],
    n_bootstrap: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for the mean."""
    rng = np.random.RandomState(seed)
    arr = np.array(scores)
    n = len(arr)
    boot_means = np.array([
        rng.choice(arr, size=n, replace=True).mean()
        for _ in range(n_bootstrap)
    ])
    alpha = (1 - ci) / 2
    lo = float(np.percentile(boot_means, alpha * 100))
    hi = float(np.percentile(boot_means, (1 - alpha) * 100))
    return (lo, hi)


def std_dev(scores: list[float]) -> float:
    """Sample standard deviation."""
    if len(scores) < 2:
        return 0.0
    return float(np.std(scores, ddof=1))


def power_analysis_min_n(
    within_model_std: float,
    effect_size: float = 2.0,
    power: float = 0.80,
    alpha: float = 0.05,
) -> int:
    """
    Derive minimum n to detect a given mean difference with specified power
    using a one-sided two-sample t-test.

    Args:
        within_model_std: estimated within-model standard deviation
        effect_size: target mean difference to detect (default $2M)
        power: desired statistical power (default 0.80)
        alpha: significance level (default 0.05)

    Returns:
        Minimum n per group.
    """
    if within_model_std <= 0:
        return 10
    z_alpha = scipy_stats.norm.ppf(1 - alpha)
    z_beta = scipy_stats.norm.ppf(power)
    n = math.ceil(2 * ((z_alpha + z_beta) * within_model_std / effect_size) ** 2)
    return max(n, 10)
