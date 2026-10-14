# 05 — Project Status and Roadmap

## Current task update — 2026-10-14

Chemistry AR continuity refinement: inspected actual UI session diagnostics
and removed unnecessary panel rebuilds triggered by atom hover or graph changes.
Only visible content/button highlights invalidate that texture; semantic changes
refresh immediately. A lightweight PinchGate shares raw pinch/hysteresis/loss
semantics with GrabController but omits unused pose/orientation work; actual held
component movement still uses GrabController. No gesture thresholds, Core
equations or report results changed. Tests cover gate equivalence during opening,
brief loss/generation/discontinuity and panel reuse/content refresh. Executed:
200 submission tests, 654 full tests passed; actual GL check ran 180 synthetic
frames with one/two-hand group hold and visible opening, finite bounded poses,
and one static compact-panel texture upload. This is engineering regression
evidence, not a measured physical hand latency/smoothness improvement.

Expanded chemistry library: user-authorized 32 neutral covalent presets in four
pages of eight entries. Graphs/finite illustrative coordinates are validated at
startup. Formula and exact element/bond-order matching distinguish ethanol from
dimethyl ether and remain independent of atom IDs or position. Candidate pruning
and a bounded topology cache replace factorial permutation enumeration. Semantic
changes refresh names/labels immediately. Finger presentation clears invalid or
misindexed observations instead of retaining vertices. Core/research parameters,
atomic data and report results are unchanged. Executed: 196 submission tests,
650 full-project tests passed; all 32 presets rendered with native event polling
and forced GC; four pages/targets checked and representative screenshots inspected.
Sources/limits are recorded in submission/stem_ui/data/README.md. No physical
reaction, energy, depth or new real-camera accuracy result is claimed.

Startup crash correction: the borrowed Pygame SDL Window wrapper is now owned
by the renderer until display replacement/close. Pygame 2.6.1 registers its
raw pointer as SDL window data; allowing the wrapper to die before event polling
caused a native access violation. Reproduced in the normal idle app, fixed with
a persistent reference, and verified with a real event loop under forced GC
and repeated F11 transitions. A subprocess regression now checks exit status,
event polling and restore after native fullscreen. Full suite: 580 passed.
Normal app launch was checked; Windows reports the window responding.

Submission source convenience: the small DroidCam control now opens direct
Wi-Fi settings (phone IP + port, default 4747) and uses DroidCam's HTTP
`/video` feed. The last valid endpoint is stored locally for reuse. Switching
between local webcam and DroidCam is serialized so the current capture worker
must finish closing before the requested source starts. Only the presentation
live FrameSource changes; Core preprocessing/tracking/filter/gesture,
ReplayRuntime and frozen report results are unchanged. Verification: direct
endpoint/FramePacket/error-path tests pass; an app-level webcam -> DroidCam ->
webcam test fails on any overlapping live worker and currently passes. Final
Latest audit also covers delayed camera closure, cancel/quit during switching,
corrupt saved preferences/workspaces, save failure, existing-bond selection,
modal input suspension and live network bursts sharing one detector millisecond.
Final regression: 125 submission tests and 579 full-project tests passed.
Actual renderer check: 90 synthetic frames across three window sizes/modes,
modal scene freeze, fullscreen button path and F11 restore passed; screenshots
inspected. A reported fullscreen defect was reproduced from offset (280,180):
desktop fullscreen now reaches origin (0,0) at 1920x1200 on this monitor and
restores (280,180) at 1360x860. F11 and queued resize regression checks pass.
Two recorded-source MediaPipe runs processed 30 frames each in tips/chemistry,
observed two hands/up to ten tips and stopped without error. A loopback HTTP
MJPEG stream produced three real OpenCV/FFmpeg frames
with valid BGR shape and increasing timestamps. A physical phone Wi-Fi session
was not measured. `git diff --check` is clean. Checklist is recorded in
`submission/stem_ui/QA_CHECKLIST.md`; Core/report results remain frozen.

Quick user-requested correction: fingertip framing now uses a configured fixed
scale and whole-hand centering, avoiding inverse small-tip-span magnification
when fingers fold or identity reacquires. Chemistry dwell default is 1 second;
the panel label reads the resolved setting. Canonical change: 02/5; modules:
submission renderer/settings/chemistry_view and tests. Presentation only;
Core/report results unchanged. Full suite 566 passed; explicit test confirms
selection at one second and no earlier activation.

Latest reported defect fix: aliased/blurry rendering, delayed chemical release
and extra fingertip vertices. Change: immutable HandView adds validated raw
landmarks beside filtered motion landmarks; UI pinch/extension use raw input,
opening freezes before timed release. Reach guards exclude straight segments
folded back toward the palm. Live surfaces/hulls retain observed vertices only;
no prism extrusion or default skeleton joint markers. Renderer requests MSAA
with context-error fallback, DPI-aware windows, cached supersampled cards/logo,
native-sized panel glyphs and mipmap/anisotropy. Stable chemistry overlays reuse
their texture. Reason: user's reported live defects. Canonical section: 02/5;
code: submission runtime/manipulation/geometry/renderer/chemistry_view/theme/
app/settings and submission tests. Algorithmic impact: presentation only;
canonical Core gestures/filter equations unchanged. Experimental impact: UI
schema 6 identifies raw discrete-state basis and observed-only vertices;
actual renderer samples are diagnostics. Compatibility: UI HandView raw tuple
is optional for older synthetic fixtures. Tests updated for observed-only
near-planar faces and quicker release; new cases cover delayed filtered release,
two-to-one-hand rebase, 0–10 vertices and backward-folded fingers.
Existing results invalidated: no; Core/report/baseline profiles untouched.
Executed: 111 submission tests, 565 full tests passed. 76-frame synthetic GL
acceptance verifies raw opening while filtered points stay closed, two-tip
nodes, overlay reuse and injected context-failure fallback (actual default
4 samples, fallback 0). 139-frame window/interaction and 697-frame chemistry
graph regressions reran. Provider replay 60 frames observed 2 hands/up to 10
tips and stopped cleanly (ui-20261014-175453-431303). Screenshots inspected.
No new live session or physical latency/FPS claim.

Current authorized refinement completed: visual refresh from the user's
submission design/assets, exact author badge, responsive glass/cyan/gold UI,
sharper lit atoms, chemistry 3-second observed hover confirmation and close
pinch manipulation. Per latest user instruction, processing/performance
telemetry is omitted from the product UI. Controls/functions remain available.
Follow-up chemistry feedback is addressed by separate pinch hysteresis/loss
grace, entering a target with an already-confirmed grip, render-rate cursor
following, second-hand free-space join for whole-component scale/rotation,
electron selection volume and shared object/electron scale. Framing includes
electron-shell extents. Progress is rendered directly in GL without texture
reuploads. Fullscreen button/F11/Esc restore dimensions/context resources.
Canonical changes: 02 section 5; no algorithm/baseline/protocol changes.
UI metadata schema 5 logs actual dwell/claim/group diagnostics; research
schema, G7/ROUND2 data, report and Core code/config remain unchanged.
Executed validation: 96 submission tests, full suite 550 passed. Synthetic
OpenGL acceptance 697 frames covers palette/graph/history/window regression;
additional 139 frames cover dwell progress, two-hand electron-atom resize,
short-loss freeze/rebase, button/F11/Esc in all three modes and layouts at
960x660, 1360x860 and 1920x1080. Screenshots were visually inspected. Actual
provider replay processed 60 mirrored two-hand-fixture frames, observed
2 hands/up to 10 tips and stopped cleanly (ui-20261014-173237-405165).
These are recorded/synthetic validations, not new live operator validation,
physical latency/FPS evidence or VR/commercial certification.

