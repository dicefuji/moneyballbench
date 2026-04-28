"""Phase 2 tests: noise function correctness."""

import pytest

from moneyballbench.config import BASE_RESERVATION_PRICES
from moneyballbench.noise import apply_reservation_noise


class TestNoiseReproducibility:
    def test_same_seed_same_output(self):
        r1 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v1.0", 42)
        r2 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v1.0", 42)
        for team in r1:
            for player in r1[team]:
                assert r1[team][player]["max_aav"] == r2[team][player]["max_aav"]
                assert r1[team][player]["max_years"] == r2[team][player]["max_years"]

    def test_different_seeds_different_output(self):
        r1 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v1.0", 0)
        r2 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v1.0", 1)
        diffs = 0
        for team in r1:
            for player in r1[team]:
                if r1[team][player]["max_aav"] != r2[team][player]["max_aav"]:
                    diffs += 1
        assert diffs > 0, "Different seeds should produce different outputs"

    def test_different_versions_different_output(self):
        r1 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v1.0", 0)
        r2 = apply_reservation_noise(BASE_RESERVATION_PRICES, "v2.0", 0)
        diffs = 0
        for team in r1:
            for player in r1[team]:
                if r1[team][player]["max_aav"] != r2[team][player]["max_aav"]:
                    diffs += 1
        assert diffs > 0


class TestNoiseRange:
    def test_noise_within_bounds(self):
        for run_id in range(50):
            noised = apply_reservation_noise(BASE_RESERVATION_PRICES, "test", run_id)
            for team, players in noised.items():
                for player, limits in players.items():
                    base = BASE_RESERVATION_PRICES[team][player]["max_aav"]
                    if base == 0:
                        assert limits["max_aav"] == 0
                        continue
                    low = base * 0.95
                    high = base * 1.05
                    rounded_low = round(low * 2) / 2
                    rounded_high = round(high * 2) / 2
                    assert limits["max_aav"] >= rounded_low - 0.01, (
                        f"{team}/{player}: {limits['max_aav']} < {rounded_low}"
                    )
                    assert limits["max_aav"] <= rounded_high + 0.01, (
                        f"{team}/{player}: {limits['max_aav']} > {rounded_high}"
                    )


class TestNoiseRounding:
    def test_rounded_to_half_million(self):
        noised = apply_reservation_noise(BASE_RESERVATION_PRICES, "test", 0)
        for team, players in noised.items():
            for player, limits in players.items():
                aav = limits["max_aav"]
                assert aav * 2 == round(aav * 2), (
                    f"{team}/{player}: {aav} not rounded to $0.5M"
                )


class TestNoiseZeroPreserved:
    def test_zero_entries_unchanged(self):
        noised = apply_reservation_noise(BASE_RESERVATION_PRICES, "test", 0)
        gb = noised["Granite Bay Bulls"]
        assert gb["Marcus Cole"]["max_aav"] == 0.0
        assert gb["Marcus Cole"]["max_years"] == 0
        assert gb["Darnell Washington"]["max_aav"] == 0.0
        assert gb["Tyrese Grant"]["max_aav"] == 0.0
        assert gb["Jaylen Brooks"]["max_aav"] == 0.0


class TestNoiseMaxYearsPreserved:
    def test_max_years_not_noised(self):
        noised = apply_reservation_noise(BASE_RESERVATION_PRICES, "test", 0)
        for team in noised:
            for player in noised[team]:
                assert noised[team][player]["max_years"] == \
                    BASE_RESERVATION_PRICES[team][player]["max_years"]
