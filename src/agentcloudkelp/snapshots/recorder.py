from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

from ..contract.schema import Contract
from ..runner.scenario_runner import ContractResult, ScenarioResult, StepExecutionResult


@dataclass
class StepSnapshot:
    user_input: str
    response: str
    tool_calls: List[Dict]
    tokens: Dict
    cost_usd: float
    latency_ms: float


@dataclass
class ScenarioSnapshot:
    name: str
    steps: List[StepSnapshot]
    total_cost_usd: float
    total_latency_ms: float
    passed: bool


@dataclass
class Snapshot:
    version: str = "1.0"
    contract_name: str = ""
    recorded_at: str = ""
    model: str = ""
    framework: str = ""
    scenarios: List[ScenarioSnapshot] = field(default_factory=list)


class SnapshotRecorder:
    def __init__(self, model: str = "gpt-4o-mini", framework: str = "function"):
        self.model = model
        self.framework = framework

    def record(self, contract_result: ContractResult, contract: Contract) -> Snapshot:
        scenarios: List[ScenarioSnapshot] = []
        for scenario_result in contract_result.scenarios:
            scenarios.append(self._scenario_snapshot(scenario_result))
        return Snapshot(
            contract_name=contract.name,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            model=self.model,
            framework=self.framework,
            scenarios=scenarios,
        )

    def _scenario_snapshot(self, scenario_result: ScenarioResult) -> ScenarioSnapshot:
        steps: List[StepSnapshot] = []
        for step_result in scenario_result.steps:
            steps.append(self._step_snapshot(step_result))
        return ScenarioSnapshot(
            name=scenario_result.scenario_name,
            steps=steps,
            total_cost_usd=scenario_result.total_cost_usd,
            total_latency_ms=scenario_result.total_latency_ms,
            passed=scenario_result.passed,
        )

    def _step_snapshot(self, step_result: StepExecutionResult) -> StepSnapshot:
        return StepSnapshot(
            user_input=step_result.user_input,
            response=step_result.step_result.response,
            tool_calls=[asdict(tool_call) for tool_call in step_result.step_result.tool_calls],
            tokens={
                "input": step_result.step_result.token_usage.input_tokens,
                "output": step_result.step_result.token_usage.output_tokens,
            },
            cost_usd=step_result.step_result.token_usage.total_cost_usd,
            latency_ms=step_result.step_result.latency_ms,
        )