Camera chemistry demonstration (current authorized addition):

Change: isolated camera-composited mode with perspective spatial panel,
hover/confirmed-pinch targeting, full offline 118-element palette, lit atoms,
neutral-atom electron-shell illustration, limited neutral covalent bond
editing, component manipulation and history/local save/load. User clarified
that both atomic and molecular views are wanted, with molecules prioritized.
Reason: user requested VR-inspired creation/manipulation directly on camera.
Canonical file/section changed: 01 section 7 and 02 section 5; 03 unchanged.
Code/modules affected: submission camera_space/chemistry/chemistry_input/
chemistry_view plus renderer/app/settings, tests and source documentation.
Algorithmic impact: application-only picking/editor semantics; no Core
provider model, equation, baseline config or research gesture changes.
Experimental impact: UI schema 4 captures molecular graph and atomic-data
file SHA. No camera-relative/physical atomic lengths or reaction results.
Compatibility impact: UI adds chemistry mode; one-hand Core contracts and
ReplayRuntime stay unchanged. Existing UI workspaces use validated schema 1.
Existing results invalidated: no; G7/ROUND2 source/config/results unchanged.
Primary data: PubChem periodic-table JSON snapshot, 118 rows with preserved
electron configurations. Direct local download returned NCBI block HTML;
that HTML was discarded. All 2,505 web-readable JSON lines were captured,
parsed and normalized, then all neutral electron totals validated against Z.
IUPAC supplies the table reference; conservative covalent rules/reference
graphs are documented with OpenStax sources. No isotope/neutron guesses.
Templates have illustrative scene-unit coordinates, not optimized geometry.
Recognized molecular names require graph matching, not formula alone.
Scope limits: no world localization, real hand/object occlusion, metric
camera depth, force fields, quantum orbital or reaction simulation.

Fingertip refinement: profile inspection of 90 synthetic render frames
identified repeated per-bone NumPy operations; batched orthonormal frames
replace those calls. Bounded error-adaptive display following improves
large-move response without predicting absent observations. Core filtering
and existing experiment profiles are unchanged. No measured physical latency
or FPS improvement is claimed from this profiling run.

Executed chemistry checks: 33 targeted tests, 83 submission tests and
full regression suite 537 passed. Existing manipulation/window controls
also re-executed successfully. Synthetic
OpenGL acceptance completed 179 frames: spatial palette selection, three
spawns, H2O topology construction, atom separation, undo, full periodic
table, resize and fullscreen restore. Actual provider replay on the existing
mirrored two-hand fixture observed 30 frames / 2 hands / up to 10 tips in
chemistry mode (ui-20261014-164451-017213), clean shutdown. This is recorded/
synthetic-source evidence, not new live operator chemistry validation.

Spatial/freshness refinement (following the continuity fix):

Change: live-only single-slot acquisition, bounded error-adaptive display
following, smoothed illustrative palm z, two-hand palm tilt plus baseline
twist, explicit one-hand push/pull, nonplanar fingertip 3D convex hull with
fitted-plane display-prism fallback, volumetric hand joints/bones and stable
session framing. Reuse overlay surfaces/textures and cache preview thumbnails;
overlay refresh and render following run at independent configured cadences.
Sphere poles were corrected to closed, nondegenerate faces; sphere uses
smooth lighting without the dense wire grid. Floor shadows are display cues.
Reason: user reported flat fingertip geometry and lingering delay.
Canonical file/section changed: 02 section 5 presentation boundary.
Code/modules affected: submission/stem_ui acquisition/runtime/manipulation/
geometry/renderer/app/settings and submission tests.
Algorithmic impact: UI only; Core x/y filtering and model z pass-through
contracts remain unchanged. Dropped live packets keep original times/IDs.
Experimental impact: UI schema 3 identifies latest_camera_single_slot vs
ordered_replay and logs actual dropped packets/queue wait. Rotation, mesh mode
and CPU draw cost excluding swap/frame cap are presentation diagnostics.
Compatibility impact: submission behavior/config/schema changed; no public
Core contract change. Replay and baseline configs remain unchanged.
Existing results invalidated: no; no G7/ROUND2 code/config/data changes.
Tests added/updated: acquisition ownership, newest-packet delivery, buffer
copy, explicit failure/stop/blocked driver, convex support faces, tilted plane,
interior nodes, closed sphere, out-of-plane two-hand tilt, push/pull,
default depth neutrality, bounded following and non-mutating display z.
Executed: 50 submission tests and full regression suite 504 passed. Mode
cycling explicitly reaches all four manipulation modes. The new camera pump opened the physical
webcam, delivered 12 observed snapshots and stopped cleanly without operator
actions (ui-20261014-160021-783314). Real provider replay on the mirrored
two-hand fixture rendered 60 observed frames / 2 hands / up to 10 tips
(ui-20261014-155909-732680). Synthetic OpenGL acceptance exercised 130 frames
with out-of-plane tilt, push/pull, 3D fingertip hull and fixed framing; existing
205-frame manipulation and window controls checks also passed. Screenshots
were inspected. These checks do not certify all live physical hand poses,
physical depth, sensor-to-photon latency or equivalence to VR headsets.

Active refinement: the user reported intermittent grab and failed size
changes, requested XR references and functional smoothing fixes. Inspection
found immediate slot/filter resets on any missing frame, frame-source-only
pose advancement, no anisotropic stretch, and unclear two-grip feedback.
Change: bounded presentation-only loss/grip state, target/render smoothing
separation, uniform/apparent-size/axis-stretch manipulation and live feedback.
Canonical owner: 02 section 5 presentation refinement; baseline 03 untouched.
Code: submission/stem_ui only plus its tests/docs. No research algorithm,
profile, replay, metric or old result changes; no existing result invalidation.
Executed refinement checks: 33 submission tests and full suite 487 passed.
Synthetic renderer acceptance drove 205 frames through OpenGL, asserting
uniform enlargement/shrinkage, axis stretch and short-loss pose freezing.
Recorded dynamic one-hand source smoke observed 60 frames / up to 5 extended
tips (ui-20261014-152637-862737); mirrored two-hand source smoke observed
60 frames / 2 hands / up to 10 tips (ui-20261014-153038-147730). Both closed
cleanly. All four solid types, help/camera visibility and fullscreen restore
were exercised again. These are synthetic/recorded-source checks, not new
simultaneous physical two-hand manipulation validation.

