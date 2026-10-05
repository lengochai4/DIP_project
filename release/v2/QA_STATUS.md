# V2 source delivery and verification — 2026-10-03

Identity: `2.0.0rc1` on `feat/v2-product-rebuild`, based on v1.0 commit
`2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`.

Implementation includes the new native frontend, all seven navigation pages,
four-gesture semantic pipeline, session calibration, shared WORLD/HAND projection,
separate two-hand product processing, exclusive routing, bimanual pinch scale,
default full-fingertip live geometry, optional recorded two-index measurement,
nine lab extensions, construction tools, preferences,
accessibility fallbacks, lifecycle handling and source packaging.

Actual executed checks during implementation:

- Latest contextual-guide/workspace update: **21 focused guide/UI tests** and
  **2 additional ten-tip layout-reprojection cases** pass within the full suite.
  Guidance tracks all nine labs/presets, LIVE/RECORDED/LEGACY, WORLD/HAND and UI
  ownership. Tests exercise persistence, exclusive panels, enlargement/restoration,
  recorded-work preservation, native scroll/shortcut handling and hidden-list hits.
- Final guide/workspace QA: **270 OpenGL + 270 software** synthetic captures in
  `runs/lab-guide-workspace-{gpu,software}-delivery/`: nine labs × two views ×
  three logical sizes (1040×680, 1280×720, 1600×900) × five states (guide visible,
  hidden, expanded, expanded with help, restored). Uses actual synthetic 21-point
  hand inputs for ten LIVE vertices; asserts complete counts, native GPU context,
  requested capture sizes, visible controls and enlarged viewport width.
  App source hashes and per-image hashes are recorded in manifests. Representative
  small-window normal/expanded images were inspected; this is not physical testing.
- Latest delivery rebuilt and hash/CRC verified **246 source/resource files**
  including the model. Extracted Qt/resources/actual blank-image model smoke and
  **all 909 tests** passed with the separate existing dependency environment at
  `runs/releases/extracted-v2-lab-guides/`. This is an extraction verification,
  not a new clean dependency installation. Physical acceptance stays deferred.

- Full regression: **909 passed** (`python -m pytest -q --tb=short`).
- Product tests: **354 tests** in the passing full regression, including independent safety/math, actual
  21-landmark pose fixtures, GUI, adapter, lifecycle and packaging checks.
- Native Qt shell initialization and software rendering: passed.
- Software QA: 66 synthetic surfaces at requested 1280×720 and 1600×900 logical
  desktop sizes. QOpenGLWidget QA: 66 synthetic surfaces covering seven pages,
  nine labs in WORLD/HAND and all eight Evidence selections. HiDPI screenshots
  use physical pixel dimensions; manifests record logical window sizes.
- Earlier full-fingertip LIVE QA: 24 native GPU and 24 software synthetic surfaces
  in `runs/live-fingertip-qa-{gpu,software}-final/`. Covers 1, 2, 3, 4, 5 and 10
  active tips, including a pinky-only/support hand, both view modes and requested
  1280×720 / 1600×900 logical sizes. Native context and complete semantic vertex
  counts were asserted. No webcam opens in this QA.
- Previous extension/3D audit: **232 GPU + 232 software** synthetic surfaces in
  `runs/extension-3d-audit-{gpu,software}-final/`: all 29 presets, both view modes
  and 1/3/4/10-tip inputs. Assertions cover complete tip counts, closed topology
  for noncoplanar input and real native GPU context. Final manifests include
  product profile and source hashes; representative images were inspected.
  Additional native QA captured 24 layout surfaces at requested 1280×720 and
  1600×900, plus 82 navigation/RECORDED/evidence/failure-state surfaces. These
  are synthetic captures, not physical success rates. Details: `EXTENSION_3D_REVIEW.md`.
- Actual MediaPipe two-hand model initialize, blank synthetic-image inference
  and close: passed, without opening a webcam. This proves model execution,
  not successful detection of physical hands.
- Compilation, dependency consistency, new-source formatting and Git whitespace
  checks: passed. The default native QOpenGLWidget context was checked valid.
