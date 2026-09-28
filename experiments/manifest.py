"""Experiment manifest loading and validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from experiments.run_replay import PROFILE_NAMES


class ManifestValidationError(ValueError):
    """Raised when an experiment manifest is invalid."""


@dataclass(frozen=True)
class ManifestTrial:
    trial_id: str
    source: Path


@dataclass(frozen=True)
class ExperimentManifest:
    schema_version: str
    experiment_id: str
    profiles: tuple[str, ...]
    model: Path
    trials: tuple[ManifestTrial, ...]
    warmup_s: float
    analysis_start_s: float
    analysis_end_s: float | None
    primary_metric: str
    planned_comparisons: tuple[
        tuple[str, str], ...
    ]
    exclusion_rules: tuple[str, ...]


def _require_nonempty_string(
    value: Any,
    *,
    name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ManifestValidationError(
            f"{name} must be a non-empty string"
        )

    return value.strip()


def _require_non_negative_number(
    value: Any,
    *,
    name: str,
) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0.0
    ):
        raise ManifestValidationError(
            f"{name} must be finite and non-negative"
        )

    return float(value)


def _resolve_path(
    value: Any,
    *,
    name: str,
    base_dir: Path,
) -> Path:
    text = _require_nonempty_string(
        value,
        name=name,
    )

    path = Path(text)

    if not path.is_absolute():
        path = base_dir / path

    return path.resolve()


def load_experiment_manifest(
    path: str | Path,
) -> ExperimentManifest:
    manifest_path = Path(path)

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"experiment manifest not found: "
            f"{manifest_path}"
        )

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        loaded = yaml.safe_load(file)

    if not isinstance(loaded, Mapping):
        raise ManifestValidationError(
            "manifest top level must be a mapping"
        )

    base_dir = manifest_path.parent.resolve()

    schema_version = _require_nonempty_string(
        loaded.get("schema_version"),
        name="schema_version",
    )

    if schema_version != "1":
        raise ManifestValidationError(
            "schema_version must be '1'"
        )

    experiment_id = _require_nonempty_string(
        loaded.get("experiment_id"),
        name="experiment_id",
    )

    profile_values = loaded.get("profiles")

    if (
        not isinstance(profile_values, list)
        or not profile_values
    ):
        raise ManifestValidationError(
            "profiles must be a non-empty list"
        )

    profiles = tuple(
        _require_nonempty_string(
            value,
            name="profile",
        ).lower()
        for value in profile_values
    )

    if len(set(profiles)) != len(profiles):
        raise ManifestValidationError(
            "profiles must be unique"
        )

    unsupported = (
        set(profiles)
        - set(PROFILE_NAMES)
    )

    if unsupported:
        raise ManifestValidationError(
            "unsupported profiles: "
            + ", ".join(sorted(unsupported))
        )

    model = _resolve_path(
        loaded.get("model"),
        name="model",
        base_dir=base_dir,
    )

    warmup_s = _require_non_negative_number(
        loaded.get("warmup_s"),
        name="warmup_s",
    )

    analysis_window = loaded.get(
        "analysis_window"
    )

    if not isinstance(
        analysis_window,
        Mapping,
    ):
        raise ManifestValidationError(
            "analysis_window must be a mapping"
        )

    analysis_start_s = (
        _require_non_negative_number(
            analysis_window.get("start_s"),
            name="analysis_window.start_s",
        )
    )

    if analysis_start_s < warmup_s:
        raise ManifestValidationError(
            "analysis_window.start_s must be "
            "greater than or equal to warmup_s"
        )

    end_value = analysis_window.get(
        "end_s"
    )

    if end_value is None:
        analysis_end_s = None
    else:
        analysis_end_s = (
            _require_non_negative_number(
                end_value,
                name="analysis_window.end_s",
            )
        )

        if analysis_end_s <= analysis_start_s:
            raise ManifestValidationError(
                "analysis_window.end_s must be "
                "greater than start_s"
            )

    primary_metric = (
        _require_nonempty_string(
            loaded.get("primary_metric"),
            name="primary_metric",
        )
    )

    trial_values = loaded.get("trials")

    if (
        not isinstance(trial_values, list)
        or not trial_values
    ):
        raise ManifestValidationError(
            "trials must be a non-empty list"
        )

    trials: list[ManifestTrial] = []

    for index, trial_value in enumerate(
        trial_values
    ):
        if not isinstance(
            trial_value,
            Mapping,
        ):
            raise ManifestValidationError(
                f"trials[{index}] must be a mapping"
            )

        trial_id = _require_nonempty_string(
            trial_value.get("trial_id"),
            name=f"trials[{index}].trial_id",
        )

        source = _resolve_path(
            trial_value.get("source"),
            name=f"trials[{index}].source",
            base_dir=base_dir,
        )

        trials.append(
            ManifestTrial(
                trial_id=trial_id,
                source=source,
            )
        )

    trial_ids = [
        trial.trial_id
        for trial in trials
    ]

    if len(set(trial_ids)) != len(
        trial_ids
    ):
        raise ManifestValidationError(
            "trial_id values must be unique"
        )

    comparison_values = loaded.get(
        "planned_comparisons"
    )

    if (
        not isinstance(comparison_values, list)
        or not comparison_values
    ):
        raise ManifestValidationError(
            "planned_comparisons must be "
            "a non-empty list"
        )

    comparisons: list[
        tuple[str, str]
    ] = []

    for index, comparison in enumerate(
        comparison_values
    ):
        if (
            not isinstance(comparison, list)
            or len(comparison) != 2
        ):
            raise ManifestValidationError(
                f"planned_comparisons[{index}] "
                "must contain two profiles"
            )

        left = _require_nonempty_string(
            comparison[0],
            name="comparison profile",
        ).lower()

        right = _require_nonempty_string(
            comparison[1],
            name="comparison profile",
        ).lower()

        if (
            left not in profiles
            or right not in profiles
        ):
            raise ManifestValidationError(
                "planned comparison profiles "
                "must be present in profiles"
            )

        if left == right:
            raise ManifestValidationError(
                "planned comparison profiles "
                "must be distinct"
            )

        comparisons.append(
            (left, right)
        )

    exclusion_values = loaded.get(
        "exclusion_rules"
    )

    if (
        not isinstance(exclusion_values, list)
        or not exclusion_values
    ):
        raise ManifestValidationError(
            "exclusion_rules must be "
            "a non-empty list"
        )

    exclusion_rules = tuple(
        _require_nonempty_string(
            value,
            name="exclusion rule",
        )
        for value in exclusion_values
    )

    return ExperimentManifest(
        schema_version=schema_version,
        experiment_id=experiment_id,
        profiles=profiles,
        model=model,
        trials=tuple(trials),
        warmup_s=warmup_s,
        analysis_start_s=analysis_start_s,
        analysis_end_s=analysis_end_s,
        primary_metric=primary_metric,
        planned_comparisons=tuple(
            comparisons
        ),
        exclusion_rules=exclusion_rules,
    )
