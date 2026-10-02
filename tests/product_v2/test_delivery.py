"""Offline source delivery, frozen compatibility and worker failure cleanup."""

import ast
import hashlib
import json
import zipfile
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from app.config import ROOT, ProductConfig
from app.runtime.application_runtime import RuntimeWorker
from developer_tools.package_v2 import build


def test_source_archive_contents_crc_hashes_and_private_data_exclusion(tmp_path):
    path = tmp_path / "product.zip"
    manifest = build(path)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert {
            "app/main.py",
            "config/product_v2.yaml",
            "pyproject.toml",
            "launch_v2.ps1",
            "setup_v2.ps1",
            "release/v2/README.md",
        } <= set(archive.namelist())
        assert not any(
            n.startswith(("runs/", ".venv/", ".git/")) for n in archive.namelist()
        )
        assert "models/hand_landmarker.task" not in archive.namelist()
        assert (
            json.loads(archive.read("PACKAGE_MANIFEST.json"))["physical_validation"]
            == "NOT RUN"
        )
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest


def test_scene_code_does_not_import_provider_tracking_or_hand_geometry():
    for path in (ROOT / "app/extensions").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    word in (node.module or "")
                    for word in (
                        "mediapipe",
                        "tracking",
                        "hand_geometry",
                        "hand_runtime",
                        "finger",
                    )
                )


def test_worker_startup_failure_is_explicit_and_partial_resource_closed(monkeypatch):
    from app.runtime import application_runtime
    from extensions.stem3d import live_demo

    app = QApplication.instance() or QApplication([])
    closed = []

    class Product:
        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            closed.append(True)

    def fail(**kwargs):
        raise RuntimeError("synthetic camera initialization failure")

    monkeypatch.setattr(application_runtime, "ProductHandRuntime", Product)
    monkeypatch.setattr(live_demo, "_build_runtime", fail)
    worker = RuntimeWorker(ProductConfig())
    errors = []
    worker.failure.connect(errors.append)
    worker.run()
    assert closed == [True] and len(errors) == 1 and "synthetic camera" in errors[0]
    worker.stop()
    assert worker.stop_event.is_set()


def test_explicit_legacy_worker_does_not_construct_product_provider(monkeypatch):
    from app.runtime import application_runtime
    from extensions.stem3d import live_demo

    app = QApplication.instance() or QApplication([])

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy must not initialize the product provider")

    class Runtime:
        def run(self, **kwargs):
            return 0

    monkeypatch.setattr(application_runtime, "ProductHandRuntime", forbidden)
    monkeypatch.setattr(live_demo, "_build_runtime", lambda **kwargs: Runtime())
    worker = RuntimeWorker(ProductConfig(), engine="LEGACY")
    errors = []
    worker.failure.connect(errors.append)
    worker.run()
    assert errors == []


@pytest.mark.parametrize("engine", ["PRODUCT", "LEGACY"])
def test_worker_uses_real_legacy_factory_and_public_presentation_callback(
    monkeypatch, tmp_path, engine
):
    """Mock devices only: factory signature, runtime, preprocessing and logger remain real."""
    import numpy as np
    from app.runtime import application_runtime
    from extensions.stem3d import live_demo
    from dip_touchless.core import (
        FramePacket,
        ColorSpace,
        LandmarkObservation,
        TrackingStatus,
        MeasurementQuality,
    )

    application = QApplication.instance() or QApplication([])
    closed = []

    class Camera:
        def __init__(self, *, run_id, **kwargs):
            self.run_id, self.done = run_id, False

        def open(self):
            pass

        def read(self):
            if self.done:
                return None
            self.done = True
            return FramePacket(
                self.run_id,
                0,
                1.0,
                np.zeros((48, 64, 3), np.uint8),
                ColorSpace.BGR,
                "synthetic camera",
            )

        def close(self):
            closed.append("camera")

    class CoreProvider:
        def __init__(self, **kwargs):
            pass

        def process(self, packet):
            return LandmarkObservation(
                packet.frame_id,
                packet.timestamp_s,
                TrackingStatus.NO_HAND,
                (),
                None,
                None,
                MeasurementQuality.unavailable(),
                None,
                "synthetic provider",
            )

        def close(self):
            closed.append("core provider")

    class Product:
        def __init__(self, *args):
            assert engine == "PRODUCT"

        def process(self, packet):
            return {}, False, "SYNTHETIC_NO_HAND"

        def close(self):
            closed.append("product provider")

    monkeypatch.setattr(application_runtime, "ROOT", tmp_path)
    # Config/model assets stay real; only the output root is isolated.
    from app.config import ROOT

    (tmp_path / "config").mkdir()
    (tmp_path / "config/default.yaml").write_bytes(
        (ROOT / "config/default.yaml").read_bytes()
    )
    monkeypatch.setattr(live_demo, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(live_demo, "OpenCVCameraSource", Camera)
    monkeypatch.setattr(live_demo, "MediaPipeHandLandmarkerProvider", CoreProvider)
    monkeypatch.setattr(application_runtime, "ProductHandRuntime", Product)
    worker = RuntimeWorker(ProductConfig(), engine=engine)
    errors = []
    worker.failure.connect(errors.append)
    worker.run()
    assert errors == [] and worker.last_failure is None
    latest = worker.take_latest()
    assert latest is not None and latest[0].frame_id == 0
    assert latest[1].status is TrackingStatus.NO_HAND
    assert latest[2] is not None and not latest[2].interaction_valid
    assert latest[5] == (
        "SYNTHETIC_NO_HAND" if engine == "PRODUCT" else "EXPLICIT_LEGACY"
    )
    assert "camera" in closed and "core provider" in closed
    assert ("product provider" in closed) == (engine == "PRODUCT")
    records = (
        (tmp_path / "runs/product-v2" / worker.run_id / "observations.jsonl")
        .read_text()
        .splitlines()
    )
    assert len(records) == 1 and json.loads(records[0])["frame_id"] == 0
