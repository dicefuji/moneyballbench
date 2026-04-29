# Calibration Notes — MoneyBall Bench v3.0

## GM Model
`claude-sonnet-4-20250514` via Anthropic API

---

## Phase 10: Sonnet 4 Calibration Remediation

### Iteration 0 (baseline, pre-Phase 10)

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| Acceptance rate | 10% | 60–75% | FAIL |
| Avg counter-offers | 1.7 | 2–4 | FAIL |
| Avg clarifying questions | 0.2 | >=1 per negotiation | FAIL |
| GB wrong-pos refusal | 100% | 100% | PASS |

**Diagnosis**: Multiple probe-side bugs identified:
1. Rounds 3-4 dropped negotiations when GM asked clarifying questions instead of counter-offering (no reply sent, thread died)
2. `close_deal` always used `years=3`, but many team-player pairs have max_years=1 or 2 (Kevin Okafor: no team allows 3yr, Raymond Torres: no team allows 3yr)
3. `_compute_metrics` counted per-negotiation instead of per-player: with 36 negotiations and max 6 signings, theoretical ceiling was 6/32=18.75%, making 60-75% target mathematically impossible

### Iteration 1 (probe bug fixes)

**Fixes applied**:
- Added `_try_close_deal()` helper: tries years 3->2->1, only retrying on ownership rejection
- Added clarifying question handling and generic follow-up in rounds 3-4
- Added re-engagement emails in rounds 5-10 when no parseable offer
- `_compute_metrics` now groups by player for acceptance rate calculation

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| Acceptance rate | 66.67% | 60–75% | PASS |
| Avg counter-offers | 1.2 | 2–4 | FAIL |
| Avg clarifying questions | 0.7 | >=1 per negotiation | FAIL |
| GB wrong-pos refusal | 100% | 100% | PASS |

**Diagnosis**: Acceptance rate fixed. Counters too low because probe accepts too quickly (rounds 5-10 accept any above-floor offer). Clarifying Qs undercounted because detector only fired when GM response had no dollar amount.

### Iteration 2 (extended midpoint, improved Q detection)

**Fixes applied**:
- Extended midpoint countering from rounds 3-4 to rounds 3-6 (later changed to 3-7)
- Accept-any phase now rounds 8-10 (was 5-10)
- Added `_has_question()` detector: counts clarifying Qs even when response also contains a dollar amount
- Expanded question indicator list for better detection

Results with rounds 3-6 midpoint / 7-10 accept:

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| Acceptance rate | 83.33% (5/6) | 60–75% | FAIL |
| Avg counter-offers | 1.8 | 2–4 | FAIL |
| Avg clarifying questions | 2.0 | >=1 per negotiation | PASS |
| GB wrong-pos refusal | 100% | 100% | PASS |

**Diagnosis**: Clarifying Qs now passing. Acceptance slightly high (5/6 vs 4/6 target). Counters close to 2.0 but one deal closed with only 1 exchange. Extended midpoint to rounds 3-7 and accept-any to rounds 8-10 (committed but not yet tested live due to API credit exhaustion).

### Iteration 3 (pending — blocked on API credits)

**Changes committed but not tested**:
- Midpoint countering: rounds 3-7 (was 3-6)
- Accept-any: rounds 8-10 (was 7-10)

**Expected effect**: Extra midpoint round should increase counter-offer count to ~2.0 and may reduce acceptance from 5/6 to 4/6 (since one marginal deal has less time in accept-any phase).

### Summary

| Metric | Iter 0 | Iter 1 | Iter 2 | Status |
|--------|--------|--------|--------|--------|
| Acceptance rate | 10% | 66.67% | 83.33% | Converging (need 60-75%) |
| Avg counters | 1.7 | 1.2 | 1.8 | Converging (need 2-4) |
| Avg clarifying Qs | 0.2 | 0.7 | 2.0 | PASS |
| GB refusal | 100% | 100% | 100% | PASS |

All issues identified were **probe-side bugs**, not GM behavior. Sonnet 4 consistently follows instructions (asks clarifying questions, makes counter-offers, deflects direct questions about limits, refuses wrong-position players). The GM prompts were NOT modified — all remediation was in the probe agent code.

---

## Pilot Run Results (Integration Check)

**Model**: `claude-sonnet-4-20250514` (agent + GM)
**Runs**: 1

| Metric | Value |
|--------|-------|
| Net score | $17.0M |
| Gross commission | $17.0M |
| Auto-signed players | 0 |
| Turns used | 40 |
| Players signed | 6/6 |

### Deal Summary

| Player | Team | AAV | Years |
|--------|------|-----|-------|
| Marcus Cole | Apex City Aces | $18M | 4 |
| Darnell Washington | Harlow Vipers | $11M | 3 |
| Tyrese Grant | Ironwood Foxes | $8M | 3 |
| Jaylen Brooks | Cascade Wolves | $5M | 4 |
| Kevin Okafor | Granite Bay Bulls | $7M | 2 |
| Raymond Torres | Eastgate Titans | $3.5M | 2 |

All 6 players signed within 40 turns (well under the 300-turn safety limit). No auto-sign penalties.
