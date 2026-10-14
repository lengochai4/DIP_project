"""Synchronous frozen Core on one worker thread; bounded latest presentation mailbox."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from threading import Event, Lock
import traceback
from PySide6.QtCore import QThread, Signal
from app.config import ROOT
from .hand_runtime import ProductHandRuntime


class RuntimeWorker(QThread):
    failure = Signal(str)
    status = Signal(str)

    def __init__(self, config, camera_index=0, parent=None, *, engine="PRODUCT"):
        super().__init__(parent)
        self.config = config
        self.camera_index = camera_index
        if engine not in {"PRODUCT", "LEGACY"}:
            raise ValueError("invalid interaction engine")
        self.engine = engine
        self.stop_event = Event()
        self.lock = Lock()
        self.latest = None
        self.last_failure = None
        self.run_id = "stem-v2-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    def stop(self):
        self.stop_event.set()

    def take_latest(self):
        with self.lock:
            value, self.latest = self.latest, None
            return value

    def run(self):
        product = output = None
        try:
            from extensions.stem3d import live_demo
            from dip_touchless.configuration import resolve_config
            from dip_touchless.telemetry import build_run_metadata

            resolved = resolve_config(
                ROOT / "config/default.yaml",
                overrides={
                    "tracking": {
                        "model_path": str(ROOT / "models/hand_landmarker.task")
                    },
                    "camera": {"index": self.camera_index},
                    "filter": {"mode": "RAW"},
                    "logging": {"output_dir": "runs/product-v2/core"},
                },
            )
            cfg = resolved.to_dict()
            metadata = build_run_metadata(resolved, run_id=self.run_id)
            if self.engine == "PRODUCT":
                product = ProductHandRuntime(
                    ROOT / "models/hand_landmarker.task", cfg, self.config
                )
            directory = ROOT / "runs/product-v2" / self.run_id
            directory.mkdir(parents=True, exist_ok=False)
            output = (directory / "observations.jsonl").open("x", encoding="utf-8")
            manifest = {
                "schema": "product-v2-5",
                "version": "2.0.0rc1",
                "run_id": self.run_id,
                "product_profile": asdict(self.config),
                "core_metadata": metadata,
                "product_pipeline": (
                    "independent full-frame P1, mirrored MediaPipe VIDEO extra-hand guard, at most 2 associated hands, canonical F1"
                    if self.engine == "PRODUCT"
                    else "not run; explicit legacy Core path only"
                ),
                "physical_validation": "NOT RUN",
                "raw_video_stored": False,
                "quality": "unavailable",
                "G7_results_invalidated": False,
                "selected_engine": self.engine,
                "product_interaction": (
                    {
                        "pose_geometry": "aspect-correct model-relative xyz joint bends; nonmetric",
                        "pinch_geometry": "unchanged aspect-correct image xy / palm span",
                        "HAND_pointer": "unmirrored source snapshot -> mirror/letterbox once; no gain",
                        "HAND_anchor": "LIVE: any extended tip; RECORDED: open acquisition; same observed associated palm until loss/reset",
                        "HAND_UI": "explicit exclusive window control",
                        "LIVE_geometry": "all extended tips from either/both hands; automatic continuous vertices, per-palm relative z visual relief",
                        "LIVE_topology": "point/segment/triangle; planar polygon or closed convex hull according to relative scene planarity; no physical depth reconstruction",
                    }
                    if self.engine == "PRODUCT"
                    else None
                ),
            }
            manifest["source_sha256"] = {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / "app").rglob("*.py")
            }
            (directory / "manifest.json").write_text(
                json.dumps(manifest, indent=2, default=str), encoding="utf-8"
            )

            def consume(packet, frame, legacy):
                filtered, valid, reason = (
                    product.process(packet)
                    if product is not None
                    else ({}, False, "EXPLICIT_LEGACY")
                )
                output.write(
                    json.dumps(
                        {
                            "frame_id": frame.frame_id,
                            "timestamp_s": frame.timestamp_s,
                            "valid": valid,
                            "reason": reason,
                            "hands": {
                                k: [asdict(p) for p in v] for k, v in filtered.items()
                            },
                        },
                        default=str,
                        allow_nan=False,
                    )
                    + "\n"
                )
                with self.lock:
                    self.latest = packet, frame, legacy, filtered, valid, reason

            # Controller implements public consumer/stop seams; never owns or mutates Core.
            worker = self

            class Sink:
                def consume_interaction(self, state):
                    pass

                def consume_presentation(self, packet, frame, legacy):
                    consume(packet, frame, legacy)

                def stop_requested(self):
                    return worker.stop_event.is_set()

            runtime = live_demo._build_runtime(
                cfg=cfg,
                run_id=self.run_id,
                controller=Sink(),
            )
            self.status.emit("Camera starting")
            runtime.run(metadata=metadata, resolved_config=cfg)
        except Exception as exc:
            self.last_failure = (
                f"Camera or hand tracking unavailable: {type(exc).__name__}: {exc}"
            )
            try:
                directory = ROOT / "runs/product-v2" / self.run_id
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "failure.json").write_text(
                    json.dumps(
                        {
                            "run_id": self.run_id,
                            "camera_index": self.camera_index,
                            "engine": self.engine,
                            "error": self.last_failure,
                            "traceback": traceback.format_exc(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except OSError:
                pass  # Keep the original failure available in Analyze even if disk logging fails.
            self.failure.emit(self.last_failure)
        finally:
            errors = []
            for resource in (product, output):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception as exc:
                        errors.append(str(exc))
            if errors:
                self.failure.emit("Cleanup failed: " + "; ".join(errors))
            self.status.emit("Stopped")
