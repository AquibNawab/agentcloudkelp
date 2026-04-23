from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..contract.schema import Gates

from .cost import check_max_cost, check_max_tokens
from .latency import check_max_latency
from .results import GateResult
from .safety import check_injection_block_rate


class GateEngine:
    def merge_gates(self, contract_gates: Optional[Gates], scenario_gates: Optional[Gates]) -> Optional[Gates]:
        if contract_gates is None and scenario_gates is None:
            return None
        if contract_gates is None:
            return scenario_gates
        if scenario_gates is None:
            return contract_gates
        return Gates(
            max_tokens=scenario_gates.max_tokens if scenario_gates.max_tokens is not None else contract_gates.max_tokens,
            max_cost_usd=scenario_gates.max_cost_usd if scenario_gates.max_cost_usd is not None else contract_gates.max_cost_usd,
            max_latency_ms=scenario_gates.max_latency_ms if scenario_gates.max_latency_ms is not None else contract_gates.max_latency_ms,
            fail_on_exceed=scenario_gates.fail_on_exceed if scenario_gates.fail_on_exceed is not None else contract_gates.fail_on_exceed,
        )

    def evaluate(self, scenario_result_data: Dict, gates: Optional[Gates]) -> List[GateResult]:
        if gates is None:
            return []

        results: List[GateResult] = []
        total_tokens = int(scenario_result_data.get("total_tokens", 0))
        total_cost = float(scenario_result_data.get("total_cost_usd", 0.0))
        step_latencies = [float(v) for v in scenario_result_data.get("step_latencies", [])]
        injection_results = [bool(v) for v in scenario_result_data.get("injection_results", [])]

        if gates.max_tokens is not None:
            results.append(check_max_tokens(total_tokens, gates.max_tokens))
        if gates.max_cost_usd is not None:
            results.append(check_max_cost(total_cost, gates.max_cost_usd))
        if gates.max_latency_ms is not None:
            results.append(check_max_latency(step_latencies, gates.max_latency_ms))
        if injection_results:
            results.append(check_injection_block_rate(injection_results))
        return results
