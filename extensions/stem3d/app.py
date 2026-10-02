"""v1.1 desktop application: point, open-palm navigation and two-hand scale."""

import argparse
from pathlib import Path
from . import live_demo
from .full_hand.observe import load_observe_profile
from .full_hand.intent_session import load_intent_profile
from .product.settings import InputMode, UserSettings, load_application_profile, load_settings
from .product.dashboard import ApplicationDashboard
from .product.composition import ApplicationComposition, ApplicationSource, RuntimeControllerProxy

ROOT = live_demo.PROJECT_ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=[m.value for m in InputMode], default=None)
    parser.add_argument("--user-profile", type=Path, help="Explicit local preference file; reference is never restored")
    parser.add_argument("--application-profile", type=Path, default=ROOT / "config/extensions/application.yaml")
    parser.add_argument("--intent-profile", type=Path, default=ROOT / "config/extensions/intent_pinch_observe.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/application-v1.1")
    parser.add_argument("--allow-two-hand", action="store_true", help="Experimental independent two-hand provider; also enable in Settings")
    parser.add_argument("--camera-index", type=int, default=None, help="Explicit camera device selection; research defaults unchanged")
    args = parser.parse_args(argv)
    if args.camera_index is not None and args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    preferences = UserSettings(InputMode.SIMPLE, mirror=True, two_hand=True)
    if args.user_profile is not None:
        try:
            preferences = load_settings(args.user_profile)
        except (OSError, ValueError) as exc:
            parser.error(f"Cannot load user profile: {exc}")
    if args.mode is not None:
        from dataclasses import replace
        preferences = replace(preferences, mode=InputMode(args.mode))
    try:
        motion, gains, two = load_application_profile(args.application_profile)
        intent = load_intent_profile(args.intent_profile)
        observe = load_observe_profile(ROOT / "config/extensions/full_hand_observe.yaml")
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"Invalid application profile: {exc}")
    dashboards, compositions = [], []

    def dashboard_factory(**kwargs):
        dashboard = ApplicationDashboard(preferences=preferences,
            preferences_path=args.user_profile or ROOT / "runs/preferences/default.json", **kwargs)
        dashboards.append(dashboard)
        return dashboard

    def build(*, cfg, run_id, controller, metadata):
        composition = ApplicationComposition(controller=controller, dashboard=dashboards[-1],
            observe_profile=observe, intent_profile=intent, motion_profile=motion, sensitivity=gains,
            directory=args.output_dir / run_id, metadata=dict(metadata),
            legacy_engine=live_demo._build_gesture_engine(cfg["gesture"]))
        compositions.append(composition)
        if args.allow_two_hand or preferences.mode is InputMode.SIMPLE:
            from .product.two_hand import TwoHandAssociation, TwoHandProfile
            from application_adapters.two_hand_provider import TwoHandProvider
            association = TwoHandAssociation(TwoHandProfile(**two), observe.pose)
            provider = TwoHandProvider(live_demo.MODEL_PATH, cfg["tracking"])
            composition.enable_two_hand_capability(provider, association)
        return live_demo._build_runtime(cfg=cfg, run_id=run_id,
            controller=RuntimeControllerProxy(controller),
            source_adapter=lambda source: ApplicationSource(source, composition),
            presentation_consumer=composition.consume)

    print("DIP Touchless STEM v1.1 / experimental interaction / physical acceptance pending")
    print("Point: rotate / Open palm: Control Space + hover select / Two open hands: scale")
    print("Settings: , / Legacy always available / Pinch calibration is experimental, optional")
    try:
        from datetime import datetime
        live_demo.main(runtime_builder=build, dashboard_factory=dashboard_factory,
            camera_index=args.camera_index, raise_on_failure=True,
            run_id_factory=lambda: "stem-v11-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    finally:
        errors = []
        for composition in compositions:
            try:
                composition.close()
            except Exception as exc:
                errors.append(exc)
        if errors:
            for extra in errors[1:]:
                errors[0].add_note(f"Further cleanup error: {extra}")
            raise errors[0]


if __name__ == "__main__":
    main()
