# v1.1 P1d: physical PINCH geometry diagnostic

Development observation only; this is not frozen G7 research evidence.
Full-hand commands remain disabled. No profile, classifier, temporal, FIST,
legacy sensitivity, Core, InteractionState, scene/router or UI behavior changes.

## Reproduction and physical labels

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --pinch-diagnostic
```

Start the existing application with Enter. Keep one observed hand in the camera
at medium distance, normal light, approximately facing the camera. Use the other
hand outside the camera to press keys with the application focused:

- U: PINCH_RELEASE, after clearly separating thumb and index.
- T: PINCH_TOUCH, after deliberate fingertip contact.
- N: optional NOTE marker; associate its marker ID with an operator note.

Hold each key briefly (approximately 0.3 seconds), then release the key. Hold
each physical state for approximately 3 seconds. Repeat 10 cycles and finish
with U, then Q. These are operator labels, not classifier-generated ground truth.
Their frame alignment includes human timing uncertainty. Consecutive T labels
without an intervening U are one interval, not multiple completed attempts.

Without `--pinch-diagnostic`, the existing observation path is unchanged. The
flag is rejected in LEGACY mode. It adds no keyboard actions to the UI: it reads
pressed-key edges without consuming the existing event queue.

## Separate local artifacts

`runs/full-hand-observe/<run-id>/` contains:

- `manifest.json` and `snapshots.jsonl`: existing profile and pose/temporal data.
- `pinch_diagnostic_manifest.json`: thresholds, units, key meanings and hashes
  of the uncommitted diagnostic composition/source.
- `pinch_geometry.jsonl`: per-frame identity, actual frame dimensions, raw and
  filtered landmark 4/8 coordinates, image-height numerator, MCP5--MCP17 palm
  width denominator, palm-normalized distance, zone, candidate and temporal state.
- `physical_markers.jsonl`: operator marker ID, event and current frame timestamp.

Local analysis may produce `pinch_analysis.json`; recordings stay under ignored
`runs/`, outside submission/evidence and experiments/final. No webcam images are
stored. Coordinates use full-frame normalized x/y; z is recorded but never used
as metric depth. Both numerator and denominator correct x by actual width/height.
Unavailable geometry stays null with a reason. ENTER is strictly distance < 0.20,
RELEASE is strictly distance > 0.35; inclusive endpoints belong to BAND.

## Physical result: P1d PARTIAL

Collection and diagnostic checks completed. A threshold/normalization correction
is not yet justified: the contact and release labels overlap substantially.
This does not pass the earlier repeated-PINCH reliability gate or authorize A6.

All runs used webcam input, actual 640x480 source geometry, RAW filtering,
OBSERVE_FULL_HAND, and revision `9793354226116eb91170723bbb98060c38de78a0`
plus the uncommitted diagnostic additions described above. The manifest records
the diagnostic source hashes; this is not a claim that HEAD alone reproduces
the diagnostic entry point. Profile SHA256 was unchanged:
`a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
Legacy config SHA256:
`ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.

| Run ID | Frames | Markers | Complete T-to-U intervals | Stable PINCH enter / release frames |
| --- | ---: | ---: | ---: | --- |
| g8-demo-20261002-092032 | 1425 | 22 | 7 | none |
| g8-demo-20261002-092337 | 1178 | 12 | 5 | 226 / 323 |
| g8-demo-20261002-092639 | 844 | 10 | 4 | 379 / 406 |

The operator confirmed actual contact/release for the first run, confirmed
normal light/one observed hand for the latter two runs, and confirmed all four
final-run cycles without observed sticking. The first run had repeated identical
labels and a final unpaired T, so it is supplemental. The second run also had
one final unpaired T. Neither unpaired interval is counted as a completed attempt.
The two later runs provide **9 confirmed complete marked attempts**. Their
contact intervals lasted 1.759-6.481 seconds; not every hold met the requested
3 seconds, but each exceeded the configured 0.25-second pinch dwell.

Two of these nine intervals contained actionable stable PINCH; seven did not.
Only one stable enter transition occurred strictly after T within a completed
interval: frame 379 in the final run. The other enter occurred before T at frame
226 in the second run, demonstrating label timing uncertainty. Both stable states
released, at frames 323 and 406. No stable PINCH or rearm state remained stuck
in the recordings. Each run armed once (frames 130, 90, 69 respectively), and
earned arming persisted through valid band input. This is not a rearm failure.

## Distance statistics and normalization

Primary contact statistics use only the nine completed T-to-U intervals on
valid, analysis-valid frames. Release statistics use the U-labeled valid frames
from the same two runs. Frames are correlated samples, not independent trials;
labels describe operator intent and have not been verified against stored video.
No classifier-zone selection was used to clean the distributions.

| Operator label | Valid samples | Min | P05 | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TOUCH, completed intervals | 799 | 0.16909 | 0.19212 | 0.26924 | 1.56232 | 1.81223 |
| RELEASE | 902 | 0.14577 | 0.19611 | 1.24651 | 1.77804 | 2.01352 |

All distances in this table are palm-width normalized. Of the 799 contact
samples, 102 were ENTER, 397 BAND and 300 RELEASE. Release-labeled samples
included 61 ENTER, 184 BAND and 657 RELEASE. Excluding the first 0.25 seconds
after each T still leaves contact P05/median/P95 = 0.19205/0.27433/1.55980
(726 samples). The overlap therefore cannot be dismissed as just one-frame
marker lag or solved honestly by selecting only low-distance contact frames.

Contact image-height numerator median/P05/P95 = 0.06035/0.04414/0.40367;
denominator median/P05/P95 = 0.22814/0.21238/0.26054, range 0.19435-0.27173.
Release denominator median/P05/P95 = 0.23363/0.21153/0.26453, range
0.19157-0.27683. Contact denominator mean/std = 0.23151/0.01529
(approximately 6.60% relative variation). There is no collapse towards zero
on these completed intervals. Pose and distance variation can affect apparent
palm width, but no aspect/unit mismatch was found: numerator and denominator
both use actual width/height, and the recorded ratio agrees with A2 geometry.
Raw and filtered measurements are exactly equal on **3447/3447 frames** with
this RAW profile. There is no filtered-only offset in this recording.

## Why contact does not enter reliably

Observed mechanism: reported 2D landmark geometry often remains above the
strict enter boundary, including continuous operator-labeled contact spans.
For example:

- 092337, marker 8, frames 800-855: 56 consecutive BAND frames, 1.824 seconds,
  distance 0.23162-0.27907 (median 0.24886); denominator 0.21091-0.22561.
- 092639, marker 7, frames 615-659: 45 consecutive BAND frames, 1.457 seconds,
  distance 0.23813-0.29981 (median 0.27240); denominator 0.21145-0.22999.
- 092639, marker 9, frames 737-781: 45 consecutive BAND frames, 1.448 seconds,
  distance 0.27332-0.31747 (median 0.29986); denominator 0.21578-0.22980.

These spans remained armed throughout. Waiting longer cannot turn BAND into
ENTER. Other unsuccessful attempts crossed below 0.20 only briefly: longest
continuous armed PINCH-candidate spans in the second run's failed contact
intervals were 0.0933, 0.0332, 0 and 0 seconds. Dwell correctly rejects those
interruptions; geometry variation around the boundary explains the interruption,
without evidence of a dwell implementation defect. A successful final-run
interval had a continuous entering-candidate span of 0.4337 seconds.

Tracking stayed valid throughout the completed contact intervals. NO_HAND totals
were 102/84/64 across the runs and include startup/withdrawal, not a measured
unintended-drop rate. There were no observer errors, no UNKNOWN-authorized
actions, and no armed/action/latch state on unusable tracking frames. Full-hand
`action_allowed` is a diagnostic permission flag, not an emitted application
command. Actual commands remained legacy-only.

This identifies the immediate failure as **reported contact geometry versus the
enter boundary**, with boundary jitter affecting dwell. It does not establish
whether nonzero fingertip separation is provider localization/occlusion bias,
anatomical contact versus landmark-tip placement, or imperfect physical-label
alignment. No camera images were stored to adjudicate those alternatives.
The marked distributions contain both near-contact and clearly separated-looking
landmark geometry under both labels; do not hide that discrepancy.

## Separability and smallest next action

Current thresholds do not reliably detect these intended contact intervals.
Physical separability sufficient for a replacement threshold is **NOT
DEMONSTRATED**: even contact P95 exceeds release P05. A proposed enter increase
from 0.20 to 0.30 would also accept release-labeled samples; the current recordings
do not justify claiming it safe. No normalization formula correction is supported.

Recommendation: keep enter **0.20 -> 0.20**, exit **0.35 -> 0.35**, and dwell
unchanged. The smallest next diagnostic is frame-verifiable held-contact and
clearly separated intervals with synchronized physical labels, to resolve
provider localization versus marker/hand-identification ambiguity before a
separately authorized calibration change. Do not reduce dwell, weaken rearm,
or select a threshold from only the already-classified BAND samples.

## Checks and integrity

- Diagnostic focused tests: 11 passed; all full-hand tests: 366 passed.
- Full suite: 921 passed. `python -m compileall extensions/stem3d` passed.
- `git diff --check` passed (existing Windows LF/CRLF notices only).
- Same-sample legacy replay matched every InteractionState field on
  **3447/3447 physical frames**, zero mismatches. This checks output parity,
  not wall-clock performance under additional file I/O.
- All three runs exited code 0 and reported clean shutdown. Existing MediaPipe
  feedback/projection warnings were retained. No webcam images or G7 evidence
  were generated or modified.
- Core/frozen report/evidence/final experiments still match `g7-final`, peeled
  commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`. Profile, FIST, temporal,
  legacy interaction/sensitivity, scenes/router/UI are unchanged. G9 remains
  stashed and absent from source.
- Changed files: `full_hand_app.py`, new `full_hand/pinch_diagnostic.py`, new
  `tests/extensions/full_hand/test_pinch_diagnostic.py`, and this report.
  Ignored local run sidecars/analysis are separate from release/evidence files.

The diagnostic flag remains opt-in and observation-only. No stage, commit,
push, tag, threshold change or next-phase implementation was performed.
