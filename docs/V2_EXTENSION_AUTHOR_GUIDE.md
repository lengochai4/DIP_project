# Author a V2 STEM extension

Add a presentation `LabGuide` entry under its ID in `app/ui/lab_guides.py` when
registering a lab. Explain purpose, actual LIVE input (all-tip geometry vs a
single semantic probe), a short recipe, expected output and scientific limits.
Include appropriate recorded/mouse guidance rather than implying every finger
controls a separate model parameter. Guide content must not read provider/Core
internals. Explore owns visibility, enlarged layout and native scroll shortcuts.
Use `developer_tools.live_fingertip_qa --workspace [--opengl]` for synthetic
guide/hidden/expanded/expanded-guide/restored checks at three desktop sizes.

Implement `StemExtension` from `app/extensions/base.py`, or subclass `Lab` for
standard transforms, picking, construction and measurement tools. Set unique
`id`, `title`, `category`, `supports_hand_anchor`, `presets` and `tools` metadata.
Register the class in `app/extensions/registry.py`.

`activate`/`deactivate` own only scene lifecycle. `reset` is deterministic;
`update(dt)` uses scene time. `render(context)` returns immutable `Geometry`
containing `Line`, `Ball`, optional triangle `Face` and labels in scene coordinates.
Set `view_radius` to a scene framing radius when default framing is insufficient.
WORLD and HAND use
the same geometry; do not create a second camera-specific scene.

Native rendering uses perspective, illuminated GPU meshes and depth testing.
Software uses the same projection with approximate primitive occlusion. Keep
faces finite and nondegenerate; do not embed GPU buffers or camera data in geometry.

`on_intent` receives semantic `GestureIntent` only. It must immediately clear
transient manipulation on CANCEL/RELEASE and ignore invalid commands. Do not
import MediaPipe, camera acquisition, landmarks, finger IDs, pose classifiers,
hand geometry or product thresholds. The renderer/presentation layer resolves
pointer coordinates into `world_or_scene_point` and pair points first.

POINT may inspect/highlight; it does not manipulate a transform. GRAB begins a
clutch; DRAG updates only that clutch. SCALE uses the entry scale multiplied by
the intent's relative factor, bounded by the product profile. Commit intents
are idempotent per input source/tool/cycle; `input_source` distinguishes GESTURE
from MANUAL fallback cycles. The shell resolves window-normalized pointers in
WORLD/UI and unmirrored source pointers/pair snapshots through camera letterboxing
in HAND scene control. Extensions receive resolved scene points in either mode;
they must not interpret source coordinates or implement their own mirror/gain.
Measurements are scene units. Missing or
view-parallel plane intersections stay unavailable, never zero-filled.

Default LIVE uses exclusive TOOL_UPDATE intents with `live_geometry=True`.
Presentation maps all active source samples into scene `points` before delivery;
up to ten vertices update continuously without commits or persistent construction.
Opaque `vertex_tokens` associate successive scene vertices; never interpret their
anatomical meaning. `Lab` implements the common layer using `live_shape` and
`constructed()`. All nine labs use it. CANCEL/RELEASE/deactivate clear the live
shape. Export takes a scene-only immutable snapshot before modal cancellation.
RECORDED retains the POINT/pinch tools above. Relative model-z relief belongs to
presentation and must never be described as physical camera depth.

LIVE nearly planar boundaries use angular order about the projected scene centroid;
surface fans use that centroid without adding a fingertip. Noncoplanar sets with
four or more vertices use a closed convex hull with outward facets and merged
coplanar faces. Interior vertices remain in points/tokens and vertex markers.
Relative SVD planarity policy is configured, never a physical calibration result.
`live_surface_overlay` fills Coordinate/Vector; other labs draw wire edges so the
live surface does not obscure the educational model. `dimensionality` states what
the model represents. Stable `LiveShape.labels` follow opaque tokens; analytical
inputs must use stable semantic order, not rotating outline order. `vertex_details`
is shown only after lab values with diagnostics enabled. No physical hand volume
or chemical dimensions may be inferred from visual geometry or its scene volume.

For computed educational values, implement exact documented equations and
tests for invariants. Distinguish illustrative geometry from physical models.
No scene computation is G7 evidence, a chemical measurement or camera depth.

Test all presets, reset, cancel/loss, picking, repeated commit, finite geometry
and shared WORLD/HAND rendering. Use `developer_tools.v2_qa` for native synthetic
captures and clearly label them; physical usability cannot be inferred from them.
Use `developer_tools.live_fingertip_qa` (optionally `--opengl`) for automatic
all-finger geometry surfaces; it uses synthetic 21-landmark input, not a webcam.
Add `--all-presets` to cover every extension/preset with point, triangle,
tetrahedron and ten-tip inputs in both WORLD/HAND.
