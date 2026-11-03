<<<<<<< HEAD
## Active V2 product rebuild — 2026-10-02

The latest user instruction approves implementing the supplied V2 blueprint
from end to end and defers physical testing. The active branch is
`feat/v2-product-rebuild`, based on immutable application v1.0 commit
`2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`. G7 remains unchanged at
`f454c6b8325c85199c0122c0e822fe8e76c1526c`.

Current task (COMPLETE): implement the user-requested contextual lab guidance with hide/show
and optional enlarged model workspace. Explain the nine labs' actual interactions,
restore prior layout safely, and verify both renderers without physical hand tests.
Retain automatic geometry that follows all fingertips directly. Preserve the
previous full-fingertip correction,
using every extended fingertip from one or two hands, following tips directly
without manual point creation. Preserve the V2 product frontend,
separate intent layer, hand anchor, two-hand adapter, educational extensions,
fallbacks and source delivery. Physical usability acceptance is explicitly
DEFERRED BY USER and must not be marked passed. The R4/current-task entries
below are historical v1.0 records. Product scope/API approval is documented
in `07_V2_PRODUCT_SPEC.md`, with the supplied blueprint in `V2_BLUEPRINT.md`.

Actual validation and delivery status: `release/v2/QA_STATUS.md`.

V2 source implementation is delivered with automatic verification as a local
`2.0.0rc1` delivery: 909 full-suite tests passed, 354 product tests covered, native
OpenGL and software synthetic render QA executed, actual two-hand model blank
inference/cleanup checked, CLI/compile/dependencies/whitespace verified, and
the frozen Core/evidence tree and original tag commits unchanged. Physical
usability and blueprint P9 percentages remain unmeasured/deferred by the user.
The RC source archive and setup/launch/docs are separate from a production or
physically accepted final release. No stage/commit/push/tag was performed.

Continuation on 2026-10-03 hardened modal ownership, native editing shortcuts,
mouse/gesture takeover, commit identity and continuous UI/scene pointer mapping.
Fresh extracted-package setup, UI/model smoke, dependency consistency and all
628 tests also passed in a newly created Python environment on this machine.
For progress accounting, P0-P8 plus P9 automated checks are ten completed gates;
the separate physical P9 gate remains deferred. Thus engineering scope is 10/10
(100%), while the eleven equally counted gates are 10/11 (90.9%). This is a task
checklist ratio, not a measured physical success rate or readiness guarantee.

Camera bug correction on 2026-10-03: the V2 worker supplied an unsupported
keyword to the frozen live-demo factory, so the original RC could fail before
opening the camera despite its isolated tests passing. The worker now supplies
the presentation callback through the factory's controller contract. New tests
execute the real factory/runtime/logger with only device boundaries mocked in
PRODUCT and LEGACY. The normal V2 Start/Stop buttons also opened physical camera
0, delivered five sampled GUI frames and shut down cleanly in run
`stem-v2-20261003-004440-362832`; all sampled frames had no detected hand.
Camera integration is verified for that run. Physical gesture usability/HAND
anchoring with real hands remains unverified; the earlier checklist percentage
must not be interpreted as an assurance of defect-free execution.

User-approved 3D/UX/environment optimization on 2026-10-03 is implemented:
perspective ray picking; GLSL sphere/bond/surface meshes with true depth testing;
shared software fallback; contextual Tools/Inspector; explicit lighting/crowding
guidance; default third-hand observation budget with at-most-two-hand acceptance.
Product manifest schema is `product-v2-2`. Real framebuffer occlusion and synthetic
third-hand rejection/reacquisition tests passed. Native/software QA each rendered
66 surfaces. Camera 0 Start/Stop passed again in run
`stem-v2-20261003-011005-330547`, still with no hand detected. Physical hand,
low-light/crowding usability, optimal UX and enterprise readiness remain unproven.

Full V2 UI audit requested on 2026-10-03 is complete for the inspected local
implementation. Confirmed UI/state/logging and educational-math defects were
fixed, and necessary Reset view, optional construction-plane grid snapping and
measurement CSV export were added. Full regression passed 682 tests; GPU and
software audit QA each captured 82 synthetic surfaces. Findings, coverage,
remaining limitations and recommended later utilities are recorded in
`release/v2/UI_AUDIT.md`. Physical hand usability remains deferred; this audit
does not certify security, enterprise readiness or absence of future defects.

The repeated audit request on 2026-10-03 prompted additional failure-path review.
It reproduced and fixed manual HAND anchor/clutch loss, destructive partial CSV
overwrite and noncanonical/reserved Windows archive member names. Presentation
may be retained only during manual takeover of an observed anchor; actual loss,
modal/context reset and source/reference changes still clear it. Full regression
now passes 697 tests (142 V2). Details are appended to `release/v2/UI_AUDIT.md`;
no physical hand test or new enterprise-readiness claim is implied.

Spec-conformance review on 2026-10-03 confirmed the frozen research boundary,
but identified an additional product-mode limitation: bimanual pinch scale works
in WORLD, while HAND requires an OPEN_PALM anchor and cancels when both hands
pinch. A synthetic public GUI/intent check reproduced this difference under
`runs/docs-conformance-check`. The general two-hand scale description in docs/07
does not explain this mode restriction adequately. Do not claim full V2 behavior
conformance or treat this as physical validation. Resolving HAND scaling requires
an explicit product interaction decision; no algorithm change was made by this
read-only conformance review. Blueprint P9 physical acceptance remains deferred.

User-reported finger/alignment failure on 2026-10-03 authorized correcting the
HAND interaction decision above. HAND now acquires on OPEN_PALM and follows the
same valid observed palm through POINT/pinch; loss/context changes still clear it.
Camera-aligned source picking replaces window picking only for HAND scene input;
explicit Control UI retains exclusive window navigation. Relative-3D finger bends,
locked measurement snapshots and presentation-only automatic Inspector expansion
are corrected. Public product changes are recorded in docs/02 section 16 and
docs/07; frozen Core/G7 contracts and results remain unchanged.
Full regression: 749 passed (194 product). Tests cover all nine labs, eight geometry
tools, HAND scale/pair locking, actual classifier-to-GUI cursor pixels and HiDPI
layout changes. Native QA captured 82 synthetic surfaces. Recorded user landmarks
from `stem-v2-20261003-082757-256103` were inspected and replayed on blank synthetic
images in both renderers; `runs/hand-fix-validation/report.json` records this
diagnostic. No ground-truth physical accuracy or acceptance percentage is inferred.
The former OPEN_PALM-every-frame HAND limitation above is now resolved in code and
synthetic tests. Physical P9 acceptance remains deferred.

Latest user correction on 2026-10-03 replaces the default index/pinch construction
experience with PRODUCT/LIVE. Every extended fingertip from either/both associated
hands is a live vertex (up to ten), with automatic point/segment/triangle/
quadrilateral/polygon geometry across all nine labs. Shapes follow directly;
there is no dwell-to-save or Add point requirement. Folded tips are inactive;
loss, no active tips and owner/context changes clear live geometry. Initial
OPEN and pinch calibration are unnecessary for LIVE. Control UI and RECORDED
retain explicit exclusive navigation/legacy construction. Both view modes use
camera-aligned vertices and bounded per-palm relative model-z visual relief,
not physical/cross-hand camera depth. Public changes are recorded in docs/02
section 16 and docs/07; product manifest schema is product-v2-4.

Executed validation: 863 full-suite / 308 product tests passed. New tests cover
all nonempty five-finger subsets in both roles, actual classifier-to-GUI counts
one through ten in both modes, movement/folding, loss/UI/modal/context, depth
projection, all nine labs, concave surface boundaries and immutable CSV export.
Native OpenGL and software QA each captured 24 synthetic all-finger surfaces
at two requested desktop sizes. No webcam or physical accuracy claim is involved.
Physical acceptance remains deferred by the user. Engineering implementation and
automatic verification of this correction are complete; delivery details are
recorded in release/v2/QA_STATUS.md.

LIVE correction delivery verified: 242 files in the rebuilt model-inclusive
source archive; extracted UI/resources/actual blank-image model smoke and all
863 tests passed with the separate previously installed dependency environment.
Compilation, dependency/format/whitespace checks passed; protected Core/G7/evidence
diff is empty and original release tag commits are unchanged. Current correction
requires no further implementation or automatic check; physical acceptance stays
deferred as requested. No staging, commit, push or tag was performed.

## 2. Current implementation evidence
=======
# 05 — Project Status and Roadmap

## Current handoff — submission after defense, 2026-10-18

User authorized freezing the current four-tab scope, merging feat/physics-lab
into main and updating installation/README guidance. The user subsequently
clarified that the video script is private; remove it and its links from the
current source, preserving a local ignored copy. ZIP-first instructions state
one initial setup command followed by one app command, with only the latter
needed on subsequent launches. Submission identity: tag submission-2026-10-18-r2;
the earlier 18/10 and 16/10 tags and
development branches remain intact. Runtime code is the accepted 688f6b4 fix.
This handoff changes documentation/Git only; no tests are rerun, following the
user's explicit request. Existing 1091-pass Python 3.11/3.12 evidence below is
retained with its actual scope and limitations. Word/PDF/slides
and source video remain separate submission artifacts; do not claim the source
ZIP includes ignored local files. Preserve personal untracked files.

## Earlier task — chemistry post-release drift fix, 2026-10-18

Change: atom/component-only early contact-break freeze and observed release.
Reason: user reported objects continuing to follow after opening; reproduced
the missing freeze in both whole-component and atom edit regression cases.
Canonical file/section changed: 01 authorized fix, 02 chemistry grab policy,
03 presentation policy, this record.
Code/modules affected: chemistry_input, UI settings/metadata, release regressions;
two earlier object tests updated to the new narrower object contact band.
Algorithmic impact: object presentation release only; panel/menu gates, shared
GrabController, Core, physics and chemical graph rules unchanged.
Experimental impact: none on research/model data. Compatibility impact: UI schema
21 adds actual per-claim opening state and identifies the object release policy.
Tests added/updated: raw-vs-filtered release, follow-tail freeze, no recapture,
reclose rebase, two-hand release, missing input not confirming/linking.
Existing results invalidated: no Core/model results; older UI logs retain their
policy identity. Status: complete. Full suites passed 1091 tests on each of
Python 3.11.9 and 3.12.14, including seven new release cases. The two raw partial-
opening cases were observed failing before the correction. Native GL ran 37
frames through whole-component and atom-edit capture, movement, partial raw
opening with still-closed filtered fingers and post-release updates. Displayed
positions/scales stayed frozen and no GL error was reported. Local script:
runs/chemistry_release_qa.py. No physical-hand accuracy/latency claim follows.
Preserve main and personal files. User requested no further tests after these
completed checks; only documentation/Git handoff remains.

