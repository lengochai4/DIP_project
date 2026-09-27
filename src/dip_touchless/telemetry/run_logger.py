"""CSV/JSON run logger for reproducible project artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, TextIO

import yaml

from dip_touchless.core import (
    InteractionState,
    TrackingFrame,
)


FRAME_FIELDS = (
    "run_id",
    "frame_id",
    "timestamp_s",
    "tracking_status",
    "roi_x",
    "roi_y",
    "roi_width",
    "roi_height",
    "roi_state",
    "illumination_state",
    "enhancement_active",
    "mean_v",
    "std_v",
    "p10_v",
    "p90_v",
    "robust_range_v",
    "quality_valid",
    "quality_value",
    "quality_source",
    "quality_semantic_name",
    "filter_mode",
    "dt_s",
    "speed",
    "beta",
    "min_cutoff_hz",
    "final_cutoff_hz",
    "signal_alpha",
    "derivative_alpha",
    "reset_occurred",
    "preprocess_ms",
    "tracking_ms",
    "filtering_ms",
    "gesture_ms",
    "compute_total_ms",
    "interaction_valid",
    "pointer_x",
    "pointer_y",
    "pinch_ratio",
    "pinch_active",
    "rotation_dx",
    "rotation_dy",
    "scale_delta",
)


LANDMARK_FIELDS = (
    "run_id",
    "frame_id",
    "timestamp_s",
    "stage",
    "landmark_index",
    "x",
    "y",
    "z",
    "coordinate_space",
)


EVENT_FIELDS = (
    "run_id",
    "frame_id",
    "timestamp_s",
    "event_type",
    "severity",
    "details_json",
)


class FileRunLogger:
    """Write one run into a versioned directory of parseable artifacts."""

    def __init__(
        self,
        output_root: str | Path,
    ) -> None:
        self._output_root = Path(output_root)

        self._run_id: str | None = None
        self._run_dir: Path | None = None

        self._frames_file: TextIO | None = None
        self._landmarks_file: TextIO | None = None
        self._events_file: TextIO | None = None

        self._frames_writer: csv.DictWriter | None = None
        self._landmarks_writer: csv.DictWriter | None = None
        self._events_writer: csv.DictWriter | None = None

        self._pending_frames: dict[int, TrackingFrame] = {}
        self._logged_frame_ids: set[int] = set()

        self._started = False
        self._closed = False

    @property
    def run_id(self) -> str | None:
        return self._run_id

    @property
    def run_dir(self) -> Path | None:
        return self._run_dir

    def start_run(
        self,
        metadata: Mapping[str, Any],
        resolved_config: Mapping[str, Any],
    ) -> None:
        if self._started:
            raise RuntimeError("run logger has already been started")

        run_id = metadata.get("run_id")

        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError(
                "metadata.run_id must be a non-empty string"
            )

        serialized_config = yaml.safe_dump(
            dict(resolved_config),
            sort_keys=True,
            allow_unicode=True,
            default_flow_style=False,
        )

        actual_hash = hashlib.sha256(
            serialized_config.encode("utf-8")
        ).hexdigest()

        expected_hash = metadata.get("config_hash")

        if expected_hash != actual_hash:
            raise ValueError(
                "metadata config_hash does not match resolved configuration"
            )

        log_schema_version = metadata.get(
            "log_schema_version"
        )

        if not log_schema_version:
            raise ValueError(
                "metadata must contain log_schema_version"
            )

        self._output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        run_dir = self._output_root / run_id

        if run_dir.exists():
            raise FileExistsError(
                f"run directory already exists: {run_dir}"
            )

        run_dir.mkdir()

        metadata_path = run_dir / "metadata.json"
        config_path = run_dir / "resolved_config.yaml"

        metadata_path.write_text(
            json.dumps(
                dict(metadata),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        config_path.write_text(
            serialized_config,
            encoding="utf-8",
        )

        self._frames_file = (
            run_dir / "frames.csv"
        ).open(
            "w",
            newline="",
            encoding="utf-8",
        )

        self._landmarks_file = (
            run_dir / "landmarks.csv"
        ).open(
            "w",
            newline="",
            encoding="utf-8",
        )

        self._events_file = (
            run_dir / "events.csv"
        ).open(
            "w",
            newline="",
            encoding="utf-8",
        )

        self._frames_writer = csv.DictWriter(
            self._frames_file,
            fieldnames=FRAME_FIELDS,
        )
        self._landmarks_writer = csv.DictWriter(
            self._landmarks_file,
            fieldnames=LANDMARK_FIELDS,
        )
        self._events_writer = csv.DictWriter(
            self._events_file,
            fieldnames=EVENT_FIELDS,
        )

        self._frames_writer.writeheader()
        self._landmarks_writer.writeheader()
        self._events_writer.writeheader()

        self._run_id = run_id
        self._run_dir = run_dir
        self._started = True

    def _require_active(self) -> None:
        if not self._started:
            raise RuntimeError(
                "run logger has not been started"
            )

        if self._closed:
            raise RuntimeError(
                "run logger is already closed"
            )

    def _validate_run_id(
        self,
        run_id: str,
    ) -> None:
        if run_id != self._run_id:
            raise ValueError(
                "artifact run_id does not match active run"
            )

    def log_tracking_frame(
        self,
        frame: TrackingFrame,
    ) -> None:
        self._require_active()
        self._validate_run_id(frame.run_id)

        if (
            frame.frame_id in self._pending_frames
            or frame.frame_id in self._logged_frame_ids
        ):
            raise ValueError(
                f"duplicate frame_id: {frame.frame_id}"
            )

        self._write_landmarks(
            frame,
            stage="raw",
            landmarks=frame.raw_landmarks,
        )

        self._write_landmarks(
            frame,
            stage="filtered",
            landmarks=frame.filtered_landmarks,
        )

        for event_type in frame.events:
            self.log_event(
                {
                    "frame_id": frame.frame_id,
                    "timestamp_s": frame.timestamp_s,
                    "event_type": event_type,
                    "severity": "INFO",
                    "details": {},
                }
            )

        self._pending_frames[frame.frame_id] = frame

    def _write_landmarks(
        self,
        frame: TrackingFrame,
        *,
        stage: str,
        landmarks: tuple,
    ) -> None:
        assert self._landmarks_writer is not None

        for landmark in landmarks:
            self._landmarks_writer.writerow(
                {
                    "run_id": frame.run_id,
                    "frame_id": frame.frame_id,
                    "timestamp_s": frame.timestamp_s,
                    "stage": stage,
                    "landmark_index": landmark.index,
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "coordinate_space": (
                        landmark.coordinate_space.value
                    ),
                }
            )

    def log_interaction_state(
        self,
        state: InteractionState,
    ) -> None:
        self._require_active()
        self._validate_run_id(state.run_id)

        frame = self._pending_frames.pop(
            state.frame_id,
            None,
        )

        if frame is None:
            raise ValueError(
                "interaction state has no pending tracking frame "
                f"for frame_id {state.frame_id}"
            )

        if state.timestamp_s != frame.timestamp_s:
            raise ValueError(
                "interaction timestamp does not match tracking frame"
            )

        self._write_frame_row(
            frame,
            state,
        )

    def _write_frame_row(
        self,
        frame: TrackingFrame,
        interaction: InteractionState | None,
    ) -> None:
        assert self._frames_writer is not None

        if frame.frame_id in self._logged_frame_ids:
            raise ValueError(
                f"duplicate frame_id: {frame.frame_id}"
            )

        pointer_x = None
        pointer_y = None

        if (
            interaction is not None
            and interaction.pointer_xy is not None
        ):
            pointer_x, pointer_y = (
                interaction.pointer_xy
            )

        rotation_dx = None
        rotation_dy = None

        if interaction is not None:
            rotation_dx, rotation_dy = (
                interaction.rotation_delta
            )

        quality = frame.quality
        diagnostics = frame.filter_diagnostics
        timings = frame.timings
        illumination = frame.illumination
        roi = frame.roi

        self._frames_writer.writerow(
        {
            "run_id": frame.run_id,
            "frame_id": frame.frame_id,
            "timestamp_s": frame.timestamp_s,
            "tracking_status": frame.status.value,

            # ROI may be unavailable.
            "roi_x": roi.x if roi is not None else None,
            "roi_y": roi.y if roi is not None else None,
            "roi_width": roi.width if roi is not None else None,
            "roi_height": roi.height if roi is not None else None,
            "roi_state": (
                roi.state.value
                if roi is not None
                else None
            ),

            # Illumination analysis may not have been executed.
            "illumination_state": (
                illumination.state.value
                if illumination is not None
                else None
            ),
            "enhancement_active": (
                illumination.enhancement_active
                if illumination is not None
                else None
            ),
            "mean_v": (
                illumination.mean_v
                if illumination is not None
                else None
            ),
            "std_v": (
                illumination.std_v
                if illumination is not None
                else None
            ),
            "p10_v": (
                illumination.p10_v
                if illumination is not None
                else None
            ),
            "p90_v": (
                illumination.p90_v
                if illumination is not None
                else None
            ),
            "robust_range_v": (
                illumination.robust_range_v
                if illumination is not None
                else None
            ),

            "quality_valid": quality.valid,
            "quality_value": quality.value,
            "quality_source": quality.source.value,
            "quality_semantic_name": quality.semantic_name,

            "filter_mode": diagnostics.mode.value,
            "dt_s": diagnostics.dt_s,
            "speed": diagnostics.speed,
            "beta": diagnostics.beta,
            "min_cutoff_hz": diagnostics.min_cutoff_hz,
            "final_cutoff_hz": diagnostics.final_cutoff_hz,
            "signal_alpha": diagnostics.signal_alpha,
            "derivative_alpha": diagnostics.derivative_alpha,
            "reset_occurred": diagnostics.reset_occurred,

            "preprocess_ms": timings.preprocess_ms,
            "tracking_ms": timings.tracking_ms,
            "filtering_ms": timings.filtering_ms,
            "gesture_ms": timings.gesture_ms,
            "compute_total_ms": timings.compute_total_ms,

            "interaction_valid": (
                interaction.interaction_valid
                if interaction is not None
                else None
            ),
            "pointer_x": pointer_x,
            "pointer_y": pointer_y,
            "pinch_ratio": (
                interaction.pinch_ratio
                if interaction is not None
                else None
            ),
            "pinch_active": (
                interaction.pinch_active
                if interaction is not None
                else None
            ),
            "rotation_dx": rotation_dx,
            "rotation_dy": rotation_dy,
            "scale_delta": (
                interaction.scale_delta
                if interaction is not None
                else None
            ),
        }
    )

        self._logged_frame_ids.add(frame.frame_id)

    def log_event(
        self,
        event: Mapping[str, Any],
    ) -> None:
        self._require_active()

        assert self._events_writer is not None

        details = event.get("details", {})

        self._events_writer.writerow(
            {
                "run_id": self._run_id,
                "frame_id": event.get("frame_id"),
                "timestamp_s": event.get(
                    "timestamp_s"
                ),
                "event_type": event.get(
                    "event_type",
                    "UNSPECIFIED",
                ),
                "severity": event.get(
                    "severity",
                    "INFO",
                ),
                "details_json": json.dumps(
                    details,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            }
        )

    def close(self) -> None:
        if not self._started or self._closed:
            return

        for frame_id in sorted(
            self._pending_frames
        ):
            self._write_frame_row(
                self._pending_frames[frame_id],
                interaction=None,
            )

        self._pending_frames.clear()

        for file_handle in (
            self._frames_file,
            self._landmarks_file,
            self._events_file,
        ):
            if file_handle is not None:
                file_handle.flush()
                file_handle.close()

        self._closed = True