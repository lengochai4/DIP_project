# v1.1 P1 physical pose observation — 2026-10-01

Status: **P1 PARTIAL**. Real webcam observation ran; OPEN and POINT reached
stable states. PINCH never became stable and FIST was never classified.
These findings do not authorize full-hand commands. No thresholds were tuned.
This supplemental development record is separate from frozen G7 evidence.

## Run identity and provenance

Executed in the existing Python 3.11.0 environment:

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND
```

The actual executable was `.venv\Scripts\python.exe`, with `-u` for console
diagnostics. Branch: `feat/v1.1-full-hand`; execution revision:
`1042d61cc9c9e7ac861c6ada551b56ff9b8834a9`.

All three manifests record the same identities:

- Legacy config hash: `ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.
- Observer profile: `config/extensions/full_hand_observe.yaml`.
- Resolved profile SHA-256: `a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
- MediaPipe model SHA-256: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.
- Actual source geometry in every snapshot: 640 × 480. Camera metadata has
  `observed: null`; dimensions above come from the captured source frame.

Local, ignored artifacts for each ID are `runs/<id>/` (legacy CSV/config logs)
and `runs/full-hand-observe/<id>/` (`manifest.json`, `snapshots.jsonl`).
No webcam images/video were saved by the observer. This is not a synthetic run.

## Recorded observations

Counts below are from physical run logs. Candidate/stable counts include only
frames whose tracking status was VALID. NO_HAND includes deliberate or possible
withdrawal/occlusion and cannot be interpreted as an unintended-drop rate.

| Run ID | Frames | Duration, first–last frame | VALID / NO_HAND | Candidate UNKNOWN / VALID | Clean shutdown |
|---|---:|---:|---:|---:|---|
| `g8-demo-20261001-221417` | 464 | 15.612 s | 423 / 41 | 220 / 423 (52.01%) | PASS |
| `g8-demo-20261001-221612` | 976 | 32.571 s | 928 / 48 | 659 / 928 (71.01%) | PASS |
| `g8-demo-20261001-222450` | 1371 | 46.174 s | 1225 / 146 | 961 / 1225 (78.45%) | PASS |

| Pose | Candidate frames, runs 1 / 2 / 3 | Stable frames, runs 1 / 2 / 3 | Reliability decision |
|---|---|---|---|
| OPEN | 78 / 133 / 75 | 67 / 89 / 27 | Observed, conditional; insufficient coverage for robust commands |
| POINT | 115 / 48 / 173 | 17 / 12 / 110 | Observed, conditional; insufficient coverage for robust commands |
| PINCH | 10 / 88 / 16 | 0 / 0 / 0 | Not ready; temporal entry/rearm blocker |
| FIST | 0 / 0 / 0 | 0 / 0 / 0 | Not ready; thumb/predicate investigation required |
| UNKNOWN | 220 / 659 / 961 | 339 / 827 / 1088 | Intermediate exercised; neutral safety observed, selectivity not quantified |

Mixed-pose UNKNOWN frequency is descriptive, **not classification accuracy**:
poses and conditions have no synchronized ground-truth annotations. Intended
intermediate poses and transitions naturally contribute UNKNOWN.

OPEN had a 2.186 s continuous stable span in run 1, frames 11–77. POINT had a
1.828 s stable span in run 3, frames 1088–1143. Stable transitions and safe
releases were recorded; brief unresolved inputs often interrupted pose dwell.

### PINCH entry failure

In run 2, all 88 PINCH candidates were unarmed with `REARM_PENDING`. Frames
337–349 remained PINCH for 0.401504 s, exceeding the configured 0.25 s entry
dwell, but never started an armed transition. Frames 80→81 show armed POINT
followed by pure `PINCH_BOUNDARY_BAND`, which cancels the pending transition and
disarms. A4 preserves the band only after stable PINCH already exists. Inspection
therefore identifies a pre-entry hysteresis/rearm incompatibility; additional
genuine UNKNOWN inputs also disarm and must remain safe.

### FIST-like geometry and thumb limitation

Run 3 contains 341 frames with INDEX/MIDDLE/RING/PINKY all FLEXED. Thumb was
INTERMEDIATE in 316 and EXTENDED in 25, never FLEXED. Resulting poses were
UNKNOWN in 338 and PINCH in 3. These are geometric observations, not 341
ground-truth FIST labels or confirmed false positives.

For example, run 3 frame 1355 has four FLEXED fingers, thumb chain minimum
angle 2.759238 rad and straightness 0.958951, while thumb opposition distance
0.360601 palm widths satisfies the opposition predicate. The thumb remains
INTERMEDIATE because FLEXED requires both chain flexion and opposition; FIST
requires all five fingers FLEXED. A comfortable thumb placed outside a fist may
not satisfy that chain predicate. Frame 337 similarly has four FLEXED fingers,
pinch exit true, and `NO_POSE_MATCH` with unresolved thumb posture.

## Physical coverage and practical limitations

The operator explicitly confirmed OPEN/POINT/PINCH were tried in the first two
runs, then asked how to perform FIST/intermediate. FIST was explained as a
comfortable closed fist with thumb outside; intermediate as half-curled fingers
or two extended fingers. Run 3 was requested specifically for those poses and
the remaining conditions. A captured live window showed a closed-looking hand.
After run 3 the operator confirmed: “làm hết rồi, tất cả đều làm như bạn”
(all requested steps completed). This confirms checklist completion but supplies
no frame-level labels, measurements, or separate usability ratings.

| Physical requirement | Evidence / status |
|---|---|
| OPEN / POINT / PINCH exercised | Operator confirmed; logged candidate/stable results above |
| FIST / intermediate exercised | Operator confirmed after targeted run 3; no FIST classification |
| Wrist rotation / translation | Operator confirmed; no synchronized condition labels |
| Near / medium / far | Operator confirmed; physical distances not measured |
| Palm toward camera / moderate side angles | Operator confirmed; angles not measured |
| Hand out / in | Operator confirmed; log returns observed: 0 / 1 / 9 by run |
| Brief occlusion | Operator confirmed; not isolated from other NO_HAND periods |
| Normal / reasonably different lighting | Operator confirmed; illumination not quantified |
| Legacy rotate / scale usability | Operator confirmed completion; commands/visible rotated object observed; no additional usability problem reported |

Tracking returned after NO_HAND nine times in run 3. Temporal reacquisition
also occurs after invalid finger geometry, so its event count must not be treated
as the provider tracking-loss count. Across all runs no UNKNOWN snapshot had
`action_allowed=true`, and no observer diagnostic errors were recorded. Camera
warnings included MediaPipe feedback-tensor support and NORM_RECT projection;
these were not hidden or changed. Existing GPU overlay obscured part of the
application header during window inspection; no UI/system setting was altered.

## Legacy parity and integrity

Offline replay of the recorded physical filtered landmarks through the unchanged
legacy GestureEngine matched every recorded InteractionState field on all
**2811 frames**, with zero mismatches. This is a legacy-engine comparison on the
same recorded samples, not a synthetic replacement for physical testing, not a
Core replay experiment, and not proof of unchanged wall-clock performance.
There were 1481 nonzero rotation-command frames and 356 nonzero scale-command
frames. Only legacy GestureEngine produced application commands; full-hand
analysis remained observation-only.

Core, legacy interaction, InteractionState, sensitivity, UI architecture,
research experiments and frozen evidence were not modified. Frozen paths and
Core source match `g7-final`; its peeled revision remains
`f454c6b8325c85199c0122c0e822fe8e76c1526c`.
G9 source paths remain absent and stash
`d709da693e6adc4dec94e6925e7cd202ae0dd507` remains retained.
No stage, commit, push or tag was performed.

## Smallest recommended next action — not implemented

1. Review the temporal treatment of a **valid, pure pinch boundary band before
   entry**. Preserve an already earned released/armed latch through that band,
   cancel pending pose dwell, keep UNKNOWN action permission false, and require
   a fresh definite PINCH dwell. Continue neutralizing on genuine ambiguity,
   invalid geometry, loss, reset and reacquisition. Verify timestamped replay of
   the failing transitions and safety regressions before another physical run.
   No distance threshold or legacy sensitivity adjustment is recommended.
2. Review a narrowly scoped FIST thumb-compatibility predicate using existing
   thumb opposition/axis geometry when four fingers are definitely FLEXED.
   Annotate representative intended FIST frames first. Preserve
   PINCH precedence and ambiguous/invalid UNKNOWN handling; do not globally
   relax finger thresholds or treat every unresolved thumb as a fist.
3. Repeat a labeled physical observation after any separately authorized fix,
   including separately labeled angle/distance/lighting/occlusion conditions and
   explicit legacy usability ratings. Do not enable full-hand commands yet.

No implementation or threshold changes were made in P1. The pytest suite was
not rerun for this observation-only task; the earlier A5 test result is not a
new P1 validation claim.
