# v1.1 P1f — matched CONTACT versus NEAR_TOUCH collection

**P1f PARTIAL. Separability: WEAKLY SEPARABLE; no predicate is justified.**
The user explicitly stopped further testing. Collection stops here, below the
requested ten verified valid pairs. No further physical test or classifier work
is authorized by this record. This label means some paired features change,
but not consistently enough to support a deterministic rule; it does not claim
contact can be recognized reliably from 2D landmarks.

## Execution and scope

All runs used the existing application, unchanged default observation profile:

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --pinch-diagnostic --pinch-visual --pinch-calibration-markers
```

- Revision: `59333d925071ff0bb5ff3445282ac1d12bc47e09`.
- Profile SHA-256: `a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
- ENTER/EXIT: 0.20/0.35; dwell and normalization unchanged.
- Full-hand commands disabled; application output remains legacy-only.
- Images are real webcam presentation copies saved locally, not research or
  submission evidence. No images are added to this documentation change.

| Run ID suffix (`g8-demo-20261002-…`) | Frames | Visual samples | Accepted pairs | Exclusions / limits |
| --- | ---: | ---: | ---: | --- |
| 141502 | 1183 | 6 | 0 | T images show open hand rather than contact; instruction trial |
| 141902 | 3882 | 36 | 3 | Two complete pairs rejected; two orphan V labels |
| 142431 | 2869 | 24 | 0 | Three complete pairs rejected; one orphan V label |
| 142940 | 2533 | 30 | 5 | Labels confirmed; intended nearer distance not visually verified |
| 143603 | 1857 | 24 | 1 | Two short near holds and one substantial palm change rejected |
| 144027 | 1331 | 26 | 0 | Already opened before stop instruction; closed cleanly; three completed pairs and one orphan V are unconfirmed and excluded |

**9 verified accepted pairs; 9 completed V→T pairs rejected; 3 additional orphan
V labels in the confirmed collection.** The final run's three completed pairs
and one orphan are retained locally but not added to verified counts or analysis.
All six processes reported clean shutdown with exit code 0. No further run was
started after the stop instruction.

Normal-light V non-contact / T actual-contact labels were explicitly requested
and confirmed by the operator for the retained runs. Source images independently
show gaps versus contact configurations, subject to camera resolution and fingertip
occlusion. The first instruction trial was rejected despite marker labels because
its images did not show contact. Duplicate marks were conservatively flagged.

## Pair selection and method

Each accepted pair has adjacent V then T, a following U, two synchronized images
per state (marker and >=0.5 s held image), continuous usable geometry and no reset
through the pair. Image inspection checks palm pose and label plausibility.
Substantial palm changes are rejected; small residual drift remains documented.

Use existing A5.4 extraction offline on the original filtered landmark CSV,
aligned to actual source geometry and timestamped snapshots. All 35 x/y-derived
features are saved per frame under `runs/p1f_matched/*_features.jsonl`.
No live diagnostic implementation is changed or injected.

Analyze each held window from marker +0.5 to +1.5 seconds. Compare the CONTACT
window median minus its matched NEAR window median. Save within-window min,
quartiles, median and max, alongside palm anchor movement, width change, lateral
axis rotation and normalized palm-shape residual. Short holds with inadequate
timing margin are flagged rather than counted toward the target. These collection
timing criteria do not alter temporal dwell or classification thresholds.

Selection/rejection reasons are preserved in `runs/p1f_matched/review.json`.
The full paired distributions for every feature are in
`paired_feature_distributions.csv` and `paired_summary.json` in that directory.
Frames within a hold and pairs from one operator/session are correlated; counts
are descriptive diagnostic evidence, not independent population accuracy trials.

## Per-pair distances

All values are aspect-corrected thumb-index distance / MCP5–17 width.

| Run / V marker | NEAR median | CONTACT median | CONTACT − NEAR |
| --- | ---: | ---: | ---: |
| 141902 / V6 | 0.35802 | 0.26618 | −0.09184 |
| 141902 / V13 | 0.21863 | 0.26251 | **+0.04388** |
| 141902 / V16 | 0.40108 | 0.22517 | −0.17591 |
| 142940 / V1 | 0.43619 | 0.19660 | −0.23959 |
| 142940 / V4 | 0.36062 | 0.23353 | −0.12709 |
| 142940 / V7 | 0.32155 | 0.25235 | −0.06921 |
| 142940 / V10 | 0.33815 | 0.26214 | −0.07601 |
| 142940 / V13 | 0.33869 | 0.27823 | −0.06045 |
| 143603 / V7 | 0.43276 | 0.33853 | −0.09423 |

