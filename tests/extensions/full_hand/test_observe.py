"""Deterministic OBSERVE/LEGACY parity through the unchanged Core runtime."""

from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from dip_touchless.configuration import resolve_config
from dip_touchless.core import (
    ColorSpace, FramePacket, Landmark, LandmarkObservation, MeasurementQuality,
    CoordinateSpace, TrackingStatus,
)
from dip_touchless.filtering import RawLandmarkFilter
from dip_touchless.runtime import RealtimeRuntime
from dip_touchless.tracking import MeasurementValidator
from extensions.stem3d.live_demo import _build_gesture_engine, DEFAULT_CONFIG
from extensions.stem3d.full_hand.observe import (
    FullHandObserver, GeometryCaptureSource, SnapshotJournal, load_observe_profile,
)
from extensions.stem3d.full_hand import HandPose, TemporalReason
from extensions.stem3d.ui import (
    InteractionRouter, build_spatial_panel_layout,
)
from extensions.stem3d.scene_state import Stem3DSceneState


PROFILE = Path(__file__).resolve().parents[3] / "config/extensions/full_hand_observe.yaml"


class Source:
    def __init__(self, fail=None):
        self.packets = [FramePacket("parity", i, i * .125,
                                   np.zeros((90, 160, 3), dtype=np.uint8),
                                   ColorSpace.BGR, "synthetic") for i in range(16)]
        self.index = 0
        self.opens = self.closes = 0
        self.fail = fail

    def open(self):
        self.index = 0
        self.opens += 1
        if self.fail == "open":
            raise RuntimeError("camera open fixture")

    def read(self):
        if self.fail == "read":
            raise RuntimeError("camera read fixture")
        if self.index == len(self.packets):
            return None
        packet = self.packets[self.index]
        self.index += 1
        return packet

    def close(self):
        self.closes += 1


class Provider:
    def __init__(self, pointer=(.5, .5), fail=False):
        self.closes = self.calls = 0
        self.pointer = pointer
        self.fail = fail

    def process(self, packet):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider fixture")
        i = packet.frame_id
        status = TrackingStatus.NO_HAND if i == 10 else TrackingStatus.REACQUIRED if i == 11 else TrackingStatus.VALID
        points = [(.50, .80), (.40, .68), (.32, .61), (.25, .53), (.20, .48),
                  (.40, .55), (.40, .42), (.40, .31), (.40, .20),
                  (.50, .50), (.50, .35), (.50, .23), (.50, .11),
                  (.60, .54), (.61, .40), (.62, .29), (.63, .19),
                  (.68, .61), (.71, .50), (.73, .41), (.75, .33)]
        normalized = [( .5 + (x - .5) / (160 / 90), y) for x, y in points]
        offset = (self.pointer[0] - normalized[8][0], self.pointer[1] - normalized[8][1])
        normalized = [(x + offset[0] + (i * .01 if self.pointer == (.5, .5) else 0),
                       y + offset[1]) for x, y in normalized]
        if i in (5, 6, 7, 11, 12):
            a, b = normalized[5], normalized[17]
            scale = np.hypot(a[0] - b[0], a[1] - b[1])
            normalized[4] = (normalized[8][0] - .1 * scale, normalized[8][1])
        landmarks = tuple(Landmark(j, x, y, -.01 * j, CoordinateSpace.FRAME_NORMALIZED)
                          for j, (x, y) in enumerate(normalized)) if status is not TrackingStatus.NO_HAND else ()
        return LandmarkObservation(i, packet.timestamp_s, status, landmarks, None, None,
                                   MeasurementQuality.unavailable(), None, "fixture")

    def close(self):
        self.closes += 1


class Logger:
    def __init__(self, fail=False):
        self.tracking = []
        self.interactions = []
        self.closes = 0
        self.fail = fail

    def start_run(self, metadata, config):
        if self.fail:
            raise RuntimeError("logger fixture")

    def log_tracking_frame(self, frame):
        self.tracking.append(frame)

    def log_interaction_state(self, interaction):
        self.interactions.append(interaction)

    def close(self):
        self.closes += 1