UI_INTERACTION resolves presentation filter overrides from settings.yaml:
adaptive base/minimum cutoff 2.5 Hz, beta_base 0.6, beta_max 4,
velocity_gain 1.2 and final maximum cutoff 15 Hz. Public filter equations are
unchanged. These are engineering UI defaults, not claimed measured optima;
the frozen F2 experiment profile and report measurements remain unchanged.
UI schema 2 logs per-hand generation/pinch ratio and application grip/pose
states so future reported failures can be inspected without raw recording.

Core/report source was committed as c79abbc and pushed on
feat/submission-round2. The user now authorized the final clean UI task on
feat/submission-ui-clean. Existing UI branches remain untouched. Direction:
minimal 3D object interface, automatic live extended-fingertip geometry for
one/two hands of one operator, optional camera view, fullscreen and hideable
guidance. The user then prioritized functional correctness and responsive
one/two-hand interaction inspired by VR grab behavior over visual polish.

Executed UI verification: 18 new automated tests, full suite 472 passed.
Physical camera opened, processed 10 frames and stopped cleanly without
requiring new operator hand actions (ui-20261014-144142-466858). Real recorded
one-hand source smoke rendered both live geometry and solid modes. A
synthetic mirrored two-hand fixture was processed by the real provider,
rendering 2 hands / up to 10 extended fingertips over 60 observed frames
(ui-20261014-143939-582158). This is not simultaneous physical two-hand
pose validation. Hide/show help/camera, all four solids, resize and fullscreen
restore were executed. Exclusive fullscreen failed on this Windows display;
desktop-sized borderless mode replaced it and the controls smoke passed.

Change: additive submission presentation scope and snapshot boundary.
Reason: user requested all fingertips/two hands and a clean 3D submission UI.
Canonical sections: 01 section 7, 02 section 5; research algorithms unchanged.
Modules: submission UI composition/runtime and renderer, outside src.
Algorithmic impact: existing Core components reused without modification;
presentation provider max two hands and slot association are demo behavior.
The renderer's separate grab controller uses pinch engagement, one-hand
local palm orientation and x/y translation; two-hand midpoint/span/twist
control position/scale/rotation. Identity/count changes rebase without snap.
This is application behavior, not a replacement for the canonical gesture
mapping or a new research comparison. Display pose smoothing is UI-only.
Experimental impact: separate UI run identities; no new RQ1/RQ2 result.
Compatibility impact: no existing public Core contract or logger changes.
Tests: coordinate/mirror mapping, fingertip selection, identity/loss safety,
mesh geometry, worker lifecycle and recorded-source UI smoke.
Existing results invalidated: no; research code/config/replay unchanged.

ROUND2 collection: six planned normal-light sources were completed, along
with two intended challenging-light sources. The operator then confirmed
that ambient illumination could not be reduced. Those two sources remain
retained, but their physical challenging-light condition is unverified.
The guided session was interrupted before the ninth source.

The user explicitly authorized simulated input dimming. The completed study
is separately identified under `experiments/round2/SIMULATED_PLAN.md`:
three fixed-gain (0.35) derivatives of the three static normal sources,
with the same canonical v1.2 primary metrics/profiles and fixed window.
No synthetic attenuation result is described as real environmental
low-light robustness. All three normal and simulated B trials returned
P0=P1 valid rates of 1.0 on 241 analyzed frames each. P1 was NORMAL with
CLAHE inactive on all 723 normal frames, and DIFFICULT with CLAHE active
on all 723 simulated frames. This validates activation, not improved
valid rate or physical low-light robustness.

Change: supplemental source-condition protocol, authorized 2026-10-14.
Reason: physical lighting control unavailable.
Canonical impact: no algorithm/interface/baseline/metric changes; this
is an explicitly documented supplemental image-domain condition under
the experiment evidence/disclosure rules of docs/00 and docs/03.
Code: experiments/round2/simulated_study.py and its tests.
Experimental impact: new simulated-source identities and hashes; separate
from G7 and from the interrupted real-lighting session.
Compatibility impact: Core and old logs unchanged.
Existing results invalidated: no; old evidence is retained with its actual
limits, and no physical low-light claim is inferred from simulated data.

The old `.venv` references a missing Python 3.11 executable. A separate
Python 3.12 research environment was installed; its actual package versions
are recorded for ROUND2. The unmodified main baseline passed 433 automated
tests in this environment on 2026-10-14. Model SHA-256 matches the retained
G7 model. This is engineering verification, not experimental superiority.

The first static sources contained substantial real hand movement and are
retained as acquisition-quality evidence. The user authorized three new
supported-wrist static trials, preregistered before collection under
`experiments/round2/HELD_STATIC_PLAN.md`. All three A1 and A2 trials have
241 common usable frames. F1/F2 reduce A1 radial RMS versus Raw in two
held trials and increase it slightly in trial 001; F1/F2 are nearly equal.
F2 A2 RMSE versus Raw is lower than F1 in all three dynamic trials. Raw
is not ground truth and this metric is not physical latency.

The final research tooling suite passed 454 tests. Core algorithm/config,
public contracts, old experiments/analysis and G7 evidence remain unchanged
from main/g7-final, f454c6b8325c85199c0122c0e822fe8e76c1526c. The decision is
to freeze that Core for the course submission: no algorithm upgrade is
justified as a prerequisite by this round. This is not enterprise or
universal robustness certification. See `docs/CORE_SUBMISSION_DECISION.md`.

The updated report source is `reports/core-final/BAO_CAO_CORE.md`; the
editable deliverable is `output/documents/Bao_cao_Core_DIP_Touchless_STEM.docx`.
Raw videos, replay logs, plots and local analysis outputs remain local
experiment artifacts under runs and are not committed.

UI development follows the Core report and must preserve Core/Extension
separation. Any addition to a public rendering contract must be specified
with compatibility impact before implementation.

The retained G7 release and experimental artifacts are not overwritten.
The evidence snapshots below remain historical records; their older
NOT STARTED labels describe the 2026-09-28 pre-evaluation state, not the
current ROUND2 task. Later sections contain the actual retained G7 results.

## 2. Historical implementation evidence

As of 2026-09-28, the implementation repository has been verified
through Gate G6.

Verified evidence includes:

