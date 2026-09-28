from pathlib import Path

import pytest

from dip_touchless.configuration import (
    resolve_config,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkFilter,
    FixedOneEuroLandmarkFilter,
    RawLandmarkFilter,
)
from experiments.run_replay import (
    DEFAULT_CONFIG,
    PROFILE_DIR,
    build_landmark_filter,
    resolve_experiment_config,
)


@pytest.mark.parametrize(
    (
        "profile_name",
        "expected_type",
    ),
    [
        (
            "f0",
            RawLandmarkFilter,
        ),
        (
            "f1",
            FixedOneEuroLandmarkFilter,
        ),
        (
            "f2",
            AdaptiveOneEuroLandmarkFilter,
        ),
        (
            "p0",
            RawLandmarkFilter,
        ),
        (
            "p1",
            RawLandmarkFilter,
        ),
    ],
)
def test_build_landmark_filter_matches_profile(
    profile_name,
    expected_type,
) -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        profile_path=(
            PROFILE_DIR
            / f"{profile_name}.yaml"
        ),
    )

    landmark_filter = build_landmark_filter(
        resolved.to_dict()
    )

    assert isinstance(
        landmark_filter,
        expected_type,
    )


@pytest.mark.parametrize(
    "profile_name",
    [
        "f0",
        "f1",
        "f2",
        "p0",
        "p1",
    ],
)
def test_single_replay_resolution_captures_identity(
    tmp_path: Path,
    profile_name: str,
) -> None:
    source = tmp_path / "source.avi"
    model = tmp_path / "model.task"

    resolved = resolve_experiment_config(
        profile_name=profile_name,
        source=source,
        model=model,
        experiment_id="g6-smoke",
        trial_id="trial-001",
        warmup_s=1.5,
        output_dir=tmp_path / "runs",
    )

    config = resolved.to_dict()

    assert (
        config["runtime"]["mode"]
        == "replay"
    )
    assert (
        config["runtime"]["replay_source"]
        == str(source)
    )
    assert (
        config["tracking"]["model_path"]
        == str(model)
    )
    assert (
        config["experiment"]["experiment_id"]
        == "g6-smoke"
    )
    assert (
        config["experiment"]["condition"]
        == profile_name.upper()
    )
    assert (
        config["experiment"]["trial_id"]
        == "trial-001"
    )
    assert (
        config["experiment"]["warmup_s"]
        == 1.5
    )
    assert (
        config["renderer"]["enabled"]
        is False
    )


def test_unknown_filter_mode_is_rejected() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
    )

    config = resolved.to_dict()
    config["filter"]["mode"] = "UNKNOWN"

    with pytest.raises(
        ValueError,
        match="unsupported filter mode",
    ):
        build_landmark_filter(config)
