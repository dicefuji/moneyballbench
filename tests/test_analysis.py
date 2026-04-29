"""Phase 6 tests: pre-registered analysis functions with synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from moneyballbench.analysis.preregistered import (
    analyze_h1,
    analyze_h2a,
    analyze_h2b,
    analyze_h2c,
    _ci_95,
    _compute_best_teams,
)
from moneyballbench.config import BASE_RESERVATION_PRICES


class TestAnalyzeH1:
    def test_clear_separation(self):
        rng = np.random.RandomState(42)
        results = {
            "model_top": [{"net_score": s} for s in rng.normal(20, 1, 30)],
            "model_bot": [{"net_score": s} for s in rng.normal(8, 1, 30)],
        }
        result = analyze_h1(results, "model_top", "model_bot")
        assert result["hypothesis"] == "H1"
        assert result["supported"] is True
        assert result["p_value_one_sided"] < 0.05
        assert result["ci_separation"] is True
        assert result["top_mean"] > result["bottom_mean"]

    def test_no_separation(self):
        results = {
            "model_a": [{"net_score": 10.0 + i * 0.1} for i in range(20)],
            "model_b": [{"net_score": 10.0 + i * 0.1} for i in range(20)],
        }
        result = analyze_h1(results, "model_a", "model_b")
        assert result["supported"] is False

    def test_result_structure(self):
        results = {
            "top": [{"net_score": 20.0}, {"net_score": 22.0}],
            "bot": [{"net_score": 8.0}, {"net_score": 10.0}],
        }
        result = analyze_h1(results, "top", "bot")
        assert "t_statistic" in result
        assert "p_value_one_sided" in result
        assert "ci_95_difference" in result
        assert "top_ci_95" in result
        assert "bottom_ci_95" in result
        assert "alpha" in result
        assert result["alpha"] == 0.05


class TestAnalyzeH2a:
    def test_strong_positive_correlation(self):
        runs = [
            {"net_score": i * 2.0, "extraction_rate": i * 0.1}
            for i in range(1, 31)
        ]
        result = analyze_h2a(runs)
        assert result["hypothesis"] == "H2a"
        assert result["rho"] > 0.3
        assert result["p_value"] < 0.05
        assert result["supported"] is True

    def test_no_correlation(self):
        rng = np.random.RandomState(42)
        runs = [
            {"net_score": rng.normal(10, 5), "extraction_rate": rng.uniform(0, 1)}
            for _ in range(50)
        ]
        result = analyze_h2a(runs)
        assert result["threshold_rho"] == 0.3
        assert result["threshold_p"] == 0.05

    def test_result_structure(self):
        runs = [
            {"net_score": 10.0, "extraction_rate": 0.5},
            {"net_score": 12.0, "extraction_rate": 0.6},
            {"net_score": 8.0, "extraction_rate": 0.4},
        ]
        result = analyze_h2a(runs)
        assert "rho" in result
        assert "p_value" in result
        assert "n" in result
        assert result["n"] == 3


class TestAnalyzeH2b:
    def test_strong_attenuation(self):
        runs = []
        rng = np.random.RandomState(42)
        for _ in range(30):
            tier = 1
            extraction = rng.uniform(0.6, 0.9)
            score = 5.0 * tier + 10.0 * extraction + rng.normal(0, 0.5)
            runs.append({"net_score": score, "model_tier": tier, "extraction_rate": extraction})
        for _ in range(30):
            tier = 0
            extraction = rng.uniform(0.1, 0.3)
            score = 5.0 * tier + 10.0 * extraction + rng.normal(0, 0.5)
            runs.append({"net_score": score, "model_tier": tier, "extraction_rate": extraction})

        result = analyze_h2b(runs)
        assert result["hypothesis"] == "H2b"
        assert result["attenuation_pct"] > 0
        assert result["model2_r2"] >= result["model1_r2"]

    def test_result_structure(self):
        runs = [
            {"net_score": 10, "model_tier": 1, "extraction_rate": 0.5},
            {"net_score": 5, "model_tier": 0, "extraction_rate": 0.2},
            {"net_score": 8, "model_tier": 1, "extraction_rate": 0.4},
            {"net_score": 3, "model_tier": 0, "extraction_rate": 0.1},
        ]
        result = analyze_h2b(runs)
        assert "model1_beta_tier" in result
        assert "model2_beta_tier" in result
        assert "model2_beta_extraction" in result
        assert "attenuation_pct" in result
        assert "threshold_pct" in result
        assert result["threshold_pct"] == 30.0


class TestAnalyzeH2c:
    def test_perfect_routing_vs_no_routing(self):
        best_teams = _compute_best_teams(BASE_RESERVATION_PRICES)
        top_runs = [
            {
                "signed_deals": [
                    {"player": p, "team": best_teams[p]} for p in best_teams
                ]
            }
            for _ in range(5)
        ]
        bot_runs = [
            {
                "signed_deals": [
                    {"player": p, "team": "Granite Bay Bulls"} for p in best_teams
                ]
            }
            for _ in range(5)
        ]
        results = {"top": top_runs, "bot": bot_runs}
        result = analyze_h2c(results, "top", "bot")
        assert result["hypothesis"] == "H2c"
        assert result["top_accuracy"] >= 0.60
        assert result["bottom_accuracy"] <= 0.40
        assert result["supported"] is True

    def test_result_structure(self):
        results = {
            "m1": [{"signed_deals": []}],
            "m2": [{"signed_deals": []}],
        }
        result = analyze_h2c(results, "m1", "m2")
        assert "top_accuracy" in result
        assert "bottom_accuracy" in result
        assert "threshold_top" in result
        assert "threshold_bottom" in result
        assert "best_team_mapping" in result


class TestHelpers:
    def test_ci_95_single_value(self):
        arr = np.array([5.0])
        lo, hi = _ci_95(arr)
        assert lo == hi == 5.0

    def test_ci_95_symmetric(self):
        arr = np.array([8.0, 10.0, 12.0])
        lo, hi = _ci_95(arr)
        assert lo < 10.0 < hi

    def test_compute_best_teams(self):
        best = _compute_best_teams(BASE_RESERVATION_PRICES)
        assert len(best) == 6
        for player in best:
            assert best[player] is not None
        assert best["Marcus Cole"] == "Apex City Aces"
