# v1.1 A5.4 — recorded multi-feature PINCH investigation

Evaluation complete; **INSUFFICIENT EVIDENCE to select a robust predicate**.
No new pose predicate, threshold, profile, temporal transition or runtime
integration is installed. The default remains 0.20/0.35; 0.33/0.35 remains the
rejected experimental observation profile. Full-hand commands remain disabled.

The geometry contains potentially useful configuration information, particularly
index bending. It does not currently justify a contact-versus-near-touch rule
that generalizes across the recorded configurations. This is an evidence limit,
not a proof that every possible joint 2D classifier is impossible. Physical
skin-contact detection is not a proposed interaction requirement.

## Sources and label discipline

Numerical regression fixtures copy observed filtered landmarks, actual frame
geometry, source SHA-256, frame/time/marker identity and run/profile provenance.
They contain no webcam images. Model-relative z is retained in the input record
but never contributes to any evaluated feature. These are local Extension
diagnostic regressions, not G7 research or submission evidence.

| Source run | Samples retained | Label basis |
| --- | ---: | --- |
| `g8-demo-20261002-092337` | 15 | P1d: five marked contact intervals, no synchronized images |
| `g8-demo-20261002-092639` | 12 | P1d: four marked contact intervals, no synchronized images |
| `g8-demo-20261002-093848` | 16 | P1e: four contact and four release events, marker/held images |
| `g8-demo-20261002-095422` | 12 | A5.3: three contact and three release events, marker/held images |
| `g8-demo-20261002-095623` | 10 | Three medium events and two supplemental near labels |
| `g8-demo-20261002-100358` | 8 | Two clean confirmed near events and two release events |

Total: **73 samples**: 42 synchronized confirmed samples, four supplemental near
samples, and 27 P1d interval samples. Each P1d interval contributes the first valid
frame at/after 0.5 s, at/after 1.0 s, and the frame with maximum index straightness
in [0.5, 1.5) s after its T marker, stopping at U. The last selection explicitly
tests a difficult configuration; it is not unbiased frequency sampling.

P1d operator-confirmed intervals still include possible motion and marker lag;
their frames are not individually visually verified contacts. Keep this weaker
label basis separate. Run 092032 has repeated/unfinished marks and is not used
as clean regression ground truth. The first V event of run 095623 was reported
contaminated by accidental contact/mislabeling: both samples are excluded. Its
remaining two V labels are supplemental, separate from the newly confirmed
clean negative trials in 100358.

The fixture's `runs` map records these historical execution revisions and profile
hashes, including the manifest SHA-256. Revision identities do not imply a clean
working tree during diagnostic runs; see the original task reports. Original
sidecars/images remain unchanged under ignored `runs/`.

## Features evaluated

`extract_pinch_features` is an offline, read-only helper with no application hook.
It reuses A2 extraction and reports 35 immutable feature diagnostics:

- Thumb-index distance and MCP 5–17 palm-width denominator.
- Thumb axis relative to the anatomical distal palm axis; distances from thumb
  tip to index/pinky MCP, preserving the existing opposition definition.
- Joint angles, straightness and tip coordinates in the anatomical palm frame
  for all five fingers.
- Cosine between directed distal segments 3→4 and 7→8; cosine of each segment
  toward the opposite fingertip; palm-axis projections of the 4→8 gap.

Directions use x multiplied by actual width/height and unchanged y. Angles,
cosines and palm-normalized features are invariant under translation, positive
uniform scaling, in-plane rotation and mirrored anatomical fixtures. Palm width
itself scales with image-space size. No handedness score or metric z is used.
Invalid A2 geometry produces explicit reasons and no plausible feature values.
Coincident tips explicitly lack a gap direction; they do not produce a fake cosine.

## Recorded contact versus clean near-touch

Primary comparison uses 14 contact samples from seven events and four clean
near samples from two events. Marker and held samples are correlated views of
the same attempt, not independent trials or a population accuracy estimate.

| Feature | Confirmed contact range | Clean near-touch range |
| --- | --- | --- |
| Distance / palm width | 0.27074–0.32976 | 0.23396–0.31777 |
| Index straightness | 0.67697–0.84524 | 0.86175–0.87209 |
| Thumb axis / palm, rad | 0.56951–0.81585 | 0.81282–0.83057 |
| Thumb tip → index MCP / palm | 0.34830–0.91099 | 0.74882–0.79283 |
| Distal segment cosine | −0.51187–0.40024 | 0.32679–0.47429 |
| Index toward thumb cosine | 0.31514–0.87372 | 0.16812–0.37827 |
| Tip gap along distal palm axis | 0.25730–0.31098 | 0.23242–0.31506 |

Opposition, distal directions and palm-frame positions overlap. The index state
is INTERMEDIATE for all 14 contacts and all four clean near samples; the other
three fingers are FLEXED in both groups. Thumb is INTERMEDIATE in ten contacts
and EXTENDED in four contacts; all four clean near samples have EXTENDED thumb.
Requiring INTERMEDIATE thumb would reject four confirmed contact samples. The
existing `thumb_opposed <= 0.5` predicate accepts only five of the 14 contacts,
including none from the A5.3 positive run. Neither is selected as a PINCH gate.

