"""Project-wide domain enumerations.

These enums define project-owned semantics and prevent provider-specific
constants from leaking into downstream modules.
"""

from enum import Enum


class ColorSpace(str, Enum):
    BGR = "BGR"
    RGB = "RGB"
    HSV = "HSV"
    GRAY = "GRAY"


class TrackingStatus(str, Enum):
    NO_HAND = "NO_HAND"
    VALID = "VALID"
    TEMPORARY_LOSS = "TEMPORARY_LOSS"
    REACQUIRED = "REACQUIRED"
    INVALID = "INVALID"


class ROIState(str, Enum):
    SEARCHING = "SEARCHING"
    TRACKING = "TRACKING"
    COASTING = "COASTING"


class IlluminationState(str, Enum):
    NORMAL = "NORMAL"
    LOW_LIGHT = "LOW_LIGHT"
    LOW_CONTRAST = "LOW_CONTRAST"
    DIFFICULT = "DIFFICULT"


class FilterMode(str, Enum):
    RAW = "RAW"
    ONE_EURO_FIXED = "ONE_EURO_FIXED"
    ONE_EURO_ADAPTIVE = "ONE_EURO_ADAPTIVE"


class QualitySource(str, Enum):
    NONE = "NONE"
    PROVIDER_DOCUMENTED = "PROVIDER_DOCUMENTED"
    EXPERIMENTAL_DERIVED = "EXPERIMENTAL_DERIVED"


class CoordinateSpace(str, Enum):
    FRAME_PIXEL = "FRAME_PIXEL"
    FRAME_NORMALIZED = "FRAME_NORMALIZED"
    VIEWPORT = "VIEWPORT"
    NDC = "NDC"
    WORLD_RENDER = "WORLD_RENDER"
    MODEL_RELATIVE_Z = "MODEL_RELATIVE_Z"