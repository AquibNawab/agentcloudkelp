from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .recorder import Snapshot, ScenarioSnapshot, StepSnapshot


class SnapshotStore:
    def __init__(self, base_dir: str = ".agentcloudkelp/snapshots"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: Snapshot, label: str) -> Path:
        path = self.base_dir / f"{label}.json"
        path.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
        return path

    def load(self, label: str) -> Snapshot:
        path = self.base_dir / f"{label}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return Snapshot(
            version=data["version"],
            contract_name=data["contract_name"],
            recorded_at=data["recorded_at"],
            model=data["model"],
            framework=data["framework"],
            scenarios=[
                ScenarioSnapshot(
                    name=scenario["name"],
                    steps=[
                        StepSnapshot(
                            user_input=step["user_input"],
                            response=step["response"],
                            tool_calls=step["tool_calls"],
                            tokens=step["tokens"],
                            cost_usd=step["cost_usd"],
                            latency_ms=step["latency_ms"],
                        )
                        for step in scenario["steps"]
                    ],
                    total_cost_usd=scenario["total_cost_usd"],
                    total_latency_ms=scenario["total_latency_ms"],
                    passed=scenario["passed"],
                )
                for scenario in data["scenarios"]
            ],
        )

    def list(self) -> List[Dict]:
        items = []
        for path in sorted(self.base_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "label": path.stem,
                    "date": data.get("recorded_at"),
                    "contract": data.get("contract_name"),
                }
            )
        return items

    def delete(self, label: str) -> bool:
        path = self.base_dir / f"{label}.json"
        if not path.exists():
            return False
        path.unlink()
        return True
