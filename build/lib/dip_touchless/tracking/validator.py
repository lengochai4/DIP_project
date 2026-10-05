"""Validation of project-domain landmark observations."""

from __future__ import annotations

import math

from dip_touchless.core import (
    CoordinateSpace,
    LandmarkObservation,
    TrackingStatus,
)


class MeasurementValidator:
    """Validate whether a landmark observation is usable downstream."""

    def validate(
        self,
        observation: LandmarkObservation,
    ) -> LandmarkObservation:
        if observation.frame_id < 0:
            raise ValueError("frame_id must be non-negative")

        if not math.isfinite(observation.timestamp_s):
            raise ValueError("timestamp_s must be finite")

        if observation.status in {
            TrackingStatus.NO_HAND,
            TrackingStatus.INVALID,
            TrackingStatus.TEMPORARY_LOSS,
        }:
            if observation.landmarks:
                raise ValueError(
                    "non-usable observation must not contain landmarks"
                )

            return observation

        if observation.status not in {
            TrackingStatus.VALID,
            TrackingStatus.REACQUIRED,
        }:
            raise ValueError(
                f"unsupported tracking status: {observation.status}"
            )

        if len(observation.landmarks) != 21:
            raise ValueError(
                "usable hand observation must contain 21 landmarks"
            )

        indices = [
            landmark.index
            for landmark in observation.landmarks
        ]

        if indices != list(range(21)):
            raise ValueError(
                "landmark indices must be exactly 0..20"
            )

        for landmark in observation.landmarks:
            if landmark.coordinate_space is not (
                CoordinateSpace.FRAME_NORMALIZED
            ):
                raise ValueError(
                    "tracking landmarks must use FRAME_NORMALIZED"
                )

            if not all(
                math.isfinite(value)
                for value in (
                    landmark.x,
                    landmark.y,
                    landmark.z,
                )
            ):
                raise ValueError(
                    "landmark coordinates must be finite"
                )

        if observation.handedness_score is not None:
            score = observation.handedness_score

            if (
                not math.isfinite(score)
                or not 0.0 <= score <= 1.0
            ):
                raise ValueError(
                    "handedness_score must be in [0, 1]"
                )

        return observation