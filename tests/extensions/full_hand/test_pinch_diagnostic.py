"""Read-only measurements, operator labels and legacy parity."""
from dataclasses import asdict, replace
import json
from types import SimpleNamespace

import pytest

from extensions.stem3d.full_hand.contracts import FrameGeometry
from extensions.stem3d.full_hand.pinch_diagnostic import (
    MarkerEdges, PinchDiagnosticJournal, diagnostic_callback, measure,
)
from test_observe import Provider, PROFILE, _execute, _run
from extensions.stem3d.full_hand.observe import load_observe_profile


def points():
    packet = SimpleNamespace(frame_id=0, timestamp_s=0)
    return Provider().process(packet).landmarks


def test_aspect_denominator_coordinates_and_immutability():
    landmarks = points()
    original = tuple(landmarks)
    geometry = FrameGeometry("parity", 0, 0., 160, 90)
    row = measure(landmarks, geometry)
    assert row["valid"]
    assert row["landmark_4"] == [landmarks[4].x, landmarks[4].y, landmarks[4].z]
    assert row["palm_width_image_height"] == pytest.approx((.28 ** 2 + .06 ** 2) ** .5)
    assert row["distance_palm"] == pytest.approx(row["distance_image_height"] / row["palm_width_image_height"])
    assert measure(landmarks, replace(geometry, width=90))["distance_palm"] != row["distance_palm"]
    assert landmarks == original


@pytest.mark.parametrize("kind", ["missing", "duplicate", "nan", "degenerate", "no_geometry"])
def test_unavailable_never_filled_with_zero(kind):
    landmarks = points()
    geometry = FrameGeometry("parity", 0, 0., 160, 90)
    if kind == "missing": landmarks = landmarks[:-1]
    if kind == "duplicate": landmarks = (*landmarks[:-1], landmarks[0])
    if kind == "nan": landmarks = (SimpleNamespace(**{**asdict(landmarks[0]), "x": float("nan")}), *landmarks[1:])
    if kind == "degenerate": landmarks = tuple(replace(p, x=landmarks[5].x, y=landmarks[5].y) if p.index == 17 else p for p in landmarks)
    if kind == "no_geometry": geometry = None
    row = measure(landmarks, geometry)
    assert not row["valid"] and row["reason"] and row["distance_palm"] is None
    json.dumps(row, allow_nan=False)


def test_marker_edges_focus_conflict_and_repeated_hold():
    edges = MarkerEdges()
    assert edges.update({"PINCH_TOUCH"}) == ("PINCH_TOUCH",)
    assert edges.update({"PINCH_TOUCH"}) == ()
    assert edges.update(set()) == ()
    assert edges.update({"PINCH_RELEASE"}, False) == ()
    assert edges.update({"PINCH_RELEASE"}, True) == ()
    edges.update(set())
    assert edges.update({"PINCH_RELEASE", "PINCH_TOUCH"}) == ("CONFLICTING_MARKERS",)


def test_journal_runtime_parity_alignment_and_cleanup(tmp_path):
    legacy, observed = _run(False), _run(True)
    calls = iter([({"PINCH_RELEASE"}, True), (set(), True), ({"PINCH_TOUCH"}, True)] + [(set(), True)] * 13)
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: next(calls))
    # Replace only the callback in this runtime fixture, using its existing seam.
    def present(packet, frame, interaction):
        observed.presented.append((packet, frame, interaction))
    observed.runtime._presentation_consumer = diagnostic_callback(observed.observer, journal, present)
    try:
        assert _execute(legacy) == _execute(observed) == 16
    finally:
        journal.close()
    assert [asdict(s) for s in legacy.received] == [asdict(s) for s in observed.received]
    rows = [json.loads(s) for s in (tmp_path / "pinch_geometry.jsonl").read_text().splitlines()]
    assert len(rows) == 16
    assert rows[2]["phase"] == "PINCH_TOUCH"
    assert rows[0]["raw"] == rows[0]["filtered"]
    assert rows[10]["zone"] is None
    assert len(observed.presented) == 16
    assert journal.rows.closed and journal.markers.closed


def test_sink_failure_still_presents_once():
    interaction, packet, frame = object(), object(), object()
    observer = SimpleNamespace(consume=lambda *args: object())
    journal = SimpleNamespace(consume=lambda *args: (_ for _ in ()).throw(OSError("fixture")))
    seen = []
    with pytest.warns(RuntimeWarning):
        result = diagnostic_callback(observer, journal, lambda *args: seen.append(args))(packet, frame, interaction)
    assert result is None and seen == [(packet, frame, interaction)]


def test_raw_filtered_measurements_are_separate():
    raw = points()
    filtered = tuple(replace(p, x=raw[8].x, y=raw[8].y) if p.index == 4 else p for p in raw)
    geometry = FrameGeometry("parity", 0, 0., 160, 90)
    assert measure(raw, geometry)["distance_palm"] > 0
    assert measure(filtered, geometry)["distance_palm"] == 0


def test_identity_rejection_and_duplicate_do_not_create_markers(tmp_path):
    observed = _run(True)
    _execute(observed)
    frame = observed.logger.tracking[0]
    snapshot = observed.snapshots[0]
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(PROFILE), lambda: ({"PINCH_TOUCH"}, True))
    try:
        with pytest.raises(ValueError, match="identity"):
            journal.consume(replace(frame, frame_id=9), snapshot)
        journal.consume(frame, snapshot)
        journal.consume(frame, snapshot)
    finally:
        journal.close()
    assert len((tmp_path / "physical_markers.jsonl").read_text().splitlines()) == 1
    assert len((tmp_path / "pinch_geometry.jsonl").read_text().splitlines()) == 1
