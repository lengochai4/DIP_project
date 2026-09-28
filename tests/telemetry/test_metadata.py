import hashlib
from pathlib import Path

from dip_touchless.configuration import (
    resolve_config,
)
from dip_touchless.telemetry.metadata import (
    build_run_metadata,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

DEFAULT_CONFIG = (
    PROJECT_ROOT
    / "config"
    / "default.yaml"
)


def test_metadata_captures_experiment_warmup() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "experiment": {
                "experiment_id": "A1",
                "condition": "F0",
                "trial_id": "trial-001",
                "warmup_s": 2.5,
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id="metadata-test-run",
        code_revision="test-revision",
    )

    assert metadata["experiment_id"] == "A1"
    assert metadata["condition"] == "F0"
    assert metadata["trial_id"] == "trial-001"
    assert metadata["warmup_s"] == 2.5


def test_metadata_hashes_model_and_replay_source(
    tmp_path: Path,
) -> None:
    model = tmp_path / "model.task"
    source = tmp_path / "source.mp4"

    model.write_bytes(b"model-fixture")
    source.write_bytes(b"replay-fixture")

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": str(source),
            },
            "tracking": {
                "model_path": str(model),
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id="checksum-test",
        code_revision="test-revision",
    )

    assert (
        metadata["provider"]["model_checksum"]
        == hashlib.sha256(
            b"model-fixture"
        ).hexdigest()
    )
    assert (
        metadata["source_data"]["sha256"]
        == hashlib.sha256(
            b"replay-fixture"
        ).hexdigest()
    )
    assert metadata["source_data"]["identity"] == str(source)


def test_metadata_keeps_missing_file_hashes_unavailable(
    tmp_path: Path,
) -> None:
    missing_source = tmp_path / "missing.mp4"
    missing_model = tmp_path / "missing.task"

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": str(missing_source),
            },
            "tracking": {
                "model_path": str(missing_model),
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id="missing-file-test",
        code_revision="test-revision",
    )

    assert metadata["provider"]["model_checksum"] is None
    assert metadata["source_data"]["sha256"] is None
