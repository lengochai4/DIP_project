# DIP Touchless STEM V2 — approved product continuation

## Contextual guidance and enlarged workspace — 2026-10-03

The user requested optional lab instructions and a larger model frame because
the non-geometry extensions were difficult to understand. Explore provides a
Vietnamese guide for all nine labs, identifying their purpose, live geometry vs
analytical probe/model controls, steps, expected output and scientific limits.
Guidance tracks lab/preset, PRODUCT LIVE/RECORDED vs LEGACY, WORLD/HAND and explicit
UI ownership. Guide and Tools share screen space exclusively. Normal guide
visibility is persisted; old preferences default to showing it.

The optional expanded workspace hides navigation, the lab library and side panels.
It retains session controls and Guide/Tools/restore actions. Restore recovers the
previous panel state and leaves scene scale/orientation and recorded work intact.
Temporary help can open while expanded without replacing the normal preference.
Leaving Explore restores normal navigation. Layout transitions cancel current
input before coordinate mapping changes; the next valid LIVE frame regenerates
all observed fingertips. G toggles help; Ctrl+Shift+F expands/restores; Esc restores
an expanded frame before normal tool cancellation. F11 remains independent.

Change: contextual help, optional enlarged viewport, preset-relevant optics inputs.
Reason: explicit user UX request; existing shared geometry did not explain each lab.
Canonical file/section: 02 §16 unchanged; 05 current task/evidence updated.
Code/modules: app/ui/lab_guides.py, shell.py, config.py; product tests and render QA.
Algorithmic impact: presentation only; no Core, tracking, filter or math changes.
Experimental impact: none for G7; product run source hashes/settings remain recorded.
Compatibility: additive validated lab_guide boolean; old JSON files remain valid.
Tests: native guide/state/persistence/scroll/layout checks and ten-tip reprojection
after expansion in both views; complete regression and synthetic render checks.
Existing results invalidated: no; frozen G7 provenance and measurements unchanged.

## Approved V2 continuation

The user approved a complete replacement of the product frontend and interaction
layer on 2026-10-02. The supplied blueprint is retained in
[V2_BLUEPRINT.md](V2_BLUEPRINT.md). This is supplemental product scope, subordinate
to canonical research contracts. G7 and application v1.0 remain immutable.

The latest user instruction defers physical testing until implementation is
finished. Therefore **implementation/automated verification** and **physical
acceptance** have separate statuses. Automated or synthetic checks cannot mark
the blueprint's physical usability gate passed, or establish its success rates.
No physical test is requested from the user during this implementation.

The product boundary is:

```text
Frozen Core -> copied presentation image + TrackingFrame + legacy InteractionState
                         |
                         +-> independent product hand runtime -> semantic GestureIntent
                                                               |
                                        exclusive router -> Qt UI / STEM extensions
```

`app/` owns the V2 runtime, geometry, intentional pinch, routing, Qt frontend,
projection and STEM extensions. No Core module imports it. Legacy scenes continue
to consume `InteractionState`; V2 extensions consume only `GestureIntent`.

The camera processing worker executes the frozen synchronous `RealtimeRuntime`.
The product adapter processes the read-only presentation copy independently with
full-frame P1 preprocessing, a separate VIDEO provider with a configurable extra-hand
guard budget (default three detections), and at most two associated hands with
canonical fixed 1-Euro instances. More than two detected hands are rejected.
This product full-frame
geometry is explicitly different from Core ROI history and is **not G7 evidence**.
The supplemental detection stream is local, synchronous and separately logged.
No legacy observations/results are substituted by product observations.

