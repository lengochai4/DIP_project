# 02 — Architecture and Contracts

**Specification set:** Canonical v1.2  
**Status:** Normative for module boundaries, public semantics, and runtime/data contracts

## 1. Architectural goals

### Physics presentation contract — authorized 2026-10-18

The applied mechanics tab owns a pure, renderer-independent SI model and bounded
fixed-step accumulator. It imports no Core algorithm internals and consumes the
same immutable submission snapshots. Eight scenario-specific state equations and
constraints replace arbitrary rigid-body simulation. Source timestamps continue
to govern hand selection; simulation time advances independently from render
elapsed time with configured catch-up bounds. Pausing/hidden tabs never accrue
wall-clock debt. Visual zoom is independent of physical parameters. Native GL
resources must survive context recreation through explicit close/open lifecycle.

PointPinch and DwellSelector may be reused without changing chemistry. Targets
are typed: menu commands, explicit parameter handles, body/launch handles and
panel handles. Capture ownership is exclusive; generation/loss/stale/source or
viewport discontinuities cancel edits without throwing the object. Editing
pauses the model, rebases after loss, and requires explicit run to start. A
second hand may manipulate another free handle; never steal a menu gesture or
an already-owned handle. Parameter ranges, time steps, capacities and gesture
settings are external configuration. Model-relative z is not physical depth.

Physics interaction refinement (2026-10-18): index-tip aim still chooses the
handle, but a held edit follows filtered wrist/MCP centroid translation rather
than thumb-index separation. Keep the acquisition offset; folding the contact
fingers alone must not move a value. The last genuine observation is followed
at render cadence through a configured first-order response, with the claimed
cursor using that same displayed position. Opening intent freezes immediately
before the normal release confirmation; missing observations, consumed/docked
claims and release never advance a pending follow target. A short return
rebases to the current displayed value, without a throw or delayed catch-up.
This presentation interpolation does not create provider observations or alter
Core timing/filter equations. Prefer the nearest visible handle in overlapping
hit radii. Scene orbit/zoom handles own the view exclusively against parameter
edits; separate parameter handles retain two-hand ownership.

Capture and retain the current fit bounds during/after an edit so auto-fitting
cannot masquerade as object motion when the hand releases. Run, reset, lab
selection or explicit frame reset may refit. Orbit is bounded away from edge-on
views for these planar models; zoom/orbit do not change SI quantities. Plane
edits reject near-parallel or backward ray/plane intersections instead of
amplifying them into extreme parameter values. Header
drag beyond an edge may dock after a short hold or a larger throw, with a
remembered edge/position and inward arrow. Docked close remains consumed until
opening. Panel translation reuses cached pixels and moves hit rectangles;
parameter readouts refresh at the configured UI cadence, while page/size and
commands refresh immediately. Physics gesture/view tuning is captured in UI
settings; the SI catalog/hash and saved-state schema remain unchanged. UI log
schema 15 adds consumed-finish state and names the Physics movement policy.

Follow-up correction (2026-10-18): orbit and zoom are explicit selectable view
tools, not button-looking drag handles. Dwell/pinch selects the tool; keep that
menu gesture consumed. After opening, a fresh pinch anywhere in the camera
canvas outside the panel controls rotates/resizes the scene. Panel commands
retain priority, visible tool/help identifies the active mode, and Edit, run,
reset, frame or lab selection returns to normal manipulation. Selecting the
active tool again also returns to Edit. Do not couple these view changes to SI.

Once a Physics claim crosses the opening threshold, keep it frozen while the
ratio remains between tight acquisition and opening. Confirm release from
configured duration and valid-observation count even if the ratio settles back
into that band; only tight contact cancels opening and neutrally rebases.
Reset pending opening evidence on loss; ambiguous contact cannot resume a
paused claim. Missing observations never count as opening samples. Shared
PointPinch, PinchGate and chemistry behavior are unchanged. UI schema 16 records
active Physics tool and per-claim opening state, and names the release policy.

Model contact-break correction (2026-10-18): model-space body/force/angle/launch,
length/load/rope/velocity and ruler handles use their own tighter configured
hold boundary before starting the existing opening latch. Stop at the currently
displayed position and discard the pending render-follow target at that point;
do not complete or snap to the last camera target. Panel headers, parameter
sliders, orbit/zoom and button selectors keep their existing boundaries. This
is a presentation policy/configuration change; the UI schema remains 16 and
the added model-hold setting is captured in the resolved UI configuration.