## Earlier task — solid palette and fingertip presentation, 2026-10-18

Change: touchless four-shape palette, observed geometry feedback, render-rate
tip labels and semantic-only basic-tab UI uploads.
Reason: user approved improving the first two tabs while preserving accepted
chemistry/physics manipulation and research semantics.
Canonical file/section changed: 01 authorized scope, 02 presentation boundary,
03 presentation policy, this record.
Code/modules affected: solid_palette, screen_sprites, renderer, geometry
projection helper, UI settings/metadata and UI/native regressions.
Algorithmic impact: presentation selection/feedback only; source filtering,
live geometry and solid object manipulation equations unchanged.
Experimental impact: none on Core/report. Compatibility impact: UI schema 20;
model revision 3/catalog/setup identity unchanged.
Tests added/updated: modal re-aim, dwell/pinch, grip priority, no grab-through,
loss/identity/time/source/viewport cancellation, tip classification, projection,
static UI uploads, context resource lifecycle and four-tab native GL.
Existing results invalidated: no Core/model results; UI recordings retain their
previous policy identity. Status: complete. Full suites passed 1084 tests each
on Python 3.11.9 and 3.12.14, adding 55 cases. After a final glyph-contrast
adjustment, 77 targeted presentation/native/release checks passed again.
Native GL QA rendered 320 frames across 640x600, 800x600, 960x660 and 1360x860,
all four tabs, side-camera toggles, both menu edges and F11 round trips; no GL
errors or header button overlaps were reported. Inspected compact/menu/tip images.
Actual Python 3.11 app replays processed 30 MediaPipe frames in each mode,
all with error=null, worker_stopped=true and UI schema 20; solid_controls logs
were parsed. Local artifacts: runs/solid-palette-qa, including app-results.json
and native-results.json. These software/synthetic checks do not establish
real-hand accuracy, physical latency or universal smoothness.
Continue feat/physics-lab; preserve main, chemistry branch and personal files.

## Earlier task — Physics quick commands and temporary scene shortcut, 2026-10-18

Change: stable open palm at a free side edge summons four existing commands;
fresh two-hand pinch in empty space enters temporary scene viewing while paused.
Reason: user approved fewer button-navigation steps, preserving original UI.
Canonical file/section changed: 01 shortcut scope, 02 shortcut contract,
03 presentation policy, this record.
Code/modules affected: Physics-only recognizer/input/view, UI settings/metadata,
documentation and shortcut/native regressions.
Algorithmic impact: gesture/presentation only; eight SI models unchanged.
Experimental impact: none on Core/RQ/report. Compatibility impact: UI schema 19;
model revision 3, SI catalog hash and setup schema unchanged.
Tests added/updated: pose/hold/rearm, stale/loss/identity, target/claim priority,
modal selection, temporary-mode release, compact layout and native GL.
Existing results invalidated: no Core/model results; old interaction recordings
remain identified by their previous UI policy. Git: continue feat/physics-lab,
preserve main/chemistry and personal untracked files. Status: complete. Full
suites passed on Python 3.11.9 and 3.12.14: 1029 tests each, 57 added cases
including a native shortcut regression. Coverage includes scale/aspect-safe
source pose gates, short/unstable/invalid input, one-shot rearming, fresh pair
activation, modal pointer re-aim, no grab-through, cancel on loss/identity/stale,
paused-only entry, original target priority and static Check. A lost temporary
grip stays consumed until observed opening, including slot generation changes.
Busy normal grabs skip new geometry/pose shortcut work.
Native GL QA rendered 780 frames over four window sizes, eight models and
quick palettes, including F11 while a palette stayed open, with no GL errors.
Inspected native progress/palette screenshots in runs/physics-shortcuts-qa.
Actual app replay ui-20261018-133657-059518 processed 30 MediaPipe frames,
reported UI schema 19, error=null and worker_stopped=true. Native export/load
still produced JSON/CSV/view JSON/PNG with independent A/B. Catalog/model/Core,
research config, chemistry/shared gestures and renderer paths have no diff
against fd1319f. Artifacts stay ignored. These software/synthetic checks do not
establish real-hand recognition accuracy or a performance improvement claim.

## Earlier task — richer direct mechanics interaction, 2026-10-18

Change: body-sized picking, explicit velocity/parameter targets, contextual
feedback, undo/cancel, optional deliberate release-to-run and coordinated
two-hand scene manipulation on the existing eight models.
Reason: user accepts the audited model but finds the limited handle-only
interaction too shallow and requests smooth, practical manipulation.
Canonical file/section changed: 01 approved presentation scope, 02 interaction
contract, 03 presentation policy, this task record.
Code/modules affected: Physics input/view, UI settings/metadata and regressions.
Algorithmic impact: presentation only; SI equations, fixed-step integration,
research filters, tracking provider and other tabs remain unchanged.
Experimental impact: none on retained Core/report/research results.
Compatibility impact: UI schema 18; model revision 3/setup schema/catalog hash
unchanged. Tests added/updated: lifecycle/ownership/two-hand transitions,
geometry picking, undo, deliberate release/loss cancellation and native GL.
Existing results invalidated: no research/model results; old UI interaction
recordings retain their original policy identity. Git: feat/physics-lab, preserve
main and personal untracked files. Status: complete and verified. Full suites
passed on Python 3.11.9 and 3.12.14: 972 tests each, with 38 new direct-interaction
cases and an extended native regression. Cases cover observed release/noise-size
gating, loss/identity/time/viewport cancellation, exact paused undo, two-hand
ownership/join/leave/near-span freeze, rotated box picking, continuous signed
velocity controls, analytic preview and bounded label rasterization cadence.
Native GL QA rendered 676 frames over four window sizes, all eight models,
tool/lesson pages and F11 with no GL errors. Inspected compact projectile and
large collision images, including font-safe undo/cancel labels. Actual Python
3.11 app replay ui-20261018-130651-614880 processed 30 frames with error=null,
worker_stopped=true and UI schema 18. Native export/load passed all four files;
verified model revision 3/catalog hash unchanged and view pose/release mode in
view.json. Local artifacts: runs/physics-direct-qa and runs/physics-qa/export-check
(ignored). Protected Core/config/research/chemistry/shared gesture/renderer/model
paths have no diff against 8d893b0. No physical gesture accuracy or measured
performance improvement is claimed from these synthetic/software checks.

## Earlier task — second mechanics boundary audit, 2026-10-18

Change: correct same-time live-force samples and exported endpoints; require
enough forward displacement and reject a transient turn/low-speed motion as a
successful static stop; project rejected
launch-vector components before computing both angle and speed.
Reason: user requested a deeper second check. New regressions reproduced six
failures on the previous code: two stale CSV final-force values (10 vs 17 N),
one force challenge falsely accepted a genuine turnaround trajectory and three
out-of-quadrant launch drags used rejected components in speed magnitude.
Two subsequent reproductions found a short .75 m trip falsely passed, while a
valid 2 m trip beginning at x=2 m was rejected. Replace initial-zone gating with
actual forward displacement and configured floating-point distance tolerance.
Canonical file/section changed: 02 endpoint/setup contracts; 03 revision-3
boundary semantics; this record. Modules: Physics model/catalog/view,
analytic/view regressions, audit notes and README. Algorithmic impact: the
eight evolution equations and integrator are unchanged; educational success,
launch-input parameter mapping and measurement publication are corrected.
Experimental impact: none on Core/research/report. Compatibility impact:
model revision 3/new catalog hash; UI schema 17 and setup schema 1 unchanged.
Known revision-1/2 setup hashes load as initial values, with existing validation.
Existing results invalidated: prior force-stop flags, out-of-domain launch
settings and stale endpoint exports are superseded; no frozen research result
or valid model trajectory at unchanged physical inputs is invalidated.
Git: continue feat/physics-lab; main/chemistry/personal untracked files preserved.
Status: complete. Full suites passed on Python 3.11.9 and 3.12.14: 934 tests
each, including 11 additional cases versus the first audit. A seeded local sweep
passed 256 valid mixed-parameter configurations across the eight models, checking
finite states and applicable energy/momentum relationships; this is observed QA,
not a universal numerical error bound. Native UI QA repeated 652 frames across
four window sizes, all eight scenes and F11 with no OpenGL errors. Export/load
of JSON/CSV/view JSON/PNG passed, and the actual app processed 30 replay frames
with error=null and worker_stopped=true. Local evidence: runs/physics-boundary-qa,
runs/physics-qa and runs/ui/ui-20261018-124319-604798 (ignored artifacts).
No new hand gesture, provider or research-filter change is included.

## Earlier task — full bounded-mechanics audit, 2026-10-18

Change: audit all eight SI models, formulas/assumptions, numerical integration,
goals, export compatibility and physical diagrams before further gesture work.
Correct along-incline velocity, pendulum damping-force and lever-reaction
arrows, model-specific scalar/period labels, signed incline-friction notation,
measured-period goal configuration and explicit lever/pulley idealizations.
Reason: user requests a physics/formula audit before adding interactions.
Canonical file/section changed: 02 schema/setup contract; 03 mechanics audit;
this record. Code/modules affected: Physics model/catalog/view, metadata,
independent analytic/conservation/diagram tests and review notes.
Algorithmic impact: eight evolution equations, fixed step and bounds unchanged;
derived tension/drag and physical display/goal semantics corrected.
Experimental impact: no Core/RQ/report changes. Compatibility impact: model
revision 2/catalog hash, UI schema 17 with added pendulum quantities. State file
schema 1 unchanged; explicitly permit the known revision-1 setup hash with full
parameter validation. Unknown mismatches rejected. Existing results invalidated:
no research data/trajectory values; prior Physics diagrams/labels/goal wording
are superseded and must not be presented as the corrected revision.
Git: continue feat/physics-lab, preserve main/chemistry and personal untracked
submission/PHAN_CONG_BAO_VE.md. Status: verified. Executed 923 full tests on
Python 3.12.14 and Python 3.11.9; 23 added regressions cover analytic damped
spring phase, nonlinear pendulum elliptic-period reference, Cartesian force
balance, configured period goals, elevated projectile landing, collision loss,
all pulley ratios, known-setup migration/unknown-hash rejection and diagram/
quantity semantics. Native QA rendered 652 frames across four window sizes,
all eight scenes/tool/lesson pages and F11, with zero GL errors. Inspected
large incline and compact pendulum screenshots. Local runs/physics-qa/ ignored.
Python 3.11 native save/load/export produced all four files with A/B final
states; a pendulum export retained revision 2 and tension/drag CSV columns.
Actual app replay ui-20261018-122908-734451 processed 30 MediaPipe frames,
reported UI schema 17/no error and stopped its worker cleanly.
git diff --check passed. Protected Core/config/chemistry/gesture/geometry/
renderer paths have no diff against 343e919. The audit is validation against
bounded ideal models, not a general-physics/commercial or device-accuracy claim.

