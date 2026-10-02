"""Opt-in observation composition; the default live_demo remains legacy."""

import argparse
from pathlib import Path

from . import live_demo
from .full_hand.observe import (
    CompositionMode, FullHandObserver, GeometryCaptureSource, SnapshotJournal,
    load_observe_profile,
)

BASELINE_PROFILE = live_demo.PROJECT_ROOT / "config/extensions/full_hand_observe.yaml"
CANDIDATE_PROFILE = live_demo.PROJECT_ROOT / "config/extensions/full_hand_pinch_candidate.yaml"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=[m.value for m in CompositionMode],
                        default=CompositionMode.OBSERVE_FULL_HAND.value)
    parser.add_argument("--profile", type=Path,
                        default=BASELINE_PROFILE)
    parser.add_argument("--output-dir", type=Path,
                        default=live_demo.PROJECT_ROOT / "runs/full-hand-observe")
    parser.add_argument("--pinch-diagnostic", action="store_true",
                        help="Observation-only geometry journal; T=touch, U=release, N=note")
    parser.add_argument("--pinch-visual", action="store_true",
                        help="Opt-in local synchronized T/U images; requires --pinch-diagnostic")
    parser.add_argument("--pinch-calibration-markers", action="store_true",
                        help="Diagnostic labels: V=near NOT touching, B=medium separation")
    parser.add_argument("--intent-pinch-observe", action="store_true",
                        help="Opt-in relative-intention observation; K=calibrate apart, X=clear")
    parser.add_argument("--intent-profile", type=Path,
                        default=live_demo.PROJECT_ROOT / "config/extensions/intent_pinch_observe.yaml")
    args = parser.parse_args(argv)
    if args.pinch_visual and not args.pinch_diagnostic:
        parser.error("--pinch-visual requires --pinch-diagnostic")
    if args.pinch_calibration_markers and not args.pinch_diagnostic:
        parser.error("--pinch-calibration-markers requires --pinch-diagnostic")
    if args.intent_pinch_observe and (args.mode == CompositionMode.LEGACY.value or args.pinch_diagnostic):
        parser.error("intent observation requires OBSERVE_FULL_HAND and separate intention labels; no contact diagnostic")
    if args.mode == CompositionMode.LEGACY.value and args.profile.resolve() == CANDIDATE_PROFILE.resolve():
        parser.error("experimental PINCH candidate requires OBSERVE_FULL_HAND; legacy profile is unchanged")
    if args.pinch_diagnostic and args.mode == CompositionMode.LEGACY.value:
        parser.error("--pinch-diagnostic requires OBSERVE_FULL_HAND")
    if args.mode == CompositionMode.LEGACY.value:
        live_demo.main()
        return
    profile = load_observe_profile(args.profile)
    print(f"Full-hand observation profile: {args.profile.resolve()} "
          f"ENTER={profile.pose.pinch_enter_distance_palm} EXIT={profile.pose.pinch_exit_distance_palm}; "
          "application commands remain legacy-only")
    journals = []
    observers = []
    intent_dashboards = []
    intent_profile = None
    if args.intent_pinch_observe:
        from .full_hand.intent_session import load_intent_profile
        intent_profile = load_intent_profile(args.intent_profile)
        print(f"RELATIVE INTENT OBSERVE profile={intent_profile.sha256}; UNVALIDATED; no full-hand commands")

    def intent_dashboard_factory(**kwargs):
        from .full_hand.intent_presentation import IntentObservationDashboard
        dashboard = IntentObservationDashboard(**kwargs)
        intent_dashboards.append(dashboard)
        return dashboard
    def build(*, cfg, run_id, controller, metadata):
        journal = SnapshotJournal(args.output_dir / run_id, profile, dict(metadata),
                                  webcam_images_stored=args.pinch_visual)
        journals.append(journal)
        observer = FullHandObserver(profile, journal.consume)
        observers.append(observer)
        print(f"OBSERVE_FULL_HAND diagnostics: {journal.directory}")
        callback = observer.presentation_callback(controller.consume_presentation)
        source_adapter = lambda source: GeometryCaptureSource(source, observer)
        if intent_profile is not None:
            from .full_hand.intent_pinch_contracts import ReferenceScope
            from .full_hand.intent_session import IntentObservationSession
            from .full_hand.intent_diagnostic import IntentDiagnosticJournal, IntentCaptureSource, intent_callback
            scope = ReferenceScope(run_id, run_id, str(cfg["camera"]["index"]),
                str(metadata.get("provider", {}).get("name", "configured-mediapipe")),
                intent_profile.sha256, "full-frame-aspect-corrected-xy", "intent-epoch-0")
            session = IntentObservationSession(intent_profile, scope)
            intent = IntentDiagnosticJournal(journal.directory / "intent_pinch", session, dict(metadata),
                live_demo._build_gesture_engine(cfg["gesture"]),
                presentation_sink=intent_dashboards[-1].set_intent_snapshot if intent_dashboards else None)
            journals.append(intent)
            callback = intent_callback(observer, intent, controller.consume_presentation)
            source_adapter = lambda source: IntentCaptureSource(source, observer, intent)
            print("INTENT KEYS: K confirms apart calibration; X clears; T intended-close phase; U open; N non-intent.")
        if args.pinch_diagnostic:
            from .full_hand.pinch_diagnostic import PinchDiagnosticJournal, diagnostic_callback
            diagnostic = PinchDiagnosticJournal(journal.directory, profile, visual_capture=args.pinch_visual,
                                                calibration_labels=args.pinch_calibration_markers)
            journals.append(diagnostic)
            callback = diagnostic_callback(observer, diagnostic, controller.consume_presentation)
            print("PHYSICAL MARKERS: hold T briefly at contact; U when apart; N optional note.")
            if args.pinch_calibration_markers:
                print("CALIBRATION LABELS: V=very near, NOT touching; B=medium separation. Labels do not issue commands.")
        return live_demo._build_runtime(
            cfg=cfg, run_id=run_id, controller=controller,
            source_adapter=source_adapter,
            presentation_consumer=callback,
        )
    try:
        if intent_profile is not None:
            live_demo.main(runtime_builder=build, dashboard_factory=intent_dashboard_factory)
        else:
            live_demo.main(runtime_builder=build)
    finally:
        try:
            for observer in observers:
                observer.reset()
        finally:
            cleanup_errors = []
            for journal in journals:
                try:
                    journal.close()
                except Exception as exc:
                    cleanup_errors.append(exc)
            if cleanup_errors:
                for extra in cleanup_errors[1:]:
                    cleanup_errors[0].add_note(f"Further diagnostic cleanup failed: {extra}")
                raise cleanup_errors[0]


if __name__ == "__main__":
    main()