- canonical six-file specification set;
- Python package using the `src/` layout;
- clean virtual-environment installation through `pyproject.toml`;
- executable pytest test suite;
- project-owned domain enums and dataclass contracts;
- configuration loading with defaults/profile/explicit override precedence;
- semantic configuration validation;
- deterministic resolved-configuration serialization and SHA-256 identity;
- project-owned Core protocols;
- run metadata identity generation;
- machine-readable run logging;
- deterministic `ReplayFrameSource` with source-derived timestamps;
- `OpenCVCameraSource` with monotonic runtime timestamps;
- successful physical webcam smoke test;
- explicit BGR frame acquisition semantics;
- MediaPipe Hand Landmarker adapter isolated behind the project-owned `LandmarkProvider` contract;
- explicit BGR → RGB conversion at the MediaPipe provider boundary;
- successful real MediaPipe model loading and inference smoke test;
- project-domain `LandmarkObservation` output without MediaPipe objects leaking downstream;
- explicit unavailable measurement quality when no documented per-observation quality value exists;
- no use of handedness classification score as tracking confidence;
- safe `NO_HAND` behavior without fake zero landmarks;
- `MeasurementValidator` for project-domain observation validation;
- Raw/F0 landmark path with no temporal smoothing;
- pre-G2 `TrackingFrame` representation with unavailable ROI/illumination diagnostics represented by `None`, not fabricated measurements;
- `ReplayRuntime` connecting replay acquisition, provider, validation, Raw filtering, `TrackingFrame`, and `RunLogger`;
- machine-readable Raw frame and landmark logs;
- replay integration tests covering deterministic frame identity, timestamps, Raw output, no-hand behavior, logging, and resource release;
- successful end-to-end replay → MediaPipe → Raw → logger smoke test;
- automated G1 test suite executed successfully.
- deterministic normalized pinch ratio and pinch hysteresis;
- bounded/deadzoned renderer-independent rotation and scale commands;
- explicit neutral initialization, loss/reset, and reacquisition behavior;
- `GestureEngine` consuming filtered project-domain landmarks and producing `InteractionState`;
- ReplayRuntime interaction integration and interaction-state logging;
- renderer-independent `Stem3DSceneState` with bounded accumulated scale;
- optional Pygame/PyOpenGL 3D Extension with lazy graphics imports;
- Extension boundary tests confirming renderer/application modules do not import Core algorithm internals;
- synchronous `RealtimeRuntime` exposing the latest public `InteractionState`;
- visible synthetic OpenGL renderer smoke test;
- live webcam → preprocessing → MediaPipe → filter → gesture → `InteractionState` → 3D Extension integration;
- physical no-hand / hand-enter / hand-leave / hand-reacquire smoke test completed successfully;
- clean camera/provider/logger/renderer shutdown verified in the live demo;
- final G5 automated project suite passing with 378 tests.
- frozen G6 primary experiment protocol before final data collection;
- explicit F0/F1/F2 and P0/P1 experiment profiles;
- deterministic single-replay experiment entry point;
- manifest-driven paired batch execution preserving one replay source across compared conditions;
- immutable batch index preserving exact trial/profile/run/source identity;
- analysis loader consuming logger-produced metadata, resolved config, frames, landmarks, and events without manual raw-log editing;
- primary A1 radial RMS jitter metric on filtered landmark 8 in FRAME_NORMALIZED coordinates;
- primary A2 trajectory-deviation RMSE relative to F0 using common usable frame IDs;
- primary Experiment B valid hand-observation rate using VALID and REACQUIRED statuses;
- paired timestamp/frame alignment checks for comparative metrics;
- automatic CSV/table and Matplotlib plot regeneration from indexed run artifacts;
- generated-analysis provenance preserving batch identity, run IDs, analysis window, planned comparisons, exclusion rules, run code revision, config hash, model/source identity, and analysis code revision;
- SHA-256 capture for available local model and replay-source files;
- explicit unavailable checksum semantics when a referenced file is not available;
- no inferential statistics or optional performance benchmark added to the minimum course gate;
- final G6 targeted acceptance suite passing with 47 tests;
- final automated project regression suite passing with 425 tests.

G0–G6 are technically complete. Final controlled data collection,
final evaluation, report conclusions, and final research outcomes are
not claimed complete by this status.

## 3. Current stage

### Specification status

```text
CANONICAL SPECIFICATION: FROZEN FOR IMPLEMENTATION
```

The six canonical specification files remain the normative project source of truth.

### Implementation status

```text
G0 — BOOTSTRAP AND CONTRACTS: COMPLETE
G1 — RAW BASELINE + REPLAY: COMPLETE
G2 — DIP PREPROCESSING: COMPLETE
G3 — CANONICAL FIXED 1-EURO: COMPLETE
G4 — BOUNDED ADAPTIVE 1-EURO: COMPLETE
G5 — GESTURE + 3D EXTENSION: COMPLETE
G6 — EXPERIMENT READINESS: COMPLETE
G7 — FINAL EVALUATION / PACKAGE: NOT STARTED
```

G0–G1 completion establishes the engineering baseline:

```text
deterministic frame acquisition
→ provider isolation
→ explicit color conversion
→ project-domain landmark observations
→ safe Raw/F0 path
→ TrackingFrame
→ structured machine-readable logs
```

G0–G6 completion establishes the implemented Core, interaction-demo,
and reproducible experiment-tooling pipeline. It does not imply that the
project hypotheses are supported, that one method outperforms another,
or that final experimental claims have been validated. Those claims
remain dependent on the controlled final experiments in G7.

## 4. Current task

**Task G7 — Run the final controlled evaluation and package the submission.**

G6 experiment readiness is technically complete.

G6 completion evidence includes:

- primary A1/A2/B metrics frozen before final data collection;
- baseline-isolated F0/F1/F2 and P0/P1 profiles;
- deterministic single-replay execution;
- manifest-driven paired replay batches;
- immutable batch indexes preserving exact run identities;
- analysis loading directly from machine-readable run artifacts;
- common-frame paired metric alignment;
- radial RMS jitter implementation for A1;
- F0-relative trajectory-deviation RMSE for A2;
- valid hand-observation rate for Experiment B;
- automatic metrics CSV and plot regeneration;
- model and replay-source SHA-256 capture when files are available;
- resolved configuration, code revision, schema, dependency, system,
  model/source, and run identity preserved through run metadata;
- predefined exclusion rules preserved through batch and generated-analysis provenance;
- analysis provenance linking generated outputs back to exact run IDs,
  configs, source/model hashes, and analysis revision;
- no optional inferential statistics required or introduced;
- G6 targeted acceptance: 47 passed;
- final G6 full regression: 425 passed.

Key G6 implementation/evidence commits:

```text
f2b9cca docs: freeze g6 primary experiment metrics
cb2e285 feat: define g6 experiment profiles
2b9af8f feat: add deterministic experiment replay runner
53ad036 feat: add paired experiment batch runner
f67c7cb feat: add run artifact analysis loader
6e16d2b feat: add primary experiment metrics
bede648 feat: persist experiment batch index
edbd1a4 feat: regenerate experiment tables and plots
6f119e9 feat: capture experiment file checksums
78725b9 feat: preserve analysis provenance and exclusions
```

G6 completion establishes experiment readiness only. No final A1, A2,
or Experiment B metric outcome has been reported, and no superiority,
jitter-reduction, robustness, accuracy, FPS, latency, or statistical
claim is made from the G6 tooling tests. Final claims depend on the G7
controlled trials and their regenerated analysis.

G5 gesture mapping and the minimal 3D STEM Extension are technically complete.

G5 completion evidence includes:

- palm-width-normalized pinch ratio with strict hysteresis;
- bounded/deadzoned rotation and scale mapping;
- deterministic neutral initialization, loss/reset, and reacquisition;
- public renderer-independent `InteractionState`;
- `GestureEngine` using filtered project-domain landmarks only;
- ReplayRuntime interaction generation and logging;
- renderer-independent 3D scene-state accumulation;
- optional Pygame/PyOpenGL renderer;
- Extension/Core dependency-boundary tests;
- synchronous RealtimeRuntime with latest `InteractionState`;
- synthetic visible 3D renderer smoke;
- physical webcam → MediaPipe → Core → InteractionState → 3D smoke;
- verified no-hand, enter, leave, and reacquisition behavior;
- clean shutdown of runtime and renderer resources;
- final automated G5 regression suite: 378 passed.

