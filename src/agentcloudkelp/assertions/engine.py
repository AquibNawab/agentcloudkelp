from __future__ import annotations

from typing import Any, List

from ..adapters.base import StepResult
from ..contract.schema import Assertions
from .results import AssertionResult

from .deterministic import (
    check_response_contains,
    check_response_matches,
    check_response_not_contains,
    check_retries,
    check_tool_args_contain,
    check_tool_called,
    check_tool_not_called,
)
from .semantic import check_custom_judge, check_injection_blocked, check_response_sentiment


class AssertionEngine:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    async def evaluate(self, step_result: StepResult, assertions: Assertions) -> List[AssertionResult]:
        results: List[AssertionResult] = []
        deterministic_results: List[AssertionResult] = []

        if assertions.tool_called:
            deterministic_results.append(check_tool_called(step_result, assertions.tool_called))
        if assertions.tool_not_called:
            deterministic_results.append(check_tool_not_called(step_result, assertions.tool_not_called))
        if assertions.tool_args_contain:
            tool_name = assertions.tool_called or assertions.tool_not_called or ""
            if tool_name:
                deterministic_results.append(check_tool_args_contain(step_result, tool_name, assertions.tool_args_contain))
        if assertions.response_contains:
            deterministic_results.append(check_response_contains(step_result, assertions.response_contains))
        if assertions.response_not_contains:
            deterministic_results.append(check_response_not_contains(step_result, assertions.response_not_contains))
        if assertions.response_matches:
            deterministic_results.append(check_response_matches(step_result, assertions.response_matches))
        if assertions.retries:
            deterministic_results.append(check_retries(step_result, assertions.retries.min, assertions.retries.max))

        results.extend(deterministic_results)
        if not all(result.passed for result in deterministic_results):
            return results

        semantic_results: List[AssertionResult] = []
        if assertions.response_sentiment:
            semantic_results.append(check_response_sentiment(step_result, assertions.response_sentiment, self.model))
        if assertions.injection_blocked is not None and assertions.injection_blocked:
            semantic_results.append(check_injection_blocked(step_result, self.model))
        if assertions.custom_judge:
            semantic_results.append(check_custom_judge(step_result, assertions.custom_judge, self.model))

        results.extend(semantic_results)
        return results
