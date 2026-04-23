from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List

from .base import AgentAdapter, StepResult


class FunctionAdapter(AgentAdapter):
    def __init__(self, handler: Callable[[str, List[Dict]], Awaitable[StepResult]], adapter_name: str = "function"):
        self._handler = handler
        self._name = adapter_name

    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        return await self._handler(message, context)

    async def reset(self) -> None:
        return None

    def name(self) -> str:
        return self._name
