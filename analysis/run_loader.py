"""Load and validate immutable run artifacts for analysis."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class RunArtifactError(ValueError):
    """Raised when serialized run artifacts are inconsistent."""


@dataclass(frozen=True)
class FrameRecord:
    run_id: str
    frame_id: int
    timestamp_s: float
    tracking_status: str
    illumination_state: str | None
    enhancement_active: bool | None
    filter_mode: str


@dataclass(frozen=True)
class LandmarkRecord:
    run_id: str
    frame_id: int
    timestamp_s: float
    stage: str
    landmark_index: int
    x: float
    y: float
    z: float
    coordinate_space: str


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    metadata: Mapping[str, Any]
    resolved_config: Mapping[str, Any]
    frames: tuple[FrameRecord, ...]
    landmarks: tuple[LandmarkRecord, ...]

    @property
    def run_id(self) -> str:
        return str(self.metadata["run_id"])

    def frames_in_window(
        self,
        *,
        start_s: float,
        end_s: float | None,
    ) -> tuple[FrameRecord, ...]:
        return tuple(
            frame
            for frame in self.frames
            if (
                frame.timestamp_s >= start_s
                and (
                    end_s is None
                    or frame.timestamp_s <= end_s
                )
            )
        )

    def landmark_series(
        self,
        *,
        stage: str,
        landmark_index: int,
        coordinate_space: str | None = None,
        start_s: float = 0.0,
        end_s: float | None = None,
    ) -> tuple[LandmarkRecord, ...]:
        return tuple(
            landmark
            for landmark in self.landmarks
            if (
                landmark.stage == stage
                and landmark.landmark_index
                == landmark_index
                and landmark.timestamp_s
                >= start_s
                and (
                    end_s is None
                    or landmark.timestamp_s
                    <= end_s
                )
                and (
                    coordinate_space is None
                    or landmark.coordinate_space
                    == coordinate_space
                )
            )
        )


def _read_json_mapping(
    path: Path,
) -> Mapping[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RunArtifactError(
            f"failed to read JSON artifact: {path}"
        ) from exc

    if not isinstance(value, Mapping):
        raise RunArtifactError(
            f"JSON artifact must contain a mapping: "
            f"{path}"
        )

    return value


def _read_yaml_mapping(
    path: Path,
) -> Mapping[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            value = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise RunArtifactError(
            f"failed to read YAML artifact: {path}"
        ) from exc

    if not isinstance(value, Mapping):
        raise RunArtifactError(
            f"YAML artifact must contain a mapping: "
            f"{path}"
        )

    return value


def _required(
    row: Mapping[str, str],
    field: str,
    *,
    artifact: str,
) -> str:
    value = row.get(field)

    if value is None or value == "":
        raise RunArtifactError(
            f"{artifact}.{field} is required"
        )

    return value


def _parse_int(
    value: str,
    *,
    name: str,
) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RunArtifactError(
            f"{name} must be an integer"
        ) from exc

    return parsed


def _parse_float(
    value: str,
    *,
    name: str,
) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise RunArtifactError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(parsed):
        raise RunArtifactError(
            f"{name} must be finite"
        )

    return parsed


def _parse_optional_bool(
    value: str | None,
    *,
    name: str,
) -> bool | None:
    if value is None or value == "":
        return None

    if value == "True":
        return True

    if value == "False":
        return False

    raise RunArtifactError(
        f"{name} must be True, False, or empty"
    )


def _read_frames(
    path: Path,
    *,
    expected_run_id: str,
) -> tuple[FrameRecord, ...]:
    try:
        with path.open(
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))
    except OSError as exc:
        raise RunArtifactError(
            f"failed to read frames artifact: {path}"
        ) from exc

    frames: list[FrameRecord] = []
    previous_frame_id: int | None = None
    previous_timestamp_s: float | None = None

    for row_index, row in enumerate(rows):
        prefix = f"frames[{row_index}]"

        run_id = _required(
            row,
            "run_id",
            artifact=prefix,
        )

        if run_id != expected_run_id:
            raise RunArtifactError(
                f"{prefix}.run_id does not match "
                "metadata.run_id"
            )

        frame_id = _parse_int(
            _required(
                row,
                "frame_id",
                artifact=prefix,
            ),
            name=f"{prefix}.frame_id",
        )

        timestamp_s = _parse_float(
            _required(
                row,
                "timestamp_s",
                artifact=prefix,
            ),
            name=f"{prefix}.timestamp_s",
        )

        if (
            previous_frame_id is not None
            and frame_id <= previous_frame_id
        ):
            raise RunArtifactError(
                "frames must have strictly increasing "
                "frame_id values"
            )

        if (
            previous_timestamp_s is not None
            and timestamp_s < previous_timestamp_s
        ):
            raise RunArtifactError(
                "frames must have non-decreasing "
                "timestamps"
            )

        illumination_state = row.get(
            "illumination_state"
        )

        if illumination_state == "":
            illumination_state = None

        frames.append(
            FrameRecord(
                run_id=run_id,
                frame_id=frame_id,
                timestamp_s=timestamp_s,
                tracking_status=_required(
                    row,
                    "tracking_status",
                    artifact=prefix,
                ),
                illumination_state=(
                    illumination_state
                ),
                enhancement_active=(
                    _parse_optional_bool(
                        row.get(
                            "enhancement_active"
                        ),
                        name=(
                            f"{prefix}."
                            "enhancement_active"
                        ),
                    )
                ),
                filter_mode=_required(
                    row,
                    "filter_mode",
                    artifact=prefix,
                ),
            )
        )

        previous_frame_id = frame_id
        previous_timestamp_s = timestamp_s

    return tuple(frames)


def _read_landmarks(
    path: Path,
    *,
    expected_run_id: str,
    frames_by_id: Mapping[int, FrameRecord],
) -> tuple[LandmarkRecord, ...]:
    try:
        with path.open(
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))
    except OSError as exc:
        raise RunArtifactError(
            f"failed to read landmarks artifact: {path}"
        ) from exc

    landmarks: list[LandmarkRecord] = []

    for row_index, row in enumerate(rows):
        prefix = f"landmarks[{row_index}]"

        run_id = _required(
            row,
            "run_id",
            artifact=prefix,
        )

        if run_id != expected_run_id:
            raise RunArtifactError(
                f"{prefix}.run_id does not match "
                "metadata.run_id"
            )

        frame_id = _parse_int(
            _required(
                row,
                "frame_id",
                artifact=prefix,
            ),
            name=f"{prefix}.frame_id",
        )

        frame = frames_by_id.get(frame_id)

        if frame is None:
            raise RunArtifactError(
                f"{prefix} references unknown frame_id "
                f"{frame_id}"
            )

        timestamp_s = _parse_float(
            _required(
                row,
                "timestamp_s",
                artifact=prefix,
            ),
            name=f"{prefix}.timestamp_s",
        )

        if not math.isclose(
            timestamp_s,
            frame.timestamp_s,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise RunArtifactError(
                f"{prefix}.timestamp_s does not match "
                "the corresponding frame"
            )

        stage = _required(
            row,
            "stage",
            artifact=prefix,
        )

        if stage not in {
            "raw",
            "filtered",
        }:
            raise RunArtifactError(
                f"{prefix}.stage must be raw or filtered"
            )

        landmark_index = _parse_int(
            _required(
                row,
                "landmark_index",
                artifact=prefix,
            ),
            name=f"{prefix}.landmark_index",
        )

        if landmark_index < 0:
            raise RunArtifactError(
                f"{prefix}.landmark_index must be "
                "non-negative"
            )

        landmarks.append(
            LandmarkRecord(
                run_id=run_id,
                frame_id=frame_id,
                timestamp_s=timestamp_s,
                stage=stage,
                landmark_index=landmark_index,
                x=_parse_float(
                    _required(
                        row,
                        "x",
                        artifact=prefix,
                    ),
                    name=f"{prefix}.x",
                ),
                y=_parse_float(
                    _required(
                        row,
                        "y",
                        artifact=prefix,
                    ),
                    name=f"{prefix}.y",
                ),
                z=_parse_float(
                    _required(
                        row,
                        "z",
                        artifact=prefix,
                    ),
                    name=f"{prefix}.z",
                ),
                coordinate_space=_required(
                    row,
                    "coordinate_space",
                    artifact=prefix,
                ),
            )
        )

    return tuple(landmarks)


def load_run_artifacts(
    run_dir: str | Path,
) -> RunArtifacts:
    """Load one logger-produced run without modifying raw artifacts."""

    run_path = Path(run_dir)

    if not run_path.is_dir():
        raise FileNotFoundError(
            f"run directory not found: {run_path}"
        )

    required_paths = {
        "metadata": run_path / "metadata.json",
        "config": (
            run_path / "resolved_config.yaml"
        ),
        "frames": run_path / "frames.csv",
        "landmarks": (
            run_path / "landmarks.csv"
        ),
        "events": run_path / "events.csv",
    }

    for name, path in required_paths.items():
        if not path.is_file():
            raise RunArtifactError(
                f"missing {name} artifact: {path}"
            )

    metadata = _read_json_mapping(
        required_paths["metadata"]
    )

    resolved_config = _read_yaml_mapping(
        required_paths["config"]
    )

    run_id = metadata.get("run_id")

    if (
        not isinstance(run_id, str)
        or not run_id.strip()
    ):
        raise RunArtifactError(
            "metadata.run_id must be a non-empty string"
        )

    if run_path.name != run_id:
        raise RunArtifactError(
            "run directory name does not match "
            "metadata.run_id"
        )

    frames = _read_frames(
        required_paths["frames"],
        expected_run_id=run_id,
    )

    frames_by_id = {
        frame.frame_id: frame
        for frame in frames
    }

    landmarks = _read_landmarks(
        required_paths["landmarks"],
        expected_run_id=run_id,
        frames_by_id=frames_by_id,
    )

    return RunArtifacts(
        run_dir=run_path,
        metadata=metadata,
        resolved_config=resolved_config,
        frames=frames,
        landmarks=landmarks,
    )
