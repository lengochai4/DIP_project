# V2 source delivery and verification — 2026-10-03

Identity: `2.0.0rc1` on `feat/v2-product-rebuild`, based on v1.0 commit
`2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`.

Implementation includes the new native frontend, all seven navigation pages,
four-gesture semantic pipeline, session calibration, shared WORLD/HAND projection,
separate two-hand product processing, exclusive routing, bimanual pinch scale,
two-index measurement, nine lab extensions, construction tools, preferences,
accessibility fallbacks, lifecycle handling and source packaging.

Actual executed checks during implementation:

- Full regression: **630 passed** (`python -m pytest -q --tb=short`).
- Product tests: **75 passed**, including independent safety/math, actual
  21-landmark pose fixtures, GUI, adapter, lifecycle and packaging checks.
- Native Qt shell initialization and software rendering: passed.
- Software QA: 66 synthetic surfaces at requested 1280×720 and 1600×900 logical
  desktop sizes. QOpenGLWidget QA: 66 synthetic surfaces covering seven pages,
  nine labs in WORLD/HAND and all eight Evidence selections. HiDPI screenshots
  use physical pixel dimensions; manifests record logical window sizes.
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

Physical camera interaction/usability: **NOT RUN / DEFERRED BY USER**. Blueprint
P9 percentages and false-activation rates are unmeasured. Its physical gate is
not passed. Synthetic safety invariants are covered, but do not establish those
physical outcomes. No commercial or production-readiness claim is made.

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