def _run(observe=True, *, pointer=(.5, .5), interaction_consumer=None,
         source_fail=None, provider_fail=False, logger_fail=False, sink=None):
    source, provider, logger = Source(source_fail), Provider(pointer, provider_fail), Logger(logger_fail)
    observer = FullHandObserver(load_observe_profile(PROFILE), sink)
    snapshots, presented, received = [], [], []
    if sink is None:
        observer.sink = snapshots.append
    def presentation(packet, tracking, interaction):
        presented.append((packet, tracking, interaction))
        packet.image[:] = 123  # Core-owned original source pixels stay unchanged.
    def interaction(state):
        received.append(state)
        if interaction_consumer:
            interaction_consumer(state)
    cfg = resolve_config(DEFAULT_CONFIG).to_dict()
    clock = iter(n * .001 for n in range(1000)).__next__
    runtime = RealtimeRuntime(
        source=GeometryCaptureSource(source, observer) if observe else source,
        provider=provider, validator=MeasurementValidator(), landmark_filter=RawLandmarkFilter(),
        logger=logger, gesture_engine=_build_gesture_engine(cfg["gesture"]),
        interaction_consumer=interaction,
        presentation_consumer=observer.presentation_callback(presentation) if observe else presentation,
        clock=clock,
    )
    return SimpleNamespace(runtime=runtime, source=source, provider=provider, logger=logger,
                           observer=observer, snapshots=snapshots, presented=presented,
                           received=received, cfg=cfg)


def _execute(run):
    return run.runtime.run(metadata={}, resolved_config=run.cfg)


def test_observe_equals_legacy_field_for_field_with_same_core_logs():
    legacy, observed = _run(False), _run(True)
    assert _execute(legacy) == _execute(observed) == 16
    assert [asdict(s) for s in legacy.received] == [asdict(s) for s in observed.received]
    assert legacy.logger.tracking == observed.logger.tracking
    assert legacy.logger.interactions == observed.logger.interactions
    assert len(observed.snapshots) == len(observed.received) == observed.provider.calls
    assert any(s.rotation_delta != (0., 0.) for s in observed.received)
    assert any(s.pinch_active for s in observed.received)
    for i, (packet, tracking, interaction) in enumerate(observed.presented):
        assert interaction is observed.received[i] is observed.logger.interactions[i]
        snapshot = observed.snapshots[i]
        assert (snapshot.run_id, snapshot.frame_id, snapshot.timestamp_s) == (packet.run_id, packet.frame_id, packet.timestamp_s)
        assert (snapshot.frame_geometry.width, snapshot.frame_geometry.height) == (160, 90)
        assert snapshot.pose.frame_geometry == snapshot.frame_geometry
        assert snapshot.temporal.frame_id == packet.frame_id
    assert all(np.count_nonzero(p.image) == 0 for p in observed.source.packets)
    assert observed.source.closes == observed.provider.closes == observed.logger.closes == 1
    assert observed.observer.latest_snapshot is None  # No stale state after shutdown.


def test_scene_receives_each_legacy_command_once_and_unchanged():
    scenes = [Stem3DSceneState(initial_scale=1., min_scale=.5, max_scale=2.) for _ in range(2)]
    counts = [0, 0]
    def consumer(index):
        def consume(state):
            counts[index] += 1
            scenes[index].consume(state)
        return consume
    for i in range(2):
        _execute(_run(bool(i), interaction_consumer=consumer(i)))
    assert counts == [16, 16]
    assert scenes[0].transform == scenes[1].transform


