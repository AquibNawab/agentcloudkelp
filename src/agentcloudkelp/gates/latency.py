from __future__ import annotations

from typing import List

from .results import GateResult


def check_max_latency(step_latencies: List[float], max_latency_ms: int) -> GateResult:
    actual = max(step_latencies) if step_latencies else 0.0
    passed = all(latency <= max_latency_ms for latency in step_latencies)
    return GateResult(
        gate_name="latency",
        passed=passed,
        limit=max_latency_ms,
        actual=actual,
        message=f"max step latency {actual:.2f} {'<=' if passed else '>'} limit {max_latency_ms:.2f}",
    )
