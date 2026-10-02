"""Read-only OBSERVE_FULL_HAND sidecar. Legacy alone owns interaction outputs."""

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
from pathlib import Path
import warnings

import yaml

from dip_touchless.core import FramePacket, FrameSource, InteractionState, TrackingFrame, TrackingStatus
from .contracts import FrameGeometry, HandGeometry
from .geometry import extract_hand_geometry
from .pose_classifier import classify_pose
from .pose_contracts import FingerThresholds, PoseObservation, PoseThresholds, ThumbThresholds
from .temporal import TemporalPoseTracker
from .temporal_contracts import StablePoseState, TemporalPoseConfig


class CompositionMode(str, Enum):
    LEGACY = "LEGACY"
    OBSERVE_FULL_HAND = "OBSERVE_FULL_HAND"


@dataclass(frozen=True, slots=True)
class ObserveProfile:
    pose: PoseThresholds
    temporal: TemporalPoseConfig

    def __post_init__(self) -> None:
        if not isinstance(self.pose, PoseThresholds) or not isinstance(self.temporal, TemporalPoseConfig):
            raise TypeError("observe profile requires immutable pose/temporal configuration")


def load_observe_profile(path: Path) -> ObserveProfile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if set(data) != {"pose", "temporal"}:
        raise ValueError("observe profile requires only pose and temporal sections")
    pose = dict(data["pose"])
    fingers = FingerThresholds(**pose.pop("fingers"))
    thumb = dict(pose.pop("thumb"))
    thumb["chain"] = FingerThresholds(**thumb["chain"])
    return ObserveProfile(PoseThresholds(fingers, ThumbThresholds(**thumb), **pose),
                          TemporalPoseConfig(**data["temporal"]))


@dataclass(frozen=True, slots=True)
class FullHandSnapshot:
    mode: CompositionMode
    run_id: str
    frame_id: int
    timestamp_s: float
    tracking_status: TrackingStatus
    analysis_valid: bool
    frame_geometry: FrameGeometry | None
    hand: HandGeometry | None
    pose: PoseObservation | None
    temporal: StablePoseState
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.errors) is not tuple or not all(isinstance(e, str) for e in self.errors):
            raise TypeError("snapshot errors must be an immutable string tuple")
        if not isinstance(self.temporal, StablePoseState):
            raise TypeError("snapshot requires immutable temporal diagnostics")
        if self.analysis_valid and (self.hand is None or not self.hand.valid or self.errors):
            raise ValueError("valid analysis requires usable geometry and no analysis errors")