Provider RGB conversion and horizontal mirror are explicit. The product provider
uses a mirrored inference input for the documented handedness convention and
maps x back to the original normalized frame afterward. UI mirror remains a
presentation preference. Hand labels are classification metadata, not confidence
or biometric identity. Ambiguous associations, overlapping palms, role changes,
invalid timestamps, loss, reacquisition and run changes cancel commands. Provider
semantics references: [Google's handedness convention](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md),
[Tasks result contract](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarkerResult).
The physical accuracy of this role convention still requires observed validation.

When LEGACY is explicitly selected, the worker bypasses the independent product
provider entirely and runs the frozen Core path only. Switching engine stops the
session before reconnecting. Core rotation deltas and the original additive scale
semantics are preserved; the presentation adapter requires release before resuming
after an owner/context switch. HAND mode requires PRODUCT; legacy WORLD and the
original Pygame application remain available without product calibration.

The navigation/RECORDED vocabulary is POINT, intentional thumb/index PINCH, OPEN PALM
and V-SIGN. POINT inspects; it never rotates. Pinch requires a confirmed comfortable
release window, stable reference, deliberate relative closing, dwell, release and
rearm. Palm projection incompatibility invalidates the reference. Open palm
presents; two open palms never scale. Both active pinches clutch relative scale.
Two POINTs preview a measurement, dwell locks it, dominant pinch commits once.
There is no automatic fallback to legacy while a product gesture is held.

## Latest user correction: automatic full-fingertip geometry

The user's 2026-10-03 correction supersedes the blueprint's index-only sequential
construction flow for the default geometry experience. Navigation still has four
commands; geometric vertices are data, not ten separate finger buttons. LIVE
mode observes all five tips on each associated hand, uses every extended tip
(including thumb/middle/ring/pinky and a support-only hand), and updates points/
geometry automatically with no Add point/pinch commit requirement. Folded tips
remain observed but are not active vertices. This stream has one exclusive TOOL
owner and cannot simultaneously navigate or issue grab/scale commands.
Recorded construction remains an explicitly selected accessibility/legacy option.
The user selected direct live-follow behavior; no dwell-to-save behavior is added.
One vertex is a point, two a segment/vector, three a triangle. The 3D audit below
extends four-to-ten vertices to closed convex geometry when noncoplanar; nearly
coplanar sets retain a quadrilateral/polygon (Rectangle only when actual conditions
hold). All vertices remain used; planar shape boundaries follow displayed
angular order about the projected scene centroid. Planar surface triangles share that
centroid, avoiding a vertex fan crossing a concave boundary. Degenerate observations
retain vertices and expose unavailable
shape/angle values rather than forcing a regular triangle/rectangle.
LIVE HAND acquisition uses an observed valid palm whenever at least one tip is
extended, including a support-only hand; an initial OPEN gesture is not required.
Folded/inactive fingers cease to be vertices; no active tips, invalid/out-of-image
samples, loss and takeover remove the live geometry. Modal CSV export takes an immutable scene-only snapshot
before cancellation; it exports that snapshot without saving camera/hand tokens.
Both view modes use camera-aligned xy. Relative per-palm z gives bounded visual
relief via an inverse camera ray, so every vertex projects back to its tip. It
does not reconstruct physical points or compare physical depth across two hands.

Change: full-fingertip product samples, automatic live geometry, default LIVE
interaction, and projective scene points with relative model-z visual relief.
Reason: user explicitly rejects index-only/manual point construction and asks
to use all fingers on both hands.
Canonical file/section changed: docs/02 section 16, additive product seam only.
Code/modules affected: app geometry/contracts/engine, projection, labs, shell,
product settings/profile/manifest, product tests and release guides.
Algorithmic impact: geometry-qualified combinations of extended fingers bypass
index-only navigation pose rules only in LIVE scene context. Core algorithms,
pinch equations and navigation vocabulary remain unchanged. Relative per-palm z
is a bounded visual cue, not metric or comparable physical depth between hands.
Experimental impact: new product semantics are separately hashed/versioned;
no mixing with old runs as equivalent usability evidence.
Compatibility impact: missing old preference field selects LIVE; RECORDED keeps
the earlier index/pinch construction. Scene receives semantic scene points only.
Tests: five/ten tips, every finger/subset, depth projection round trips, topology,
loss/roles/UI/modal neutralization, live geometry/render and automatic defaults.
Existing results invalidated: no G7 results; no physical success claim is made.

## Latest extension/UI 3D audit direction

The user requested a full extension/UI review and correction of the flat-looking
3D experience. Four or more genuinely noncoplanar scene vertices may form a closed
convex hull automatically: four extreme vertices form a tetrahedron; larger sets
form a convex polyhedron. Every observed active vertex/token is retained, including
interior points; hull boundary faces need not use interior points. Nearly coplanar
sets retain a surface/polygon using the product profile's relative planarity policy.
One/two/three vertices remain a point/segment/triangle. No invented thickness or
metric hand reconstruction is introduced. Closed shapes use outward faces and
physical-free scene-unit edge/volume values derived from the rendered scene only.

LIVE Vector Lab consumes stable-token live scene vertices, never hidden RECORDED
constructions. Missing vector pairs remain unavailable. Other analytical probes
use one stable semantic vertex. Analytical/molecular labs retain wire outlines
of automatic geometry so opaque hull faces do not obscure the actual lab model;
Coordinate/Vector render filled geometry. Renderer and content dimensionality are
visible; wave/optics diagrams and planar molecules must not be artificially
extruded to appear volumetric. Explicit mouse orbit must work after mode switches.

The UI keeps stable A–J labels by opaque semantic token order. LIVE Vector pairs
are A→B and C→D; sample positions are not anatomical commands. Default Inspector
prioritizes lab values; all vertex XYZ follows them only when diagnostics is enabled.

NH3's previous hard-coded pyramid implied an incorrect H–N–H angle. Its educational
shape now uses the profile's 106.7-degree reference from
[NIST CCCBDB](https://cccbdb.nist.gov/listangleexp3x.asp?bi=16&descript=aHNH&mi=16).
Scene lengths remain unscaled, not measured chemical bond lengths. Frozen H2O/CH4
preset data remains unchanged; CO2 remains linear.

Change: automatic solid/surface classification, closed product geometry, stable
LIVE analytical inputs, corrected NH3 illustration and clearer rendering/dimensionality guidance.
Reason: user asks why the 3D experience looks 2D and requests a full extension/UI audit.
Canonical file/section changed: none; docs/02 section 16 already permits semantic
scene points and triangle faces. Product detail changes only in this section/docs/05.
Code/modules affected: product live geometry/labs/viewport/UI, product profile,
manifest, synthetic QA and product tests.
Algorithmic impact: product presentation only; configurable relative planarity
policy, no change to Core/provider/filter/pinch equations or G7 scope.
Experimental impact: product semantics versioned separately; no new accuracy or
commercial claim, no mixing with historical runs as equivalent evidence.
Compatibility impact: LIVE follows all tips as before; planar sets keep earlier
shapes, RECORDED retains original controls and data, CSV point columns unchanged.
Tests: closed manifold/volume/degeneracy, live analytical input, mode-switch orbit,
all-presets real Qt rendering, depth/projection and full regression.
Existing results invalidated: no G7 results; physical acceptance remains deferred.

Router priority: system modal > calibration > UI > tool > scene. A pinch lease
retains its owner until release/cancel. Native button/list/selector hits belong
to UI and cannot manipulate a scene simultaneously. Scene/view/tool/preferences
switches and focus loss cancel before applying changes. Legacy is explicitly
selected in Settings, preserving the original command meanings.

WORLD and HAND share each extension's geometry. All scene points and distances
are renderer scene units. Camera letterboxing and mirror are explicit. A shared
invertible projection handles picking/plane construction. Palm center, image
span, roll and model-relative orientation cues produce a presentation anchor;
timestamp-based smoothing is separate from research filtering. This is neither
metric camera pose nor reconstructed physical depth.

WORLD and explicit UI control use mirrored/gain-adjusted normalized **window**
xy. HAND scene control uses the additive unmirrored `source_pointer_xy` and
`source_points`: mirror and camera letterboxing are applied exactly once, with
no pointer gain. Cursor and picks therefore use the same filtered index tip as
the camera skeleton. Locked measurement pairs retain their source snapshot.
HAND's explicit "Control UI" toggle selects exclusive window/UI control;
turning it off restores camera-aligned scene control and cancels/rearms first.
Endpoints outside the scene remain unavailable; a pair cannot silently become
a one-point commit. This is image alignment, not physical depth/contact.

HAND acquires its presentation anchor from an OPEN_PALM. While the same
associated hand remains valid, the anchor follows its observed palm through
POINT, V_SIGN and intentional PINCH, allowing single-hand tools and two-hand
scaling. It is never extrapolated through loss. Invalid data, discontinuity,
identity/role/context change, focus loss and modal takeover clear acquisition.
UNKNOWN poses still cancel commands even when their observed palm is displayed.
Automatic Inspector expansion after an already-routed measure intent is a
presentation change and retains the live anchor/locked pair. Explicit tool,
mode or UI-control switches still cancel/rearm. Intentional pinch closing retains
the dwell-locked source pair despite the index tip's natural motion during pinch.

Change record (2026-10-03, user-reported finger interaction/alignment failure):
Change: camera-aligned HAND picking, observed anchor continuity and relative-3D
finger joint classification (aspect-correct x/z and y, nonmetric).
Reason: window picking visibly missed fingertips; open-only anchors disappeared
as soon as a user pointed/pinched; projected 2D joints lose finger bend cues.
Canonical file/section changed: docs/02 section 16, product-only coordinate seam.
Code/modules affected: app interaction contracts/engine/geometry, anchor, UI,
viewport and product journal manifest schema product-v2-3.
Algorithmic impact: product pose predicates use model-relative joint geometry;
pinch ratio/reference equations, thresholds, Core filters and G7 are unchanged.
Provider z convention: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/android
Experimental impact: new product runs have different pose semantics/source hashes;
they must not be pooled with old product runs as equivalent usability evidence.
Compatibility impact: additive immutable source coordinates; WORLD mapping kept.
Tests added/updated: tilted/folded finger fixtures, letterboxed cursor/picking,
observed anchor continuity/loss and HAND scale/measurement/UI exclusivity.
Existing results invalidated: no G7 results; no prior physical usability claim.

Hardening continuation on 2026-10-03: native modal dialogs cancel/rearm gesture
clutches and block scene input. An active mouse clutch owns the scene while
camera presentation continues; takeover cancels the gesture clutch first.
Native number/text editing disables product shortcuts until editing ends.
`GestureIntent.input_source` defaults to `GESTURE`; fallback commands carry
`MANUAL`. Commit idempotence uses input source/tool/cycle, so unrelated manual
and gesture cycles cannot suppress each other. This additive product-only
contract and pointer mapping do not alter frozen Core or G7 logs/evidence.

Camera correction on 2026-10-03: the controller passed to the unchanged frozen
factory now implements `consume_presentation`, as required by its existing
signature. The unsupported factory keyword was removed. The read-only runtime
callback/API remains unchanged. Device-mocked tests execute the actual factory,
runtime and logger; a bounded Start/Stop camera run verified real acquisition
and GUI presentation with no detected hand, without validating hand usability.

The Qt frontend uses native navigation and contextual inspector docks.
QOpenGLWidget renders sphere/bond/surface meshes with GLSL lighting, perspective
and actual depth testing. Software fallback uses the same scene and perspective
projection with depth-sorted QPainter primitives; its per-pixel occlusion is an
approximation. Ray picking and plane intersections share the projection used
for display. Camera distance and initial fit are configured; CH4 is the initial
molecular preset so the nonplanar tetrahedral structure is immediately visible.
The original H2O/CH4 definitions remain unchanged. GPU buffers/programs are
released with the Qt context current. A bounded latest
presentation mailbox avoids accumulating queued camera images. The Core worker
itself processes every frame synchronously; GUI backlog dropping affects only
presentation/product command consumption and cannot alter logged G7 semantics.

Engineering defaults are in `config/product_v2.yaml`; local preferences and
calibration are separate. References are session-only. Raw camera video is never
stored by the product runtime. Logs include product configuration, code hashes,
Core metadata, observations, semantic intents and settings under `runs/product-v2/`.

STEM labs: Coordinate, Molecule, Orbital, Vector, Function Surface, Wave/Signal,
Vector Field, Optics and Crystal Lattice. H2O/CH4 import immutable existing presets.
Additional molecular/lattice/field/optics models are educational illustrations.
No new chemical lengths, physical gravitational accuracy, processing performance
or research superiority is claimed.

Change: new V2 product boundary/API/frontend and approved educational extensions.
Reason: implement the user's supplied complete product blueprint.
Canonical sections changed: 01 §13, 02 §16, 05 active continuation.
Code affected: app/, product configuration, product tests/tools and launch/setup.
Algorithmic impact: new product geometry/intents; frozen Core equations unchanged.
Experimental impact: separate development observations, no G7 experiment changes.
Compatibility impact: legacy APIs and release tags preserved; V2 optional extra.
Tests: independent product safety, geometry, STEM math, native UI and provider seams.
Existing results invalidated: no; product runs must not be mixed with G7 results.

3D/UX/environment continuation approved by the user on 2026-10-03:

- Explore keeps the scene dominant; Inspector opens through Tools. Construction
  actions are contextual; polygon completion is visible only for Polygon,
  unavailable actions are disabled, and the duplicated Reset button was removed.
  Changing dock layout cancels a held clutch before the viewport changes.
  Environment notice layout changes follow the same rule. Inspect never commits
  measurements, completed work remains undoable, and interruption resets UI dwell.
- Low-light guidance reads observed Core illumination state. Product P1 already
  applies adaptive CLAHE; it cannot recover missing detail or establish accurate
  tracking under darkness. No new tracking-confidence value or performance claim
  is introduced.
- `provider_max_hands` is three by default to make an extra-hand observation
  possible. Association accepts at most two, rejects extra/ambiguous hands,
  clears filters and reacquires neutrally. This is neither multi-user support nor
  a guarantee that every extra hand will be detected. MediaPipe defines num_hands
  as a detection limit, not a detected population count; see the
  [official options](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python).
- Product observation manifest schema is now `product-v2-2`; source/config hashes
  distinguish the new detector budget. Do not mix these observations with older
  product detector configurations as if equivalent. Frozen G7 evidence is unchanged.
- `Geometry.faces` is an additive product-only triangle contract with a default
  empty tuple. Extensions remain independent of tracking and GPU objects.

This improves implementation and presentation. It does not establish enterprise
readiness or proven optimal UX. Physical low-light/crowding/gesture accuracy,
device compatibility and observed user-task usability still need evidence.

UI audit continuation approved by the user on 2026-10-03:

- Reset view is separate from destructive Reset lab; the latter has a native
  confirmation modal. Optional local CSV export includes only lab construction
  data in scene units, never camera frames, hands or calibration references.
- Rectangle accepts four ordered nondegenerate right-angle corners, with the
  external numerical `construction_tolerance`. Quadrilateral explicitly handles
  arbitrary four corners. `construction_snap` is an off-by-default local setting;
  `construction_grid_step` controls optional free-point grid spacing on the active
  construction plane. Exact sphere/atom-centre picks are not quantized.
- Scene keys are scoped to Explore and respect native buttons/list navigation.
  HAND scene commands require a visible anchor. Logging failure is explicit and
  contained in the product GUI; an incomplete intent journal is never reported
  as complete. Camera stop clears stale ready indicators.
- A recapture/source/role change invalidates old calibration checks. A cancelled
  pinch cannot validate a completed calibration cycle. LEGACY cannot claim
  product calibration or a running product filter.
- Educational corrections preserve central thin-lens rays, use full 3D radius
  for idealized electric fields, mark zero-vector projection unavailable and
  preserve idempotent Optics placement. These change product illustrations only.

Change: UI correctness audit, educational math corrections and small local tools.
Reason: user requested a full new-3D-interface review and necessary utilities.
Canonical sections: 02 §16 product boundary unchanged; 05 current-task record.
Code: app UI/rendering/config/extensions; product tests and delivery verifier.
Algorithmic impact: product tools/illustrations only; frozen Core unchanged.
Experimental impact: source/config hashes distinguish product revisions; do not
compare them as equivalent gesture/illustration observations.
Compatibility: additive product settings/config/tools; legacy and G7 preserved.
Tests: UI negative paths, calibration, snapping/rectangle, math and package checks.
Existing results invalidated: no G7 result; product runs retain original provenance.

Second audit follow-up: manual scene commands may cancel gesture ownership while
retaining the currently observed presentation anchor/plane. They do not create
or extrapolate a missing anchor. Loss in HAND cancels manual clutch immediately;
release always ends mouse ownership, even without an anchor. Clear-reference,
modal and context cancellations retain their original clearing behavior.
CSV export writes a sibling temporary file and replaces the destination only
after successful close, preserving previous exports when writing/replacement
fails. Package member validation rejects noncanonical path segments and invalid
Windows names before extraction. These are product UI/local-delivery changes;
Core algorithms, public research contracts and G7 results remain unchanged.
