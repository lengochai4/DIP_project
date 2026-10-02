# v1.1 P1c physical PINCH validation — 2026-10-02

**Final status: P1c PARTIAL.** Stable PINCH, release and stable re-entry occurred
physically, but only two stable PINCH entries were recorded. Five confirmed
successful cycles were not achieved. Repeated operator attempts often stayed
inside the hysteresis band. Do not promote this result to A6 readiness.

No code, configuration, thresholds or FIST logic changed. Full-hand commands
remained disabled; the original legacy GestureEngine drove the application.

## Run identity and evidence

All runs executed the existing observation-only entry point:

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND
```

Actual launcher: `.venv\Scripts\python.exe -u`; branch `feat/v1.1-full-hand`;
revision `70b8f5a257db091c41eaf6cfa83b550d9a84c14b`, clean at launch.
Actual source geometry: 640 × 480. Each manifest records:

- Observer profile: `config/extensions/full_hand_observe.yaml`.
- Profile SHA-256: `a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
- Legacy config hash: `ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.

Real webcam logs are local ignored development artifacts in `runs/<run-id>/`
and `runs/full-hand-observe/<run-id>/`. The latter contains the manifest and
per-frame snapshots. Analysis outputs are in `runs/p1c-observation/`, including
`final_summary.json`. Original physical logs were not edited; no synthetic
physical evidence, webcam image archive or frozen G7 evidence was created.

## Attempts, transitions and coverage

| Run ID suffix (`g8-demo-20261002-…`) | Frames / duration | Operator attempts | Armed transitions | Stable PINCH enters | Strict release, ready again | Stable re-entries |
|---|---|---|---:|---:|---:|---:|
| `082250` | 402 / 13.918 s | Startup/exploratory; count unknown | 2 | 0 | 0 | 0 |
| `082444` | 437 / 14.574 s | 2–3, normal light; operator reported all OK | 2 | 2 | 2 | 1 |
| `082622` | 506 / 17.420 s | 5, operator confirmed retrospectively | 1 | 0 | 0 | 0 |
| `083033` | 488 / 16.224 s | 5–6, normal light; operator confirmed supplemental conditions too | 1 | 0 | 0 | 0 |

`082622` was previously unfinished from the agent's perspective after Computer
Use was stopped. On continuation, its complete sidecar and 506 matching legacy
frame rows were analyzed, and its process reported exit code 0 and clean shutdown.
It is valid evidence of **missed stable recognition**, not a successful-cycle run.

The operator confirmed moderate wrist rotation, near/medium/far, moderate side
angle, darker light, and brief hand-out/in were all tried in the final mixed
run. There are no synchronized condition markers or measured angles/distances/
illumination, so individual condition-specific success cannot be established.
Exact requested hold lengths were not verified; logs were shorter than the
initial suggested 2–3 second-per-phase sequence would take for every condition.

Missed stable attempts: five in `082622` and five–six in `083033`, because there
were zero stable entries in those operator-confirmed attempts. The earlier
2–3-attempt answer is approximate; with two logged stable entries, zero–one
additional missed attempt cannot be resolved from that answer. No accuracy or
success-rate benchmark is claimed. There are at least ten missed stable attempts
in the two later runs, so the repeated-cycle acceptance gate is not met.

## Successful physical lifecycle

In `082444`:

- Frame 117, 4.233696 s: semantic UNKNOWN has strict release geometry and
  `REARMED`. This directly exercises A5.2's geometry-driven rearm.
- Frame 282, 9.722638 s: stable PINCH enter, normalized distance 0.189859.
- Frame 288, 9.916786 s: strict release distance 1.222513, safe semantic release,
  no PINCH latch, and armed remains true.
- Frame 333, 11.429528 s: stable PINCH again, distance 0.155609.
- Frame 417, 14.254267 s: strict release distance 1.195634, latch cleared,
  armed retained.

There are 90 stable PINCH snapshots, including diagnostic memory on band
frames, and 63 currently eligible PINCH snapshots. The longest stable-memory
span is frames 333–416, 2.794298 s. Eligibility is a diagnostic permission flag,
not an enabled full-hand application command.

"Ready again" counts above mean strict released geometry cleared the stable
PINCH and left the clutch armed. A5.2 does not forcibly disarm after each valid
release, so these are not fabricated new false→true `REARMED` events. Total
false→true armed transitions are six, including startup and reacquisition.

## Why repeated recognition still misses

| Run suffix | Candidate PINCH | Pure band frames / sampled duration | Candidate UNKNOWN on VALID frames |
|---|---:|---|---:|
| `082250` | 1 | 60 / 1.990356 s | 117 |
| `082444` | 91 | 62 / 2.082496 s | 212 |
| `082622` | 6 | 263 / 8.849961 s | 294 |
| `083033` | 3 | 327 / 10.889870 s | 381 |

Band duration uses each band's interval to the next timestamp, with no invented
tail duration. In `083033`, tracking was VALID on 486/488 frames; arm was earned
at frame 8 and remained available. Definite enter evidence was only three frames.
The minimum recorded normalized distance was 0.191195, only just below enter
0.2. Most candidate crossings therefore could not satisfy the 0.25 s dwell.

Recomputing palm-normalized, aspect-corrected distances from raw and filtered
CSV landmarks gave identical ranges/counts in each run. The available recordings
thus do not show a filtered-only distance discrepancy causing these misses.
Neither threshold optimality nor intended fingertip contact at every frame can
be inferred without synchronized labels.

## Safety, parity and shutdown

- No UNKNOWN snapshot authorized action; 1004 UNKNOWN candidates occurred on
  VALID tracking frames across the four runs. NO_HAND snapshots were also safe.
- No valid pure-band frame incorrectly disarmed an earned clutch.
- No stuck stable PINCH observed; every recorded stable PINCH ended with strict
  release and no latch. The final snapshots were action-blocked and unlatched.
- No failure to rearm after a continuous valid strict-release span of the
  configured 0.125 s was found. Band-waiting is not counted as stuck rearm.
- Tracking loss→usable return pairs: 2 / 2 / 1 / 1. All unusable tracking and
  reset snapshots were unarmed, action-blocked and unlatched. Intentional hand
  withdrawal is not separated from unintended loss in those counts.
- Same-sample legacy GestureEngine replay matched every InteractionState field
  on **1833/1833 frames**, zero mismatches. This is local development comparison
  using physical filtered samples, not a Core research experiment or a claim of
  unchanged wall-clock performance.
- All four processes exited with code 0 and `Live demo closed cleanly`.
  No observer diagnostic errors were recorded. Existing MediaPipe feedback and
  projection warnings were retained.

## Smallest next action

Keep A6 opt-in command work deferred. Perform one synchronized, labeled
held-pinch measurement at medium distance/front-facing hand under normal light,
recording intended contact intervals, landmark 4/8 positions and palm-width
normalization alongside the current candidate/dwell. Inspect why intended
contact remains in the band before deciding whether there is a geometry defect
or a separately authorized calibration need. Do not blindly lower thresholds,
weaken dwell or change the now-working geometry rearm state machine.

This task adds only this development report. Core/G7, legacy sensitivity,
InteractionState, scenes/router/UI, profile and FIST are unchanged. Frozen Core
and report/evidence/final-experiment paths still match `g7-final`, peeled revision
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. G9 remains stashed and absent from
the source tree. No stage, commit, push, tag or next-phase implementation occurred.
Feature tests were not rerun for this observation-only task; parity and new-log
analysis above were executed. Documentation whitespace checks passed.