## Earlier task — model-only early contact-break freeze, 2026-10-18

Change: freeze Physics model/ruler handles at a separate contact-hold boundary
and discard their pending render-follow target at the displayed position.
Reason: user reports a small displacement on release specifically in the model,
not in the panel. In local UI session ui-20261018-092815-203515, body frames
293..295 have raw pinch ratios approximately .274, .364, .457; frame 294 still
has an active claim and position0 changes from 1.8515216557 to 1.8657805417 m
before opening freezes at frame 295. This demonstrates an allowed movement
window before the old .45 boundary, not ground-truth physical hand intent or
accuracy. The opening boundary for model handles is now separately configured;
panel/slider/view/menu boundaries are preserved.
Canonical file/section changed: 02 model contact-break correction; this record.
Code/modules affected: Physics input, UI setting and input/native regressions.
Algorithmic impact: model-handle presentation only, no SI equation/filter change.
Experimental impact: none. Compatibility impact: UI schema 16/catalog/state
schema unchanged; new setting captured in resolved UI configuration. Existing
results invalidated: no; Core/provider/research/config, shared gestures,
chemistry, solid/fingertip logic and scene/panel layout are unchanged.
Git: continue feat/physics-lab; main and personal untracked files remain intact.
Status: verified with 900 full tests passed on Python 3.12.14 and Python 3.11.9.
Nine added regressions cover the recorded scalar opening sequence over model
handles and preserve panel/slider/orbit/zoom boundaries. Extended native GL
regression grabs the actual model handle, moves it, opens to .364 with palm
displacement and a pending follow target, and checks unchanged displayed
position through confirmation/drop. Existing menu/tool/edge/F11 tests pass.
Protected Core/config/chemistry/shared gesture/geometry/model/catalog/view/
renderer paths have no diff against d28f851; git diff --check passed.
Tests use recorded scalar ratios with synthetic palm geometry because the logs
do not contain landmark trajectories. No real-hand success-rate claim is added.

## Earlier task — Physics release latch and discoverable view tools, 2026-10-18

Change: replace button-looking orbit/zoom drag handles with selectable tools;
allow a fresh pinch anywhere outside the panel to control the selected view.
Show active tool/instructions, preserve menu consumption and add explicit Edit
return. Latch opening intent across the ambiguous pinch band; confirm release
from real observations, or require tight contact and neutral rebase to resume.
Reason: user reports unusable/unclear orbit and zoom plus intermittent sticking
after opening. Code allowed an ambiguous ratio below the freeze threshold to
resume the same claim before the old full-open release threshold was reached.
Local sessions ui-20261018-091358-168674 and ui-20261018-091457-792076 have
object/force/ruler claims but no orbit/zoom claims or menu-selector states;
they do not contain full hand trajectories or intent labels and cannot establish
individual failure causes or physical success rates.
Canonical file/section changed: 02 Physics follow-up contract; this record.
Code/modules affected: Physics input/view/settings, UI metadata, README/tests.
Algorithmic impact: Physics presentation only. Experimental impact: none.
Compatibility impact: UI schema 16 adds tool/opening diagnostics and release
policy; SI catalog/hash/state schema unchanged. Existing results invalidated:
no; Core/provider/research/config, shared gesture classes, accepted chemistry,
solid/fingertip logic and physics equations remain unchanged.
Git: continue feat/physics-lab; main/chemistry branch and personal untracked
submission/PHAN_CONG_BAO_VE.md remain intact.
Status: implemented and verified. Executed 891 full tests on Python 3.12.14
and Python 3.11.9. Seven added regressions cover band-settling release, a single
opening spike with tight neutral rebase, ambiguous return after loss, both tool
targets/panel priority, menu-pinch consumption/fresh canvas grab and one-shot
dwell tool selection. Extended native GL test selects and hand-drags both tools,
checks SI invariance and partial-open release, returns to Edit and checks F11.
Native visual QA rendered Edit/orbit/zoom at 640x600, 768x520 and 1360x860;
zero GL errors, controls contained, active mode refreshed immediately. Inspected
compact orbit and large zoom images in ignored runs/physics-tool-qa/.
Actual Python 3.11 app replay ui-20261018-092443-860088 processed 30 MediaPipe
frames, wrote a screenshot and stopped cleanly with no error (UI schema 16).
Protected Core/config/chemistry/shared gesture/geometry/model/catalog/renderer
paths have no diff against 91fa00f; git diff --check passed. No extra multi-
finger gestures are added; more gesture classes do not establish better
recognition/usability. No physical-hand success-rate or commercial claim.

## Earlier task — Physics manipulation and view correction, 2026-10-18

Change: stabilize Physics-only held edits using wrist/MCP translation, shared
render-follow position for values/cursor, immediate freeze on opening/loss,
neutral reacquisition, retained fit bounds and nearest-handle picking. Add
bounded orbit and scene zoom handles, drag-to-edge docking with four restoring
arrows, and panel texture reuse/parameter-readout throttling.
Reason: user reports movement on release, uneven control and asks about view
rotation/zoom, edge docking and effects on accepted tabs. Inspection found
contact-midpoint displacement during folding, camera-cadence value updates vs
independently smoothed cursor, continuous auto-fit and redundant panel uploads.
These code paths explain possible symptoms; existing logs do not record full
hand trajectories/intent and cannot establish each physical failure's cause.
Canonical file/section changed: 02 Physics presentation contract; this record.
Code/modules affected: Physics input/view, additional Physics-only UI settings,
UI metadata, README and interaction/view/native regressions.
Algorithmic impact: presentation control only; eight SI equations unchanged.
Experimental impact: none. Compatibility impact: UI schema 15 records finished
claims/movement policy; catalog content/hash and state schema 1 are unchanged,
so previously saved Physics configurations retain compatibility.
Existing results invalidated: no; Core/provider/raw/fixed/adaptive/replay,
research/report and accepted chemistry/solid/fingertip logic are unchanged.
Git: continue feat/physics-lab; main and chemistry branch remain intact. Preserve
untracked personal submission/PHAN_CONG_BAO_VE.md and local QA artifacts.
Status: implemented and verified. Executed 884 full tests on Python 3.12.14
and Python 3.11.9. Seventeen added regressions cover finger-only motion, source
vs render cadence, no post-release/loss tail, neutral rebase, consumed docking,
two-hand view ownership, four-edge restore, hold vs throw intent, stable fit,
bounded orbit/zoom, invalid plane edits, nearest-handle picking and texture
reuse/readout refresh. Extended native GL regression also exercises real draw
cadence release, hand-drag docking and orbit, then F11 restoration.
Local native QA rendered 165 frames over 640x600, 768x520 and 1360x860 with
all four docking edges and eight labs at different angles; zero GL errors.
Inspected large angled pendulum and compact right-edge screenshots. Artifacts:
runs/physics-refinement-qa/ (ignored). Actual Python 3.11 app replay run
ui-20261018-091136-360338 processed 30 MediaPipe frames, wrote a screenshot,
reported no error and stopped its worker cleanly; metadata uses UI schema 15.
Protected Core/config/chemistry/solid/fingertip/model/catalog paths have no
diff against 7b46be9. git diff --check passed. No physical accuracy or
commercial-readiness claim is inferred from synthetic hands or automated tests.

## Earlier task — eight-scenario applied mechanics tab, 2026-10-18

Change: promote the user-approved Physics presentation scope into active work.
Eight bounded SI experiments, common gesture controls, measurement/plot tools,
A/B comparison, learning challenges and local save/export are required.
Reason: user approved the complete pre-code checklist and requested implementation
with a coherent Git workflow and useful innovation within that scope.
Canonical file/section changed: 01 presentation scope; 02 Physics contract; this
record. Code/modules affected: new submission physics model/catalog/view/input,
minimal renderer/app integration and targeted tests/documentation.
Algorithmic impact: presentation teaching models only. Experimental impact: none.
Compatibility impact: Physics state schema 1, UI schema 14 with catalog hash and
compact model/control diagnostics; no full trajectory copy in every frame log.
Existing results invalidated: no; Core, fixed/adaptive/raw baselines, replay,
research report/evidence and accepted chemistry remain frozen.
Git: `feat/physics-lab` branches from chemistry milestone `825ac93`; retain main
and chemistry branch, stage task files only, test coherent commits and push the
development branch. Personal `submission/PHAN_CONG_BAO_VE.md` stays untracked.
Status: the approved eight-scenario v1 functional scope is implemented. Model
milestone `91ce10d` contains the independent SI models/catalog/49 math/config
regressions; the following integration commit adds hand/mouse controls, native
GL scenes, paged compact panels, two-point SI ruler, vectors/traces/energy/plots,
independent A/B initial/input histories, predictions, configured challenges and
JSON/CSV/view/image export. Static scenarios require explicit Check; dynamic
goals pause at the achieved state. Help/formula/assumption pages and panel/scene
zoom are accessible without a mouse. Hidden tabs pause without time debt.

Executed validation on the complete working tree: 867 full tests passed on
Python 3.12.14 and Python 3.11.9, including 78 new Physics regressions. They cover
analytic trajectories, friction stop/reversal, momentum/energy accounting,
nonlinear pendulum period, ideal machine relationships, extreme configured
parameters, deterministic render-time partitioning, invalid/unbounded dt config,
file validation, exclusive two-hand claims, short-loss rebasing, dwell/pinch
one-shot semantics, SI projection/zoom and paged compact tool/help reachability.
The native Windows Physics test exercises all eight scenes, hand-selected
library/collapse/restore, immediate target geometry, semantic HUD refresh and
F11 context restoration. A chemistry-native expectation was updated to pass its
actual mode to scene_rect; extra solid controls wrap below the four-tab bar.