class FullHandObserver:
    """Latest snapshot is available to presentation adapters; no image retained."""

    def __init__(self, profile: ObserveProfile,
                 sink: Callable[[FullHandSnapshot], object] | None = None) -> None:
        self.profile = profile
        self.tracker = TemporalPoseTracker(profile.temporal)
        self.sink = sink
        self.frame_geometry: FrameGeometry | None = None
        self.latest_snapshot: FullHandSnapshot | None = None
        self._capture_error: str | None = None
        self._sink_errors: set[str] = set()
        self._last_tracking: TrackingFrame | None = None
        self._last_legacy: InteractionState | None = None

    def reset(self) -> None:
        self.tracker.reset()
        self.frame_geometry = self.latest_snapshot = None
        self._capture_error = None
        self._last_tracking = self._last_legacy = None

    def capture(self, packet: FramePacket) -> None:
        try:
            height, width = packet.image.shape[:2]
            self.frame_geometry = FrameGeometry(packet.run_id, packet.frame_id,
                                                packet.timestamp_s, width, height)
            self._capture_error = None
        except Exception as exc:
            self.frame_geometry = None
            self._capture_error = f"frame geometry unavailable: {type(exc).__name__}: {exc}"

    def consume(self, packet: FramePacket, frame: TrackingFrame,
                legacy: InteractionState | None) -> FullHandSnapshot:
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        old = self.latest_snapshot
        geometry = self.frame_geometry
        hand = pose = None
        errors = ()
        try:
            if geometry is None:
                raise ValueError(self._capture_error or "source frame geometry not captured")
            if (geometry.run_id, geometry.frame_id, geometry.timestamp_s) != identity:
                raise ValueError("source/tracking frame identity mismatch")
            if (packet.run_id, packet.frame_id, packet.timestamp_s) != identity:
                raise ValueError("presentation/tracking frame identity mismatch")
            if packet.image.shape[:2] != (geometry.height, geometry.width):
                raise ValueError("presentation dimensions differ from actual source frame")
            if legacy is not None and (legacy.run_id, legacy.frame_id, legacy.timestamp_s) != identity:
                raise ValueError("legacy/tracking frame identity mismatch")
            if (old is not None and (old.run_id, old.frame_id, old.timestamp_s) == identity
                    and old.frame_geometry == geometry and self._last_tracking == frame
                    and self._last_legacy == legacy):
                return old  # Identical diagnostic delivery; no second update/log.
            hand = extract_hand_geometry(frame, geometry)
            pose = classify_pose(hand, self.profile.pose)
            temporal = self.tracker.update(pose, tracking_status=frame.status,
                                           filter_reset=frame.filter_diagnostics.reset_occurred)
        except Exception as exc:
            errors = (f"observation unavailable: {type(exc).__name__}: {exc}",)
            temporal = self.tracker.reset()
        snapshot = FullHandSnapshot(CompositionMode.OBSERVE_FULL_HAND, *identity,
                                    frame.status, hand is not None and hand.valid and not errors,
                                    geometry, hand, pose, temporal, errors)
        self.latest_snapshot = snapshot
        self._last_tracking, self._last_legacy = frame, legacy
        if self.sink is not None:
            try:
                self.sink(snapshot)
            except Exception as exc:
                error = f"observation sink failed: {type(exc).__name__}: {exc}"
                self.latest_snapshot = snapshot = replace(snapshot, analysis_valid=False,
                                                          errors=(*errors, error))
                if error not in self._sink_errors:
                    self._sink_errors.add(error)
                    try:
                        warnings.warn(error, RuntimeWarning, stacklevel=2)
                    except RuntimeWarning:
                        # -Werror must not give a diagnostic sink command authority.
                        pass  # The immutable latest snapshot still exposes the error.
        return snapshot

    def presentation_callback(self, legacy_presentation):
        def consume(packet, frame, interaction):
            self.consume(packet, frame, interaction)
            return legacy_presentation(packet, frame, interaction)
        return consume


class GeometryCaptureSource:
    """Capture shape/identity before processing; pass the SAME source packet."""

    def __init__(self, source: FrameSource, observer: FullHandObserver) -> None:
        self.source, self.observer = source, observer

    def open(self) -> None:
        self.observer.reset()
        self.source.open()

    def read(self) -> FramePacket | None:
        packet = self.source.read()
        if packet is not None:
            self.observer.capture(packet)
        return packet

    def close(self) -> None:
        try:
            self.source.close()
        finally:
            self.observer.reset()


class SnapshotJournal:
    """Separate Extension JSONL, never writes Core/G7 logs or webcam images."""

    def __init__(self, directory: Path, profile: ObserveProfile, metadata: dict,
                 *, webcam_images_stored: bool = False) -> None:
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        profile_data = asdict(profile)
        canonical = json.dumps(profile_data, sort_keys=True, allow_nan=False)
        manifest = {
            "schema": "full-hand-observe-v1", "mode": CompositionMode.OBSERVE_FULL_HAND,
            "legacy_metadata": metadata, "profile": profile_data,
            "profile_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "scope": "development observation; not G7 research evidence",
            "commands": "legacy GestureEngine only", "webcam_images_stored": webcam_images_stored,
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
        self._file = (directory / "snapshots.jsonl").open("x", encoding="utf-8")
        self._last_console = None

    def consume(self, snapshot: FullHandSnapshot) -> None:
        self._file.write(json.dumps(asdict(snapshot), allow_nan=False) + "\n")
        self._file.flush()
        summary = (snapshot.tracking_status, snapshot.pose.pose if snapshot.pose else None,
                   snapshot.temporal.stable_pose, snapshot.temporal.armed, snapshot.errors,
                   tuple(f.state for f in snapshot.pose.fingers) if snapshot.pose else ())
        if summary != self._last_console:
            self._last_console = summary
            fingers = ",".join(f"{f.finger.value}:{f.state.value}" for f in snapshot.pose.fingers) if snapshot.pose else "unavailable"
            candidate = snapshot.pose.pose.value if snapshot.pose else "unavailable"
            print(f"[OBSERVE_FULL_HAND] frame={snapshot.frame_id} tracking={summary[0].value} "
                  f"candidate={candidate} stable={summary[2].value} fingers={fingers} "
                  f"armed={summary[3]} transition={snapshot.temporal.transition_id} "
                  f"reasons={snapshot.temporal.reasons} errors={snapshot.errors}")

    def close(self) -> None:
        self._file.close()
