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

### PI-1: OpenRouter free tier blocks calibration runs (402 Payment Required)

**Provider:** OpenRouter (free tier)

**Issue:** The free tier enforces a very low per-request token ceiling (~5 max_tokens). Requests with max_tokens >= 50 return HTTP 402, even though the account shows $9.80 remaining of $10 limit. The calibration probe requires max_tokens=400 per GM response, making it impossible to run on the free tier.

**Workaround:** Add credits to the OpenRouter account ($1-5 is sufficient for the full bake-off). The retry logic in `OpenRouterGMClient` handles transient 402s gracefully.

**Impact:** Phase 11 bake-off blocked until funded account is available.

### PI-2: Kimi K2.5 is a reasoning model — returns null content

**Provider:** OpenRouter, model `moonshotai/kimi-k2.5`

**Issue:** Kimi K2.5 routes through a reasoning inference path. The `content` field in responses is `null`; output appears in the `reasoning` field instead. With max_tokens=400, all tokens go to reasoning and the model never produces a final answer.

**Workaround:** Use Kimi K2.6 (`moonshotai/kimi-k2.6`) instead — same model family, returns proper content. The OpenRouterGMClient also falls back to the `reasoning` field when `content` is null, as a safety net.

**Decision:** Updated default bake-off candidate from K2.5 to K2.6.

---

## PHASE 13 DECISIONS

### P13-1: DeepSeek V3 snapshot selection

**Section:** Phase 13 — production defaults

**Available snapshots on OpenRouter (as of 2026-04-29):**
- `deepseek/deepseek-v3.2-exp` — experimental, prompt $0.00000027/token, completion $0.00000041/token
- `deepseek/deepseek-v3.2` — stable, prompt $0.000000252/token, completion $0.000000378/token
- `deepseek/deepseek-v3.2-speciale` — speciale variant, prompt $0.0000004/token, completion $0.0000012/token
- `deepseek/deepseek-chat-v3-0324` — March 2024 snapshot (used in Phase 11 bake-off)
- `deepseek/deepseek-chat-v3.1` — v3.1 stable

**Decision:** Selected `deepseek/deepseek-v3.2-exp` as production snapshot. Rationale: (a) user specified `deepseek-v3.2-exp` in the Phase 13 task, (b) it's the newest V3 variant, (c) pricing is competitive. Note: Phase 11 bake-off data was collected against `deepseek/deepseek-chat-v3-0324`, a different snapshot. Counter-offer behavior may differ slightly on v3.2-exp.

### P13-2: Counter-offer band update

**Section:** Appendix C — calibration thresholds

**Change:** Band widened from 2–4 to 4–6 per research team decision. This reflects observed natural negotiation length of DeepSeek V3 as production GM (bake-off measured 6.5 on v3-0324).

### P13-3: Kimi K2.5 as agent model — reasoning token handling

**Issue:** Kimi K2.5 returns null in `content` field with output in `reasoning` field (same issue as PI-2). When used as an agent (not GM), this means the orchestration loop would receive empty text content. The OpenRouter agent client handles this by checking for tool_calls in the response, which work correctly even when content is null.

**Decision:** Include K2.5 in the pilot as specified. The agent client handles the null-content edge case. If K2.5 cannot use tool calling effectively via OpenRouter, document and proceed with K2.6 only.

---

## PHASE 16 DECISIONS

### P16-1: Qwen agent model selection

**Section:** Phase 16 — extended pilot

**Available Qwen models on OpenRouter (as of 2026-05-01):**
- `qwen/qwen3-max` — current-generation Qwen3 Max. Released Sep 23, 2025. 262,144 context, $0.78/M input, $3.90/M output. Optimized for tool calling and RAG. Does NOT include dedicated "thinking" mode. Tool call error rate ~6% per OpenRouter metrics.
- `qwen/qwen3-235b-a22b` — Qwen3 235B MoE. Larger but less optimized for tool calling.
- `qwen/qwen-max` — older Qwen Max (pre-Qwen3 series).

**Decision:** Selected `qwen/qwen3-max` as the Qwen agent model. Rationale: (a) it is the most recent current-generation Qwen model, (b) explicitly optimized for tool calling and RAG per OpenRouter description, (c) no "thinking" mode means no reasoning token overhead (unlike K2.6), (d) user specified "qwen/qwen3-max or the closest current-generation Qwen agent-capable model."

### P16-2: DeepSeek V3 self-play documentation

**Section:** Phase 16 — extended pilot

**Self-play configuration:** `deepseek/deepseek-v3.2-exp` serves simultaneously as:
- GM model (generates negotiation responses)
- Agent model (generates agent tool calls and strategy)
- Leakage judge model (evaluates thread leakage)

**Implications:**
1. The agent and GM share architecture, training data, and behavioral tendencies. The agent may benefit from "knowing" how the GM tends to respond, which could inflate scores.
2. The judge evaluating its own model's behavior may have blind spots for leakage patterns characteristic of its own generation style.
3. These overlaps are documented in run metadata and PILOT_RESULTS.md for researcher awareness.

**Decision:** Proceed with self-play as specified. The self-play dynamic is itself a research question worth documenting. Results should be interpreted with awareness of the shared-architecture advantage.

### P16-3: Qwen3 Max performance characteristics