Additional native QA rendered 652 scene/tool frames at 640x600, 800x600,
960x660 and 1360x860, plus 1130 synthetic-gesture frames at 640x600, 768x520
and 1360x860. All eight labs were hand-selectable; slider/header editing,
loss/rebase, arrow restoration, camera preview and F11 passed. All contexts
reported zero GL error. Inspected representative screenshots and fixed stale
HUD titles, first-frame collapse target sizing, cumulative drag projection and
inverted pulley-load drag. Local artifacts: `runs/physics-qa/`; these use
recorded imagery/synthetic hands and do not measure physical-hand success rate.

Actual app replay smokes on both interpreters processed 30 frames through
MediaPipe in Physics mode, rendered a screenshot and stopped the worker cleanly
without error. Python 3.11 check_setup/pip check passed, including the new catalog.
`git diff --check` passed. Core/config/research/report and chemistry model/input/
view/control/manipulation diffs against `825ac93` are empty. No research metric,
real-hand accuracy, latency target, universal-device or commercial-readiness
claim is added. Electricity/optics and general-purpose rigid-body simulation
remain outside this increment; accepted main and chemistry branch stay intact.

## Earlier task — chemistry pinch-selection stability correction, 2026-10-18

Change: preserve armed aim through small movements inside the same button;
after bounded fingertip capture, check observed palm translation relative to
captured size rather than rejecting natural contact-finger movement. Preserve
confirmation through a narrow configured hold-ratio band after tight samples;
require multiple tight observations and the existing confirmation duration.
Dispatch the captured target, and accept a smoothed visual anchor only when it
still hits that target. Keep release/rearm, loss/identity cancellation, menu
consumption, 1-second dwell and original manipulation controllers unchanged.

Reason/evidence: user reports that pinch selects but is inconsistent. Local
schema-12 sessions `ui-20261018-074603-796004` and
`ui-20261018-074810-827878` show both completed selections and cancelled closes.
In the latter, the raw ratio sequence at 12.664..12.793s is approximately
0.4013, 0.1287, 0.1904, 0.2802; the final value barely exceeds tight acquisition
0.28 and erased two prior tight samples before confirmation. Existing code
also reset armed aim against an old origin, cancelled on folding-finger motion,
and repeated hit-testing at a smoothed cursor could discard a captured action.
These are decision-logic weaknesses; logs do not contain raw trajectories or
human-intent labels and do not prove each cancellation's cause or success rate.

Canonical files/sections changed: 02 point-and-pinch correction; this record.
Code/modules affected: submission chemistry controls/input/view/settings,
runtime metadata, README and tests. Algorithmic impact: presentation menu
selection only. Experimental impact: none. Compatibility impact: UI schema 13
adds actual selector ratio and cancellation reason to interaction logs. Existing
results invalidated: no; Core/provider/filter/replay/research configuration,
report data, molecular rules and accepted main remain unchanged. No missing
hand geometry is invented; no accuracy/smoothness benchmark is asserted.

Executed: 789 full tests passed on Python 3.12.14 and Python 3.11.9. Nine added
regressions cover the recorded scalar threshold crossing (synthetic geometry),
partial/spike rejection, armed movement inside a button, independent finger
closure, excessive palm translation, smoothed-anchor validation and captured
target dispatch. Existing release/loss/page-change/dwell/grab tests also pass.
Native GL QA rendered 558 frames across six window sizes, including all three
modes, one-shot/repeat/collapse/restore and F11. Buttons remained within the
window and non-overlapping; contexts reported zero GL error. Artifacts are local
under `runs/chemistry-point-pinch-qa/`, using recorded imagery and synthetic
hands. This is software validation, not a physical-hand success-rate trial.
`git diff --check` passed. Accepted main is unchanged.

## Earlier task — responsive review and point-and-pinch selection, 2026-10-18

Change: fit the initial window to desktop dimensions with configurable chrome
margins; do not shrink subsequent user resizing/restoration repeatedly. Wrap
controls at compact widths, reserve the extra solid-control row only where
used, keep all author glyphs within their badge using real font metrics, and
fit/clip sidebar content to its card. Fall back from a missing Windows panel
font. Preserve camera-cover geometry, raster/glyph caching and F11 lifecycle.

Default chemistry quick selection changes to open-hand aim plus confirmed raw
XY thumb-index pinch. Capture the displayed cursor/target during a bounded
close, require tight pinch and multiple observations, emit once, unlock after
feedback, and require confirmed opening/fresh aim for another explicit click.
Consume menu pinches across page changes so they cannot grab objects behind
the palette. Keep the existing 1-second dwell and its normal leave/rearm
behavior; a dwell activation also consumes the current menu gesture. Maintain
existing atom/component/header manipulation and graph rules. The previous
index-push selector is retained only as an explicit experimental configuration.

Reason/evidence: user requested another smoothness/sharpness/layout review and
a more practical selector, retaining dwell. The default 1360x860 window could
exceed a 768-pixel-high laptop display. The narrow badge title was outside its
card and 13px glyph rows overlapped by one bounding-box pixel. Schema-11 local
sessions `ui-20261017-164032-225005` and `ui-20261018-071830-751249` contain aim/
armed/cancelled states but no completed push click. This motivates replacing
the default policy, not claiming a tracking accuracy improvement. Reference:
Microsoft point-and-commit design, linked in 02; no device performance transfer.

Canonical files/sections changed: 01 authorized presentation scope; 02 point-
and-pinch contract; this record. Modules: submission controls/input/view/theme/
renderer/app/settings/metadata, README and tests. Algorithmic impact: UI menu
selection and responsive display only. Experimental impact: none. Compatibility
impact: UI schema 12 records selector name and actual window/fullscreen in
interaction logs. Existing results invalidated: no; Core/provider/filter/raw-
fixed-adaptive/replay/config/report data, chemistry data and accepted main are
unchanged. No new model, camera resolution increase or UI telemetry panel.

Executed: 780 full tests passed on Python 3.12.14 and Python 3.11.9. Coverage
includes gradual close, one-shot/release/re-aim, no depth dependency, invalid/
loss/identity/time cancellation, partial/spike/shake rejection, actual-cursor
capture, dwell fallback/no duplicate action, same-tile repeat, edge restore and
no grab through a changed page or short loss during a consumed menu gesture.
Layout tests cover ten badge widths and four
desktop-fit examples. Legacy push tests now explicitly select the legacy mode.

Native GL selector/layout QA rendered 558 frames at actual sizes 640x600,
800x600, 960x660, 1248x640, 1334x688 and 1888x1080 (1920x1080 requested, fitted
to the current desktop). All three modes' buttons remained inside the window
and non-overlapping; selection/repeat/collapse/restore/F11 passed. An additional
333 native motion frames checked header capture, brief-loss rebasing, two-to-
one-hand transitions, resize texture reuse and F11 at three window sizes.
All contexts reported zero GL error; representative screenshots were inspected.
Artifacts: `runs/chemistry-point-pinch-qa/` (ignored). Recorded camera imagery
and synthetic hands were used. No labeled physical-hand trial, >90% recognition
claim, universal-display guarantee, or new latency/accuracy result is asserted.
Camera-image detail still depends on the input resolution/lighting. Physics
remains deferred; accepted main is unchanged.

## Earlier task — renderer timing and chemistry hot-path audit, 2026-10-17

Change: derive animation dt/draw CPU durations and electron phase from
`perf_counter`; reset the dt origin on display-context rebuild. Keep snapshot
freshness on its existing monotonic delivery clock. Project atom labels from
the known camera geometry without per-atom GL state queries. Cache small glyph
textures and draw them every frame independently of the full-window UI texture;
only visible UI state or optional side-camera preview invalidates that overlay.
Delete/rebuild glyph textures with each GL context. Distinguish pending opening
from actual missing input and too-close two-hand span in molecular feedback.

Reason/evidence: further user-requested audit. On this Windows Python 3.12.14,
`get_clock_info` reports `GetTickCount64` / 0.015625 s for monotonic and
`QueryPerformanceCounter` / 1e-7 s for perf_counter. The renderer previously
used the coarse clock for following and CPU durations; session logs contain
quantized draw times. Moving label coordinates also invalidated the full UI
overlay, although only small glyphs had moved. These are code-level sources of
stepped animation and avoidable rendering work, not a physical latency result.

The newer `ui-20261017-162526-970468` session identifies `baf715e` / schema 10.
It still contains real missing-hand samples and visible-hand pending release
near the new hysteresis boundary. Processed frame timestamps continue during
NO_HAND entries; those entries do not by themselves mean camera disconnection.
No processed-frame gap exceeded the chemistry cancellation interval in that
session. Do not keep raising grip thresholds or fabricate hand observations to
hide this. Capture remains a single pending-packet live pump; no new queue,
provider/model/filter/association tuning or quick-press change is introduced.

Canonical files/sections changed: 02 presentation timing/render audit; this
record. Modules: submission renderer, chemistry view, runtime metadata, README,
render regressions. Algorithmic impact: presentation animation timing/render
work and feedback only. Experimental impact: none; Core/replay timestamps,
equations, research data and molecular rules unchanged. Compatibility impact:
UI schema 11 records render clock implementation/resolution; prior coarse CPU
duration logs must not be treated as a paired latency benchmark. Shared renderer
timing also applies to solid/tips, without changing their recognition/controls.
Existing results invalidated: no; accepted main and report evidence unchanged.

Executed: 744 full tests passed on Python 3.12.14 and Python 3.11.9. New tests
exercise advancing animation while the coarse clock stands still, label
projection/clipping at four aspect ratios, independent moving labels/camera
background with static UI reuse, real UI/preview refresh and honest pause text.
Native GL QA rendered 513 frames at three window sizes, including header
capture, one/two-hand transitions, short loss, resizing and F11. At each size,
60 moving-label frames after warmup produced zero full-window UI uploads and
zero new glyph uploads; native GLU projection and pure projection agreed within
pixel rounding. Contexts reported zero GL error. Resize reuse still passed;
a representative screenshot was inspected. Artifacts remain local under
`runs/chemistry-render-audit-qa/`. These use recorded imagery and synthetic
motion, not a new physical-hand success-rate or latency benchmark.

## Earlier task — chemistry grab review after live feedback, 2026-10-17

