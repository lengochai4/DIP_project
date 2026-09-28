from pathlib import Path

import pytest

from analysis import (
    RunArtifactError,
    load_run_artifacts,
)
from dip_touchless.configuration import (
    resolve_config,
)
from dip_touchless.core import (
    CoordinateSpace,
    FilterDiagnostics,
    FilterMode,
    Landmark,
    MeasurementQuality,
    StageTimings,
    TrackingFrame,
    TrackingStatus,
)
from dip_touchless.telemetry import (
    FileRunLogger,
    build_run_metadata,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG = (
    PROJECT_ROOT / "config" / "default.yaml"
)


def _generate_run(
    tmp_path: Path,
) -> Path:
    run_id = "analysis-generated-run"

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "experiment": {
                "experiment_id": "A1",
                "condition": "F0",
                "trial_id": "trial-001",
                "warmup_s": 0.0,
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    landmark = Landmark(
        index=8,
        x=0.4,
        y=0.5,
        z=-0.1,
        coordinate_space=(
            CoordinateSpace.FRAME_NORMALIZED
        ),
    )

    frame = TrackingFrame(
        run_id=run_id,
        frame_id=0,
        timestamp_s=0.0,
        status=TrackingStatus.VALID,
        raw_landmarks=(landmark,),
        filtered_landmarks=(landmark,),
        quality=MeasurementQuality.unavailable(),
        roi=None,
        illumination=None,
        filter_diagnostics=FilterDiagnostics(
            mode=FilterMode.RAW,
            dt_s=None,
            speed=None,
            beta=None,
            min_cutoff_hz=None,
            final_cutoff_hz=None,
            signal_alpha=None,
            derivative_alpha=None,
            reset_occurred=False,
            events=(),
        ),
        timings=StageTimings(
            preprocess_ms=0.0,
            tracking_ms=0.0,
            filtering_ms=0.0,
            gesture_ms=0.0,
            compute_total_ms=0.0,
        ),
        events=(),
    )

    logger = FileRunLogger(
        tmp_path / "runs"
    )

    logger.start_run(
        metadata,
        resolved.to_dict(),
    )

    logger.log_tracking_frame(frame)
    logger.close()

    return (
        tmp_path
        / "runs"
        / run_id
    )


def test_loader_consumes_generated_run_without_csv_editing(
    tmp_path: Path,
) -> None:
    run_dir = _generate_run(tmp_path)

    run = load_run_artifacts(run_dir)

    assert run.run_id == "analysis-generated-run"
    assert run.metadata["experiment_id"] == "A1"
    assert run.metadata["condition"] == "F0"
    assert len(run.frames) == 1
    assert len(run.landmarks) == 2

    frame = run.frames[0]

    assert frame.frame_id == 0
    assert frame.timestamp_s == pytest.approx(0.0)
    assert frame.tracking_status == "VALID"
    assert frame.filter_mode == "RAW"
    assert frame.illumination_state is None
    assert frame.enhancement_active is None

    filtered = run.landmark_series(
        stage="filtered",
        landmark_index=8,
        coordinate_space="FRAME_NORMALIZED",
    )

    assert len(filtered) == 1
    assert filtered[0].x == pytest.approx(0.4)
    assert filtered[0].y == pytest.approx(0.5)


def test_analysis_window_filters_by_timestamp(
    tmp_path: Path,
) -> None:
    run = load_run_artifacts(
        _generate_run(tmp_path)
    )

    assert len(
        run.frames_in_window(
            start_s=0.0,
            end_s=0.0,
        )
    ) == 1

    assert (
        run.frames_in_window(
            start_s=0.1,
            end_s=None,
        )
        == ()
    )


def test_loader_rejects_missing_required_artifact(
    tmp_path: Path,
) -> None:
    run_dir = _generate_run(tmp_path)

    (
        run_dir / "landmarks.csv"
    ).unlink()

    with pytest.raises(
        RunArtifactError,
        match="missing landmarks",
    ):
        load_run_artifacts(run_dir)
