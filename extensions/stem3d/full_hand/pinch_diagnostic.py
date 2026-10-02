"""Opt-in physical labels and measurements, without command authority."""

from dataclasses import asdict
import hashlib
import json
import math
import time
from pathlib import Path
import warnings

from dip_touchless.core import CoordinateSpace

PHYSICAL_LABELS = ("PINCH_TOUCH", "PINCH_RELEASE", "PINCH_NEAR_NO_TOUCH", "PINCH_MEDIUM_SEPARATION")


def measure(landmarks, geometry):
    """Image-height distances; z is recorded only, never used as depth."""
    result = {"valid": False, "reason": None, "landmark_4": None,
              "landmark_8": None, "distance_image_height": None,
              "palm_width_image_height": None, "distance_palm": None}
    if geometry is None:
        result["reason"] = "FRAME_GEOMETRY_UNAVAILABLE"
        return result
    points = {p.index: p for p in landmarks}
    if len(landmarks) != 21 or len(points) != 21 or set(points) != set(range(21)):
        result["reason"] = "LANDMARK_INDICES"
        return result
    if any(p.coordinate_space is not CoordinateSpace.FRAME_NORMALIZED for p in landmarks):
        result["reason"] = "COORDINATE_SPACE"
        return result
    if any(not all(math.isfinite(v) for v in (p.x, p.y, p.z)) for p in landmarks):
        result["reason"] = "NON_FINITE_COORDINATE"
        return result
    for index in (4, 8):
        p = points[index]
        result[f"landmark_{index}"] = [p.x, p.y, p.z]
    aspect = geometry.width / geometry.height
    def distance(a, b):
        return math.hypot((points[a].x - points[b].x) * aspect,
                          points[a].y - points[b].y)
    numerator, denominator = distance(4, 8), distance(5, 17)
    result.update(distance_image_height=numerator, palm_width_image_height=denominator)
    if denominator <= 1e-12:
        result["reason"] = "DEGENERATE_PALM"
        return result
    result.update(valid=True, distance_palm=numerator / denominator)
    return result


class MarkerEdges:
    """Read pressed keys only; never remove events from the legacy event queue."""

    def __init__(self):
        self.previous = set()

    def update(self, pressed, focused=True):
        current = set(pressed)
        rising = current - self.previous if focused else set()
        self.previous = current
        if len(set(PHYSICAL_LABELS) & rising) > 1:
            return ("CONFLICTING_MARKERS",)
        return tuple(name for name in (*PHYSICAL_LABELS, "NOTE") if name in rising)


def poll_markers(*, calibration=False):
    import pygame
    keys = pygame.key.get_pressed()
    bindings = [(pygame.K_t, "PINCH_TOUCH"), (pygame.K_u, "PINCH_RELEASE"), (pygame.K_n, "NOTE")]
    if calibration:
        bindings.extend(((pygame.K_v, "PINCH_NEAR_NO_TOUCH"), (pygame.K_b, "PINCH_MEDIUM_SEPARATION")))
    return {name for key, name in bindings
            if keys[key]}, pygame.key.get_focused()


