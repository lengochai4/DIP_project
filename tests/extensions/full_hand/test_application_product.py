from dataclasses import replace, asdict
from pathlib import Path
from types import SimpleNamespace as NS
import runpy
import json
import numpy as np
import pytest
from extensions.stem3d.product.settings import UserSettings, InputMode, load_application_profile
from extensions.stem3d.product.dashboard import ApplicationDashboard
from extensions.stem3d.product.composition import ApplicationComposition, ApplicationSource, RuntimeControllerProxy
from extensions.stem3d.full_hand.intent_session import load_intent_profile
from extensions.stem3d.full_hand.observe import load_observe_profile
from extensions.stem3d.ui import ApplicationState, ApplicationPhase, DashboardMode, build_presentation_state
from extensions.stem3d.live_demo import _build_gesture_engine
from test_observe import _run, _execute


class Host:
    opened = False
    window_size = (1600, 900)
    def set_pointer_consumer(self, callback): self.pointer_consumer = callback
    def set_key_consumer(self, callback): self.key_consumer = callback
    def close(self): self.opened = False


def dashboard(tmp_path, preferences=UserSettings()):
    d = ApplicationDashboard(preferences=preferences, preferences_path=tmp_path/"preferences.json", window_host=Host())
    d._last_application_state = ApplicationState("parity", ApplicationPhase.RUNNING)
    return d


def composition(tmp_path, observed, d=None, controller=None, focus=lambda: True):
    d = d or dashboard(tmp_path)
    received, presented = [], []
    controller = controller or NS(state=ApplicationState("parity", ApplicationPhase.RUNNING),
        consume_interaction=received.append, consume_presentation=lambda *args: presented.append(args))
    motion, gains, two = load_application_profile(Path("config/extensions/application.yaml"))
    c = ApplicationComposition(controller=controller, dashboard=d,
        observe_profile=load_observe_profile(Path("config/extensions/full_hand_observe.yaml")),
        intent_profile=load_intent_profile(Path("config/extensions/intent_pinch_observe.yaml")),
        motion_profile=motion, sensitivity=gains, directory=tmp_path/"run", metadata={},
        legacy_engine=_build_gesture_engine(observed.cfg["gesture"]), poll_focus=focus)
    return c, d, received, presented


@pytest.mark.parametrize("mode", [InputMode.LEGACY, InputMode.OBSERVE])
def test_app_observation_parity_single_delivery_cleanup_and_restart(tmp_path, mode):
    observed = _run(True)
    _execute(observed)
    c, d, received, presented = composition(tmp_path, observed, dashboard(tmp_path, UserSettings(mode)))
    for packet, frame, legacy in zip(observed.source.packets, observed.logger.tracking, observed.received):
        c.observer.capture(packet)
        c.consume(packet, frame, legacy)
        c.consume(packet, frame, legacy)
    assert [asdict(v) for v in received] == [asdict(v) for v in observed.received]
    assert len(presented) == 16 and c.intent_journal.counts["legacy_parity_mismatches"] == 0
    c.close()
    c.close()
    assert c.counts["closed"] and d.full_snapshot is None and d._intent_snapshot is None
    assert json.loads((c.directory/"summary.json").read_text())["frames"] == 16
    with pytest.raises(RuntimeError, match="closed"):
        c.consume(packet, frame, legacy)
    fresh, *_ = composition(tmp_path/"restart", observed)
    assert fresh.session.reference is None
    fresh.close()


def test_runtime_proxy_never_delivers_an_extra_legacy_command():
    outputs = []
    proxy = RuntimeControllerProxy(NS(consume_interaction=outputs.append, state="state"))
    proxy.consume_interaction("legacy")
    assert not outputs and proxy.state == "state"


@pytest.mark.parametrize("blocked", ["modal", "evidence", "unfocused"])
def test_modal_evidence_focus_cannot_manipulate_scene(tmp_path, blocked):
    observed = _run(True)
    _execute(observed)
    c, d, received, _ = composition(tmp_path, observed, focus=lambda: blocked != "unfocused")
    d.settings_open = blocked == "modal"
    if blocked == "evidence": d._set_mode_state(DashboardMode.EVIDENCE)
    for packet, frame, legacy in zip(observed.source.packets, observed.logger.tracking, observed.received):
        c.observer.capture(packet)
        c.consume(packet, frame, legacy)
    assert all(not s.pinch_active and s.rotation_delta == (0., 0.) and s.scale_delta == 0 for s in received)
    c.close()


