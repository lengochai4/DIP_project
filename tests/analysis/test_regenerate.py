import csv
import hashlib
import json
from pathlib import Path

from analysis.regenerate import regenerate_batch
from dip_touchless.configuration import resolve_config
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
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"


def _make_run(
    tmp_path: Path,
    *,
    run_id: str,
    condition: str,
    points: tuple[
        tuple[float, float] | None,
        ...,
    ],
    trial_id: str = "trial-001",
) -> None:
    source = tmp_path / "source.mp4"
    source.touch(exist_ok=True)

    filter_mode = {
        "F0": FilterMode.RAW,
        "F1": FilterMode.ONE_EURO_FIXED,
        "F2": FilterMode.ONE_EURO_ADAPTIVE,
    }[condition]

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": str(source.resolve()),
            },
            "filter": {
                "mode": filter_mode.value,
            },
            "experiment": {
                "experiment_id": "A1",
                "condition": condition,
                "trial_id": trial_id,
                "warmup_s": 0.0,
            },
        },
    )

    logger = FileRunLogger(tmp_path / "runs")
    logger.start_run(
        build_run_metadata(
            resolved,
            run_id=run_id,
            code_revision="test-revision",
        ),
        resolved.to_dict(),
    )

    for frame_id, point in enumerate(points):
        if point is None:
            status = TrackingStatus.NO_HAND
            raw_landmarks = ()
            filtered_landmarks = ()
        else:
            x, y = point
            landmark = Landmark(
                index=8,
                x=x,
                y=y,
                z=-0.1,
                coordinate_space=(
                    CoordinateSpace.FRAME_NORMALIZED
                ),
            )
            status = TrackingStatus.VALID
            raw_landmarks = (landmark,)
            filtered_landmarks = (landmark,)

        logger.log_tracking_frame(
            TrackingFrame(
                run_id=run_id,
                frame_id=frame_id,
                timestamp_s=frame_id * 0.1,
                status=status,
                raw_landmarks=raw_landmarks,
                filtered_landmarks=filtered_landmarks,
                quality=MeasurementQuality.unavailable(),
                roi=None,
                illumination=None,
                filter_diagnostics=FilterDiagnostics(
                    mode=filter_mode,
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
        )

    logger.close()


def test_regenerate_batch_creates_primary_assets(
    tmp_path: Path,
) -> None:
    _make_run(
        tmp_path,
        run_id="run-f0",
        condition="F0",
        points=((0.0, 0.0), (2.0, 0.0)),
    )
    _make_run(
        tmp_path,
        run_id="run-f1",
        condition="F1",
        points=((0.5, 0.0), (1.5, 0.0)),
    )
    _make_run(
        tmp_path,
        run_id="run-f2",
        condition="F2",
        points=((0.75, 0.0), (1.25, 0.0)),
    )

    source = (tmp_path / "source.mp4").resolve()
    batch_index = tmp_path / "batch_index.json"
    batch_index.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "batch_id": "batch-test",
                "experiment_id": "A1",
                "analysis_window": {
                    "start_s": 0.0,
                    "end_s": 0.1,
                },
                "primary_metric": "radial_rms_jitter",
                "planned_comparisons": [
                    ["f0", "f1"],
                    ["f0", "f2"],
                ],
                "exclusion_rules": ["startup warmup"],
                "runs": [
                    {
                        "experiment_id": "A1",
                        "trial_id": "trial-001",
                        "profile": "f0",
                        "source": str(source),
                        "run_id": "run-f0",
                        "processed_frames": 2,
                    },
                    {
                        "experiment_id": "A1",
                        "trial_id": "trial-001",
                        "profile": "f1",
                        "source": str(source),
                        "run_id": "run-f1",
                        "processed_frames": 2,
                    },
                    {
                        "experiment_id": "A1",
                        "trial_id": "trial-001",
                        "profile": "f2",
                        "source": str(source),
                        "run_id": "run-f2",
                        "processed_frames": 2,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_dir = regenerate_batch(
        batch_index=batch_index,
        runs_root=tmp_path / "runs",
        output_root=tmp_path / "results",
        analysis_code_revision=(
            "test-analysis-revision"
        ),
    )

    with (output_dir / "metrics.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert [row["profile"] for row in rows] == [
        "F0",
        "F1",
        "F2",
    ]
    assert all(
        row["metric_name"] == "radial_rms_jitter"
        for row in rows
    )
    assert all(
        row["available"] == "true"
        and row["unavailable_reason"] == ""
        and float(row["value"]) >= 0.0
        for row in rows
    )
    assert (output_dir / "primary_metric.png").stat().st_size > 0
    assert (output_dir / "trajectories.csv").is_file()
    assert (output_dir / "trajectory_xy.png").stat().st_size > 0

    provenance_path = output_dir / "provenance.json"
    provenance = json.loads(
        provenance_path.read_text(
            encoding="utf-8"
        )
    )

    assert provenance["analysis"]["code_revision"] == (
        "test-analysis-revision"
    )
    assert provenance["analysis"]["recorded_trial_count"] == 1
    assert provenance["analysis"]["evaluable_trial_count"] == 1
    assert provenance["analysis"]["unavailable_trials"] == []
    assert provenance["exclusion_rules"] == [
        "startup warmup"
    ]
    assert provenance["planned_comparisons"] == [
        ["f0", "f1"],
        ["f0", "f2"],
    ]
    assert provenance["batch_index"]["sha256"] == (
        hashlib.sha256(
            batch_index.read_bytes()
        ).hexdigest()
    )
    assert [
        row["run_id"]
        for row in provenance["runs"]
    ] == [
        "run-f0",
        "run-f1",
        "run-f2",
    ]
    assert all(
        row["config_hash"]
        for row in provenance["runs"]
    )
    assert all(
        row["run_code_revision"] == "test-revision"
        for row in provenance["runs"]
    )
    assert all(
        row["source_data"]["sha256"]
        for row in provenance["runs"]
    )


def test_regenerate_marks_no_common_frames_unavailable(
    tmp_path: Path,
) -> None:
    runs = [
        (
            "trial-001",
            "F0",
            "run-trial-001-f0",
            ((0.0, 0.0), (2.0, 0.0)),
        ),
        (
            "trial-001",
            "F1",
            "run-trial-001-f1",
            ((0.5, 0.0), (1.5, 0.0)),
        ),
        (
            "trial-001",
            "F2",
            "run-trial-001-f2",
            ((0.75, 0.0), (1.25, 0.0)),
        ),
        ("trial-002", "F0", "run-trial-002-f0", (None, None)),
        ("trial-002", "F1", "run-trial-002-f1", (None, None)),
        ("trial-002", "F2", "run-trial-002-f2", (None, None)),
    ]

    for trial_id, condition, run_id, points in runs:
        _make_run(
            tmp_path,
            run_id=run_id,
            condition=condition,
            trial_id=trial_id,
            points=points,
        )

    source = (tmp_path / "source.mp4").resolve()
    batch_index = tmp_path / "batch_index.json"
    batch_index.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "batch_id": "batch-unavailable",
                "experiment_id": "A1",
                "analysis_window": {
                    "start_s": 0.0,
                    "end_s": 0.1,
                },
                "primary_metric": "radial_rms_jitter",
                "planned_comparisons": [
                    ["f0", "f1"],
                    ["f0", "f2"],
                ],
                "exclusion_rules": ["startup warmup"],
                "runs": [
                    {
                        "experiment_id": "A1",
                        "trial_id": trial_id,
                        "profile": condition.lower(),
                        "source": str(source),
                        "run_id": run_id,
                        "processed_frames": 2,
                    }
                    for trial_id, condition, run_id, _ in runs
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_dir = regenerate_batch(
        batch_index=batch_index,
        runs_root=tmp_path / "runs",
        output_root=tmp_path / "results",
        analysis_code_revision="test-analysis-revision",
    )

    with (output_dir / "metrics.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 6
    evaluable_rows = [
        row
        for row in rows
        if row["trial_id"] == "trial-001"
    ]
    unavailable_rows = [
        row
        for row in rows
        if row["trial_id"] == "trial-002"
    ]

    assert len(evaluable_rows) == 3
    assert all(
        row["available"] == "true"
        and row["unavailable_reason"] == ""
        and row["value"] != ""
        for row in evaluable_rows
    )
    assert len(unavailable_rows) == 3
    assert all(
        row["available"] == "false"
        and row["unavailable_reason"]
        == "no_common_usable_frames"
        and row["value"] == ""
        and row["sample_count"] == "0"
        for row in unavailable_rows
    )
    assert (output_dir / "primary_metric.png").stat().st_size > 0

    provenance = json.loads(
        (output_dir / "provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert provenance["analysis"]["recorded_trial_count"] == 2
    assert provenance["analysis"]["evaluable_trial_count"] == 1
    assert provenance["analysis"]["unavailable_trials"] == [
        {
            "trial_id": "trial-002",
            "reason": "no_common_usable_frames",
        }
    ]