Key G5 implementation/evidence commits:

```text
8435352 docs: freeze deterministic gesture semantics
0b978ba feat: add gesture configuration
f464c04 feat: add gesture math
ba7a2cd feat: add deterministic gesture engine
b5e2c1d feat: integrate gesture interaction into replay
55cc986 feat: add stem3d scene state
319c043 feat: add optional stem3d renderer
495587e feat: add visible stem3d smoke demo
7d88e9c feat: add realtime interaction runtime
eaa1c18 feat: add live touchless stem3d demo
```

Physical G5 smoke evidence:

```text
live run 1: 386 processed frames, clean shutdown
live run 2: 1141 processed frames, clean shutdown
manual acceptance: no-hand / enter / leave / reacquire / shutdown PASS
```

G5 completion demonstrates practical rendered interaction and safe runtime
behavior. It does not claim experimental superiority, accuracy, FPS,
latency, or final RQ3 research outcome.

G4 bounded adaptive 1-Euro is technically complete.

G4 completion evidence includes:

- frozen project-specific bounded adaptive 1-Euro semantics;
- speed derived from filtered per-landmark x/y derivatives;
- bounded velocity-dependent beta;
- optional quality-dependent minimum-cutoff primitive with no invented
  measurement quality;
- primary F2 baseline using `f_base` when quality adaptation is disabled
  or unavailable;
- independent final-cutoff bounds;
- project-specific independent per-landmark x/y adaptive state;
- model-relative z pass-through;
- shared F1/F2 timestamp, short-loss, long-loss, discontinuity, reset,
  and reacquisition semantics;
- public `ONE_EURO_ADAPTIVE` `LandmarkFilter`;
- deterministic frame-level adaptive diagnostics;
- validated adaptive configuration and engineering defaults;
- explicit filter-originated temporal events propagated through
  `FilterDiagnostics` and `TrackingFrame`;
- temporal reset/discontinuity events serialized to `events.csv`;
- ReplayRuntime integration for Raw/F0, Fixed/F1, and Adaptive/F2;
- acceptance coverage for beta bounds, cutoff bounds, monotonic beta,
  unavailable quality fallback, valid-quality minimum-cutoff
  monotonicity, extreme finite speed, invalid dt, long-gap reset,
  missing measurements, and reacquisition;
- full automated project suite passing with 290 tests.

Key G4 implementation/evidence commits:

```text
8884df1 docs: define bounded adaptive one euro semantics
877d17f feat: add bounded adaptive filter policy
958e3e4 feat: add adaptive one euro landmark core
e7be912 feat: share temporal semantics across one euro filters
2145739 feat: expose adaptive one euro filter configuration
5730abb docs: define temporal filter event propagation
3bbe8bf feat: expose temporal filter events
35aa24a docs: clarify tracking frame event serialization
2ddfd34 test: integrate adaptive filter replay logging
15a5a4f test: complete adaptive filter gate acceptance
```
G4 completion establishes the project F2 temporal baseline. It does not
claim that F2 outperforms F0/F1; that conclusion remains dependent on
future recorded experiments.
G5 followed G4 and preserves the Core/Extension boundary: gesture
processing consumes filtered project-domain landmarks, and the 3D
Extension consumes InteractionState rather than reaching into filter,
tracking, or preprocessing internals.


### G1 contract correction — LandmarkProvider input

Change:

`LandmarkProvider.process` accepts `FramePacket` instead of separate image/timestamp arguments.

Reason:

The previous signature could not preserve required `frame_id` identity and conflicted with the rule that the MediaPipe adapter owns explicit BGR → RGB conversion.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, Public interfaces.

Code/modules affected:

`core/interfaces.py`, tracking-provider adapter, runtime integration.

Algorithmic impact:

None.

Experimental impact:

None.

Compatibility impact:

Public interface corrected before final provider experiments existed.

Tests added/updated:

Provider tests verify frame identity, timestamps, and explicit BGR → RGB conversion.

Existing results invalidated:

No — no final provider experiment results existed before the correction.

### G1 contract correction — pre-G2 TrackingFrame diagnostics

Change:

`TrackingFrame.roi` and `TrackingFrame.illumination` may be `None` when the corresponding stages have not been executed.

Reason:

G1 requires a Raw `TrackingFrame`, while ROI and illumination processing are introduced only in G2. Fabricating zero-valued measurements would violate project evidence semantics.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, TrackingFrame contract.

Code/modules affected:

`core/contracts.py`, `RunLogger`, replay runtime integration.

Algorithmic impact:

None.

Experimental impact:

Pre-G2 development logs explicitly distinguish unavailable diagnostics from measured diagnostics.

Compatibility impact:

G2+ runs are required to populate ROI and illumination whenever the preprocessing stages are executed.

Tests added/updated:

Core contract, logger, and replay-integration tests verify explicit unavailable pre-G2 diagnostics.

Existing results invalidated:

No — no final G2+ experiment results existed before the correction.

### G2 algorithm decision — illumination state stabilization

Change:

Defined the baseline illumination-state decision using EMA-smoothed
`mean_v` and `robust_range_v`, with separate enter/exit hysteresis
thresholds.

Reason:

The canonical specification required `NORMAL`, `LOW_LIGHT`,
`LOW_CONTRAST`, and `DIFFICULT` states and required temporal stability,
but did not previously define the exact mapping from descriptors to
states.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Illumination assessment.

Code/modules affected:

`configuration`, `preprocessing/illumination_decision.py`, future
adaptive preprocessing/runtime integration.

Algorithmic impact:

Defines the course-baseline illumination classification and
stabilization behavior.

Experimental impact:

Future P0/P1 preprocessing runs must preserve the resolved threshold and
EMA configuration used for each run.

Compatibility impact:

No completed final illumination experiments existed before this rule was
defined.

Tests added/updated:

Configuration threshold-ordering tests and illumination
EMA/hysteresis/state-transition tests.

Existing results invalidated:

No — no final G2 illumination results exist yet.

### G2 semantic clarification — enhancement_active

Change:

`IlluminationMetrics.enhancement_active` is defined as whether CLAHE was
actually applied after preprocessing policy resolution.

Reason:

Illumination state and preprocessing policy are distinct. A difficult
illumination state may still be intentionally bypassed in P0/bypass
conditions.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Adaptive CLAHE.

Code/modules affected:

`preprocessing/illumination_decision.py`,
`preprocessing/adaptive_preprocessor.py`,
future runtime/logging integration.

Algorithmic impact:

Clarifies adaptive/always/bypass policy behavior.

Experimental impact:

P0/P1 logs can distinguish measured illumination state from actual
enhancement application.

Existing results invalidated:

No — no final G2 preprocessing experiment results exist yet.

### G3 algorithm clarification — landmark vectorization scope

Change:

Defined the fixed 1-Euro landmark vectorization as one independent x/y
2D filter vector per landmark. Each landmark derives one shared x/y
speed and cutoff from its own filtered x/y derivatives. Model-relative
z is passed through unchanged in the course baseline.

Reason:

