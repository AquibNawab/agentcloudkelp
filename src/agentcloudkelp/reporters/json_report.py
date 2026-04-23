from __future__ import annotations

import json
from dataclasses import asdict


class JSONReporter:
    def report(self, result) -> str:
        return json.dumps(asdict(result), indent=2, default=str)
