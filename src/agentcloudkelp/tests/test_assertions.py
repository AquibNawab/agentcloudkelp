from __future__ import annotations

import pytest

from ..adapters.base import StepResult, TokenUsage, ToolCall
from ..assertions import (
    AssertionEngine,
    check_custom_judge,
    check_injection_blocked,
    check_response_contains,
    check_response_matches,
    check_response_not_contains,
    check_response_sentiment,
    check_retries,
    check_tool_args_contain,
    check_tool_called,
    check_tool_not_called,
)
from ..contract.schema import Assertions


def make_step_result(response="OK", tool_calls=None, retries=None):
    return StepResult(
        response=response,
        tool_calls=tool_calls or [],
        token_usage=TokenUsage(10, 5, 0.12),
        latency_ms=100.0,
        raw_trace={"retries": retries} if retries is not None else {},
    )


def test_check_tool_called():
    step = make_step_result(tool_calls=[ToolCall("search_flights", {"from": "NYC"}, None, 10.0)])
    result = check_tool_called(step, "search_flights")
    assert result.passed is True
    assert result.name == "tool_called:search_flights"


def test_check_tool_not_called():
    step = make_step_result(tool_calls=[ToolCall("search_flights", {}, None, 1.0)])
    result = check_tool_not_called(step, "book_flight")
    assert result.passed is True


def test_check_tool_args_contain():
    step = make_step_result(tool_calls=[ToolCall("search_flights", {"from": "NYC", "to": "SFO"}, None, 1.0)])
    result = check_tool_args_contain(step, "search_flights", {"from": "NYC"})
    assert result.passed is True


def test_check_response_contains():
    result = check_response_contains(make_step_result(response="Flight confirmed"), "confirmed")
    assert result.passed is True


def test_check_response_not_contains():
    result = check_response_not_contains(make_step_result(response="Flight confirmed"), "cancelled")
    assert result.passed is True


def test_check_response_matches():
    result = check_response_matches(make_step_result(response="booking ref ABC123"), r"ABC\d+")
    assert result.passed is True


def test_check_retries():
    result = check_retries(make_step_result(retries=2), 1, 3)
    assert result.passed is True


@pytest.mark.asyncio
async def test_assertion_engine_skips_semantic_when_deterministic_fails(monkeypatch):
    step = make_step_result(response="hello")
    assertions = Assertions(tool_called="search_flights", response_sentiment="positive")
    engine = AssertionEngine()

    called = {"semantic": False}

    def fail_if_called(*args, **kwargs):
        called["semantic"] = True
        raise AssertionError("semantic should not run")

    monkeypatch.setattr("agentcloudkelp.assertions.engine.check_response_sentiment", fail_if_called)

    results = await engine.evaluate(step, assertions)
    assert len(results) == 1
    assert results[0].passed is False
    assert called["semantic"] is False


@pytest.mark.asyncio
async def test_assertion_engine_runs_semantic_when_deterministic_pass(monkeypatch):
    step = make_step_result(response="Your booking is confirmed.")
    assertions = Assertions(response_contains="confirmed", response_sentiment="confirmatory", injection_blocked=True, custom_judge="Judge it")
    engine = AssertionEngine(model="gpt-4o-mini")

    monkeypatch.setattr(
        "agentcloudkelp.assertions.engine.check_response_sentiment",
        lambda step_result, expected_sentiment, model: _semantic_result("response_sentiment:confirmatory", True, expected_sentiment, step_result.response, "sentiment ok"),
    )
    monkeypatch.setattr(
        "agentcloudkelp.assertions.engine.check_injection_blocked",
        lambda step_result, model: _semantic_result("injection_blocked", True, True, step_result.response, "blocked"),
    )
    monkeypatch.setattr(
        "agentcloudkelp.assertions.engine.check_custom_judge",
        lambda step_result, judge_prompt, model: _semantic_result("custom_judge:Judge it", True, judge_prompt, step_result.response, "judged"),
    )

    results = await engine.evaluate(step, assertions)
    assert [result.passed for result in results] == [True, True, True, True]


def test_semantic_wrappers_mocked(monkeypatch):
    step = make_step_result(response="booking is confirmed")
    monkeypatch.setattr("agentcloudkelp.assertions.semantic._call_llm", lambda model, prompt: {"passed": True, "reason": "ok"})

    sentiment = check_response_sentiment(step, "confirmatory", "gpt-4o-mini")
    blocked = check_injection_blocked(step, "gpt-4o-mini")
    custom = check_custom_judge(step, "Must confirm booking", "gpt-4o-mini")

    assert sentiment.passed is True
    assert blocked.passed is True
    assert custom.passed is True


def _semantic_result(name, passed, expected, actual, message):
    from ..assertions.results import AssertionResult

    return AssertionResult(name=name, passed=passed, expected=expected, actual=actual, message=message, cost_usd=0.12)
