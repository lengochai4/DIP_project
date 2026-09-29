# 06 — G8 UI, STEM Extension, and Productization Direction

**Project:** DIP Touchless STEM
**Status:** Supplemental post-G7 implementation direction and roadmap
**Research baseline:** `g7-final`
**Authority:** Non-canonical; subordinate to canonical specification files `00–05`

---

## 1. Purpose

G7 completed the final controlled research evaluation, evidence package, report, and reproducible release.

G8 has a different objective:

> transform the existing demonstration layer into a polished, extensible STEM interaction application while preserving the frozen Digital Image Processing Core and G7 evidence.

The resulting application should support three audiences:

```text
examiner
    → clearly sees the DIP pipeline and evidence

student / STEM user
    → interacts naturally with educational 3D content

future product developer
    → can add new STEM experiences without rewriting the Core
```

G8 is not a second research experiment unless explicitly declared.

G8 is a separately approved post-G7 continuation. It does not expand or
retroactively redefine the canonical-v1.2 course scope, the frozen G7
results, or the final report. “Productization” describes an engineering
direction; G8 completion MUST NOT be presented as proof of commercial
readiness, market validation, or user-study success.

---

## 2. Authority and frozen baseline

The following remain the normative research specification:

```text
docs/00_GOVERNANCE.md
docs/01_MASTER_SPEC.md
docs/02_ARCHITECTURE_AND_CONTRACTS.md
docs/03_ALGORITHM_AND_EXPERIMENTS.md
docs/04_IMPLEMENTATION_TESTING_GUIDE.md
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

This document must not redefine them.

This is supplemental project guidance, not a seventh canonical
specification. `00_GOVERNANCE.md` owns specification authority and
precedence; `05_PROJECT_STATUS_AND_ROADMAP.md` owns the active task and
current status.

Frozen G7 release:

```text
tag:
g7-final

release commit:
f454c6b8325c85199c0122c0e822fe8e76c1526c
```

Primary final live-demo execution revision:

```text
6a87dc50f9d3920ed9fd39a2669e266be00f9735
```

G8 work may create new commits/releases but must preserve these historical identities.

The release tag resolves to commit
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. The live-demo execution
revision `6a87dc50f9d3920ed9fd39a2669e266be00f9735` is a separate
recorded code identity, not the release commit. G8 MUST NOT move, delete,
or rewrite `g7-final`.

### G7 baseline at the start of G8

The tagged G7 tree already contains the final report, submission guide,
and selected generated evidence under `submission/evidence/`. The last
recorded G7 full regression is 433 passing tests, as recorded in
`submission/README.md`; this is historical evidence, not a test run made
by G8 work.

The current final-demo implementation is not a blank UI shell. It has an
OpenCV camera/status dashboard with a live frame, ROI and pointer overlays,
tracking, illumination, CLAHE, filter, timing, and pinch readouts, plus a
separate Pygame/OpenGL window for the coordinate cube. It supports start,
reset, and stop controls. A scene registry, application modes, and a
touchless spatial control panel are not yet present in this baseline.

The frozen research findings include unavailable A2 responsiveness
metrics for all three final trials and no CLAHE activation in the analyzed
P1 frames. Any G8 evidence view MUST preserve those limitations alongside
the recorded A1 and Experiment B outcomes. See `FINAL_REPORT.md` and the
selected artifacts in `submission/evidence/` for the exact results.

---

## 3. Product vision

The intended product direction is:

> a touchless STEM visualization workspace driven by a reusable Digital Image Processing interaction pipeline.

The application should visually communicate:

```text
SEE
    camera / image-processing state

UNDERSTAND
    ROI / illumination / preprocessing / filtering state

INTERACT
    touchless pointer / rotation / scaling / selection

EXPLORE
    multiple STEM visualization modules

VERIFY
    final experimental evidence and known limitations
```

The application should feel closer to a scientific visualization instrument than to a game prototype.

---

## 4. Architecture principle

The architectural direction remains:

```text
                    DIP CORE
                       │
                       │ public contracts
                       ▼
            TrackingFrame / InteractionState
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
 Presentation Adapter       Interaction Router
           │                       │
           ▼                       ▼
 PresentationState            STEM Scenes
           │
           ▼
 Dashboard / overlays
