from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import List, Optional

from ..adapters.base import AgentAdapter, StepResult, ToolCall
from ..assertions.engine import AssertionEngine, AssertionResult
from ..contract.schema import Contract, Gates, Scenario
from ..gates.engine import GateEngine, GateResult


@dataclass
class StepExecutionResult:
    step_index: int
    user_input: str
    step_result: StepResult
    assertion_results: List[AssertionResult]
    passed: bool


@dataclass
class ScenarioResult:
    scenario_name: str
    steps: List[StepExecutionResult]
    gate_results: List[GateResult]
    total_cost_usd: float
    total_latency_ms: float
    passed: bool
    failure_reason: Optional[str]


@dataclass
class ContractResult:
    contract_name: str
    scenarios: List[ScenarioResult]
    total_passed: int
    total_failed: int
    total_cost_usd: float
    total_time_seconds: float


class ScenarioRunner:
    def __init__(self, adapter: AgentAdapter, assertion_engine: AssertionEngine):
        self.adapter = adapter
        self.assertion_engine = assertion_engine
        self.gate_engine = GateEngine()

    async def run_contract(self, contract: Contract, tags: Optional[List[str]] = None) -> ContractResult:
        start = perf_counter()
        scenarios = contract.scenarios
        if tags:
            wanted = set(tags)
            scenarios = [scenario for scenario in scenarios if wanted.intersection(scenario.tags)]

        results: List[ScenarioResult] = []
        total_passed = 0
        total_failed = 0
        total_cost_usd = 0.0

        for scenario in scenarios:
            result = await self.run_scenario(scenario, contract.gates)
            results.append(result)
            total_cost_usd += result.total_cost_usd
            if result.passed:
                total_passed += 1
            else:
                total_failed += 1

        return ContractResult(
            contract_name=contract.name,
            scenarios=results,
            total_passed=total_passed,
            total_failed=total_failed,
            total_cost_usd=total_cost_usd,
            total_time_seconds=perf_counter() - start,
        )

    async def run_scenario(self, scenario: Scenario, contract_gates: Optional[Gates] = None) -> ScenarioResult:
        await self.adapter.reset()
        context: List[dict] = []
        step_results: List[StepExecutionResult] = []
        all_step_step_results: List[StepResult] = []
        total_cost_usd = 0.0
        total_latency_ms = 0.0
        failure_reason: Optional[str] = None

        if scenario.chaos is not None:
            # Chaos will be injected by a dedicated engine later.
            pass

        for index, step in enumerate(scenario.steps):
            step_result = await self.adapter.send_message(step.user, context)
            all_step_step_results.append(step_result)
            context.append({"role": "user", "content": step.user})
            context.append({"role": "assistant", "content": step_result.response})

            assertion_results = await self.assertion_engine.evaluate(step_result, step.expect)
            passed = all(result.passed for result in assertion_results)
            if not passed and failure_reason is None:
                failed = next((result for result in assertion_results if not result.passed), None)
                failure_reason = failed.message if failed else f"step {index} failed"

            step_results.append(
                StepExecutionResult(
                    step_index=index,
                    user_input=step.user,
                    step_result=step_result,
                    assertion_results=assertion_results,
                    passed=passed,
                )
            )
            total_cost_usd += step_result.token_usage.total_cost_usd
            total_latency_ms += step_result.latency_ms

        merged_gates = self.gate_engine.merge_gates(contract_gates, scenario.gates)
        gate_results = self.gate_engine.evaluate(
            {
                "total_tokens": sum(step.token_usage.input_tokens + step.token_usage.output_tokens for step in all_step_step_results),
                "total_cost_usd": total_cost_usd,
                "step_latencies": [step.latency_ms for step in all_step_step_results],
                "injection_results": [True for _ in step_results],
            },
            merged_gates,
        )
        if failure_reason is None:
            failing_gate = next((gate for gate in gate_results if not gate.passed), None)
            if failing_gate is not None:
                failure_reason = failing_gate.message

        passed = failure_reason is None and all(step.passed for step in step_results) and all(gate.passed for gate in gate_results)
        return ScenarioResult(
            scenario_name=scenario.name,
            steps=step_results,
            gate_results=gate_results,
            total_cost_usd=total_cost_usd,
            total_latency_ms=total_latency_ms,
            passed=passed,
            failure_reason=failure_reason,
        )
