from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .base import AgentAdapter, StepResult, TokenUsage, ToolCall

try:  # pragma: no cover - optional dependency
    from langgraph.graph import CompiledGraph, StateGraph
except ImportError:  # pragma: no cover - optional dependency
    CompiledGraph = StateGraph = None


class LangGraphAdapter(AgentAdapter):
    def __init__(self, graph: Any, input_key: str = "messages", adapter_name: str = "langgraph"):
        if CompiledGraph is None or StateGraph is None:
            raise ImportError(
                "LangGraph is not installed. Install it with `pip install langgraph` to use LangGraphAdapter."
            )
        self.graph = graph
        self.input_key = input_key
        self._name = adapter_name

    def _build_messages(self, message: str, context: List[Dict]) -> List[Dict]:
        return [*context, {"role": "user", "content": message}]

    def _extract_tool_calls(self, result: Any) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []
        messages = []
        if isinstance(result, dict):
            messages = result.get("messages", [])
        elif hasattr(result, "messages"):
            messages = getattr(result, "messages")
        for msg in messages or []:
            tool_calls.extend(self._tool_calls_from_message(msg))
        return tool_calls

    def _tool_calls_from_message(self, message: Any) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []
        additional = getattr(message, "additional_kwargs", {}) or {}
        tool_calls_data = additional.get("tool_calls") or []
        for item in tool_calls_data:
            tool_calls.append(
                ToolCall(
                    name=str(item.get("name", "")),
                    arguments=item.get("args", {}) or item.get("arguments", {}) or {},
                    result=item.get("result"),
                    duration_ms=float(item.get("duration_ms", 0.0) or 0.0),
                )
            )
        return tool_calls

    def _extract_response(self, result: Any) -> str:
        if isinstance(result, dict):
            for key in ("response", "output", "final", "answer"):
                if isinstance(result.get(key), str):
                    return result[key]
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = getattr(last, "content", None)
                if isinstance(content, str):
                    return content
        return str(result)

    def _extract_token_usage(self, result: Any) -> TokenUsage:
        input_tokens = 0
        output_tokens = 0
        if isinstance(result, dict):
            messages = result.get("messages", [])
        else:
            messages = getattr(result, "messages", [])
        for message in messages or []:
            usage = getattr(message, "usage_metadata", None)
            if usage:
                input_tokens += int(getattr(usage, "input_tokens", 0) or usage.get("input_tokens", 0) if isinstance(usage, dict) else 0)
                output_tokens += int(getattr(usage, "output_tokens", 0) or usage.get("output_tokens", 0) if isinstance(usage, dict) else 0)
        return TokenUsage.from_usage(input_tokens, output_tokens, response=getattr(result, "model_dump", lambda: {})())

    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        start = time.perf_counter()
        payload = {self.input_key: self._build_messages(message, context)}
        graph = self.graph

        if hasattr(graph, "ainvoke"):
            result = await graph.ainvoke(payload)
        elif hasattr(graph, "invoke"):
            result = graph.invoke(payload)
        elif hasattr(graph, "astream"):
            chunks = []
            async for chunk in graph.astream(payload):
                chunks.append(chunk)
            result = chunks[-1] if chunks else {}
        else:
            raise TypeError("Graph object must implement invoke, ainvoke, or astream")

        return StepResult(
            response=self._extract_response(result),
            tool_calls=self._extract_tool_calls(result),
            token_usage=self._extract_token_usage(result),
            latency_ms=(time.perf_counter() - start) * 1000.0,
            raw_trace=result if isinstance(result, dict) else {"result": str(result)},
        )

    async def reset(self) -> None:
        return None

    def name(self) -> str:
        return self._name
