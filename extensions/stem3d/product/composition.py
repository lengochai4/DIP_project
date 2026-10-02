"""Read-only Core outputs -> one selected application command -> existing router."""

from dataclasses import asdict, replace
import json
import hashlib
from pathlib import Path
from dip_touchless.core import InteractionState
from ..full_hand.intent_diagnostic import IntentDiagnosticJournal
from ..full_hand.intent_pinch_contracts import ReferenceScope
from ..full_hand.intent_session import IntentObservationSession
from ..full_hand.observe import FullHandObserver, GeometryCaptureSource
from .interaction import FullHandCommandMapper, neutral
from .settings import InputMode
from .simple_interaction import SimpleHandControls


class RuntimeControllerProxy:
    """Core still generates/logs legacy output. Presentation owns application delivery."""
    def __init__(self, controller):
        self.controller = controller

    def consume_interaction(self, interaction):
        pass

    def __getattr__(self, name):
        return getattr(self.controller, name)


class ApplicationComposition:
    def __init__(self, *, controller, dashboard, observe_profile, intent_profile,
                 motion_profile, sensitivity, directory, metadata, legacy_engine, poll_focus=None):
        self.controller, self.dashboard = controller, dashboard
        self.observer = FullHandObserver(observe_profile)
        scope = ReferenceScope(controller.state.run_id, controller.state.run_id,
            str(metadata.get("camera", {}).get("index", "configured-camera")),
            "configured-mediapipe", intent_profile.sha256, "full-frame-aspect-corrected-xy", "intent-epoch-0")
        self.session = IntentObservationSession(intent_profile, scope)
        self.mapper = FullHandCommandMapper(motion_profile)
        self.simple = SimpleHandControls(motion_profile)
        self.sensitivity = sensitivity
        self.directory = directory
        self._closed = False
        self._last_identity = None
        self._snapshot = None
        self._fault = False
        self.two_hand_provider = None
        self.two_hand_association = None
        self.two_hand_snapshot = None
        self._focus = poll_focus or self._poll_focus
        self._polled_focus = True
        self._event_pulse = False
        self._queued_events = ()
        self.intent_journal = IntentDiagnosticJournal(directory / "intent", self.session, metadata,
            legacy_engine, poll=self._poll_events, presentation_sink=self._set_snapshot,
            command_description="observation evidence only; selected app commands are in ../application.jsonl")
        self.counts = dict(frames=0, commands=0, observation_errors=0, manual_frames=0,
                           invalid_commands=0, closed=False)
        self._output = None
        try:
            self._output = (directory / "application.jsonl").open("x", encoding="utf-8")
            manifest = dict(schema="stem-application-v1.1", validation="PHYSICAL PENDING",
                legacy_metadata=metadata, intent_profile=asdict(intent_profile),
                observe_profile=asdict(observe_profile),
                intent_profile_sha256=intent_profile.sha256, motion_profile=asdict(motion_profile),
                sensitivity=sensitivity, image_storage=False,
                commands="single selected owner; SIMPLE finger-count navigation; optional FULL_HAND pinch experiment; legacy available",
                reference_persistence=False, frozen_evidence_modified=False)
            root = Path(__file__).resolve().parents[3]
            sources = [*Path(__file__).parent.glob("*.py"), root/"extensions/stem3d/app.py",
                root/"extensions/stem3d/live_demo.py", root/"extensions/stem3d/shell_renderer.py",
                root/"extensions/stem3d/ui/shell.py", root/"application_adapters/two_hand_provider.py"]
            manifest["source_sha256"] = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in sources}
            (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
        except Exception:
            self.close()
            raise

    @staticmethod
    def _poll_focus():
        import pygame
        return pygame.key.get_focused()

    def _poll_events(self):
        # Journal is edge-based. Queue pulses have an intervening empty poll so
        # repeated explicit confirmations cannot disappear as a held key.
        self._polled_focus = bool(self._focus())
        if self._event_pulse:
            self._event_pulse = False
            return set(), self._polled_focus
        events, self._queued_events = self._queued_events, ()
        self._event_pulse = bool(events)
        return set(events), self._polled_focus

    def _set_snapshot(self, snapshot):
        self._snapshot = snapshot
        self.dashboard.set_intent_snapshot(snapshot)

    def reset(self):
        self.session.reset()
        self.observer.reset()
        self.mapper.reset()
        self.simple.reset()
        self._set_snapshot(None)
        self.dashboard.full_snapshot = None
        self._last_identity = None
        self._queued_events = ()
        if self.two_hand_association is not None:
            self.two_hand_association.reset()
        self.two_hand_snapshot = None

    def enable_two_hand_capability(self, provider, association):
        self.two_hand_provider = provider
        self.two_hand_association = association
        path = self.directory/"manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["two_hand"] = dict(capability_enabled=True, profile=asdict(association.profile),
                                    separate_provider=True, filter="RAW", commands="experimental OPEN-pair scale only")
        path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")

    def consume(self, packet, frame, legacy):
        if self._closed:
            raise RuntimeError("application composition is closed")
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if identity == self._last_identity:
            return  # No duplicate application command, UI click or journal row.
        self._last_identity = identity
        self._queued_events += self.dashboard.drain_events()
        selected = neutral(frame)
        focus = "UI" if self.dashboard._spatial_panel_state.open else "SCENE"
        focused = self._focus()
        try:
            full = self.observer.consume(packet, frame, legacy)
            self.dashboard.full_snapshot = full
            self.intent_journal.consume(packet, frame, legacy, full)
            focused = focused and self._polled_focus
            context = (self.controller.state.active_scene, self.dashboard.mode,
                       self.dashboard.action_epoch, focused, self.dashboard.blocked)
            if self.dashboard.preferences.mode is InputMode.SIMPLE:
                selected = self.simple.update(frame, full, settings=self.dashboard.preferences,
                    sensitivity=self.sensitivity[self.dashboard.preferences.sensitivity],
                    focus=focus, context=context,
                    panel=self.dashboard.spatial_panel_layout() if focus == "UI" else None)
                self.dashboard.simple_feedback = self.simple.feedback
                diagnostics = self.simple.diagnostics
            else:
                self.simple.reset()
                self.dashboard.simple_feedback = None
                selected = self.mapper.update(frame, legacy, full, self._snapshot,
                settings=self.dashboard.preferences,
                sensitivity=self.sensitivity[self.dashboard.preferences.sensitivity],
                focus=focus, context=context)
                diagnostics = self.mapper.diagnostics
            self.dashboard.command_diagnostics = diagnostics
            if self.dashboard.preferences.mode is InputMode.SIMPLE and self.dashboard.mode.value == "EVIDENCE" and focus != "UI":
                # Evidence can open the navigation drawer, never transform a hidden scene.
                selected = neutral(frame)
            if self._fault or self.dashboard.blocked or not focused:
                selected = neutral(frame)
                self.mapper.reset()
                self.simple.reset()
            if (self.dashboard.preferences.mode is InputMode.FULL_HAND and self._snapshot is not None
                    and self._snapshot.calibration_status == "CAPTURING_RELEASE"):
                selected = neutral(frame)
                self.mapper.reset()
            pair_present = False
            if self.dashboard.preferences.two_hand and self.dashboard.preferences.mode in {InputMode.FULL_HAND, InputMode.SIMPLE}:
                if self.two_hand_provider is None:
                    self.dashboard.feedback = "Two-hand capability requires restart with --allow-two-hand. One-hand remains available."
                else:
                    hands = self.two_hand_provider.process(packet)
                    self.two_hand_association.practical = self.dashboard.preferences.mode is InputMode.SIMPLE
                    self.two_hand_snapshot = self.two_hand_association.update(full.frame_geometry, hands)
                    # Pair present/ambiguous: never mix a one-hand command with pair scale.
                    if len(hands) == 2:
                        pair_present = True
                        self.mapper.reset()
                        self.simple.reset()
                        selected = neutral(frame)
                        eligible = (focused and not self.dashboard.blocked and focus == "SCENE"
                            and self.dashboard.mode.value != "EVIDENCE"
                            and full.analysis_valid and frame.status.value == "VALID"
                            and (self.dashboard.preferences.mode is InputMode.SIMPLE or (
                                self.mapper.diagnostics.owner == "FULL_HAND" and self._snapshot is not None
                                and self._snapshot.reference is not None and self._snapshot.reference.valid))
                            and self.two_hand_snapshot.armed)
                        if eligible:
                            limit = self.two_hand_association.profile.scale_max_delta
                            delta = self.two_hand_snapshot.scale_delta*self.sensitivity[self.dashboard.preferences.sensitivity]
                            selected = InteractionState(*identity, True, None, None, False, (0., 0.),
                                                        max(-limit, min(limit, delta)))
                    self.dashboard.two_hand_feedback = f"Two hands: {self.two_hand_snapshot.status} / {self.two_hand_snapshot.reason}"
            elif self.two_hand_association is not None:
                self.two_hand_association.reset()
                self.two_hand_snapshot = None
            if (self.dashboard.preferences.mode is InputMode.SIMPLE and not pair_present
                    and self.simple.feedback.open_panel and focused and not self.dashboard.blocked):
                # UI focus changes before delivery; this frame is neutral.
                self.dashboard.handle_key(ord("p"))
                selected = neutral(frame)
            if self._fault and self.dashboard.preferences.mode in {InputMode.LEGACY, InputMode.OBSERVE}:
                self._fault = False  # Explicit fallback choice recovers diagnostic failure.
        except Exception as exc:
            self.counts["observation_errors"] += 1
            self.session.reset()
            self.mapper.reset()
            self.simple.reset()
            self._set_snapshot(None)
            self.dashboard.full_snapshot = None
            self.dashboard.feedback = f"Full-hand unavailable ({type(exc).__name__}). Select LEGACY or restart."
            self._fault = True
            if self.dashboard.preferences.mode in {InputMode.LEGACY, InputMode.OBSERVE} and focused and not self.dashboard.blocked:
                selected = legacy if legacy is not None else neutral(frame)
        manual = self.dashboard.drain_manual()
        if manual and focused and not self.dashboard.blocked and focus == "SCENE" and self.dashboard.mode.value != "EVIDENCE":
            self.mapper.reset()
            self.simple.reset()
            gain = self.sensitivity[self.dashboard.preferences.sensitivity]
            rotation = self.mapper.profile.manual_rotation * gain
            scale = self.mapper.profile.manual_scale * gain
            x = sum(rotation if c == "l" else -rotation if c == "j" else 0. for c in manual)
            y = sum(rotation if c == "o" else -rotation if c == "i" else 0. for c in manual)
            s = sum(scale if c in {"+", "="} else -scale if c == "-" else 0. for c in manual)
            for c in manual:
                if isinstance(c, tuple):
                    kind, dx, dy = c
                    if kind == "drag":
                        x += dx*self.mapper.profile.rotation_gain*gain
                        y += dy*self.mapper.profile.rotation_gain*gain
                    elif kind == "wheel":
                        s += dy*scale
            selected = InteractionState(*identity, True, None, None, False,
                (max(-rotation, min(rotation, x)), max(-rotation, min(rotation, y))), max(-scale, min(scale, s)))
            self.counts["manual_frames"] += 1
        command = selected.pinch_active or selected.scale_delta != 0 or selected.rotation_delta != (0., 0.)
        self.counts["frames"] += 1
        self.counts["commands"] += int(command)
        self.counts["invalid_commands"] += int(command and not selected.interaction_valid)
        self._output.write(json.dumps(dict(identity=identity, selected=asdict(selected),
            diagnostics=asdict(self.dashboard.command_diagnostics or self.mapper.diagnostics),
            simple=asdict(self.simple.feedback) if self.dashboard.preferences.mode is InputMode.SIMPLE else None,
            preferences=asdict(self.dashboard.preferences),
            focused=focused, focus=focus, blocked=self.dashboard.blocked, manual=manual,
            two_hand=asdict(self.two_hand_snapshot) if self.two_hand_snapshot else None), allow_nan=False) + "\n")
        self.controller.consume_interaction(selected)
        self.controller.consume_presentation(packet, frame, selected)

    def close(self):
        if self._closed:
            return
        self._closed = True
        errors = []
        actions = [self.intent_journal.close, self.reset]
        if self.two_hand_provider is not None:
            actions.append(self.two_hand_provider.close)
        if self._output is not None:
            actions.append(self._output.close)
        for action in actions:
            try:
                action()
            except Exception as exc:
                errors.append(exc)
        self.counts["closed"] = True
        self.counts["cleanup_errors"] = len(errors)
        try:
            (self.directory / "summary.json").write_text(json.dumps(self.counts, indent=2), encoding="utf-8")
        except Exception as exc:
            errors.append(exc)
        if errors:
            for extra in errors[1:]:
                errors[0].add_note(f"Further cleanup failed: {extra}")
            raise errors[0]


class ApplicationSource(GeometryCaptureSource):
    def __init__(self, source, composition):
        super().__init__(source, composition.observer)
        self.composition = composition

    def open(self):
        self.composition.reset()
        super().open()

    def close(self):
        try:
            super().close()
        finally:
            self.composition.reset()