```

There must be no reverse dependency from Core into UI or scene classes.

---

## 5. Core preservation rule

G8 UI and scene work should not change:

```text
ROI equations/state semantics
illumination algorithms
CLAHE activation policy
measurement validity
MediaPipe adapter semantics
F0/F1/F2 filter equations
tracking-loss semantics
gesture equations
final experiment definitions
analysis metrics
selected G7 evidence
```

If a requested feature truly requires one of these changes, that work becomes a separately reviewed research revision rather than ordinary G8 UI work.

---

## 6. Target application structure

Recommended long-term structure:

```text
extensions/stem3d/
│
├── live_demo.py
│
├── demo.py
│
├── application/
│   ├── __init__.py
│   ├── app.py
│   ├── controller.py
│   ├── mode.py
│   └── interaction_router.py
│
├── ui/
│   ├── __init__.py
│   ├── theme.py
│   ├── layout.py
│   ├── components.py
│   ├── presentation_model.py
│   ├── dashboard.py
│   ├── overlays.py
│   └── spatial_panel.py
│
├── scenes/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── coordinate_cube.py
│   ├── molecule.py
│   ├── orbital.py
│   ├── vector_field.py
│   └── ...
│
└── evidence/
    ├── __init__.py
    └── presentation.py
```

This is a target responsibility map rather than a requirement that all files appear in the first G8 commit.

Refactor incrementally.

---

## 7. Application modes

The application defines three primary modes.

### 7.1 DEMO

Goal:

```text
maximize visual clarity
maximize interaction visibility
minimize technical clutter
```

Primary content:

```text
live camera/DIP preview
large 3D STEM viewport
tracking indicator
current scene
basic interaction help
start/reset/stop
```

### 7.2 ANALYSIS

Goal:

```text
make the Digital Image Processing contribution visible
```

Display relevant read-only diagnostics:

```text
ROI state
ROI rectangle
landmarks
pointer
tracking status
illumination state
illumination descriptors when available
enhancement active/bypass
temporal filter mode
pinch state
frame/runtime diagnostics
```

This mode should make it easy to explain:

```text
camera
→ ROI
→ HSV illumination analysis
→ adaptive preprocessing
→ landmark observation
→ temporal filtering
→ gesture mapping
→ interaction
```

### 7.3 EVIDENCE

Goal:

```text
present frozen G7 evaluation clearly
```

It may display selected evidence from:

```text
submission/evidence/
```

including:

```text
A1 static jitter
A1 trajectories
A2 unavailable responsiveness result
B-normal valid observation rate
B-lowlight valid observation rate
DIP image-domain visual
```

Evidence mode must not alter, regenerate, reinterpret, or hide G7 results.

Negative and unavailable findings remain visible.

---

## 8. Presentation model

UI components should not directly traverse large research-domain objects.

Create a presentation adapter that maps public runtime output to a small immutable UI state.

Conceptual model:

```python
@dataclass(frozen=True)
class PresentationState:
    frame_id: int
    run_id: str | None

    tracking_status: str
    roi_state: str | None
    illumination_state: str | None
    enhancement_active: bool | None
    filter_mode: str | None

    interaction_valid: bool
    pointer_xy: tuple[float, float] | None
    pinch_active: bool
    pinch_ratio: float | None

    fps: float | None
```

The exact type may follow existing project dataclasses and naming
conventions. This model is a G8 design target; it is not an existing public
Core contract. Any change to the public callback or Core contracts must be
reviewed under `02_ARCHITECTURE_AND_CONTRACTS.md`.

`pointer_xy` is full-frame normalized camera-image position. Mapping it
to a screen-space panel requires an explicit viewport transform and a
documented mirror/orientation convention. A display-only FPS estimate,
if shown, must be labeled as a presentation diagnostic and must not be
reported as a measured research result without a defined measurement
procedure.

The adapter is presentation-only.

---

## 9. STEM scene system

### 9.1 Scene contract

Each educational visualization is a `STEMScene`.

Conceptual interface:

```python
class STEMScene(Protocol):
    id: str
    title: str
    category: str

    def activate(self) -> None: ...
    def deactivate(self) -> None: ...
    def reset(self) -> None: ...
    def update(self, dt_s: float) -> None: ...
    def apply_interaction(self, state: InteractionState) -> None: ...
    def render(self, viewport) -> None: ...
```

Optional scene metadata may include:

```text
description
educational topic
interaction hints
default camera
supported visual options
icon identifier
```

### 9.2 Scene registry

Use a local registry:

```text
SceneRegistry
    ├── coordinate-cube
    ├── molecule
    ├── orbital-system
    ├── vector-field
    └── future scenes