Change: restore main's observed contact anchors and component response rates;
remove the previous captured-palm XY substitution. Atomic edits follow the
filtered index and components/panel motion use the filtered pinch midpoint.
Keep the cursor on the index throughout capture. Widen only chemistry held-
grip release hysteresis from 0.45 to 0.60, retaining tight 0.28 acquisition,
opening freeze/confirmation and bounded loss/identity cancellation. A recent
header/corner aim survives bounded fingertip displacement while closing pinch;
never acquire through a current button/atom, another page or hand generation.
Retain the prior short-loss pause/rebase, released-hand removal, texture reuse
and captured hit-test fixes. Add actual gate diagnostics in UI schema 10.

Reason/evidence: the user reports jerky motion and failed header dragging.
Session `ui-20261017-161053-978692` identifies `a819a95` and records repeated
visible-hand pauses at raw ratios just above the 0.45 release threshold, as
well as actual missing hands and identity changes. There was no processed-
frame timestamp gap over 0.25 s in that session. Comparison with main shows
the capture/provider/filter path unchanged; runtime differences are metadata.
The new palm anchor discards independent contact movement, and higher display
response passes more input steps to the screen. Restore the baseline behavior
rather than claim those unvalidated changes are an improvement. The thin
header previously required the post-pinch index to hit it anew.

Canonical files/sections changed: 02 chemistry grab review; this record.
Code/modules affected: submission chemistry input/controls/settings, metadata,
README and regression tests. Algorithmic impact: presentation-only capture,
hysteresis and following. Experimental impact: none. Compatibility impact:
schema 10 adds gate state; settings separate push cancellation from grab
release so the deferred quick-press policy keeps its previous value. Existing
results invalidated: no. Core, solid/tips, chemical graph/data and main stay
unchanged. True observation loss still freezes/cancels safely, not extrapolated.

Executed: 737 full-project tests passed on Python 3.12.14 and Python 3.11.9.
Regressions cover recorded threshold crossings, no partial-pinch acquisition,
immediate freeze and release without drift, original-controller pose parity,
contact movement independent of palm, index cursor continuity, cover-invariant
pinch ratio and bounded header aim. Native GL QA rendered 333 frames across
960x660, 1360x860 and 1920x1080 windows, including closing off the actual header,
short loss/rebase, two-to-one-hand transition, resizing and fullscreen. All
contexts reported zero GL error; active resize caused zero texture uploads,
with at most one refresh on release. Representative screenshots were inspected.
Local artifacts: `runs/chemistry-grab-review-qa/`. Recorded raw-ratio replay is
diagnostic only: no human-intent labels, physical gesture success rate or new
camera latency/accuracy result is claimed. No new physical-camera trial was
requested. Quick press and physics remain deferred.

## Earlier task — chemistry drag continuity, 2026-10-17

Change: retain paused panel claims across brief loss/opening confirmation;
rebase at the displayed pose on same-generation return. Use a captured
pinch-to-palm XY offset for held chemistry motion, preserving raw pinch input.
Explicitly remove a released hand from the component controller so two-to-one
hand transitions do not stall for another loss-grace interval. Cancel all grips
without linking on invalid/reversed/over-grace timestamps. Skip redundant scene
picking for captured hands. Keep the panel texture resolution during resize,
then update its final quantized resolution at most once on release if changed.
Chemistry has separate configurable render-following rates for translation,
rotation, scale and held atoms; no second LPF is applied to component poses.

Reason: the user deferred the non-working quick press and prioritized smooth
panel/atom dragging. Inspection found immediate panel-claim deletion during
short loss and a released hand remaining inside the component controller's
missing-hand grace. Raw contact-landmark noise could also move an otherwise
stationary grip. Resize tier changes could trigger rasterization during a drag.

Canonical files/sections changed: 02 chemistry drag continuity; this task record.
Code/modules affected: submission chemistry input/scene/view/settings, runtime
metadata, README and motion regressions. Algorithmic impact: presentation-only
grip anchoring, ownership and render following. Experimental impact: none.
Compatibility impact: presentation schema 9 identifies the new grip policy;
the optional scene advance argument preserves existing callers. Existing
results invalidated: no; Core/provider/Raw/Fixed/Adaptive, research configs,
experiments and molecular data/rules remain unchanged. IndexPush, selection
thresholds, solid/tips tabs and shared GrabController code are unchanged.
The quick-press usability failure remains unresolved and outside this task.

Tests added/updated: short/long panel loss, reacquisition away from the header,
pending opening/bounce, two-hand loss/span rebasing, contact XY noise in atom
and component modes, immediate two-to-one-hand continuation, timestamp
cancellation without accidental bonding, captured hit-test reuse and deferred
resize rasterization. Executed: 723 full-project tests passed on Python 3.12.14
and Python 3.11.9. Native GL QA rendered 312 frames at 960x660, 1360x860 and
1920x1080, including short-loss no-jump resume, hand release/continuation,
resize and fullscreen. Each 60-frame active resize made zero texture uploads;
release made zero uploads at 960x660 (same raster tier) and one at each larger
size. All three contexts reported zero GL error; representative screenshots
were inspected. Local artifacts: `runs/chemistry-motion-qa/` (ignored).
`git diff --check` passed. Recorded imagery and synthetic hands were used;
no new physical webcam trial, end-to-end latency or tracking-accuracy result
is claimed. The accepted main and submission tag remain unchanged.

## Earlier chemistry input follow-up — 2026-10-17

Change: replaced the rejected 2D bend prototype with relative index push,
bounded cursor capture and palm-relative direction/pose/noise checks. Kept
1-second dwell, with a stability radius. Collapsed panels now dock as an inward
arrow on the frame edge; header dragging to/beyond an edge docks without needing
the fingertip to leave the camera. The arrow restores the prior page/pose/scale.
Removed duplicate toolbar toggle/reset; reset is in the spatial panel. Added
undoable clear-all. Hover feedback now draws as GPU geometry instead of
rasterizing/uploading the text panel on each target change.

Reason: user feedback rejected unreliable bend selection and duplicate toolbar
controls. The latest retained local UI session recorded chemistry aim/press
states but no completed quick selection. This is diagnostic evidence of that
prototype's limitation, not a before/after tracking-accuracy benchmark.

Canonical files/sections changed: 01 submission scope; 02 presentation input,
docking/history and schema; this current task record.

Code/modules affected: submission chemistry controls/input/view/scene/settings,
dwell and toolbar; presentation metadata; corresponding submission tests.
Algorithmic impact: presentation-only recognition/feedback; no MediaPipe model,
provider thresholds, Core filters, gesture baseline or molecular grab threshold
changes. Source coordinates supply push features; camera cover remains display
geometry. Pointer lock ends after confirmation feedback or cancellation, rather
than waiting indefinitely for a particular projected finger angle.

Experimental impact: none. Compatibility impact: presentation schema 8 records
the replacement policy and docking state; schema 7 sessions remain historical.
Existing results invalidated: no; Core/replay/config/analysis and report evidence
are unchanged. Physics remains deferred. The accepted main/submission tag is
not part of this development branch update.

Tests added/updated: push/retract, no repeated click, cursor unlock, cancellation,
sideways shake, pure 2D bending, rigid wrist rotation/translation, one-frame z
spike, all-edge docking/restore, inside-camera panel throw, corner-resize
isolation, clear-all undo/redo and native toolbar/arrow regressions. Executed:
711 full-project tests passed on Python 3.12.14 and Python 3.11.9. Native GL QA
rendered 529 frames across 960x660, 1360x860, 1920x1080 and 1080x1000 windows,
including one/two-hand molecular hold/release, anchored push selection, automatic
edge docking, touchless dwell restore, clear-all/undo and repeated fullscreen.
All four contexts reported zero GL error; each 30-frame panel translation
sequence made zero panel texture uploads. Button-hover reuse has a regression
test. Representative screenshots were inspected. Local scripts/results/images
remain ignored under `runs/chemistry-spatial-qa/`; no camera was opened for this
QA. `git diff --check` passed.

The push is a conservative RGB landmark heuristic. It can still miss or confuse
motion under occlusion/noise and is not equivalent to physical contact sensing.
No new physical-hand latency/accuracy evaluation or optimum threshold claim is
made. Dwell remains available without another model or inference pass.

## Initial chemistry iteration (superseded UI policy) — 2026-10-17

Initial authorized task: chemistry first, on `feat/chemistry-spatial-ui` from
the accepted `main` commit `82359a1`. The submission tag/main remain unchanged.
Physics-tab work is explicitly deferred.

Implemented an aspect-preserving camera-cover viewport and the matching
presentation-only landmark XY transform. Source snapshots, detector ROI and
Core/research configuration are unchanged. Panel text uses quantized
supersampled raster resolution and mipmaps. Stationary projection is cached;
translation reuses the texture. The crystal palette supports header drag,
corner resize, two-hand panel translation/scale and mouse drag/wheel. Panel
claims are exclusive with molecular manipulation. Collapse retains a small
title/restore bar and remembers the page; permanent toolbar toggle/reset and
viewport bounds retain recovery after window/fullscreen changes.

The existing 1-second dwell is retained. Optional quick selection uses stable
straight-index aim followed by a confirmed image-space bend. It anchors the
actual displayed cursor before the bend, shares the dwell latch across pages,
and requires extension to rearm. Cancellation and loss do not invent a press.
Presentation schema 7 records the policy and actual tap/panel diagnostic state.
No model, inference worker, chemistry graph rules, molecular gesture thresholds,
element data, presets or previous report results were changed.

Executed: 700 full-project tests passed on Python 3.11.9 and Python 3.12.14.
The current checkout module path was verified in the 3.11 environment. Native
OpenGL QA rendered 371 frames across 960x660, 1360x860, 1920x1080 and 1080x1000
windows with recorded camera imagery and synthetic input. Repeated fullscreen,
all panel page sizes, collapsed restore, mouse drag, one/two-hand molecular
hold/release and one-shot anchored quick selection passed. GL error was zero;
30 translation frames per window caused zero panel texture uploads.
Representative screenshots were inspected; local QA artifacts are in
`runs/chemistry-spatial-qa/` and are not committed. `git diff --check` passed.

These are software regression/display checks, not a new physical-hand latency,
accuracy or low-light evaluation. RGB camera resolution, lighting, occlusion
and viewing angle still limit input and camera detail; dwell/mouse remain
available when the bend is ambiguous. Core experiments/report evidence remain
the previously accepted results.

## Python compatibility correction — 2026-10-16

