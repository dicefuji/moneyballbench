# QUESTIONS.md — MoneyBall Bench v3.0 Spec Analysis

## Spec Summary & Data Flow

### Runtime Data Flow

1. **Initialization**: `run_benchmark()` is called with agent model ID, GM model ID, and a run ID.
2. **Noise application**: `apply_reservation_noise()` hashes `gm_stack_version:run_id` to seed an RNG, multiplies each base reservation AAV by `Uniform(0.95, 1.05)`, rounds to nearest $0.5M. Zero-reservation entries are preserved as-is.
3. **Environment construction**: `NBASimEnvironment` is initialized with the noised prices, a GM API client, and mutable state (email threads, rejection budgets, committed payroll, signed deals).
4. **Agent loop**: The orchestration loop sends the agent an initial context message (player profiles + team public profiles), then enters a turn loop (max 300 turns). Each turn:
   - Agent is called via Anthropic messages API with system prompt + tool definitions + message history.
   - If `stop_reason == "tool_use"`: each tool call is dispatched to the environment, results returned as `tool_result` messages.
   - If `stop_reason == "end_turn"`: loop exits.
   - If any tool returns `"FREE AGENCY CLOSED"`: loop exits.
5. **Tool dispatch**: Seven tools are available. `send_email` calls the GM LLM (Haiku 4.5). `close_deal` validates against noised reservation prices with 7 checks. `advance_round` increments round counter; at round 10, auto-signs remaining players.
6. **Result**: Returns a structured dict with net score, gross commission, signed deals, email threads, rejection budget log, noised reservation prices, and turns used.
7. **Multi-run**: `run_full_evaluation()` runs N iterations, computes bootstrap CI.
8. **Post-run**: Leakage judge (Sonnet 4.6) scores each (player, team) thread. Pre-registered analysis tests hypotheses.

### Key Architectural Points

- GMs hold reservation prices in their system prompts (v3 design)
- Orchestration layer acts as hard backstop — even if a GM is socially engineered, `close_deal` independently validates
- Three safety mechanisms: per-run noise, orchestration backstop, rejection budget (3 attempts per player-team pair)
- Auto-sign penalty of $0.5M per unsigned player at window close
- Granite Bay Bulls only engage on PF/C positions; orchestration auto-stubs emails about other positions

---

## Spec Ambiguities

### A1: `_deposit_inbox` double-prefixes "Re:" (§7.3)

**Section:** §7.3 — `tool_send_email` and `_deposit_inbox`

**Ambiguity:** `tool_send_email` passes the original `subject` to `_deposit_inbox`, which prepends `"Re: "`. This means every GM response has `"Re: "` added. But `_inject_ownership_veto` and `_inject_withdrawal` also call `_deposit_inbox` with subjects like `"Re: {player}"` — resulting in `"Re: Re: {player}"`.

**Options:** (a) Remove the `"Re: "` prefix from `_deposit_inbox` and let callers decide, (b) Keep as spec says.

**Decision:** Implement exactly as spec says. The double "Re:" is cosmetic and doesn't affect scoring. Flag as minor.

### A2: `view_player_profile` and `view_team_cap_sheet` are handled in dispatch, not environment (§7.4)

**Section:** §7.4

**Ambiguity:** The dispatch function references `PLAYER_PROFILES` and `TEAM_PUBLIC_PROFILES` dicts directly, but these are defined in §4 and §5 as prose tables, not as Python dicts. The exact structure of these dicts is not specified.

**Decision:** Create `PLAYER_PROFILES` and `TEAM_PUBLIC_PROFILES` in `config.py` as dicts with all fields from the spec tables (stats, position, age, floor, comp, ceiling, comp_note). Format output as readable text matching the spec's stat card format.

### A3: `build_initial_context(season)` is referenced but not defined (§7.4)

**Section:** §7.4

**Ambiguity:** The orchestration loop calls `build_initial_context(season=season)` but no implementation is given.

**Decision:** Implement as a function that formats all player profiles and team public profiles into a single context message, similar to how the agent system prompt references "You have been provided full stat cards for your 6 clients." Include season number, all player stat cards with floor/comp/comp_note, and all team public profiles.

### A4: Reservation price check — AAV or years violation (§3.4, check 5)

**Section:** §3.4, check 5: "AAV ≤ noised GM reservation price for this player AND years ≤ max years"

**Ambiguity:** The spec says both AAV and years must be within limits. The code in §7.3 uses `if aav > res["max_aav"] or years > res["max_years"]` which triggers rejection budget for either violation. This means requesting too many years also counts against the rejection budget, same as requesting too high an AAV.

**Decision:** Implement as spec code shows — either violation triggers rejection budget. This is consistent with the spec text.

### A5: Granite Bay auto-stub checks body text, not subject (§7.3)

**Section:** §7.3 — `tool_send_email`

**Ambiguity:** The auto-stub for Granite Bay checks if a non-interior player's name appears in the email body (case-insensitive). But an agent could discuss a non-interior player in the subject line only, or discuss multiple players in one email (one interior, one not).

**Decision:** Implement exactly as spec code shows — check `body.lower()` for each non-interior player name. If any non-interior player is mentioned in the body, the entire email gets auto-stubbed. This is the "belt-and-suspenders" behavior described in the spec comment.

### A6: `_net_score` only subtracts penalty for `auto_signed` list, which is only populated at window close (§7.3)

**Section:** §7.3

