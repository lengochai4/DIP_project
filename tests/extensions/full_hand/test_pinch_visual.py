"""Synthetic tests for image synchronization, colors, opt-in and parity."""
from dataclasses import asdict, replace
import json

import cv2
import numpy as np
import pytest

from dip_touchless.core import ColorSpace
from extensions.stem3d.full_hand.observe import load_observe_profile
from extensions.stem3d.full_hand.pinch_diagnostic import PinchDiagnosticJournal, diagnostic_callback
from test_observe import PROFILE, _execute, _run


def fixture():
    run = _run(True)
    _execute(run)
    return run


def test_no_visual_storage_without_flag(tmp_path):
    run = fixture()
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: ({"PINCH_TOUCH"}, True))
    try:
        journal.consume(run.logger.tracking[0], run.snapshots[0], run.source.packets[0])
    finally:
        journal.close()
    assert not (tmp_path / "pinch_visual").exists()


@pytest.mark.parametrize("space", [ColorSpace.BGR, ColorSpace.RGB])
def test_synchronized_source_color_overlay_and_immutability(tmp_path, space):
    run = fixture()
    image = np.zeros((90, 160, 3), dtype=np.uint8)
    image[:, :, 0] = 20
    image[:, :, 2] = 240
    packet = replace(run.source.packets[0], image=image, color_space=space)
    original = image.copy()
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: ({"PINCH_TOUCH"}, True), visual_capture=True)
    try:
        journal.consume(run.logger.tracking[0], run.snapshots[0], packet)
    finally:
        journal.close()
    path = tmp_path / "pinch_visual"
    metadata = json.loads(next(path.glob("*.json")).read_text())
    source = cv2.imread(str(path / metadata["original_image"]))
    overlay = cv2.imread(str(path / metadata["overlay_image"]))
    expected = original if space is ColorSpace.BGR else original[:, :, ::-1]
    assert np.array_equal(source, expected)
    assert not np.array_equal(source, overlay)
    assert np.array_equal(image, original)
    assert metadata["frame_id"] == metadata["physical_marker"]["frame_id"] == 0
    assert metadata["marker_offset_s"] == 0
    assert metadata["raw_landmarks"] == [asdict(p) for p in run.logger.tracking[0].raw_landmarks]
    assert metadata["filtered"]["distance_palm"] == pytest.approx(run.snapshots[0].hand.thumb_index_distance_palm)


def test_delayed_sample_cancellation_duplicates_and_bound(tmp_path):
    run = fixture()
    keys = iter([{"PINCH_TOUCH"}, set(), {"PINCH_RELEASE"}] + [set()] * 13)
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: (next(keys), True), visual_capture=True)
    journal.visual.max_samples = 3
    try:
        for packet, frame, snapshot in zip(run.source.packets, run.logger.tracking, run.snapshots):
            journal.consume(frame, snapshot, packet)
            journal.consume(frame, snapshot, packet)
    finally:
        journal.close()
    samples = [json.loads(p.read_text()) for p in (tmp_path / "pinch_visual").glob("*.json")]
    assert len(samples) == 3
    assert sorted((s["frame_id"], s["sample_kind"]) for s in samples) == [(0, "MARKER"), (2, "MARKER"), (6, "HELD_050S")]
    assert all(s["physical_marker"]["event"] == "PINCH_RELEASE" for s in samples if s["sample_kind"] == "HELD_050S")


@pytest.mark.parametrize("mismatch", ["identity", "dimensions"])
def test_misaligned_images_are_not_saved(tmp_path, mismatch):
    run = fixture()
    packet = run.source.packets[0]
    packet = replace(packet, frame_id=30) if mismatch == "identity" else replace(packet, image=np.zeros((40, 40, 3), dtype=np.uint8))
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: ({"PINCH_TOUCH"}, True), visual_capture=True)
    try:
        with pytest.raises(ValueError, match="mismatch"):
            journal.consume(run.logger.tracking[0], run.snapshots[0], packet)
    finally:
        journal.close()
    assert not list((tmp_path / "pinch_visual").iterdir())


def test_visual_runtime_legacy_parity_and_once_only_presentation(tmp_path):
    legacy, observed = _run(False), _run(True)
    events = iter([{"PINCH_RELEASE"}, set(), {"PINCH_TOUCH"}] + [set()] * 13)
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: (next(events), True), visual_capture=True)
    presented = []
    observed.runtime._presentation_consumer = diagnostic_callback(observed.observer, journal, lambda *args: presented.append(args))
    try:
        assert _execute(legacy) == _execute(observed) == 16
    finally:
        journal.close()
    assert [asdict(s) for s in legacy.received] == [asdict(s) for s in observed.received]
    assert len(presented) == 16
    assert all(np.count_nonzero(p.image) == 0 for p in observed.source.packets)


def test_image_write_failure_preserves_legacy_callback(tmp_path, monkeypatch):
    observed = _run(True)
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: ({"PINCH_TOUCH"}, True), visual_capture=True)
    monkeypatch.setattr(cv2, "imwrite", lambda *args: False)
    presented = []
    observed.runtime._presentation_consumer = diagnostic_callback(observed.observer, journal, lambda *args: presented.append(args))
    try:
        with pytest.warns(RuntimeWarning, match="cannot save"):
            assert _execute(observed) == 16
    finally:
        journal.close()
    assert len(presented) == 16


def test_cli_requires_explicit_diagnostic_opt_in():
    from extensions.stem3d.full_hand_app import main
    with pytest.raises(SystemExit) as exc:
        main(["--pinch-visual"])
    assert exc.value.code == 2
