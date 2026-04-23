from __future__ import annotations

from rich.console import Console
from rich.table import Table


class CLIReporter:
    def __init__(self, contract_name: str, framework: str, model: str):
        self.contract_name = contract_name
        self.framework = framework
        self.model = model
        self.console = Console()

    def report(self, result, verbose: bool = False) -> None:
        self.console.print("[bold]AgentCloudKelp v0.1.0 - Behavioral Contract Testing for AI Agents[/bold]")
        self.console.print(f"Contract: {self.contract_name} | Framework: {self.framework} | Model: {self.model}")

        table = Table(show_header=True, header_style="bold")
        table.add_column("SCENARIO")
        table.add_column("STEPS")
        table.add_column("ASSERTIONS")
        table.add_column("GATES")
        table.add_column("COST")
        table.add_column("TIME")
        table.add_column("STATUS")

        for scenario in result.scenarios:
            assertions = sum(len(step.assertion_results) for step in scenario.steps)
            status = "✅" if scenario.passed else "❌"
            if not scenario.passed and scenario.failure_reason:
                status += " ⚠️"
            table.add_row(
                scenario.scenario_name,
                str(len(scenario.steps)),
                str(assertions),
                str(len(scenario.gate_results)),
                f"${scenario.total_cost_usd:.4f}",
                f"{scenario.total_latency_ms / 1000:.2f}s",
                status,
            )
            if verbose and scenario.failure_reason:
                self.console.print(f"  [red]Failure:[/red] {scenario.failure_reason}")
                for step in scenario.steps:
                    if not step.passed:
                        self.console.print(f"    Step {step.step_index}: {step.user_input}")
                        self.console.print(f"    Response: {step.step_result.response}")
                        for assertion in step.assertion_results:
                            self.console.print(f"    - {assertion.name}: {assertion.message}")

        self.console.print(table)
        status = "✅" if result.total_failed == 0 else "❌"
        self.console.print(
            f"Results: {result.total_passed} passed, {result.total_failed} failed | Total cost: ${result.total_cost_usd:.4f} | Total time: {result.total_time_seconds:.2f}s {status}"
        )
