"""Opt-in observation composition; the default live_demo remains legacy."""

import argparse
from pathlib import Path

from . import live_demo
from .full_hand.observe import (
    CompositionMode, FullHandObserver, GeometryCaptureSource, SnapshotJournal,
    load_observe_profile,
)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=[m.value for m in CompositionMode],
                        default=CompositionMode.OBSERVE_FULL_HAND.value)
    parser.add_argument("--profile", type=Path,
                        default=live_demo.PROJECT_ROOT / "config/extensions/full_hand_observe.yaml")
    parser.add_argument("--output-dir", type=Path,
                        default=live_demo.PROJECT_ROOT / "runs/full-hand-observe")
    parser.add_argument("--pinch-diagnostic", action="store_true",
                        help="Observation-only geometry journal; T=touch, U=release, N=note")
    args = parser.parse_args(argv)
    if args.pinch_diagnostic and args.mode == CompositionMode.LEGACY.value:
        parser.error("--pinch-diagnostic requires OBSERVE_FULL_HAND")
    if args.mode == CompositionMode.LEGACY.value:
        live_demo.main()
        return
    profile = load_observe_profile(args.profile)
    journals = []
    observers = []
    def build(*, cfg, run_id, controller, metadata):
        journal = SnapshotJournal(args.output_dir / run_id, profile, dict(metadata))
        journals.append(journal)
        observer = FullHandObserver(profile, journal.consume)
        observers.append(observer)
        print(f"OBSERVE_FULL_HAND diagnostics: {journal.directory}")
        callback = observer.presentation_callback(controller.consume_presentation)
        if args.pinch_diagnostic:
            from .full_hand.pinch_diagnostic import PinchDiagnosticJournal, diagnostic_callback
            diagnostic = PinchDiagnosticJournal(journal.directory, profile)
            journals.append(diagnostic)
            callback = diagnostic_callback(observer, diagnostic, controller.consume_presentation)
            print("PHYSICAL MARKERS: hold T briefly at contact; U when apart; N optional note.")
        return live_demo._build_runtime(
            cfg=cfg, run_id=run_id, controller=controller,
            source_adapter=lambda source: GeometryCaptureSource(source, observer),
            presentation_consumer=callback,
        )
    try:
        live_demo.main(runtime_builder=build)
    finally:
        try:
            for observer in observers:
                observer.reset()
        finally:
            for journal in journals:
                journal.close()


if __name__ == "__main__":
    main()
