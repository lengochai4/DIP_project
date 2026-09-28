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
