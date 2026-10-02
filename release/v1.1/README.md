# DIP Touchless STEM v1.1 application candidate

The application is implemented for engineering evaluation. **Physical acceptance
is pending**. Commercial validation, production readiness and general gesture
accuracy are not established. v1.0 and G7 remain immutable rollback/research
baselines. G9 was not restored. This release directory is separate from frozen
`submission/evidence/` and final research experiments.

## Setup

Use Python 3.11 and a Windows desktop with OpenGL. Extract the full source package
and run commands from its root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,demo3d]"
.venv\Scripts\python.exe -m pip check
```

Provide `models/hand_landmarker.task`; see [model setup](../../models/README.md)
for the official download and pinned checksum. The verified local SHA-256 is
`fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.
The model is **not** included in the source ZIP. No fresh environment installation
is claimed by the current QA; dependencies were checked in the existing venv.
Do not install a second OpenCV distribution alongside the declared contrib package.

## Launch

```powershell
.venv\Scripts\python.exe -m extensions.stem3d.app
.venv\Scripts\python.exe -m extensions.stem3d.app --mode LEGACY
.venv\Scripts\python.exe -m extensions.stem3d.app --mode OBSERVE
.venv\Scripts\python.exe -m extensions.stem3d.app --mode FULL_HAND
.venv\Scripts\python.exe -m extensions.stem3d.app --mode FULL_HAND --allow-two-hand
.venv\Scripts\python.exe -m extensions.stem3d.app --help
```

`launch_application.ps1` selects the repository venv and runs from the correct
directory. `--camera-index N` explicitly selects another camera. `--user-profile`
loads explicitly saved ergonomic preferences; measured references never persist.
SIMPLE preferences can be restored explicitly; experimental PINCH actions and
measured references do not resume at the next launch.
`--application-profile` and `--intent-profile` select Extension engineering
configuration explicitly. Default new-input values are unvalidated starters,
not tuned physical findings; research configuration is unchanged.

Press Enter/S to start. Startup has loading/camera/model/renderer/logging error
states. On failure, dismiss with Q, correct the component and restart. The v1.1
entry returns a nonzero exit status for runtime failure. Sessions use unique
`stem-v11-YYYYMMDD-HHMMSS-microseconds` identities. Local journals/settings live
under writable `runs/`. Images are off by default; there is no network telemetry.

## Application walkthrough

1. **Workspace:** choose Coordinate Geometry, Molecule (Water/Methane) or Orbital.
   Keyboard/mouse fallback works without a detected hand.
2. **Analysis:** inspect the original DIP pipeline, filtered/raw landmarks and
   full-hand candidate/stable pose, finger states and relative-intent lifecycle.
   The old scalar PINCH pose and new intentional-PINCH state are separate diagnostics.
3. **Evidence:** read the frozen G7 Overview/A1/A2/B/RQ3 pages. Live v1.1 output
   does not change the research record. Scene manipulation is suspended in this view.
4. **Simple controls (default):** extend only the index finger and move it to
   rotate. Open one palm for 0.8 s to open Control Space; move the palm cursor
   over a button for 1.2 s to select. Move off a selected button before selecting
   it again. Close the menu, open two palms for dwell, then move them apart/together
   to scale. Thumb stretch/contact is not required. No PINCH calibration is needed.
   The source-camera central 70% maps to the full menu; mirror applies consistently.
   UNKNOWN/loss cancels immediately and a returned pose needs fresh dwell.
5. **Settings (,):** select SIMPLE, LEGACY, OBSERVE or experimental FULL_HAND. Legacy
   commands are unchanged. OBSERVE computes full-hand diagnostics alongside them.
   Select sensitivity (Gentle/Standard/Responsive), mirror or explicit reference reset.
6. **Optional experimental PINCH calibration:** hold thumb/index comfortably apart; press **K** or click
   Confirm apart & calibrate. Hold steady for 1.5 s until READY, then wait for
   RELEASED/rearm. No automatic enrollment, skin-contact test or startup reference
   guessing. Noisy/interrupted windows require explicit retry. **X** clears reference.
7. **Experimental FULL_HAND:** stable POINT controls pointer/rotation; intentional closing
   followed by dwell enables PINCH. In the scene, hold PINCH and move the hand
   vertically to scale. Open/release to rearm. In Control Space, hover, release
   then pinch once to select. UI and scene never receive simultaneous commands.
   FIST is diagnostic only. UNKNOWN/loss/reset revokes; returning closed cannot
   resume an old action. Projection/source changes may require recalibration.
8. **Two-hand SIMPLE scale:** the default launcher enables the independent provider
   and Settings toggle. Four extended non-thumb fingers on each hand form the
   open-palm signal; it does not depend on a one-hand pinch reference. Only scale
   is mapped to two hands; pair presence suppresses one-hand rotation/menu selection.
   Association crossing, discontinuity or loss revokes and requires new dwell.
   The additional inference cost and physical usability remain to be validated.
9. **Advanced two-hand experiment:** requires `--allow-two-hand` plus the Settings toggle
   and FULL_HAND with a valid one-hand release reference. Keep both palms open
   for dwell; change projected palm separation to scale. No rotation/click is
   mapped to the pair. Ambiguous association/occlusion/loss is neutral. Returning
   to one hand requires safe release. The extra independent provider uses Raw
   x/y landmarks and adds inference cost; physical reliability is unverified.

Fallback: **J/L**, **I/O** rotate; **+/-** scale; right-drag/wheel inside the scene
rotate/scale. **R** reset; **1/2/3** scenes; **D/A/E** views; **P** Control Space;
**? / F1** Help; **Q/ESC** exit. Settings/Help/Provenance are modal and suspend
touchless scene commands. Mouse can close Help and select all controls.

## Validation and local artifacts

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall extensions/stem3d
git diff --check
.venv\Scripts\python.exe -m developer_tools.application_qa --capture-gl
.venv\Scripts\python.exe -m developer_tools.package_application
```

The QA tool uses synthetic landmarks and a hidden actual OpenGL renderer,
without webcam/model inference. Screenshots are visibly labeled synthetic.
CPU profiling measures UI construction only; it is not webcam FPS/latency evidence.
The package tool checks frozen paths/tags, builds a source snapshot from current
tracked/untracked source files, excludes local runs/environments/model/G9 and
records hashes plus dirty-tree provenance. ZIP creation never publishes a release.
An existing output is never overwritten silently. The Core wheel alone does not
contain the application/resources; use the full source snapshot.

Before a release, use the [physical acceptance procedure](PHYSICAL_ACCEPTANCE.md).
Record counts honestly, then fix observed defects in the smallest relevant unit.
Recommended eventual commit: `feat: complete v1.1 intentional full-hand application`.
Recommended eventual tag: `dip-touchless-stem-v1.1` **after** physical gates pass.
No stage, commit, push, tag or stash deletion has been performed.
