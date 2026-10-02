"""Run the V2 product frontend. Camera starts only on explicit user action."""

import argparse
import sys
from app.config import ProductConfig, Settings, ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=str(ROOT / "config/product_v2.yaml"))
    parser.add_argument(
        "--preferences", default=str(ROOT / "runs/product-v2/preferences.json")
    )
    parser.add_argument(
        "--software",
        action="store_true",
        help="Use the identical scene on a software surface if OpenGL is unavailable",
    )
    parser.add_argument("--camera", type=int)
    args = parser.parse_args(argv)
    try:
        config = ProductConfig.load(args.profile)
        settings = Settings.load(args.preferences)
        if args.camera is not None:
            from dataclasses import replace

            settings = replace(settings, camera_index=args.camera)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    from PySide6.QtWidgets import QApplication
    from app.ui.shell import ProductWindow

    application = QApplication.instance() or QApplication(sys.argv[:1])
    window = ProductWindow(
        config, settings, software=args.software, preferences_path=args.preferences
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
