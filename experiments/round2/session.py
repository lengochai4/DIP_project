"""Prepare, guide, record and analyze an independently identified evidence round.

Run as python -m experiments.round2.session. No Core algorithm is modified.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import platform
from pathlib import Path
import re

import cv2
import numpy as np
import yaml

from analysis.regenerate import regenerate_batch
from dip_touchless.capture import OpenCVCameraSource
from dip_touchless.configuration import resolve_config
from dip_touchless.core import FramePacket, TrackingFrame
from dip_touchless.filtering import RawLandmarkFilter
from dip_touchless.preprocessing import (
    AdaptivePreprocessor, IlluminationAnalyzer, IlluminationDecisionStabilizer, ROIManager,
)
from dip_touchless.runtime import RealtimeRuntime
from dip_touchless.telemetry import FileRunLogger, build_run_metadata
from dip_touchless.tracking import MediaPipeHandLandmarkerProvider, MeasurementValidator
from experiments.record_source import record_frame_source
from experiments.run_batch import run_experiment_batch, build_batch_index, write_batch_index
from experiments.manifest import load_experiment_manifest

ROOT = Path(__file__).resolve().parents[2]
PLAN = Path(__file__).with_name("PLAN.md")
WINDOW = "DIP - ROUND2 data collection"
GROUPS = ("static_normal", "dynamic_normal", "static_lowlight")
TASKS = {
    "static_normal": ("NORMAL LIGHT - STATIC", "Keep the whole hand visible. Rest wrist. Hold fingertip still."),
    "dynamic_normal": ("NORMAL LIGHT - MOTION", "Move the whole hand slowly left-right between the two guides."),
    "static_lowlight": ("LOW FRONT LIGHT - STATIC", "Reduce front light. Keep the same hand pose and camera position."),
}
BATCHES = ("a1_static", "a2_dynamic", "b_normal", "b_lowlight")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def prepare(session_id: str, *, camera_index=0, backend="default") -> Path:
    if not re.fullmatch(r"ROUND2-[A-Za-z0-9_-]+", session_id):
        raise ValueError("session ID must start with ROUND2- and use safe filename characters")
    folder = ROOT / "runs" / "round2" / session_id
    if folder.exists():
        raise FileExistsError(f"session already exists: {folder}")
    model = ROOT / "models" / "hand_landmarker.task"
    if not model.is_file():
        raise FileNotFoundError(model)
    resolved = resolve_config(ROOT / "config/default.yaml", overrides={
        "camera": {"index": camera_index, "backend": backend},
        "tracking": {"model_path": str(model)}, "renderer": {"enabled": False},
    })
    folder.mkdir(parents=True)
    (folder / "PLAN.md").write_bytes(PLAN.read_bytes())
    for name in BATCHES:
        payload = yaml.safe_load((ROOT / f"experiments/final/g7_{name}.yaml").read_text(encoding="utf-8"))
        payload["experiment_id"] = f"{session_id}-{name.upper()}"
        payload["model"] = str(model)
        for trial in payload["trials"]:
            group = "static_normal" if name in ("a1_static", "b_normal") else "dynamic_normal" if name == "a2_dynamic" else "static_lowlight"
            trial["source"] = str(folder / "sources" / group / f"{trial['trial_id']}.avi")
        (folder / f"{name}.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    tracked = [p for directory in ("src/dip_touchless", "config", "experiments", "analysis")
               for p in (ROOT / directory).rglob("*") if p.is_file() and p.suffix in (".py", ".yaml", ".md")]
    metadata = build_run_metadata(resolved, run_id=session_id)
    metadata.update({
        "session_id": session_id, "status": "prepared", "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "new evidence round; never replaces frozen G7", "camera_config": resolved.to_dict()["camera"],
        "encoded_fps": 30.0, "frames_per_source": 360, "settle_s": 3.0,
        "replay_timestamp_rule": "frame_id / encoded_fps", "expected_sources": 9,
        "research_sha256": {str(p.relative_to(ROOT)): sha(p) for p in tracked},
        "plan_sha256": sha(folder / "PLAN.md"),
        "manifest_sha256": {name: sha(folder / f"{name}.yaml") for name in BATCHES},
    })
    save_json(folder / "session.json", metadata)
    return folder


def verify_session(folder: Path) -> dict:
    payload = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    if sha(folder / "PLAN.md") != payload["plan_sha256"]:
        raise ValueError("frozen session plan changed")
    for name, digest in payload["manifest_sha256"].items():
        if sha(folder / f"{name}.yaml") != digest:
            raise ValueError(f"frozen manifest changed: {name}")
    for name, digest in payload["research_sha256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"research code/config changed after preparation: {name}")
    model = ROOT / "models/hand_landmarker.task"
    if sha(model) != payload["provider"]["model_checksum"]:
        raise ValueError("model changed after preparation")
    if platform.python_version() != payload["python_version"]:
        raise ValueError("Python changed after preparation; prepare a separately identified session")
    for name, expected in payload["dependency_versions"].items():
        if expected is not None and version(name) != expected:
            raise ValueError(f"dependency changed after preparation: {name}")
    return payload


def validate_recorded_source(path: Path) -> dict:
    """Reject corrupt/mismatched capture artifacts without discarding poor tracking."""
    sidecar = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if sha(path) != sidecar["video"]["sha256"] or sidecar["video"]["frame_count"] != 360:
        raise ValueError(f"source identity/count invalid: {path}")
    with path.with_suffix(".timestamps.csv").open(encoding="utf-8", newline="") as f:
        timeline = list(csv.DictReader(f))
    if len(timeline) != 360 or [int(r["video_frame_id"]) for r in timeline] != list(range(360)):
        raise ValueError(f"acquisition timeline incomplete: {path}")
    timestamps = [float(r["acquisition_timestamp_s"]) for r in timeline]
    if not all(math.isfinite(t) for t in timestamps) or any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError(f"acquisition timestamps invalid: {path}")
    capture = cv2.VideoCapture(str(path))
    count = 0
    try:
        if not capture.isOpened():
            raise ValueError(f"recorded video unreadable: {path}")
        while True:
            ok, image = capture.read()
            if not ok:
                break
            if image.shape[:2] != (sidecar["video"]["encoded_height"], sidecar["video"]["encoded_width"]):
                raise ValueError(f"recorded geometry invalid: {path}")
            count += 1
    finally:
        capture.release()
    if count != 360:
        raise ValueError(f"decoded frame count invalid ({count}): {path}")
    return sidecar


def view(image: np.ndarray, lines: list[str], *, points=(), roi=None, dynamic=False) -> int:
    # Display annotations are never applied to the raw camera buffer.
    displayed = image.copy()
    height, width = displayed.shape[:2]
    if dynamic:
        for x in (int(width * .25), int(width * .75)):
            cv2.line(displayed, (x, 0), (x, height - 1), (70, 220, 220), 1)
    for point in points:
        cv2.circle(displayed, (round(point.x * width), round(point.y * height)), 3, (80, 255, 110), -1)
    if roi is not None:
        cv2.rectangle(displayed, (roi.x, roi.y), (roi.x + roi.width - 1, roi.y + roi.height - 1), (220, 170, 70), 1)
    panel = np.zeros((130 + height, max(width, 900), 3), dtype=np.uint8)
    panel[130:130+height, :width] = displayed
    for index, text in enumerate(lines):
        cv2.putText(panel, text, (14, 24 + 24 * index), cv2.FONT_HERSHEY_SIMPLEX, .53, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.imshow(WINDOW, panel)
    key = cv2.waitKey(1) & 255
    if key in (27, ord("q"), ord("Q")) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
        raise KeyboardInterrupt("operator stopped collection")
    return key


def make_camera(camera: dict, run_id: str) -> OpenCVCameraSource:
    return OpenCVCameraSource(run_id=run_id, camera_index=camera["index"], width=camera["width"],
                              height=camera["height"], requested_fps=camera["requested_fps"], backend=camera["backend"])


def preflight(folder: Path, session: dict, group: str, trial: str) -> None:
    """Run the public realtime pipeline for positioning; keep it outside primary analysis."""
    resolved = resolve_config(ROOT / "config/default.yaml", profile_path=ROOT / "config/experiments/p1.yaml", overrides={
        "camera": session["camera_config"], "tracking": {"model_path": str(ROOT / "models/hand_landmarker.task")},
        "logging": {"output_dir": str(folder / "preflight")}, "renderer": {"enabled": False},
        "experiment": {"experiment_id": session["session_id"] + "-PREFLIGHT", "trial_id": f"{group}-{trial}"},
    })
    config = resolved.to_dict()
    done = False
    last_status = None

    def present(packet: FramePacket, frame: TrackingFrame, _interaction) -> None:
        nonlocal done, last_status
        illumination = frame.illumination
        last_status = frame.status.value
        assert illumination is not None
        info = f"{frame.status.value} | V={illumination.mean_v:.1f} range={illumination.robust_range_v:.1f} | {illumination.state.value} | CLAHE={illumination.enhancement_active}"
        key = view(packet.image, [f"{group} / {trial} - CHECK BEFORE RECORDING", TASKS[group][1], info,
                                  "SPACE: confirm setup and start. Q/ESC: stop. All recorded outcomes will be kept."],
                   points=frame.raw_landmarks, roi=frame.roi, dynamic=group == "dynamic_normal")
        if key == 32:
            done = True

    run_id = session["session_id"] + "-preflight-" + datetime.now(timezone.utc).strftime("%H%M%S%f")
    clahe = dict(config["clahe"]); clahe["tile_grid_size"] = tuple(clahe["tile_grid_size"])
    provider_config = {key: value for key, value in config["tracking"].items() if key != "provider"}
    runtime = RealtimeRuntime(
        source=make_camera(config["camera"], run_id),
        provider=MediaPipeHandLandmarkerProvider(**provider_config),
        validator=MeasurementValidator(), landmark_filter=RawLandmarkFilter(), logger=FileRunLogger(folder / "preflight"),
        roi_manager=ROIManager(**config["roi"]), illumination_analyzer=IlluminationAnalyzer(),
        illumination_decision=IlluminationDecisionStabilizer(**config["illumination"]),
        adaptive_preprocessor=AdaptivePreprocessor(**clahe), presentation_consumer=present, stop_requested=lambda: done,
    )
    runtime.run(metadata=build_run_metadata(resolved, run_id=run_id), resolved_config=config)
    with (folder / "setup_confirmations.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"group": group, "trial": trial, "preflight_run": run_id, "status_at_confirmation": last_status,
                            "confirmed_at_utc": datetime.now(timezone.utc).isoformat()}) + "\n")


class PreviewRecordingSource:
    """Raw capture with copy-only preview and actual acquisition timestamps."""
    def __init__(self, source, group: str, trial: str, *, settle_s: float):
        self.source = source
        self.group, self.trial, self.settle_s = group, trial, settle_s
        self.timeline = []

    def __getattr__(self, name):
        return getattr(self.source, name)

    def open(self):
        self.source.open()

    def read(self):
        packet = self.source.read()
        if packet.timestamp_s < self.settle_s:
            phase = f"GET READY: {max(0.0, self.settle_s-packet.timestamp_s):.1f} seconds"
        else:
            self.timeline.append((len(self.timeline), packet.frame_id, packet.timestamp_s))
            phase = f"RECORDING RAW: {len(self.timeline)} / 360 frames"
        view(packet.image, [f"{self.group} / {self.trial} - {phase}", TASKS[self.group][1],
                           "Tracking is not measured during recording. Raw image is saved without annotations.",
                           "Keep performing the task until DONE. Q/ESC: stop."], dynamic=self.group == "dynamic_normal")
        return packet

    def close(self):
        self.source.close()


def collect(folder: Path) -> None:
    session = verify_session(folder)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, 1100, 750)
    session["status"] = "collecting"
    save_json(folder / "session.json", session)
    try:
        for group in GROUPS:
            for index in range(1, 4):
                trial = f"trial-{index:03d}"
                output = folder / "sources" / group / f"{trial}.avi"
                if output.exists():
                    validate_recorded_source(output)
                    continue
                preflight(folder, session, group, trial)
                source = PreviewRecordingSource(make_camera(session["camera_config"], session["session_id"] + "-capture"), group, trial, settle_s=3.0)
                record_frame_source(source=source, output_path=output, frame_count=360, encoded_fps=30.0, settle_s=3.0,
                    requested_camera=session["camera_config"], lighting_label="low-light-room" if group == "static_lowlight" else "normal-room",
                    auto_exposure_status="unknown", auto_white_balance_status="unknown",
                    notes=f"ROUND2 operator confirmed {TASKS[group][0]}; no lux measurement; timestamp rule frame_id / encoded_fps")
                if len(source.timeline) != 360:
                    raise RuntimeError("capture timestamp count does not match recorded frames")
                with output.with_suffix(".timestamps.csv").open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f); writer.writerow(("video_frame_id", "camera_frame_id", "acquisition_timestamp_s")); writer.writerows(source.timeline)
                validate_recorded_source(output)
                print(f"Recorded {group}/{trial}: 360 raw frames", flush=True)
        session["status"] = "recorded"
    except BaseException as error:
        session["status"] = "interrupted"
        session["last_error"] = str(error)
        raise
    finally:
        save_json(folder / "session.json", session)
        cv2.destroyAllWindows()


def analyze(folder: Path) -> dict:
    session = verify_session(folder)
    sources = list((folder / "sources").glob("*/*.avi"))
    if len(sources) != 9:
        raise ValueError("analysis requires the nine planned sources; partial sessions stay explicit")
    for name in BATCHES:
        manifest = load_experiment_manifest(folder / f"{name}.yaml")
        for trial in manifest.trials:
            validate_recorded_source(trial.source)
    result = {}
    for name in BATCHES:
        print(f"Paired replay: {name}", flush=True)
        manifest = load_experiment_manifest(folder / f"{name}.yaml")
        runs = run_experiment_batch(manifest, output_dir=folder / "replay")
        index = write_batch_index(build_batch_index(manifest, runs, manifest_path=folder / f"{name}.yaml"), index_root=folder / "batches")
        result[name] = str(regenerate_batch(batch_index=index, runs_root=folder / "replay", output_root=folder / "analysis"))
    save_json(folder / "analysis_index.json", result)
    session["status"] = "analyzed"
    save_json(folder / "session.json", session)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "collect", "analyze", "all"))
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--session", type=Path)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--backend", default="default", choices=("default", "dshow", "msmf"))
    args = parser.parse_args()
    if args.command in ("prepare", "all") and args.session is None:
        folder = prepare(args.session_id or "ROUND2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), camera_index=args.camera_index, backend=args.backend)
    elif args.session is not None:
        folder = args.session.resolve()
    else:
        parser.error("--session is required for collect/analyze")
    print(f"Session: {folder}", flush=True)
    if args.command in ("collect", "all"):
        collect(folder)
    if args.command in ("analyze", "all"):
        print(json.dumps(analyze(folder), indent=2), flush=True)


if __name__ == "__main__":
    main()
