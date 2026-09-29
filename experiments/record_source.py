"""Record fixed raw-BGR replay sources for final experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

import cv2
import numpy as np

from dip_touchless.capture.camera import OpenCVCameraSource
from dip_touchless.configuration import resolve_config
from dip_touchless.core import ColorSpace, FramePacket


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"

_CODEC = "MJPG"


class RecordingSource(Protocol):
    def open(self) -> None: ...

    def read(self) -> FramePacket: ...

    def close(self) -> None: ...


class VideoWriterLike(Protocol):
    def write(self, frame: np.ndarray) -> None: ...

    def release(self) -> None: ...


WriterFactory = Callable[
    [Path, float, tuple[int, int]],
    VideoWriterLike,
]


@dataclass(frozen=True)
class RecordedSource:
    video_path: Path
    metadata_path: Path
    frame_count: int
    sha256: str


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None

    revision = result.stdout.strip()
    return revision or None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _create_writer(
    path: Path,
    fps: float,
    size: tuple[int, int],
) -> VideoWriterLike:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*_CODEC),
        fps,
        size,
    )

    if not writer.isOpened():
        writer.release()
        raise RuntimeError(
            f"failed to open video writer: {path}"
        )

    return writer


def _validate_packet(
    packet: FramePacket,
    *,
    expected_shape: tuple[int, int, int] | None = None,
) -> None:
    if packet.color_space is not ColorSpace.BGR:
        raise RuntimeError(
            "source recorder requires BGR frames"
        )

    image = packet.image

    if (
        not isinstance(image, np.ndarray)
        or image.dtype != np.uint8
        or image.ndim != 3
        or image.shape[2] != 3
        or image.size == 0
    ):
        raise RuntimeError(
            "source recorder requires non-empty "
            "HxWx3 uint8 frames"
        )

    if (
        expected_shape is not None
        and image.shape != expected_shape
    ):
        raise RuntimeError(
            "camera frame shape changed during recording"
        )


def record_frame_source(
    *,
    source: RecordingSource,
    output_path: Path,
    frame_count: int,
    encoded_fps: float,
    settle_s: float,
    requested_camera: Mapping[str, Any],
    lighting_label: str,
    auto_exposure_status: str,
    auto_white_balance_status: str,
    notes: str | None = None,
    writer_factory: WriterFactory = _create_writer,
    code_revision: str | None = None,
) -> RecordedSource:
    """Record one immutable paired-replay source."""

    if output_path.suffix.lower() != ".avi":
        raise ValueError(
            "recorded source output must use .avi"
        )

    if (
        not isinstance(frame_count, int)
        or isinstance(frame_count, bool)
        or frame_count <= 0
    ):
        raise ValueError("frame_count must be positive")

    if not math.isfinite(encoded_fps) or encoded_fps <= 0.0:
        raise ValueError("encoded_fps must be positive")

    if not math.isfinite(settle_s) or settle_s < 0.0:
        raise ValueError("settle_s must be non-negative")

    if not lighting_label.strip():
        raise ValueError("lighting_label must not be empty")

    valid_control_states = {
        "enabled",
        "disabled",
        "unknown",
    }

    if auto_exposure_status not in valid_control_states:
        raise ValueError("invalid auto-exposure status")

    if auto_white_balance_status not in valid_control_states:
        raise ValueError("invalid auto-white-balance status")

    metadata_path = output_path.with_suffix(".json")

    if output_path.exists():
        raise FileExistsError(
            f"source already exists: {output_path}"
        )

    if metadata_path.exists():
        raise FileExistsError(
            "source metadata already exists: "
            f"{metadata_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer: VideoWriterLike | None = None
    completed = False
    first_timestamp_s: float | None = None
    last_timestamp_s: float | None = None
    observed_width: int | None = None
    observed_height: int | None = None
    observed_fps: float | None = None
    backend_name: str | None = None
    recorded_at_utc = datetime.now(
        timezone.utc
    ).isoformat()

    try:
        source.open()

        observed_width = getattr(
            source,
            "observed_width",
            None,
        )
        observed_height = getattr(
            source,
            "observed_height",
            None,
        )
        observed_fps = getattr(
            source,
            "observed_fps",
            None,
        )
        backend_name = getattr(
            source,
            "backend_name",
            None,
        )

        packet = source.read()

        while packet.timestamp_s < settle_s:
            packet = source.read()

        _validate_packet(packet)
        expected_shape = packet.image.shape
        height, width = (
            int(expected_shape[0]),
            int(expected_shape[1]),
        )

        writer = writer_factory(
            output_path,
            encoded_fps,
            (width, height),
        )

        for index in range(frame_count):
            if index > 0:
                packet = source.read()

            _validate_packet(
                packet,
                expected_shape=expected_shape,
            )

            if first_timestamp_s is None:
                first_timestamp_s = packet.timestamp_s

            last_timestamp_s = packet.timestamp_s
            writer.write(packet.image)

        completed = True
    finally:
        cleanup_needed = not completed

        try:
            if writer is not None:
                writer.release()
        except BaseException:
            cleanup_needed = True
            raise
        finally:
            try:
                source.close()
            except BaseException:
                cleanup_needed = True
                raise
            finally:
                if cleanup_needed:
                    output_path.unlink(missing_ok=True)
                    metadata_path.unlink(missing_ok=True)

    if (
        not output_path.is_file()
        or output_path.stat().st_size <= 0
    ):
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            "recorded source file is missing or empty"
        )

    try:
        source_sha256 = _file_sha256(output_path)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    payload = {
        "schema_version": "1",
        "recorded_at_utc": recorded_at_utc,
        "video": {
            "path": str(output_path.resolve()),
            "codec": _CODEC,
            "color_space": "BGR",
            "dtype": "uint8",
            "frame_count": frame_count,
            "encoded_fps": encoded_fps,
            "encoded_width": width,
            "encoded_height": height,
            "encoded_duration_s": frame_count / encoded_fps,
            "replay_last_timestamp_s": (
                (frame_count - 1) / encoded_fps
            ),
            "sha256": source_sha256,
        },
        "acquisition": {
            "settle_s": settle_s,
            "first_recorded_timestamp_s": (
                first_timestamp_s
            ),
            "last_recorded_timestamp_s": (
                last_timestamp_s
            ),
            "source_timestamp_span_s": (
                last_timestamp_s - first_timestamp_s
                if (
                    first_timestamp_s is not None
                    and last_timestamp_s is not None
                )
                else None
            ),
        },
        "camera": {
            "backend": backend_name,
            "requested": dict(requested_camera),
            "observed": {
                "width": observed_width,
                "height": observed_height,
                "fps": observed_fps,
            },
        },
        "lighting": {
            "label": lighting_label,
            "auto_exposure": auto_exposure_status,
            "auto_white_balance": auto_white_balance_status,
            "notes": notes,
        },
        "processing": {
            "preprocessing": "none",
            "description": (
                "Raw BGR camera frames written directly to AVI."
            ),
        },
        "software": {
            "code_revision": code_revision or _git_revision(),
            "python_version": platform.python_version(),
            "opencv_version": cv2.__version__,
        },
    }

    try:
        metadata_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise

    return RecordedSource(
        video_path=output_path,
        metadata_path=metadata_path,
        frame_count=frame_count,
        sha256=source_sha256,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Record one raw BGR camera source "
            "for deterministic paired replay."
        )
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--duration-s",
        required=True,
        type=float,
    )
    parser.add_argument(
        "--settle-s",
        type=float,
        default=3.0,
    )
    parser.add_argument(
        "--lighting-label",
        required=True,
    )
    parser.add_argument(
        "--auto-exposure",
        choices=("enabled", "disabled", "unknown"),
        default="unknown",
    )
    parser.add_argument(
        "--auto-white-balance",
        choices=("enabled", "disabled", "unknown"),
        default="unknown",
    )
    parser.add_argument(
        "--notes",
        default=None,
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--backend",
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if (
        not math.isfinite(args.duration_s)
        or args.duration_s <= 0.0
    ):
        raise ValueError("--duration-s must be positive")

    camera_overrides = {}

    if args.camera_index is not None:
        camera_overrides["index"] = args.camera_index
    if args.width is not None:
        camera_overrides["width"] = args.width
    if args.height is not None:
        camera_overrides["height"] = args.height
    if args.fps is not None:
        camera_overrides["requested_fps"] = args.fps
    if args.backend is not None:
        camera_overrides["backend"] = args.backend

    overrides = (
        {"camera": camera_overrides}
        if camera_overrides
        else None
    )
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides=overrides,
    )
    camera = resolved.to_dict()["camera"]
    encoded_fps = float(camera["requested_fps"])
    frame_count = max(
        1,
        int(round(args.duration_s * encoded_fps)),
    )

    capture_id = "source-" + datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")
    source = OpenCVCameraSource(
        run_id=capture_id,
        camera_index=camera["index"],
        width=camera["width"],
        height=camera["height"],
        requested_fps=encoded_fps,
        backend=camera["backend"],
    )

    result = record_frame_source(
        source=source,
        output_path=args.output,
        frame_count=frame_count,
        encoded_fps=encoded_fps,
        settle_s=args.settle_s,
        requested_camera={
            "index": camera["index"],
            "width": camera["width"],
            "height": camera["height"],
            "fps": encoded_fps,
            "backend": camera["backend"],
        },
        lighting_label=args.lighting_label,
        auto_exposure_status=args.auto_exposure,
        auto_white_balance_status=args.auto_white_balance,
        notes=args.notes,
    )

    print(f"video: {result.video_path}")
    print(f"metadata: {result.metadata_path}")
    print(f"frames: {result.frame_count}")
    print(f"sha256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
