# v1.1 P1b physical re-validation — 2026-10-01

**P1b PARTIAL.** Two real webcam runs after A5.1 closed cleanly. The pure-band
disarm defect did not recur, and recorded legacy InteractionState parity was
exact. PINCH and FIST did not reach stable states, so release/re-entry and reliable
FIST operation are not validated. Full-hand remains observation-only.

## Identity and unchanged setup

Executed with `.venv\Scripts\python.exe -u`:

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND
```

- Branch: `feat/v1.1-full-hand`.
- Revision: `38188f8b0acba74e5e360f2093f289fa84477ef6` (clean at launch).
- Profile: `config/extensions/full_hand_observe.yaml`.
- Resolved profile SHA-256, both runs:
  `a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
- Legacy config hash:
  `ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.
- Actual frame geometry: 640 × 480; Python 3.11.0.
- No profile, thresholds, commands, Core or application behavior changed.

Local ignored provenance: `runs/<id>/frames.csv`, `landmarks.csv`,
`resolved_config.yaml`, and `runs/full-hand-observe/<id>/manifest.json` /
`snapshots.jsonl`. Local read-only analysis outputs are under
`runs/p1b-observation/`. No observer webcam images/video were stored; no
synthetic physical validation was substituted. These are development artifacts,
separate from frozen G7 evidence/experiments.

## Physical procedure and operator evidence

Requested three cycles of OPEN, POINT, OPEN, PINCH hold, OPEN release, PINCH
re-entry, OPEN, FIST and intermediate, plus wrist rotation, near/medium/far,
moderate side angles, withdrawal/reacquisition and brief occlusion. After run 1,
the operator answered that the environment was too dark, detection worked
intermittently, and the FIST thumb was not recognized. Exact hold durations,
cycle count and condition boundaries were not annotated.

A second slower run was requested with sufficient ordinary light and 5-second
OPEN → PINCH → OPEN → PINCH → OPEN → FIST → intermediate holds. Its preview
still looked dim at the inspected instant. Completion/lighting change and a
separate legacy usability rating have not been explicitly confirmed for this
second run. Each run contains about 28 seconds of processed frames; neither
log proves that every requested hold/cycle was completed as instructed.

## Per-pose recorded result

Counts include VALID tracking frames only. Stable counts are diagnostics, not
application command counts. Mixed-condition counts are not classification
accuracy or false-positive rates.

| Item | `g8-demo-20261001-225053` | `g8-demo-20261001-225528` |
|---|---:|---:|
| Processed frames | 837 | 834 |
| First–last frame duration | 28.380 s | 28.106 s |
| VALID / NO_HAND | 584 / 253 | 631 / 203 |
| OPEN candidate / stable | 120 / 51 | 17 / 6 |
| POINT candidate / stable | 117 / 17 | 150 / 90 |
| PINCH candidate / stable | 19 / 0 | 54 / 0 |
| FIST candidate / stable | 25 / 0 | 16 / 0 |
| UNKNOWN candidate / stable | 303 / 516 | 394 / 535 |
| Stable PINCH enter transitions | 0 | 0 |
| Stable FIST enter transitions | 0 | 0 |
| Generic release/rearm completions (`REARMED`) | 12 | 7 |
| Pure band frames | 67 | 159 |
| Sampled time in pure band | 2.236588 s | 5.347743 s |
| Band incorrectly disarmed an earned arm | 0 | 0 |
| Tracking loss → return pairs | 18 | 7 |
| Observer diagnostic errors | 0 | 0 |
| UNKNOWN frames permitting action | 0 | 0 |

Band duration sums each band frame's interval to the next timestamp; there is
no invented final-frame duration. NO_HAND includes intended withdrawal/occlusion
and possible unintended loss; it is not an isolated tracking-failure measurement.

OPEN and POINT can stabilize but remain conditional. Longest stable OPEN:
run 1 frames 708–734, 0.859659 s; POINT: run 2 frames 478–543, 2.180542 s.
Intermediate UNKNOWN remained action-blocked. Wrist/distance/angle conditions
have no synchronized labels, so per-condition reliability is insufficiently
established.

## PINCH transition evidence

Run 1 frame 528 completed rearm. Frames 531–537 are UNKNOWN with
`PINCH_BAND_HOLD`, retain `armed=True`, cancel pending dwell, and never permit
action. Across both runs there were no armed→unarmed changes caused solely by
the valid pure band. Run 2 records 159 `PINCH_BAND_WAIT` frames while unarmed:
the band did not pretend to provide release evidence.

Run 2 frames 229–244 have usable geometry, known finger states and distances
0.634469 down to 0.370215 palm widths, all **above exit 0.35**. Nevertheless,
their pose is UNKNOWN/`NO_POSE_MATCH`, causing `UNKNOWN_INPUT` and disarming.
Frames 245–258 are definite candidate PINCH for 0.440686 s (longer than the
0.25 s enter dwell), but remain unarmed/`REARM_PENDING`.

Of 73 total PINCH candidates, 70 report `REARM_PENDING`, two are reacquisition
neutral and one starts a pending candidate transition. No stable PINCH release
or re-entry transitions occurred. No stuck stable PINCH was observed because
PINCH never latched; post-latch release safety and successful re-entry therefore
remain **unverified**, rather than passing by absence.

## FIST states and false-positive limitations

Run 1 has 109 frames with four non-thumb fingers FLEXED; thumb is INTERMEDIATE
in 95 and EXTENDED in 14. Of these, 25 classify FIST, 17 PINCH and 67 UNKNOWN.
Run 2 has 147 such frames; thumb is INTERMEDIATE in 145 and EXTENDED in two;
16 classify FIST, nine PINCH and 122 UNKNOWN.

The A5.1 compatibility predicate can therefore produce FIST candidates without
relabeling the thumb FLEXED, but no stable FIST transition occurs. The longest
candidate FIST spans are only 0.111527 s and 0.036595 s. Among four-curled-finger
frames, 23 / 15 fail thumb compatibility and 45 / 112 lie in the pinch band.
Example run 2 frame 151 has a thumb EXTENDED with MCP distance 0.728888 palm
widths, so the opposition predicate correctly does not pass; perspective and
the intended posture at that exact frame are unannotated.

The operator reported difficulty recognizing the thumb during FIST. Candidate
FIST observations show predicate acceptance during the mixed physical exercise,
but cannot be assigned definitive true-positive labels without synchronized
intent. False FIST during OPEN/POINT/PINCH/intermediate likewise cannot be
confirmed or ruled out from unannotated logs. **Zero stable FIST is not proof
of zero candidate false positives.** No false-positive rate is claimed.

## Legacy parity, safety and shutdown

Offline replay of the same recorded physical filtered landmarks through the
unchanged legacy GestureEngine matched all InteractionState fields on
**1671 / 1671 frames**, with **zero mismatches**. This is not a Core replay
experiment or a claim of identical timing across independently captured runs.
There were 719 nonzero legacy rotation-command frames and 158 nonzero scale
frames. A real preview and rotated/scaled-looking scene were observed in run 2;
subjective unchanged usability was not separately rated.

All tracking-unusable frames and all temporal reset snapshots were unarmed,
action-blocked and unlatched. Loss/reacquisition safety passed on the recorded
samples. Both processes exited with code 0 and `Live demo closed cleanly`.
MediaPipe feedback-tensor and NORM_RECT projection warnings remain present.
The GPU overlay obscured some header text; no UI/system setting was changed.

## Smallest next correction — recommendation only

Review separating **release/rearm evidence** from a successful full-pose label.
The definite-release samples in run 2 frames 229–244 currently cannot rearm
because no OPEN/POINT/FIST predicate matches. A narrow follow-up could accept
continuous valid, known-finger `distance > exit` evidence specifically for
UNKNOWN/`NO_POSE_MATCH`, while neutralizing stable action, canceling pending
pose dwell and forbidding every UNKNOWN-frame action. Keep band, conflicting
features, invalid geometry, loss/reset and reacquisition excluded; require a
fresh definite PINCH enter dwell. Specify/test that safety separation before
any implementation. Do not lower pinch thresholds or temporal dwell.

No further thumb threshold change is justified by these dim, unlabeled runs.
Before changing FIST again, capture a labeled, adequately lit comfortable FIST
hold and compare the existing opposition/axis predicates and pinch-band overlap.
This follow-up is a validation requirement, not a tuning recommendation.

## Integrity and task boundary

Only this supplemental report was added. Core, InteractionState, legacy gains,
scene/router/UI architecture, config/profile, G7 evidence and experiments are
unchanged. Core/frozen paths still match `g7-final` at
`f454c6b8325c85199c0122c0e822fe8e76c1526c`; G9 files remain absent and stash
`d709da693e6adc4dec94e6925e7cd202ae0dd507` is retained. No thresholds were tuned,
no full-hand commands enabled and no correction implemented.

No stage, commit, push or tag performed. Automated feature tests were not rerun
for this observation-only task; parity above was actually executed on new logs.
