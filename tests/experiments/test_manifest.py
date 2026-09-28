from pathlib import Path

import pytest

from experiments.manifest import (
    ManifestValidationError,
    load_experiment_manifest,
)


def _write_manifest(
    path: Path,
    body: str,
) -> None:
    path.write_text(
        body.strip(),
        encoding="utf-8",
    )


def test_load_valid_manifest(
    tmp_path: Path,
) -> None:
    manifest_path = (
        tmp_path / "manifest.yaml"
    )

    _write_manifest(
        manifest_path,
        """
schema_version: "1"
experiment_id: "A1"
profiles: [f0, f1, f2]
model: "model.task"
warmup_s: 1.0

analysis_window:
  start_s: 1.0
  end_s: 10.0

primary_metric: "radial_rms_jitter"

planned_comparisons:
  - [f0, f1]
  - [f0, f2]

exclusion_rules:
  - "startup warmup"
  - "corrupted source"
  - "invalid timestamps"

trials:
  - trial_id: "trial-001"
    source: "trial-001.mp4"
  - trial_id: "trial-002"
    source: "trial-002.mp4"
""",
    )

    manifest = load_experiment_manifest(
        manifest_path
    )

    assert manifest.experiment_id == "A1"
    assert manifest.profiles == (
        "f0",
        "f1",
        "f2",
    )
    assert manifest.warmup_s == 1.0
    assert manifest.analysis_start_s == 1.0
    assert manifest.analysis_end_s == 10.0
    assert len(manifest.trials) == 2

    assert manifest.model == (
        tmp_path / "model.task"
    ).resolve()

    assert manifest.trials[0].source == (
        tmp_path / "trial-001.mp4"
    ).resolve()


@pytest.mark.parametrize(
    "profiles",
    [
        "[]",
        "[f0, f0]",
        "[f0, unknown]",
    ],
)
def test_invalid_profiles_are_rejected(
    tmp_path: Path,
    profiles: str,
) -> None:
    manifest_path = (
        tmp_path / "manifest.yaml"
    )

    _write_manifest(
        manifest_path,
        f"""
schema_version: "1"
experiment_id: "A1"
profiles: {profiles}
model: "model.task"
warmup_s: 0.0

analysis_window:
  start_s: 0.0
  end_s: 10.0

primary_metric: "radial_rms_jitter"

planned_comparisons:
  - [f0, f1]

exclusion_rules:
  - "startup warmup"

trials:
  - trial_id: "trial-001"
    source: "trial.mp4"
""",
    )

    with pytest.raises(
        ManifestValidationError
    ):
        load_experiment_manifest(
            manifest_path
        )


def test_analysis_window_cannot_enter_warmup(
    tmp_path: Path,
) -> None:
    manifest_path = (
        tmp_path / "manifest.yaml"
    )

    _write_manifest(
        manifest_path,
        """
schema_version: "1"
experiment_id: "A1"
profiles: [f0, f1, f2]
model: "model.task"
warmup_s: 2.0

analysis_window:
  start_s: 1.0
  end_s: 10.0

primary_metric: "radial_rms_jitter"

planned_comparisons:
  - [f0, f1]

exclusion_rules:
  - "startup warmup"

trials:
  - trial_id: "trial-001"
    source: "trial.mp4"
""",
    )

    with pytest.raises(
        ManifestValidationError,
        match="warmup",
    ):
        load_experiment_manifest(
            manifest_path
        )


def test_duplicate_trial_ids_are_rejected(
    tmp_path: Path,
) -> None:
    manifest_path = (
        tmp_path / "manifest.yaml"
    )

    _write_manifest(
        manifest_path,
        """
schema_version: "1"
experiment_id: "A1"
profiles: [f0, f1, f2]
model: "model.task"
warmup_s: 0.0

analysis_window:
  start_s: 0.0
  end_s: null

primary_metric: "radial_rms_jitter"

planned_comparisons:
  - [f0, f1]

exclusion_rules:
  - "corrupted source"

trials:
  - trial_id: "same"
    source: "a.mp4"
  - trial_id: "same"
    source: "b.mp4"
""",
    )

    with pytest.raises(
        ManifestValidationError,
        match="unique",
    ):
        load_experiment_manifest(
            manifest_path
        )
