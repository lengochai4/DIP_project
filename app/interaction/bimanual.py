"""Conservative image association; ambiguous crossings cancel rather than swap roles."""

from dataclasses import dataclass
from itertools import permutations
from .hand_geometry import distance


@dataclass(frozen=True)
class Detection:
    landmarks: tuple
    label: str | None = None


class HandAssociation:
    def __init__(self, config):
        self.config = config
        self.previous = {}
        self.reason = "INITIAL"

    def reset(self):
        self.previous = {}

    def update(self, detections, aspect=1.0):
        if not 1 <= len(detections) <= 2:
            self.reset()
            self.reason = "TOO_MANY_HANDS" if len(detections) > 2 else "NO_HAND"
            return {}
        centers = [
            tuple(
                sum(getattr(d.landmarks[i], axis) for i in (0, 5, 9, 13, 17)) / 5
                for axis in ("x", "y")
            )
            for d in detections
        ]
        if (
            len(centers) == 2
            and distance(*centers, aspect) <= self.config.association_margin
        ):
            self.reset()
            self.reason = "AMBIGUOUS_OVERLAP"
            return {}
        keys = tuple(self.previous)
        result = {}
        if len(keys) == len(detections):
            candidates = sorted(
                (
                    sum(
                        distance(self.previous[k], centers[p[j]], aspect)
                        for j, k in enumerate(keys)
                    ),
                    p,
                )
                for p in permutations(range(len(detections)))
            )
            cost, perm = candidates[0]
            if (
                len(candidates) > 1
                and candidates[1][0] - cost <= self.config.association_margin
                or any(
                    distance(self.previous[k], centers[perm[j]], aspect)
                    > self.config.association_distance
                    for j, k in enumerate(keys)
                )
            ):
                self.reset()
                self.reason = "ASSOCIATION_AMBIGUOUS"
                return {}
            result = {k: detections[perm[j]] for j, k in enumerate(keys)}
        elif len(keys) == 1 and len(detections) == 2:
            prev_k = keys[0]
            other_k = "Left" if prev_k == "Right" else "Right"
            d0 = distance(self.previous[prev_k], centers[0], aspect)
            d1 = distance(self.previous[prev_k], centers[1], aspect)
            if d0 <= self.config.association_distance and d0 <= d1:
                result = {prev_k: detections[0], other_k: detections[1]}
            elif d1 <= self.config.association_distance and d1 < d0:
                result = {prev_k: detections[1], other_k: detections[0]}
            else:
                if centers[0][0] <= centers[1][0]:
                    result = {"Left": detections[0], "Right": detections[1]}
                else:
                    result = {"Right": detections[0], "Left": detections[1]}
            self.reason = "ACQUIRING"
        elif len(keys) == 2 and len(detections) == 1:
            d_left = distance(self.previous.get("Left", (999.0, 999.0)), centers[0], aspect)
            d_right = distance(self.previous.get("Right", (999.0, 999.0)), centers[0], aspect)
            if d_left < d_right and d_left <= self.config.association_distance:
                result = {"Left": detections[0]}
            elif d_right <= d_left and d_right <= self.config.association_distance:
                result = {"Right": detections[0]}
            else:
                label = detections[0].label if detections[0].label in {"Left", "Right"} else "Right"
                result = {label: detections[0]}
            self.reason = "ACQUIRING"
        else:
            if len(detections) == 2:
                labels = [d.label for d in detections]
                if set(labels) == {"Left", "Right"}:
                    result = dict(zip(labels, detections))
                else:
                    if centers[0][0] <= centers[1][0]:
                        result = {"Left": detections[0], "Right": detections[1]}
                    else:
                        result = {"Right": detections[0], "Left": detections[1]}
                self.reason = "ACQUIRING"
            else:
                label = detections[0].label
                if label not in {"Left", "Right"}:
                    label = "Right"
                result = {label: detections[0]}
                self.reason = "ACQUIRING"
        self.previous = {k: centers[detections.index(v)] for k, v in result.items()}
        self.reason = "TRACKING" if len(keys) == len(detections) else "ACQUIRING"
        return result
