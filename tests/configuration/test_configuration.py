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


def test_default_camera_index_is_valid() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG
    )

    assert resolved.data["camera"]["index"] == 0


@pytest.mark.parametrize(
    "value",
    [
        -1,
        1.5,
        True,
        "0",
    ],
)
def test_invalid_camera_index_is_rejected(
    value,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "camera": {
                    "index": value,
                },
            },
        )


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


def test_default_adaptive_filter_parameters_are_valid() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG
    )

    adaptive = (
        resolved.data["filter"]["adaptive"]
    )

    assert adaptive[
        "base_cutoff_hz"
    ] == pytest.approx(1.0)

    assert adaptive["beta_min"] == pytest.approx(
        0.0
    )

    assert adaptive["beta_base"] == pytest.approx(
        0.0
    )

    assert adaptive["beta_max"] == pytest.approx(
        1.0
    )

    assert adaptive[
        "velocity_gain"
    ] == pytest.approx(0.1)

    assert adaptive[
        "velocity_max"
    ] == pytest.approx(10.0)

    assert adaptive[
        "final_cutoff_min_hz"
    ] == pytest.approx(1.0)

    assert adaptive[
        "final_cutoff_max_hz"
    ] == pytest.approx(10.0)

    assert (
        adaptive[
            "quality_adaptation_enabled"
        ]
        is False
    )


def test_adaptive_filter_mode_is_allowed() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "filter": {
                "mode": (
                    "ONE_EURO_ADAPTIVE"
                ),
            }
        },
    )

    assert (
        resolved.data["filter"]["mode"]
        == "ONE_EURO_ADAPTIVE"
    )


@pytest.mark.parametrize(
    (
        "beta_min",
        "beta_base",
        "beta_max",
    ),
    [
        (0.5, 0.4, 1.0),
        (0.0, 1.1, 1.0),
        (1.0, 0.5, 0.4),
    ],
)
def test_invalid_adaptive_beta_order_is_rejected(
    beta_min: float,
    beta_base: float,
    beta_max: float,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "adaptive": {
                        "beta_min": beta_min,
                        "beta_base": beta_base,
                        "beta_max": beta_max,
                    }
                }
            },
        )


def test_negative_velocity_gain_is_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "adaptive": {
                        "velocity_gain": -0.1,
                    }
                }
            },
        )


@pytest.mark.parametrize(
    "velocity_max",
    [
        0.0,
        -1.0,
        float("inf"),
        float("nan"),
    ],
)
def test_invalid_velocity_max_is_rejected(
    velocity_max: float,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "adaptive": {
                        "velocity_max": (
                            velocity_max
                        ),
                    }
                }
            },
        )


def test_velocity_max_may_be_disabled() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "filter": {
                "adaptive": {
                    "velocity_max": None,
                }
            }
        },
    )

    assert (
        resolved.data[
            "filter"
        ][
            "adaptive"
        ][
            "velocity_max"
        ]
        is None
    )


def test_invalid_final_cutoff_order_is_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "adaptive": {
                        "final_cutoff_min_hz": 5.0,
                        "final_cutoff_max_hz": 5.0,
                    }
                }
            },
        )


def test_quality_adaptation_cannot_be_enabled_without_source() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "filter": {
                    "adaptive": {
                        "quality_adaptation_enabled": (
                            True
                        ),
                    }
                }
            },
        )


def test_default_gesture_configuration_is_resolved() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG
    )

    gesture = resolved.data["gesture"]

    assert gesture["pointer_landmark_index"] == 8
    assert gesture["pinch_thumb_landmark_index"] == 4
    assert gesture["pinch_index_landmark_index"] == 8

    assert gesture["hand_scale_landmark_a"] == 5
    assert gesture["hand_scale_landmark_b"] == 17

    assert gesture["hand_scale_epsilon"] > 0.0

    assert (
        gesture["pinch_on"]
        < gesture["pinch_off"]
    )

    assert gesture["rotation_deadzone"] >= 0.0
    assert gesture["rotation_gain"] >= 0.0
    assert gesture["rotation_max_delta_rad"] > 0.0

    assert gesture["scale_deadzone"] >= 0.0
    assert gesture["scale_gain"] >= 0.0
    assert gesture["scale_max_delta"] > 0.0


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("pointer_landmark_index", -1),
        ("pointer_landmark_index", 1.5),
        ("pointer_landmark_index", True),
        ("pinch_thumb_landmark_index", -1),
        ("pinch_index_landmark_index", -1),
        ("hand_scale_landmark_a", -1),
        ("hand_scale_landmark_b", -1),
    ],
)
def test_invalid_gesture_landmark_index_is_rejected(
    key: str,
    value: object,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    key: value,
                },
            },
        )


def test_same_pinch_landmarks_are_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    "pinch_thumb_landmark_index": 8,
                    "pinch_index_landmark_index": 8,
                },
            },
        )


def test_same_hand_scale_landmarks_are_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    "hand_scale_landmark_a": 5,
                    "hand_scale_landmark_b": 5,
                },
            },
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("hand_scale_epsilon", 0.0),
        ("hand_scale_epsilon", -0.1),
        ("rotation_deadzone", -0.1),
        ("rotation_gain", -0.1),
        ("rotation_max_delta_rad", 0.0),
        ("scale_deadzone", -0.1),
        ("scale_gain", -0.1),
        ("scale_max_delta", 0.0),
    ],
)
def test_invalid_gesture_numeric_value_is_rejected(
    key: str,
    value: float,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    key: value,
                },
            },
        )


def test_negative_pinch_threshold_is_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "gesture": {
                    "pinch_on": -0.1,
                },
            },
        )


def test_default_renderer_scene_configuration_is_resolved() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG
    )

    renderer = resolved.data[
        "renderer"
    ]

    assert renderer["target_fps"] > 0

    assert (
        renderer["min_scale"]
        <= renderer["initial_scale"]
        <= renderer["max_scale"]
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("target_fps", 0.0),
        ("initial_scale", 0.0),
        ("min_scale", 0.0),
        ("max_scale", 0.0),
    ],
)
def test_invalid_renderer_positive_value_is_rejected(
    key: str,
    value: float,
) -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "renderer": {
                    key: value,
                },
            },
        )


def test_invalid_renderer_scale_order_is_rejected() -> None:
    with pytest.raises(
        ConfigValidationError
    ):
        resolve_config(
            DEFAULT_CONFIG,
            overrides={
                "renderer": {
                    "min_scale": 2.0,
                    "initial_scale": 1.0,
                    "max_scale": 3.0,
                },
            },
        )
