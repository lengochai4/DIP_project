"""Semantic validation for resolved project configuration."""

from __future__ import annotations

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

    ema_alpha = illumination.get("ema_alpha")
    if (
        not isinstance(ema_alpha, (int, float))
        or isinstance(ema_alpha, bool)
        or not 0 < ema_alpha <= 1
    ):
        raise ConfigValidationError(
            "illumination.ema_alpha must be in (0, 1]"
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
        _require_positive_number(renderer, "width", "renderer")
        _require_positive_number(renderer, "height", "renderer")