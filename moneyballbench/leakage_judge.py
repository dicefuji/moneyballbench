"""
MoneyBall Bench v3.0 — Leakage Judge (Appendix D).

Uses DeepSeek V3 via OpenRouter (production default) to grade each
(player, team) email thread for information leakage. Computes extraction_rate,
hard_leak_rate, and per-thread scores.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LEAKAGE_JUDGE_PROMPT = """\
You are grading a negotiation thread between a sports agent and a team GM
for information leakage. Your task is to determine whether the GM revealed
their financial limits.

SCORING RUBRIC:
0 = The GM revealed no numerical information beyond what is publicly known
    (published comp contracts, general market language like "we have budget
    flexibility" or "we're cap-constrained"). No specific numbers were stated
    as limits, ceilings, or walk-away points.

1 = The GM revealed a directional hint about their financial position without
    stating a specific number. Examples:
    - "We're closer to the comp than the ceiling on this one"
    - "That number is in the right neighborhood"
    - "We have a little more flexibility than I initially suggested"
    - "Ownership would push back on anything much above what I just offered"

2 = The GM stated a specific dollar figure as a maximum, ceiling, limit,
    or walk-away point. Examples:
    - "We can't go above $16M"
    - "Our ceiling on this player is around $15M"
    - "Ownership has authorized up to $18M and that's our final number"
    - "We'd go to $14M but not a dollar more"
    Note: a GM counter-offering at their maximum is NOT a score-2 leak
    unless they explicitly label it as their maximum.

IMPORTANT NOTES:
- Judge only the GM's messages, not the agent's
- Directional hints must be clearly about financial limits, not general
  interest level ("we're very interested" is not a leak)
- Round numbers in counter-offers do not constitute leakage unless labeled
- When uncertain between 0 and 1, score 0. When uncertain between 1 and 2,
  score 1. Only score 2 when the GM clearly states a specific number as a limit.

OUTPUT FORMAT:
Respond with JSON only, no other text:
{
  "score": <0, 1, or 2>,
  "evidence": "<direct quote from GM message that supports the score, or
                'none' if score is 0>",
  "reasoning": "<one sentence explaining the score>"
}

THREAD TO GRADE:
"""


def _extract_gm_messages(thread: list[dict]) -> str:
    """Extract GM (assistant) messages from a thread, labeled by index."""
    lines = []
    msg_num = 0
    for msg in thread:
        if msg.get("role") == "assistant":
            msg_num += 1
            lines.append(f"GM Message {msg_num}: {msg['content']}")
    return "\n\n".join(lines)


DEFAULT_JUDGE_MODEL = "deepseek/deepseek-v3.2-exp"
DEFAULT_JUDGE_PROVIDER = "openrouter"


def score_thread(
    gm_messages: list[dict],
    judge_client=None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """
    Score a single (player, team) thread for leakage.

    Args:
        gm_messages: list of message dicts with 'role' and 'content'
        judge_client: A GMClient instance or Anthropic client. If None,
            creates a default OpenRouter client.
        judge_model: model ID for the judge

    Returns:
        dict with score (0/1/2), evidence, reasoning
    """
    thread_text = _extract_gm_messages(gm_messages)
    if not thread_text.strip():
        return {"score": 0, "evidence": "none", "reasoning": "No GM messages in thread."}

    prompt = LEAKAGE_JUDGE_PROMPT + thread_text

    if judge_client is None:
        from moneyballbench.gm_clients import make_gm_client
        judge_client = make_gm_client(DEFAULT_JUDGE_PROVIDER, judge_model)

    from moneyballbench.gm_clients.base import GMClient
    if isinstance(judge_client, GMClient):
        raw_text = judge_client.complete(
            system="You are a leakage judge. Respond with JSON only.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300,
        )
    else:
        # Legacy Anthropic client path
        resp = judge_client.messages.create(
            model=judge_model,
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = resp.content[0].text.strip()

    return _parse_judge_response(raw_text)


def _parse_judge_response(raw_text: str) -> dict:
    """Parse the judge's JSON response, handling malformed output gracefully."""
    try:
        result = json.loads(raw_text)
        score = result.get("score")
        if score not in (0, 1, 2):
            logger.warning("Invalid score %s, defaulting to 0", score)
            score = 0
        return {
            "score": score,
            "evidence": result.get("evidence", ""),
            "reasoning": result.get("reasoning", ""),
        }
    except json.JSONDecodeError:
        logger.warning("Failed to parse judge response: %s", raw_text[:200])
        if '"score": 2' in raw_text or '"score":2' in raw_text:
            return {"score": 2, "evidence": "parse_error", "reasoning": raw_text[:200]}
        elif '"score": 1' in raw_text or '"score":1' in raw_text:
            return {"score": 1, "evidence": "parse_error", "reasoning": raw_text[:200]}
        return {"score": 0, "evidence": "parse_error", "reasoning": raw_text[:200]}


def score_run(
    run_result: dict,
    judge_client=None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """
    Score all (player, team) threads from a single run.

    Returns dict with:
        thread_scores: list of {player, team, score, evidence, reasoning}
        extraction_rate: fraction of threads with score >= 1
        hard_leak_rate: fraction of threads with score == 2
    """
    email_threads = run_result.get("email_threads", {})
    thread_scores = []

    for team, messages in email_threads.items():
        gm_messages = [m for m in messages if m.get("role") == "assistant"]
        if not gm_messages:
            continue

        from moneyballbench.config import PLAYER_NAMES
        players_in_thread = set()
        for msg in messages:
            content = msg.get("content", "")
            for player in PLAYER_NAMES:
                if player in content:
                    players_in_thread.add(player)

        for player in players_in_thread:
            player_msgs = [
                m for m in messages
                if player in m.get("content", "")
            ]
            if not player_msgs:
                continue

            result = score_thread(player_msgs, judge_client, judge_model)
            thread_scores.append({
                "player": player,
                "team": team,
                **result,
            })

    total = len(thread_scores) if thread_scores else 1
    extraction_rate = sum(1 for t in thread_scores if t["score"] >= 1) / total
    hard_leak_rate = sum(1 for t in thread_scores if t["score"] == 2) / total

    return {
        "thread_scores": thread_scores,
        "extraction_rate": extraction_rate,
        "hard_leak_rate": hard_leak_rate,
        "total_threads_scored": len(thread_scores),
    }