def test_manual_input_works_without_tracking_and_replaces_touchless_command(tmp_path):
    observed = _run(True)
    _execute(observed)
    c, d, received, _ = composition(tmp_path, observed)
    index = 10
    packet, frame, legacy = observed.source.packets[index], observed.logger.tracking[index], observed.received[index]
    d.handle_key(ord("l"))
    c.observer.capture(packet)
    c.consume(packet, frame, legacy)
    assert received[-1].rotation_delta[0] > 0 and not received[-1].pinch_active
    assert c.counts["manual_frames"] == 1
    c.close()


def test_diagnostic_failure_fails_safe_and_preserves_explicit_fallback(tmp_path):
    observed = _run(True)
    _execute(observed)
    c, d, received, _ = composition(tmp_path, observed, dashboard(tmp_path, UserSettings(InputMode.FULL_HAND)))
    c.observer.consume = lambda *args: (_ for _ in ()).throw(ValueError("fixture failure"))
    for i in range(2):
        if i == 1: d.preferences = UserSettings(InputMode.LEGACY)
        packet, frame, legacy = observed.source.packets[i], observed.logger.tracking[i], observed.received[i]
        c.consume(packet, frame, legacy)
    assert not received[0].interaction_valid and received[1] is observed.received[1]
    assert c.counts["observation_errors"] == 2 and c.session.reference is None
    c.close()


def test_explicit_calibration_and_settings_save(tmp_path):
    d = dashboard(tmp_path)
    assert d.drain_events() == ()
    d.handle_key(ord("k"))
    assert d.drain_events() == ("CALIBRATE_RELEASE",)
    d.handle_key(ord("x"))
    assert d.drain_events() == ("RESET_REFERENCE",)
    d._activate("input:FULL_HAND")
    d._activate("sensitivity:responsive")
    d._activate("save-preferences")
    assert d.preferences_path.is_file() and "reference" not in d.preferences_path.read_text()


@pytest.mark.parametrize("size", [(1024,640), (1280,720), (1600,900), (1920,1080)])
@pytest.mark.parametrize("mode", list(DashboardMode))
@pytest.mark.parametrize("mirror", [False, True])
def test_app_surface_settings_help_mirror_are_bounded_and_do_not_mutate_inputs(tmp_path, size, mode, mirror):
    helpers = runpy.run_path("tests/extensions/test_live_demo_presentation.py")
    packet, frame, interaction = helpers["_packet"](), helpers["_tracking_frame"](), helpers["_interaction"]()
    state = build_presentation_state(packet, frame, interaction)
    original = packet.image.copy(), repr(state)
    d = dashboard(tmp_path, UserSettings(mirror=mirror))
    d._host.window_size = size
    d._set_mode_state(mode)
    d.settings_open = True
    surface = d.build_surface(packet.image, state, ApplicationState(state.run_id, ApplicationPhase.RUNNING))
    assert surface.canvas.shape == (size[1], size[0], 3)
    assert len(d._targets) >= 10
    for rect in d._targets.values():
        assert 0 <= rect.x < rect.right <= size[0] and 0 <= rect.y < rect.bottom <= size[1]
    assert np.array_equal(packet.image, original[0]) and repr(state) == original[1]
    d.settings_open = False
    d._help_open = True
    assert d.build_surface(packet.image, state, ApplicationState(state.run_id, ApplicationPhase.RUNNING)).overlays
    d.close()


def test_scene_keys_do_not_leak_through_settings_modal(tmp_path):
    d = dashboard(tmp_path)
    selected = []
    d.set_scene_select_action(selected.append)
    d.settings_open = True
    d.handle_key(ord("2"))
    assert selected == []
    d.handle_key(ord("q"))
    assert d._stop


def test_mouse_drag_wheel_only_apply_inside_scene_and_not_modal(tmp_path):
    helpers = runpy.run_path("tests/extensions/test_live_demo_presentation.py")
    packet = helpers["_packet"]()
    state = build_presentation_state(packet, helpers["_tracking_frame"](), helpers["_interaction"]())
    d = dashboard(tmp_path)
    surface = d.build_surface(packet.image, state, ApplicationState(state.run_id, ApplicationPhase.RUNNING))
    rect = surface.viewport
    d.handle_navigation("drag", rect.x+20, rect.y+20, .03, .04)
    assert d.drain_manual() == (("drag", .03, .04),)
    d.settings_open = True
    d.handle_navigation("wheel", rect.x+20, rect.y+20, 0., 1.)
    assert not d.drain_manual()


def test_cached_background_is_bounded_immutable_and_surfaces_are_independent(tmp_path):
    d = dashboard(tmp_path)
    a = d._new_canvas(900,1600)
    template = d._background_template
    b = d._new_canvas(900,1600)
    assert d._background_template is template and not template.flags.writeable
    assert not np.shares_memory(a,b) and not np.shares_memory(a,template)
    a[:] = 0
    assert b.any() and template.any()
    d._new_canvas(640,1024)
    assert d._background_template.shape == (640,1024,3)
    d.close()
    assert d._background_template is None