- Source archive tests verify ZIP CRC, per-file hashes, essential resources and
  exclusion of environments/private session data. The local archive includes the
  separately supplied official model, with its documented checksum verified.
- Extracted archive native UI/resources/model smoke and full regression passed
  using the existing dependency environment. On 2026-10-03, the supplied
  `setup_v2.ps1` also created a fresh environment inside the extracted package
  and installed `.[dev,product]` successfully. In that fresh environment,
  **628 tests passed**, dependency consistency passed, and native UI plus actual
  blank-image model inference/cleanup passed. No webcam was opened. This verifies
  the tested Windows/Python installation, not other operating systems or a
  standalone executable. The final source archive is under `runs/releases/`.

Protected-tree verification: `git diff --name-only g7-final -- src/dip_touchless
config/default.yaml experiments/final analysis FINAL_REPORT.md submission/evidence`
returned no changes. Peeled tag commits remain:

- `g7-final`: `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- `dip-touchless-stem-v1.0`: `2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`.

Engineering delivery status by blueprint phase:

| Phase | Status |
| --- | --- |
| P0 freeze / product branch | Complete; original tags preserved |
| P1 native product shell | Implemented and native render checked |
| P2 one-hand intent / ownership | Implemented; synthetic safety tests pass |
| P3 session calibration | Implemented; reference/dwell/rearm tests pass |
| P4 Coordinate / Molecule / Orbital | Migrated to the V2 API; preset tests pass |
| P5 shared hand anchor | Implemented; native synthetic HAND render checked |
| P6 two-hand processing / scale / measure | Implemented; actual model no-hand smoke and synthetic behavior pass |
| P7 new educational extensions | Implemented; all nine labs/presets checked |
| P8 hardening / fallback / cleanup | Implemented; GUI/lifecycle tests pass |
| P9 automated validation | Passed for tested synthetic invariants |
| P9 physical usability acceptance | Deferred by user; unmeasured |
| Source package / guides / RC identity | Local delivery prepared; no remote publication |

Structured physical usability acceptance: **NOT RUN / DEFERRED BY USER**. Blueprint
P9 percentages and false-activation rates are unmeasured. Its physical gate is
not passed. Synthetic safety invariants are covered, but do not establish those
physical outcomes. No commercial or production-readiness claim is made.
The user's later screenshot and recorded hand observations were used to diagnose
HAND defects; they do not constitute a labeled physical acceptance evaluation.

The delivery is a local release candidate source package, not a remote publication
or a standalone executable. Both original Git tags remain immutable. Source
changes are reviewable in the working tree; no commit/tag/push is required to
run this package. `PACKAGE_MANIFEST.json` records file hashes for the archive.

Continuation checks on 2026-10-03 cover modal cancellation/rearm in the real GUI
consumer, native input retaining typed digits, mouse ownership during ongoing
synthetic camera frames, independent manual/gesture commit IDs, identical pointer
gain/mirror for both measurement endpoints, WORLD/HAND cursor-picking agreement
and rejection of partial out-of-scene pair commits. Modal cancellation also
works without camera frames. The new 66-surface OpenGL QA explicitly checks a
valid QOpenGLWidget context, and the Molecule HAND capture was visually inspected.
No webcam was opened.

Progress accounting: count P0-P8 as nine gates, P9 automated verification as one
gate and P9 physical usability acceptance as one gate. Ten of eleven gates are
complete: **90.9%, with 9.1% remaining**, solely the deferred physical gate.
For the user-authorized engineering scope that excludes physical testing, ten
of ten gates are complete: **100%, with 0% implementation gates remaining**.
These are equally counted task gates, not code coverage, measured gesture success
percentages, workload estimates or claims that future defects are impossible.

Camera startup correction after the user's report on 2026-10-03:

- Root cause: an unsupported `presentation_consumer` keyword supplied to the
  frozen `_build_runtime` factory. Earlier mocked-factory tests and model/UI
  smoke did not exercise this integration and missed it.
- Fix: the worker's controller implements `consume_presentation`; the factory
  signature and frozen runtime/Core remain unchanged. PRODUCT and LEGACY tests
  now run the real factory, preprocessing, runtime and logger, mocking devices
  only. Startup failures remain visible in Analyze and header after cleanup,
  with traceback records under the product run directory when writable.
- Actual physical camera check: V2 Start/Stop, camera 0, run
  `stem-v2-20261003-004440-362832`. Five distinct GUI-presented frames were
  sampled, camera opened successfully and clean shutdown passed. No images or
  video were stored. The local record is
  `runs/product-v2/camera-smoke-20261003-004443.json`.
- All samples reported `NO_HAND` and zero product hands. This validates live
  camera integration only; real hand anchoring, pinch/role accuracy and P9
  gesture usability remain unvalidated. Earlier “no webcam opened” entries
  refer to the automated checks before this explicitly scoped camera run.

3D/UX/environment follow-up on 2026-10-03:

- Actual GPU framebuffer occlusion passed: a near blue sphere occludes a far red
  sphere even when the far one is drawn last. The test did not skip on this machine.
  Mesh positions/normals, perspective/plane roundtrip, display/clip-matrix agreement,
  clipping and sphere picking are tested. Surface has filled triangle faces;
  native rendering uses depth testing and illustrative lighting.
- Both GPU mesh QA and software QA rendered 66 synthetic surfaces each after the
  renderer/UX changes; Surface was visually inspected. QA explicitly verifies
  a mesh renderer and valid context. Software primitive occlusion is approximate.
- Tools are hidden until requested; construction/polygon actions are contextual,
  availability is explicit and layout changes cancel active manipulation.
  Inspect cannot commit measurements; completed constructions remain undoable
  after returning to Inspect. Dwell selection requires a new full dwell window
  after invalid tracking or timestamp gaps; notices also cancel a clutch before
  changing viewport height.
- Detector budget is three, interaction accepts at most two. Tests verify third
  detected hand rejection, filter clearing and neutral reacquisition. This does
  not prove all extra hands are detected or that multiple people can safely interact.
- Low-light guidance derives from actual illumination state. Real dark-room hand
  detection/gesture performance is unmeasured. No fabricated confidence is used.
- Camera 0 Start/Stop passed again with the new detector budget in run
  `stem-v2-20261003-011005-330547`, local record
  `runs/product-v2/camera-smoke-20261003-011008.json`. Five GUI samples all showed
  NO_HAND; clean shutdown passed, raw video was not saved.
- Enterprise readiness and optimal user-task UX are **not established**. This
  local RC has not demonstrated a device/environment/user acceptance matrix.

Full UI/function audit on 2026-10-03: see `UI_AUDIT.md` for the complete findings,
seven-page/nine-lab coverage, fixed defects, necessary local utilities and remaining
limitations. Full suite passed **682 tests**, including **127 product tests**.
New negative-path checks cover hidden-page/native-key ownership, stale calibration,
missing HAND anchor, journal IO failure, stale status and late GPU fallback.
Educational checks cover Rectangle/grid snap, lens rays, 3D electric radius,
zero-vector projection and crystal sites. Delivery verification checks manifest
hashes/member paths before executing extracted source; this is not a digital signature.
GPU and software audit captures each contain 82 synthetic surfaces under
`runs/v2-qa-audit` and `runs/v2-qa-audit-software`. No new camera run was needed.

Final audit delivery verification: 237 source/resource/model files were verified
in the rebuilt RC archive. Extracted UI/resource/model smoke and all **682 tests**
passed using the separately installed environment from the earlier fresh setup.
Final Black check, compileall and installed-environment pip check passed.
The archive remains local source delivery; no standalone executable, commit,
release tag or remote publication is claimed.

Repeated-request second audit: new isolated tests reproduced HAND mouse takeover
clearing its own anchor, a stuck manual clutch after anchor loss, partial CSV
overwrite, and accepted noncanonical/reserved Windows package paths. All are
fixed; actual loss/reference/context resets still clear presentation. Full suite
passed **697 tests**, including **142 V2 tests**. Prior 682-test/package checks
above describe the first audit revision. No new camera/physical-hand run was made.

Second-audit RC verification: 238 files verified in the rebuilt source archive;
extracted UI/model smoke and all 697 tests passed in the separate dependency
environment. Black, compileall, pip check and diff whitespace checks passed.
Protected G7/Core/evidence paths have no diff and `g7-final` still resolves to
`f454c6b8325c85199c0122c0e822fe8e76c1526c`.

User-reported HAND fix: full regression **749 passed**, product suite **194 passed**.
New checks cover all nine labs and eight construction tools, single-hand live
anchor continuity, HAND two-pinch scale, camera-aligned source pairs retained
through pinch motion and automatic Inspector expansion, explicit UI ownership,
relative-3D finger bends, and actual classifier-to-GUI cursor pixels across layout
changes. Native QA rendered 82 synthetic surfaces in `runs/v2-hand-fix-qa`.
Recorded user landmarks were inspected and two snapshots replayed on blank images
in GPU/software, with synthetic timing and no original camera image. Diagnostic
and captures: `runs/hand-fix-validation/report.json`. Cursor/preview alignment was
checked; no physical accuracy or acceptance rate follows from this replay.
Product schema is product-v2-3; frozen Core/G7 semantics are unchanged.
HAND-fix source delivery: rebuilt archive contains 238 verified source/resource/
model files. Extracted native UI/model smoke and all 749 tests passed using the
separate environment installed during the earlier fresh setup. Black (38 files),
compileall and pip check passed. No camera, staging/commit/tag/push was performed.

Latest direct-follow LIVE correction: **863 full-suite / 308 product tests passed**.
The new 114 tests cover every nonempty finger subset in either role, one to ten
actual classifier-to-GUI vertices in WORLD/HAND, pinky motion/folding, support-only
input, all-nine-lab rendering, loss/empty tips/context/UI/modal cleanup, visual
depth round trips, concave outline surfaces, old-preference automatic defaults,
RECORDED switching and scene-only CSV snapshots. Native GPU/software each captured
24 synthetic surfaces in `runs/live-fingertip-qa-{gpu,software}-final/`; representative
images were inspected. Source semantics are versioned as product-v2-4.

Delivery verification: rebuilt archive has **242 verified source/resource/model
files**. Extracted native UI/resources/actual blank-image model execution and all
**863 tests passed** in `runs/releases/extracted-v2-live-fingertips/`, using the
separate dependency environment installed during the earlier fresh setup. This
turn did not reinstall dependencies. Black (42 source/test files), compileall,
pip check and Git whitespace checks passed. Protected Core/G7/evidence diff is
empty and both peeled release tag commits remain unchanged. No webcam was opened;
physical acceptance remains deferred. No staging/commit/tag/push was performed.

Extension/UI 3D audit: **886 full-suite tests passed**, including the collected
**331 product tests**. Targeted new audit module: **23 passed**. Fixes include
closed convex geometry with manifold/outward/volume tests, LIVE vector inputs,
missing-pair safety, mode-switch orbit, stable labels/probe, model-preserving
wire overlays, prioritized lab Inspector information, renderer/dimensionality
captions and NIST-referenced NH3 angle. Source semantics are product-v2-5;
frozen H2O/CH4, Core/G7 and original tags remain unchanged. Tests, source review
and synthetic captures establish checked software behavior only; physical
hand quality, UX optimality and enterprise readiness remain unproven.

3D-audit source delivery: **244 files verified** in the rebuilt model-inclusive
archive. Extracted native UI/resources/actual blank-image model smoke and all
**886 tests passed** in `runs/releases/extracted-v2-extension-3d/`, using the
separate dependency environment installed during earlier setup. This turn did
not reinstall dependencies. Compileall, pip check, Black and whitespace checks
passed. Source hashes in final all-preset manifests identify the checked app.
No webcam, staging, commit, push or tag action was performed.
