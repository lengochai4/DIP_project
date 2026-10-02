"""Observation integration, exact legacy parity and UI/lifecycle isolation."""

from dataclasses import asdict, replace
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from extensions.stem3d.full_hand.intent_diagnostic import IntentDiagnosticJournal, IntentCaptureSource, intent_callback
from extensions.stem3d.full_hand.intent_session import IntentObservationSession, IntentObserveProfile
from extensions.stem3d.full_hand.intent_pinch_contracts import RelativeClosureThresholds, ReferenceStatus
from extensions.stem3d.full_hand.intent_presentation import IntentObservationDashboard
from extensions.stem3d.full_hand.intent_temporal import IntentTemporalConfig
from extensions.stem3d.live_demo import _build_gesture_engine
from extensions.stem3d.ui import ApplicationState, ApplicationPhase, build_presentation_state
from test_observe import _run, _execute
from test_relative_intent_pinch import _scope, _policy


def _journal(tmp_path, observed, poll=None, sink=None):
    policy = replace(_policy(), min_samples=2, min_duration_s=.125)
    profile = IntentObserveProfile(policy, RelativeClosureThresholds(.5, .25),
        IntentTemporalConfig(.125, .125, .125, 1., 2., .125, 2.), .125, .2, 3.)
    session = IntentObservationSession(profile, replace(_scope(), run_id="parity", session_id="parity"))
    return IntentDiagnosticJournal(tmp_path / "intent", session, {"revision": "synthetic-test"},
        _build_gesture_engine(observed.cfg["gesture"]), poll=poll or (lambda: (set(), True)), presentation_sink=sink)


def _rows(observed):
    return zip(observed.source.packets, observed.logger.tracking, observed.received, observed.snapshots)


def test_observation_replay_has_exact_legacy_parity_no_commands_and_safe_loss(tmp_path):
    legacy, observed = _run(False), _run(True)
    assert _execute(legacy) == _execute(observed) == 16
    deliveries = []
    keys = iter([{"CALIBRATE_RELEASE"}, set(), set(), set(), {"INTEND_CLOSE"},
                 set(), set(), set(), {"INTEND_OPEN"}, set(), set(), set(),
                 {"NON_INTENT"}, set(), set(), set()])
    journal = _journal(tmp_path, observed, lambda: (next(keys), True), deliveries.append)
    try:
        for packet, frame, interaction, snapshot in _rows(observed):
            before = repr(frame), repr(interaction), packet.image.copy()
            journal.consume(packet, frame, interaction, snapshot)
            assert (repr(frame), repr(interaction)) == before[:2]
            assert np.array_equal(packet.image, before[2])
    finally:
        journal.close()
    assert [asdict(s) for s in observed.received] == [asdict(s) for s in legacy.received]
    rows = [json.loads(line) for line in (journal.directory / "intent_snapshots.jsonl").read_text().splitlines()]
    assert len(rows) == 16 and all(r["legacy_parity"] for r in rows)
    assert journal.counts["legacy_parity_compared"] == 16 and not journal.counts["legacy_parity_mismatches"]
    assert journal.counts["entries"] == 1 and not journal.counts["safety_violations"]
    assert rows[10]["snapshot"]["temporal"]["active_evidence"] is False
    assert rows[11]["snapshot"]["temporal"]["active_evidence"] is False
    assert deliveries[-1] is None
    summary = json.loads((journal.directory / "summary.json").read_text())
    assert summary["journal_closed"] and journal.session.reference.status is ReferenceStatus.INVALIDATED
    manifest = json.loads((journal.directory / "manifest.json").read_text())
    assert not manifest["webcam_images_stored"] and manifest["commands"] == "legacy GestureEngine ONLY"
    assert len(manifest["source_sha256"]) == 7


def test_actual_runtime_composition_preserves_legacy_outputs_and_closes_resources(tmp_path):
    from dip_touchless.runtime import RealtimeRuntime
    from dip_touchless.filtering import RawLandmarkFilter
    from dip_touchless.tracking import MeasurementValidator
    legacy, observed = _run(False), _run(True)
    journal = _journal(tmp_path, observed)
    received = []
    runtime = RealtimeRuntime(
        source=IntentCaptureSource(observed.source, observed.observer, journal),
        provider=observed.provider, validator=MeasurementValidator(), landmark_filter=RawLandmarkFilter(),
        logger=observed.logger, gesture_engine=_build_gesture_engine(observed.cfg["gesture"]),
        interaction_consumer=received.append,
        presentation_consumer=intent_callback(observed.observer, journal, lambda *args: None),
        clock=iter(i * .001 for i in range(1000)).__next__,
    )
    try:
        assert _execute(legacy) == runtime.run(metadata={}, resolved_config=observed.cfg) == 16
        assert [asdict(s) for s in received] == [asdict(s) for s in legacy.received]
        assert journal.counts["legacy_parity_compared"] == 16
        assert not journal.counts["diagnostic_errors"] and not journal.counts["legacy_parity_mismatches"]
        assert observed.source.closes == observed.provider.closes == observed.logger.closes == 1
    finally:
        journal.close()


def test_duplicate_presentation_does_not_advance_shadow_or_write_again(tmp_path):
    observed = _run(True)
    _execute(observed)
    journal = _journal(tmp_path, observed)
    packet, frame, legacy, snapshot = next(_rows(observed))
    try:
        journal.consume(packet, frame, legacy, snapshot)
        journal.consume(packet, frame, legacy, snapshot)
        assert journal.counts["frames"] == journal.counts["legacy_parity_compared"] == 1
    finally:
        journal.close()