`pyproject.toml` remains the package authority with `requires-python = ">=3.11"`.
The Windows bootstrap previously narrowed this to exactly Python 3.12; corrected
to accept the declared floor on x64 and let pip resolve compatible wheels.
The 3.12 dependency snapshot remains an explicit `--locked` reproduction mode,
not a restriction on normal 3.11 installation. Setup records the actual resolved
environment under `runs/ui-install/environment.json`.

Executed a fresh Python 3.11.9 installation in an isolated source directory:
model download/hash and initialization passed, pip check passed, 667 full tests
passed, and all three app modes opened/closed for 30 native event iterations each
with the camera off. All screenshots were inspected. Python 3.12.14 also passed
667 tests. This does not assert compatibility of untested future Python versions.

Core algorithms/configuration, presentation gestures/renderer and report evidence
are unchanged. Existing experiment results remain tied to their original recorded
environment; the new flexible installer does not regenerate or replace them.
The corrected handoff uses tag `submission-2026-10-16-r2`; the prior tag is retained.
The source ZIP should be submitted intact with the Word report separately.
Raw experimental video is local and requires a separate dataset handoff only if
the recipient needs to rerun the recorded experiments from source video.

## Submission handoff — 2026-10-16

The user accepted the current UI and authorized finalizing it on `main`.
The submission is identified by tag `submission-2026-10-16`; older UI branches
remain historical and are not required for installation or demonstration.
The primary recipient instructions are `HUONG_DAN_CHAY.md` and the root README.

Windows/Python 3.12 x64 setup now creates a separate `.venv-ui`, installs the
recorded dependency snapshot, downloads version 1 of the official Hand Landmarker
model and verifies its SHA-256. No environment or model binary is committed.
The explicit setup checker verifies imports/assets, installed versions and
model initialization without opening a camera. Source-clean installation was
executed in a separate directory with a new virtual environment: setup passed,
`pip check` reported no broken requirements and all 659 tests passed. The real
app opened/closed in solid, tips and chemistry modes for 30 native event loops
per mode with the camera off; all three screenshots were inspected.

Core source, research configuration, UI renderer/settings and interaction logic
remain the accepted `92d0831` behavior. Report conclusions and recorded research
data are unchanged. This handoff does not claim a new physical webcam session
or universal driver/latency/accuracy guarantees. The Word report is submitted
separately; generated reports, raw video/logs and private study notes are not
part of the source repository. Future feature work should start on a new branch.

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
>>>>>>> 0ec444cf3fb9488c51f457dc3ebc0ae783020982

User-requested lab guidance and optional workspace expansion — 2026-10-03:
implemented in product presentation only. Explore has Vietnamese per-lab guidance
with purpose, mode-aware steps, expected output and limitations; lab, preset,
WORLD/HAND and Control UI changes update it. Normal guide visibility is persisted
with a backward-compatible `lab_guide` preference. Guide and Tools are exclusive.
Phóng to hides navigation/library/side panels; Thu gọn/Esc restores prior layout
without clearing recorded work or changing scale/orientation. Temporary guidance
can open in the expanded workspace without changing the normal preference.
G toggles guidance; Ctrl+Shift+F toggles expansion; F11 remains independent.
Optics shows only preset-relevant controls, with parameter tooltips. Reading help
keeps native scroll keys; layout changes cancel stale input and hidden lists
cannot capture touchless hits. Core/G7 and automatic all-fingertip semantics remain
unchanged. Recorded regression: 909 passed; physical acceptance stays deferred.
Final synthetic QA: 270 OpenGL + 270 software captures, covering nine labs,
WORLD/HAND and five guide/workspace states at 1040×680, 1280×720 and 1600×900.
The model-inclusive source archive contains 246 verified files; extracted
UI/resources/model blank-image smoke and all 909 tests passed. No remaining
implementation/automated check for this request; no physical test requested.
Latest visual/delivery evidence is in release/v2/QA_STATUS.md.

Latest user-requested full extension/UI 3D audit — 2026-10-03: code corrections
and automatic verification are complete. Noncoplanar live vertices now create
closed convex geometry; nearly planar sets retain surfaces. Stable tokens feed
LIVE vectors/probes/labels; hidden recorded data no longer drives LIVE math,
and recorded-tool mode switches no longer block mouse orbit. Coordinate/Vector
fill shapes; other labs keep wire overlays to preserve the actual STEM model.
Inspector prioritizes lab data, with optional XYZ diagnostics. The viewport
states renderer and dimensionality; NH3 uses the NIST 106.7-degree reference,
while frozen H2O/CH4 geometry stays unchanged. Product schema is product-v2-5.
Recorded checks: 886 full-suite tests passed (331 product cases), 23 focused
audit tests passed, 232 final GPU and 232 final software all-preset captures,
24 additional layout captures and 82 native page/RECORDED captures. Source
review and limitations are in release/v2/EXTENSION_3D_REVIEW.md. Physical
acceptance remains deferred; no commercial-readiness/physical-accuracy claim.
Delivery: 244 verified files in the rebuilt model-inclusive source archive;
extracted UI/resources/actual blank-image model smoke and all 886 tests passed
using the separate existing dependency environment. Compilation/dependencies/
format/whitespace passed; frozen Core/evidence diff and release tags unchanged.
No webcam/staging/commit/push/tag action; no remaining code task for this audit.

As of 2026-09-29, the implementation repository has been verified
through Gate G7 and the G7 release is tagged.

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
- frozen G7 final A1/A2/Experiment B trial plans and recorded sources;
- regenerated, provenance-linked G7 metrics, plots, and selected evidence
  under `submission/evidence/`;
- final report and submission instructions included in the tagged tree;
- recorded G7 full regression of 433 passing tests, as stated in
  `submission/README.md`;
- physical final-demo smoke and a separate run recording the exact live
  execution revision, both with clean shutdown;
- annotated `g7-final` tag resolving to release commit
  `f454c6b8325c85199c0122c0e822fe8e76c1526c`.

G0–G7 are complete as the canonical-v1.2 research and submission
baseline. G7 does not establish universal method superiority: A2's
primary metric is unavailable in all three final trials, and the
adaptive P1 path did not activate CLAHE in the analyzed B trials. Final
claims remain limited to the recorded evidence in `FINAL_REPORT.md`.

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
G7 — FINAL EVALUATION / PACKAGE: COMPLETE (FROZEN AT `g7-final`)
G8 — FINAL DESKTOP APPLICATION: COMPLETE; U8 VALIDATED
G9 — PRODUCT V2 EXPERIMENTAL INTERACTION: STASHED / DEFERRED
U10 — SUBMISSION PACKAGING: COMPLETE
R1 — TERMINOLOGY / DOCS ALIGNMENT: COMPLETE
R2 — FINAL SCREENSHOTS: COMPLETE (SYNTHETIC PRESENTATION CAPTURES)
R3 — FINAL APPLICATION PHYSICAL SMOKE: PASS (DOCUMENTED USABILITY LIMITATIONS)
R4 — FINAL RELEASE REVIEW: READY TO RELEASE; COMMIT / TAG PUBLICATION PENDING
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

G0–G7 completion establishes the implemented Core, interaction demo,
reproducible experiment tooling, and the final evidence-bounded report.
It does not imply that the project hypotheses are universally supported
or that one method outperforms another. The unavailable A2 result and
inactive adaptive-CLAHE path remain explicit limitations.

G8 is a separate post-G7 presentation/Extension direction. It does not
change the scope or interpretation of the frozen G7 experiment release.

## 4. Current task

**R4 — Final application release review — READY TO RELEASE; stop before commit/tag.**

G7 research/Core is frozen at `g7-final`. G8 final desktop application and U10
submission packaging are complete. G9 Product V2 experimental interaction is
stashed/deferred; it is not part of the v1.0 application. Final synthetic
presentation screenshots are complete. Real webcam captures are not included
in R2. R3 real webcam smoke passed with user-reported orientation discomfort and
low sensitivity. R4 release review is complete; commit/tag publication remains
pending. No feature, interaction or sensitivity changes belong to this review.

Use “final application” and “application walkthrough” for current product-level
documentation. Preserve historical research wording, evidence labels such as
“RQ3 / Demo”, technical module names `extensions.stem3d.live_demo` and
`extensions.stem3d.demo`, the `demo3d` dependency extra and existing run IDs.

### Final application release roadmap

| Step | Status | Deliverable |
| --- | --- | --- |
| R1 — Terminology/docs alignment | COMPLETE | Current application wording and one consistent release roadmap |
| R2 — Final screenshots | COMPLETE (synthetic) | 15 curated 1600 × 900 images, contact sheet and manifest under `submission/screenshots/`; frozen evidence unchanged |
| R3 — Final application smoke | PASS with usability limitations | Two real webcam runs; all twelve items user-confirmed; clean shutdown/restart logged; see `submission/R3_PHYSICAL_SMOKE.md` |
| R4 — Final release/tag | Review READY TO RELEASE; publication pending | Reviewed source package/notes; create `dip-touchless-stem-v1.0` only on the final reviewed documentation commit |

R1 does not authorize performing R2–R4. Never move, delete or rewrite `g7-final`.
The v1.0 application release is separate from the frozen research identity.

### Advanced interaction backlog — after v1.0

Keep the G9 Product V2 prototype stashed/deferred. Any future grab/release or
motion-mapping investigations, interaction tuning or additional gestures require
a separately approved post-v1.0 scope. User-adjustable sensitivity Settings are
also deferred here following R3 feedback; existing gains/thresholds remain intact.
They are not release blockers and must
not alter the frozen Core or G7 evidence. No backlog implementation starts here.

G8 is not a new research experiment and does not claim commercial
readiness. Any change to Core semantics, public contracts, experiment
metrics, or G7 evidence requires the canonical governance and change
review process.

### Historical completion records

The records below describe their execution-time status. The current stage and
R1–R4 roadmap above supersede earlier “next task” or “not started” statements.

### G8-U6 Evidence Mode completion — 2026-09-30

Evidence Mode displays selected immutable G7 plots and recorded trial values
across six navigable pages. It preserves the A2 unavailable status and reason,
the CLAHE non-activation limitation, A1 trial availability and five-frame
caution, the practical false-positive limitation, and separate release/demo
provenance. Missing images and malformed optional metadata produce explicit
unavailable states.

