# DIP Touchless STEM V2 — approved product continuation

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
full-frame P1 preprocessing, a separate VIDEO provider configured for two hands,
and canonical fixed 1-Euro instances per associated hand. This product full-frame
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

The product vocabulary is exactly POINT, intentional thumb/index PINCH, OPEN PALM
and V-SIGN. POINT inspects; it never rotates. Pinch requires a confirmed comfortable
release window, stable reference, deliberate relative closing, dwell, release and
rearm. Palm projection incompatibility invalidates the reference. Open palm
presents; two open palms never scale. Both active pinches clutch relative scale.
Two POINTs preview a measurement, dwell locks it, dominant pinch commits once.
There is no automatic fallback to legacy while a product gesture is held.

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

The product control pointer is mirrored/gain-adjusted normalized **window** xy.
UI hits, the displayed control cursor and both measurement endpoints share this
mapping. The shell converts window xy to viewport-local xy once before scene
picking in WORLD and HAND. Camera skeletons and palm anchoring separately use
normalized source-image xy with letterboxing. The control cursor may differ from
the index overlay, especially with pointer gain; it is not a camera registration
measurement. Endpoints outside the scene remain unavailable, and a pair cannot
silently become a one-point commit.

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

The Qt frontend uses native navigation and inspector docks, QOpenGLWidget with
depth-ordered projected geometry, and the same QPainter geometry on a software
surface. The rendering model is orthographic 3D visualization, not a full physics
or photorealistic graphics engine. GPU resources are Qt-owned. A bounded latest
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
