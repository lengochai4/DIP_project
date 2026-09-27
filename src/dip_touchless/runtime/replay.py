"""Deterministic Raw replay runtime."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from typing import Any

from dip_touchless.core import (
    FrameSource,
    LandmarkFilter,
    LandmarkProvider,
    RunLogger,
    StageTimings,
    TrackingFrame,
)
from dip_touchless.tracking import MeasurementValidator


class ReplayRuntime:
    """Run the pre-G2 Raw pipeline over a replay-compatible FrameSource."""

    def __init__(
        self,
        *,
        source: FrameSource,
        provider: LandmarkProvider,
        validator: MeasurementValidator,
        landmark_filter: LandmarkFilter,
        logger: RunLogger,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._source = source
        self._provider = provider
        self._validator = validator
        self._filter = landmark_filter
        self._logger = logger
        self._clock = clock

    def run(
        self,
        *,
        metadata: Mapping[str, Any],
        resolved_config: Mapping[str, Any],
    ) -> int:
        """Execute one replay run and return the processed frame count."""

        processed_frames = 0

        try:
            self._logger.start_run(
                metadata,
                resolved_config,
            )

            self._filter.reset()
            self._source.open()

            while True:
                packet = self._source.read()

                if packet is None:
                    break

                tracking_start = self._clock()

                observation = self._provider.process(
                    packet
                )

                observation = self._validator.validate(
                    observation
                )

                tracking_end = self._clock()

                if observation.frame_id != packet.frame_id:
                    raise RuntimeError(
                        "provider changed frame_id"
                    )

                if (
                    observation.timestamp_s
                    != packet.timestamp_s
                ):
                    raise RuntimeError(
                        "provider changed timestamp_s"
                    )

                filtering_start = self._clock()

                filtered_landmarks, diagnostics = (
                    self._filter.update(
                        observation
                    )
                )

                filtering_end = self._clock()

                tracking_ms = self._duration_ms(
                    tracking_start,
                    tracking_end,
                )

                filtering_ms = self._duration_ms(
                    filtering_start,
                    filtering_end,
                )

                # G1 has no preprocessing or gesture stage yet.
                preprocess_ms = 0.0
                gesture_ms = 0.0

                compute_total_ms = (
                    preprocess_ms
                    + tracking_ms
                    + filtering_ms
                    + gesture_ms
                )

                tracking_frame = TrackingFrame(
                    run_id=packet.run_id,
                    frame_id=packet.frame_id,
                    timestamp_s=packet.timestamp_s,
                    status=observation.status,
                    raw_landmarks=(
                        observation.landmarks
                    ),
                    filtered_landmarks=(
                        filtered_landmarks
                    ),
                    quality=observation.quality,
                    roi=None,
                    illumination=None,
                    filter_diagnostics=diagnostics,
                    timings=StageTimings(
                        preprocess_ms=preprocess_ms,
                        tracking_ms=tracking_ms,
                        filtering_ms=filtering_ms,
                        gesture_ms=gesture_ms,
                        compute_total_ms=(
                            compute_total_ms
                        ),
                    ),
                    events=(),
                )

                self._logger.log_tracking_frame(
                    tracking_frame
                )

                processed_frames += 1

        finally:
            try:
                self._source.close()
            finally:
                try:
                    self._provider.close()
                finally:
                    self._logger.close()

        return processed_frames

    def _duration_ms(
        self,
        start: float,
        end: float,
    ) -> float:
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
        ):
            raise RuntimeError(
                "runtime clock produced non-finite time"
            )

        if end < start:
            raise RuntimeError(
                "runtime clock moved backwards"
            )

        return (end - start) * 1000.0