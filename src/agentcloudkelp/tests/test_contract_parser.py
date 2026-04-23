from __future__ import annotations

from pathlib import Path

import pytest

from ..contract.errors import ContractNotFoundError, ContractValidationError
from ..contract.parser import load_contract


FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_contract_parsing():
    contract = load_contract(FIXTURES / "valid_contract.yaml")

    assert contract.name == "flight-booking-agent"
    assert contract.config.model == "gpt-4o-mini"
    assert len(contract.scenarios) == 2
    assert contract.gates.max_tokens == 1200

    scenario = contract.scenarios[0]
    assert scenario.chaos is not None
    assert scenario.chaos.tool_failures[0].tool == "search_flights"
    assert scenario.chaos.latency_injection.delay_ms == 250
    assert scenario.steps[0].expect.retries.max == 2


def test_missing_required_fields(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text(
        """
config:
  model: gpt-4o-mini
scenarios: []
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract(path)

    assert "line" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_invalid_enum_values(tmp_path):
    path = tmp_path / "invalid_enum.yaml"
    path.write_text(
        """
name: invalid-enum
scenarios:
  - name: bad
    steps:
      - user: hello
        expect:
          response_sentiment: ecstatic
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract(path)

    assert "line" in str(exc_info.value)
    assert "Input should be" in str(exc_info.value) or "valid" in str(exc_info.value)


def test_environment_variable_substitution(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKING_MODEL", "gpt-4.1-mini")
    path = tmp_path / "env.yaml"
    path.write_text(
        """
name: env-contract
config:
  model: $env{BOOKING_MODEL}
scenarios:
  - name: env scenario
    steps:
      - user: hello
""".strip(),
        encoding="utf-8",
    )

    contract = load_contract(path)

    assert contract.config.model == "gpt-4.1-mini"


def test_nested_scenario_validation(tmp_path):
    path = tmp_path / "nested_invalid.yaml"
    path.write_text(
        """
name: nested-invalid
scenarios:
  - name: bad scenario
    steps:
      - user: hello
        expect:
          retries:
            min: 3
            max: 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract(path)

    assert "line" in str(exc_info.value)
    assert "max must be greater than or equal to min" in str(exc_info.value)


def test_missing_file_raises_contract_not_found():
    with pytest.raises(ContractNotFoundError):
        load_contract(Path("/does/not/exist/contract.yaml"))
