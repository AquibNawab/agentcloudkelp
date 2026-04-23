from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolFailureDecision:
    injected: bool
    payload: Any


class ToolFailureInjector:
    def __init__(
        self,
        config=None,
        rng: Optional[random.Random] = None,
        *,
        tool: str | None = None,
        failure_type: str | None = None,
        probability: float | None = None,
        after_step: int | None = None,
        delay_ms: int | None = None,
    ):
        if config is None and tool is not None:
            from types import SimpleNamespace

            config = SimpleNamespace(
                tool_failures=[
                    SimpleNamespace(
                        tool=tool,
                        failure_type=failure_type or "timeout",
                        probability=1.0 if probability is None else probability,
                        after_step=after_step,
                        delay_ms=0 if delay_ms is None else delay_ms,
                    )
                ]
            )
        self.config = config
        self.rng = rng or random.Random()

    def should_inject(self, tool_name: str, step_index: int) -> bool:
        for failure in getattr(self.config, "tool_failures", []) or []:
            if failure.tool != tool_name:
                continue
            after_step = getattr(failure, "after_step", None)
            if after_step is not None and step_index < after_step:
                continue
            if self.rng.random() < float(failure.probability):
                return True
        return False

    async def inject(self, tool_name: str, step_index: int) -> ToolFailureDecision:
        matched = None
        for failure in getattr(self.config, "tool_failures", []) or []:
            if failure.tool == tool_name:
                after_step = getattr(failure, "after_step", None)
                if after_step is None or step_index >= after_step:
                    matched = failure
                    if self.rng.random() < float(failure.probability):
                        break
                    matched = None
        if matched is None:
            return ToolFailureDecision(False, None)

        failure_type = getattr(matched, "failure_type", None)
        if getattr(failure_type, "value", failure_type) == "timeout":
            delay = getattr(matched, "delay_ms", 0)
            await asyncio.sleep(delay / 1000.0)
            raise asyncio.TimeoutError(f"Injected timeout for tool '{tool_name}'")
        if getattr(failure_type, "value", failure_type) == "error_500":
            return ToolFailureDecision(True, {"error": "Internal server error", "status": 500})
        if getattr(failure_type, "value", failure_type) == "empty_response":
            return ToolFailureDecision(True, {})
        if getattr(failure_type, "value", failure_type) == "malformed_json":
            return ToolFailureDecision(True, "{invalid-json")
        return ToolFailureDecision(False, None)

    def maybe_encode(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("{invalid-json"):
            return value
        return json.loads(json.dumps(value))
