from __future__ import annotations

from .results import GateResult


def check_max_tokens(total_tokens: int, max_tokens: int) -> GateResult:
    passed = total_tokens <= max_tokens
    return GateResult(
        gate_name="cost",
        passed=passed,
        limit=max_tokens,
        actual=total_tokens,
        message=f"total tokens {total_tokens} {'<=' if passed else '>'} limit {max_tokens}",
    )


def check_max_cost(total_cost_usd: float, max_cost_usd: float) -> GateResult:
    passed = total_cost_usd <= max_cost_usd
    return GateResult(
        gate_name="cost",
        passed=passed,
        limit=max_cost_usd,
        actual=total_cost_usd,
        message=f"total cost ${total_cost_usd:.4f} {'<=' if passed else '>'} limit ${max_cost_usd:.4f}",
    )