```

Scene selection should not require a large conditional chain in the application entry point.

The registry is not a remote plugin marketplace.

---

## 10. Recommended STEM extension catalog

The architecture should support many modules, but implementation should be incremental.

### Tier 1 — Final presentation priority

#### Coordinate Geometry

Features:

```text
3D coordinate axes
grid
labeled X/Y/Z directions
orientation visualization
rotation/scale interaction
```

Educational value:

```text
coordinate systems
spatial transformation
3D orientation
```

#### Molecular Geometry

Initial examples:

```text
H2O
CH4
optional additional molecules
```

Features:

```text
atom spheres
bond connections
labels
bond-angle visualization
rotation/scale interaction
```

Educational value:

```text
molecular structure
bond geometry
spatial chemistry visualization
```

#### Orbital Mechanics

Features:

```text
central body
orbiting body/bodies
orbit paths
slow autonomous time evolution
user-controlled global view
```

Educational value:

```text
orbital systems
relative motion
3D spatial reasoning
```

### Tier 2 — Strong expansion candidates

#### Vector Field

```text
3D arrows
field magnitude visualization
camera rotation/scale
selectable preset fields
```

Suitable for:

```text
electromagnetism
fluid flow
mathematics
```

#### Function Surface

```text
z = f(x,y)
surface mesh
coordinate grid
preset mathematical functions
```

Suitable for:

```text
calculus
optimization
multivariable mathematics
```

#### Wave Visualization

```text
sine wave
standing wave
surface wave
frequency/amplitude visualization
```

Suitable for:

```text
signals
physics
Digital Image Processing signal concepts
```

### Tier 3 — Future product research

Possible later scenes:

```text
crystal lattice
electric field
magnetic field
optics/ray visualization
mechanical linkage
simple CAD/engineering inspection
anatomical educational model
graph/network visualization
```

These are not required for the initial G8 release.

---

## 11. Spatial Control Panel

### 11.1 Purpose

The application should support a touchless control surface that appears inside the displayed workspace when the user activates a dedicated control.

Conceptually:

```text
[ CONTROL SPACE ]
        ↓
spatial panel appears
        ↓
pointer moves over controls
        ↓
pinch selects
```

This is compatible with the project because it operates after `InteractionState`.

### 11.2 Initial implementation

The first version SHOULD be a rendered screen-space panel over or beside
the 3D viewport. The G7 baseline currently uses separate OpenCV and
Pygame/OpenGL windows, so the G8 layout may be coordinated or unified
based on a tested renderer integration; it must not assume that the
existing OpenGL context can be embedded into an arbitrary UI toolkit.

Example:

```text
┌─────────────────────────────┐
│        CONTROL SPACE        │
├─────────────────────────────┤
│ Scene                       │
│ [Cube] [Molecule] [Orbit]   │
│                             │
│ View                        │
│ [Home] [Reset] [Axes]       │
│                             │
│ Display                     │
│ [ROI] [Landmarks] [Help]    │
│                             │
│ Mode                        │
│ [Demo] [Analysis] [Evidence]│
│                             │
│            [ Close ]        │
└─────────────────────────────┘
```

### 11.3 Interaction mapping

Reuse public state.

```text
pointer_xy
    → spatial-panel cursor

pinch inactive → active
    → activation/click edge

pinch held
    → do not repeatedly click every frame

tracking lost
    → cancel hover/press safely

reacquisition
    → neutral until normal interaction resumes
```

A small application-layer click state machine should detect the pinch
rising edge.

Only `interaction_valid=True` frames may move or activate the spatial
cursor. An invalid or reacquisition-neutral frame cancels any pending
hover/press and clears the click edge. After such a reset, the router
SHOULD require a valid released-pinch frame before arming another click;
this prevents a hand that reappears while pinched from selecting a
control immediately. This is Extension behavior and MUST NOT change
`GestureEngine` semantics.

The panel cursor is mapped from full-frame normalized `pointer_xy` using
an explicit transform into the panel/viewport bounds. If the preview or
viewport is mirrored, the cursor transform must use the same documented
orientation. This is screen-space UI mapping, not physical 3D pointing or
augmented reality.

No new Core gesture is required.

### 11.4 Input focus

Introduce an application-level interaction router.

States may include:

```text
SCENE_FOCUS
UI_FOCUS
```

When:

```text
SCENE_FOCUS
```

the active scene receives:

```text
rotation_delta
scale_delta
```

When:

```text
UI_FOCUS
```

the spatial panel receives:

```text
pointer_xy
pinch state
```

and the application does not apply scene rotation/scale for those frames.

Core processing is unchanged.

### 11.5 Future world-space panel

After the screen-space panel is stable, an optional future implementation may render the control surface as a plane in the 3D scene.

For example:

```text
user presses CONTROL SPACE
        ↓