Focused Extension tests passed (40), the full project suite passed (478),
`compileall extensions/stem3d` succeeded, and six synthetic dashboard pages
rendered for presentation inspection. No physical webcam smoke was run for
U6. The frozen G7 evidence files and `g7-final` tag remain unchanged.

### G8-U7 Commercial UX Hardening completion — 2026-09-30

The dashboard and application controller now expose explicit startup,
component-failure, tracking, and shutdown states. Camera, hand model/provider,
renderer, and dashboard failures remain distinct from ordinary no-hand or
tracking-loss states. Invalid interaction clears stale landmarks, pointer,
panel hover/press, and interaction values; touchless controls are visibly
disabled until interaction is available. Keyboard guidance and contextual
molecule shortcuts match the current DEMO/ANALYSIS/EVIDENCE and three-scene
surface. Evidence asset errors remain separate from frozen experiment-level
unavailability.

Partial renderer/dashboard initialization is cleaned up, shutdown is
idempotent, and cleanup failures are not reported as a clean stop. Focused
Extension tests passed (93), the full project suite passed (499),
`compileall extensions/stem3d` succeeded, and `git diff --check` was clean.
Five synthetic startup, camera/model/renderer failure, and clean-shutdown
screens rendered at the supported minimum dashboard size. No physical
webcam/hand smoke was run for U7.

Core algorithms, research contracts, G7 results/evidence, and the `g7-final`
tag are unchanged. The next roadmap unit is U8 — Automated Validation.

### G8-U7.5 Unified product application shell completion — 2026-10-01

U7 remains COMPLETE. U7.5 is COMPLETE as a separate approved post-G7
presentation refinement; U8 remains NEXT and has not been started.

The live composition now uses a single integrated Pygame/OpenGL window,
one event queue, and a reusable UI texture around the existing scene
drawing code. Workspace is the display label for the existing DEMO mode;
no mode enum or Core contract changed. The same controller, presentation
adapter, scene registry, Evidence catalog, and U5 interaction router are
reused. An OpenCV emergency error view remains available if the GL host
cannot initialize or fails; it replaces the failed host rather than
creating a second normal application window.

Workspace prioritizes the scene and compact Live Vision. Analysis shows
the unmirrored ROI/raw/filtered/pointer preview, all eight pipeline stages,
and compact diagnostics. Evidence retains all six frozen pages, recorded
trial values, unavailable outcomes, limitations, and distinct release/demo
provenance. Session identity is available on demand through Help. Control
Space is a 320-pixel screen-space drawer preserving rising-edge selection,
validity gating, rearm, and the release barrier before scene control resumes.
Help and provenance dialogs prevent mouse clicks through to covered actions.

Visual tokens, cached geometric outline icons, typography measurements,
bounded resized-evidence caching, and reuse of the GL texture are centralized
in the Extension. Hover/press feedback uses presentation time only. Lifecycle
and component-error states remain explicit, with renderer failure identity
preserved by the application controller. Live demo run IDs retain `g8-demo-*`.

Validation executed: 132 focused Extension tests and 538 full-project tests
passed; Extension compile validation succeeded and `git diff --check` was
clean. Synthetic real-OpenGL QA rendered and inspected Workspace scenes,
Analysis, all six Evidence pages, provenance/session details, Control Space,
Help, no-hand/loss, component errors, startup, and shutdown at 1024x640,
1280x720, 1600x900, and 1920x1080. Native SDL resize, keyboard event dispatch,
texture reuse, and cleanup were exercised. These are synthetic presentation
checks, not a physical webcam/hand smoke or new research measurements.
Physical-hand smoke for U7.5: NOT RUN.

Core algorithms, public research contracts, frozen metrics, G7 evidence,
`FINAL_REPORT.md`, and the `g7-final` release identity are unchanged.
No staging, commit, push, or U8/U9/U10/G9 implementation belongs to this task.

### G6 experiment-readiness completion record (historical)

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

At the end of G6, tooling completion alone did not establish final
experiment outcomes or method superiority. G7 outcomes and their
limitations are recorded in the evidence snapshot below and in
`FINAL_REPORT.md`; no FPS, latency, accuracy, or inferential-statistics
claim is made from the G6 tooling tests.

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

No — no final G2+ experiment results existed at the time of this
correction.

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

No — no final G2 illumination results existed when this rule was
recorded.

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

No — no final G2 preprocessing experiment results existed when this
rule was recorded.

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

Fixed landmark 1-Euro core, temporal-filter wrapper, diagnostics,
synthetic tests, and adaptive-filter extension.

Algorithmic impact:

Clarifies the project-specific vectorization layered on top of the
canonical scalar 1-Euro algorithm. The canonical scalar equations are
unchanged.

Experimental impact:

F1/F2 landmark filtering uses independent per-landmark x/y motion
rather than a concatenated all-landmark speed vector.

Compatibility impact:

At the time of this clarification, no completed F1/F2 experiment results
existed.

Tests added/updated:

G3.4 tests cover shared x/y cutoff within one landmark, independence
between landmarks, z pass-through, and preservation of landmark
identity/coordinate space.

Existing results invalidated:

No — no final fixed/adaptive temporal-filter experiment results existed
at the time of this clarification.

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

No completed fixed/adaptive final experiment logs existed at the time of
this clarification. Existing Raw logs were unaffected.

Tests added/updated:

G3.6 tests cover max-speed representative selection, deterministic tie
handling, initialization/no-measurement diagnostics, reset reporting,
and runtime serialization.

Existing results invalidated:

No — no final F1/F2 experimental results existed at the time of this
clarification.

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

Adaptive landmark core, adaptive public LandmarkFilter, configuration
validation, and replay/logging tests.

Algorithmic impact:

F2 beta is explicitly nondecreasing with speed and bounded by configured
beta limits. Optional velocity limiting applies to beta adaptation.
Final cutoff remains independently bounded.

Experimental impact:

Defines the F2 method used in the final G7 comparison with F0 and F1.
Primary F2 does not use measurement-quality adaptation unless a valid
documented source exists.

Compatibility impact:

No adaptive implementation or final F2 result existed when this decision
was recorded.

Tests added/updated:

G4 tests cover beta bounds/monotonicity, velocity spikes, final cutoff
bounds, unavailable quality, invalid dt, reset, and reacquisition.

Existing results invalidated:

No — no F2 implementation or final experimental results existed when
this decision was recorded.

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

F1/F2 run artifacts preserve temporal reset/discontinuity events needed
for auditability and exclusion/debugging.

Compatibility impact:

In-memory `FilterDiagnostics` gains an events field. Existing CSV column
schemas are unchanged; the events artifact now receives the events that
were previously dropped.

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

No — no final F1/F2 experimental result set existed when this change
was made. Earlier development runs may lack these event records and must
not be treated as final event-complete runs.

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

No final experiment result set existed when this decision was recorded.
Development runs produced before this decision may be used for
tooling/debugging but MUST NOT be mixed into final tables unless they
satisfy the frozen protocol.

Tests added/updated:

G6 tests cover metric calculations, paired frame alignment, manifest
validation, deterministic condition expansion, and analysis of generated
run artifacts without manual CSV editing.

Existing results invalidated:

No — at the time this pre-G7 design decision was recorded, no final
A1/A2/B result set had been collected.

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

Analysis regeneration tests cover empty common paired sets producing an
explicit unavailable metric record rather than aborting the entire batch,
while ordinary evaluable trials remain unchanged.

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
The final demo runs, execution identity, observed interaction, and known
false-positive limitation are recorded below and in `FINAL_REPORT.md`.

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

### G7 release closure and G8 transition — 2026-09-29

