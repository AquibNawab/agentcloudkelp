from __future__ import annotations

import pytest

from ..adapters.base import StepResult, TokenUsage, ToolCall
from ..adapters.function import FunctionAdapter
from ..assertions.engine import AssertionEngine
from ..contract.schema import Assertions, Contract, ContractConfig, Gates, Scenario, Step
from ..runner.scenario_runner import ScenarioRunner


def build_step_result(response: str, tool_name: str | None = None, retries: int = 0) -> StepResult:
    tool_calls = []
    if tool_name:
        tool_calls.append(ToolCall(name=tool_name, arguments={"from": "NYC"}, result={"ok": True}, duration_ms=12.0))
    return StepResult(
        response=response,
        tool_calls=tool_calls,
        token_usage=TokenUsage(10, 5, 0.03),
        latency_ms=25.0,
        raw_trace={"retries": retries},
    )


@pytest.mark.asyncio
async def test_run_scenario_with_function_adapter(monkeypatch):
    async def mock_agent(message: str, context):
        if "search" in message.lower():
            return build_step_result("I found flights and will confirm.", "search_flights", retries=1)
        return build_step_result("Booking confirmed.")

    adapter = FunctionAdapter(mock_agent)
    engine = AssertionEngine()
    runner = ScenarioRunner(adapter, engine)

    scenario = Scenario(
        name="happy path",
        steps=[
            Step(
                user="Search flights from NYC to SFO",
                expect=Assertions(
                    tool_called="search_flights",
                    response_contains="found flights",
                    retries={"min": 0, "max": 2},
                ),
            ),
            Step(
                user="Confirm booking",
                expect=Assertions(response_contains="confirmed"),
            ),
        ],
        gates=Gates(max_cost_usd=1.0, max_latency_ms=1000, max_tokens=100),
    )

    result = await runner.run_scenario(scenario)

    assert result.passed is True
    assert len(result.steps) == 2
    assert result.steps[0].passed is True
    assert result.steps[1].passed is True
    assert result.gate_results and all(gate.passed for gate in result.gate_results)


@pytest.mark.asyncio
async def test_run_contract_filters_by_tags(monkeypatch):
    calls = []

    async def mock_agent(message: str, context):
        calls.append(message)
        return build_step_result("OK")

    adapter = FunctionAdapter(mock_agent)
    runner = ScenarioRunner(adapter, AssertionEngine())

    contract = Contract(
        name="tagged-contract",
        config=ContractConfig(),
        scenarios=[
            Scenario(name="run me", tags=["smoke"], steps=[Step(user="hello")]),
            Scenario(name="skip me", tags=["regression"], steps=[Step(user="bye")]),
        ],
        gates=None,
    )

    result = await runner.run_contract(contract, tags=["smoke"])

    assert len(result.scenarios) == 1
    assert result.scenarios[0].scenario_name == "run me"
    assert calls == ["hello"]
    assert result.total_passed == 1
    assert result.total_failed == 0
