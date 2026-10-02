# v1.1 P1e: synchronized physical PINCH correlation

Completed local diagnostic collection and inspection on 2026-10-02.
This is development observation, not G7 research/submission evidence or an A6
command-readiness gate. No thresholds or interaction behavior were changed.

## Opt-in capture and identity

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --pinch-diagnostic --pinch-visual
```

`--pinch-visual` requires the existing diagnostic flag and observation mode.
Without it, no images are stored. With it, explicit T/PINCH_TOUCH and
U/PINCH_RELEASE edges save the synchronized full-frame presentation image,
a separate landmark overlay, and JSON metadata. One additional held-state
sample is saved on the first frame at least 0.5 seconds after the marker;
a new T/U/conflicting physical marker cancels the pending held sample.
The run is capped at 24 samples. N remains a note marker, without image capture.

Images are unmirrored 640x480 webcam frames, not generated or reconstructed.
The source PNG is unannotated; its overlay is separate. Raw landmark dots and
filtered landmark rings identify 4 (magenta), 8 (yellow), and palm references
0/5/9/13/17 (green). The line 5--17 shows the normalization denominator.
PNG encoding receives explicitly converted BGR pixels. JSON includes all raw
and filtered normalized landmarks, numerator, denominator, zone, pose/temporal
state, actual frame geometry, marker identity/frame/time, poll perf-counter,
sample offset and processing time. z is recorded but not used as metric depth.

The marker timestamp belongs to the current processed source frame. Key state
is polled after processing; the recorded poll clock is not a physical contact
time or OS key-down timestamp. Frame identity/geometry are checked before any
image save. Images are saved before the legacy presentation callback, from its
read-only image copy. Neither images nor landmarks are mutated in place.

Run: **g8-demo-20261002-093848**.
Revision: `c369f1235d381e1f7c29a87cf339e438c45dac32`, plus uncommitted diagnostic
changes. `pinch_diagnostic_manifest.json` records hashes of the actual diagnostic
and composition files. Profile SHA256 remains
`a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`;
legacy config SHA256 remains
`ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.
The profile is RAW. The observation manifest honestly declares
`webcam_images_stored: true` for this opt-in run.

Local paths:

- `runs/full-hand-observe/g8-demo-20261002-093848/pinch_visual/`
- `physical_markers.jsonl`, `pinch_geometry.jsonl`, `snapshots.jsonl` in that run.
- Local analysis: `pinch_visual_analysis.json`, `pinch_analysis.json`.

These ignored local artifacts are outside `submission/evidence/` and
`experiments/final/`. Historical P1d recordings remain unchanged.

## Synchronized examples inspected

The operator was instructed to establish contact/release for approximately one
second before marking, then hold for two more seconds under normal lighting.
The operator confirmed the four T events represented actual contact. They did
not specifically identify pad/side contact versus opposing fingertip peaks;
the geometric interpretation below is visual inference, not a reported fact.

Eight markers form **4 complete T-to-U attempts**, with **16 synchronized
samples: 16 source PNGs + 16 overlay PNGs + 16 JSON files**. All 32 images were
inspected. The held samples were 0.5113-0.5423 seconds after their marker frames.

| Cycle | TOUCH marker / held frame | Distance marker / held | RELEASE marker / held frame | Distance marker / held |
| --- | --- | --- | --- | --- |
| 1 | 199 / 215 | 0.30425 / 0.31250 | 405 / 420 | 1.17213 / 1.20005 |
| 2 | 537 / 553 | 0.31222 / 0.30650 | 649 / 664 | 1.60527 / 1.62474 |
| 3 | 767 / 782 | 0.27084 / 0.27074 | 859 / 874 | 1.54944 / 1.51247 |
| 4 | 954 / 970 | 0.28314 / 0.30003 | 1038 / 1054 | 1.53702 / 1.54961 |

| Visually inspected state | Samples | Min | Median | Max | Zone |
| --- | ---: | ---: | ---: | ---: | --- |
| Contact | 8 | 0.27074 | 0.30214 | 0.31250 | BAND on all 8 |
| Clearly released | 8 | 1.17213 | 1.54323 | 1.62474 | RELEASE on all 8 |

These are eight correlated samples of four attempts from one person in one
orientation/framing condition, not an accuracy estimate or general calibration
dataset. At all eight contact samples, the tracker was armed but candidate and
stable poses were UNKNOWN. None could enter with the unchanged `< 0.20` rule.
All eight release samples were candidate/stable POINT. No stable PINCH occurred
in the run. This is a recorded miss, not hidden by the visually clear separation.

## Root-cause categories

