import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from dip_touchless.core import ColorSpace, FramePacket, LandmarkObservation, MeasurementQuality, TrackingStatus
from experiments.round2 import session
from experiments.record_source import record_frame_source
from experiments.manifest import load_experiment_manifest


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    original = session.ROOT
    shutil.copytree(original / "config", root / "config")
    shutil.copytree(original / "experiments/final", root / "experiments/final")
    (root / "models").mkdir()
    (root / "models/hand_landmarker.task").write_bytes(b"fixture-model")
    monkeypatch.setattr(session, "ROOT", root)
    return session.prepare("ROUND2-fixture")


def test_session_freezes_same_primary_metrics_and_matched_sources(prepared):
    payload = session.verify_session(prepared)
    assert payload["expected_sources"] == 9
    assert payload["status"] == "prepared"
    manifests = {name: load_experiment_manifest(prepared / f"{name}.yaml") for name in session.BATCHES}
    assert manifests["a1_static"].primary_metric == "radial_rms_jitter"
    assert manifests["a2_dynamic"].primary_metric == "trajectory_deviation_rmse"
    for manifest in manifests.values():
        assert len(manifest.trials) == 3
        assert (manifest.analysis_start_s, manifest.analysis_end_s) == (2.0, 10.0)
    assert [t.source for t in manifests["a1_static"].trials] == [t.source for t in manifests["b_normal"].trials]
    assert manifests["a1_static"].profiles == ("f0", "f1", "f2")
    assert manifests["b_lowlight"].profiles == ("p0", "p1")


def test_session_rejects_manifest_tampering_and_partial_analysis(prepared):
    with pytest.raises(ValueError, match="nine planned sources"):
        session.analyze(prepared)
    path = prepared / "a2_dynamic.yaml"
    path.write_text(path.read_text().replace("10.0", "9.0"))
    with pytest.raises(ValueError, match="frozen manifest changed"):
        session.verify_session(prepared)


def test_session_rejects_research_and_model_changes(prepared):
    config = session.ROOT / "config/default.yaml"
    config.write_text(config.read_text() + "\n# changed\n")
    with pytest.raises(ValueError, match="research code/config changed"):
        session.verify_session(prepared)


def test_preparation_never_overwrites_existing_session(prepared):
    before = (prepared / "session.json").read_bytes()
    with pytest.raises(FileExistsError):
        session.prepare("ROUND2-fixture")
    assert (prepared / "session.json").read_bytes() == before


@pytest.mark.parametrize("value", ["../escape", "ROUND2-../escape", "ROUND2-a/b", "G7-final", ""])
def test_session_id_cannot_escape_workspace(value):
    with pytest.raises(ValueError):
        session.prepare(value)


def test_preview_does_not_mutate_recorded_pixels(monkeypatch):
    image = np.full((100, 120, 3), 70, dtype=np.uint8)
    before = image.copy()
    shown = []
    monkeypatch.setattr(session.cv2, "imshow", lambda _, frame: shown.append(frame.copy()))
    monkeypatch.setattr(session.cv2, "waitKey", lambda _: 255)
    monkeypatch.setattr(session.cv2, "getWindowProperty", lambda *_: 1)
    session.view(image, ["fixture"], dynamic=True)
    np.testing.assert_array_equal(image, before)
    assert np.any(shown[0][130:230, :120] != image)


def test_recorder_preserves_raw_bytes_and_acquisition_timeline(tmp_path, monkeypatch):
    packets = [FramePacket("fixture", n, n/10, np.full((2, 2, 3), n, dtype=np.uint8), ColorSpace.BGR, "fixture") for n in range(4)]
    class Source:
        def __init__(self): self.index = 0; self.closed = False
        def open(self): pass
        def close(self): self.closed = True
        def read(self):
            result = packets[self.index]; self.index += 1; return result
    class Writer:
        def __init__(self, path): self.path = path; path.write_bytes(b"")
        def write(self, image):
            with self.path.open("ab") as f: f.write(image.tobytes())
        def release(self): pass
    source = Source()
    wrapper = session.PreviewRecordingSource(source, "static_normal", "trial-001", settle_s=.1)
    monkeypatch.setattr(session, "view", lambda *_args, **_kwargs: 255)
    path = tmp_path / "source.avi"
    record_frame_source(source=wrapper, output_path=path, frame_count=3, encoded_fps=10, settle_s=.1,
        requested_camera={}, lighting_label="fixture", auto_exposure_status="unknown", auto_white_balance_status="unknown",
        writer_factory=lambda path, *_: Writer(path))
    assert path.read_bytes() == b"".join(p.image.tobytes() for p in packets[1:])
    assert wrapper.timeline == [(0, 1, .1), (1, 2, .2), (2, 3, .3)]
    assert source.closed


def test_capture_cancel_does_not_leave_a_plausible_partial_source(tmp_path, monkeypatch):
    class Source:
        closed = False
        def open(self): pass
        def close(self): self.closed = True
        def read(self): return FramePacket("fixture", 0, 0, np.zeros((2, 2, 3), dtype=np.uint8), ColorSpace.BGR, "fixture")
    source = Source()
    wrapper = session.PreviewRecordingSource(source, "static_normal", "trial-001", settle_s=0)
    def cancel(*_args, **_kwargs): raise KeyboardInterrupt()
    monkeypatch.setattr(session, "view", cancel)
    path = tmp_path / "source.avi"
    with pytest.raises(KeyboardInterrupt):
        record_frame_source(source=wrapper, output_path=path, frame_count=360, encoded_fps=30, settle_s=0,
            requested_camera={}, lighting_label="fixture", auto_exposure_status="unknown", auto_white_balance_status="unknown")
    assert source.closed
    assert not path.exists()
    assert not path.with_suffix(".json").exists()


def test_preflight_runs_real_public_pipeline_and_records_confirmation(prepared, monkeypatch):
    class Camera:
        def __init__(self): self.closed = False; self.run_id = None
        def open(self): pass
        def read(self): return FramePacket(self.run_id, 0, .1, np.full((8, 8, 3), 100, dtype=np.uint8), ColorSpace.BGR, "fixture")
        def close(self): self.closed = True
    class Provider:
        def __init__(self, **_kwargs): self.closed = False
        def process(self, frame):
            return LandmarkObservation(frame.frame_id, frame.timestamp_s, TrackingStatus.NO_HAND, (), None, None,
                                       MeasurementQuality.unavailable(), None, "fixture")
        def close(self): self.closed = True
    camera = Camera()
    def camera_factory(_config, run_id): camera.run_id = run_id; return camera
    monkeypatch.setattr(session, "make_camera", camera_factory)
    monkeypatch.setattr(session, "MediaPipeHandLandmarkerProvider", Provider)
    shown = []
    def view(image, lines, **_kwargs): shown.append(lines); return 32
    monkeypatch.setattr(session, "view", view)
    session.preflight(prepared, session.verify_session(prepared), "static_normal", "trial-001")
    assert camera.closed
    assert "NO_HAND" in shown[0][2]
    confirmation = json.loads((prepared / "setup_confirmations.jsonl").read_text())
    assert confirmation["status_at_confirmation"] == "NO_HAND"
    assert list((prepared / "preflight").glob("*/frames.csv"))
