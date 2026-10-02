# v1.1 A5.2 — geometry-driven PINCH release/rearm

Implemented 2026-10-02; observation-only. The classifier, FIST thumb logic,
thresholds/profile and all legacy commands remain unchanged.

## State-machine change

Clutch evidence and semantic pose permission are now separate:

- Geometry validity requires complete unique finger geometry without geometry
  errors, a finite nonnegative palm-normalized pinch distance and exactly one
  valid A3 enter/exit/band predicate. A semantic UNKNOWN finger or pose does not
  by itself invalidate that pinch geometry. Known command candidates still
  require consistent semantic observations with known finger states.
- Initialization, run/frame/timestamp discontinuity, excessive gap, filter reset,
  explicit reset, invalid geometry, tracking loss and reacquisition neutralize
  the pose, clear all dwell, and disarm. Their first/reset sample cannot rearm.
- While unarmed, continuous valid geometry with **distance > exit** earns the
  existing `rearm_dwell_s`. No OPEN/POINT/FIST match is required. The completing
  frame reports `REARMED`, is still action-neutral, and does not begin pose dwell.
- Band (`enter <= distance <= exit`) and definite enter (`distance < enter`)
  cancel partial release dwell. They cannot rearm. An unarmed pure band exposes
  both `PINCH_BAND_WAIT` and `REARM_PENDING`; an earned arm is preserved.
- After armed, known candidates use the unchanged enter/exit dwell rules.
  UNKNOWN always cancels pending pose dwell and permits no action. General
  semantic UNKNOWN releases stable action memory/latch but preserves an earned
  geometry-based arm and valid release dwell. The existing pure-band exception
  can retain diagnostic stable memory/latch, still with action permission false.
- Returning to PINCH while waiting for release cancels release dwell. Re-entry
  after semantic UNKNOWN starts fresh candidate dwell; it cannot inherit an old
  pending transition. Geometry/lifecycle faults always override earned rearm.

The tracker consumes A3's strict distance predicates rather than introducing
duplicate distance thresholds. No new calibration, commands or profile fields
were added. `InteractionState` is untouched.

## Recorded regression evidence

New development fixture `tests/extensions/full_hand/fixtures/p1_rearm_sequences.json`
contains contiguous recorded sidecar excerpts and filter-reset metadata from
legacy frame logs. Original logs, physical reports and G7 evidence are unchanged.
The fixture stores original revisions/profile hashes, unrounded distances and
timestamps, geometry reasons, semantic observations and original armed states.
No images/video or intended-pose accuracy labels were added.

Compared the HEAD A5.1 tracker and updated tracker in memory on the same excerpts:

| Recorded excerpt | A5.1 stable PINCH | A5.2 result |
|---|---|---|
| P1 `g8-demo-20261001-221612`, frames 74–349 | None | Stable PINCH snapshots 322–349; earned rearm survives semantic UNKNOWN |
| P1b `g8-demo-20261001-225528`, frames 228–258 | None | UNKNOWN release geometry rearms at 233; stable PINCH at 252–258 |

Both comparisons had zero UNKNOWN snapshots permitting action. These are
timestamped **excerpt replays**, not a new physical run, whole-run accuracy,
or frozen Core research experiments. Starting an excerpt initializes the
tracker at its first frame; counts are not substituted for full-run results.

## Validation and change record

- Focused `pytest -q tests/extensions/full_hand`: **355 passed**.
- Full `pytest -q`: **910 passed**.
- `python -m compileall extensions/stem3d`: PASS.
- `git diff --check` and new-file whitespace checks: PASS.
- Added 20 test cases: recorded P1/P1b sequences, UNKNOWN release timing and
  dwell boundaries, inclusive band endpoints, interrupted release, fresh PINCH
  re-entry, semantic finger UNKNOWN versus valid pinch geometry, loss and
  reacquisition, invalid geometry, run/time/gap/filter/explicit resets, and no
  action on UNKNOWN. Earlier tests were updated only where they required the
  superseded semantic-pose-dependent rearm rule. Existing safety, classifier,
  legacy parity and observation lifecycle tests remain passing.

Change: separate semantic action cancellation from clutch neutralization;
geometry-only release evidence. Reason: P1b definite-release geometry was
discarded by UNKNOWN/NO_POSE_MATCH. Canonical sections changed: NONE.
Code: `extensions/stem3d/full_hand/temporal.py`; tests and supplemental docs.
Algorithmic impact: opt-in Extension temporal observation only. Experimental
impact: NONE. Compatibility impact: the explicitly requested rearm semantics;
public dataclass fields and Core/legacy application output unchanged. Existing
G7 results invalidated: no. Frozen paths, G7 tag, G9 stash and source absence
remain unchanged. No stage, commit, push or tag performed.

**Ready for P1c physical validation in OBSERVE_FULL_HAND.** Physical validation
of A5.2 is NOT RUN. Full-hand commands remain disabled. Verify sustained
release → enter → hold → release → re-enter, UNKNOWN action blocking and
loss/reacquisition at adequate lighting; automated replay does not establish
physical reliability.
