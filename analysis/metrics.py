"""Frozen primary descriptive metrics for G6 experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from analysis.run_loader import (
    LandmarkRecord,
    RunArtifacts,
)


class MetricCalculationError(ValueError):
    """Raised when a primary metric cannot be computed safely."""


@dataclass(frozen=True)
class MetricResult:
    name: str
    value: float
    sample_count: int


DEFAULT_LANDMARK_INDEX = 8
DEFAULT_STAGE = "filtered"
DEFAULT_COORDINATE_SPACE = "FRAME_NORMALIZED"

_USABLE_TRACKING_STATUSES = {
    "VALID",
    "REACQUIRED",
}


def _landmarks_by_frame(
    run: RunArtifacts,
    *,
    landmark_index: int,
    stage: str,
    coordinate_space: str,
    start_s: float,
    end_s: float | None,
) -> dict[int, LandmarkRecord]:
    series = run.landmark_series(
        stage=stage,
        landmark_index=landmark_index,
        coordinate_space=coordinate_space,
        start_s=start_s,
        end_s=end_s,
    )

    result: dict[int, LandmarkRecord] = {}

    for landmark in series:
        if landmark.frame_id in result:
            raise MetricCalculationError(
                "duplicate target landmark for "
                f"frame_id {landmark.frame_id}"
            )

        result[landmark.frame_id] = landmark

    return result


def _frame_timestamps(
    run: RunArtifacts,
) -> dict[int, float]:
    return {
        frame.frame_id: frame.timestamp_s
        for frame in run.frames
    }


def common_landmark_frame_ids(
    runs: Sequence[RunArtifacts],
    *,
    landmark_index: int = DEFAULT_LANDMARK_INDEX,
    stage: str = DEFAULT_STAGE,
    coordinate_space: str = DEFAULT_COORDINATE_SPACE,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> tuple[int, ...]:
    """Return target-landmark frame IDs present in every run."""

    if not runs:
        raise MetricCalculationError(
            "at least one run is required"
        )

    frame_sets = []

    for run in runs:
        landmarks = _landmarks_by_frame(
            run,
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )

        frame_sets.append(
            set(landmarks)
        )

    common = set.intersection(*frame_sets)

    if not common:
        raise MetricCalculationError(
            "no common usable landmark frames"
        )

    return tuple(sorted(common))


def _require_matching_timestamps(
    runs: Sequence[RunArtifacts],
    frame_ids: Sequence[int],
) -> None:
    if not runs:
        raise MetricCalculationError(
            "at least one run is required"
        )

    timestamps_by_run = tuple(
        _frame_timestamps(run)
        for run in runs
    )
    reference = timestamps_by_run[0]

    for frame_id in frame_ids:
        if frame_id not in reference:
            raise MetricCalculationError(
                f"reference run is missing frame "
                f"{frame_id}"
            )

        expected = reference[frame_id]

        for timestamps in timestamps_by_run[1:]:
            if frame_id not in timestamps:
                raise MetricCalculationError(
                    f"run is missing frame {frame_id}"
                )

            if not math.isclose(
                timestamps[frame_id],
                expected,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise MetricCalculationError(
                    "paired runs have mismatched "
                    f"timestamp at frame {frame_id}"
                )


def radial_rms_jitter(
    run: RunArtifacts,
    *,
    frame_ids: Sequence[int] | None = None,
    landmark_index: int = DEFAULT_LANDMARK_INDEX,
    stage: str = DEFAULT_STAGE,
    coordinate_space: str = DEFAULT_COORDINATE_SPACE,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> MetricResult:
    """Compute radial RMS jitter around the trajectory mean."""

    landmarks = _landmarks_by_frame(
        run,
        landmark_index=landmark_index,
        stage=stage,
        coordinate_space=coordinate_space,
        start_s=start_s,
        end_s=end_s,
    )

    if frame_ids is None:
        selected_ids = tuple(
            sorted(landmarks)
        )
    else:
        selected_ids = tuple(frame_ids)

    if not selected_ids:
        raise MetricCalculationError(
            "radial RMS jitter has no samples"
        )

    try:
        selected = tuple(
            landmarks[frame_id]
            for frame_id in selected_ids
        )
    except KeyError as exc:
        raise MetricCalculationError(
            "requested frame is missing the "
            "target landmark"
        ) from exc

    count = len(selected)

    mean_x = math.fsum(
        landmark.x
        for landmark in selected
    ) / count

    mean_y = math.fsum(
        landmark.y
        for landmark in selected
    ) / count

    mean_squared_radius = math.fsum(
        (
            (landmark.x - mean_x) ** 2
            + (landmark.y - mean_y) ** 2
        )
        for landmark in selected
    ) / count

    return MetricResult(
        name="radial_rms_jitter",
        value=math.sqrt(
            mean_squared_radius
        ),
        sample_count=count,
    )


def radial_rms_jitter_comparison(
    runs: Mapping[str, RunArtifacts],
    *,
    landmark_index: int = DEFAULT_LANDMARK_INDEX,
    stage: str = DEFAULT_STAGE,
    coordinate_space: str = DEFAULT_COORDINATE_SPACE,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> dict[str, MetricResult]:
    """Compute A1 metrics on common paired usable frames."""

    if not runs:
        raise MetricCalculationError(
            "at least one condition run is required"
        )

    run_values = tuple(runs.values())

    common_ids = common_landmark_frame_ids(
        run_values,
        landmark_index=landmark_index,
        stage=stage,
        coordinate_space=coordinate_space,
        start_s=start_s,
        end_s=end_s,
    )

    _require_matching_timestamps(
        run_values,
        common_ids,
    )

    return {
        condition: radial_rms_jitter(
            run,
            frame_ids=common_ids,
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )
        for condition, run in runs.items()
    }


def trajectory_deviation_rmse(
    reference: RunArtifacts,
    compared: RunArtifacts,
    *,
    frame_ids: Sequence[int] | None = None,
    landmark_index: int = DEFAULT_LANDMARK_INDEX,
    stage: str = DEFAULT_STAGE,
    coordinate_space: str = DEFAULT_COORDINATE_SPACE,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> MetricResult:
    """Compute A2 trajectory deviation from the F0 reference."""

    if frame_ids is None:
        common_ids = common_landmark_frame_ids(
            (reference, compared),
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )
    else:
        common_ids = tuple(frame_ids)

        if not common_ids:
            raise MetricCalculationError(
                "trajectory deviation has no samples"
            )

    _require_matching_timestamps(
        (reference, compared),
        common_ids,
    )

    reference_landmarks = (
        _landmarks_by_frame(
            reference,
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )
    )

    compared_landmarks = (
        _landmarks_by_frame(
            compared,
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )
    )

    try:
        mean_squared_deviation = math.fsum(
            (
                (
                    compared_landmarks[frame_id].x
                    - reference_landmarks[frame_id].x
                )
                ** 2
                + (
                    compared_landmarks[frame_id].y
                    - reference_landmarks[frame_id].y
                )
                ** 2
            )
            for frame_id in common_ids
        ) / len(common_ids)
    except KeyError as exc:
        raise MetricCalculationError(
            "requested frame is missing the "
            "target landmark"
        ) from exc

    return MetricResult(
        name="trajectory_deviation_rmse",
        value=math.sqrt(
            mean_squared_deviation
        ),
        sample_count=len(common_ids),
    )


def trajectory_deviation_comparison(
    runs: Mapping[str, RunArtifacts],
    *,
    reference_condition: str = "F0",
    landmark_index: int = DEFAULT_LANDMARK_INDEX,
    stage: str = DEFAULT_STAGE,
    coordinate_space: str = DEFAULT_COORDINATE_SPACE,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> dict[str, MetricResult]:
    """Compute A2 on one common paired landmark frame set."""

    if reference_condition not in runs:
        raise MetricCalculationError(
            f"missing reference condition: "
            f"{reference_condition}"
        )

    run_values = tuple(runs.values())

    common_ids = common_landmark_frame_ids(
        run_values,
        landmark_index=landmark_index,
        stage=stage,
        coordinate_space=coordinate_space,
        start_s=start_s,
        end_s=end_s,
    )

    _require_matching_timestamps(
        run_values,
        common_ids,
    )

    reference = runs[reference_condition]

    return {
        condition: trajectory_deviation_rmse(
            reference,
            run,
            frame_ids=common_ids,
            landmark_index=landmark_index,
            stage=stage,
            coordinate_space=coordinate_space,
            start_s=start_s,
            end_s=end_s,
        )
        for condition, run in runs.items()
    }


def valid_hand_observation_rate(
    run: RunArtifacts,
    *,
    start_s: float = 0.0,
    end_s: float | None = None,
) -> MetricResult:
    """Compute Experiment B valid hand-observation rate."""

    frames = run.frames_in_window(
        start_s=start_s,
        end_s=end_s,
    )

    if not frames:
        raise MetricCalculationError(
            "valid observation rate has "
            "no analyzed frames"
        )

    usable_count = sum(
        frame.tracking_status
        in _USABLE_TRACKING_STATUSES
        for frame in frames
    )

    return MetricResult(
        name="valid_hand_observation_rate",
        value=usable_count / len(frames),
        sample_count=len(frames),
    )
