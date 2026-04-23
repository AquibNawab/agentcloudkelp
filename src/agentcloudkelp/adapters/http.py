from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import httpx

from .base import AgentAdapter, StepResult, TokenUsage, ToolCall


class HTTPAdapter(AgentAdapter):
    def __init__(
        self,
        base_url: str,
        headers: Optional[Mapping[str, str]] = None,
        field_mappings: Optional[Mapping[str, str]] = None,
        timeout: float = 30.0,
        adapter_name: str = "http",
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = dict(headers or {})
        self.field_mappings = {
            "response": "response",
            "tool_calls": "tool_calls",
            "input_tokens": "input_tokens",
            "output_tokens": "output_tokens",
            "latency_ms": "latency_ms",
            "raw_trace": "raw_trace",
            **dict(field_mappings or {}),
        }
        self.timeout = timeout
        self._name = adapter_name

    async def send_message(self, message: str, context: List[Dict]) -> StepResult:
        payload = {"message": message, "context": context}
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"HTTP adapter timeout calling {self.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text
            raise RuntimeError(f"HTTP adapter request failed with status {status}: {body}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"HTTP adapter request error: {exc}") from exc

        data = response.json()
        return self._parse_result(data)

    def _parse_result(self, data: Dict[str, Any]) -> StepResult:
        response_text = str(data.get(self.field_mappings["response"], ""))
        raw_trace = data.get(self.field_mappings["raw_trace"], data)
        tool_calls_payload = data.get(self.field_mappings["tool_calls"], []) or []
        tool_calls = [
            ToolCall(
                name=item.get("name", ""),
                arguments=item.get("arguments", {}) or {},
                result=item.get("result"),
                duration_ms=float(item.get("duration_ms", 0.0)),
            )
            for item in tool_calls_payload
        ]
        input_tokens = int(data.get(self.field_mappings["input_tokens"], 0) or 0)
        output_tokens = int(data.get(self.field_mappings["output_tokens"], 0) or 0)
        latency_ms = float(data.get(self.field_mappings["latency_ms"], 0.0) or 0.0)
        token_usage = TokenUsage.from_usage(input_tokens, output_tokens, response=data)
        return StepResult(
            response=response_text,
            tool_calls=tool_calls,
            token_usage=token_usage,
            latency_ms=latency_ms,
            raw_trace=raw_trace if isinstance(raw_trace, dict) else {"raw_trace": raw_trace},
        )

    async def reset(self) -> None:
        return None

    def name(self) -> str:
        return self._name
