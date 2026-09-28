from pathlib import Path

import pytest

from analysis import (
    FrameRecord,
    LandmarkRecord,
    MetricCalculationError,
    RunArtifacts,
    common_landmark_frame_ids,
    radial_rms_jitter,
    radial_rms_jitter_comparison,
    trajectory_deviation_rmse,
    valid_hand_observation_rate,
)


def _run(
    *,
    name: str,
    points: dict[
        int,
        tuple[float, float, float],
    ],
    statuses: dict[int, str] | None = None,
) -> RunArtifacts:
    frames = tuple(
        FrameRecord(
            run_id=name,
            frame_id=frame_id,
            timestamp_s=timestamp_s,
            tracking_status=(
                statuses.get(
                    frame_id,
                    "VALID",
                )
                if statuses
                else "VALID"
            ),
            illumination_state=None,
            enhancement_active=None,
            filter_mode="RAW",
        )
        for frame_id, (
            timestamp_s,
            _,
            _,
        ) in sorted(points.items())
    )

    landmarks = tuple(
        LandmarkRecord(
            run_id=name,
            frame_id=frame_id,
            timestamp_s=timestamp_s,
            stage="filtered",
            landmark_index=8,
            x=x,
            y=y,
            z=-0.1,
            coordinate_space=(
                "FRAME_NORMALIZED"
            ),
        )
        for frame_id, (
            timestamp_s,
            x,
            y,
        ) in sorted(points.items())
    )

    return RunArtifacts(
        run_dir=Path(name),
        metadata={
            "run_id": name,
        },
        resolved_config={},
        frames=frames,
        landmarks=landmarks,
    )


def test_radial_rms_jitter_known_value() -> None:
    run = _run(
        name="f0",
        points={
            0: (0.0, 0.0, 0.0),
            1: (0.1, 2.0, 0.0),
        },
    )

    result = radial_rms_jitter(run)

    assert result.name == "radial_rms_jitter"
    assert result.sample_count == 2
    assert result.value == pytest.approx(1.0)


def test_common_landmark_frame_ids_use_intersection() -> None:
    first = _run(
        name="f0",
        points={
            0: (0.0, 0.0, 0.0),
            1: (0.1, 1.0, 0.0),
            2: (0.2, 2.0, 0.0),
        },
    )

    second = _run(
        name="f1",
        points={
            1: (0.1, 1.0, 0.0),
            2: (0.2, 2.0, 0.0),
            3: (0.3, 3.0, 0.0),
        },
    )

    assert common_landmark_frame_ids(
        (first, second)
    ) == (1, 2)


def test_a1_comparison_uses_same_common_frames() -> None:
    f0 = _run(
        name="f0",
        points={
            0: (0.0, 100.0, 0.0),
            1: (0.1, 0.0, 0.0),
            2: (0.2, 2.0, 0.0),
        },
    )

    f1 = _run(
        name="f1",
        points={
            1: (0.1, 0.5, 0.0),
            2: (0.2, 1.5, 0.0),
        },
    )

    results = radial_rms_jitter_comparison(
        {
            "F0": f0,
            "F1": f1,
        }
    )

    assert results["F0"].sample_count == 2
    assert results["F1"].sample_count == 2

    assert results["F0"].value == pytest.approx(
        1.0
    )

    assert results["F1"].value == pytest.approx(
        0.5
    )


def test_trajectory_deviation_rmse_known_value() -> None:
    reference = _run(
        name="f0",
        points={
            0: (0.0, 0.0, 0.0),
            1: (0.1, 1.0, 1.0),
        },
    )

    compared = _run(
        name="f2",
        points={
            0: (0.0, 3.0, 4.0),
            1: (0.1, 4.0, 5.0),
        },
    )

    result = trajectory_deviation_rmse(
        reference,
        compared,
    )

    assert result.sample_count == 2
    assert result.value == pytest.approx(5.0)


def test_reference_deviation_from_itself_is_zero() -> None:
    reference = _run(
        name="f0",
        points={
            0: (0.0, 0.1, 0.2),
            1: (0.1, 0.3, 0.4),
        },
    )

    result = trajectory_deviation_rmse(
        reference,
        reference,
    )

    assert result.value == pytest.approx(0.0)


def test_paired_metric_rejects_timestamp_mismatch() -> None:
    first = _run(
        name="f0",
        points={
            0: (0.0, 0.0, 0.0),
        },
    )

    second = _run(
        name="f1",
        points={
            0: (0.01, 0.0, 0.0),
        },
    )

    with pytest.raises(
        MetricCalculationError,
        match="timestamp",
    ):
        trajectory_deviation_rmse(
            first,
            second,
        )


def test_valid_hand_observation_rate() -> None:
    run = _run(
        name="p0",
        points={
            0: (0.0, 0.0, 0.0),
            1: (0.1, 0.0, 0.0),
            2: (0.2, 0.0, 0.0),
            3: (0.3, 0.0, 0.0),
        },
        statuses={
            0: "VALID",
            1: "NO_HAND",
            2: "REACQUIRED",
            3: "INVALID",
        },
    )

    result = valid_hand_observation_rate(
        run
    )

    assert result.sample_count == 4
    assert result.value == pytest.approx(0.5)


def test_valid_rate_obeys_analysis_window() -> None:
    run = _run(
        name="p1",
        points={
            0: (0.0, 0.0, 0.0),
            1: (1.0, 0.0, 0.0),
            2: (2.0, 0.0, 0.0),
        },
        statuses={
            0: "NO_HAND",
            1: "VALID",
            2: "REACQUIRED",
        },
    )

    result = valid_hand_observation_rate(
        run,
        start_s=1.0,
        end_s=2.0,
    )

    assert result.sample_count == 2
    assert result.value == pytest.approx(1.0)
