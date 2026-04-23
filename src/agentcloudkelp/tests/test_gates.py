from __future__ import annotations

from ..contract.schema import Gates
from ..gates import check_injection_block_rate, check_max_cost, check_max_latency, check_max_tokens, GateEngine


def test_check_max_tokens():
    result = check_max_tokens(90, 100)
    assert result.passed is True
    assert result.gate_name == "cost"


def test_check_max_cost():
    result = check_max_cost(1.25, 2.0)
    assert result.passed is True


def test_check_max_latency_fails_if_any_step_exceeds():
    result = check_max_latency([100.0, 250.0, 80.0], 200)
    assert result.passed is False
    assert result.actual == 250.0


def test_check_injection_block_rate():
    result = check_injection_block_rate([True, True, False], min_rate=0.5)
    assert result.passed is True
    assert round(result.actual, 2) == 0.67


def test_gate_merge_logic():
    engine = GateEngine()
    contract = Gates(max_tokens=100, max_cost_usd=2.0, max_latency_ms=500, fail_on_exceed=True)
    scenario = Gates(max_tokens=None, max_cost_usd=1.5, max_latency_ms=None, fail_on_exceed=False)

    merged = engine.merge_gates(contract, scenario)

    assert merged.max_tokens == 100
    assert merged.max_cost_usd == 1.5
    assert merged.max_latency_ms == 500
    assert merged.fail_on_exceed is False


def test_gate_engine_evaluate():
    engine = GateEngine()
    gates = Gates(max_tokens=100, max_cost_usd=2.0, max_latency_ms=500)
    results = engine.evaluate(
        {
            "total_tokens": 90,
            "total_cost_usd": 1.25,
            "step_latencies": [100.0, 200.0],
            "injection_results": [True, True],
        },
        gates,
    )

    assert [result.passed for result in results] == [True, True, True, True]
