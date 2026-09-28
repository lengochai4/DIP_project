import json
from pathlib import Path

import pytest

from experiments.manifest import (
    ExperimentManifest,
    ManifestTrial,
)
from experiments.run_batch import (
    BatchIndex,
    BatchRunResult,
    build_batch_index,
    run_experiment_batch,
    write_batch_index,
)


def test_batch_expansion_is_paired_and_deterministic(
    tmp_path: Path,
) -> None:
    source_a = tmp_path / "a.mp4"
    source_b = tmp_path / "b.mp4"

    manifest = ExperimentManifest(
        schema_version="1",
        experiment_id="A1",
        profiles=(
            "f0",
            "f1",
            "f2",
        ),
        model=tmp_path / "model.task",
        trials=(
            ManifestTrial(
                trial_id="trial-001",
                source=source_a,
            ),
            ManifestTrial(
                trial_id="trial-002",
                source=source_b,
            ),
        ),
        warmup_s=1.0,
        analysis_start_s=1.0,
        analysis_end_s=10.0,
        primary_metric="radial_rms_jitter",
        planned_comparisons=(
            ("f0", "f1"),
            ("f0", "f2"),
        ),
        exclusion_rules=(
            "startup warmup",
        ),
    )

    calls = []

    def fake_runner(**kwargs):
        calls.append(kwargs)

        return (
            f"run-{len(calls)}",
            100,
        )

    results = run_experiment_batch(
        manifest,
        output_dir=tmp_path / "runs",
        runner=fake_runner,
    )

    assert [
        (
            call["trial_id"],
            call["profile_name"],
            call["source"],
        )
        for call in calls
    ] == [
        ("trial-001", "f0", source_a),
        ("trial-001", "f1", source_a),
        ("trial-001", "f2", source_a),
        ("trial-002", "f0", source_b),
        ("trial-002", "f1", source_b),
        ("trial-002", "f2", source_b),
    ]

    assert len(results) == 6

    assert all(
        call["experiment_id"] == "A1"
        for call in calls
    )

    assert all(
        call["warmup_s"] == 1.0
        for call in calls
    )


def test_batch_index_preserves_exact_run_identity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"

    manifest = ExperimentManifest(
        schema_version="1",
        experiment_id="A1",
        profiles=(
            "f0",
            "f1",
            "f2",
        ),
        model=tmp_path / "model.task",
        trials=(
            ManifestTrial(
                trial_id="trial-001",
                source=source,
            ),
        ),
        warmup_s=1.0,
        analysis_start_s=1.0,
        analysis_end_s=10.0,
        primary_metric=(
            "radial_rms_jitter"
        ),
        planned_comparisons=(
            ("f0", "f1"),
            ("f0", "f2"),
        ),
        exclusion_rules=(
            "startup warmup",
        ),
    )

    results = (
        BatchRunResult(
            experiment_id="A1",
            trial_id="trial-001",
            profile="f0",
            source=source,
            run_id="run-f0",
            processed_frames=100,
        ),
        BatchRunResult(
            experiment_id="A1",
            trial_id="trial-001",
            profile="f1",
            source=source,
            run_id="run-f1",
            processed_frames=100,
        ),
        BatchRunResult(
            experiment_id="A1",
            trial_id="trial-001",
            profile="f2",
            source=source,
            run_id="run-f2",
            processed_frames=100,
        ),
    )

    manifest_path = (
        tmp_path / "a1.yaml"
    )
    manifest_path.touch()

    index = build_batch_index(
        manifest,
        results,
        manifest_path=manifest_path,
        batch_id="batch-test",
    )

    path = write_batch_index(
        index,
        index_root=(
            tmp_path / "results"
        ),
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["schema_version"] == "1"
    assert payload["batch_id"] == "batch-test"
    assert payload["experiment_id"] == "A1"

    assert payload["analysis_window"] == {
        "start_s": 1.0,
        "end_s": 10.0,
    }

    assert [
        row["run_id"]
        for row in payload["runs"]
    ] == [
        "run-f0",
        "run-f1",
        "run-f2",
    ]

    assert {
        row["source"]
        for row in payload["runs"]
    } == {
        str(source),
    }


def test_batch_index_does_not_overwrite_existing_batch(
    tmp_path: Path,
) -> None:
    index = BatchIndex(
        batch_id="same-batch",
        experiment_id="A1",
        manifest_path=None,
        analysis_start_s=0.0,
        analysis_end_s=None,
        primary_metric=(
            "radial_rms_jitter"
        ),
        planned_comparisons=(
            ("f0", "f1"),
        ),
        exclusion_rules=(
            "corrupted source",
        ),
        runs=(),
    )

    root = tmp_path / "results"

    write_batch_index(
        index,
        index_root=root,
    )

    with pytest.raises(
        FileExistsError
    ):
        write_batch_index(
            index,
            index_root=root,
        )
