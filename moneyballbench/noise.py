"""
MoneyBall Bench v3.0 — Reservation price noise.

Implements apply_reservation_noise() exactly as specified in §7.2.
Seed structure: hash(gm_stack_version + run_id) ensures all models
in a leaderboard cohort face identical fuzz values for a given run_id.
"""

from __future__ import annotations

import hashlib
import random


def apply_reservation_noise(
    base_prices: dict[str, dict[str, dict]],
    gm_stack_version: str,
    run_id: int,
) -> dict[str, dict[str, dict]]:
    """
    Apply per-run multiplicative noise to reservation prices.

    Each non-zero reservation AAV is multiplied by a noise factor drawn
    from Uniform(0.95, 1.05), then rounded to nearest $0.5M.

    Same seed structure ensures all models in a leaderboard cohort face
    identical fuzz values for a given run_id.
    """
    seed_str = f"{gm_stack_version}:{run_id}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    noised: dict[str, dict[str, dict]] = {}
    for team, players in base_prices.items():
        noised[team] = {}
        for player, limits in players.items():
            if limits["max_aav"] == 0:
                noised[team][player] = limits.copy()
            else:
                noise = rng.uniform(0.95, 1.05)
                raw = limits["max_aav"] * noise
                noised_aav = round(raw * 2) / 2
                noised[team][player] = {
                    "max_aav": noised_aav,
                    "max_years": limits["max_years"],
                }
    return noised