Distance decreases in eight pairs but increases in one visually matched,
operator-confirmed pair. Its NEAR median is lower than its CONTACT median.
This reversal must not be discarded merely because it prevents a clean separator.
The paired median decrease of 0.09184 does not imply a universal absolute threshold.

## Paired feature distributions

Ranges and medians below are over nine **paired median differences**, not pooled
class samples. Sign counts describe CONTACT lower / higher than NEAR.

| Feature | Difference min | Median | Max | Lower / higher |
| --- | ---: | ---: | ---: | --- |
| Thumb-index distance / palm | −0.23959 | −0.09184 | +0.04388 | 8 / 1 |
| Thumb tip → index MCP / palm (opposition geometry) | −0.22897 | −0.02055 | +0.17102 | 5 / 4 |
| Distal segment cosine | −0.81013 | +0.03728 | +0.12978 | 3 / 6 |
| Index straightness | −0.36170 | +0.00437 | +0.07374 | 4 / 5 |
| Thumb straightness | −0.01673 | +0.00560 | +0.02402 | 3 / 6 |
| Tip gap along distal palm axis / palm | −0.24430 | −0.08779 | +0.05230 | 8 / 1 |
| Palm-width denominator, image-height units | −0.00872 | −0.00500 | +0.01087 | 8 / 1 |

All individual palm-frame fingertip coordinates and finger joint angles are
retained in the full paired CSV/JSON, including within-hold quartiles. Opposition,
distal directions and straightness have mixed signs. Distance and its distal-axis
projection are strongly related measurements, not independent corroboration.
Denominator variation alone does not explain the reversed pair: 141902/V13 has
approximately −2.39% width change with only −0.02 degrees lateral-axis rotation
and a 0.00900-palm-width shape residual. No normalization replacement is justified.

## Visual observations and limitations

- Retained V and T configurations are visually similar; gaps can be visible while
  the provider's tip landmarks remain offset from the skin surface.
- Rejected examples include an open-hand T label, repeated label sequences,
  insufficient timing margin, opening the near pose further during a hold,
  whole-hand translation of about 0.58 palm widths, and rotation changes exceeding
  20 degrees. Raw data is retained; these are not hidden as successful collection.
- Medium versus genuinely nearer hand size is represented, but only one retained
  nearer pair and limited side-angle coverage remain. There is no balanced factorial
  coverage. Curvature varied across runs and within the closing movement; the
  requested controlled two-configuration validation is not fully established.
- Near-tips and contact can be hard to judge from 640×480 images. Operator labels
  plus image inspection do not measure skin-contact force, depth or intent.
- No UNKNOWN snapshot or lost-tracking snapshot authorizes full-hand action in
  any run; offline checks found zero unsafe records and zero observer errors.
  This is existing observation safety, not validation of a new predicate.

## Conclusion and smallest next step

**WEAKLY SEPARABLE with current evidence.** Paired distances often change in the
expected direction, but reversals and inconsistent additional features do not
support a small robust deterministic predicate. The evidence also does not prove
all joint 2D geometry intrinsically incapable of separating the classes. No complex
classifier is fitted, threshold tuned, or predicate implemented.

Following the user's stop request, do not propose another webcam repetition as
the immediate step. First review the intended PINCH acceptance criterion against
the existing recorded observations: a deliberate stable hand pose and physical
skin-contact detection are different validation objectives. Any change of that
criterion requires explicit agreement; this collection changes neither semantics
nor architecture. No A6 work begins.

## Integrity

Application/diagnostic code changes: **NONE**. Only this report is added; local
analysis helpers, review annotations, numeric outputs and webcam samples remain
under ignored `runs/`. Tests are not rerun because the validated implementation
is unchanged; no new test pass is claimed.

Core, FIST, classifier, profiles, temporal behavior, legacy sensitivity/interaction,
InteractionState, scene/router/UI and frozen evidence/experiments remain unchanged.
`g7-final` still resolves to `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
No stage, commit, push, tag, predicate implementation or further test phase.
