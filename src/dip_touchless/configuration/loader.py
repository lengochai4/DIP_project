"""Configuration loading, merging, freezing, and hashing."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from .validation import validate_config


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    if loaded is None:
        return {}

    if not isinstance(loaded, dict):
        raise ValueError(
            f"top-level configuration must be a mapping: {path}"
        )

    return loaded


def _deep_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(dict(base))

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, Mapping)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )

    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)

    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _thaw(item)
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [_thaw(item) for item in value]

    return value


def _serialize_deterministically(
    config: Mapping[str, Any],
) -> str:
    return yaml.safe_dump(
        _thaw(config),
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )


@dataclass(frozen=True)
class ResolvedConfig:
    """Immutable resolved configuration and its reproducibility identity."""

    data: Mapping[str, Any]
    serialized_yaml: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(_thaw(self.data))


def resolve_config(
    defaults_path: str | Path,
    profile_path: str | Path | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> ResolvedConfig:
    """Resolve defaults < profile < explicit overrides."""

    merged = _load_yaml(Path(defaults_path))

    if profile_path is not None:
        profile = _load_yaml(Path(profile_path))
        merged = _deep_merge(merged, profile)

    if overrides:
        merged = _deep_merge(merged, overrides)

    validate_config(merged)

    frozen = _freeze(merged)
    serialized = _serialize_deterministically(frozen)

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    return ResolvedConfig(
        data=frozen,
        serialized_yaml=serialized,
        sha256=digest,
    )


def write_resolved_config(
    config: ResolvedConfig,
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        config.serialized_yaml,
        encoding="utf-8",
    )