The previous specification required a "shared speed" and "shared
cutoff" for landmark vectors but did not state whether sharing applied
within one landmark or across all 21 landmarks. Those interpretations
produce materially different filtering behavior.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Section 7.2 Project vectorization.

Code/modules affected:

Future fixed landmark 1-Euro core, temporal-filter wrapper, diagnostics,
synthetic tests, and adaptive filter extension.

Algorithmic impact:

Clarifies the project-specific vectorization layered on top of the
canonical scalar 1-Euro algorithm. The canonical scalar equations are
unchanged.

Experimental impact:

F1/F2 landmark filtering will use independent per-landmark x/y motion
rather than a concatenated all-landmark speed vector.

Compatibility impact:

No completed F1/F2 experiment results exist yet.

Tests added/updated:

Upcoming G3.4 tests will verify shared x/y cutoff within one landmark,
independence between landmarks, z pass-through, and preservation of
landmark identity/coordinate space.

Existing results invalidated:

No — no final fixed/adaptive temporal-filter experiment results exist.

### G3 contract clarification — frame-level filter diagnostics

Change:

Defined the scalar public `FilterDiagnostics` fields for per-landmark
vector filtering. Frame-level `speed` is the maximum per-landmark x/y
speed; `final_cutoff_hz` and `signal_alpha` come from the same landmark.
Ties use the lowest landmark index. Initialization and no-measurement
semantics were also defined.

Reason:

The public contract contains one scalar diagnostic set while the frozen
G3 landmark vectorization maintains independent speed/cutoff state for
each landmark. Leaving the mapping unspecified would make logs
ambiguous.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, `FilterDiagnostics`;
`03_ALGORITHM_AND_EXPERIMENTS.md`, fixed-filter diagnostics and common
loss/reset semantics.

Code/modules affected:

Fixed/adaptive LandmarkFilter wrappers, ReplayRuntime integration,
RunLogger serialization tests, later analysis diagnostics.

Algorithmic impact:

None on landmark filtering equations. The aggregation is diagnostic
only and MUST NOT feed back into filtering.

Experimental impact:

F1/F2 frame diagnostics become deterministic and comparable. Primary
jitter/responsiveness metrics remain trajectory-based.

Compatibility impact:

No completed fixed/adaptive final experiment logs exist. Existing Raw
logs are unaffected.

Tests added/updated:

Upcoming G3.6 tests will verify max-speed representative selection,
deterministic tie handling, initialization/no-measurement diagnostics,
reset reporting, and runtime serialization.

Existing results invalidated:

No — no final F1/F2 experimental results exist.

### G4 contract clarification — bounded adaptive beta mapping

Change:

Defined the exact project-specific F2 velocity-to-beta mapping, clarified
per-landmark adaptive vectorization, primary quality-disabled behavior,
final-cutoff safety, and adaptive public diagnostic aggregation.

Reason:

The canonical specification already defined adaptive parameters and
final cutoff bounds but did not state the exact beta(v) equation.
Implementation would otherwise have to choose algorithm behavior
silently.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, adaptive F2 algorithm;
`02_ARCHITECTURE_AND_CONTRACTS.md`, adaptive FilterDiagnostics semantics.

Code/modules affected:

Upcoming adaptive landmark core, adaptive public LandmarkFilter,
configuration validation, replay/logging tests.

Algorithmic impact:

F2 beta is explicitly nondecreasing with speed and bounded by configured
beta limits. Optional velocity limiting applies to beta adaptation.
Final cutoff remains independently bounded.

Experimental impact:

Defines the F2 method that will later be compared with F0 and F1.
Primary F2 does not use measurement-quality adaptation unless a valid
documented source exists.

Compatibility impact:

No adaptive implementation or final F2 result exists yet.

Tests added/updated:

Upcoming G4 tests will cover beta bounds/monotonicity, velocity spikes,
final cutoff bounds, unavailable quality, invalid dt, reset, and
reacquisition.

Existing results invalidated:

No — no F2 implementation/final experimental results exist.

### G4 contract correction — temporal filter event propagation

Change:

Added explicit filter-event propagation through `FilterDiagnostics.events`
to `TrackingFrame.events` and `RunLogger.log_event`. Frozen the existing
temporal event names for F1/F2.

Reason:

The temporal filter cores already detect timestamp/loss/reset events, and
the run artifact contract already includes `TrackingFrame.events` and
`events.csv`, but the public `LandmarkFilter` return contract had no path
for carrying those events to the runtime. ReplayRuntime therefore could
not preserve them without duplicating temporal state logic.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, FilterDiagnostics / TrackingFrame /
LandmarkFilter logging semantics;

`03_ALGORITHM_AND_EXPERIMENTS.md`, tracking-loss/discontinuity event
semantics.

Code/modules affected:

Core FilterDiagnostics contract;
Raw/fixed/adaptive LandmarkFilter implementations;
ReplayRuntime;
run logging integration and tests.

Algorithmic impact:

None. Existing timestamp, loss, reset, and reacquisition decisions are
unchanged.

Experimental impact:

Future F1/F2 run artifacts preserve temporal reset/discontinuity events
needed for auditability and exclusion/debugging.

Compatibility impact:

In-memory `FilterDiagnostics` gains an events field. Existing CSV column
schemas are unchanged; the already-defined events artifact will begin
receiving the events that were previously dropped.

The existing FileRunLogger already serializes TrackingFrame.events.
The contract therefore assigns serialization responsibility to RunLogger
rather than requiring ReplayRuntime to issue a second duplicate
log_event call.

Tests added/updated:

Core contract tests;
Raw/F1/F2 public-filter tests;
ReplayRuntime event propagation tests;
events.csv logging tests.

Existing results invalidated:

No — no final F1/F2 experimental result set exists. Earlier development
runs may lack these event records and must not be treated as final
event-complete runs.

### G5 algorithm/interface decision — deterministic gesture mapping

Change:

Defined the course-baseline gesture mapping and GestureEngine contract:
configured landmark roles, palm-width-normalized pinch, pinch
hysteresis, bounded/deadzoned pointer rotation, pinch-ratio scale delta,
and explicit neutral loss/reset/reacquisition behavior.

Reason:

The previous G5 specification required normalized pinch, hysteresis,
rotation/scale deadzones and clamps, but did not define the exact
landmark roles, scale mapping, public InteractionState field semantics,
or initialization/reacquisition state transitions. Implementing those
details without a specification decision would make gesture behavior
ambiguous.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, InteractionState and public
interfaces;

`03_ALGORITHM_AND_EXPERIMENTS.md`, Gesture mapping.

Code/modules affected:

future `interaction` / gesture modules, configuration validation,
ReplayRuntime/RealtimeRuntime gesture integration, interaction logging,
and 3D STEM Extension.

Algorithmic impact:

Defines the project-specific G5 gesture algorithm. It does not alter Raw,
fixed 1-Euro, adaptive 1-Euro, ROI, illumination, or landmark-provider
behavior.

Experimental impact:

RQ1/RQ2 preprocessing and temporal-filter baselines are unchanged.
Future RQ3 demo behavior must use this gesture mapping and preserve its
resolved configuration.

Compatibility impact:

