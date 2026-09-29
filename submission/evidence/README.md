# Final Evidence Package

This directory contains selected generated evidence for the G7 final package.

## A1 — Static temporal stability

Batch:

`G7-A1-STATIC-20260928T144254479591Z`

Primary metric:

`radial_rms_jitter`

Recorded trials: 3

Evaluable trials: 2

`trial-002` is retained with primary metric unavailable because
`no_common_usable_frames`.

Files:

- `a1_static/static_jitter.png`
- `a1_static/trajectory_xy.png`
- `a1_static/trajectories.csv`
- `a1_static/metrics.csv`
- `a1_static/provenance.json`

## A2 — Dynamic responsiveness characterization

Batch:

`G7-A2-DYNAMIC-20260928T151157912799Z`

Primary metric:

`trajectory_deviation_rmse`

Recorded trials: 3

Evaluable trials: 0

All three primary metrics are unavailable because
`no_common_usable_frames`.

`a2_dynamic/responsiveness_unavailable.png` intentionally contains no
numeric bars or fabricated zero-valued measurements.

Files:

- `a2_dynamic/responsiveness_unavailable.png`
- `a2_dynamic/metrics.csv`
- `a2_dynamic/provenance.json`

## Experiment B — Illumination robustness

Primary metric:

`valid_hand_observation_rate`

Normal batch:

`G7-B-NORMAL-20260928T151702564004Z`

Low-light batch:

`G7-B-LOWLIGHT-20260928T152103579608Z`

The final P1 runs logged `enhancement_active=False` throughout the analyzed
normal and low-light windows. Therefore equality between P0 and P1 must not
be interpreted as a direct CLAHE-active versus bypass comparison.

Files:

- `b_normal/valid_hand_rate.png`
- `b_normal/metrics.csv`
- `b_normal/provenance.json`
- `b_lowlight/valid_hand_rate.png`
- `b_lowlight/metrics.csv`
- `b_lowlight/provenance.json`

## DIP method visualization

`dip_visual/dip_clahe_frame161.png` is a method illustration generated with
the production `AdaptivePreprocessor` forced to `policy="always"`.

It is not a primary Experiment-B P1 result.

Files:

- `dip_visual/dip_clahe_frame161.png`
- `dip_visual/dip_clahe_frame161.json`

## Evidence boundary

These selected files preserve measured outcomes, unavailable primary metrics,
and provenance without changing the frozen G7 analysis window, source set,
primary metrics, or exclusion policy.
