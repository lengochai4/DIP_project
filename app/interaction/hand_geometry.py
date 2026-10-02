"""Explicit aspect-correct image geometry, no inferred confidence or metric z."""

import math
import numpy as np
from dip_touchless.core import CoordinateSpace
from .contracts import AnchorPose, HandState

PALM = (0, 5, 9, 13, 17)
CHAINS = (
    (1, 2, 3, 4),
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 16),
    (17, 18, 19, 20),
)
EDGES = tuple((a, b) for chain in CHAINS for a, b in zip((0, *chain), chain)) + (
    (5, 9),
    (9, 13),
    (13, 17),
)


def distance(a, b, aspect=1.0):
    return math.hypot((a[0] - b[0]) * aspect, a[1] - b[1])


def describe(landmarks, width, height, config, *, track_id="dominant", role="DOMINANT"):
    if (
        width <= 0
        or height <= 0
        or len(landmarks) != 21
        or {p.index for p in landmarks} != set(range(21))
    ):
        return None
    lm = sorted(landmarks, key=lambda p: p.index)
    if any(
        p.coordinate_space is not CoordinateSpace.FRAME_NORMALIZED
        or not all(math.isfinite(v) for v in (p.x, p.y, p.z))
        for p in lm
    ):
        return None
    xy = np.array([(p.x, p.y) for p in lm], dtype=float)
    aspect = width / height
    p = xy * (aspect, 1.0)
    span = float(np.linalg.norm(p[5] - p[17]))
    if span <= config.palm_epsilon:
        return None
    fingers = []
    for chain in CHAINS:
        q = p[list(chain)]
        lengths = np.linalg.norm(np.diff(q, axis=0), axis=1)
        if np.any(lengths <= config.palm_epsilon):
            return None
        angles = []
        for j in (1, 2):
            a, b = q[j - 1] - q[j], q[j + 1] - q[j]
            angles.append(
                math.acos(
                    float(
                        np.clip(
                            np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)),
                            -1,
                            1,
                        )
                    )
                )
            )
        straight = float(np.linalg.norm(q[-1] - q[0]) / sum(lengths))
        fingers.append(
            straight >= config.finger_straightness
            and min(angles) >= config.finger_angle_rad
        )
    fingers[0] = (
        fingers[0] and np.linalg.norm(p[4] - p[5]) / span >= config.thumb_spread
    )
    _, i, m, r, k = fingers
    pose = (
        "OPEN_PALM"
        if all(fingers)
        else (
            "POINT"
            if i and not (m or r or k)
            else "V_SIGN" if i and m and not (r or k) else "UNKNOWN"
        )
    )
    center = tuple(float(v) for v in xy[list(PALM)].mean(axis=0))
    transverse = p[17] - p[5]
    # z affects orientation cues only and is never used to measure distance.
    yaw = math.atan2(lm[17].z - lm[5].z, span)
    distal = float(np.linalg.norm(p[9] - p[0]))
    pitch = math.atan2(lm[9].z - lm[0].z, max(distal, config.palm_epsilon))
    palm = AnchorPose(
        center, span, math.atan2(transverse[1], transverse[0]), pitch, yaw
    )
    signature = tuple(
        float(np.linalg.norm(p[a] - p[b]) / span)
        for j, a in enumerate(PALM)
        for b in PALM[j + 1 :]
    )
    return HandState(
        track_id,
        role,
        pose,
        tuple(bool(v) for v in fingers),
        tuple(xy[8]),
        palm,
        float(np.linalg.norm(p[4] - p[8]) / span),
        True,
        signature,
    )
