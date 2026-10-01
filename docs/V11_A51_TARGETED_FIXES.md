# v1.1 A5.1 — targeted P1 fixes

Implemented 2026-10-01 on `feat/v1.1-full-hand`, starting from
`d93ead49931bcfdbc55236713bbfe067d3c0bbe7`. This is Extension-only,
observation-only behavior. No full-hand commands are enabled.

## Evidence inspected before implementation

Read the original P1 sidecars and filtered landmark logs for
`g8-demo-20261001-221417`, `g8-demo-20261001-221612` and
`g8-demo-20261001-222450`. Execution revision and unchanged profile hash are
recorded in [the historical P1 report](V11_P1_PHYSICAL_OBSERVATION.md).
Original local logs and that report were not rewritten.

The new regression fixture preserves selected recorded coordinates, timestamps,
distances, finger states and original classifications. It is development test
data, separate from frozen G7 evidence. It stores no images/video. Its provenance
and transformed-input distinction are in
[the fixture index](../tests/extensions/full_hand/fixtures/README.md).
Before implementation, the new regression tests produced **19 failures and
5 passes**, reproducing both the band-disarm and opposed-thumb FIST failures.

## PINCH root cause and exact semantics

Run 2 frames 74–78 earned release/rearm with POINT and strict pinch exit.
Frame 81 entered the pure A3 pinch boundary band and discarded that earned arm.
The old exception held the band only after PINCH was already stable. This made
the ordinary pre-entry crossing behave like genuine pose ambiguity.

Only a valid observation with known fingers and exactly
`PINCH_BOUNDARY_BAND` receives the following treatment:

- Preserve an already earned `armed` state and stable diagnostic memory/latch.
- If unarmed, remain unarmed and expose `PINCH_BAND_WAIT`; the band never creates
  an arm, latch or action.
- Cancel pending pose entry/exit and clear release/rearm dwell. No dwell may
  bridge band frames. `PINCH_BAND_HOLD` identifies preservation when armed.
- Every UNKNOWN frame remains `action_allowed=False`.
- After initialization, loss, reset or genuine ambiguity, rearm still requires
  continuous valid, known non-PINCH observations with **distance > exit** for
  the existing configured rearm dwell. Equality is not release evidence.
- Returning to definite PINCH cancels release dwell. A new PINCH entry after
  a band must earn a fresh complete entry dwell; a stable PINCH can resume on a
  definite enter observation. Definite released candidates still require exit
  dwell before replacing a stable PINCH.
- Genuine UNKNOWN, invalid geometry, loss, reacquisition, timestamp/run/filter
  resets retain their immediate neutralization/disarm behavior.

No timing or distance threshold changed.

## FIST root cause and exact predicate change

The recorded FIST attempts often have four non-thumb fingers FLEXED with the
thumb opposed across the palm, while the projected thumb chain is intermediate
or nearly straight. Requiring chain flexion **and** opposition to classify the
thumb FLEXED made the old all-five-FLEXED FIST predicate reject this posture.

Run 3 frame 337 has opposed distance 0.128429 palm widths, axis-to-palm angle
0.184773 rad, chain minimum angle 2.205964 rad and straightness 0.838501.
Frame 1355 has opposed distance 0.360601, axis 0.718961, angle 2.759238 and
straightness 0.958951. Both have four FLEXED non-thumb fingers and strict pinch
exit, but the recorded thumb state and pose were INTERMEDIATE/UNKNOWN.

The finger estimator is unchanged. FIST now requires four non-thumb FLEXED
states plus either:

1. a FLEXED thumb (the original accepted case); or
2. an INTERMEDIATE thumb with both existing `thumb_opposed` and palm-axis
   predicates true.

The explicit new `fist_thumb_compatible` diagnostic explains the decision.
Opposition uses the existing maximum MCP distance; axis compatibility uses the
existing maximum axis angle. No thresholds, geometry extraction or per-finger
states changed. Unopposed/axis-incompatible intermediate thumbs, conflicting
features, invalid geometry and UNKNOWN fingers do not pass. OPEN/POINT rules,
PINCH precedence and the A3 UNKNOWN band are unchanged. Mirrored and in-plane
rotated recorded fixtures exercise the same correction.

## Replay result and remaining limitation

Reclassified all **2811 original P1 snapshots** using the same recorded geometry
and replayed timestamps/tracking/filter-reset metadata through the updated
temporal tracker. This is offline development analysis, not a new physical run,
accuracy measurement or Core research experiment.

| Run suffix | Candidate changes | New stable FIST snapshots | UNKNOWN action permission |
|---|---|---:|---:|
| `221417` | 4 UNKNOWN → FIST | 0 | 0 |
| `221612` | 2 UNKNOWN → FIST | 0 | 0 |
| `222450` | 151 UNKNOWN → FIST | 128 | 0 |

All original OPEN/POINT/PINCH candidates were preserved. Stable-state counts
include diagnostic memory retained on band frames; they are not command counts
or ground-truth correctness labels. Run 2 preserved an earned arm on 85 band
frames. **Stable PINCH remains absent in the complete recorded sequences**:
genuine UNKNOWN/invalid observations still disarm, and several definite PINCH
spans are too short. The fix resolves the isolated pure-band defect; it does not
justify bypassing other safety gates or lowering thresholds.

## Validation and change record

- Focused full-hand suite: **335 passed**.
- Full `pytest -q`: **890 passed**.
- `python -m compileall extensions/stem3d`: PASS.
- `git diff --check`, including new-file whitespace checks: PASS.
- Regression coverage: recorded FIST and band excerpts; reflection/rotation;
  thumb opposition/axis boundaries and negative/conflicting cases; PINCH
  precedence; band equality, dwell cancellation, fresh entry, loss/reacquisition;
  existing legacy parity and observation lifecycle tests.

Change: targeted temporal band preservation and FIST-only thumb compatibility.
Reason: reproduced P1 failures. Canonical sections changed: NONE. Modules:
`full_hand/temporal.py`, `temporal_contracts.py`, `pose_classifier.py` and their
tests/docs. Algorithmic impact: opt-in Extension pose observations only.
Experimental impact: NONE. Compatibility impact: additive diagnostics and the
documented targeted full-hand changes; Core/InteractionState/legacy application
output, sensitivity, scenes/router/UI architecture remain unchanged.
Existing G7 results invalidated: **no**; frozen research paths and Core match
`g7-final`, whose peeled revision remains
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. G9 paths remain absent and its stash
is retained. No stage, commit, push or tag was performed.

**Ready for a P1 re-run in OBSERVE_FULL_HAND only.** Repeat OPEN → definite
release → slow PINCH crossing → sustained PINCH, then comfortable FIST and
intermediate poses, with clear per-condition labels. Verify safety and legacy
usability. Physical validation of this fix is **NOT RUN**; enabling commands is
not authorized by these automated results.
