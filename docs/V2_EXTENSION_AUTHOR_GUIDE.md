# Author a V2 STEM extension

Implement `StemExtension` from `app/extensions/base.py`, or subclass `Lab` for
standard transforms, picking, construction and measurement tools. Set unique
`id`, `title`, `category`, `supports_hand_anchor`, `presets` and `tools` metadata.
Register the class in `app/extensions/registry.py`.

`activate`/`deactivate` own only scene lifecycle. `reset` is deterministic;
`update(dt)` uses scene time. `render(context)` returns immutable `Geometry`
containing `Line`, `Ball` and labels in scene coordinates. WORLD and HAND use
the same geometry; do not create a second camera-specific scene.

`on_intent` receives semantic `GestureIntent` only. It must immediately clear
transient manipulation on CANCEL/RELEASE and ignore invalid commands. Do not
import MediaPipe, camera acquisition, landmarks, finger IDs, pose classifiers,
hand geometry or product thresholds. The renderer/presentation layer resolves
pointer coordinates into `world_or_scene_point` and pair points first.

POINT may inspect/highlight; it does not manipulate a transform. GRAB begins a
clutch; DRAG updates only that clutch. SCALE uses the entry scale multiplied by
the intent's relative factor, bounded by the product profile. Commit intents
are idempotent per input source/tool/cycle; `input_source` distinguishes GESTURE
from MANUAL fallback cycles. The shell resolves window-normalized control pointers
to viewport-local picking coordinates in both WORLD and HAND; source-image palm
and skeleton coordinates remain separate. Measurements are scene units. Missing or
view-parallel plane intersections stay unavailable, never zero-filled.

For computed educational values, implement exact documented equations and
tests for invariants. Distinguish illustrative geometry from physical models.
No scene computation is G7 evidence, a chemical measurement or camera depth.

Test all presets, reset, cancel/loss, picking, repeated commit, finite geometry
and shared WORLD/HAND rendering. Use `developer_tools.v2_qa` for native synthetic
captures and clearly label them; physical usability cannot be inferred from them.
