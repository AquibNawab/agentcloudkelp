from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..adapters.base import AgentAdapter, StepResult, TokenUsage

from .input_mutator import InputMutator
from .latency import LatencyInjector
from .tool_failure import ToolFailureInjector


@dataclass
class ChaosWrappedAdapter(AgentAdapter):
    adapter: AgentAdapter
    input_mutator: InputMutator
    latency_injector: LatencyInjector
    tool_failure_injector: ToolFailureInjector
    step_index: int = 0

    async def send_message(self, message: str, context: List[dict]) -> StepResult:
        mutated_message = self.input_mutator.mutate(message)
        await self.latency_injector.inject("message")
        current_step = self.step_index
        self.step_index += 1
        try:
            decision = await self.tool_failure_injector.inject("message", current_step)
            if decision.injected:
                return StepResult(
                    response=str(decision.payload),
                    tool_calls=[],
                    token_usage=TokenUsage(0, 0, 0.0),
                    latency_ms=0.0,
                    raw_trace={"chaos": decision.payload},
                )
        except Exception:
            raise
        return await self.adapter.send_message(mutated_message, context)

    async def reset(self) -> None:
        self.step_index = 0
        await self.adapter.reset()

    def name(self) -> str:
        return self.adapter.name()


class ChaosInjector:
    def __init__(self, config):
        self.config = config

    def wrap_adapter(self, adapter: AgentAdapter) -> AgentAdapter:
        return ChaosWrappedAdapter(
            adapter=adapter,
            input_mutator=InputMutator(self.config),
            latency_injector=LatencyInjector(self.config),
            tool_failure_injector=ToolFailureInjector(self.config),
        )
