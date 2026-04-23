from __future__ import annotations

import time
from typing import Any, Dict, List

from .base import AgentAdapter, StepResult, TokenUsage, ToolCall

try:  # pragma: no cover - optional dependency
    from agents import Runner
except ImportError:  # pragma: no cover - optional dependency
    Runner = None


class OpenAISDKAdapter(AgentAdapter):
    def __init__(self, agent: Any, adapter_name: str = "openai_sdk"):
        if Runner is None:
            raise ImportError(
                "openai-agents is not installed. Install it with `pip install openai-agents` to use OpenAISDKAdapter."
            )
        self.agent = agent
        self._name = adapter_name

    def _build_input(self, message: str, context: List[Dict]) -> List[Dict]:
        return [*context, {"role": "user", "content": message}]

    def _extract_tool_calls(self, result: Any) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []
        for item in getattr(result, "new_items", []) or []:
            item_type = getattr(item, "type", "") or item.__class__.__name__
            if "toolcall" not in item_type.lower():
                continue
            tool_calls.append(
                ToolCall(
                    name=str(getattr(item, "name", "") or getattr(item, "tool_name", "")),
                    arguments=getattr(item, "arguments", {}) or getattr(item, "input", {}) or {},
                    result=getattr(item, "result", None),
                    duration_ms=float(getattr(item, "duration_ms", 0.0) or 0.0),
                )
            )
        return tool_calls

    def _extract_response(self, result: Any) -> str:
        for attr in ("final_output", "output_text", "response", "output"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value:
                return value
        return str(result)

    def _extract_token_usage(self, result: Any) -> TokenUsage:
        input_tokens = 0
        output_tokens = 0
        for raw in getattr(result, "raw_responses", []) or []:
            usage = getattr(raw, "usage", None) or getattr(raw, "model_usage", None)
            if usage is None:
                continue
            input_tokens += int(getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0)
            output_tokens += int(getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0)
        return TokenUsage.from_usage(input_tokens, output_tokens, response=getattr(result, "model_dump", lambda: {})())

    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        start = time.perf_counter()
        runner = Runner
        result = await runner.run(self.agent, input=self._build_input(message, context))
        return StepResult(
            response=self._extract_response(result),
            tool_calls=self._extract_tool_calls(result),
            token_usage=self._extract_token_usage(result),
            latency_ms=(time.perf_counter() - start) * 1000.0,
            raw_trace=result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)},
        )

    async def reset(self) -> None:
        return None

    def name(self) -> str:
        return self._name