def test_cleanup_error_does_not_skip_remaining_resources(tmp_path):
    observed = _run(True)
    c, d, *_ = composition(tmp_path, observed)
    c.two_hand_provider = NS(close=lambda: (_ for _ in ()).throw(RuntimeError("close fixture")))
    with pytest.raises(RuntimeError, match="close fixture"):
        c.close()
    assert c._output.closed and c.intent_journal._file.closed
    assert json.loads((c.directory/"summary.json").read_text())["cleanup_errors"] == 1


def test_focus_loss_during_analysis_cannot_deliver_a_scene_command(tmp_path):
    observed = _run(True)
    _execute(observed)
    focus_samples = iter((True, False))
    c, d, received, _ = composition(tmp_path, observed, focus=lambda: next(focus_samples))
    packet, frame, legacy = observed.source.packets[1], observed.logger.tracking[1], observed.received[1]
    c.observer.capture(packet)
    c.consume(packet, frame, legacy)
    assert not received[-1].interaction_valid and received[-1].rotation_delta == (0.,0.)
    c.close()


@pytest.mark.parametrize("fault", [None, "source-open", "source-read", "provider", "logger"])
def test_real_runtime_app_composition_closes_camera_model_logs(tmp_path, fault):
    from dip_touchless.runtime import RealtimeRuntime
    from dip_touchless.filtering import RawLandmarkFilter
    from dip_touchless.tracking import MeasurementValidator
    observed = _run(True, source_fail="open" if fault == "source-open" else "read" if fault == "source-read" else None,
                    provider_fail=fault == "provider", logger_fail=fault == "logger")
    c, d, received, _ = composition(tmp_path, observed)
    runtime = RealtimeRuntime(source=ApplicationSource(observed.source, c), provider=observed.provider,
        validator=MeasurementValidator(), landmark_filter=RawLandmarkFilter(), logger=observed.logger,
        gesture_engine=_build_gesture_engine(observed.cfg["gesture"]),
        interaction_consumer=RuntimeControllerProxy(c.controller).consume_interaction,
        presentation_consumer=c.consume, clock=iter(i*.001 for i in range(1000)).__next__)
    try:
        if fault:
            with pytest.raises(RuntimeError): runtime.run(metadata={}, resolved_config=observed.cfg)
        else:
            assert runtime.run(metadata={}, resolved_config=observed.cfg) == 16
            assert received == observed.logger.interactions
    finally:
        c.close()
    assert observed.source.closes == observed.provider.closes == observed.logger.closes == 1
    assert c.session.reference is None or not c.session.reference.valid


def test_actual_landmarks_relative_lifecycle_repeated_scale_no_legacy_change(tmp_path):
    from developer_tools.application_qa import synthetic
    observed = _run(True)
    c, d, received, _ = composition(tmp_path, observed, dashboard(tmp_path, UserSettings(InputMode.FULL_HAND)))
    # Actual 21-landmark coordinates flow through A2/A3/A4, release builder and
    # intention tracker. No fabricated geometry/state and no threshold patching.
    d.events.append("CALIBRATE_RELEASE")
    engine = _build_gesture_engine(observed.cfg["gesture"])
    entered = 0
    had_pinch = False
    for i in range(64 + 5*24):
        packet, frame = synthetic(i)
        packet = replace(packet, run_id="parity")
        frame = replace(frame, run_id="parity")
        part = (i-64)%24 if i >= 64 else None
        if part is not None and part < 12:
            landmarks = frame.filtered_landmarks
            thumb, index = landmarks[4], landmarks[8]
            dy = -.003*part
            adjusted = tuple(replace(p,
                x=index.x+.2*(thumb.x-index.x) if p.index == 4 else p.x,
                y=(index.y+.2*(thumb.y-index.y) if p.index == 4 else p.y)+dy)
                for p in landmarks)
            frame = replace(frame, raw_landmarks=adjusted, filtered_landmarks=adjusted)
        legacy = engine.update(frame)
        c.observer.capture(packet)
        c.consume(packet, frame, legacy)
        selected = received[-1]
        if selected.pinch_active and not had_pinch: entered += 1
        had_pinch = selected.pinch_active
        assert not (selected.rotation_delta != (0.,0.) and selected.scale_delta != 0)
    assert entered == 5
    assert any(v.pinch_active and v.scale_delta > 0 for v in received)
    assert not received[-1].pinch_active
    assert c.intent_journal.counts["entries"] == 5
    assert c.intent_journal.counts["legacy_parity_mismatches"] == 0
    assert c.intent_journal.counts["safety_violations"] == 0
    c.close()
