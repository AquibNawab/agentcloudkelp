from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_tokens: Optional[int] = None
    max_cost_usd: Optional[float] = None
    max_latency_ms: Optional[int] = None
    fail_on_exceed: bool = True


class FailureType(str, Enum):
    error = "error"
    timeout = "timeout"
    malformed = "malformed"


class MutationType(str, Enum):
    insert = "insert"
    replace = "replace"
    delete = "delete"


class ToolFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    failure_type: FailureType
    probability: float = Field(ge=0.0, le=1.0)


class LatencyInjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    delay_ms: int = Field(ge=0)


class InputMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MutationType
    payload: str


class ChaosConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_failures: List[ToolFailure] = Field(default_factory=list)
    latency_injection: Optional[LatencyInjection] = None
    input_mutations: List[InputMutation] = Field(default_factory=list)


class RetryBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int = Field(ge=0)
    max: int = Field(ge=0)

    @field_validator("max")
    @classmethod
    def validate_bounds(cls, value: int, info):
        min_value = info.data.get("min")
        if min_value is not None and value < min_value:
            raise ValueError("max must be greater than or equal to min")
        return value


class Assertions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_called: Optional[str] = None
    tool_not_called: Optional[str] = None
    tool_args_contain: Optional[Dict[str, Any]] = None
    response_contains: Optional[str] = None
    response_not_contains: Optional[str] = None
    response_sentiment: Optional[Literal["positive", "negative", "neutral", "confirmatory"]] = None
    response_matches: Optional[str] = None
    injection_blocked: Optional[bool] = None
    custom_judge: Optional[str] = None
    retries: Optional[RetryBounds] = None


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str
    expect: Assertions = Field(default_factory=Assertions)
    timeout: Optional[int] = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    tags: List[str] = Field(default_factory=list)
    chaos: Optional[ChaosConfig] = None
    steps: List[Step]
    gates: Optional[Gates] = None


class ContractConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "gpt-4o-mini"
    timeout: int = 30
    retry: int = 0


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    config: ContractConfig = Field(default_factory=ContractConfig)
    scenarios: List[Scenario]
    gates: Optional[Gates] = None