No implemented G5 gesture engine or final RQ3 interaction result existed
before this decision.

Tests added/updated:

G5 tests cover normalized pinch, denominator protection, hysteresis,
rotation deadzone/gain/clamp, scale deadzone/gain/clamp, loss reset,
first-frame neutrality, temporal-filter-reset neutrality, reacquisition
neutrality, scene-state accumulation and bounds, Extension/Core dependency
boundaries, ReplayRuntime/RealtimeRuntime interaction integration, and
clean renderer/runtime behavior.

Existing results invalidated:

No — no final G5 interaction experiments/results exist.

### G6 experiment-design decision — primary metrics and baseline isolation

Change:

Frozen the minimum course primary metrics and comparison isolation rules:

- A1 F0/F1/F2 primary metric: radial RMS jitter of filtered landmark 8;
- A2 F0/F1/F2 primary metric: 2D trajectory-deviation RMSE relative to
  F0 on the identical dynamic replay;
- Experiment B P0/P1 primary metric: valid hand-observation rate;
- A1/A2 hold preprocessing constant at P1;
- Experiment B holds temporal filtering constant at F0 / Raw;
- paired conditions use the same source, timestamps, predefined analysis
  window, and common usable frame IDs where applicable.

Reason:

The canonical experiment specification required choosing one primary
metric before final comparison but intentionally did not preselect the
metric. G6 tooling requires those choices to be frozen before final data
collection so analysis code cannot select favorable metrics after viewing
results.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Experiments A1, A2, and B.

Code/modules affected:

Future G6 experiment manifests, analysis loaders, metric functions,
batch runner, result tables, and plot regeneration.

Algorithmic impact:

None. F0, F1, F2, P0, and P1 processing algorithms are unchanged.

Experimental impact:

Defines the primary descriptive outcomes that will support RQ1/RQ2 and
prevents preprocessing and temporal-filter conditions from being changed
simultaneously in their primary comparisons.

Compatibility impact:

No final experiment result set exists. Development runs produced before
this decision may be used for tooling/debugging but MUST NOT be mixed into
final tables unless they satisfy the frozen protocol.

Tests added/updated:

Upcoming G6 tests will cover metric calculations, paired frame alignment,
manifest validation, deterministic condition expansion, and analysis of
generated run artifacts without manual CSV editing.

Existing results invalidated:

No — no final A1/A2/B result set has been collected.

### G7 experiment-protocol clarification — unavailable paired metric

Change:

Defined explicit handling for A1/A2 trials whose predefined paired
analysis window contains zero common usable F0/F1/F2 landmark frames.

Such a trial remains in the final experiment record, but its paired
primary metric is marked unavailable with reason
`no_common_usable_frames`. Analysis continues for other trials.

Reason:

The first final A1 batch exposed a previously unspecified edge case:
one retained final trial contained no usable landmark observations in
the predefined analysis window for any F0/F1/F2 condition. The frozen
exclusion policy correctly prevents removing that trial for poor
tracking/NO_HAND behavior, while the radial RMS metric cannot be
numerically calculated without usable landmark samples.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, paired A1/A2 metric availability.

Code/modules affected:

`analysis/regenerate.py`, analysis tests, and possibly metric-result
serialization helpers. Core algorithms, acquisition, tracking provider,
preprocessing, filtering, and recorded sources are unchanged.

Algorithmic impact:

None.

Experimental impact:

The planned and recorded trial remains part of the experiment. The
primary paired metric is calculated only for trials having a non-empty
common usable landmark-frame set. Generated outputs must explicitly
retain unavailable trials and report the evaluable-trial count.

Compatibility impact:

The existing G7 A1 batch and all nine recorded final sources remain
valid. No A1 primary metric output had been successfully generated
before this clarification. No source is replaced and no analysis window
is changed.

Tests added/updated:

Analysis regeneration tests will verify that an empty common paired set
produces an explicit unavailable metric record rather than aborting the
entire batch, while ordinary evaluable trials remain unchanged.

Existing results invalidated:

No. A1 regeneration previously failed before producing final metric
outputs. The raw run artifacts and frozen source recordings remain
valid.


### G7 presentation-interface addition — read-only realtime callback

Change:

Added an optional `RealtimeRuntime` presentation callback that receives
one presentation-safe camera-frame copy, the public `TrackingFrame`, and
the current `InteractionState | None` once per processed realtime frame.

Reason:

The final presentation shell requires camera preview plus
tracking/ROI/illumination/filter/interaction status. `RealtimeRuntime`
previously exposed only the latest `InteractionState`, while the required
tracking diagnostics existed only inside the runtime/logger path.
Presentation code must not reach into mutable Core internals.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, RealtimeRuntime presentation seam.

Code/modules affected:

`src/dip_touchless/runtime/realtime.py`;
`tests/runtime/test_realtime_runtime.py`;
future submission/demo presentation code.

Algorithmic impact:

None. ROI selection, illumination decisions, CLAHE behavior, landmark
provider behavior, temporal filtering, gesture mapping, logging, and the
3D scene-state algorithm are unchanged.

Experimental impact:

None. ReplayRuntime and all frozen G7 A1/A2/B experiment semantics and
recorded result artifacts are unchanged. The callback is realtime-only
presentation plumbing.

Compatibility impact:

Additive optional constructor argument only. Existing RealtimeRuntime
callers remain valid. The existing `interaction_consumer` remains the
InteractionState-only boundary used by the 3D Extension.

Tests added/updated:

RealtimeRuntime test coverage verifies one callback per processed frame,
matching frame identity/status/interaction state, and a non-shared camera
image copy that presentation code can mutate without modifying the source
frame buffer.

Existing results invalidated:

No — the change does not alter ReplayRuntime, experiment configuration,
analysis code, or any algorithm used to generate the retained final
results.

### G7 final evaluation evidence snapshot — A1/A2/B

Status:

Final paired replay collection and primary analysis have been executed for
A1, A2, B-normal, and B-lowlight using the frozen G7 sources, predefined
2.0--10.0 s analysis window, frozen manifests, and exclusion policy.

No source recording, analysis window, primary metric, or comparison condition
was replaced after inspecting outcomes.

Analysis regeneration revision:

`abdc32b2417fde28cbb9df4b96f1ce5e20e0be4f`

#### A1 — static temporal stability

Batch:

`G7-A1-STATIC-20260928T144254479591Z`

Primary metric:

`radial_rms_jitter`

Recorded trials:

3

Evaluable trials:

2

Observed results:

- `trial-001`, common usable frames = 5:
  - F0 = `0.006607584161915466`
  - F1 = `0.001628449479902759`
  - F2 = `0.001629070583985972`
- `trial-002`:
  - paired primary metric unavailable;
  - reason = `no_common_usable_frames`;
  - the trial remains in the final experiment record.
- `trial-003`, common usable frames = 128:
  - F0 = `0.030597141717346094`
  - F1 = `0.026704461422596908`
  - F2 = `0.026753300347156422`

Evidence-bounded interpretation:

- F1 and F2 both have lower radial RMS jitter than F0 in the two evaluable
  trials.
- F1 and F2 are very close to each other in both evaluable trials.
- `trial-001` contains only five common usable frames, so its numeric value
  is weak descriptive evidence.