G7 is complete and frozen at annotated tag `g7-final`, which resolves to
release commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`. The tag tree
contains `FINAL_REPORT.md`, `submission/README.md`, and the selected
generated assets under `submission/evidence/`. The primary live-demo
execution revision `6a87dc50f9d3920ed9fd39a2669e266be00f9735` is recorded
separately in the report and is not the release commit.

The last recorded G7 full regression is 433 passing tests, as reported by
`submission/README.md`. This is a historical project result; no test suite
was run as part of this documentation update.

G7 evidence remains bounded: two of three A1 trials have evaluable paired
metrics; A2 has no evaluable trial; P0 and P1 have equal valid-observation
rates in the retained B trials, while adaptive P1 never activated CLAHE in
the analyzed windows. The live demo ran successfully, with an occasional
face/background false-positive recorded as a limitation. Exact values and
provenance remain in the report and evidence artifacts.

The current branch `feat/final-ui-extension` starts from the frozen G7
release. G8 is promoted as a separate post-G7 UI/Extension roadmap. It is
not a seventh canonical research specification and does not change the
canonical-v1.2 algorithms, G7 measurements, or report conclusions.

Canonical file/section changed:

`05_PROJECT_STATUS_AND_ROADMAP.md`, current stage/task and immediate
roadmap; supplemental direction in `06_G8_UI_EXTENSION_PRODUCTIZATION.md`.

Algorithmic and experimental impact:

None. G7 provenance and all final experiment artifacts remain frozen.

## 5. Immediate next tasks

G7 is closed. U1–U7 and U7.5 are implemented on `feat/final-ui-extension`. U2
provides DEMO/ANALYSIS modes, live ROI and pointer overlays, distinct
raw/filtered landmarks, DIP diagnostics, and run identity from recorded
metadata. U3 defines the `STEMScene` contract and local `SceneRegistry`,
routes scenes through an Extension-owned lifecycle, and leaves Core
unchanged. U4 registers Coordinate Geometry, Molecular Geometry (H2O and
CH4), and Orbital System through the same scene contract. U4-focused tests
pass (56), the full automated suite passes (462), and Extension compile
validation succeeds. An OpenGL renderer smoke opened a visible window,
rendered all three scenes, exercised rotation/scale/reset, switched the
molecule preset, advanced the orbital scene, repeated scene switches, and
closed cleanly using synthetic public `InteractionState` values. It did
not use a webcam or physical hand input. Continue with the post-G7 roadmap in
`docs/06_G8_UI_EXTENSION_PRODUCTIZATION.md`, in this order:

1. **U1 — Application foundation — COMPLETE:** add an application controller,
   immutable presentation state, centralized design tokens, responsive
   layout calculations, and a dashboard shell. Keep the existing live
   demo working while extracting responsibilities incrementally.
2. **U2 — DIP visibility — COMPLETE:** present camera, ROI, landmarks, pointer,
   tracking, illumination, CLAHE, filter, and runtime identity using the
   public read-only realtime presentation seam.
3. **U3 — Scene architecture — COMPLETE:** define the Extension-owned `STEMScene`
   lifecycle and local registry, then migrate the existing coordinate
   cube without changing `InteractionState` semantics.
4. **U4 — STEM scenes — COMPLETE:** provide coordinate geometry, H2O/CH4
   molecular geometry, and a deterministic educational orbital system.
5. **U5 — Spatial Control Panel — COMPLETE:** add screen-space touchless navigation
   using normalized `pointer_xy`, valid pinch rising edges, and explicit
   UI/scene focus routing. Keep all click and focus behavior in the
   Extension.
6. **U6 — Evidence mode — COMPLETE:** display selected frozen G7 assets and retain
   unavailable findings and known limitations without editing or
   regenerating the source evidence.
7. **U7 — Commercial UX hardening — COMPLETE:** make startup and component
   failures explicit; clear stale tracking/interaction presentation;
   disable unusable touchless controls; preserve keyboard fallback; and
   make partial initialization and shutdown cleanup safe.
8. **U7.5 — Unified product application shell — COMPLETE:** integrate the
   existing scene renderer and presentation surface into one normal window;
   refine Workspace, Analysis, Evidence, Control Space, Help, and lifecycle
   states without changing the frozen research baseline.
9. **U8 — Automated validation — COMPLETE for the final presentation pass:**
   Extension/UI tests and full regression executed on 2026-10-01; see below.
10. **U9 / R3 — Physical validation — PASS with usability limitations:** two real
    webcam runs, user-confirmed checklist and clean shutdown/restart are recorded
    in `submission/R3_PHYSICAL_SMOKE.md`; sensitivity/orientation remain unchanged.
11. **U10 — Submission packaging — COMPLETE:** setup/run guides, package-path
    verification, application walkthrough, screenshot checklist and limitations
    are prepared. R2 screenshots and R4 review are complete; commit/tag
    publication remains pending and does not reopen application/packaging work.

G8 is a product-direction phase, not a new scientific evaluation. Do not
add cloud, account, telemetry-backend, or unrelated platform features.

### Final product presentation pass — 2026-10-01

FINAL PRODUCT PASS: COMPLETE within the UI/presentation scope requested by the
user. Starting branch: `feat/final-ui-extension`, HEAD
`30d86f09b4c58fb552b3e54913746acfc53c0b9f`. This pass retains the existing
legacy G7 interaction and the integrated single-window shell. Experimental G9
sources remain outside the working tree; no stash was restored. Two ignored
directories containing only obsolete G9 `.pyc` files were removed after checking
their resolved workspace paths and contents. All five prohibited G9 source paths
are absent, including the two directories themselves.

Workspace uses a compact horizontal scene selector, dominant STEM viewport,
small Live Vision, concise interaction feedback and on-demand controls/help.
ROI and raw/filtered overlays remain in Analysis; Analysis displays the actual
public interaction deltas, filter/illumination state, Core compute timing and
session/frame identity. Evidence is a separate read-only findings view with
Overview, A1 Static, A2 Dynamic, B Normal, B Low-light and RQ3 / Demo sections.
It retains frozen unavailable outcomes, negative findings, limitations and
provenance. Camera framing and background polish change presentation only;
molecule values, orbital behavior and scene transforms are unchanged.

Executed validation:

- `.venv\Scripts\python.exe -m pytest tests/extensions -q --tb=short`: 149 passed.
- `.venv\Scripts\python.exe -m pytest -q --tb=short`: 555 passed.
- `.venv\Scripts\python.exe -m compileall extensions/stem3d`: passed.
- `git diff --check`: passed.
- Synthetic OpenGL/UI QA: 69 local images covering Workspace, Analysis, all
  Evidence pages, three scenes plus both molecule presets, Control Space, Help,
  no-hand, ready/loading/error states and a missing-evidence-asset state. Four
  desktop sizes: 1280x720, 1440x900, 1600x900 and 1920x1080. Images and helper
  scripts are ignored local QA artifacts under `runs/final-product-qa/`, not
  submission screenshots or physical research evidence.
- G7 integrity: 24 Git blobs across report/submission/final manifests and six
  raw PNG SHA-256 hashes match `g7-final`; the peeled release commit remains
  `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- Core, configuration, analysis, frozen report/evidence/manifests and staged
  diffs are empty. No stage, commit or push was performed.

Final UI physical smoke: NOT RUN. Historical G7 live demo evidence remains
historical. No FPS/latency improvement, quantified density reduction, commercial
validation or production-readiness claim is made. U9/U10 remain not started.

Change: final G8 presentation hierarchy, responsive layout, diagnostic visibility,
evidence readability/navigation, camera framing and shared shortcut descriptions.
Reason: finish a polished scientific visualization workspace on the legacy path.
Canonical file/section changed: this status/validation section only.
Code/modules affected: `extensions/stem3d/` presentation code and Extension tests.
Algorithmic impact: NONE; frozen Core and legacy GestureEngine unchanged.
Experimental impact: NONE; no replacement metrics or research evidence.
Compatibility impact: existing InteractionState/scene APIs and resource ownership
preserved; protected renderer framing hook defaults to the original view.
Tests added/updated: desktop geometry, drawer overlap, actual Analysis output,
evidence navigation, error guidance, camera framing and read-only ROI presentation.
Existing results invalidated: no.

Implementation stopped after verification. Recommended single commit (not made):
`feat(stem3d): finalize product presentation`.

### U10 submission and application preparation — 2026-10-01

The preceding final-product-pass entry is historical. Its changes are now
committed at `7bd1ebb` (`feat(stem3d): finalize product presentation`), the clean
starting revision for this task. U10 preparation is COMPLETE within the user's
documentation/verification scope; physical validation, final captures and release
are pending. No new feature phase was started.

Updated root/submission entry guides and added `submission/DEMO_GUIDE.md` and
`models/README.md`. Setup includes the `demo3d` extra, the pinned model download
and checksum, root-relative resources and writable session output. The application walkthrough
is Workspace → Analysis → Evidence → STEM scenes with existing keyboard fallback.
The live Raw/F0 path and frozen F1/F2 evidence are distinguished explicitly.

Executed checks:

- `.venv\Scripts\python.exe -m pytest -q`: 555 passed.
- `.venv\Scripts\python.exe -m compileall extensions/stem3d`: passed.
- `git diff --check`: passed.
- `.venv\Scripts\python.exe -m pip check`: no broken requirements.
- Existing environment imports/version checks and actual model initialize/close:
  passed without a camera. No fresh-environment installation is claimed.
- Local ignored source preview: 173 files, ZIP CRC/content checks, extracted
  Core/application imports and config/frozen-resource paths passed. This working-tree
  preview includes the new guides, excludes the model/environment/caches/runs,
  and is not a tagged release or the final hand-in archive.
- Frozen checks match `g7-final`: 23 blobs across `FINAL_REPORT.md`,
  `submission/evidence/`, `experiments/final/`, plus six PNG SHA-256 hashes.
  This count excludes the intentionally updated, non-frozen `submission/README.md`.
  Tag peeled commit remains `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- Core/config/analysis/frozen/staged diffs empty. Five G9 source paths absent;
  existing G9 stash retained at `d709da693e6adc4dec94e6925e7cd202ae0dd507`.

Physical webcam smoke: NOT RUN. Existing automated lifecycle tests cover startup,
cancellation, component errors and cleanup; no physical shutdown observation is
claimed. No additional obsolete production/debug code was clearly safe to remove;
the synthetic renderer smoke and ignored QA artifacts remain separate from the
final application and submission evidence.

Canonical change: current status and validation only. Algorithmic, experimental,
interaction, sensitivity, dependency and UI architecture changes: NONE. Existing
results invalidated: no. No stage, commit, push or tag performed. Recommended
commit: `docs: finalize submission and demo package`; release preparation should
use a new post-G7 tag only after review and record any omitted physical validation.

### R1 terminology/docs alignment — 2026-10-01

Aligned current README, model setup, submission guide and application walkthrough
wording; updated the current stage/task and supplemental roadmap to R1–R4.
Recommended application tag: `dip-touchless-stem-v1.0`. Historical completion
records and technical identifiers remain intact. R1 changes documentation only;
Core, interaction behavior, sensitivity, UI architecture, evidence, experiments
and G7 artifacts are unchanged. Validation: `git diff --check` passed.
No stage, commit, push, tag, screenshot capture, physical smoke or later roadmap
step was performed by this alignment task.

### R4 final application release review — 2026-10-01

READY TO RELEASE with the documented R3 usability limitations. Review covered
all pending status/package/walkthrough/R3 documentation, the committed R2 images
and provenance, launch/model/dependency instructions, and the source-package path.
Added `submission/RELEASE_NOTES_v1.0.md`; corrected the source-archive guide to
include committed screenshots and to exclude the ignored external model.

Executed validation: 555 tests passed; `compileall extensions/stem3d`,
`git diff --check` and existing-environment `pip check` passed. Local working-tree
source preview: 193 files, ZIP CRC/content, extracted imports/resources and 43
local Markdown links passed. R2 dimensions/hashes, R3 run identities/frame counts
and the local model SHA-256 were verified. No fresh-environment installation or
new physical run is claimed by R4.

Core/config/experiments/analysis match the frozen G7 tree; application/tests match
the R3 execution revision `21ab8cddf037c9f21f33ca6f2ec8fb237eaebb72`. All 23 frozen
file SHA-256 hashes and `g7-final` remain unchanged. All five G9 source paths are
absent; the existing stash is retained. Interaction semantics, sensitivity and
UI architecture changes: NONE. Python Core package version `0.1.0` is unchanged;
v1.0 identifies the application release.

Recommended final commit: `docs: finalize v1.0 release notes and smoke record`.
Include only `README.md`, this status document, `docs/06`,
`submission/README.md`, `submission/DEMO_GUIDE.md`,
`submission/screenshots/README.md`, `submission/R3_PHYSICAL_SMOKE.md` and
`submission/RELEASE_NOTES_v1.0.md`. The screenshot binaries and R1/R2 guides are
already committed at `21ab8cdd`; local QA ZIPs/helpers/logs are not commit inputs.

`dip-touchless-stem-v1.0` was absent locally and on `origin` during review. It is
safe to create on the final reviewed documentation commit after that commit is
made; current HEAD does not yet include the pending R3/release documentation.
No stage, commit, push or tag was performed. Release publication remains pending.
