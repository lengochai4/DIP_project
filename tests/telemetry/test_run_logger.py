import csv
import json
from pathlib import Path

from dip_touchless.configuration import (
    resolve_config,
)
from dip_touchless.core import (
    FilterDiagnostics,
    FilterMode,
    IlluminationMetrics,
    IlluminationState,
    InteractionState,
    MeasurementQuality,
    ROI,
    ROIState,
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


def _tracking_frame(
    run_id: str,
) -> TrackingFrame:
    return TrackingFrame(
        run_id=run_id,
        frame_id=0,
        timestamp_s=1.0,
        status=TrackingStatus.NO_HAND,
        raw_landmarks=(),
        filtered_landmarks=(),
        quality=MeasurementQuality.unavailable(),
        roi=ROI(
            x=0,
            y=0,
            width=640,
            height=480,
            state=ROIState.SEARCHING,
        ),
        illumination=IlluminationMetrics(
            mean_v=0.0,
            std_v=0.0,
            p10_v=0.0,
            p90_v=0.0,
            robust_range_v=0.0,
            state=IlluminationState.NORMAL,
            enhancement_active=False,
        ),
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


def test_logger_creates_run_artifacts(
    tmp_path: Path,
) -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    metadata = build_run_metadata(
        resolved,
        run_id="test-run",
        code_revision="test-revision",
    )

    logger = FileRunLogger(tmp_path)

    logger.start_run(
        metadata,
        resolved.to_dict(),
    )

    logger.close()

    run_dir = tmp_path / "test-run"

    assert (
        run_dir / "metadata.json"
    ).is_file()

    assert (
        run_dir / "resolved_config.yaml"
    ).is_file()

    assert (
        run_dir / "frames.csv"
    ).is_file()

    assert (
        run_dir / "landmarks.csv"
    ).is_file()

    assert (
        run_dir / "events.csv"
    ).is_file()


def test_metadata_contains_reproducibility_identity(
    tmp_path: Path,
) -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    metadata = build_run_metadata(
        resolved,
        run_id="test-run",
        code_revision="abc123",
    )

    logger = FileRunLogger(tmp_path)

    logger.start_run(
        metadata,
        resolved.to_dict(),
    )

    logger.close()

    stored = json.loads(
        (
            tmp_path
            / "test-run"
            / "metadata.json"
        ).read_text(encoding="utf-8")
    )

    assert stored["run_id"] == "test-run"
    assert stored["code_revision"] == "abc123"
    assert stored["config_hash"] == resolved.sha256
    assert stored["log_schema_version"] == "1"


def test_logger_serializes_unavailable_quality(
    tmp_path: Path,
) -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    metadata = build_run_metadata(
        resolved,
        run_id="test-run",
        code_revision="abc123",
    )

    logger = FileRunLogger(tmp_path)

    logger.start_run(
        metadata,
        resolved.to_dict(),
    )

    frame = _tracking_frame("test-run")

    logger.log_tracking_frame(frame)

    logger.log_interaction_state(
        InteractionState(
            run_id="test-run",
            frame_id=0,
            timestamp_s=1.0,
            interaction_valid=False,
            pointer_xy=None,
            pinch_ratio=None,
            pinch_active=False,
            rotation_delta=(0.0, 0.0),
            scale_delta=0.0,
        )
    )

    logger.close()

    with (
        tmp_path
        / "test-run"
        / "frames.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 1

    row = rows[0]

    assert row["frame_id"] == "0"
    assert row["quality_valid"] == "False"
    assert row["quality_value"] == ""
    assert row["quality_source"] == "NONE"


def test_event_log_remains_parseable(
    tmp_path: Path,
) -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    metadata = build_run_metadata(
        resolved,
        run_id="test-run",
        code_revision="abc123",
    )

    logger = FileRunLogger(tmp_path)

    logger.start_run(
        metadata,
        resolved.to_dict(),
    )

    logger.log_event(
        {
            "frame_id": 4,
            "timestamp_s": 2.5,
            "event_type": "TEST_EVENT",
            "severity": "INFO",
            "details": {
                "message": "fixture",
            },
        }
    )

    logger.close()

    with (
        tmp_path
        / "test-run"
        / "events.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 1
    assert rows[0]["event_type"] == "TEST_EVENT"

    details = json.loads(
        rows[0]["details_json"]
    )

    assert details["message"] == "fixture"