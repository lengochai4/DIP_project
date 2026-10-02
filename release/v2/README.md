# DIP Touchless STEM V2 — 2.0.0rc1

New PySide6 frontend and semantic product interaction layer. Frozen G7 research
and the Pygame v1.0 application remain available unchanged.

From the repository root:

```powershell
.\setup_v2.ps1
.\launch_v2.ps1
```

The existing local model is expected at `models/hand_landmarker.task`. Setup and
its official download/hash are documented in [models/README.md](../../models/README.md).
The model is included only in the optional local source archive built with
`--include-model`; it is never committed to Git.

No camera opens on launch. Use **Start camera** when needed. All labs can be
explored without a camera using mouse and keyboard. If OpenGL is unavailable:

```powershell
.\launch_v2.ps1 -Software
```

Home opens first. Explore provides lab library, WORLD/HAND and inspector tools.
Analyze shows live Core diagnostics and the separate product hand path. Evidence
reads frozen G7 assets. Calibrate has release reference, intentional pinch/release,
POINT and OPEN PALM steps. Settings provides explicit PRODUCT/LEGACY selection,
dominant hand, mirror/sensitivity, camera and accessibility preferences. Help
contains gestures and keyboard controls.

Gestures: POINT inspects; calibrated PINCH selects/clutches; OPEN PALM anchors;
V-SIGN enters construction/measure mode. Two calibrated pinches scale relative
to their starting palm separation. Two index pointers preview/lock a measurement
and dominant pinch commits it. Lost/unknown tracking cancels; release to rearm.

Mouse: hover to inspect, drag to rotate, wheel to scale. Select a construction
tool and click to commit points. Inspector Commit point, Undo, Finish polygon,
Cancel and Reset provide visible fallbacks. Keyboard: 1–7 pages, H WORLD/HAND,
M measurement, Enter commit, Esc cancel, arrows rotate, +/- scale, Space pause,
R reset and F11 full screen. Text inputs retain ordinary native editing.

Optional source archive:

```powershell
.\.venv\Scripts\python.exe -m developer_tools.package_v2 --include-model
```

Archives contain source, setup/launch, configuration, tests, documentation and
frozen resources. They exclude virtual environments, session logs and private
preferences. Installation still needs Python and dependency packages; this is
not a standalone executable or an offline dependency bundle.

Status and actual checks are recorded in [QA_STATUS.md](QA_STATUS.md). Physical
usability testing is deferred by the user. No physical success percentages,
false-activation rate, commercial validation or production readiness are claimed.
The RC identity labels this source delivery; no remote release was published.
