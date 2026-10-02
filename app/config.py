"""Explicit engineering defaults and local preferences, separate from G7 config."""

from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProductConfig:
    max_gap_s: float = 0.5
    pose_dwell_s: float = 0.18
    finger_straightness: float = 0.82
    finger_angle_rad: float = 2.35
    thumb_spread: float = 0.45
    palm_epsilon: float = 0.000001
    release_duration_s: float = 1.2
    release_min_samples: int = 12
    release_max_mad: float = 0.08
    reference_shape_delta: float = 0.30
    pinch_enter: float = 0.60
    pinch_exit: float = 0.25
    pinch_progress: float = 0.18
    pinch_dwell_s: float = 0.20
    rearm_s: float = 0.25
    closing_timeout_s: float = 3.0
    association_distance: float = 0.4
    association_margin: float = 0.04
    measure_dwell_s: float = 0.5
    measure_motion: float = 0.025
    anchor_tau_s: float = 0.10
    anchor_gain: float = 1.6
    min_scale: float = 0.2
    max_scale: float = 5.0
    motion_gain: float = 3.0
    max_delta: float = 0.12
    pointer_gain: float = 1.0
    dwell_select_s: float = 1.2
    filter_min_cutoff_hz: float = 1.0
    filter_beta: float = 0.05
    filter_derivative_cutoff_hz: float = 1.0

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or v <= 0
            ):
                raise ValueError(f"{f.name} must be finite and positive")
        if not 0 < self.pinch_exit < self.pinch_enter < 1:
            raise ValueError("pinch boundaries must satisfy 0 < exit < enter < 1")
        if not 0 < self.finger_straightness < 1 or self.finger_angle_rad >= math.pi:
            raise ValueError("invalid finger geometry policies")
        if type(self.release_min_samples) is not int or self.release_min_samples < 2:
            raise ValueError("reference requires at least two samples")
        if (
            self.min_scale >= self.max_scale
            or self.closing_timeout_s <= self.pinch_dwell_s
        ):
            raise ValueError("invalid scale/closing bounds")

    @classmethod
    def load(cls, path=None):
        data = yaml.safe_load(
            Path(path or ROOT / "config/product_v2.yaml").read_text(encoding="utf-8")
        )
        if not isinstance(data, dict):
            raise ValueError("product profile must be a mapping")
        return cls(**data)


@dataclass(frozen=True)
class Settings:
    dominant_hand: str = "Right"
    engine: str = "PRODUCT"
    pointer_sensitivity: float = 1.0
    manipulation_sensitivity: float = 1.0
    mirror: bool = True
    skeleton: bool = True
    gesture_labels: bool = True
    grid: bool = True
    object_labels: bool = True
    mouse_fallback: bool = True
    keyboard_shortcuts: bool = True
    dwell_select: bool = False
    reduced_motion: bool = False
    diagnostics: bool = False
    camera_index: int = 0

    def __post_init__(self):
        if self.dominant_hand not in {"Left", "Right"} or self.engine not in {
            "PRODUCT",
            "LEGACY",
        }:
            raise ValueError("invalid hand or engine")
        for name in ("pointer_sensitivity", "manipulation_sensitivity"):
            v = getattr(self, name)
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or not 0.25 <= v <= 3
            ):
                raise ValueError("sensitivity must be in [.25, 3]")
        if type(self.camera_index) is not int or self.camera_index < 0:
            raise ValueError("camera index must be nonnegative")
        for name in (
            "mirror",
            "skeleton",
            "gesture_labels",
            "grid",
            "object_labels",
            "mouse_fallback",
            "keyboard_shortcuts",
            "dwell_select",
            "reduced_motion",
            "diagnostics",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")

    @classmethod
    def load(cls, path):
        p = Path(path)
        return cls(**json.loads(p.read_text(encoding="utf-8"))) if p.exists() else cls()

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        temp = p.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        temp.replace(p)