floating panel appears next to STEM object
        ↓
pointer ray/normalized pointer selects buttons
```

This is a presentation feature, not physical augmented reality.

The project must not claim that the panel exists in physical 3D space.

---

## 12. Dashboard visual design

Target visual language:

```text
professional
scientific
minimal
dark
high contrast
calm
consistent
```

Avoid:

```text
gaming HUD clutter
excessive neon
unnecessary animation
many unrelated colors
tiny diagnostic text
hard-coded scattered geometry
```

### Core layout

Recommended desktop structure:

```text
┌──────────────────────────────────────────────────────────┐
│ APP HEADER                        SYSTEM / FPS / STATUS   │
├─────────────────────────┬────────────────────────────────┤
│                         │                                │
│ LIVE VISION             │ INTERACTIVE STEM VIEW          │
│ camera + DIP overlay    │ active scene                   │
│                         │                                │
├─────────────────────────┼────────────────────────────────┤
│ DIP PIPELINE STATUS     │ INTERACTION STATUS             │
├─────────────────────────┴────────────────────────────────┤
│ MODE / SCENE / RESET / CONTROL SPACE / STOP             │
└──────────────────────────────────────────────────────────┘
```

### Design tokens

Centralize at least:

```text
background
surface
raised surface
border
primary text
secondary text
muted text
accent
success
warning
error

spacing scale
corner radius scale
font-size hierarchy
```

Do not duplicate raw style constants across components.

---

## 13. Responsive layout

Avoid a UI built from scattered fixed coordinates.

Create layout calculations from:

```text
window dimensions
margin
header height
footer height
workspace split
minimum panel dimensions
```

Define a supported minimum window size.

Resize should preserve:

```text
camera aspect ratio
usable 3D viewport
readable status regions
accessible controls
```

---

## 14. Error and empty states

Product-oriented presentation should provide explicit states.

Handle at least:

```text
camera unavailable
model unavailable
no hand
tracking temporarily lost
tracking reacquiring
interaction invalid
renderer initialization failure
unsupported evidence asset
clean shutdown
```

Do not leave stale green status indicators when the underlying state is invalid.

---

## 15. Research parameter safety

Normal application controls MUST NOT casually modify research-critical behavior.

Read-only display is encouraged for:

```text
active filter mode
illumination state
enhancement status
tracking status
run identity
```

The normal control panel may modify presentation state:

```text
scene
view
overlay visibility
application mode
scene reset
scene-specific visualization options
```

Changing algorithm thresholds or filter configuration requires an explicitly separate advanced/research configuration workflow with appropriate logging and governance.

---

## 16. Productization seam

The long-term architecture should make a future frontend replacement possible.

Conceptually:

```text
DIP Core
   │
public project contracts
   │
PresentationState + InteractionState
   │
   ├── current OpenCV + Pygame/OpenGL demo composition
   │
   └── future desktop/native/web frontend