**Observation (post-pilot):** Qwen3 Max demonstrated the most consistent performance of any model tested:
- 10/10 success rate
- Lowest standard deviation (1.32) across all 4 models
- Mean 15.89, CI (15.14, 16.71) — remarkably tight
- Average 28 turns per run — efficient negotiations
- Only 1 auto-signed player across all 10 runs

The model's non-reasoning architecture (no dedicated thinking tokens) eliminates the truncation risk that plagued K2.6, while its tool-calling optimization results in reliable engagement.

---

## PHASE 17 DECISIONS

### P17-1: DeepSeek V4 Flash agent model selection

**Section:** Phase 17 — extended pilot

**Model ID on OpenRouter:** `deepseek/deepseek-v4-flash`
**Snapshot resolved by OpenRouter:** `deepseek/deepseek-v4-flash-20260423` (released Apr 24, 2026)

**Model characteristics:**
- 284B total parameters, 13B activated (Mixture-of-Experts)
- 1,048,576 token context window
- $0.14/M input tokens, $0.28/M output tokens
- Supports `high` and `xhigh` reasoning efforts; `xhigh` maps to max reasoning
- Hybrid attention for efficient long-context processing

**Decision:** Used default reasoning mode (no explicit `high` or `xhigh` reasoning effort parameter set). Per instructions: "use the default — do not enable explicit reasoning modes unless the run consistently fails without them." All 10 runs succeeded at default, so no reasoning mode override was needed.

### P17-2: DeepSeek V4 Flash performance characteristics

**Observation (post-pilot):** DeepSeek V4 Flash demonstrated strong, consistent performance:
- 10/10 success rate
- Mean 16.69, CI (15.83, 17.60)
- Standard deviation 1.55 — tight, though slightly wider than Qwen3 Max (1.32) and DeepSeek V3 (1.02)
- Average 21 turns per run — efficient negotiations comparable to K2.5 (18) and Qwen3 Max (28)
- Zero auto-signed players across all 10 runs
- Zero rejection budget usage — never triggered above-reservation close_deal attempts
- Lowest cost of any model tested ($0.24 for 10 runs)

The model includes reasoning tokens in its output (visible as `reasoning` field in OpenRouter responses), but these fit comfortably within the 2048 max_tokens budget — no truncation issues observed.

### P17-3: Transient API errors with V4 Flash

**Issue:** During the pilot run, V4 Flash occasionally returned HTTP 400 (Bad Request) and 429 (rate limit) errors from OpenRouter. These were transient and resolved by retry logic.

**Decision:** Added HTTP 400 to the list of retryable error codes in both agent and GM OpenRouter clients. The 400 errors appear to be provider-side routing issues (different providers handle the model: AtlasCloud, SiliconFlow) rather than malformed requests, since the same request succeeds on retry.

---

## PHASE 18 DECISIONS

### P18-1: DeepSeek V4 Pro agent model selection

**Section:** Phase 18 — extended pilot (final model)

**Model ID on OpenRouter:** `deepseek/deepseek-v4-pro`
**Snapshot resolved by OpenRouter:** `deepseek/deepseek-v4-pro-20260423` (released Apr 24, 2026)

**Model characteristics:**
- 1.6T total parameters, 49B activated (Mixture-of-Experts)
- 1,048,576 token context window
- $0.435/M input tokens, $0.87/M output tokens
- Supports `high` and `xhigh` reasoning efforts; `xhigh` maps to max reasoning
- Built on same architecture as V4 Flash; larger activated parameter count (49B vs 13B)

**Decision:** Used default reasoning mode (no explicit `high` or `xhigh` reasoning effort parameter set). All 10 runs succeeded at default.

### P18-2: DeepSeek V4 Pro performance characteristics

**Observation (post-pilot):** V4 Pro matched DeepSeek V3 (self-play) in the top tier:
- 10/10 success rate
- Mean 18.20, CI (17.68, 18.85) — overlaps with DeepSeek V3 CI (17.76, 18.97)
- Standard deviation 1.01 — tightest of all models tested
- Average 20 turns per run — 3.5x fewer than DeepSeek V3 (69 turns)
- Zero auto-signed players, zero rejection budget usage
- Low leakage (0.56% extraction, 0% hard leak)
- Cost: ~$0.44 for 10 runs (still cheap)

V4 Pro reaching V3's score level without self-play advantage is significant — it suggests the DeepSeek V4 architecture is genuinely strong at negotiation, not just benefiting from shared GM/agent model.

### P18-3: V4 Pro tool-calling argument errors

**Issue:** V4 Pro occasionally sends malformed `send_email` tool arguments — splitting the `to`, `subject`, and `body` parameters across multiple tool calls instead of one, or omitting required parameters.

**Decision:** Added graceful error handling in the orchestration dispatch function. When a tool call raises `TypeError` or `KeyError` (wrong/missing arguments), the error is returned to the agent as a structured error message instead of crashing the run. V4 Pro consistently self-corrects after receiving the error feedback.

This is a general improvement to orchestration robustness — it doesn't change benchmark scoring or mechanics. Previous models that used tools correctly are unaffected (verified: 220 tests still pass). The fix benefits any future model that occasionally misformats tool calls.

### P18-4: OpenRouter credit exhaustion

**Issue:** The initial V4 Pro pilot attempt exhausted the $10 OpenRouter credit limit after completing only 1/10 runs. The previous key had accumulated ~$10 in usage across Phases 13-17.

**Resolution:** User provided a new API key with fresh credits. All 10 runs completed successfully on the second attempt.
