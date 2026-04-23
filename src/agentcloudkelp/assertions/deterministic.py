from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .results import AssertionResult
from ..adapters.base import StepResult


def _find_tool_call(step_result: StepResult, tool_name: str) -> Optional[Dict[str, Any]]:
    for tool_call in step_result.tool_calls:
        if tool_call.name == tool_name:
            return {
                "name": tool_call.name,
                "arguments": tool_call.arguments,
                "result": tool_call.result,
                "duration_ms": tool_call.duration_ms,
            }
    return None


def check_tool_called(step_result: StepResult, expected_tool: str) -> AssertionResult:
    actual = [tool_call.name for tool_call in step_result.tool_calls]
    passed = expected_tool in actual
    message = f"expected tool '{expected_tool}' to be called"
    if passed:
        message = f"tool '{expected_tool}' was called"
    return AssertionResult(f"tool_called:{expected_tool}", passed, expected_tool, actual, message, 0.0)


def check_tool_not_called(step_result: StepResult, forbidden_tool: str) -> AssertionResult:
    actual = [tool_call.name for tool_call in step_result.tool_calls]
    passed = forbidden_tool not in actual
    message = f"expected tool '{forbidden_tool}' not to be called"
    if passed:
        message = f"tool '{forbidden_tool}' was not called"
    return AssertionResult(f"tool_not_called:{forbidden_tool}", passed, forbidden_tool, actual, message, 0.0)


def check_tool_args_contain(step_result: StepResult, tool_name: str, expected_args: Dict[str, Any]) -> AssertionResult:
    found = _find_tool_call(step_result, tool_name)
    actual = found["arguments"] if found else None
    passed = bool(found) and all(actual.get(key) == value for key, value in expected_args.items())
    message = f"expected tool '{tool_name}' arguments to contain {expected_args}"
    if found and passed:
        message = f"tool '{tool_name}' arguments contained {expected_args}"
    elif not found:
        message = f"tool '{tool_name}' was not called"
    return AssertionResult(f"tool_args_contain:{tool_name}", passed, expected_args, actual, message, 0.0)


def check_response_contains(step_result: StepResult, substring: str) -> AssertionResult:
    actual = step_result.response
    passed = substring in actual
    message = f"expected response to contain '{substring}'"
    if passed:
        message = f"response contained '{substring}'"
    return AssertionResult(f"response_contains:{substring}", passed, substring, actual, message, 0.0)


def check_response_not_contains(step_result: StepResult, substring: str) -> AssertionResult:
    actual = step_result.response
    passed = substring not in actual
    message = f"expected response not to contain '{substring}'"
    if passed:
        message = f"response did not contain '{substring}'"
    return AssertionResult(f"response_not_contains:{substring}", passed, substring, actual, message, 0.0)


def check_response_matches(step_result: StepResult, regex_pattern: str) -> AssertionResult:
    actual = step_result.response
    passed = re.search(regex_pattern, actual) is not None
    message = f"expected response to match /{regex_pattern}/"
    if passed:
        message = f"response matched /{regex_pattern}/"
    return AssertionResult(f"response_matches:{regex_pattern}", passed, regex_pattern, actual, message, 0.0)


def check_retries(step_result: StepResult, min_retries: int, max_retries: int) -> AssertionResult:
    actual = step_result.raw_trace.get("retries")
    passed = isinstance(actual, int) and min_retries <= actual <= max_retries
    message = f"expected retries to be between {min_retries} and {max_retries}"
    if passed:
        message = f"retries {actual} were within range {min_retries}..{max_retries}"
    return AssertionResult(f"retries:{min_retries}:{max_retries}", passed, {"min": min_retries, "max": max_retries}, actual, message, 0.0)