| Category | Observation and interpretation |
| --- | --- |
| Landmark 4/8 placement | Points remain associated with the thumb and index rather than switching to unrelated fingers. They mark different distal-finger locations, separated by 26.63-31.71 image pixels during contact. The thumb point appears set back from the shared contact boundary, while index 8 lies above it. This supports contact-surface versus reported-tip-location mismatch/localization offset; no manually annotated anatomical ground truth quantifies a provider error. |
| Contact/occlusion ambiguity | The source frames show the two distal surfaces brought together, corroborated by the operator. The meeting surface is partly hidden by the curled fingers. Touching skin surfaces does not imply coincident reported landmark points. The exact contact interface cannot be measured from this single RGB view. |
| Orientation/perspective | Contact is observed in a curled/oblique hand pose, with the hand near the left image border and some palm context cropped. Perspective/occlusion can affect localization. No front-facing, fully centered comparison was collected, so orientation is a plausible contributor rather than an isolated causal result. |
| Palm normalization | Contact denominator is 0.19574-0.22132 image-height units (median 0.20237); release is 0.19470-0.22345 (median 0.21683). The ranges overlap, there is no collapse, and numerator/denominator both use actual 640/480 aspect correction. No normalization-unit defect was found. Changing the denominator merely to fit contact would change its meaning without supporting evidence. |
| Marker timing | Every marker image agrees visually with its label, and its held image remains in the same physical state. Contact stays BAND after more than 0.5 seconds. Marker timing cannot explain the persistent offset in these 16 samples, although human timing uncertainty remains elsewhere in the full intervals. |
| Ordinary jitter | Maximum marker-to-held contact distance change is 0.01689. This is an observed paired change, not a statistical noise bound. All sampled contacts remain well above 0.20 despite it; jitter contributes variation but does not explain away the systematic separation. RAW/filtered measurements match throughout. |
| Temporal dwell/rearm | All sampled contacts are armed and BAND. The candidate cannot begin pinch dwell; extending hold time cannot turn BAND into ENTER. No dwell/rearm defect is demonstrated. |

Immediate cause: this user's visually confirmed contact style produces reported
tip geometry around 0.27-0.31 palm widths, above the development enter threshold.
The strongest supported explanation is mismatch between actual skin contact
and the two reported 2D fingertip locations, with curled pose/occlusion and
localization bias as contributors. Their separate contributions are not resolved
by these images. This is not evidence of a Core/filter normalization bug.

## Separability and smallest proposed correction

**YES, contact and clearly separated release are visually and numerically
separable in this small synchronized set.** The minimum release distance
1.17213 exceeds the maximum contact distance 0.31250. This improves on P1d's
unverified marker intervals, whose broad distributions overlapped. It does not
retroactively relabel those intervals or prove separation of near-contact
non-touching poses, which were not collected here.

The evidence supports a **small, separately authorized Extension-profile
calibration trial**, not a universal/default threshold change:

- Proposed ENTER: **0.20 -> 0.33** (not implemented).
- EXIT: **0.35 -> 0.35**.
- Pinch enter dwell: **0.25 s -> 0.25 s**; release/rearm timings unchanged.
- Aspect correction and palm normalization: unchanged.

0.33 clears the observed contact maximum plus the largest observed
marker-to-held contact change: 0.31250 + 0.01689 = approximately 0.32940.
This is a starting value justified by these observations, not an estimated
worst-case jitter bound. It would narrow the hysteresis band from 0.15 to 0.02
palm widths; false enters and boundary churn require explicit validation.
Near-touching but non-contact poses, fully centered/front-facing hands,
rotation and distance changes must be included before accepting it. Merely
clearing these 8 correlated positive samples is insufficient to approve a
general profile or enable commands. Do not change EXIT, weaken dwell, move
landmarks, replace palm normalization, or modify the provider to force a pass.

## Tests, parity and integrity

- Focused diagnostic/visual tests: **20 passed**, including **9 new visual
  cases**. Full-hand regression: **375 passed**. Full suite: **930 passed**.
- Tests verify default no-image storage, explicit visual opt-in, source RGB/BGR
  conversion, identity/dimension checks, raw/filtered metadata, input immutability,
  marker/held synchronization, cancellation, duplicate suppression, sample cap,
  callback preservation on write failure and field-for-field legacy parity.
- `python -m compileall extensions/stem3d` and `git diff --check` passed.
- Physical recording: 1111 frames, 1067 VALID and 44 NO_HAND (startup included).
  Same-sample legacy replay matches **1111/1111 InteractionState records**.
  RAW/filtered measurements match on 1111/1111 frames. No UNKNOWN-authorized
  full-hand action, unsafe loss state or observer errors; full-hand commands
  remain disabled. Additional file I/O is not claimed to preserve wall-clock
  performance. Process exited 0 and closed cleanly.
- Two existing lifecycle test mocks were updated to forward the new optional
  journal metadata keyword. No existing test assertions were removed.
- Core, G7 report/evidence/final experiments remain identical to `g7-final`
  (`f454c6b8325c85199c0122c0e822fe8e76c1526c`). FIST/classifier/temporal thresholds,
  legacy sensitivity, InteractionState, scenes/router/UI are unchanged.
  G9 remains stashed and absent.

Changed files: `full_hand/pinch_visual.py`, `full_hand/pinch_diagnostic.py`,
`full_hand/observe.py` (image-storage metadata only), `full_hand_app.py`,
`tests/extensions/full_hand/test_pinch_visual.py`,
`tests/extensions/full_hand/test_observe.py` (mock forwarding), and this report.
The visual diagnostic remains opt-in/local. No correction was implemented;
no stage, commit, push, tag or next-phase command implementation occurred.
