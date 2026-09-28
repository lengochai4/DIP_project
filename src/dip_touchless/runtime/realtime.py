"""Synchronous realtime interaction runtime."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from dip_touchless.core import (
    FramePacket,
    FrameSource,
    GestureEngine,
    InteractionState,
    IlluminationMetrics,
    LandmarkFilter,
    LandmarkProvider,
    ROI,
    RunLogger,
    StageTimings,
    TrackingFrame,
)
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
    ROIManager,
)
from dip_touchless.tracking import MeasurementValidator


class RealtimeRuntime:
    """Run the synchronous realtime interaction pipeline."""

    def __init__(
        self,
        *,
        source: FrameSource,
        provider: LandmarkProvider,
        validator: MeasurementValidator,
        landmark_filter: LandmarkFilter,
        logger: RunLogger,
        gesture_engine: GestureEngine | None = None,
        interaction_consumer: (
            Callable[[InteractionState], object]
            | None
        ) = None,
        stop_requested: (
            Callable[[], bool]
            | None
        ) = None,
        roi_manager: ROIManager | None = None,
        illumination_analyzer: IlluminationAnalyzer | None = None,
        illumination_decision: IlluminationDecisionStabilizer | None = None,
        adaptive_preprocessor: AdaptivePreprocessor | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        preprocessing_components = (
            roi_manager,
            illumination_analyzer,
            illumination_decision,
            adaptive_preprocessor,
        )

        supplied_count = sum(
            component is not None
            for component in preprocessing_components
        )

        if supplied_count not in {
            0,
            len(preprocessing_components),
        }:
            raise ValueError(
                "G2 preprocessing components must be supplied "
                "all together or all omitted"
            )

        self._source = source
        self._provider = provider
        self._validator = validator
        self._filter = landmark_filter
        self._logger = logger
        self._gesture_engine = gesture_engine
        self._interaction_consumer = (
            interaction_consumer
        )
        self._stop_requested = stop_requested
        self._latest_interaction_state: (
            InteractionState | None
        ) = None

        self._roi_manager = roi_manager
        self._illumination_analyzer = (
            illumination_analyzer
        )
        self._illumination_decision = (
            illumination_decision
        )
        self._adaptive_preprocessor = (
            adaptive_preprocessor
        )

        self._clock = clock

    @property
    def preprocessing_enabled(self) -> bool:
        """Whether the G2 preprocessing path is enabled."""

        return self._roi_manager is not None

    @property
    def latest_interaction_state(
        self,
    ) -> InteractionState | None:
        """Most recent public interaction state."""

        return self._latest_interaction_state

    def run(
        self,
        *,
        metadata: Mapping[str, Any],
        resolved_config: Mapping[str, Any],
    ) -> int:
        """Execute one deterministic replay run."""

        processed_frames = 0
        self._latest_interaction_state = None

        # ROI for frame t is selected from the most recent observation
        # available before frame t is processed. Therefore current-frame
        # preprocessing uses the hand geometry observed on frame t - 1.
        previous_hand_bbox: ROI | None = None

        try:
            self._logger.start_run(
                metadata,
                resolved_config,
            )

            self._filter.reset()

            if self._gesture_engine is not None:
                self._gesture_engine.reset()

            if self._roi_manager is not None:
                self._roi_manager.reset()

            if self._illumination_decision is not None:
                self._illumination_decision.reset()

            self._source.open()

            while True:
                if (
                    self._stop_requested is not None
                    and self._stop_requested()
                ):
                    break

                packet = self._source.read()

                if packet is None:
                    break

                (
                    provider_frame,
                    roi,
                    illumination,
                    preprocess_ms,
                ) = self._prepare_provider_frame(
                    packet,
                    previous_hand_bbox=previous_hand_bbox,
                )

                tracking_start = self._clock()

                observation = self._provider.process(
                    provider_frame
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

                # Becomes the geometry input for the next frame.
                # Missing/invalid observations naturally supply None,
                # allowing ROIManager to enter COASTING/SEARCHING.
                previous_hand_bbox = (
                    observation.hand_bbox
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

                compute_before_gesture_ms = (
                    preprocess_ms
                    + tracking_ms
                    + filtering_ms
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
                    roi=roi,
                    illumination=illumination,
                    filter_diagnostics=diagnostics,
                    timings=StageTimings(
                        preprocess_ms=preprocess_ms,
                        tracking_ms=tracking_ms,
                        filtering_ms=filtering_ms,
                        gesture_ms=0.0,
                        compute_total_ms=(
                            compute_before_gesture_ms
                        ),
                    ),
                    events=diagnostics.events,
                )

                interaction_state = None
                gesture_ms = 0.0

                if self._gesture_engine is not None:
                    gesture_start = self._clock()

                    interaction_state = (
                        self._gesture_engine.update(
                            tracking_frame
                        )
                    )

                    gesture_end = self._clock()

                    gesture_ms = self._duration_ms(
                        gesture_start,
                        gesture_end,
                    )

                    tracking_frame = replace(
                        tracking_frame,
                        timings=StageTimings(
                            preprocess_ms=preprocess_ms,
                            tracking_ms=tracking_ms,
                            filtering_ms=filtering_ms,
                            gesture_ms=gesture_ms,
                            compute_total_ms=(
                                compute_before_gesture_ms
                                + gesture_ms
                            ),
                        ),
                    )

                self._logger.log_tracking_frame(
                    tracking_frame
                )

                if interaction_state is not None:
                    self._logger.log_interaction_state(
                        interaction_state
                    )

                    self._latest_interaction_state = (
                        interaction_state
                    )

                    if (
                        self._interaction_consumer
                        is not None
                    ):
                        self._interaction_consumer(
                            interaction_state
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

    def _prepare_provider_frame(
        self,
        packet: FramePacket,
        *,
        previous_hand_bbox: ROI | None,
    ) -> tuple[
        FramePacket,
        ROI | None,
        IlluminationMetrics | None,
        float,
    ]:
        """Run optional G2 preprocessing for one frame."""

        if not self.preprocessing_enabled:
            return (
                packet,
                None,
                None,
                0.0,
            )

        assert self._roi_manager is not None
        assert self._illumination_analyzer is not None
        assert self._illumination_decision is not None
        assert self._adaptive_preprocessor is not None

        preprocess_start = self._clock()

        frame_height, frame_width = (
            packet.image.shape[:2]
        )

        roi = self._roi_manager.update(
            frame_width=frame_width,
            frame_height=frame_height,
            hand_bbox=previous_hand_bbox,
        )

        descriptors = (
            self._illumination_analyzer.measure(
                packet,
                roi,
            )
        )

        preliminary_illumination = (
            self._illumination_decision.update(
                descriptors
            )
        )

        preprocess_result = (
            self._adaptive_preprocessor.process_frame(
                packet,
                roi,
                preliminary_illumination,
            )
        )

        preprocess_end = self._clock()

        preprocess_ms = self._duration_ms(
            preprocess_start,
            preprocess_end,
        )

        return (
            preprocess_result.frame,
            roi,
            preprocess_result.illumination,
            preprocess_ms,
        )

    @staticmethod
    def _duration_ms(
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

        return (
            end - start
        ) * 1000.0
