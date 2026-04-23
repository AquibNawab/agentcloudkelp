from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .errors import ContractNotFoundError, ContractValidationError
from .schema import Contract

ENV_PATTERN = re.compile(r"\$env\{([A-Z0-9_]+)\}")


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name not in os.environ:
                raise ContractValidationError(f"environment variable '{var_name}' is not set")
            return os.environ[var_name]

        return ENV_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_substitute_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _substitute_env(item) for key, item in value.items()}
    return value


def _build_line_map(node: yaml.Node, path: tuple[Any, ...] = ()) -> dict[tuple[Any, ...], int]:
    line_map: dict[tuple[Any, ...], int] = {}
    line_map[path] = node.start_mark.line + 1
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            key = key_node.value
            line_map.update(_build_line_map(value_node, path + (key,)))
    elif isinstance(node, yaml.SequenceNode):
        for index, item in enumerate(node.value):
            line_map.update(_build_line_map(item, path + (index,)))
    return line_map


def _format_validation_error(exc: ValidationError, line_map: dict[tuple[Any, ...], int]) -> ContractValidationError:
    first = exc.errors(include_url=False)[0]
    loc = list(first.get("loc", ()))
    line = line_map.get(tuple(item for item in loc if isinstance(item, (str, int))), 1)
    message = first.get("msg", "invalid contract")
    return ContractValidationError(message, line=line)


def load_contract(path: str | Path) -> Contract:
    contract_path = Path(path)
    if not contract_path.exists():
        raise ContractNotFoundError(str(contract_path))

    try:
        text = contract_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContractNotFoundError(str(contract_path)) from exc

    node = yaml.compose(text)
    if node is None:
        raise ContractValidationError("contract file is empty")

    line_map = _build_line_map(node)
    raw = yaml.safe_load(text)
    raw = _substitute_env(raw)

    try:
        return Contract.model_validate(raw)
    except ValidationError as exc:
        raise _format_validation_error(exc, line_map) from exc


def parse_contract(path: str | Path) -> Contract:
    return load_contract(path)
