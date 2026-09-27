from pathlib import Path

import pytest
import yaml

from dip_touchless.configuration import (
    ConfigValidationError,
    resolve_config,
    write_resolved_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"


def test_default_config_resolves() -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    assert resolved.data["runtime"]["mode"] == "realtime"
    assert len(resolved.sha256) == 64


def test_override_has_highest_precedence() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": "sample.mp4",
            }
        },
    )

    assert resolved.data["runtime"]["mode"] == "replay"
    assert (
        resolved.data["runtime"]["replay_source"]
        == "sample.mp4"
    )


def test_profile_overrides_defaults(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"

    profile_path.write_text(
        """
camera:
  requested_fps: 60
""".strip(),
        encoding="utf-8",
    )

    resolved = resolve_config(
        DEFAULT_CONFIG,
        profile_path=profile_path,
    )

    assert resolved.data["camera"]["requested_fps"] == 60
    assert resolved.data["camera"]["width"] == 640


def test_explicit_override_wins_over_profile(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "profile.yaml"

    profile_path.write_text(
        """
runtime:
  mode: replay
  replay_source: profile.mp4
""".strip(),
        encoding="utf-8",
    )

    resolved = resolve_config(
        DEFAULT_CONFIG,
        profile_path=profile_path,
        overrides={
            "runtime": {
                "replay_source": "override.mp4",
            }
        },
    )

    assert resolved.data["runtime"]["mode"] == "replay"
    assert (
        resolved.data["runtime"]["replay_source"]
        == "override.mp4"
    )


def test_config_hash_is_deterministic() -> None:
    first = resolve_config(DEFAULT_CONFIG)
    second = resolve_config(DEFAULT_CONFIG)

    assert first.serialized_yaml == second.serialized_yaml
    assert first.sha256 == second.sha256


def test_different_config_changes_hash() -> None:
    first = resolve_config(DEFAULT_CONFIG)

    second = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "camera": {
                "requested_fps": 60,
            }
        },
    )

    assert first.sha256 != second.sha256


def test_resolved_configuration_is_immutable() -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    with pytest.raises(TypeError):
        resolved.data["camera"]["width"] = 1920


def test_invalid_pinch_hysteresis_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    "pinch_on": 0.5,
                    "pinch_off": 0.4,
                }
            },
        )


def test_invalid_derivative_cutoff_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "derivative_cutoff_hz": 0,
                }
            },
        )


def test_write_resolved_config(tmp_path: Path) -> None:
    resolved = resolve_config(DEFAULT_CONFIG)
    output = tmp_path / "resolved_config.yaml"

    write_resolved_config(resolved, output)

    assert output.exists()

    parsed = yaml.safe_load(
        output.read_text(encoding="utf-8")
    )

    assert parsed["project"]["name"] == "DIP Touchless STEM"


def test_invalid_tracking_confidence_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "tracking": {
                    "min_tracking_confidence": 1.1,
                }
            },
        )


def test_multi_hand_mode_is_rejected_for_baseline() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "tracking": {
                    "num_hands": 2,
                }
            },
        )


def test_negative_coast_expand_ratio_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "roi": {
                    "coast_expand_ratio": -0.1,
                }
            },
        )


def test_non_positive_roi_min_width_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "roi": {
                    "min_width": 0,
                }
            },
        )


def test_non_positive_roi_min_height_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "roi": {
                    "min_height": 0,
                }
            },
        )


def test_roi_min_width_cannot_exceed_camera_width() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "camera": {
                    "width": 640,
                },
                "roi": {
                    "min_width": 641,
                },
            },
        )


def test_roi_min_height_cannot_exceed_camera_height() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "camera": {
                    "height": 480,
                },
                "roi": {
                    "min_height": 481,
                },
            },
        )


def test_low_light_hysteresis_order_is_validated() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "illumination": {
                    "low_light_enter_v": 90.0,
                    "low_light_exit_v": 80.0,
                }
            },
        )


def test_low_contrast_hysteresis_order_is_validated() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "illumination": {
                    "low_contrast_enter_range_v": 50.0,
                    "low_contrast_exit_range_v": 40.0,
                }
            },
        )


def test_illumination_threshold_must_be_in_byte_range() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "illumination": {
                    "low_light_enter_v": -1.0,
                }
            },
        )


def test_invalid_clahe_policy_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "clahe": {
                    "policy": "unknown",
                }
            },
        )


def test_default_fixed_filter_parameters_are_valid() -> None:
    resolved = resolve_config(DEFAULT_CONFIG)

    filter_config = resolved.data["filter"]

    assert filter_config["mode"] == "RAW"
    assert filter_config["min_cutoff_hz"] == pytest.approx(1.0)
    assert filter_config["beta"] == pytest.approx(0.0)
    assert (
        filter_config["derivative_cutoff_hz"]
        == pytest.approx(1.0)
    )
    assert filter_config["reset_gap_s"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    "mode",
    [
        "",
        "FIXED",
        "ONE_EURO",
        "UNKNOWN",
    ],
)
def test_invalid_filter_mode_is_rejected(
    mode: str,
) -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "mode": mode,
                }
            },
        )


@pytest.mark.parametrize(
    "min_cutoff_hz",
    [
        0.0,
        -1.0,
    ],
)
def test_invalid_min_cutoff_is_rejected(
    min_cutoff_hz: float,
) -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "min_cutoff_hz": (
                        min_cutoff_hz
                    ),
                }
            },
        )


def test_negative_fixed_beta_is_rejected() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "beta": -0.1,
                }
            },
        )


def test_zero_fixed_beta_is_allowed() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "filter": {
                "beta": 0.0,
            }
        },
    )

    assert (
        resolved.data["filter"]["beta"]
        == pytest.approx(0.0)
    )