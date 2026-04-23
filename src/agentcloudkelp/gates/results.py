from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    limit: Any
    actual: Any
    message: str
