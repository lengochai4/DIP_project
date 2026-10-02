"""Observation-only composition, local sidecar and exact legacy shadow parity."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
import warnings

from dip_touchless.core import TrackingStatus
from .intent_session import IntentObservationSession
from .intent_temporal import IntentTransitionReason as Reason
from .observe import GeometryCaptureSource


KEY_ORDER = ("RESET_REFERENCE", "CALIBRATE_RELEASE", "INTEND_CLOSE", "INTEND_OPEN", "NON_INTENT")


def poll_intent_keys():
    import pygame
    keys = pygame.key.get_pressed()
    bindings = ((pygame.K_k, "CALIBRATE_RELEASE"), (pygame.K_x, "RESET_REFERENCE"),
                (pygame.K_t, "INTEND_CLOSE"), (pygame.K_u, "INTEND_OPEN"), (pygame.K_n, "NON_INTENT"))
    return {event for key, event in bindings if keys[key]}, pygame.key.get_focused()


class IntentCaptureSource(GeometryCaptureSource):
    """Reset observation references on source open/close, including failures."""

    def __init__(self, source, observer, journal):
        super().__init__(source, observer)
        self.journal = journal

    def open(self):
        self.journal.session.reset()
        super().open()

    def close(self):
        try:
            super().close()
        finally:
            self.journal.session.reset()
            if self.journal.presentation_sink:
                self.journal.presentation_sink(None)


class IntentDiagnosticJournal:
    def __init__(self, directory: Path, session: IntentObservationSession, metadata: dict,
                 legacy_engine, *, poll=poll_intent_keys, presentation_sink=None,
                 command_description="legacy GestureEngine ONLY"):
        self.directory, self.session = directory, session
        self.legacy_engine = legacy_engine
        self.poll, self.presentation_sink = poll, presentation_sink
        directory.mkdir(parents=True, exist_ok=False)
        self._previous_keys = set()
        self._previous_identity = None
        self._last_console = None
        self._last_time = self._last_status = None
        self._last_eligible = False
        self._phase = "UNLABELED"
        self._markers = 0
        self._file = (directory / "intent_snapshots.jsonl").open("x", encoding="utf-8")
        self.counts = dict(frames=0, tracking_valid=0, valid_tracking_seconds=0., entries=0,
                           safe_releases=0, rearms=0, revalidations=0, unknown_frames=0,
                           legacy_parity_compared=0, legacy_parity_mismatches=0,
                           safety_violations=0, diagnostic_errors=0,
                           non_intent_entries=0, non_intent_valid_seconds=0.,
                           non_intent_eligible_seconds=0.)
        files = ("intent_pinch_contracts.py", "pinch_reference.py", "relative_closure.py",
                 "intent_temporal.py", "intent_session.py", "intent_diagnostic.py", "intent_presentation.py")
        manifest = dict(schema="intent-pinch-observe-v1", scope="local development, not G7 or submission evidence",
                        commands=command_description, profile=asdict(session.profile),
                        profile_sha256=session.profile.sha256, legacy_metadata=metadata,
                        source_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                       for name in files},
                        webcam_images_stored=False,
                        keys=dict(K="confirm comfortable-apart calibration window", X="clear reference",
                                  T="begin intended closing phase", U="intended opening", N="non-intent phase"),
                        label_timing="focused rising key at source frame; operator timing uncertainty",
                        protocol="observe only; physical attempts and misses require operator confirmation")
        try:
            (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
        except Exception:
            self._file.close()
            raise

    def consume(self, packet, frame, legacy, full_hand_snapshot):
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if identity == self._previous_identity:
            return
        if identity != (full_hand_snapshot.run_id, full_hand_snapshot.frame_id, full_hand_snapshot.timestamp_s):
            raise ValueError("intent/full-hand identity mismatch")
        pressed, focused = self.poll()
        current = set(pressed)
        rising = current - self._previous_keys if focused else set()
        self._previous_keys = current
        events = tuple(e for e in KEY_ORDER if e in rising)
        previous_phase = self._phase
        # An unfocused window must not continue a hold/enrollment silently.
        if not focused:
            self.session.reset()
        if "INTEND_CLOSE" in events and "INTEND_OPEN" in events:
            events = tuple(e for e in events if e not in ("INTEND_CLOSE", "INTEND_OPEN"))
            self._phase = "AMBIGUOUS"
        for e in events:
            if e in ("INTEND_CLOSE", "INTEND_OPEN", "NON_INTENT"):
                self._phase = e
        if events:
            self._markers += 1
        result = self.session.consume(frame, full_hand_snapshot.hand, events=events)
        expected = self.legacy_engine.update(frame)
        mismatch = tuple(name for name in expected.__dataclass_fields__
                         if legacy is None or getattr(expected, name) != getattr(legacy, name))
        self._previous_identity = identity
        if self.presentation_sink:
            self.presentation_sink(result)  # None explicitly clears stale presentation.
        self.counts["frames"] += 1
        valid_tracking = frame.status is TrackingStatus.VALID
        self.counts["tracking_valid"] += int(valid_tracking)
        dt = 0. if self._last_time is None else frame.timestamp_s - self._last_time
        tracked_interval = valid_tracking and self._last_status is TrackingStatus.VALID and 0 < dt <= self.session.profile.temporal.reset_gap_s
        eligible = (result is not None and valid_tracking and result.observation is not None
                    and result.observation.valid and result.reference is not None
                    and result.reference.valid and result.temporal.armed)
        if tracked_interval:
            self.counts["valid_tracking_seconds"] += dt
            if self._phase == previous_phase == "NON_INTENT":
                self.counts["non_intent_valid_seconds"] += dt
                if eligible and self._last_eligible:
                    self.counts["non_intent_eligible_seconds"] += dt
        self._last_time, self._last_status = frame.timestamp_s, frame.status
        self._last_eligible = eligible
        self.counts["legacy_parity_compared"] += 1
        self.counts["legacy_parity_mismatches"] += bool(mismatch)
        if result:
            state = result.temporal
            self.counts["entries"] += Reason.ENTERED in state.reasons
            self.counts["safe_releases"] += Reason.SAFE_RELEASE in state.reasons
            self.counts["rearms"] += Reason.REARMED in state.reasons
            self.counts["revalidations"] = result.revalidation_id
            self.counts["unknown_frames"] += state.state.value == "UNKNOWN"
            self.counts["non_intent_entries"] += self._phase == "NON_INTENT" and Reason.ENTERED in state.reasons
            safe = (valid_tracking and result.observation is not None and result.observation.valid
                    and result.reference is not None and result.reference.valid)
            self.counts["safety_violations"] += state.active_evidence and not safe
        else:
            self.counts["unknown_frames"] += 1
        row = dict(run_id=frame.run_id, frame_id=frame.frame_id, timestamp_s=frame.timestamp_s,
                   tracking_status=frame.status, phase=self._phase, marker_id=self._markers,
                   events=events, poll_monotonic_s=time.perf_counter(),
                   snapshot=asdict(result) if result else None,
                   fingers={f.finger.value: f.state.value for f in full_hand_snapshot.pose.fingers}
                           if full_hand_snapshot.pose else None,
                   candidate_pose=full_hand_snapshot.pose.pose if full_hand_snapshot.pose else None,
                   stable_pose=full_hand_snapshot.temporal.stable_pose,
                   legacy_parity=not mismatch, legacy_mismatched_fields=mismatch)
        self._file.write(json.dumps(row, allow_nan=False) + "\n")
        self._file.flush()
        summary = (result.calibration_status, result.temporal.state, result.temporal.armed,
                   result.temporal.cycle_id, result.enrollment_reasons) if result else None
        if summary != self._last_console:
            self._last_console = summary
            print(f"[INTENT OBSERVE] frame={frame.frame_id} {summary} legacy_parity={not mismatch}", flush=True)

    def close(self):
        self.session.reset()
        if self.presentation_sink:
            self.presentation_sink(None)
        self._file.close()
        (self.directory / "summary.json").write_text(
            json.dumps(dict(self.counts, journal_closed=True), indent=2), encoding="utf-8")


def intent_callback(observer, journal, legacy_presentation):
    reported = set()
    def consume(packet, frame, legacy):
        try:
            full_snapshot = observer.consume(packet, frame, legacy)
            journal.consume(packet, frame, legacy, full_snapshot)
        except Exception as exc:
            journal.counts["diagnostic_errors"] += 1
            journal.session.reset()
            if journal.presentation_sink:
                journal.presentation_sink(None)
            message = f"Intent observation unavailable: {type(exc).__name__}: {exc}"
            if message not in reported:
                reported.add(message)
                try:
                    warnings.warn(message, RuntimeWarning)
                except RuntimeWarning:
                    pass
        return legacy_presentation(packet, frame, legacy)
    return consume
