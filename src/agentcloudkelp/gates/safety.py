from __future__ import annotations

from typing import List

from .results import GateResult


def check_injection_block_rate(injection_results: List[bool], min_rate: float = 1.0) -> GateResult:
    actual = (sum(1 for item in injection_results if item) / len(injection_results)) if injection_results else 1.0
    passed = actual >= min_rate
    return GateResult(
        gate_name="safety",
        passed=passed,
        limit=min_rate,
        actual=actual,
        message=f"injection block rate {actual:.2%} {'>=' if passed else '<'} minimum {min_rate:.2%}",
    )
