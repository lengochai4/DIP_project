# P1 regression excerpts

`p1_regressions.json` is a development regression fixture derived without
rounding from ignored local P1 artifacts. It contains no images/video and is
separate from frozen G7 research evidence. It is not an accuracy dataset.

- Execution revision and resolved profile SHA-256 are recorded in the fixture.
- Geometry samples: filtered `runs/<run_id>/landmarks.csv`, combined with actual
  dimensions, timestamps and original diagnostics in
  `runs/full-hand-observe/<run_id>/snapshots.jsonl`.
- Temporal samples: consecutive sidecar frames 74–81 of
  `g8-demo-20261001-221612`, reproducing earned rearm followed by pure pinch band.
- Run `g8-demo-20261001-222450`: frames 337 and 1355 reproduce four curled fingers
  and an opposed but INTERMEDIATE thumb with definite pinch exit. Frame 200
  checks that the pinch band remains UNKNOWN; frame 80 checks an unopposed thumb.
- Run `g8-demo-20261001-221612`: frames 550, 620 and 337 preserve representative
  OPEN, POINT and PINCH observations respectively.

Mirror/rotation variants in tests are explicitly transformed regression inputs,
not additional physical observations. Original recorded classifications are kept
to document the pre-fix result; the operator's checklist does not provide precise
frame-level intended-pose labels.

`p1_rearm_sequences.json` adds contiguous pose/pinch/tracking/reset excerpts
for A5.2: P1 run `g8-demo-20261001-221612` frames 74–349, and P1b run
`g8-demo-20261001-225528` frames 228–258. Source sidecars and legacy frame CSVs
are the same ignored development paths described above. Each run records its
original revision and resolved profile. Distances/timestamps are unrounded;
there are no images, altered source logs, or added physical accuracy labels.
