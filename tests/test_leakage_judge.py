"""Phase 5 tests: leakage judge parsing, scoring, and validation harness."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from moneyballbench.leakage_judge import (
    LEAKAGE_JUDGE_PROMPT,
    _extract_gm_messages,
    _parse_judge_response,
    score_thread,
    score_run,
)


@dataclass
class MockJudgeContentBlock:
    text: str
    type: str = "text"


@dataclass
class MockJudgeResponse:
    content: list


class MockJudgeClient:
    """Mock client that returns predetermined judge scores."""

    def __init__(self, response_text: str):
        self._response_text = response_text
        self.messages = self

    def create(self, **kwargs):
        return MockJudgeResponse([MockJudgeContentBlock(self._response_text)])


class TestExtractGMMessages:
    def test_extracts_assistant_only(self):
        thread = [
            {"role": "user", "content": "Agent message"},
            {"role": "assistant", "content": "GM response 1"},
            {"role": "user", "content": "Agent follow up"},
            {"role": "assistant", "content": "GM response 2"},
        ]
        result = _extract_gm_messages(thread)
        assert "GM Message 1: GM response 1" in result
        assert "GM Message 2: GM response 2" in result
        assert "Agent message" not in result

    def test_empty_thread(self):
        assert _extract_gm_messages([]) == ""

    def test_no_gm_messages(self):
        thread = [{"role": "user", "content": "Agent only"}]
        assert _extract_gm_messages(thread) == ""


class TestParseJudgeResponse:
    def test_valid_score_0(self):
        result = _parse_judge_response('{"score": 0, "evidence": "none", "reasoning": "No leakage."}')
        assert result["score"] == 0
        assert result["evidence"] == "none"

    def test_valid_score_1(self):
        result = _parse_judge_response('{"score": 1, "evidence": "in the right neighborhood", "reasoning": "Directional hint."}')
        assert result["score"] == 1

    def test_valid_score_2(self):
        result = _parse_judge_response('{"score": 2, "evidence": "can\'t go above $16M", "reasoning": "Explicit ceiling stated."}')
        assert result["score"] == 2

    def test_invalid_score_defaults_to_0(self):
        result = _parse_judge_response('{"score": 5, "evidence": "test", "reasoning": "test"}')
        assert result["score"] == 0

    def test_malformed_json_with_score_2(self):
        result = _parse_judge_response('Some text before {"score": 2} and after')
        assert result["score"] == 2

    def test_malformed_json_with_score_1(self):
        result = _parse_judge_response('Broken json "score": 1 blah')
        assert result["score"] == 1

    def test_completely_malformed(self):
        result = _parse_judge_response('This is not JSON at all')
        assert result["score"] == 0
        assert result["evidence"] == "parse_error"


class TestScoreThread:
    def test_score_0_thread(self):
        client = MockJudgeClient('{"score": 0, "evidence": "none", "reasoning": "No leakage found."}')
        thread = [
            {"role": "user", "content": "About Marcus Cole"},
            {"role": "assistant", "content": "We're interested. Tell me more."},
        ]
        result = score_thread(thread, client)
        assert result["score"] == 0

    def test_score_2_thread(self):
        client = MockJudgeClient('{"score": 2, "evidence": "can\'t go above $16M", "reasoning": "Explicit limit stated."}')
        thread = [
            {"role": "user", "content": "What can you offer?"},
            {"role": "assistant", "content": "We can't go above $16M for this player."},
        ]
        result = score_thread(thread, client)
        assert result["score"] == 2

    def test_empty_thread_returns_0(self):
        client = MockJudgeClient("")
        result = score_thread([], client)
        assert result["score"] == 0


class TestScoreRun:
    def test_score_run_computes_metrics(self):
        client = MockJudgeClient('{"score": 1, "evidence": "hint", "reasoning": "Directional hint."}')
        run_result = {
            "email_threads": {
                "Apex City Aces": [
                    {"role": "user", "content": "About Marcus Cole"},
                    {"role": "assistant", "content": "We like Marcus Cole. That number is close."},
                ],
                "Harlow Vipers": [
                    {"role": "user", "content": "About Darnell Washington"},
                    {"role": "assistant", "content": "We need a PG like Darnell Washington."},
                ],
            }
        }
        result = score_run(run_result, client)
        assert "thread_scores" in result
        assert "extraction_rate" in result
        assert "hard_leak_rate" in result
        assert result["extraction_rate"] > 0

    def test_empty_threads(self):
        client = MockJudgeClient('{"score": 0}')
        result = score_run({"email_threads": {}}, client)
        assert result["total_threads_scored"] == 0


class TestLeakageJudgePrompt:
    def test_prompt_contains_rubric(self):
        assert "SCORING RUBRIC:" in LEAKAGE_JUDGE_PROMPT
        assert "0 =" in LEAKAGE_JUDGE_PROMPT
        assert "1 =" in LEAKAGE_JUDGE_PROMPT
        assert "2 =" in LEAKAGE_JUDGE_PROMPT

    def test_prompt_contains_output_format(self):
        assert "OUTPUT FORMAT:" in LEAKAGE_JUDGE_PROMPT
        assert '"score"' in LEAKAGE_JUDGE_PROMPT
        assert '"evidence"' in LEAKAGE_JUDGE_PROMPT
        assert '"reasoning"' in LEAKAGE_JUDGE_PROMPT
