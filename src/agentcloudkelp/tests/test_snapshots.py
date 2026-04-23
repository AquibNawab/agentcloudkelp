from __future__ import annotations

import json
from pathlib import Path

from ..snapshots import ScenarioSnapshot, SnapshotDiffer, SnapshotRecorder, SnapshotStore, StepSnapshot
from ..snapshots.recorder import Snapshot


def test_snapshot_store_save_load_list_delete(tmp_path):
    store = SnapshotStore(base_dir=str(tmp_path))
    snapshot = Snapshot(
        contract_name="demo",
        recorded_at="2026-04-23T00:00:00+00:00",
        model="gpt-4o-mini",
        framework="function",
        scenarios=[],
    )

    path = store.save(snapshot, "baseline")
    assert path.exists()

    loaded = store.load("baseline")
    assert loaded.contract_name == "demo"
    assert store.list()[0]["label"] == "baseline"
    assert store.delete("baseline") is True
    assert store.delete("baseline") is False


def test_snapshot_differ_detects_drift():
    baseline = Snapshot(
        contract_name="demo",
        recorded_at="2026-04-23T00:00:00+00:00",
        model="gpt-4o-mini",
        framework="function",
        scenarios=[
            ScenarioSnapshot(
                name="scenario",
                steps=[
                    StepSnapshot(
                        user_input="hello",
                        response="booking confirmed",
                        tool_calls=[{"name": "search_flights", "arguments": {}, "result": {}, "duration_ms": 1.0}],
                        tokens={"input": 1, "output": 1},
                        cost_usd=0.1,
                        latency_ms=100.0,
                    )
                ],
                total_cost_usd=0.1,
                total_latency_ms=100.0,
                passed=True,
            )
        ],
    )
    current = Snapshot(
        contract_name="demo",
        recorded_at="2026-04-23T00:00:00+00:00",
        model="gpt-4o-mini",
        framework="function",
        scenarios=[
            ScenarioSnapshot(
                name="scenario",
                steps=[
                    StepSnapshot(
                        user_input="hello",
                        response="totally different response",
                        tool_calls=[{"name": "book_flight", "arguments": {}, "result": {}, "duration_ms": 1.0}],
                        tokens={"input": 1, "output": 1},
                        cost_usd=0.2,
                        latency_ms=300.0,
                    )
                ],
                total_cost_usd=0.2,
                total_latency_ms=300.0,
                passed=False,
            )
        ],
    )

    diff = SnapshotDiffer().diff(baseline, current)
    assert diff.has_drift is True
    assert diff.scenario_diffs[0].step_diffs[0].tool_calls_changed is True
    assert diff.scenario_diffs[0].step_diffs[0].response_similarity < 0.85


def test_snapshot_recorder_records_contract_result():
    from ..adapters.base import StepResult, TokenUsage, ToolCall
    from ..runner.scenario_runner import ContractResult, ScenarioResult, StepExecutionResult
    from ..contract.schema import Contract

    step_result = StepResult(
        response="ok",
        tool_calls=[ToolCall(name="search_flights", arguments={}, result={}, duration_ms=1.0)],
        token_usage=TokenUsage(1, 2, 0.01),
        latency_ms=10.0,
        raw_trace={},
    )
    contract_result = ContractResult(
        contract_name="demo",
        scenarios=[
            ScenarioResult(
                scenario_name="scenario",
                steps=[StepExecutionResult(0, "hello", step_result, [], True)],
                gate_results=[],
                total_cost_usd=0.01,
                total_latency_ms=10.0,
                passed=True,
                failure_reason=None,
            )
        ],
        total_passed=1,
        total_failed=0,
        total_cost_usd=0.01,
        total_time_seconds=0.1,
    )
    snapshot = SnapshotRecorder().record(contract_result, Contract(name="demo", scenarios=[]))
    assert snapshot.contract_name == "demo"
    assert snapshot.scenarios[0].steps[0].response == "ok"
