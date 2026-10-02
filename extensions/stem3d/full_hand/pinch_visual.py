"""Bounded local marker-frame captures; never research/submission evidence."""

from dataclasses import asdict
import json
import math
import time

from dip_touchless.core import ColorSpace, CoordinateSpace


class PinchVisualCapture:
    """Save marker frame plus one held-state frame >= 0.5 s later.

    The delayed sample is cancelled by a new physical marker. No video buffer,
    continuous image storage, mirroring, commands or UI event consumption.
    """

    def __init__(self, directory, max_samples=24):
        self.directory = directory / "pinch_visual"
        self.directory.mkdir(exist_ok=False)
        self.max_samples = max_samples
        self.count = 0
        self.pending = None

    def consume(self, packet, frame, snapshot, row, markers):
        from .pinch_diagnostic import PHYSICAL_LABELS
        for marker in markers:
            if marker["event"] in (*PHYSICAL_LABELS, "CONFLICTING_MARKERS"):
                self.pending = None
            if marker["event"] in PHYSICAL_LABELS:
                self._save(packet, frame, snapshot, row, marker, "MARKER")
                self.pending = marker
        if self.pending and not markers and frame.timestamp_s >= self.pending["timestamp_s"] + .5:
            marker, self.pending = self.pending, None
            self._save(packet, frame, snapshot, row, marker, "HELD_050S")

    def _save(self, packet, frame, snapshot, row, marker, sample_kind):
        if self.count >= self.max_samples:
            return
        if packet is None:
            raise ValueError("visual diagnostic requires synchronized presentation packet")
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if identity != (packet.run_id, packet.frame_id, packet.timestamp_s):
            raise ValueError("visual packet/tracking identity mismatch")
        geometry = snapshot.frame_geometry
        if geometry is None or packet.image.shape[:2] != (geometry.height, geometry.width):
            raise ValueError("visual packet/frame geometry mismatch")
        import cv2
        if packet.color_space is ColorSpace.BGR:
            image = packet.image.copy()
        elif packet.color_space is ColorSpace.RGB:
            image = cv2.cvtColor(packet.image, cv2.COLOR_RGB2BGR)
        elif packet.color_space is ColorSpace.GRAY:
            image = cv2.cvtColor(packet.image, cv2.COLOR_GRAY2BGR)
        elif packet.color_space is ColorSpace.HSV:
            image = cv2.cvtColor(packet.image, cv2.COLOR_HSV2BGR)
        else:
            raise ValueError("unsupported diagnostic image color space")
        overlay = image.copy()
        raw, filtered = frame.raw_landmarks, frame.filtered_landmarks
        height, width = image.shape[:2]
        def pixel(p):
            # Frame-normalized units are fractions of full dimensions. Do not
            # clamp out-of-frame provider coordinates into invented edge points.
            return round(p.x * width), round(p.y * height)
        def usable(points):
            return {p.index: p for p in points if p.coordinate_space is CoordinateSpace.FRAME_NORMALIZED
                    and all(math.isfinite(v) for v in (p.x, p.y, p.z))}
        raw_points, filtered_points = usable(raw), usable(filtered)
        for index in (0, 5, 9, 13, 17, 4, 8):
            color = (255, 0, 255) if index == 4 else (0, 255, 255) if index == 8 else (0, 220, 0)
            if index in raw_points:
                xy = pixel(raw_points[index])
                cv2.circle(overlay, xy, 3, color, -1)
                cv2.putText(overlay, str(index), (xy[0] + 6, xy[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
            if index in filtered_points:
                cv2.circle(overlay, pixel(filtered_points[index]), 7, color, 1)
        for a, b, color in ((5, 17, (0, 220, 0)), (4, 8, (255, 255, 255))):
            if a in filtered_points and b in filtered_points:
                cv2.line(overlay, pixel(filtered_points[a]), pixel(filtered_points[b]), color, 1)
        lines = [f"LOCAL DEVELOPMENT ONLY | {marker['event']} | {sample_kind}",
                 f"frame={frame.frame_id} t={frame.timestamp_s:.6f} marker_dt={frame.timestamp_s-marker['timestamp_s']:.3f}s",
                 f"distance/palm={row['filtered']['distance_palm']} zone={row['zone']}",
                 f"palm width={row['filtered']['palm_width_image_height']}",
                 "4 magenta / 8 yellow / palm green; raw dots, filtered rings; unmirrored"]
        for i, text in enumerate(lines):
            cv2.putText(overlay, text, (8, 18 + i * 19), cv2.FONT_HERSHEY_SIMPLEX, .40, (0, 0, 0), 3)
            cv2.putText(overlay, text, (8, 18 + i * 19), cv2.FONT_HERSHEY_SIMPLEX, .40, (255, 255, 255), 1)
        stem = f"marker-{marker['marker_id']:03d}_frame-{frame.frame_id:06d}_{sample_kind}"
        metadata = {**row, "physical_marker": marker, "sample_kind": sample_kind,
                    "marker_offset_s": frame.timestamp_s - marker["timestamp_s"],
                    "capture_perf_counter_s": time.perf_counter(),
                    "image_source": "synchronized full-frame presentation copy; unmirrored",
                    "source_color_space": packet.color_space, "png_codec_input": "BGR",
                    "raw_landmarks": [asdict(p) for p in raw],
                    "filtered_landmarks": [asdict(p) for p in filtered],
                    "tracking_compute_total_ms": frame.timings.compute_total_ms,
                    "scope": "local development diagnostic; not research/submission evidence",
                    "original_image": stem + "_source.png", "overlay_image": stem + "_overlay.png"}
        for name, pixels in ((metadata["original_image"], image), (metadata["overlay_image"], overlay)):
            if not cv2.imwrite(str(self.directory / name), pixels):
                raise OSError(f"cannot save local diagnostic sample {name}")
        (self.directory / (stem + ".json")).write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
        self.count += 1