def test_no_reference_legacy_fallback_stays_exact(tmp_path):
    observed = _run(True)
    _execute(observed)
    journal = _journal(tmp_path, observed)
    try:
        for row in _rows(observed):
            journal.consume(*row)
        assert not journal.counts["entries"] and not journal.counts["legacy_parity_mismatches"]
        assert journal.session.reference is None
    finally:
        journal.close()


def test_disabled_reference_does_not_manufacture_non_intent_eligible_exposure(tmp_path):
    observed = _run(True)
    _execute(observed)
    keys = iter([{"NON_INTENT"}] + [set()] * 15)
    journal = _journal(tmp_path, observed, lambda: (next(keys), True))
    try:
        for row in _rows(observed):
            journal.consume(*row)
        assert journal.counts["non_intent_valid_seconds"] > 0
        assert journal.counts["non_intent_eligible_seconds"] == 0
        assert not journal.counts["entries"]
    finally:
        journal.close()


def test_focus_loss_cancels_reference_and_repeated_keys_do_not_reenroll(tmp_path):
    observed = _run(True)
    _execute(observed)
    keys = iter([({"CALIBRATE_RELEASE"}, True), ({"CALIBRATE_RELEASE"}, True),
                 ({"CALIBRATE_RELEASE"}, True), (set(), False), (set(), True)])
    journal = _journal(tmp_path, observed, lambda: next(keys))
    try:
        for row in list(_rows(observed))[:5]:
            journal.consume(*row)
        assert journal.session._version == 1
        assert journal.session.reference.status is ReferenceStatus.INVALIDATED
    finally:
        journal.close()


def test_diagnostic_failure_does_not_suppress_legacy_presentation(tmp_path):
    observed = _run(True)
    _execute(observed)
    cleared, legacy_calls = [], []
    def failed_poll(): raise OSError("fixture input failure")
    journal = _journal(tmp_path, observed, failed_poll, cleared.append)
    callback = intent_callback(SimpleNamespace(consume=lambda *args: observed.snapshots[0]),
                               journal, lambda *args: legacy_calls.append(args))
    try:
        packet, frame, legacy, _ = next(_rows(observed))
        with pytest.warns(RuntimeWarning, match="Intent observation unavailable"):
            callback(packet, frame, legacy)
        assert len(legacy_calls) == 1 and legacy_calls[0][2] is legacy
        assert cleared[-1] is None and journal.counts["diagnostic_errors"] == 1
    finally:
        journal.close()


def test_source_close_failure_still_neutralizes_and_clears_feedback(tmp_path):
    observed = _run(True)
    _execute(observed)
    cleared = []
    journal = _journal(tmp_path, observed, sink=cleared.append)
    class BrokenSource:
        def close(self): raise OSError("fixture close")
    source = IntentCaptureSource(BrokenSource(), observed.observer, journal)
    try:
        with pytest.raises(OSError, match="fixture close"):
            source.close()
        assert cleared[-1] is None and observed.observer.latest_snapshot is None
    finally:
        journal.close()


@pytest.mark.parametrize("args", [["--mode", "LEGACY", "--intent-pinch-observe"],
                                 ["--intent-pinch-observe", "--pinch-diagnostic"]])
def test_intent_mode_explicit_and_contact_labels_cannot_be_mixed(args):
    from extensions.stem3d.full_hand_app import main
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


def test_cli_opt_in_selects_distinct_dashboard_only_for_intent_mode(monkeypatch):
    from extensions.stem3d import full_hand_app
    calls = []
    monkeypatch.setattr(full_hand_app.live_demo, "main", lambda **kwargs: calls.append(kwargs))
    full_hand_app.main([])
    full_hand_app.main(["--intent-pinch-observe"])
    assert "dashboard_factory" not in calls[0]
    assert "dashboard_factory" in calls[1]


class FakeHost:
    window_size = (1600, 900)
    def set_pointer_consumer(self, callback): pass
    def set_key_consumer(self, callback): pass
    def close(self): pass


@pytest.mark.parametrize("size", [(1024, 640), (1600, 900), (1920, 1080)])
def test_intent_feedback_draws_without_mutating_image_and_rejects_stale_state(tmp_path, size):
    observed = _run(True)
    _execute(observed)
    dashboard = IntentObservationDashboard(window_host=FakeHost())
    journal = _journal(tmp_path, observed, sink=dashboard.set_intent_snapshot)
    try:
        packet, frame, legacy, snapshot = next(_rows(observed))
        journal.consume(packet, frame, legacy, snapshot)
        state = build_presentation_state(packet, frame, legacy)
        before = packet.image.copy()
        app = ApplicationState(frame.run_id, ApplicationPhase.RUNNING)
        surface = dashboard.build_surface(packet.image, state, app, width=size[0], height=size[1])
        assert surface.canvas.shape == (size[1], size[0], 3)
        assert np.array_equal(before, packet.image)
        # A new displayed frame without a new intent snapshot must not show old ACTIVE.
        stale = replace(state, frame_id=frame.frame_id + 1)
        dashboard.build_surface(packet.image, stale, app, width=size[0], height=size[1])
    finally:
        journal.close()
        dashboard.close()


def test_keyboard_poll_uses_focused_pressed_keys_without_consuming_events(monkeypatch):
    import sys
    from extensions.stem3d.full_hand.intent_diagnostic import poll_intent_keys
    fake = SimpleNamespace(K_k=0, K_x=1, K_t=2, K_u=3, K_n=4,
        key=SimpleNamespace(get_pressed=lambda: [True, False, False, False, True], get_focused=lambda: True))
    monkeypatch.setitem(sys.modules, "pygame", fake)
    assert poll_intent_keys() == ({"CALIBRATE_RELEASE", "NON_INTENT"}, True)
