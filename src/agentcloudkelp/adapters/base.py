from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from litellm import completion_cost
except Exception:  # pragma: no cover - optional dependency
    completion_cost = None


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    result: Optional[Any]
    duration_ms: float


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_cost_usd: float = field(default=0.0)

    @classmethod
    def from_usage(
        cls,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
        response: Any | None = None,
    ) -> "TokenUsage":
        if completion_cost is None:
            cost = 0.0
        else:
            payload = response if response is not None else {
                "model": model,
                "usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens},
            }
            try:
                cost = float(completion_cost(payload))
            except Exception:
                cost = 0.0
        return cls(input_tokens=input_tokens, output_tokens=output_tokens, total_cost_usd=cost)


@dataclass
class StepResult:
    response: str
    tool_calls: List[ToolCall]
    token_usage: TokenUsage
    latency_ms: float
    raw_trace: Dict[str, Any]


class AgentAdapter(ABC):
    @abstractmethod
    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        raise NotImplementedError

    @abstractmethod
    async def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError
