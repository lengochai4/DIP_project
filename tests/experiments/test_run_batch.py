from pathlib import Path

from experiments.manifest import (
    ExperimentManifest,
    ManifestTrial,
)
from experiments.run_batch import (
    run_experiment_batch,
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