The strongest apparent extra discriminator is index straightness. The offline
hypothesis `distance < 0.33 AND index straightness < 0.85` accepts all 14 primary
contact samples and rejects all four clean near samples. The gap between their
straightness ranges is only **0.01651** and has no independent validation.

P1d exposes overlapping contact-labeled configurations, even with distance well
below 0.33:

| Run / frame | Distance | Index straightness |
| --- | ---: | ---: |
| `092337 / 278` | 0.22142 | 0.86274 |
| `092337 / 501` | 0.22801 | 0.86953 |

Thus the bend hypothesis drops two additional P1d contact-labeled samples: the
distance candidate accepts 24/27, while adding bend accepts 22/27. The remaining
three are already outside the distance candidate. These weaker labels cannot
prove a physical false negative, but they also cannot be dismissed to justify
installing the rule. A narrow fitted boundary or conjunction of several overlapping
features could memorize the small dataset without explaining intentional PINCH.
No such classifier is invented here. The numeric 0.85 is a rejected offline
hypothesis in regression analysis, never a configurable runtime threshold.

Inspection of the existing source images for 095422/frame 683 and
100358/frames 370 and 680 confirms very similar curled finger arrangements.
Near images show a visible gap, while contact is operator-confirmed. Wrists/palm
are partly outside the left image edge. Changes of bend, orientation and visible
surface contact are not independently controlled. Geometric similarity and
landmark-to-skin offset remain plausible limitations; scalar overlap is not
attributed to a new dwell or rearm defect.

## Scalar comparison and confusion

Counts below are single-frame PINCH candidates, not stable transitions.

| Confirmed synchronized class | Samples | Baseline 0.20 enters | Rejected 0.33 enters | Offline distance+bend hypothesis |
| --- | ---: | ---: | ---: | ---: |
| Contact | 14 | 0 | 14 | 14 |
| Clean near, no touch | 4 | 0 | 4 false | 0 |
| Medium separation | 6 | 0 | 0 | 0 |
| Clear release | 18 | 0 | 0 | 0 |

On this primary static set, baseline has 14 missed contacts and no accepted
negatives. The rejected candidate admits all contacts and all four clean near
samples. Medium/release negatives are rejected by both. Four supplemental old
near samples are rejected by both (distance 0.41560–0.55420); they do not dilute
the clean false-positive result. The bend hypothesis's apparent perfect primary
confusion is a retrospective fit, not an accepted predicate or validation PASS.

The actual A5.3 physical outcome remains two of three contact attempts with
sampled stable PINCH and two of two clean near attempts falsely stable. Sparse
fixtures cannot establish dwell/re-entry success or replace the full timestamped
physical record. No new physical run or command gate is claimed by A5.4.

## Smallest next physical action

Ready for **another observation-only data collection gate**, not A6 commands or
acceptance of a new predicate. Use existing opt-in capture and baseline:

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --pinch-diagnostic --pinch-visual --pinch-calibration-markers
```

Collect paired T contact / V near-no-touch / B medium / U release with a fully
centered hand, matched wrist orientation and distance. Include near-touch with
both bent and relatively straight index, contact with both configurations, and
similar thumb opposition. Maintain a visible gap throughout V. Keep marked holds
long enough to inspect jitter and transitions, and split development/validation
by whole attempts and sessions. Do not tune during capture. First resolve whether
the apparent index separator follows intent or merely the operator's chosen pose.
Any later predicate must explicitly abstain on ambiguous/invalid geometry and
pass unchanged temporal UNKNOWN, loss/reacquisition and legacy-parity gates.

## Changes, tests and integrity

New files only for A5.4:

- `extensions/stem3d/full_hand/pinch_feature_analysis.py` — pure offline features.
- `tests/extensions/full_hand/fixtures/pinch_feature_recordings.json` — 73 numeric
  observed fixtures with source identities, excluded-label record and no images.
- `tests/extensions/full_hand/test_pinch_feature_analysis.py` — 93 tests including
  source-distance reproduction, recorded confusion, the rejected bend hypothesis,
  immutable inputs/outputs, invalid geometry, absent directions, aspect correction,
  mirror/rotation/translation/scale invariance, z independence and exact pose/temporal
  replay equivalence with/without analysis for both profiles.
- This evaluation report.

Executed: focused full-hand suite **489 passed**; full suite **1044 passed**;
`python -m compileall extensions/stem3d` and `git diff --check` passed.
The earlier A5.3 modifications remain pending and untouched by
A5.4. Local exploratory scripts/reports remain in ignored `runs/`.

Classifier/FIST, temporal hysteresis/rearm, default profile, legacy interaction,
InteractionState, scenes/router/UI and sensitivity are unchanged. Existing
observation/legacy parity tests pass; no new physical parity measurement is
claimed. Core/frozen report/evidence/experiments match `g7-final`, peeled commit
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. All five G9 source paths remain absent,
and its stash is retained. No staging, commit, push, tag or subsequent phase.
