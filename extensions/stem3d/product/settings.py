"""Validated application preferences; release references are never persisted."""

from dataclasses import asdict, dataclass
from enum import Enum
import json
import math
from pathlib import Path
import yaml


class InputMode(str, Enum):
    SIMPLE = "SIMPLE"
    LEGACY = "LEGACY"
    OBSERVE = "OBSERVE"
    FULL_HAND = "FULL_HAND"


@dataclass(frozen=True, slots=True)
class UserSettings:
    mode: InputMode = InputMode.LEGACY
    sensitivity: str = "standard"
    mirror: bool = False
    two_hand: bool = False

    def __post_init__(self):
        if not isinstance(self.mode, InputMode) or self.sensitivity not in {"gentle", "standard", "responsive"}:
            raise ValueError("unsupported application preference")
        if type(self.mirror) is not bool or type(self.two_hand) is not bool:
            raise ValueError("preference flags must be booleans")


@dataclass(frozen=True, slots=True)
class MotionProfile:
    rotation_gain: float
    rotation_deadzone: float
    rotation_max_delta: float
    scale_gain: float
    scale_deadzone: float
    scale_max_delta: float
    max_gap_s: float
    manual_rotation: float
    manual_scale: float

    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in asdict(self).values()):
            raise ValueError("motion parameters must be finite nonnegative numbers")
        if min(self.max_gap_s, self.rotation_max_delta, self.scale_max_delta) <= 0:
            raise ValueError("positive motion limits and gap required")


def load_application_profile(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"motion", "sensitivity", "two_hand"}:
        raise ValueError("application profile has missing/unknown fields")
    motion = MotionProfile(**data["motion"])
    gains = data["sensitivity"]
    if set(gains) != {"gentle", "standard", "responsive"} or any(
        type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in gains.values()
    ):
        raise ValueError("sensitivity profiles must be explicit positive gains")
    from .two_hand import TwoHandProfile
    TwoHandProfile(**data["two_hand"])
    return motion, dict(gains), dict(data["two_hand"])


def save_settings(path, settings):
    """Explicit save only. Persist ergonomic preferences, never a measured reference."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"schema": 1, **asdict(settings)}, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_settings(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema", "mode", "sensitivity", "mirror", "two_hand"} or data.pop("schema") != 1:
        raise ValueError("unsupported saved settings schema")
    # Command opt-in is per launch, even if a prior user preference was saved.
    saved_mode = InputMode(data["mode"])
    data["mode"] = saved_mode if saved_mode in {InputMode.SIMPLE, InputMode.LEGACY} else InputMode.OBSERVE
    data["two_hand"] = data["two_hand"] if saved_mode is InputMode.SIMPLE else False
    return UserSettings(**data)
