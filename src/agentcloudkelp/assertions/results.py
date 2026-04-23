from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AssertionResult:
    name: str
    passed: bool
    expected: Any
    actual: Any
    message: str
    cost_usd: float
