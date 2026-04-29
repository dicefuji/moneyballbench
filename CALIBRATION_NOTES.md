# Calibration Notes — MoneyBall Bench v3.0

## GM Model Used
`claude-sonnet-4-20250514` (Haiku models were not available with the provided API key)

## Calibration Results (Probe Agent)

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| Acceptance rate | 10% | 60–75% | FAIL |
| Avg counter-offers | 1.7 | 2–4 | FAIL |
| Avg clarifying questions | 0.2 | ≥1 per negotiation | FAIL |
| Granite Bay wrong-position refusal | 100% | 100% | PASS |

**Overall: FAIL**

### Analysis

The probe agent's scripted behavior (fixed ask prices, templated responses) does not fully exercise the negotiation loop. The low acceptance rate (10%) indicates that most negotiations stall because the probe's scripted midpoint countering doesn't converge within the 4-round negotiation window. GMs respond substantively but the probe's rigid response templates don't advance negotiations to closure.

The Granite Bay wrong-position refusal metric passes perfectly — GMs correctly decline non-interior players with polite refusals.

### Remediation Path (per Appendix C)

1. **Extend probe negotiation window**: The probe currently only accepts offers within 5% of ask in rounds 3-4. Widening this to 10% or extending to rounds 3-6 would increase acceptance rate.
2. **GM temperature tuning**: The current temperature (0.3) produces consistent but sometimes overly conservative GM responses. Could test 0.4-0.5.
3. **Counter-offer calibration**: The probe's midpoint countering is mechanical; GMs may need more nuanced engagement to produce 2-4 counter-offers before agreement.

These are calibration tuning items for the research team — the infrastructure itself works correctly end-to-end.

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

All 6 players signed within 40 turns (well under the 300-turn safety limit). No auto-sign penalties. Result schema validates correctly. Full email threads captured.

## Conclusion

The infrastructure runs end-to-end against the live API. The calibration probe needs tuning (expected for v3.0 first run), but the core benchmark pipeline — negotiation, deal validation, scoring, result capture — works correctly.
