from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class LatencyDecision:
    delay_ms: int


class LatencyInjector:
    def __init__(self, config):
        self.config = config

    async def inject(self, tool_name: str) -> LatencyDecision | None:
        latency = getattr(self.config, "latency_injection", None)
        if latency is None or latency.tool != tool_name:
            return None
        await asyncio.sleep(latency.delay_ms / 1000.0)
        return LatencyDecision(delay_ms=latency.delay_ms)
