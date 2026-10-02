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
            self.reason = "NO_HAND"
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
            # Contrary labels are an explicit domain break, never a silent hand switch.
            if any(
                d.label in {"Left", "Right"} and d.label != k for k, d in result.items()
            ):
                self.reset()
                self.reason = "ROLE_CHANGED"
                return {}
        else:
            labels = [d.label for d in detections]
            if any(l not in {"Left", "Right"} for l in labels) or len(
                set(labels)
            ) != len(labels):
                self.reset()
                self.reason = "HANDEDNESS_UNAVAILABLE"
                return {}
            result = dict(zip(labels, detections))
            self.reason = "ACQUIRING"
        self.previous = {k: centers[detections.index(v)] for k, v in result.items()}
        return result
