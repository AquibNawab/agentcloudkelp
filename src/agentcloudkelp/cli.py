from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import click

from .adapters.base import StepResult, TokenUsage, ToolCall
from .adapters.function import FunctionAdapter
from .adapters.http import HTTPAdapter
from .assertions.engine import AssertionEngine
from .contract.errors import ContractNotFoundError, ContractValidationError
from .contract.parser import load_contract
from .reporters.cli import CLIReporter
from .reporters.json_report import JSONReporter
from .reporters.junit import JUnitReporter
from .snapshots import SnapshotDiffer, SnapshotRecorder, SnapshotStore
from .runner.scenario_runner import ScenarioRunner


def _build_adapter(framework: str):
    framework = framework.lower()
    if framework == "function":
        async def echo_agent(message: str, context):
            return StepResult(
                response=message,
                tool_calls=[],
                token_usage=TokenUsage(0, 0, 0.0),
                latency_ms=0.0,
                raw_trace={},
            )

        return FunctionAdapter(echo_agent)
    if framework == "http":
        api_key = os.getenv("AGENTCLOUDKELP_API_KEY")
        if not api_key:
            raise click.ClickException("Missing API key. Set AGENTCLOUDKELP_API_KEY for the http adapter.")
        return HTTPAdapter("http://localhost:8000", headers={"Authorization": f"Bearer {api_key}"})
    raise click.ClickException(f"Adapter not found: {framework}. Available adapters: function, http")


def _parse_tags(tags: Optional[str]) -> Optional[list[str]]:
    if not tags:
        return None
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


@click.group()
def main():
    """AgentCloudKelp CLI."""


@main.group()
def snapshot():
    """Snapshot management commands."""


@main.command()
@click.option("--contract", "-c", default="kelp.yaml", show_default=True)
@click.option("--framework", "-f", default="function", show_default=True)
@click.option("--model", "-m", default="gpt-4o-mini", show_default=True)
@click.option("--tags", "-t", default=None)
@click.option("--reporter", "-r", type=click.Choice(["cli", "json", "junit"]), default="cli", show_default=True)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.option("--fail-fast", is_flag=True, default=False)
def run(contract, framework, model, tags, reporter, verbose, fail_fast):
    try:
        contract_obj = load_contract(contract)
    except ContractNotFoundError:
        raise click.ClickException(f"Contract not found: {contract}")
    except ContractValidationError as exc:
        raise click.ClickException(str(exc))

    adapter = _build_adapter(framework)
    engine = AssertionEngine(model=model)
    runner = ScenarioRunner(adapter, engine)
    tags_list = _parse_tags(tags)

    import asyncio

    result = asyncio.run(runner.run_contract(contract_obj, tags=tags_list))

    if reporter == "cli":
        CLIReporter(contract_name=contract_obj.name, framework=framework, model=model).report(result, verbose=verbose)
    elif reporter == "json":
        click.echo(JSONReporter().report(result))
    elif reporter == "junit":
        click.echo(JUnitReporter().report(result))

    if fail_fast and result.total_failed:
        raise click.ClickException("Run failed.")
    if result.total_failed:
        raise click.ClickException("One or more scenarios failed.")


@main.command()
def init():
    sample = Path("kelp.yaml")
    if sample.exists():
        raise click.ClickException("kelp.yaml already exists")
    sample.write_text(
        """name: flight-booking-agent
config:
  model: gpt-4o-mini
  timeout: 45
  retry: 2
scenarios:
  - name: book round trip with confirmation
    tags: [happy-path, booking]
    steps:
      - user: \"Find me a flight from NYC to SFO next Friday.\"
        expect:
          tool_called: search_flights
          response_contains: \"available flights\"
          response_sentiment: confirmatory
""",
        encoding="utf-8",
    )
    click.echo("Created kelp.yaml")


@main.command()
@click.option("--contract", "-c", required=True)
def validate(contract):
    try:
        load_contract(contract)
    except ContractNotFoundError:
        raise click.ClickException(f"Contract not found: {contract}")
    except ContractValidationError as exc:
        raise click.ClickException(str(exc))
    click.echo("Contract is valid.")


@snapshot.command("save")
@click.argument("label")
@click.option("--contract", "-c", default="kelp.yaml", show_default=True)
@click.option("--framework", "-f", default="function", show_default=True)
@click.option("--model", "-m", default="gpt-4o-mini", show_default=True)
def snapshot_save(label, contract, framework, model):
    import asyncio

    try:
        contract_obj = load_contract(contract)
    except ContractNotFoundError:
        raise click.ClickException(f"Contract not found: {contract}")
    except ContractValidationError as exc:
        raise click.ClickException(str(exc))

    adapter = _build_adapter(framework)
    result = asyncio.run(ScenarioRunner(adapter, AssertionEngine(model=model)).run_contract(contract_obj))
    snapshot_obj = SnapshotRecorder(model=model, framework=framework).record(result, contract_obj)
    path = SnapshotStore().save(snapshot_obj, label)
    click.echo(f"Saved snapshot to {path}")


@snapshot.command("diff")
@click.argument("label")
@click.option("--contract", "-c", default="kelp.yaml", show_default=True)
@click.option("--framework", "-f", default="function", show_default=True)
@click.option("--model", "-m", default="gpt-4o-mini", show_default=True)
def snapshot_diff(label, contract, framework, model):
    import asyncio

    try:
        contract_obj = load_contract(contract)
    except ContractNotFoundError:
        raise click.ClickException(f"Contract not found: {contract}")
    except ContractValidationError as exc:
        raise click.ClickException(str(exc))

    store = SnapshotStore()
    try:
        baseline = store.load(label)
    except FileNotFoundError:
        raise click.ClickException(f"Snapshot not found: {label}")
    adapter = _build_adapter(framework)
    current_result = asyncio.run(ScenarioRunner(adapter, AssertionEngine(model=model)).run_contract(contract_obj))
    current = SnapshotRecorder(model=model, framework=framework).record(current_result, contract_obj)
    diff = SnapshotDiffer().diff(baseline, current)
    click.echo(JSONReporter().report(diff))


@snapshot.command("list")
def snapshot_list():
    items = SnapshotStore().list()
    for item in items:
        click.echo(f"{item['label']} | {item['date']} | {item['contract']}")


@snapshot.command("delete")
@click.argument("label")
def snapshot_delete(label):
    deleted = SnapshotStore().delete(label)
    if not deleted:
        raise click.ClickException(f"Snapshot not found: {label}")
    click.echo(f"Deleted snapshot {label}")