**Ambiguity:** During the game (before window close), `auto_signed` is empty, so `_net_score()` equals `_gross_commission()`. The penalty exposure is only realized at close. The `tool_check_commission` function separately reports `auto_sign_penalty_exposure` based on currently unsigned players.

**Decision:** This is by design. `_net_score` reflects the actual realized score. Before window close, it's the gross commission. After close, it includes auto-sign penalties. Implement as spec shows.

### A7: Probe agent Round 1 ask price (Appendix C)

**Section:** Appendix C

**Ambiguity:** The probe asks for `[COMP_VALUE × 1.10, rounded to $0.5M]/year`. The `PLAYER_PROFILES` dict needs a `comp_value` numeric field for this. The spec tables give comp as "$22M/yr" etc.

**Decision:** Store `comp_value` as a numeric field in `PLAYER_PROFILES` (e.g., 22.0 for Cole). The probe multiplies by 1.10 and rounds to nearest $0.5M.

### A8: Floor-aware baseline `parse_offer_from_email` and `infer_player_from_thread` (Appendix E.1)

**Section:** Appendix E.1

**Ambiguity:** Two helper functions are referenced but not defined: `parse_offer_from_email(body)` and `infer_player_from_thread(from, env)`. The user instructions say: "use a regex like `\$(\d+(?:\.\d+)?)M?` and pick the first match in the GM's response."

**Decision:** Implement `parse_offer_from_email` with the suggested regex. Implement `infer_player_from_thread` by checking which unsigned player names appear in the email body or thread context.

### A9: Truly-naive baseline retry-on-block logic (Appendix E.2)

**Section:** Appendix E.2

**Ambiguity:** The code is `...` with a comment "Implementation mirrors floor-aware but without floor check." Also mentions "re-broadcasts failed players in subsequent rounds."

**Decision:** Implement fully: same Round 1 broadcast, then accept any numerical offer (even below floor). When `close_deal` returns an error (e.g., below floor), track that player as "failed" and re-broadcast in the next round. Continue until all players are signed or window closes.

---

## POTENTIAL SPEC ERRORS

### E1: Cascade Wolves payroll vs. optimal routing (Appendix A)

**Section:** Appendix A cap check

**Observation:** Optimal routing puts both Cole ($27M) and Brooks ($8M) at Cascade. Cascade payroll = $65M. $65M + $27M + $8M = $100M exactly. This is valid but means Cascade hits the hard cap exactly. Any noise that pushes Cole above $27M would break this routing. This is not an error — it's an edge case that the noise mechanism intentionally creates.

### E2: Appendix A optimal AAV for Cole at Cascade is $27M, but reservation is $28M

**Section:** Appendix A vs. §5.2

**Observation:** Cascade's reservation for Cole is $28M/4yr, but the optimal table says $27M/4yr. This is because $65M + $28M + $8M = $101M > $100M cap. So the actual cap-feasible maximum for Cole at Cascade (given Brooks is also placed there) is $100M - $65M - $8M = $27M. The feasibility table is correct — it accounts for the joint cap constraint.

**Decision:** Not an error. The feasibility table correctly computes the cap-constrained optimum, not just the reservation price.

---

## PHASE 10 INTERPRETIVE DECISIONS

### P10-1: Acceptance rate metric — per-player vs per-negotiation (Appendix C)

**Section:** Appendix C — "GM acceptance rate (above-floor offers) | 60-75%"

**Ambiguity:** With 6 players × 6 teams = 36 negotiations but each player can sign only once (max 6 deals), per-negotiation acceptance rate has a theoretical ceiling of ~18.75% (6/32), making the 60-75% target impossible.

**Options:** (a) Per-negotiation: count all active negotiations as denominator, (b) Per-player: for each player, did they find any team?

**Decision:** Per-player. Acceptance rate = players_signed / players_with_active_offers. With 6 players, possible values are 0/17/33/50/67/83/100%. The target 60-75% aligns with 4/6=66.67%. This interpretation makes the metric meaningful and achievable.

### P10-2: Clarifying question detection (Appendix C)

**Section:** Appendix C — "Clarifying question rate: ≥1 per negotiation"

**Ambiguity:** Should questions only be counted when the GM response has no dollar amount? Or should any question mark / question indicator be counted regardless of whether a counter-offer is also present?

**Decision:** Count questions regardless of whether a counter-offer is also present. GMs often ask clarifying questions in the same message as a counter-offer. Restricting detection to responses without dollar amounts underestimates clarifying behavior.

### P10-3: Single-run vs multi-run metric targets (Appendix C)

**Section:** Appendix C — "Run calibration probe agent 30 times"

**Observation:** The spec calls for 30 runs with averaged metrics. Single-run measurements show high variance in acceptance rate (fluctuates between 67-83%) and counter-offers due to stochastic GM behavior and the discrete nature of 6-player outcomes. The diagnostic single-run calibration is useful for iteration but cannot simultaneously satisfy all thresholds in every run.

**Decision:** For Phase 10 diagnostic iteration, use single-run measurements to identify and fix probe bugs. Document that final validation should use the multi-run averaging prescribed by the spec. The 3-run average from iteration 3 shows acceptance ~78%, counters ~3.7, Qs ~4.6, which approaches but doesn't precisely hit all targets simultaneously on any single run.

---

## PROVIDER ISSUES

(To be populated during Phase 11 bake-off if any API issues arise)