```

Do not couple Core semantics to Pygame event objects or OpenGL scene classes.

---

## 17. Testing strategy

### Unit tests

Test:

```text
presentation-state mapping
layout calculations
scene registry
scene reset behavior
interaction focus routing
pinch rising-edge UI activation
spatial-panel hit testing
mode transitions
pointer transform/orientation mapping
click cancellation and release-to-rearm after invalid/reacquisition state
evidence view remains read-only with unavailable findings visible
```

### Existing interaction regression

Preserve tests for:

```text
rotation
scale
reset
loss/reacquisition
presentation callback
scene-state behavior
```

### Full regression

Run the full existing test suite after shared application/Extension changes.

G8 test count may grow beyond the G7 baseline.

Do not change old tests merely to hide a regression.

---

## 18. Physical validation

Before a G8 release, perform physical smoke validation for:

```text
camera preview
ROI/landmark overlays
touchless scene rotation
touchless scale
open spatial control panel
pointer hover
pinch select
scene switching
panel close
tracking loss while panel open
reacquisition
reset
clean shutdown
```

Record practical limitations honestly.

---

## 19. G8 implementation roadmap

### U0 — Baseline freeze

```text
[✓] G7 release tagged
[✓] G7 evidence frozen
[✓] feature branch created
```

Gate:

```text
post-G7 work starts from g7-final
```

### U1 — Application foundation

Implement:

```text
application controller
presentation state
theme tokens
responsive layout
basic dashboard shell
```

Keep existing 3D scene functional.

Gate:

```text
existing interaction works
layout resizes correctly
Core unchanged
focused tests pass
```

### U2 — DIP visibility

Implement:

```text
camera card
ROI overlay
landmark overlay
pointer overlay
tracking status
illumination status
CLAHE state
filter status
runtime identity
```

Gate:

```text
ANALYSIS mode visibly explains the DIP pipeline
```

### U3 — Scene architecture

Implement:

```text
STEMScene contract
SceneRegistry
scene lifecycle
existing cube migrated to registry
```

Gate:

```text
adding a new scene does not require modifying Core
```

### U4 — STEM scene package

Implement at least:

```text
coordinate geometry
molecule
orbital system
```

Gate:

```text
all scenes accept the same InteractionState contract
```

### U5 — Spatial Control Panel

Implement:

```text
CONTROL SPACE button
spatial panel
pointer cursor
pinch rising-edge selection
UI/scene focus routing
scene selection
mode selection
reset/home actions
```

Gate:

```text
panel operation requires no Core gesture change
```

### U6 — Evidence mode

Implement:

```text
RQ cards
selected G7 plots
evidence limitations
frozen result labels
```

Gate:

```text
no G7 claim is changed
```

### U7 — Commercial UX hardening

Implement:

```text
loading states
error states
empty states
disabled-state visuals
keyboard fallback
resource cleanup
responsive polish
```

### U8 — Automated validation

Run:

```text
targeted UI/Extension tests
full pytest regression
```

### U9 — Physical validation

Exercise complete realtime interaction.

### U10 — Documentation and release

Produce:

```text
screenshots
demo script
architecture diagram
extension-author guide
known limitations
new release/tag
```

---

## 20. Extension-author checklist

A new STEM scene is acceptable when:

```text
[ ] unique scene ID exists
[ ] metadata exists
[ ] it implements the scene interface
[ ] it consumes InteractionState only
[ ] it does not import MediaPipe
[ ] it does not access Core mutable internals
[ ] reset is deterministic
[ ] renderer resources are released
[ ] focused tests exist
[ ] scene selection works through registry
[ ] interaction remains safe after tracking loss
```

---

## 21. Codex optimization policy

Codex is encouraged to improve internal UI/Extension architecture when doing so makes the code:

```text
simpler
less coupled
more testable
more extensible
more readable
more robust
```

Codex must preserve:

```text
canonical Core semantics
G7 provenance
public interaction meaning
Core/Extension dependency direction
scientific claim boundaries
```

Large refactors should be split into coherent commits rather than mixing:

```text
architecture
visual polish
new scenes
behavior change
documentation
```

in one unreviewable change.

---

## 22. Productization direction and limits

G8 should improve the engineering qualities that could support later
product validation:

```text
clean modular boundaries
replaceable components
professional UX
multiple educational use cases
robust failure handling
testability
reproducibility
clear configuration ownership
future frontend portability
```

G8 completion does not establish commercial readiness. This phase does
not require introducing:

```text
accounts
cloud backend
telemetry service
subscription system
remote plugin marketplace
enterprise infrastructure
```

during G8.

Those belong to later product validation.

---

## 23. G8 Definition of Done

G8 is complete when:

```text
[ ] G7 tag/provenance remains unchanged

[ ] professional responsive dashboard exists

[ ] DEMO mode exists
[ ] ANALYSIS mode exists
[ ] EVIDENCE mode exists

[ ] DIP pipeline is visibly explainable in the application

[ ] STEMScene contract exists
[ ] SceneRegistry exists

[ ] at least three meaningful STEM scenes exist

[ ] spatial control panel exists
[ ] touchless pointer navigation works
[ ] pinch selection works
[ ] UI focus prevents accidental simultaneous scene manipulation

[ ] tracking loss/reacquisition is safe

[ ] no scene directly consumes raw landmarks or MediaPipe objects

[ ] error/empty states are explicit

[ ] targeted tests pass
[ ] full regression passes

[ ] physical camera smoke passes

[ ] extension architecture is documented
[ ] presentation/demo script is documented

[ ] a new post-G7 release identity is created
```

---

## 24. Final design principle

The project direction should be explainable in one sentence:

> The DIP Core produces an explicit, validity-bearing interaction signal; the Extension platform turns that signal into reusable touchless STEM experiences.

Every G8 design decision should reinforce that separation.

---
