from __future__ import annotations

from typing import Any


class GitHubReporter:
    def format_pr_comment(self, result) -> str:
        lines = [
            "## 🔍 AgentCloudKelp Results",
            "",
            "| Scenario | Steps | Assertions | Gates | Cost | Status |",
            "|---|---:|---:|:---:|---:|:---:|",
        ]

        failed_names = []
        for scenario in result.scenarios:
            step_total = len(scenario.steps)
            step_passed = sum(1 for step in scenario.steps if step.passed)
            assertion_total = sum(len(step.assertion_results) for step in scenario.steps)
            assertion_passed = sum(
                1 for step in scenario.steps for assertion in step.assertion_results if assertion.passed
            )
            gates_ok = "✅" if all(gate.passed for gate in scenario.gate_results) else "❌"
            status = "✅ Pass" if scenario.passed else "❌ Fail"
            if not scenario.passed:
                failed_names.append(scenario.scenario_name)
            lines.append(
                f"| {scenario.scenario_name} | {step_passed}/{step_total} | {assertion_passed}/{assertion_total} | {gates_ok} | ${scenario.total_cost_usd:.3f} | {status} |"
            )

        lines.append("")
        if failed_names:
            lines.append(f"**Failed:** `{', '.join(failed_names)}`")
            for scenario in result.scenarios:
                if not scenario.passed:
                    for step in scenario.steps:
                        if not step.passed:
                            failing = next((a for a in step.assertion_results if not a.passed), None)
                            if failing is not None:
                                lines.append(
                                    f"→ Step {step.step_index + 1}: expected {failing.name}={failing.expected}, got {failing.actual}"
                                )
                                break

        lines.append("")
        lines.append(
            f"**Summary:** {result.total_passed} passed, {result.total_failed} failed | Total: ${result.total_cost_usd:.3f}"
        )
        return "\n".join(lines)
