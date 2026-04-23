from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List

from .recorder import Snapshot


@dataclass
class StepDiff:
    step_index: int
    response_similarity: float
    tool_calls_changed: bool
    tools_added: List[str]
    tools_removed: List[str]
    cost_change_pct: float
    latency_change_pct: float


@dataclass
class ScenarioDiff:
    scenario_name: str
    step_diffs: List[StepDiff]


@dataclass
class SnapshotDiff:
    has_drift: bool
    scenario_diffs: List[ScenarioDiff]


class SnapshotDiffer:
    def __init__(self, drift_threshold: float = 0.85):
        self.drift_threshold = drift_threshold

    def diff(self, baseline: Snapshot, current: Snapshot) -> SnapshotDiff:
        scenario_diffs: List[ScenarioDiff] = []
        drift = False
        baseline_map = {scenario.name: scenario for scenario in baseline.scenarios}
        for current_scenario in current.scenarios:
            base_scenario = baseline_map.get(current_scenario.name)
            if base_scenario is None:
                continue
            step_diffs: List[StepDiff] = []
            for index, current_step in enumerate(current_scenario.steps):
                if index >= len(base_scenario.steps):
                    break
                baseline_step = base_scenario.steps[index]
                similarity = SequenceMatcher(None, baseline_step.response, current_step.response).ratio()
                baseline_tools = {tool.get("name", "") for tool in baseline_step.tool_calls}
                current_tools = {tool.get("name", "") for tool in current_step.tool_calls}
                added = sorted(current_tools - baseline_tools)
                removed = sorted(baseline_tools - current_tools)
                cost_change = self._pct_change(baseline_step.cost_usd, current_step.cost_usd)
                latency_change = self._pct_change(baseline_step.latency_ms, current_step.latency_ms)
                step_diffs.append(
                    StepDiff(
                        step_index=index,
                        response_similarity=similarity,
                        tool_calls_changed=bool(added or removed),
                        tools_added=added,
                        tools_removed=removed,
                        cost_change_pct=cost_change,
                        latency_change_pct=latency_change,
                    )
                )
                if similarity < self.drift_threshold or added or removed:
                    drift = True
            scenario_diffs.append(ScenarioDiff(scenario_name=current_scenario.name, step_diffs=step_diffs))
        return SnapshotDiff(has_drift=drift, scenario_diffs=scenario_diffs)

    def _pct_change(self, baseline: float, current: float) -> float:
        if baseline == 0:
            return 0.0 if current == 0 else 100.0
        return ((current - baseline) / baseline) * 100.0
