"""Semantic validation for resolved project configuration."""

from __future__ import annotations

import math

from typing import Any, Mapping


REQUIRED_SECTIONS = {
    "project",
    "camera",
    "runtime",
    "roi",
    "illumination",
    "clahe",
    "tracking",
    "filter",
    "gesture",
    "logging",
    "experiment",
    "renderer",
}


class ConfigValidationError(ValueError):
    """Raised when a resolved configuration violates project constraints."""


def _require_positive_number(
    section: Mapping[str, Any],
    key: str,
    section_name: str,
) -> None:
    value = section.get(key)

    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ConfigValidationError(
            f"{section_name}.{key} must be a positive number"
        )


def _require_non_negative_number(
    section: Mapping[str, Any],
    key: str,
    section_name: str,
) -> None:
    value = section.get(key)

    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ConfigValidationError(
            f"{section_name}.{key} must be a non-negative number"
        )


def _require_unit_interval(
    section: Mapping[str, Any],
    key: str,
    section_name: str,
) -> None:
    value = section.get(key)

    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0.0 <= value <= 1.0
    ):
        raise ConfigValidationError(
            f"{section_name}.{key} must be in [0, 1]"
        )


def validate_config(config: Mapping[str, Any]) -> None:
    """Validate project-level configuration semantics."""

    missing = REQUIRED_SECTIONS.difference(config)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ConfigValidationError(
            f"missing required configuration sections: {missing_text}"
        )

    camera = config["camera"]
    runtime = config["runtime"]
    roi = config["roi"]
    illumination = config["illumination"]
    clahe = config["clahe"]
    tracking = config["tracking"]
    filter_config = config["filter"]
    gesture = config["gesture"]
    renderer = config["renderer"]

    _require_positive_number(camera, "width", "camera")
    _require_positive_number(camera, "height", "camera")
    _require_positive_number(camera, "requested_fps", "camera")

    if runtime.get("mode") not in {"realtime", "replay"}:
        raise ConfigValidationError(
            "runtime.mode must be 'realtime' or 'replay'"
        )

    padding_ratio = roi.get("padding_ratio")
    if (
        not isinstance(padding_ratio, (int, float))
        or isinstance(padding_ratio, bool)
        or padding_ratio < 0
    ):
        raise ConfigValidationError(
            "roi.padding_ratio must be a non-negative number"
        )

    coast_frames = roi.get("coast_frames")
    if (
        not isinstance(coast_frames, int)
        or isinstance(coast_frames, bool)
        or coast_frames < 0
    ):
        raise ConfigValidationError(
            "roi.coast_frames must be a non-negative integer"
        )

    coast_expand_ratio = roi.get("coast_expand_ratio")
    if (
        not isinstance(coast_expand_ratio, (int, float))
        or isinstance(coast_expand_ratio, bool)
        or coast_expand_ratio < 0
    ):
        raise ConfigValidationError(
            "roi.coast_expand_ratio must be a non-negative number"
        )

    min_width = roi.get("min_width")
    if (
        not isinstance(min_width, int)
        or isinstance(min_width, bool)
        or min_width <= 0
    ):
        raise ConfigValidationError(
            "roi.min_width must be a positive integer"
        )

    min_height = roi.get("min_height")
    if (
        not isinstance(min_height, int)
        or isinstance(min_height, bool)
        or min_height <= 0
    ):
        raise ConfigValidationError(
            "roi.min_height must be a positive integer"
        )

    if min_width > camera["width"]:
        raise ConfigValidationError(
            "roi.min_width must not exceed camera.width"
        )

    if min_height > camera["height"]:
        raise ConfigValidationError(
            "roi.min_height must not exceed camera.height"
        )

    ema_alpha = illumination.get("ema_alpha")
    if (
        not isinstance(ema_alpha, (int, float))
        or isinstance(ema_alpha, bool)
        or not 0 < ema_alpha <= 1
    ):
        raise ConfigValidationError(
            "illumination.ema_alpha must be in (0, 1]"
        )

    for key in (
        "low_light_enter_v",
        "low_light_exit_v",
        "low_contrast_enter_range_v",
        "low_contrast_exit_range_v",
    ):
        _require_byte_range_number(
            illumination,
            key,
            "illumination",
        )

    low_light_enter = illumination[
        "low_light_enter_v"
    ]
    low_light_exit = illumination[
        "low_light_exit_v"
    ]

    if not low_light_enter < low_light_exit:
        raise ConfigValidationError(
            "illumination.low_light_enter_v must be less than "
            "illumination.low_light_exit_v"
        )

    low_contrast_enter = illumination[
        "low_contrast_enter_range_v"
    ]
    low_contrast_exit = illumination[
        "low_contrast_exit_range_v"
    ]

    if not low_contrast_enter < low_contrast_exit:
        raise ConfigValidationError(
            "illumination.low_contrast_enter_range_v must be less than "
            "illumination.low_contrast_exit_range_v"
        )

    clip_limit = clahe.get("clip_limit")
    if (
        not isinstance(clip_limit, (int, float))
        or isinstance(clip_limit, bool)
        or clip_limit <= 0
    ):
        raise ConfigValidationError(
            "clahe.clip_limit must be positive"
        )

    tile_grid_size = clahe.get("tile_grid_size")
    if (
        not isinstance(tile_grid_size, list)
        or len(tile_grid_size) != 2
        or not all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
            for value in tile_grid_size
        )
    ):
        raise ConfigValidationError(
            "clahe.tile_grid_size must contain two positive integers"
        )

    clahe_policy = clahe.get("policy")

    if clahe_policy not in {
        "adaptive",
        "always",
        "bypass",
    }:
        raise ConfigValidationError(
            "clahe.policy must be 'adaptive', 'always', or 'bypass'"
        )

    num_hands = tracking.get("num_hands")

    if (
        not isinstance(num_hands, int)
        or isinstance(num_hands, bool)
        or num_hands != 1
    ):
        raise ConfigValidationError(
            "tracking.num_hands must be 1 for the current "
            "single-control-hand baseline"
        )

    for key in (
        "min_hand_detection_confidence",
        "min_hand_presence_confidence",
        "min_tracking_confidence",
    ):
        _require_unit_interval(
            tracking,
            key,
            "tracking",
        )

    # ------------------------------------------------------------------
    # Filter configuration
    # ------------------------------------------------------------------

    filter_mode = filter_config.get("mode")

    if filter_mode not in {
        "RAW",
        "ONE_EURO_FIXED",
        "ONE_EURO_ADAPTIVE",
    }:
        raise ConfigValidationError(
            "filter.mode must be "
            "'RAW', 'ONE_EURO_FIXED', or 'ONE_EURO_ADAPTIVE'"
        )

    _require_positive_number(
        filter_config,
        "min_cutoff_hz",
        "filter",
    )

    _require_non_negative_number(
        filter_config,
        "beta",
        "filter",
    )

    _require_positive_number(
        filter_config,
        "derivative_cutoff_hz",
        "filter",
    )

    _require_positive_number(
        filter_config,
        "reset_gap_s",
        "filter",
    )

    adaptive = filter_config.get(
        "adaptive"
    )

    if not isinstance(adaptive, Mapping):
        raise ConfigValidationError(
            "filter.adaptive must be a mapping"
        )

    _require_positive_number(
        adaptive,
        "base_cutoff_hz",
        "filter.adaptive",
    )

    for key in (
        "beta_min",
        "beta_base",
        "beta_max",
        "velocity_gain",
    ):
        _require_non_negative_number(
            adaptive,
            key,
            "filter.adaptive",
        )

    beta_min = adaptive["beta_min"]
    beta_base = adaptive["beta_base"]
    beta_max = adaptive["beta_max"]

    if not (
        beta_min
        <= beta_base
        <= beta_max
    ):
        raise ConfigValidationError(
            "filter.adaptive beta bounds must satisfy "
            "beta_min <= beta_base <= beta_max"
        )

    velocity_max = adaptive.get(
        "velocity_max"
    )

    if velocity_max is not None:
        if (
            not isinstance(
                velocity_max,
                (int, float),
            )
            or isinstance(
                velocity_max,
                bool,
            )
            or not math.isfinite(
                velocity_max
            )
            or velocity_max <= 0.0
        ):
            raise ConfigValidationError(
                "filter.adaptive.velocity_max "
                "must be positive and finite "
                "when enabled"
            )

    _require_positive_number(
        adaptive,
        "final_cutoff_min_hz",
        "filter.adaptive",
    )

    _require_positive_number(
        adaptive,
        "final_cutoff_max_hz",
        "filter.adaptive",
    )

    if not (
        adaptive["final_cutoff_min_hz"]
        < adaptive["final_cutoff_max_hz"]
    ):
        raise ConfigValidationError(
            "filter.adaptive final cutoff bounds "
            "must satisfy min < max"
        )

    quality_enabled = adaptive.get(
        "quality_adaptation_enabled"
    )

    if not isinstance(
        quality_enabled,
        bool,
    ):
        raise ConfigValidationError(
            "filter.adaptive."
            "quality_adaptation_enabled "
            "must be boolean"
        )

    if quality_enabled:
        raise ConfigValidationError(
            "filter.adaptive quality adaptation "
            "must remain disabled until a valid "
            "documented quality source is configured"
        )

    pinch_on = gesture.get("pinch_on")
    pinch_off = gesture.get("pinch_off")

    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        for value in (pinch_on, pinch_off)
    ):
        raise ConfigValidationError(
            "gesture pinch thresholds must be numeric"
        )

    if not pinch_on < pinch_off:
        raise ConfigValidationError(
            "gesture.pinch_on must be less than gesture.pinch_off"
        )

    if renderer.get("enabled"):
        _require_positive_number(
            renderer,
            "width",
            "renderer",
        )
        _require_positive_number(
            renderer,
            "height",
            "renderer",
        )


def _require_byte_range_number(
    section: Mapping[str, Any],
    key: str,
    section_name: str,
) -> None:
    value = section.get(key)

    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0.0 <= value <= 255.0
    ):
        raise ConfigValidationError(
            f"{section_name}.{key} must be in [0, 255]"
        )