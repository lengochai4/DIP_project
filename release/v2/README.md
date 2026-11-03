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
**Hướng dẫn (G)** shows/hides Vietnamese instructions for the selected lab,
preset and interaction mode; its normal visibility is saved in Settings.
**Phóng to (Ctrl+Shift+F)** expands the model frame by hiding the surrounding
panels. **Thu gọn / Esc** restores the prior layout. Guide/Tools remain available
while expanded; F11 separately toggles full screen. Guide and Tools open one at
a time. Optics only displays Index for Refraction and Focal for Lens.
Tools opens the contextual Inspector. Default LIVE geometry follows fingertips
automatically; point-by-point construction actions appear only in RECORDED mode.
Native GPU rendering uses perspective, lit meshes and depth testing,
with a software fallback. Molecular starts with tetrahedral CH4; H2O remains available.
Analyze shows live Core diagnostics and the separate product hand path. Evidence
reads frozen G7 assets. Calibrate has release reference, intentional pinch/release,
POINT and OPEN PALM steps. Settings provides explicit PRODUCT/LEGACY selection,
dominant hand, mirror/sensitivity, camera and accessibility preferences. Help
contains gestures and keyboard controls.

Default **PRODUCT / LIVE**: every extended fingertip on one or two hands becomes
a live vertex, including thumb, middle, ring and pinky. One vertex gives a point,
two a segment/vector and three a triangle. Four or more noncoplanar vertices form
a closed tetrahedron/polyhedron; nearly coplanar sets remain a quadrilateral/polygon.
Move, extend or fold fingers to reshape it continuously; no
Add point, pinch, preliminary calibration or automatic saved shape is needed.
All nine labs share the live geometry layer. WORLD/HAND vertices project back
to displayed tips, including mirror and letterboxing. HAND acquires from any
extended fingertip and an observed palm, including a support-only hand.
Model-relative depth is a bounded visual cue, not physical camera depth or a
measurement of depth between hands. Loss, no extended tips and context takeover
clear the live shape. Export measurements freezes the current scene for CSV.
Coordinate/Vector fill the geometry; other labs use its wire outline to keep the
lab model visible. Stable A–J labels identify active tips. LIVE Vector uses A→B
and C→D; missing pairs remain unavailable. Default Inspector prioritizes lab
values; Settings > diagnostics shows full XYZ afterward. The viewport labels
GPU/software rendering and planar versus spatial content. Wave/Optics are
intentional planar diagrams; H2O/CO2 remain planar molecules with 3D atom meshes.

**Control UI** explicitly switches to exclusive window/menu navigation using
POINT and calibrated PINCH; turn it off to resume live geometry. Calibration
is required for that pinch selection, not live geometry.

Optional **RECORDED**, selected in Settings > geometry_mode, keeps the earlier
point-by-point construction and model-manipulation flow described below.
Recorded gestures: POINT inspects; calibrated PINCH selects/clutches; OPEN PALM anchors;
V-SIGN enters construction/measure mode. Two calibrated pinches scale relative
to their starting palm separation. Two index pointers preview/lock a measurement
and dominant pinch commits it. Lost/unknown tracking cancels; release to rearm.
In HAND, open the palm once to acquire the scene; the same tracked palm continues
to anchor while pointing or pinching. The cursor follows the displayed index tip,
including mirror/letterboxing, independently of window pointer sensitivity.
In RECORDED/navigation, use only the index finger extended for POINT. Control UI explicitly switches
HAND to window/menu navigation, cancelling the current scene action first.
The on-screen hint distinguishes pose, missing calibration and support-only hands.
When more than two hands are detected, gesture control pauses and requires
neutral reacquisition/release. This cannot guarantee detection of every bystander's
hand. Low-light guidance appears when observed illumination is weak; add frontal
light for the camera. Contrast enhancement cannot recover missing scene detail.

Mouse: hover to inspect, drag to rotate, wheel to scale. In RECORDED, select a construction
tool and click to commit points. Inspector Commit point, Undo, Finish polygon,
Cancel and Reset provide visible fallbacks. Keyboard: 1–7 pages, H WORLD/HAND,
M measurement, Enter commit, Esc cancel, arrows rotate, +/- scale, Space pause,
R resets view and F11 full screen. M/Enter point construction is for RECORDED;
LIVE ignores manual commit/finish/undo. Scene shortcuts apply only in Explore;
text inputs, buttons and list navigation retain ordinary native behavior.

Reset view keeps measurements and lab parameters. Tools contains a separate
Reset lab action with confirmation, optional Snap free points and measurement
CSV export. Recorded grid snapping defaults off; its 0.25-scene-unit spacing is configurable
in the product profile. Free points snap within the current construction plane;
exact atom-centre picks are preserved. Rectangle validates right angles; use
Quadrilateral for arbitrary four corners. Undo corrects an invalid Rectangle.
CSV records construction points, first-edge distance/vector and, when applicable,
the first-three-point angle/triangle area. It contains no camera/hand/session data.
HAND without an anchor blocks scene input; choose WORLD for manual controls.

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
