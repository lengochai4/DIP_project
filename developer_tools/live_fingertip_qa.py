"""Native automatic multi-fingertip render QA; no webcam or physical hand claims."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app.config import ROOT, ProductConfig, Settings
from app.ui.shell import ProductWindow
from app.rendering.viewport import Viewport
from dip_touchless.core import (
    FramePacket,
    ColorSpace,
    TrackingFrame,
    TrackingStatus,
    MeasurementQuality,
    FilterDiagnostics,
    FilterMode,
    StageTimings,
)
from .synthetic_hands import landmarks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/live-fingertip-qa"))
    parser.add_argument("--opengl", action="store_true")
    parser.add_argument(
        "--workspace",
        action="store_true",
        help="Capture all labs with guides and expanded/restored layouts at three window sizes",
    )
    parser.add_argument(
        "--all-presets",
        action="store_true",
        help="Audit every lab/preset with point, triangle, tetrahedron and ten-tip inputs",
    )
    args = parser.parse_args(argv)
    if args.workspace and args.all_presets:
        parser.error("--workspace and --all-presets are separate QA matrices")
    args.output.mkdir(parents=True, exist_ok=True)
    qt = QApplication.instance() or QApplication([])
    config = ProductConfig.load()
    captures = []
    cases = {
        1: {"Left": {4}},
        2: {"Left": {4}, "Right": {2}},
        3: {"Right": {1, 2, 3}},
        4: {"Right": {1, 2, 3, 4}},
        5: {"Right": set(range(5))},
        10: {"Left": set(range(5)), "Right": set(range(5))},
    }
    if args.all_presets:
        cases = {n: cases[n] for n in (1, 3, 4, 10)}
    elif args.workspace:
        cases = {10: cases[10]}
    with patch.object(
        QApplication,
        "applicationState",
        return_value=Qt.ApplicationState.ApplicationActive,
    ):
        window = ProductWindow(
            config,
            Settings(),
            software=not args.opengl,
            preferences_path=args.output / "preferences.json",
        )
        qt.applicationStateChanged.disconnect(window._application_state)
        window.show()
        try:
            window.navigate("Explore")
            window.select_lab("coordinate")
            window.reveal_tools(True)
            variants = (
                [
                    (lab.id, preset)
                    for lab in window.registry.extensions.values()
                    for preset in lab.presets
                ]
                if args.all_presets
                else (
                    [
                        (lab.id, lab.preset)
                        for lab in window.registry.extensions.values()
                    ]
                    if args.workspace
                    else [("coordinate", "Default")]
                )
            )
            sizes = (
                ((1040, 680), (1280, 720), (1600, 900))
                if args.workspace
                else (
                    ((1600, 900),) if args.all_presets else ((1280, 720), (1600, 900))
                )
            )
            states = (
                ("guide", "guide-hidden", "expanded", "expanded-guide", "restored")
                if args.workspace
                else ("tools",)
            )
            sequence = (
                (lab_id, preset, size, mode, count, roles, state)
                for lab_id, preset in variants
                for size in sizes
                for mode in ("WORLD", "HAND")
                for count, roles in cases.items()
                for state in states
            )
            for lab_id, preset, size, mode, count, roles, state in sequence:
                if window._expanded:
                    window.set_expanded(False)
                if args.workspace:
                    # Keep capture dimensions independent of desktop work-area limits.
                    window.setFixedSize(*size)
                else:
                    window.resize(*size)
                if window.registry.current.id != lab_id:
                    window.select_lab(lab_id)
                if window.registry.current.preset != preset:
                    window.choose_preset(preset)
                window.set_mode(mode)
                if args.workspace:
                    window.reveal_guide(True)
                    qt.processEvents()
                    baseline = window.viewport.width()
                    if state == "guide-hidden":
                        window.reveal_guide(False)
                    elif state in {"expanded", "expanded-guide", "restored"}:
                        window.set_expanded(True)
                        qt.processEvents()
                        assert window.viewport.width() > baseline
                        if state == "expanded-guide":
                            window.reveal_guide(True)
                        elif state == "restored":
                            window.set_expanded(False)
                            assert window.guide_button.isChecked()
                    qt.processEvents()
                hands = {
                    label: landmarks(
                        fingers,
                        center=0.25 if label == "Left" else 0.7,
                        tip_depths=(0, 0.05, -0.05, 0.05, -0.05),
                    )
                    for label, fingers in roles.items()
                }
                run = f"synthetic-live-qa-{uuid4().hex[:12]}"
                for i in range(3):
                    ts = 1 + i * 0.1
                    packet = FramePacket(
                        run,
                        i,
                        ts,
                        np.full((480, 640, 3), (34, 45, 55), np.uint8),
                        ColorSpace.BGR,
                        "synthetic geometry",
                    )
                    frame = TrackingFrame(
                        run,
                        i,
                        ts,
                        TrackingStatus.VALID,
                        (),
                        (),
                        MeasurementQuality.unavailable(),
                        None,
                        None,
                        FilterDiagnostics(
                            FilterMode.RAW,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            False,
                        ),
                        StageTimings(0, 0, 0, 0, 0),
                        (),
                    )
                    window.consume(packet, frame, None, hands, True, "TRACKING")
                    qt.processEvents()
                shape = window.registry.current.live_shape
                assert len(shape.points) == count
                if count in {4, 10}:
                    assert shape.solid
                assert not window.tool_actions.isVisible()
                if args.workspace:
                    assert (window.width(), window.height()) == size, (
                        lab_id,
                        mode,
                        state,
                        size,
                        (window.width(), window.height()),
                        window.minimumSizeHint(),
                    )
                    for control in (
                        window.guide_button,
                        window.expand_button,
                        window.world_button,
                        window.hand_button,
                        window.ui_control_button,
                        window.tools_button,
                    ):
                        assert control.isVisible()
                        assert window.rect().contains(
                            control.mapTo(window, control.rect().bottomRight())
                        )
                if args.opengl:
                    assert (
                        isinstance(window.viewport, Viewport)
                        and window.viewport.isValid()
                    )
                    assert (
                        window.viewport.gpu_renderer is not None
                        and window.viewport.gpu_error is None
                    )
                suffix = (
                    f"-{lab_id}-{preset.lower().replace(' ', '-')}"
                    if args.all_presets or args.workspace
                    else ""
                )
                if args.workspace:
                    suffix += "-" + state
                path = (
                    args.output
                    / f"{size[0]}x{size[1]}-{mode.lower()}-{count}-vertices{suffix}-synthetic.png"
                )
                assert window.grab().save(str(path))
                captures.append(
                    {
                        "path": path.name,
                        "lab": lab_id,
                        "preset": preset,
                        "vertices": count,
                        "kind": shape.kind,
                        "solid": shape.solid,
                        "mode": mode,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "logical_size": [window.width(), window.height()],
                        "workspace": state,
                        "viewport_size": [
                            window.viewport.width(),
                            window.viewport.height(),
                        ],
                    }
                )
        finally:
            window.close()
            qt.processEvents()
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "validation": "synthetic only; no webcam; not physical accuracy",
                "renderer": "OpenGL mesh/depth" if args.opengl else "software",
                "interaction": "automatic LIVE fingertips; no Add point or pinch commit",
                "product_profile": asdict(config),
                "source_sha256": {
                    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (ROOT / "app").rglob("*.py")
                },
                "captures": captures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Captured {len(captures)} automatic full-fingertip surfaces to {args.output}"
    )


if __name__ == "__main__":
    main()
