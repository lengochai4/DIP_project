"""Product-only semantic contracts; no change to Core InteractionState."""

from dataclasses import dataclass
from enum import Enum
import math


class IntentType(str, Enum):
    POINT = "POINT"
    SELECT = "SELECT"
    GRAB = "GRAB"
    DRAG = "DRAG"
    SCALE = "SCALE"
    ANCHOR = "ANCHOR"
    RELEASE = "RELEASE"
    MEASURE_BEGIN = "MEASURE_BEGIN"
    MEASURE_UPDATE = "MEASURE_UPDATE"
    MEASURE_COMMIT = "MEASURE_COMMIT"
    TOOL_BEGIN = "TOOL_BEGIN"
    TOOL_UPDATE = "TOOL_UPDATE"
    TOOL_COMMIT = "TOOL_COMMIT"
    CANCEL = "CANCEL"


class Phase(str, Enum):
    BEGIN = "BEGIN"
    UPDATE = "UPDATE"
    END = "END"
    CANCEL = "CANCEL"


class Owner(str, Enum):
    SYSTEM_MODAL = "SYSTEM_MODAL"
    CALIBRATION = "CALIBRATION"
    UI = "UI"
    TOOL = "TOOL"
    SCENE = "SCENE"


@dataclass(frozen=True)
class AnchorPose:
    center_xy: tuple[float, float]
    span: float
    roll_rad: float
    # Visual orientation cues, never metric camera pose/depth.
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0


@dataclass(frozen=True)
class GestureIntent:
    type: IntentType
    phase: Phase = Phase.UPDATE
    hand_role: str = "DOMINANT"
    pointer_xy: tuple[float, float] | None = None
    delta_xy: tuple[float, float] = (0.0, 0.0)
    scale_factor: float = 1.0
    world_or_scene_point: tuple[float, float, float] | None = None
    anchor_pose: AnchorPose | None = None
    tool_id: str | None = None
    validity: bool = True
    reason: str = ""
    cycle_id: int = 0
    owner: Owner = Owner.SCENE
    points: tuple[tuple[float, float, float], ...] = ()
    input_source: str = "GESTURE"

    def __post_init__(self):
        if (
            not isinstance(self.type, IntentType)
            or not isinstance(self.phase, Phase)
            or not isinstance(self.owner, Owner)
        ):
            raise ValueError("typed intent enums required")
        numbers = [*self.delta_xy, self.scale_factor]
        if self.pointer_xy is not None:
            numbers.extend(self.pointer_xy)
        if self.world_or_scene_point is not None:
            numbers.extend(self.world_or_scene_point)
        numbers.extend(v for p in self.points for v in p)
        if (
            not all(math.isfinite(v) for v in numbers)
            or self.scale_factor <= 0
            or self.cycle_id < 0
        ):
            raise ValueError("intent geometry must be finite; scale positive")
        if not self.validity and self.type is not IntentType.CANCEL:
            raise ValueError("invalid data can only cancel")
        if self.input_source not in {"GESTURE", "MANUAL"}:
            raise ValueError("unknown product input source")


@dataclass(frozen=True)
class HandState:
    track_id: str
    role: str
    pose: str
    fingers: tuple[bool, ...]
    pointer_xy: tuple[float, float]
    palm: AnchorPose
    pinch_ratio: float
    valid: bool = True
    palm_signature: tuple[float, ...] = ()
