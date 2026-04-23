from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .base import AgentAdapter, StepResult, TokenUsage, ToolCall

try:  # pragma: no cover - optional dependency
    from crewai import Agent, Crew, Task
except ImportError:  # pragma: no cover - optional dependency
    Agent = Crew = Task = None


class CrewAIAdapter(AgentAdapter):
    def __init__(
        self,
        agent: Any,
        crew: Any = None,
        task_description: str = "Respond to the user message using the provided context.",
        adapter_name: str = "crewai",
    ):
        if Crew is None or Agent is None or Task is None:
            raise ImportError(
                "CrewAI is not installed. Install it with `pip install crewai` to use CrewAIAdapter."
            )
        self.agent = agent
        self.crew = crew
        self.task_description = task_description
        self._name = adapter_name

    def _build_context_text(self, message: str, context: List[Dict]) -> str:
        lines = [f"User: {message}"]
        for item in context:
            role = item.get("role", "user")
            content = item.get("content", "")
            lines.append(f"{role.title()}: {content}")
        return "\n".join(lines)

    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        start = time.perf_counter()
        prompt = self._build_context_text(message, context)
        task = Task(description=f"{self.task_description}\n\n{prompt}", agent=self.agent)
        crew = self.crew or Crew(agents=[self.agent], tasks=[task], verbose=False)

        tool_calls: List[ToolCall] = []
        callback = self._callback_factory(tool_calls)
        if hasattr(crew, "callbacks") and crew.callbacks is not None:
            crew.callbacks = list(crew.callbacks) + [callback]
        else:
            setattr(crew, "callbacks", [callback])

        result = crew.kickoff()
        response = self._extract_final_output(result)
        raw_trace = self._serialize_result(result)
        latency_ms = (time.perf_counter() - start) * 1000.0
        token_usage = self._extract_token_usage(result)
        return StepResult(
            response=response,
            tool_calls=tool_calls,
            token_usage=token_usage,
            latency_ms=latency_ms,
            raw_trace=raw_trace,
        )

    def _callback_factory(self, tool_calls: List[ToolCall]):
        def callback(event):
            tool_name = getattr(event, "tool_name", None) or getattr(event, "name", None)
            if not tool_name:
                return
            arguments = getattr(event, "tool_input", None) or getattr(event, "arguments", {}) or {}
            result = getattr(event, "result", None)
            duration_ms = float(getattr(event, "duration_ms", 0.0) or 0.0)
            tool_calls.append(
                ToolCall(name=str(tool_name), arguments=dict(arguments), result=result, duration_ms=duration_ms)
            )

        return callback

    def _extract_final_output(self, result: Any) -> str:
        for attr in ("raw", "output", "final_output", "result"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value:
                return value
        return str(result)

    def _extract_token_usage(self, result: Any) -> TokenUsage:
        usage = getattr(result, "usage", None) or getattr(result, "token_usage", None)
        if usage is None:
            return TokenUsage.from_usage(0, 0, response=getattr(result, "model_dump", lambda: {})())
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0)
        return TokenUsage.from_usage(input_tokens, output_tokens, response=getattr(result, "model_dump", lambda: {})())

    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        return {"result": str(result)}

    async def reset(self) -> None:
        return None

    def name(self) -> str:
        return self._name