class PinchDiagnosticJournal:
    def __init__(self, directory, profile, poll=poll_markers, *, visual_capture=False,
                 calibration_labels=False):
        self.poll = (lambda: poll_markers(calibration=calibration_labels)) if poll is poll_markers else poll
        self.edges = MarkerEdges()
        self.phase, self.marker_id, self.last_identity = "UNLABELED", 0, None
        self.enter = profile.pose.pinch_enter_distance_palm
        self.exit = profile.pose.pinch_exit_distance_palm
        self.visual = None
        if visual_capture:
            from .pinch_visual import PinchVisualCapture
            self.visual = PinchVisualCapture(directory, max_samples=40 if calibration_labels else 24)
        self.rows = (directory / "pinch_geometry.jsonl").open("x", encoding="utf-8")
        try:
            self.markers = (directory / "physical_markers.jsonl").open("x", encoding="utf-8")
        except Exception:
            self.rows.close()
            raise
        manifest = {
            "schema": "physical-pinch-diagnostic-v1", "scope": "development; not G7 evidence",
            "keys": {"T": "PINCH_TOUCH", "U": "PINCH_RELEASE", "N": "NOTE"},
            "calibration_labels": calibration_labels,
            "extra_keys": {"V": "PINCH_NEAR_NO_TOUCH", "B": "PINCH_MEDIUM_SEPARATION"} if calibration_labels else {},
            "label_alignment": "operator key rising edge at current presentation frame; human timing uncertainty",
            "distance_units": "hypot(dx * frame_width/frame_height, dy) / MCP5--MCP17 width",
            "enter": self.enter, "exit": self.exit,
            "visual_capture": visual_capture,
            "visual_samples": f"marker frame + >=0.5s held frame, capped at {self.visual.max_samples} samples" if visual_capture else None,
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                              (Path(__file__), Path(__file__).with_name("pinch_visual.py"),
                               Path(__file__).parents[1] / "full_hand_app.py")},
        }
        (directory / "pinch_diagnostic_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")

    def consume(self, frame, snapshot, packet=None):
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if identity == self.last_identity:
            return
        if identity != (snapshot.run_id, snapshot.frame_id, snapshot.timestamp_s):
            raise ValueError("diagnostic frame/snapshot identity mismatch")
        self.last_identity = identity
        pressed, focused = self.poll()
        marker_poll_time = time.perf_counter()
        events = []
        for event in self.edges.update(pressed, focused):
            self.marker_id += 1
            if event in PHYSICAL_LABELS:
                self.phase = event
            elif event == "CONFLICTING_MARKERS":
                self.phase = "UNLABELED"
            marker = dict(run_id=frame.run_id, frame_id=frame.frame_id,
                          timestamp_s=frame.timestamp_s, marker_id=self.marker_id, event=event,
                          poll_perf_counter_s=marker_poll_time)
            events.append(marker)
            self.markers.write(json.dumps(marker) + "\n")
            self.markers.flush()
            print(f"[PHYSICAL MARKER {self.marker_id}] {event} frame={frame.frame_id}")
        filtered = measure(frame.filtered_landmarks, snapshot.frame_geometry)
        raw = measure(frame.raw_landmarks, snapshot.frame_geometry)
        d = filtered["distance_palm"]
        zone = None if d is None else "ENTER" if d < self.enter else "RELEASE" if d > self.exit else "BAND"
        row = dict(run_id=frame.run_id, frame_id=frame.frame_id, timestamp_s=frame.timestamp_s,
                   phase=self.phase, marker_id=self.marker_id, tracking_status=frame.status,
                   analysis_valid=snapshot.analysis_valid, raw=raw, filtered=filtered, zone=zone,
                   candidate_pose=snapshot.pose.pose if snapshot.pose else None,
                   geometry=snapshot.frame_geometry and asdict(snapshot.frame_geometry),
                   temporal=asdict(snapshot.temporal), errors=snapshot.errors)
        self.rows.write(json.dumps(row, allow_nan=False) + "\n")
        self.rows.flush()
        if self.visual is not None:
            self.visual.consume(packet, frame, snapshot, row, events)

    def close(self):
        self.rows.close()
        self.markers.close()


def diagnostic_callback(observer, journal, legacy_presentation):
    """Diagnostic failure cannot suppress or duplicate a legacy presentation."""
    reported = set()
    def consume(packet, frame, interaction):
        snapshot = observer.consume(packet, frame, interaction)
        try:
            journal.consume(frame, snapshot, packet)
        except Exception as exc:
            message = f"PINCH diagnostic unavailable: {exc}"
            if message not in reported:
                reported.add(message)
                try:
                    warnings.warn(message, RuntimeWarning)
                except RuntimeWarning:
                    pass
        return legacy_presentation(packet, frame, interaction)
    return consume
