# Practical controls decision — 2026-10-02

The user explicitly replaced the PINCH-first product direction with simple
one-finger / one-open-hand / two-hand actions, authorized UI/UX implementation
without prior documentation scope locks, and permitted Core optimization when
needed and recorded. Historical documents remain execution records; their gate
sequence does not block this authorized product change.

## Application semantics

- SIMPLE is the new `extensions.stem3d.app` launch default. LEGACY, OBSERVE and
  the unvalidated intentional-PINCH experiment remain selectable, unchanged.
- One extended index with middle/ring/pinky FLEXED: POINT rotates the scene after
  0.25 s valid source-time dwell. First stable frame only captures a new anchor.
- Four extended non-thumb fingers: OPEN navigates. Thumb pose/contact is not
  required; the name means comfortable open palm, not a precise five-finger test.
  UNKNOWN/intermediate non-thumb states are neutral. No A3/FIST thresholds change.
- OPEN held 0.8 s opens Control Space once. A fresh POINT/UNKNOWN is needed before
  a subsequent automatic opening, preventing immediate reopening after Close.
- In Control Space, OPEN moves the palm pointer. Central 70% of the source frame
  maps to the menu, then optional mirror. Continuous hover on an enabled target
  for 1.2 s issues one UI-only selection pulse; the same target cannot repeat until
  the pointer leaves or the gesture is lost/changed. A progress bar explains dwell.
  On menu entry the pointer must first move at least 0.04 in normalized menu
  coordinates; a stationary palm cannot auto-select the button under it.
- The existing router consumes the pulse in its click-edge field; it is explicitly
  **not physical PINCH evidence**. No scene rotation/scale accompanies UI selection.
- Two OPEN palms use deterministic existing association plus acquisition dwell
  and bounded projected-separation scaling. Pair presence suppresses one-hand
  rotation and menu selection. No PINCH reference is required in SIMPLE.
- Evidence permits menu navigation but never transforms the hidden scene. Modal
  Settings/Help, lost focus, invalid geometry/timestamps and tracking loss revoke.
- Frozen research output remains the legacy shadow. Product output is recorded
  separately with SIMPLE owner/candidate/stable/hover/pulse diagnostics.

These timing/mapping values are explicit application starters, not findings of
physical accuracy testing. No physical skin-contact classifier, new FIST command,
metric depth claim or handedness-confidence shortcut is introduced.

## Core and performance record

No Core change was needed for this unit. The existing read-only runtime callback
and InteractionState boundary support all three actions. Existing measured CPU
UI background-copy optimization remains Extension-only. Independent two-hand
inference adds cost; no unmeasured speedup or webcam FPS is claimed. Future Core
optimization must identify the measured hot path and record contract/regression
impact rather than rewrite filters/provider semantics speculatively.

G7 and v1.0 tags, frozen report/evidence/experiments remain unchanged. G9 remains
absent/stashed. No stage, commit, push or tag operation belongs to this work.

## Validation

Synthetic tests cover finger-count semantics for every thumb state, dwell,
motion-anchor capture, hover latching through a scene change, menu close/reopen,
UNKNOWN/loss/reacquisition, stale frame identity, timestamp faults, mirror,
deterministic replay, no-reference composition and exclusive two-hand delivery.
They are software checks, not physical usability evidence. Next decision is a
short complete-application smoke using the three practical gestures, followed by
fixes for observed failures. Experimental PINCH calibration failures in run
`stem-v11-20261002-175620-990648` do not gate the SIMPLE product path.