- The three-trial source-group size is small; no population-level or
  inferential superiority claim is supported.

#### A2 — dynamic responsiveness characterization

Batch:

`G7-A2-DYNAMIC-20260928T151157912799Z`

Primary metric:

`trajectory_deviation_rmse`

Recorded trials:

3

Evaluable trials:

0

All three trials retain explicit unavailable primary-metric records with:

`no_common_usable_frames`

Diagnostic result:

- `trial-001`: all 360 replay frames were `NO_HAND`;
- `trial-002`: all 360 replay frames were `NO_HAND`;
- `trial-003`: one `VALID` raw-landmark frame occurred at frame 33, outside
  the predefined 2.0--10.0 s primary analysis window; the analysis window
  contained no usable landmark frame;
- within each trial, the raw usable-frame sets were identical across
  F0/F1/F2, so the unavailable result is not evidence of a filter-specific
  alignment difference.

Evidence-bounded interpretation:

The final A2 source set does not provide an evaluable quantitative
trajectory-deviation result. Therefore the final RQ2 evidence can describe
the observed A1 static-jitter behavior, but the predefined primary
responsiveness characterization is unavailable and must remain an explicit
limitation.

No A2 source is replaced and the analysis window is not changed after seeing
this outcome.

#### Experiment B — illumination robustness

Primary metric:

`valid_hand_observation_rate`

Temporal filtering was held at F0 / Raw.

##### B-normal

Batch:

`G7-B-NORMAL-20260928T151702564004Z`

Recorded/evaluable trials:

3 / 3

Each condition used 241 analyzed frames per trial.

Observed P0 / P1 rates:

- `trial-001`: `0.02074688796680498 / 0.02074688796680498`
- `trial-002`: `0.0 / 0.0`
- `trial-003`: `0.5311203319502075 / 0.5311203319502075`

P0 and P1 therefore produced the same primary outcome in each tested
normal-light trial.

##### B-lowlight

Batch:

`G7-B-LOWLIGHT-20260928T152103579608Z`

Recorded/evaluable trials:

3 / 3

Each condition used 241 analyzed frames per trial.

Observed P0 / P1 rates:

- `trial-001`: `0.0 / 0.0`
- `trial-002`: `0.0 / 0.0`
- `trial-003`: `0.0 / 0.0`

The retained source sidecars label these three recordings
`low-light-room`. Auto-exposure and auto-white-balance state were recorded
as `unknown`, so no claim is made about whether camera auto controls
compensated for the physical lighting change.

Illumination-activation audit:

- B-normal P1: stabilized state was `NORMAL` and
  `enhancement_active=False` for all 723 analyzed frames;
- B-lowlight P1: stabilized state was also `NORMAL` and
  `enhancement_active=False` for all 723 analyzed frames.

Therefore the final P0/P1 equality must not be described as evidence that
CLAHE itself is ineffective. Under the tested sources and resolved
configuration, the adaptive activation policy did not request/apply CLAHE,
so P1 resolved to the unenhanced path throughout the analyzed frames.

Evidence-bounded RQ1 interpretation:

Under the tested final conditions, adaptive preprocessing did not increase
valid hand-observation rate relative to bypass. The challenging-light source
group also exposes an activation-policy limitation: despite being acquired
and documented as `low-light-room`, the runtime illumination classifier
remained `NORMAL`, so the final experiment does not provide a direct
CLAHE-active-versus-bypass tracking comparison.

This limitation must remain explicit in the Results and Discussion and must
not be converted into a general claim about CLAHE effectiveness.

#### Current RQ evidence boundary

RQ1:

The primary P0/P1 metric is available for all normal and low-light trials.
No improvement was observed, but the low-light P1 path never activated
CLAHE, limiting the conclusion to the tested adaptive policy and source
conditions.

RQ2:

Static-jitter evidence is available for two of three A1 trials. The primary
A2 responsiveness metric is unavailable for all three final dynamic trials
because the predefined analysis windows contain no common usable landmarks.

RQ3:

The existing G5 physical interaction smoke test demonstrates practical
interaction behavior but is not treated as an RQ1/RQ2 quantitative result.
Final demo/presentation evidence remains to be packaged separately.

### G7 final demo physical smoke — 2026-09-29

Final presentation-shell smoke run:

```text
run_id: g7-demo-20260929-190838
processed_frames: 4947
shutdown: clean
Observed behavior:
- final camera/status presentation and 3D interaction ran successfully;
- the frozen gesture mapping remained unchanged: index-fingertip motion
  controls rotation and thumb-index pinch controls scale;
- the application remained operational through the live run and closed
  cleanly;
- an occasional false-positive hand-like detection was observed around
  the user's face/background, producing a small unintended cube rotation.
Interpretation:
The false-positive behavior is retained as a practical tracking limitation
of the final live demo. It is not hidden by post-hoc tracking-threshold or
algorithm changes. It does not alter the frozen A1/A2/B replay results or
their interpretation.
### G7 post-commit final demo identity verification — 2026-09-29

A second final-demo run was executed after committing the completed
presentation shell so that runtime metadata identifies the exact immutable
code revision used for submission.

```text
run_id: g7-demo-20260929-192030
processed_frames: 1188
shutdown: clean
code_revision: 6a87dc50f9d3920ed9fd39a2669e266be00f9735
spec_version: canonical-v1.2
config_hash: ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08
model_filename: hand_landmarker.task
model_sha256: fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1

The recorded code_revision exactly matched repository HEAD for this
run. This run is therefore the primary reproducibility identity for the
final submitted live demo.
The earlier g7-demo-20260929-190838 run remains the physical behavior
smoke in which rotation, pinch/scale, reset, reacquisition, presentation
status, and clean shutdown were exercised. Its observed occasional
face/background false-positive remains a documented practical limitation.
No Core algorithm, experiment source, analysis window, or retained G7
experiment result was changed between the final evidence collection and
this demo-identity verification.
## 5. Immediate next tasks

Proceed in this order unless a documented blocker requires rearrangement:

1. **G7 Final controlled evaluation** — define the actual final A1, A2,
   and Experiment B manifests, including recorded source identities,
   actual trial counts, predefined analysis windows/warmup, and exclusion
   rules before inspecting final outcomes.

2. **Run final paired replay experiments** — execute F0/F1/F2 for the
   static and dynamic RQ2 sources and P0/P1 for the required illumination
   conditions using the frozen G6 tooling.

3. **Regenerate final evidence** — produce the required trajectories,
   primary metric tables/plots, illumination comparison outputs, and
   DIP-focused before/after visual evidence directly from recorded artifacts.

4. **Submission demo application/presentation shell** — after the final
   experiment evidence is secured, add only the presentation-oriented UI
   needed for the final demo: camera preview, tracking/ROI/illumination/filter
   status, pinch/interaction state, 3D view, start/stop/reset controls, and
   run/log identity. Do not alter Core algorithms or experiment semantics.

5. **Final report/package** — write evidence-bounded Results, Discussion,
   limitations/threats to validity, and Conclusions for RQ1–RQ3; package
   reproducibility instructions, model acquisition/checksum information,
   selected result assets, and the final demo.
