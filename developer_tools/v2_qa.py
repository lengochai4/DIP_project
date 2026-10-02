"""Synthetic native UI captures, never webcam usability/research evidence."""

from pathlib import Path
import argparse
import hashlib
import json
from PySide6.QtWidgets import QApplication
from app.config import ROOT, ProductConfig, Settings
from app.ui.shell import ProductWindow, PAGES
from app.interaction.contracts import AnchorPose
from app.rendering.viewport import Viewport


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runs/v2-qa")
    parser.add_argument("--opengl", action="store_true")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window = ProductWindow(
        ProductConfig.load(),
        Settings(),
        software=not args.opengl,
        preferences_path=args.output / "preferences.json",
    )
    window.show()
    rows = []

    def capture(key):
        app.processEvents()
        if args.opengl and window.page_name == "Explore":
            if (
                not isinstance(window.viewport, Viewport)
                or not window.viewport.isValid()
            ):
                raise RuntimeError(
                    "OpenGL QA requires a valid QOpenGLWidget context; run software QA instead."
                )
        path = args.output / (key + "-synthetic.png")
        window.grab().save(str(path))
        rows.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": window.width(),
                "height": window.height(),
                "source": "synthetic UI; no physical webcam",
            }
        )

    try:
        for size in ((1280, 720), (1600, 900)):
            window.resize(*size)
            app.processEvents()
            prefix = f"{size[0]}x{size[1]}"
            for name in PAGES:
                window.navigate(name)
                capture(prefix + "-" + name.lower())
            window.navigate("Explore")
            for key in window.registry.extensions:
                window.select_lab(key)
                window.set_mode("WORLD")
                capture(prefix + "-" + key + "-world")
                window.set_mode("HAND")
                import numpy as np
                from app.rendering.viewport import bgr_image

                image = np.zeros((480, 640, 3), np.uint8)
                image[:] = (34, 45, 55)
                window.viewport.image = bgr_image(image)
                window.viewport.anchor = AnchorPose((0.5, 0.6), 0.18, 0.0)
                capture(prefix + "-" + key + "-hand")
            for i in range(8):
                window.navigate("Evidence")
                window.evidence_select.setCurrentIndex(i)
                capture(prefix + f"-evidence-{i}")
    finally:
        window.close()
        app.processEvents()
    manifest = {
        "validation": "synthetic only",
        "renderer": "QOpenGLWidget" if args.opengl else "software",
        "opengl_context_verified": args.opengl,
        "captures": rows,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Rendered {len(rows)} synthetic surfaces to {args.output}")


if __name__ == "__main__":
    main()