Design reference (affordances and separate movement/rotation/scale targets):
[Microsoft direct manipulation](https://learn.microsoft.com/en-us/windows/mixed-reality/design/direct-manipulation).
This guides presentation design; it transfers no HoloLens accuracy/performance
claim to a monocular RGB webcam.

Local state/export has its own version and bounded validation. Simulated SI
measurements, constraints/assumptions, A/B inputs and initial conditions must be
preserved. They are not experiment evidence for RQ1/RQ2 or measured camera-world
values. Unit/analytic/invariant checks and actual native renderer checks are
required; commercial/accuracy/latency claims require separate real evidence.

The system MUST be:

- small enough for a final-term project;
- modular enough to test without a physical webcam or renderer;
- deterministic enough for paired experiments;
- explicit enough for a new human or AI contributor to implement correctly;
- replaceable at external-provider boundaries;
- free of unnecessary service/framework complexity.

Microservices, distributed backends, plugin marketplaces, and dependency-injection frameworks are not required.

## 2. Logical pipeline

```text
FrameSource
   ↓
FramePacket
   ↓
ROIManager
   ↓
IlluminationAnalyzer
   ↓
AdaptivePreprocessor
   ↓
LandmarkProvider
   ↓
MeasurementValidator
   ↓
TemporalFilter
   ↓
TrackingFrame
   ↓
GestureEngine
   ↓
InteractionState
   ↓
3D STEM Extension
```

Cross-cutting research output:

```text
Frame/Tracking diagnostics + timings
                 ↓
             RunLogger
                 ↓
         versioned run artifacts
```

## 3. Runtime separation

### 3.1 RealtimeRuntime

Purpose: interactive demonstration and operational smoke testing.

It MUST:

- acquire webcam frames;
- assign/propagate monotonic timestamps;
- execute the same Core components used by replay;
- expose the latest `InteractionState`;
- remain safe when no hand is present or tracking is lost;
- collect diagnostics without redefining algorithm semantics.

For presentation-only realtime UI, `RealtimeRuntime` MAY expose an
optional callback invoked once per processed frame with the public
runtime outputs:

```text
FramePacket presentation copy
TrackingFrame
InteractionState | None
```

The presentation `FramePacket.image` MUST be a copy of the acquired
camera image so drawing or annotation in presentation code cannot mutate
the image buffer used by Core processing. The callback is read-only with
respect to Core behavior: it MUST NOT replace preprocessing, tracking,
filtering, gesture, logging, or experiment semantics.

This presentation seam does not change the 3D Extension boundary. The
3D STEM Extension continues to consume `InteractionState` only.

The course baseline SHOULD use synchronous processing for clarity. Async/latest-frame execution is FUTURE unless separately specified and tested.

### 3.2 ReplayRuntime

Purpose: deterministic experiments and regression tests.

It MUST:

- consume a recorded/synthetic ordered source;
- preserve deterministic frame order;
- preserve recorded timestamps or construct them by a documented fixed rule;
- run alternative configurations on the same source sequence;
- produce the same public contracts/log artifacts as RealtimeRuntime where applicable.

Paired algorithm comparisons SHOULD use ReplayRuntime. Realtime behavior may be measured separately when the live camera itself is part of the question.

## 4. Component boundaries

### 4.1 `FrameSource`

Required implementations:

- `OpenCVCameraSource`;
- `ReplayFrameSource`.

Recommended test implementation:

- synthetic/mock source.

Acquisition MUST NOT perform hidden preprocessing.

### 4.2 `ROIManager`

Owns ROI state and geometry only. It does not call MediaPipe and does not alter pixels.

### 4.3 `IlluminationAnalyzer`

Reads ROI pixels and produces illumination descriptors/state. It does not mutate the frame.

### 4.4 `AdaptivePreprocessor`

Applies bypass/CLAHE behavior selected from configuration and illumination state. The course baseline preserves full-frame dimensions and detector geometry.

### 4.5 `LandmarkProvider`

Project-owned interface around an external hand-landmark implementation. The required course provider is a MediaPipe Hand Landmarker adapter.

Provider-specific classes MUST NOT leak into downstream Core modules.

### 4.6 `MeasurementValidator`

Converts provider output into project-domain status/contracts and decides whether a usable observation exists. It also carries optional documented measurement quality; it MUST NOT synthesize one merely because the filter can consume one.

### 4.7 `TemporalFilter`

Required modes:

```text
RAW
ONE_EURO_FIXED
ONE_EURO_ADAPTIVE
```

Algorithm semantics are defined only in `03_ALGORITHM_AND_EXPERIMENTS.md`.

### 4.8 `GestureEngine`

Consumes filtered project-domain landmarks and emits renderer-independent interaction state. It does not know MediaPipe objects or scene classes.

### 4.9 `RunLogger`

Records machine-readable run artifacts. Logger failure MUST be explicit and MUST NOT fabricate missing measurements.

### 4.10 `3D STEM Extension`

Consumes `InteractionState` only. It MAY manage renderer/scene/application behavior but MUST NOT reach into ROI, tracking, filtering, or experiment internals.

## 5. Dependency direction

### Additive submission presentation boundary — 2026-10-14

#### Visual refresh and chemistry confirmation — authorized 2026-10-14

The user requested a visual-only refresh using the supplied design/assets,
an exact author badge, responsive controls, sharper 3D materials and a
translucent crystal-styled panel. Processing/filter/performance telemetry
stays in local logs; sample FPS values in mockups are omitted from the UI.
Fullscreen button and F11 share one reversible SDL desktop-fullscreen
transition without changing monitor resolution. They remember the current
monitor, restore window dimensions and position, and rebuild context-owned
resources. Stale resize events from a previous fullscreen transition must not
resize the restored window.

Chemistry panel actions now use configurable 1-second continuous fingertip
hover with visible progress and a one-shot latch. Leaving the target, missing
observations, identity change, timestamp discontinuity or stale input cancel
progress. A just-activated target must not rearm through a page change until
the pointer deliberately leaves the panel or moves to a different region.
Pinch manipulates objects or explicit panel handles (added 2026-10-17).
Chemistry grab uses separate
tight normalized thumb-index press/release thresholds; it is an image-space
heuristic, not sensing physical contact. Existing chemical graph rules,
history/save/load, Core gesture/filter/replay semantics remain unchanged.

Following the user's chemistry continuity/zoom feedback, a confirmed closed
grip may acquire an object upon entering its target. Opening hysteresis and
short loss grace are configured separately for chemistry; missing input
freezes motion and reacquisition rebases without extrapolation. In whole-
component mode the second hand may join the held component from free space,
but not through panel buttons. Selected electron view uses a selection volume
around the illustrated shells. Nucleus, electron radii and selection volume
share the stored object scale; framing includes the shell extents. UI schema
5 adds actual dwell/claim/group state to local interaction diagnostics.

The submission UI may select either the local OpenCV webcam or a presentation-
only DroidCam Wi-Fi source using the phone's explicit IP/port. The Wi-Fi source
reads the documented HTTP `/video` feed and emits the same raw BGR
`FramePacket` contract. Source switching is serialized: the current live
worker/capture must finish closing before the requested source is opened.
The acquired BGR frames continue through the same Core preprocessing,
landmark, filtering and gesture path; replay behavior and research baselines
are unchanged. Network quality/latency is an input-device property and is not
treated as a new algorithmic result.

Opening the camera-settings dialog suspends scene input and cancels existing
claims/dwell without clearing the scene. Cancel/quit during a pending source
switch must not start a new capture. Live packets whose timestamps round to
the same MediaPipe millisecond are skipped before Core processing, retaining
original timestamps and logging the skipped count. Replay retains its strict
timestamp validation; no research timing or filtering semantics change.

#### Camera chemistry mode — 2026-10-14

The renderer may composite the immutable mirrored BGR camera snapshot as
the scene background. A camera-aligned perspective scene, textured spatial
panel and atom/bond geometry use WORLD_RENDER. Hand targets map through the
same aspect-preserving center-cropped cover rectangle and perspective ray;
the crop fills the chemistry scene panel, with source XY transformed only in
presentation copies of hands. Core snapshots/ROI remain unchanged. Arbitrary stretch
or a second mirror must not misalign targets and the camera image.
The panel is display-anchored, not localized to a physical room. No physical
hand/object occlusion or depth sensing is implied. Panel selection uses the
continuous observed hover contract above, with a mouse fallback. Each hand
may claim one object; generation/loss/stale input release claims safely.
A latched panel selection cannot trigger repeatedly.

The revised 2026-10-17 interaction replaces the rejected index-bend prototype
with a presentation-only relative index push. Stable extended-index aim arms
the target. Model-relative tip displacement along the observed palm normal,
normalized by apparent palm size, supplies a non-metric forward-motion cue.
Source-space raw landmarks, not cover-cropped display coordinates, supply
these features. Feature smoothing/noise bounds, direction, travel, observation
count and timing gates reject ambiguous motion. Rigid hand translation is
subtracted; lateral movement, excessive rotation/scale change, pinch, claims,
loss/invalid input or identity/time discontinuity cancel. These are heuristics,
not proof of physical touch or complete shake/press separability from RGB.

Only a coherent press captures the actual displayed XY; confirmation provides
brief bounded feedback, then ordinary cursor motion resumes even if the finger
stays forward. Retraction or deliberate departure rearms. Push and dwell share
one activation latch across page changes. Dwell remains 1 second and requires
bounded positional stability; shaking across a large button must reset progress.
All tunable thresholds live in submission settings, outside Core/research config.

Panel header/corner claims are exclusive with atom/component claims. A header
pinch drags; the corner resizes; two simultaneous panel grips translate and
uniformly scale, independently of molecular scale. Releasing or losing a panel
hand freezes/rebases the layout. Mouse drag/corner/wheel are fallbacks. Collapse
retains only an inward arrow on the scene edge, preserving page, expanded pose
and scale. The arrow has priority hit testing and supports dwell/push selection.
Moving a claimed header into the edge briefly, or throwing it beyond the edge,
docks it there; corner resize cannot dock it. Duplicate toolbar toggle/reset
controls are removed. Reset remains in the spatial panel; B/mouse are optional
fallbacks. A held pinch cannot immediately reopen the docked arrow. Layout is
clamped to the viewport after resizing/fullscreen, which cancels input claims
before changing projection. Panel translation reuses its texture; scale uses
quantized raster resolution and progress remains GPU geometry.
Hover outlines are also GPU geometry and must not invalidate the text texture
when the pointer moves between buttons. Only visible semantic content or
quantized raster resolution changes require panel rasterization/upload.

Clear-all is an explicit spatial-panel action that removes atoms/bonds and
selection in one undoable history step. Repeating it on an empty scene is a
no-op. It does not alter element data, bonding rules, presets or file formats.

A renderer-independent chemistry scene owns sourced element data, atoms,
bond topology, history and explicit action modes. Whole-component grab may
reuse the submission GrabController for one/two-hand movement/rotation/scale.
Atomic edit moves one atom and separates bonds only in the explicit edit
mode; nearby permitted atoms may link on deliberate release. Display atom
radii/positions are scene units, not physical atomic distances. Formula
counts and verified small graph labels must not claim a reaction or stability.
Electron shells are an illustrative neutral-atom model, not electron paths
or computed quantum orbitals. No chemistry logic is added to DIP Core.

The user authorized an expanded 32-preset neutral covalent library. Presets
must be connected, have finite display positions, valid bond orders and the
configured complete neutral valences. Identification is exact element/bond-
order graph matching, with candidate pruning and a bounded topology cache;
motion/display scale must not change the molecular name. Stereochemistry,
ions and resonance remain outside this library. The spatial palette paginates
eight entries per page so every preset remains reachable without overlapping
existing controls. Preset coordinates are authored illustrative scene units.

Chemistry's discrete pinch gate reuses the exact raw ratio, hysteresis,
confirmation/loss durations and generation behavior without computing an
unused object pose. Held components continue to use GrabController. The panel
texture depends only on visible panel content and raster resolution; hovering
atoms, moving objects or changing bond topology must not repaint an unchanged
panel. Selection/page/control changes update immediately. Scientific graph
labels remain owned by the scene/overlay, independently of the panel texture.

#### Point-and-pinch menu confirmation — authorized 2026-10-18

The default presentation selector is now `point_pinch`, alongside unchanged
1-second dwell. The prior unsuccessful `index_push` remains an explicitly
selectable experimental configuration, not the default or a proven gesture.
This replaces the default quick-selection policy described historically below.

Require an observed open hand and stable aim at an actual menu button before
arming. A gradual close may retain that button within configured position/time
bounds. Capture the actual displayed cursor when closure passes the configured
capture ratio. Require tight raw XY pinch, a minimum observation count and
confirmation duration before emitting once. Do not use model-relative z to
infer touch. After feedback the cursor unlocks even if pinch stays closed.
Release confirmation and fresh stable aim are required before another explicit
selection; this permits deliberately selecting the same tile again. Dwell
keeps its existing leave/rearm behavior. A dwell activation consumes the current
menu gesture so a coincident pinch does not immediately activate twice.

While a menu pinch is captured/latched it cannot acquire an atom or header
behind a changed/collapsed page, join a molecular grab or start another dwell.
Existing object/header claims block menu confirmation. Thumb-index holds on
atoms/header/corners still use their original gate and movement controllers.
Partial pinches, opening before confirmation, excessive motion, time/identity
discontinuity, invalid/missing observations and stale/source/viewport changes
cancel safely. A reacquired already-closed hand cannot arm a menu click.
Consumed selection/cancelled-capture intent is retained through brief loss and
page changes until opening, so a closed returning hand cannot acquire an object
behind the button. This retains no missing hand geometry and does not freeze
the ordinary cursor. An incomplete cancelled capture still permits dwell.
All tunable aim/capture/timeout/observation settings live in submission settings.

Selection-stability correction, 2026-10-18: after initial stable aim, small
movements inside the same button update the armed origin instead of repeatedly
restarting aim against an old origin. Initial capture still bounds fingertip
displacement; after capture, cancellation bounds observed XY palm translation
relative to captured palm size, allowing independent finger closure. This is a
decision check only, not a synthetic palm-based cursor or manipulation anchor.
Require at least two tight contact observations; a separate narrow hold-ratio
band preserves confirmation through small contact jitter. Partial pinches and
one tight spike cannot confirm. The captured target owns dispatch until release
or cancellation, and a smoothed cursor may replace its visual anchor only when
it lies on that same target. UI schema 13 adds observed selector ratio and
cancellation reason. Dwell, object/header gates, movement and Core stay unchanged.

The initial window is fitted to the current desktop minus configured chrome
margins. Later user resizing/fullscreen restoration is not repeatedly shrunk.
At compact widths the top controls and solid controls wrap to extra rows;
the camera scene reserves that space. Author glyphs stay inside their badge,
with spacing derived from font metrics. Sidebar content is clipped to its card.
Panel font loading falls back if the Windows font file is absent. UI schema 12
records selector mode and actual window dimensions/fullscreen in local logs.
Core/replay/filter/report data remain unchanged. Simulated regressions establish
software invariants only, not physical-hand recognition accuracy.

Interaction reference: Microsoft point-and-commit design (concept only; this
RGB implementation does not inherit HoloLens tracking or performance):
https://learn.microsoft.com/en-us/windows/mixed-reality/design/point-and-commit

#### Presentation timing and chemistry render audit — authorized 2026-10-17

Renderer animation dt, draw CPU-duration diagnostics and illustrative electron
phase use `perf_counter`, not a potentially coarse platform `monotonic` clock.
Reset the renderer dt origin when rebuilding the display context. Snapshot
freshness remains in the existing `monotonic` delivery-clock domain; Core
filters/replay still derive timing from original frame timestamps. Presentation
schema 11 records the render clock implementation/resolution. Earlier timing
logs retain their old clock precision and are not a paired latency benchmark.

Chemistry atom labels use the known camera projection, with near/far/viewport
clipping, without per-atom GL matrix/viewport queries. Small cached glyph
textures follow atoms each draw and are clipped to the chemistry view. Moving
labels do not invalidate the window-sized UI overlay. Static UI refreshes on
actual content/control changes; an explicitly enabled side-camera preview
continues refreshing at its existing bounded cadence. Label textures belong
to the GL context and must be deleted/recreated on resize/fullscreen/shutdown.

Pending release is not reported as tracking loss. Footer feedback distinguishes
visible-hand opening confirmation, actual missing observations and a too-small
two-hand grip span. This changes feedback only; pinch/loss thresholds and
capture ownership retain the preceding chemistry-grab-review policy.

#### Chemistry grab review — authorized 2026-10-17

This review supersedes the captured-palm anchor and higher response rates
below. Restore observed filtered pinch-midpoint translation for components
and panel handles, and index-tip translation for atomic editing, matching
the original main interaction anchors. Do not rewrite contact landmarks to
follow the palm. The rendered cursor remains at the observed index during
capture. Restore main component display-following rates; panel following
uses its own configurable rate. Core/source observations remain immutable.

The user's schema-9 session contains repeated visible-hand pauses near the
0.45 release threshold, alongside actual missing/changed hand observations.
Keep tight initial acquisition, but widen chemistry's configurable held-grip
hysteresis to 0.60. This tolerates small separation after acquisition, not
proof of physical contact. Opening confirmation, generation/loss cancellation
and immediate motion freeze during confirmed-opening pending remain intact.

A recently aimed panel header/corner may be acquired while pinching just off
the handle within configurable time and aspect-correct screen-distance limits.
Identity/page change, expiry and distance invalidate it; an actual button or
atom target must never be stolen by the retained aim. This is capture intent,
not a new click gesture. Push policy is deferred and unchanged. Presentation
schema 10 records the policy and raw gate held/pending/suspended diagnostics.
Keep the prior short-loss pause/rebase, immediate released-hand removal,
captured hit-test reuse and deferred resize rasterization fixes.

#### Earlier chemistry drag continuity — superseded anchoring, 2026-10-17

The user deferred quick selection and prioritized continuous panel/atom drags.
No IndexPush policy or Core/provider/filter/other-tab behavior changes here.
For a confirmed chemistry hand claim, capture the filtered pinch-to-palm XY
offset. Translation follows the observed filtered palm center plus that captured
offset; ordinary unclaimed pointing remains the index fingertip. This stabilizes
contact-landmark noise without mutating source observations or inventing depth.
Whole-component rotation/scale still use GrabController; presentation copies of
the two contact XY points carry the stable anchor while raw pinch stays raw.

Panel claims, like atoms/components, pause and retain ownership during the
configured brief loss/opening-confirmation interval. Freeze the displayed pose;
clear the panel motion target; on valid same-generation return, capture a new
anchor and rebase at the displayed pose before continuing. With two panel grips,
one paused owner freezes both; joining/leaving rebases the span. Confirmed
opening, timeout, generation/source/viewport discontinuity still release safely.
Do not link atoms on loss. A confirmed release removes the hand immediately
from the component controller instead of treating it as a missing hand and
stalling the remaining hand for another loss-grace interval.

Chemistry-only display response rates are configurable and separate from the
Core filter and other tabs. A held atom has one render-rate follower; component
motion already follows in the controller and must not receive another LPF.
Captured hands do not repeatedly hit-test the scene. Panel movement/size/hit
geometry update every draw; during a panel claim keep the existing texture
resolution, then refresh the final quantized resolution once when released if
needed. Semantic content changes remain immediate. Presentation schema 9 logs
this grip policy and uses paused claims for actual loss/opening state.

#### Spatial presentation and freshness refinement — 2026-10-14

The user authorized further responsiveness and spatial manipulation work.
Only the submission live camera may use an acquisition thread with one
replaceable pending packet. Unprocessed camera packets may be dropped;
accepted packets retain increasing original frame IDs and timestamps.
The filter derives dt from those timestamps. Replay never uses this pump
and preserves every source packet in order. Capture and close belong to
the acquisition thread; stop/retry must not overlap camera owners.
UI schema 3 records dropped packets and acquisition-to-processing wait,
not physical sensor-to-photon latency. Missing hands remain explicit.

Presentation-only render response may increase within configured bounds
as pose error grows; it must not predict absent hands. Within-hand model z
may be smoothed for illustrative orientation/geometry separately from Core
outputs, which retain their original z semantics. Two-hand rotation may
combine screen-plane baseline twist with the average valid palm tilt.
An explicit one-hand push/pull mode maps apparent palm-size ratios to
bounded display z translation, never metric camera depth.

Live geometry uses a convex 3D hull when the observed relative-z geometry
is sufficiently nonplanar; near-planar points form a triangulated surface
using observed fingertip vertices only. No automatic prism/extrusion is added
(user-reported extra vertices, 2026-10-14). All selected fingertips remain nodes,
including interior points. Within-hand skeletons may be shown as lit joint
spheres/bones. Framing stays fixed within a continuous hand-identity session
so hand translation and apparent size changes are not normalized away.
Geometry and display filtering are submission-only, not research outputs.
Quick refinement requested by user: fingertip scene scale is fixed by UI
configuration, not divided by the span of currently selected tips. Initial
centering uses the whole observed hand geometry, so folding fingers or a
short reacquisition cannot trigger excessive automatic enlargement.

#### Interaction continuity refinement — 2026-10-14

The user requested fixing intermittent grab, scaling and stretching.
Presentation slots may retain association and public filter state for a
bounded short observation gap, while the snapshot still exposes no missing
hand geometry. An identity generation increments on a new/reset/ambiguous
assignment; no grab may transfer between generations. A UI-only pinch
recognizer may apply palm-normalized hysteresis and timed press/release
confirmation to validated filtered landmarks. It does not replace the
canonical GestureEngine or its recorded InteractionState semantics.

Short loss freezes the current object pose during a bounded grip grace
period; it never extrapolates absent hands. Recovery rebases from the held
pose. Expiry, identity replacement, stop and stale input terminate the hold.
Input updates set target pose; each renderer frame independently advances
the display pose with timestamp-derived smoothing and quaternion rotation.
Explicit release freezes immediately, preventing post-release drift.

Presentation scaling includes uniform two-hand span scaling, bounded
one-hand apparent-palm-size scaling, and an explicit two-hand stretch mode.
Stretch acts along the dominant object-local axis selected at attach time;
this is display deformation, not a measured physical distance. Screen-plane
translation and twist map through the inverse view rotation. Model-relative
z is used only for within-hand illustrative orientation and visualization.
UI-owned temporal-filter parameter overrides may be resolved and captured
under condition UI_INTERACTION. They reuse the unchanged public bounded
adaptive filter implementation, are not the F2 research parameter profile,
and may not be mixed into G7/ROUND2 results. Their values are engineering
defaults, not measured optima. Baseline configuration files remain unchanged.

The new submission composition root may reuse public Core components
in a separate application runtime with a provider configured for up to
two hands of one operator. Existing RealtimeRuntime, ReplayRuntime,
InteractionState and one-hand provider semantics are unchanged.

The composition root converts provider results to validated project-owned
LandmarkObservation objects, maintains separate filters/gesture engines per
associated hand, and produces an immutable presentation snapshot containing:
frame identity/time, a non-shared BGR preview copy, valid raw and filtered
landmark tuples per hand, InteractionState per hand, and explicit illumination/ROI
diagnostics. The renderer consumes this snapshot and application geometry,
never provider objects or mutable algorithm state. Unavailable hands produce
no geometry; identity discontinuity/loss clears that presentation slot.

Submission raw observations identify discrete pinch/extension transitions;
filtered landmarks still drive motion geometry. Visible opening freezes motion
on its first observation while release confirmation completes; reacquisition
uses the displayed pose. This avoids using motion smoothing to delay release.
Finger selection also requires fingertip reach beyond the bent joints. Joint
spheres of unselected fingers are omitted from the default fingertip scene.
UI schema 6 records the raw pinch-state input basis. Renderer-only antialiasing,
cached supersampled cards and panel mipmaps may improve display quality with
an explicit supported-context fallback; no performance/depth claim follows.

Presentation schema 7 (2026-10-17) additionally identifies the cover viewport and
index-bend/shared-latch selection policy. Local chemistry diagnostics include
actual panel layout and per-hand tap phase; they remain presentation evidence,
never a new research confidence/accuracy metric.

Presentation schema 8 supersedes the rejected bend policy with the relative
index-push policy and includes edge docking in actual panel-layout diagnostics.
Earlier UI runs remain historical; no Core experimental schema/result changes.

The application runtime may process accepted packets sequentially on one worker while
the UI consumes the latest complete snapshot. Dropped presentation snapshots
do not skip accepted packets inside that worker's filter. The live acquisition
pump above may replace pending packets before processing. Stop/retry must not
create overlapping camera workers. Only this presentation runtime uses
latest-packet/snapshot delivery; research replay remains synchronous/deterministic.

Preview mirroring is display-only: x becomes 1-x consistently for landmarks
and image. FRAME_NORMALIZED to WORLD_RENDER is explicit. Any extrusion is a
display thickness, and model-relative z is never camera depth. Separate UI
metadata/logs identify the two-hand configuration and cannot be presented
as the one-hand experiment schema.

Allowed conceptual direction:

```text
domain/contracts
    ↑
capture | preprocessing | tracking-provider | filtering | interaction
    ↑
pipeline/runtime

telemetry/logging reads public Core data
extension reads public InteractionState
analysis reads run artifacts
```

Forbidden examples:

```text
Core → Pygame/OpenGL scene classes
filtering → MediaPipe classes
preprocessing → renderer classes
analysis → renderer internals
extension → mutable filter/ROI internals
```

Circular dependencies across these boundaries are not allowed.

## 6. Color-space contract

The baseline image path is explicit:

```text
OpenCV capture/replay image: BGR uint8
        ↓
ROI illumination/preprocessing: explicit BGR → HSV
        ↓
CLAHE modifies V only when active
        ↓
explicit HSV → BGR
        ↓
enhanced ROI composited into unchanged full-size BGR frame
        ↓
provider adapter: explicit BGR → RGB
        ↓
MediaPipe
```

No module may silently reinterpret BGR as RGB. Any additional color space requires an explicit contract change or an optional experiment branch that does not alter the baseline semantics.

## 7. Coordinate-space contract

The project distinguishes these spaces:

```text
FRAME_PIXEL       full-frame integer pixel coordinates
FRAME_NORMALIZED  normalized image coordinates associated with full-frame geometry
VIEWPORT          renderer/window coordinates
NDC               normalized device coordinates for rendering
WORLD_RENDER      renderer world coordinates
MODEL_RELATIVE_Z  provider/model-relative landmark z semantics
```

Rules:

- ROI rectangles use `FRAME_PIXEL` coordinates.
- MediaPipe normalized x/y are converted into project landmarks tagged `FRAME_NORMALIZED`.
- Provider `z` MUST remain explicitly model-relative unless a separately specified calibration/reconstruction method exists.
- `MODEL_RELATIVE_Z` MUST NOT be labeled centimeters, physical depth, or distance from camera.
- Transformations between frame coordinates and renderer spaces MUST be explicit and testable.

## 8. Timestamp/frame contract

Within each run:

- `frame_id` MUST be a monotonically increasing integer;
- `timestamp_s` MUST be finite and monotonic for ordinary continuous updates;
- timestamps are seconds in a documented monotonic/source time domain;
- filter update interval is derived from timestamps, not assumed solely from requested camera FPS;
- requested FPS and observed timing are distinct values.

If a timestamp is invalid, non-increasing, or produces a gap beyond the configured filter-reset threshold, the sample MUST NOT be processed as an ordinary continuous filter update. Exact reset behavior belongs to `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 9. Public enums

Code names may differ, but semantics MUST map unambiguously to:

```python
ColorSpace = {BGR, RGB, HSV, GRAY}
TrackingStatus = {NO_HAND, VALID, TEMPORARY_LOSS, REACQUIRED, INVALID}
ROIState = {SEARCHING, TRACKING, COASTING}
IlluminationState = {NORMAL, LOW_LIGHT, LOW_CONTRAST, DIFFICULT}
FilterMode = {RAW, ONE_EURO_FIXED, ONE_EURO_ADAPTIVE}
QualitySource = {NONE, PROVIDER_DOCUMENTED, EXPERIMENTAL_DERIVED}
CoordinateSpace = {
    FRAME_PIXEL,
    FRAME_NORMALIZED,
    VIEWPORT,
    NDC,
    WORLD_RENDER,
    MODEL_RELATIVE_Z
}
```

`EXPERIMENTAL_DERIVED` quality is disabled by default and requires an explicit experimental definition before it may influence final course results.

## 10. Public data contracts

Python snippets are semantic examples; exact syntax is implementation detail.

### 10.1 `FramePacket`

```python
@dataclass(frozen=True)
class FramePacket:
    run_id: str
    frame_id: int
    timestamp_s: float
    image: np.ndarray
    color_space: ColorSpace
    source_name: str
```

Invariants: non-empty image, finite timestamp, correct explicit color space, increasing frame ID.

### 10.2 `ROI`

```python
@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    width: int
    height: int
    state: ROIState
```

ROI coordinates are full-frame pixels, clamped to valid frame bounds, with positive dimensions.

### 10.3 `IlluminationMetrics`

```python
@dataclass(frozen=True)
class IlluminationMetrics:
    mean_v: float
    std_v: float
    p10_v: float
    p90_v: float
    robust_range_v: float
    state: IlluminationState
    enhancement_active: bool
```

### 10.4 `Landmark`

```python
@dataclass(frozen=True)
class Landmark:
    index: int
    x: float
    y: float
    z: float
    coordinate_space: CoordinateSpace
```

A representation MAY separate x/y space from z semantics if that makes the implementation safer; it MUST preserve the coordinate meanings above.

### 10.5 `MeasurementQuality`

```python
@dataclass(frozen=True)
class MeasurementQuality:
    value: float | None
    source: QualitySource
    valid: bool
    semantic_name: str | None
```

Normative semantics:

- baseline invalid quality: `value=None`, `source=NONE`, `valid=False`;
- a valid value MUST be finite and in `[0,1]`;
- `semantic_name` MUST describe the real provider/experimental quantity;
- MediaPipe threshold configuration is not a per-frame quality output;
- handedness classification score is handedness metadata, not tracking confidence;
- hard-coded `1.0` for “hand exists” is invalid;
- downstream code MUST function when quality is unavailable.

### 10.6 `LandmarkObservation`

```python
@dataclass(frozen=True)
class LandmarkObservation:
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    landmarks: tuple[Landmark, ...]
    handedness_label: str | None
    handedness_score: float | None
    quality: MeasurementQuality
    hand_bbox: ROI | None
    provider_name: str
```

Downstream modules MUST check `status`; missing/invalid observations are never represented by fake zero landmarks.

### 10.7 `FilterDiagnostics`

```python
@dataclass(frozen=True)
class FilterDiagnostics:
    mode: FilterMode
    dt_s: float | None
    speed: float | None
    beta: float | None
    min_cutoff_hz: float | None
    final_cutoff_hz: float | None
    signal_alpha: float | None
    derivative_alpha: float | None
    reset_occurred: bool
    events: tuple[str, ...]
```

For vector landmark filters, the scalar diagnostic fields are a
frame-level summary and do not redefine the per-landmark filtering
algorithm.

For an accepted ordinary fixed/adaptive landmark update:

```text
speed
    = maximum finite per-landmark x/y speed for that frame

representative landmark
    = landmark with maximum per-landmark x/y speed
      (tie → lowest landmark index)

final_cutoff_hz
signal_alpha
    = values belonging to the same representative landmark that
      produced `speed`

derivative_alpha
    = common derivative alpha for the frame
      because all filtered x/y components use the same accepted `dt`
      and configured derivative cutoff
```

For `ONE_EURO_ADAPTIVE`, the effective `beta` is also taken from the same
representative landmark selected by maximum speed.

Thus for an accepted ordinary adaptive update:

```text
representative landmark
    = maximum per-landmark x/y speed
      (tie → lowest landmark index)

speed
beta
final_cutoff_hz
signal_alpha
    = values from that same representative landmark

min_cutoff_hz
    = the effective frame minimum cutoff:
      f_base when quality adaptation is disabled/unavailable,
      otherwise the valid quality-derived minimum cutoff

derivative_alpha
    = common derivative alpha for the accepted frame dt
```

The representative diagnostic aggregation MUST NOT feed back into any
landmark filtering calculation.

If multiple landmarks tie for maximum speed, the lowest landmark index
MUST be selected so serialization remains deterministic.

For adaptive initialization/reinitialization:

```text
dt_s = None
speed = 0
beta = beta_base
min_cutoff_hz = effective minimum cutoff
final_cutoff_hz =
    clip(min_cutoff_hz, final_cutoff_min, final_cutoff_max)
signal_alpha = None
derivative_alpha = None
```

For a fixed-filter initialization/reinitialization frame:

```text
dt_s = None
speed = 0
beta = configured beta
min_cutoff_hz = configured minimum cutoff
final_cutoff_hz =
    clip(min_cutoff_hz, final_cutoff_min, final_cutoff_max)
signal_alpha = None
derivative_alpha = None
```

For an adaptive frame with no accepted landmark measurement:

```text
dt_s = None
speed = None
beta = None
final_cutoff_hz = None
signal_alpha = None
derivative_alpha = None
```

For a fixed-filter frame with no accepted landmark measurement:

```text
dt_s = None
speed = None
final_cutoff_hz = None
signal_alpha = None
derivative_alpha = None
```

For a frame with no accepted landmark measurement, configured parameter
fields such as `beta` and `min_cutoff_hz` MAY remain populated when the
implementation uses them to expose the active filter configuration.
For the adaptive no-measurement contract above, `beta` is explicitly
`None` and `min_cutoff_hz` MAY remain populated if the effective
configuration is intentionally exposed.

`reset_occurred` retains its existing semantics.

The frame-level summary is diagnostic metadata only. Final jitter and
responsiveness outcomes MUST be computed from the recorded landmark
trajectories rather than treating this summary speed as an experimental
outcome.

### Temporal-filter event propagation

`FilterDiagnostics.events` carries filter-originated state-transition
events produced while processing the current observation.

For ordinary updates with no transition:

```text
events = ()
For F1/F2 timestamp/loss/reset transitions, the event names and
generation semantics are defined by 03_ALGORITHM_AND_EXPERIMENTS.md.
The LandmarkFilter.update return shape remains unchanged:

tuple[tuple[Landmark, ...], FilterDiagnostics]
The runtime MUST copy filter-originated diagnostic events into
TrackingFrame.events.
For each filter event in TrackingFrame.events, RunLogger MUST preserve
one corresponding event record in events.csv.

A runtime MUST NOT separately duplicate the same event through
RunLogger.log_event(...) when log_tracking_frame() already serializes
TrackingFrame.events.

Event propagation is diagnostic/logging behavior only. It MUST NOT feed
back into landmark filtering calculations.
Raw/F0 emits no temporal-filter events:
events = ()

This clarification does not add a new serialized artifact or change the
existing events.csv purpose.

### 10.8 `StageTimings`

```python
@dataclass(frozen=True)
class StageTimings:
    preprocess_ms: float
    tracking_ms: float
    filtering_ms: float
    gesture_ms: float
    compute_total_ms: float
```

`compute_total_ms` MUST have one documented calculation used consistently in all final runs.

### 10.9 `TrackingFrame`

```python
@dataclass(frozen=True)
class TrackingFrame:
    run_id: str
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    raw_landmarks: tuple[Landmark, ...]
    filtered_landmarks: tuple[Landmark, ...]
    quality: MeasurementQuality
    roi: ROI | None
    illumination: IlluminationMetrics | None
    filter_diagnostics: FilterDiagnostics
    timings: StageTimings
    events: tuple[str, ...]
```

This is the primary research/logging boundary. Analysis SHOULD depend on this contract or serialized equivalents, not on the renderer.
For pre-G2 Raw-baseline runs, `roi` and `illumination` MAY be `None`
when those stages have not been executed.

`None` means explicitly unavailable/not executed; it MUST NOT be
replaced by fabricated zero-valued ROI or illumination measurements.

Once the G2 preprocessing path is enabled, both fields MUST be populated.
### 10.10 `InteractionState`

```python
@dataclass(frozen=True)
class InteractionState:
    run_id: str
    frame_id: int
    timestamp_s: float
    interaction_valid: bool
    pointer_xy: tuple[float, float] | None
    pinch_ratio: float | None
    pinch_active: bool
    rotation_delta: tuple[float, float]
    scale_delta: float
```

The renderer may derive application-specific state but MUST NOT mutate Core state.

`InteractionState` has the following public semantics:

```text
run_id
    copied from the source TrackingFrame

frame_id
    copied from the source TrackingFrame

timestamp_s
    copied from the source TrackingFrame

interaction_valid
    true only for an ordinary usable continuation frame;
    false for loss, invalid input, initialization, reset, and
    reacquisition-neutral frames

pointer_xy
    filtered configured pointer-landmark x/y in FRAME_NORMALIZED
    coordinates when the current frame is gesture-usable;
    otherwise None

pinch_ratio
    normalized thumb-index distance divided by configured hand scale
    when gesture-usable;
    otherwise None

pinch_active
    hysteretic pinch state;
    false whenever interaction state is reset or invalid

rotation_delta
    renderer-independent (yaw_delta_rad, pitch_delta_rad);
    neutral value is (0.0, 0.0)

scale_delta
    renderer-independent signed dimensionless scale command;
    positive means enlarge, negative means shrink;
    neutral value is 0.0
```

Gesture equations and state transitions are owned by
`03_ALGORITHM_AND_EXPERIMENTS.md`.

The 3D Extension MAY accumulate these commands into renderer-specific
object state, but MUST NOT reinterpret tracking/filter internals or
mutate Core state.

The project-owned gesture interface is:

```python
class GestureEngine(Protocol):
    def update(
        self,
        frame: TrackingFrame,
    ) -> InteractionState: ...

    def reset(self) -> None: ...
```

`GestureEngine.update` consumes only project-owned public data. The
baseline gesture implementation MUST derive interaction commands from
`TrackingFrame.filtered_landmarks`, not from raw landmarks or provider
objects.

## 11. Public interfaces

```python
class FrameSource(Protocol):
    def open(self) -> None: ...
    def read(self) -> FramePacket | None: ...
    def close(self) -> None: ...
```

Replay EOF may return `None`; camera failure must be distinguishable from normal replay EOF.

```python
class LandmarkProvider(Protocol):
    def process(self, frame: FramePacket) -> LandmarkObservation: ...
    def close(self) -> None: ...
```
The provider receives the project-owned FramePacket so frame identity,
timestamp, and declared color space remain coupled.

For the required MediaPipe adapter, the input FramePacket MUST be BGR.
The adapter owns the explicit BGR → RGB conversion before constructing
the MediaPipe image.

The emitted LandmarkObservation MUST preserve frame.frame_id and
frame.timestamp_s exactly.

```python
class LandmarkFilter(Protocol):
    def update(self, observation: LandmarkObservation) -> tuple[tuple[Landmark, ...], FilterDiagnostics]: ...
    def reset(self) -> None: ...
```

```python
class RunLogger(Protocol):
    def start_run(self, metadata: dict, resolved_config: dict) -> None: ...
    def log_tracking_frame(self, frame: TrackingFrame) -> None: ...
    def log_interaction_state(self, state: InteractionState) -> None: ...
    def log_event(self, event: dict) -> None: ...
    def close(self) -> None: ...
```

## 12. Configuration contract

Configuration precedence:

```text
repository defaults
< experiment profile
< explicit CLI overrides
```

At run start the application MUST:

1. load and merge configuration;
2. validate semantic constraints;
3. create the resolved configuration;
4. serialize it deterministically;
5. compute/store a config hash;
6. use that frozen resolved configuration for the run.

Required configuration sections or equivalent grouping:

```text
project
camera
runtime
roi
illumination
clahe
tracking
filter
gesture
logging
experiment
renderer
```

Required parameter families include:

- requested camera size/FPS/backend;
- runtime mode and replay source;
- ROI padding/coasting/fallback limits;
- illumination EMA/hysteresis thresholds;
- CLAHE policy/clip/tile parameters;
- provider/model and provider threshold settings;
- filter mode, `derivative_cutoff_hz`, fixed and adaptive parameters, reset gap;
- gesture gains/deadzone/clamps and pinch hysteresis/hand-scale pair;
- logging schema/output/video policy;
- experiment ID/condition/trial/warmup metadata;
- renderer enable/window settings.

Algorithmic parameter invariants are defined with the algorithms in `03_ALGORITHM_AND_EXPERIMENTS.md`; configuration validation MUST enforce them.

## 13. Run artifact contract

A final experiment/demo run SHOULD produce:

```text
runs/<run_id>/
├── metadata.json
├── resolved_config.yaml
├── frames.csv
├── landmarks.csv
├── events.csv
└── optional/
    └── recorded_video.*
```

Raw video is optional and off by default unless explicitly required.

Minimum reproducibility identity stored in metadata:

```text
run_id
experiment_id / condition / trial index when applicable
spec version
code revision/commit
log schema version
config hash
Python + key dependency versions
provider/model filename + checksum
camera/backend and requested/observed properties when applicable
source-data identity/hash when practical
OS/hardware summary
```

`frames.csv` MUST carry enough fields to reconstruct status, ROI/illumination state, filter diagnostics, interaction validity, and stage timings. `landmarks.csv` MUST identify raw vs filtered stage and landmark index in a declared coordinate space. `events.csv` MUST carry frame/time, event type, severity, and details.

Breaking serialized semantic changes require a schema-version bump.

## 14. Failure containment

Failures MUST be explicit rather than converted into plausible-looking fake data:

```text
camera unavailable      → explicit startup/runtime failure
invalid ROI             → clamp/fallback/search state
no hand                 → invalid/no-hand observation
bad timestamp           → reset/discontinuity path, not ordinary update
tracking loss           → no zero-landmark injection
reacquisition           → initialized/neutral interaction transition
logger failure          → diagnostic/error, never fabricated log values
renderer failure        → must not rewrite already-computed research data
```

Exact algorithm response to tracking loss/reacquisition is owned by `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 15. Thin future seams

The architecture MAY expose clean seams for:

- alternate `FrameSource`;
- alternate `LandmarkProvider`;
- calibration/camera-capability service;
- alternate renderer;
- packaged desktop launcher;
- local diagnostic export.

These interfaces do not justify implementing speculative product features in the course baseline.