def test_router_clicks_are_not_duplicated_by_observation():
    layout = build_spatial_panel_layout(1600, 900)
    button = next(b for b in layout.buttons if b.enabled)
    pointer = ((button.rect.x + button.rect.width // 2 - layout.viewport.x) / (layout.viewport.width - 1),
               (button.rect.y + button.rect.height // 2 - layout.viewport.y) / (layout.viewport.height - 1))
    outcomes = []
    for observe in (False, True):
        router = InteractionRouter()
        router.open_panel()
        routes = []
        run = _run(observe, pointer=pointer, interaction_consumer=lambda state: routes.append(router.route(state, layout)))
        _execute(run)
        outcomes.append(routes)
    assert outcomes[0] == outcomes[1]
    assert len(outcomes[0]) == 16
    assert sum(r.action is not None for r in outcomes[0]) == 1


def test_snapshot_loss_and_reacquisition_are_neutral():
    run = _run()
    _execute(run)
    assert run.snapshots[10].analysis_valid is False
    assert run.snapshots[10].pose.pose is HandPose.UNKNOWN
    assert TemporalReason.TRACKING_LOSS in run.snapshots[10].temporal.reasons
    assert TemporalReason.REACQUISITION in run.snapshots[11].temporal.reasons
    assert not run.snapshots[11].temporal.action_allowed
    assert len(run.snapshots[1].pose.fingers) == 5
    assert run.snapshots[1].pose.fingers[0].predicates


def test_source_capture_is_passthrough_and_restart_clears_state():
    source = Source()
    observer = FullHandObserver(load_observe_profile(PROFILE))
    wrapped = GeometryCaptureSource(source, observer)
    wrapped.open()
    packet = wrapped.read()
    assert packet is source.packets[0]
    assert observer.frame_geometry.width == 160
    wrapped.close()
    assert observer.frame_geometry is None
    wrapped.open()
    assert observer.latest_snapshot is None and wrapped.read() is packet
    wrapped.close()
    assert source.opens == source.closes == 2


@pytest.mark.parametrize("mismatch", ["capture", "packet", "legacy", "dimensions", "missing"])
def test_alignment_defects_invalidate_observer_without_altering_legacy(mismatch):
    run = _run()
    _execute(run)
    packet, tracking, interaction = run.presented[0]
    observer = run.observer
    observer.capture(packet)
    if mismatch == "capture":
        observer.frame_geometry = replace(observer.frame_geometry, frame_id=99)
    elif mismatch == "packet":
        packet = replace(packet, timestamp_s=123.)
    elif mismatch == "legacy":
        interaction = replace(interaction, frame_id=99)
    elif mismatch == "dimensions":
        packet = replace(packet, image=np.zeros((10, 10, 3), np.uint8))
    else:
        observer.frame_geometry = None
    before = asdict(interaction)
    result = observer.consume(packet, tracking, interaction)
    assert not result.analysis_valid and result.errors
    assert not result.temporal.action_allowed
    assert asdict(interaction) == before


def test_duplicate_diagnostic_delivery_is_idempotent():
    run = _run()
    _execute(run)
    packet, tracking, interaction = run.presented[0]
    run.observer.capture(packet)
    a = run.observer.consume(packet, tracking, interaction)
    count = len(run.snapshots)
    b = run.observer.consume(packet, tracking, interaction)
    assert a is b and len(run.snapshots) == count


def test_duplicate_identity_cannot_hide_changed_loss_or_bad_alignment():
    run = _run()
    _execute(run)
    packet, tracking, interaction = run.presented[1]
    observer = run.observer
    observer.capture(packet)
    assert observer.consume(packet, tracking, interaction).analysis_valid
    lost = replace(tracking, status=TrackingStatus.NO_HAND,
                   raw_landmarks=(), filtered_landmarks=())
    result = observer.consume(packet, lost, interaction)
    assert not result.analysis_valid and not result.temporal.action_allowed
    bad_packet = replace(packet, image=np.zeros((1, 1, 3), np.uint8))
    result = observer.consume(bad_packet, lost, interaction)
    assert result.errors and not result.temporal.action_allowed


@pytest.mark.parametrize("failure", ["open", "read", "provider", "logger", "presentation"])
def test_runtime_cleanup_on_failure(failure):
    run = _run(source_fail=failure if failure in ("open", "read") else None,
               provider_fail=failure == "provider", logger_fail=failure == "logger")
    if failure == "presentation":
        def fail(*args):
            raise RuntimeError("presentation fixture")
        run.runtime._presentation_consumer = run.observer.presentation_callback(fail)
    with pytest.raises(RuntimeError):
        _execute(run)
    assert run.source.closes == run.provider.closes == run.logger.closes == 1
    assert run.observer.latest_snapshot is None


def test_sink_failure_does_not_change_or_stop_legacy():
    def fail(snapshot):
        raise OSError("sidecar fixture")
    run = _run(sink=fail)
    legacy = _run(False)
    with pytest.warns(RuntimeWarning, match="sink failed"):
        assert _execute(run) == 16
    _execute(legacy)
    assert run.received == legacy.received


def test_jsonl_is_separate_and_records_profile_and_snapshot(tmp_path):
    profile = load_observe_profile(PROFILE)
    journal = SnapshotJournal(tmp_path / "observe", profile, {"run_id": "parity"})
    run = _run(sink=journal.consume)
    _execute(run)
    journal.close()
    import json
    manifest = json.loads((journal.directory / "manifest.json").read_text())
    snapshots = [json.loads(line) for line in (journal.directory / "snapshots.jsonl").read_text().splitlines()]
    assert len(snapshots) == 16 and snapshots[0]["mode"] == "OBSERVE_FULL_HAND"
    assert manifest["profile"] == asdict(profile)
    assert len(manifest["profile_sha256"]) == 64
    assert not manifest["webcam_images_stored"]
    assert sorted(p.name for p in journal.directory.iterdir()) == ["manifest.json", "snapshots.jsonl"]
    assert journal._file.closed


def test_entrypoint_legacy_mode_never_builds_observer(monkeypatch):
    from extensions.stem3d import full_hand_app
    calls = []
    monkeypatch.setattr(full_hand_app.live_demo, "main", lambda: calls.append("legacy"))
    full_hand_app.main(["--mode", "LEGACY", "--profile", "does-not-exist.yaml"])
    assert calls == ["legacy"]


def test_filter_reset_and_run_change_are_observer_only():
    run = _run()
    _execute(run)
    packet, tracking, interaction = run.presented[0]
    observer = run.observer
    observer.capture(packet)
    first = observer.consume(packet, tracking, interaction)
    packet2, tracking2, interaction2 = run.presented[1]
    observer.capture(packet2)
    before = asdict(interaction2)
    tracking2 = replace(tracking2, filter_diagnostics=replace(tracking2.filter_diagnostics,
                                                             reset_occurred=True))
    reset = observer.consume(packet2, tracking2, interaction2)
    assert TemporalReason.FILTER_RESET in reset.temporal.reasons
    assert not reset.temporal.action_allowed and asdict(interaction2) == before
    new_packet = replace(packet, run_id="second")
    new_tracking = replace(tracking, run_id="second")
    new_interaction = replace(interaction, run_id="second")
    observer.capture(new_packet)
    changed = observer.consume(new_packet, new_tracking, new_interaction)
    assert TemporalReason.RUN_CHANGE in changed.temporal.reasons
    assert changed.temporal.reset_id > first.temporal.reset_id


def test_entrypoint_observe_factory_wires_hooks_and_closes_journal(monkeypatch, tmp_path):
    from extensions.stem3d import full_hand_app
    built = []
    journals = []
    original_journal = full_hand_app.SnapshotJournal
    def journal(*args):
        result = original_journal(*args)
        journals.append(result)
        return result
    monkeypatch.setattr(full_hand_app, "SnapshotJournal", journal)
    presented = []
    controller = SimpleNamespace(consume_presentation=lambda *args: presented.append(args))
    def runtime(**kwargs):
        built.append(kwargs)
        assert kwargs["source_adapter"](Source()).observer is not None
        return "runtime"
    monkeypatch.setattr(full_hand_app.live_demo, "_build_runtime", runtime)
    def main(*, runtime_builder):
        assert runtime_builder(cfg={}, run_id="factory", controller=controller,
                               metadata={"run_id": "factory"}) == "runtime"
    monkeypatch.setattr(full_hand_app.live_demo, "main", main)
    full_hand_app.main(["--output-dir", str(tmp_path)])
    assert len(built) == len(journals) == 1
    assert journals[0]._file.closed
    assert callable(built[0]["presentation_consumer"])


def test_entrypoint_build_failure_closes_sidecar(monkeypatch, tmp_path):
    from extensions.stem3d import full_hand_app
    journals = []
    original = full_hand_app.SnapshotJournal
    def journal(*args):
        result = original(*args)
        journals.append(result)
        return result
    monkeypatch.setattr(full_hand_app, "SnapshotJournal", journal)
    def fail(**kwargs):
        raise RuntimeError("partial runtime fixture")
    monkeypatch.setattr(full_hand_app.live_demo, "_build_runtime", fail)
    def main(*, runtime_builder):
        runtime_builder(cfg={}, run_id="failure", metadata={},
                        controller=SimpleNamespace(consume_presentation=lambda *args: None))
    monkeypatch.setattr(full_hand_app.live_demo, "main", main)
    with pytest.raises(RuntimeError, match="partial runtime"):
        full_hand_app.main(["--output-dir", str(tmp_path)])
    assert journals[0]._file.closed


def test_sink_failure_remains_non_authoritative_with_warnings_as_errors():
    import warnings
    def fail(snapshot):
        raise OSError("sidecar warning fixture")
    run = _run(sink=fail)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        assert _execute(run) == 16


def test_snapshot_is_immutable_and_observation_exceptions_keep_presentation(monkeypatch):
    from dataclasses import FrozenInstanceError
    import extensions.stem3d.full_hand.observe as module
    run = _run()
    def fail(*args):
        raise RuntimeError("analysis fixture")
    monkeypatch.setattr(module, "extract_hand_geometry", fail)
    assert _execute(run) == 16
    assert len(run.received) == len(run.presented) == 16
    assert all(s.errors and not s.temporal.action_allowed for s in run.snapshots)
    with pytest.raises(FrozenInstanceError):
        run.snapshots[0].analysis_valid = True


def test_profile_rejects_missing_and_unknown_sections(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("pose: {}\ntemporal: {}\ncommands: true\n")
    with pytest.raises(ValueError):
        load_observe_profile(path)


def test_empty_or_invalid_source_image_geometry_fails_safe():
    run = _run()
    _execute(run)
    packet, tracking, interaction = run.presented[0]
    malformed = replace(packet, image=np.zeros((5,), np.uint8))
    run.observer.capture(malformed)
    snapshot = run.observer.consume(malformed, tracking, interaction)
    assert snapshot.frame_geometry is None and snapshot.errors
    assert not snapshot.analysis_valid and not snapshot.temporal.action_allowed
