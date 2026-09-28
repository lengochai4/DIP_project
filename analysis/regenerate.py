"""Regenerate descriptive experiment tables and plots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from analysis.metrics import (
    MetricCalculationError,
    MetricResult,
    common_landmark_frame_ids,
    radial_rms_jitter_comparison,
    trajectory_deviation_comparison,
    valid_hand_observation_rate,
)
from analysis.run_loader import (
    RunArtifacts,
    load_run_artifacts,
)


class RegenerationError(ValueError):
    """Raised when a batch cannot be regenerated safely."""


@dataclass(frozen=True)
class IndexedRun:
    experiment_id: str
    trial_id: str
    profile: str
    source: Path
    run_id: str
    processed_frames: int


@dataclass(frozen=True)
class LoadedBatchIndex:
    batch_id: str
    experiment_id: str
    manifest_path: str | None
    analysis_start_s: float
    analysis_end_s: float | None
    primary_metric: str
    planned_comparisons: tuple[
        tuple[str, str], ...
    ]
    exclusion_rules: tuple[str, ...]
    runs: tuple[IndexedRun, ...]


@dataclass(frozen=True)
class PrimaryMetricRow:
    batch_id: str
    experiment_id: str
    trial_id: str
    profile: str
    run_id: str
    metric_name: str
    value: float
    sample_count: int


def _nonempty_string(
    value: Any,
    *,
    name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise RegenerationError(
            f"{name} must be a non-empty string"
        )

    return value.strip()


def _safe_component(
    value: str,
    *,
    name: str,
) -> str:
    if (
        value in {".", ".."}
        or Path(value).name != value
        or "/" in value
        or "\\" in value
    ):
        raise RegenerationError(
            f"{name} must be a path-safe identifier"
        )

    return value


def load_batch_index(
    path: str | Path,
) -> LoadedBatchIndex:
    """Load and validate a persisted G6 experiment batch index."""

    index_path = Path(path)

    try:
        payload = json.loads(
            index_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RegenerationError(
            f"failed to read batch index: {index_path}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise RegenerationError(
            "batch index must contain a mapping"
        )

    if payload.get("schema_version") != "1":
        raise RegenerationError(
            "unsupported batch index schema"
        )

    batch_id = _safe_component(
        _nonempty_string(
            payload.get("batch_id"),
            name="batch_id",
        ),
        name="batch_id",
    )
    experiment_id = _nonempty_string(
        payload.get("experiment_id"),
        name="experiment_id",
    )
    primary_metric = _nonempty_string(
        payload.get("primary_metric"),
        name="primary_metric",
    )

    manifest_path = payload.get(
        "manifest_path"
    )

    if (
        manifest_path is not None
        and (
            not isinstance(manifest_path, str)
            or not manifest_path.strip()
        )
    ):
        raise RegenerationError(
            "manifest_path must be a non-empty "
            "string or null"
        )

    raw_comparisons = payload.get(
        "planned_comparisons"
    )

    if (
        not isinstance(raw_comparisons, list)
        or not raw_comparisons
    ):
        raise RegenerationError(
            "planned_comparisons must be "
            "a non-empty list"
        )

    comparisons: list[tuple[str, str]] = []

    for index, comparison in enumerate(raw_comparisons):
        if (
            not isinstance(comparison, list)
            or len(comparison) != 2
        ):
            raise RegenerationError(
                f"planned_comparisons[{index}] "
                "must contain two profiles"
            )

        left, right = comparison

        if (
            not isinstance(left, str)
            or not left.strip()
            or not isinstance(right, str)
            or not right.strip()
        ):
            raise RegenerationError(
                "comparison profiles must be "
                "non-empty strings"
            )

        comparisons.append(
            (
                left.strip().lower(),
                right.strip().lower(),
            )
        )

    raw_exclusions = payload.get(
        "exclusion_rules"
    )

    if (
        not isinstance(raw_exclusions, list)
        or not raw_exclusions
    ):
        raise RegenerationError(
            "exclusion_rules must be "
            "a non-empty list"
        )

    exclusion_rules: list[str] = []

    for index, rule in enumerate(raw_exclusions):
        if (
            not isinstance(rule, str)
            or not rule.strip()
        ):
            raise RegenerationError(
                f"exclusion_rules[{index}] "
                "must be a non-empty string"
            )

        exclusion_rules.append(rule.strip())

    window = payload.get("analysis_window")

    if not isinstance(window, Mapping):
        raise RegenerationError(
            "analysis_window must be a mapping"
        )

    start_s = window.get("start_s")
    end_s = window.get("end_s")

    if (
        not isinstance(start_s, (int, float))
        or isinstance(start_s, bool)
        or not math.isfinite(start_s)
        or start_s < 0.0
    ):
        raise RegenerationError(
            "analysis_window.start_s is invalid"
        )

    if end_s is not None and (
        not isinstance(end_s, (int, float))
        or isinstance(end_s, bool)
        or not math.isfinite(end_s)
        or end_s <= start_s
    ):
        raise RegenerationError(
            "analysis_window.end_s is invalid"
        )

    raw_runs = payload.get("runs")

    if not isinstance(raw_runs, list) or not raw_runs:
        raise RegenerationError(
            "batch index must contain runs"
        )

    runs: list[IndexedRun] = []
    identities: set[tuple[str, str]] = set()
    run_ids: set[str] = set()

    for index, raw_run in enumerate(raw_runs):
        if not isinstance(raw_run, Mapping):
            raise RegenerationError(
                f"runs[{index}] must be a mapping"
            )

        trial_id = _nonempty_string(
            raw_run.get("trial_id"),
            name=f"runs[{index}].trial_id",
        )
        profile = _nonempty_string(
            raw_run.get("profile"),
            name=f"runs[{index}].profile",
        ).lower()
        run_id = _safe_component(
            _nonempty_string(
                raw_run.get("run_id"),
                name=f"runs[{index}].run_id",
            ),
            name=f"runs[{index}].run_id",
        )
        source = _nonempty_string(
            raw_run.get("source"),
            name=f"runs[{index}].source",
        )

        identity = (trial_id, profile)

        if identity in identities:
            raise RegenerationError(
                "duplicate trial/profile in batch"
            )

        if run_id in run_ids:
            raise RegenerationError(
                "run_id values must be unique in batch"
            )

        identities.add(identity)
        run_ids.add(run_id)

        if raw_run.get("experiment_id") != experiment_id:
            raise RegenerationError(
                "run experiment_id does not match "
                "batch experiment_id"
            )

        processed_frames = raw_run.get(
            "processed_frames"
        )

        if (
            not isinstance(processed_frames, int)
            or isinstance(processed_frames, bool)
            or processed_frames < 0
        ):
            raise RegenerationError(
                "processed_frames must be a "
                "non-negative integer"
            )

        runs.append(
            IndexedRun(
                experiment_id=experiment_id,
                trial_id=trial_id,
                profile=profile,
                source=Path(source),
                run_id=run_id,
                processed_frames=processed_frames,
            )
        )

    indexed_profiles = {
        run.profile
        for run in runs
    }

    for left, right in comparisons:
        if (
            left not in indexed_profiles
            or right not in indexed_profiles
        ):
            raise RegenerationError(
                "planned comparison references "
                "a profile absent from the batch"
            )

    trial_sources: dict[str, Path] = {}

    for run in runs:
        previous = trial_sources.get(run.trial_id)

        if previous is None:
            trial_sources[run.trial_id] = run.source
        elif previous != run.source:
            raise RegenerationError(
                "paired profiles within one trial "
                "must use the same source"
            )

    return LoadedBatchIndex(
        batch_id=batch_id,
        experiment_id=experiment_id,
        manifest_path=manifest_path,
        analysis_start_s=float(start_s),
        analysis_end_s=(
            float(end_s)
            if end_s is not None
            else None
        ),
        primary_metric=primary_metric,
        planned_comparisons=tuple(comparisons),
        exclusion_rules=tuple(exclusion_rules),
        runs=tuple(runs),
    )


def _load_runs(
    index: LoadedBatchIndex,
    *,
    runs_root: Path,
) -> dict[str, dict[str, RunArtifacts]]:
    grouped: dict[str, dict[str, RunArtifacts]] = {}

    for entry in index.runs:
        run = load_run_artifacts(
            runs_root / entry.run_id
        )
        metadata = run.metadata

        if metadata.get("experiment_id") != index.experiment_id:
            raise RegenerationError(
                "run metadata experiment_id mismatch"
            )

        if metadata.get("trial_id") != entry.trial_id:
            raise RegenerationError(
                "run metadata trial_id mismatch"
            )

        condition = metadata.get("condition")

        if (
            not isinstance(condition, str)
            or condition.lower() != entry.profile
        ):
            raise RegenerationError(
                "run metadata condition mismatch"
            )

        runtime_config = run.resolved_config.get(
            "runtime"
        )

        if not isinstance(runtime_config, Mapping):
            raise RegenerationError(
                "resolved runtime config is missing"
            )

        replay_source = runtime_config.get(
            "replay_source"
        )

        if (
            not isinstance(replay_source, str)
            or Path(replay_source).resolve()
            != entry.source.resolve()
        ):
            raise RegenerationError(
                "resolved replay source does not "
                "match batch index"
            )

        grouped.setdefault(entry.trial_id, {})[
            entry.profile.upper()
        ] = run

    return grouped


def _require_same_frame_timeline(
    runs: Mapping[str, RunArtifacts],
    *,
    start_s: float,
    end_s: float | None,
) -> None:
    reference: tuple[tuple[int, float], ...] | None = None

    for run in runs.values():
        timeline = tuple(
            (frame.frame_id, frame.timestamp_s)
            for frame in run.frames_in_window(
                start_s=start_s,
                end_s=end_s,
            )
        )

        if reference is None:
            reference = timeline
            continue

        if len(timeline) != len(reference):
            raise RegenerationError(
                "paired runs have different frame "
                "counts in analysis window"
            )

        for reference_row, current_row in zip(
            reference,
            timeline,
            strict=True,
        ):
            if (
                reference_row[0] != current_row[0]
                or not math.isclose(
                    reference_row[1],
                    current_row[1],
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ):
                raise RegenerationError(
                    "paired runs have different "
                    "frame/timestamp timelines"
                )


def _metric_rows(
    index: LoadedBatchIndex,
    grouped: Mapping[str, Mapping[str, RunArtifacts]],
) -> tuple[PrimaryMetricRow, ...]:
    rows: list[PrimaryMetricRow] = []
    run_id_lookup = {
        (entry.trial_id, entry.profile.upper()): entry.run_id
        for entry in index.runs
    }

    for trial_id, trial_runs in grouped.items():
        _require_same_frame_timeline(
            trial_runs,
            start_s=index.analysis_start_s,
            end_s=index.analysis_end_s,
        )

        if index.primary_metric == "radial_rms_jitter":
            results: Mapping[str, MetricResult] = (
                radial_rms_jitter_comparison(
                    trial_runs,
                    start_s=index.analysis_start_s,
                    end_s=index.analysis_end_s,
                )
            )
        elif index.primary_metric == "trajectory_deviation_rmse":
            results = trajectory_deviation_comparison(
                trial_runs,
                reference_condition="F0",
                start_s=index.analysis_start_s,
                end_s=index.analysis_end_s,
            )
        elif index.primary_metric == "valid_hand_observation_rate":
            results = {
                profile: valid_hand_observation_rate(
                    run,
                    start_s=index.analysis_start_s,
                    end_s=index.analysis_end_s,
                )
                for profile, run in trial_runs.items()
            }
        else:
            raise RegenerationError(
                "unsupported primary metric: "
                f"{index.primary_metric}"
            )

        for profile, result in results.items():
            rows.append(
                PrimaryMetricRow(
                    batch_id=index.batch_id,
                    experiment_id=index.experiment_id,
                    trial_id=trial_id,
                    profile=profile,
                    run_id=run_id_lookup[(trial_id, profile)],
                    metric_name=result.name,
                    value=result.value,
                    sample_count=result.sample_count,
                )
            )

    return tuple(rows)


def _write_metrics_csv(
    rows: tuple[PrimaryMetricRow, ...],
    path: Path,
) -> None:
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "batch_id",
                "experiment_id",
                "trial_id",
                "profile",
                "run_id",
                "metric_name",
                "value",
                "sample_count",
            ),
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "batch_id": row.batch_id,
                    "experiment_id": row.experiment_id,
                    "trial_id": row.trial_id,
                    "profile": row.profile,
                    "run_id": row.run_id,
                    "metric_name": row.metric_name,
                    "value": row.value,
                    "sample_count": row.sample_count,
                }
            )


def _write_primary_plot(
    rows: tuple[PrimaryMetricRow, ...],
    path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    profiles = tuple(dict.fromkeys(row.profile for row in rows))
    figure, axes = plt.subplots()

    for x, profile in enumerate(profiles):
        values = [
            row.value
            for row in rows
            if row.profile == profile
        ]
        axes.scatter([x] * len(values), values)

    axes.set_xticks(range(len(profiles)), profiles)
    axes.set_xlabel("Condition")
    axes.set_ylabel(rows[0].metric_name)
    axes.set_title("Primary descriptive metric")
    axes.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _write_trajectory_example(
    index: LoadedBatchIndex,
    grouped: Mapping[str, Mapping[str, RunArtifacts]],
    *,
    csv_path: Path,
    plot_path: Path,
) -> bool:
    if not grouped:
        return False

    first_trial_id = next(iter(grouped))
    runs = grouped[first_trial_id]

    if "F0" not in runs or len(runs) < 2:
        return False

    try:
        common_ids = common_landmark_frame_ids(
            tuple(runs.values()),
            start_s=index.analysis_start_s,
            end_s=index.analysis_end_s,
        )
    except MetricCalculationError as exc:
        if str(exc) == "no common usable landmark frames":
            return False
        raise

    series_by_profile = {
        profile: {
            landmark.frame_id: landmark
            for landmark in run.landmark_series(
                stage="filtered",
                landmark_index=8,
                coordinate_space="FRAME_NORMALIZED",
                start_s=index.analysis_start_s,
                end_s=index.analysis_end_s,
            )
        }
        for profile, run in runs.items()
    }

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "trial_id",
                "profile",
                "frame_id",
                "timestamp_s",
                "x",
                "y",
            ),
        )
        writer.writeheader()

        for profile, landmarks in series_by_profile.items():
            for frame_id in common_ids:
                landmark = landmarks[frame_id]
                writer.writerow(
                    {
                        "trial_id": first_trial_id,
                        "profile": profile,
                        "frame_id": frame_id,
                        "timestamp_s": landmark.timestamp_s,
                        "x": landmark.x,
                        "y": landmark.y,
                    }
                )

    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    figure, axes = plt.subplots()

    for profile, landmarks in series_by_profile.items():
        selected = [landmarks[frame_id] for frame_id in common_ids]
        axes.plot(
            [landmark.x for landmark in selected],
            [landmark.y for landmark in selected],
            marker=".",
            label=profile,
        )

    axes.set_xlabel("x (FRAME_NORMALIZED)")
    axes.set_ylabel("y (FRAME_NORMALIZED)")
    axes.set_title(
        "Filtered landmark 8 trajectory "
        f"— {first_trial_id}"
    )
    axes.legend()
    axes.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(plot_path, dpi=160)
    plt.close(figure)
    return True


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None

    revision = result.stdout.strip()
    return revision or None


def _file_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _write_provenance(
    index: LoadedBatchIndex,
    grouped: Mapping[
        str,
        Mapping[str, RunArtifacts],
    ],
    *,
    batch_index_path: Path,
    output_path: Path,
    analysis_code_revision: str | None,
) -> None:
    run_rows = []

    for entry in index.runs:
        run = grouped[
            entry.trial_id
        ][entry.profile.upper()]
        metadata = run.metadata

        run_rows.append(
            {
                "trial_id": entry.trial_id,
                "profile": entry.profile,
                "run_id": entry.run_id,
                "spec_version": metadata.get(
                    "spec_version"
                ),
                "run_code_revision": metadata.get(
                    "code_revision"
                ),
                "log_schema_version": metadata.get(
                    "log_schema_version"
                ),
                "config_hash": metadata.get(
                    "config_hash"
                ),
                "source_data": metadata.get(
                    "source_data"
                ),
                "provider": metadata.get(
                    "provider"
                ),
            }
        )

    payload = {
        "schema_version": "1",
        "batch_id": index.batch_id,
        "experiment_id": index.experiment_id,
        "manifest_path": index.manifest_path,
        "primary_metric": index.primary_metric,
        "analysis_window": {
            "start_s": index.analysis_start_s,
            "end_s": index.analysis_end_s,
        },
        "planned_comparisons": [
            [left, right]
            for left, right in index.planned_comparisons
        ],
        "exclusion_rules": list(index.exclusion_rules),
        "batch_index": {
            "path": str(batch_index_path.resolve()),
            "sha256": _file_sha256(batch_index_path),
        },
        "analysis": {
            "code_revision": analysis_code_revision,
        },
        "runs": run_rows,
    }

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def regenerate_batch(
    *,
    batch_index: Path,
    runs_root: Path,
    output_root: Path,
    analysis_code_revision: str | None = None,
) -> Path:
    """Regenerate primary metric table and plots from a batch index."""

    index = load_batch_index(batch_index)
    grouped = _load_runs(index, runs_root=runs_root)
    rows = _metric_rows(index, grouped)

    if not rows:
        raise RegenerationError(
            "no primary metric rows produced"
        )

    output_dir = output_root / index.batch_id
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_analysis_revision = (
        analysis_code_revision
        if analysis_code_revision is not None
        else _git_revision()
    )

    _write_metrics_csv(rows, output_dir / "metrics.csv")
    _write_primary_plot(rows, output_dir / "primary_metric.png")

    trajectories_path = output_dir / "trajectories.csv"
    trajectory_plot_path = output_dir / "trajectory_xy.png"
    has_trajectory = _write_trajectory_example(
        index,
        grouped,
        csv_path=trajectories_path,
        plot_path=trajectory_plot_path,
    )

    if not has_trajectory:
        trajectories_path.unlink(missing_ok=True)
        trajectory_plot_path.unlink(missing_ok=True)

    _write_provenance(
        index,
        grouped,
        batch_index_path=batch_index,
        output_path=output_dir / "provenance.json",
        analysis_code_revision=resolved_analysis_revision,
    )

    return output_dir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate descriptive experiment tables and plots "
            "from immutable runs."
        )
    )
    parser.add_argument(
        "--batch-index",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("runs"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results") / "generated",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_dir = regenerate_batch(
        batch_index=args.batch_index,
        runs_root=args.runs_root,
        output_root=args.output_root,
    )
    print(f"generated_results: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
