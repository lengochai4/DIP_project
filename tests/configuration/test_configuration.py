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