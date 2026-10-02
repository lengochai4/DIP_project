# v1.1 A5.3: experimental PINCH profile

Development observation only; no full-hand commands are enabled. The candidate
is not a universal/default threshold or frozen G7 research configuration.

## Explicit selection

Baseline remains `config/extensions/full_hand_observe.yaml`, ENTER=0.20 and
EXIT=0.35. Omitting `--profile` still selects it. Candidate is a separate file:
`config/extensions/full_hand_pinch_candidate.yaml`, ENTER=0.33 and EXIT=0.35.
Only ENTER differs. All finger/thumb/FIST thresholds, normalization, dwell,
loss/rearm and discontinuity rules remain unchanged. The named candidate is
rejected with LEGACY mode; normal legacy launch still uses its own untouched
GestureEngine configuration and ignores unrelated observation-profile paths.

```powershell
# Baseline, still the default observation profile
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND

# Explicit experimental candidate, diagnostic collection only
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --profile config/extensions/full_hand_pinch_candidate.yaml --pinch-diagnostic --pinch-visual --pinch-calibration-markers
```

Additional labels require `--pinch-calibration-markers` and `--pinch-diagnostic`:
T=deliberate contact; V=very near, NOT touching; B=medium separation;
U=clear release; N=optional note. V/B have no default key behavior or application
commands. Simultaneous physical labels are recorded as conflicting, not guessed.
Opt-in visual samples include marker and >=0.5-second held frames for all four
classes, capped at 40 samples per calibration run. Otherwise the existing
24-sample visual cap and T/U-only polling remain unchanged.

Physical protocol: establish each state for approximately one second before
marking, hold two more seconds, and repeat U -> V -> B -> T -> U. In particular,
start near-touch trials after a clear release, and do not touch during V. PNGs
and JSONL remain local under ignored `runs/full-hand-observe/<run-id>/`, outside
research/submission evidence. The resolved profile/hash, unchanged legacy config
hash, and diagnostic source hashes identify the run.

Baseline profile SHA256:
`a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba`.
Candidate profile SHA256:
`7db057ff924639ad4ff695086ac3fece15c90a5035a96a561edd95d862445c92`.
Legacy config SHA256:
`ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.

## Tests and unchanged safety contracts

21 candidate/label cases verify explicit profile selection and legacy rejection,
the frozen baseline resolved-profile hash, an exact one-field candidate diff,
strict `< 0.33` ENTER and `> 0.35` RELEASE boundaries (inclusive endpoints BAND),
baseline BAND behavior on P1e contacts, candidate dwell, UNKNOWN action blocking,
band latch diagnostics, interrupted strict-release rearm, loss/reacquisition,
exit-equality rejection, re-entry, exact legacy InteractionState parity, opt-in
V/B polling, label conflicts and four-class synchronized capture metadata.

Full-hand regression: 396 passed. Full suite: 951 passed.
`python -m compileall extensions/stem3d` and `git diff --check` passed.
No classifier or temporal implementation was changed. UNKNOWN never grants
full-hand diagnostic action permission; application commands remain legacy-only.

## Physical decision: TOO PERMISSIVE

The experimental profile was implemented and tested, but **0.33/0.35 is NOT
ACCEPTABLE as a contact-calibrated v1.1 profile**. Confirmed non-touching trials
produce stable PINCH. Keep it explicit/experimental for reproduction; do not
promote it, tune it automatically, or enable full-hand commands.

All three webcam runs used revision
`40af4e729f483c789db8f6aaf9048b5e646f52d2` plus the uncommitted A5.3 additions,
the same candidate/profile/config hashes above, RAW filtering and actual 640x480
geometry. Thresholds stayed fixed throughout collection. Diagnostic manifests
record the changed observation/composition source hashes. Images are real local
captures, not synthetic screenshots or G7 research evidence.

| Run ID | Frames | Marker samples | Role |
| --- | ---: | ---: | --- |
| g8-demo-20261002-095422 | 929 | 12 images-with-JSON samples | 3 T/contact attempts and 3 U/release labels; only 2 completed T-to-U cycles |
| g8-demo-20261002-095623 | 1517 | 12 samples | 3 V/near and 3 B/medium labels; first V was contaminated |
| g8-demo-20261002-100358 | 759 | 8 samples | 2 clean U-to-V trials, separately confirmed by operator |

Each sample comprises a source PNG, separate overlay PNG and JSON. Total:
**32 synchronized samples / 64 PNGs**, under each run's `pinch_visual/` directory.
The operator did not complete the requested third clean V/U cycle or a final U
marker in the last run; do not claim three clean negative trials. Two confirmed
failures suffice to reject this candidate, not to estimate a false-positive rate.

### Label correction and visual correlation

The operator reported brief contact or a marker mistake, then identified
"marker 1" in the context of the first V trial in 095623. That V interval and
its two synchronized samples are retained as contaminated supplemental data,
excluded from clean false-enter statistics. Four transitions inside that old
V-labeled interval are not claimed as four independently confirmed false enters.
The other two V labels in that run have no sampled stable PINCH; their operator
labels are retained as supplemental, not substitutes for the clean re-run.

For 100358, the operator explicitly confirmed **both V trials had no contact**
throughout the held state. Source images at frames 370/385 and 680/696 show a
visible gap, while all four synchronized snapshots are armed, candidate PINCH,
stable PINCH and action-allowed. Those are confirmed false stable-PINCH states,
not a UNKNOWN permission violation. No full-hand application action was emitted.

### Per-class distributions

The primary table uses synchronized marker/held samples: all T labels in 095422,
only the newly confirmed clean V trials in 100358, all B labels in 095623, and
the U labels in 095422/100358. These are correlated samples from one operator,
not independent trials or a benchmark. Medium spacing was not standardized:
one B marker image is visibly widely separated before the held frame settles;
the 1.77587 outlier is kept rather than silently relabeled or removed.

| Physical class | Marked trials / samples | Min | P05 | Median | P95 | Max | Sampled stable PINCH |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Deliberate contact | 3 / 6 | 0.28877 | 0.29044 | 0.30681 | 0.32459 | 0.32976 | 2/3 trials; 4/6 snapshots actionable |
| Confirmed near, NOT touching | 2 / 4 | 0.23396 | 0.23579 | 0.27650 | 0.31612 | 0.31777 | **2/2 trials; 4/4 snapshots actionable** |
| Medium separation | 3 / 6 | 0.49227 | 0.50156 | 0.71645 | 1.54948 | 1.77587 | 0/3 trials |
| Clear release | 5 / 10 | 0.70211 | 0.70749 | 1.18095 | 1.34880 | 1.38368 | 0/5 labels |

The two remaining old V labels have four supplemental samples spanning
0.41560-0.55420, none stable PINCH. Including them with the two clean new
negatives yields 2/4 marked negative trials with sampled stable PINCH, but this
small heterogeneous set must not be presented as an estimated 50% error rate.

Local `a53_analysis.json` records full per-frame labeled-interval distributions
as well as synchronized examples. Whole intervals include pose movement before
the next delayed operator marker: apparent enters under a U label can be the
next contact/near pose already established before T/V, not false enters during
visually verified clear release. The primary table does not mix these transition
frames into a claim about the inspected held-state images.

### Enter, release/rearm/re-entry and safety evidence

- Positive contact run: stable enters at **433 and 664** precede their T markers
  456 and 683, consistent with establishing the pose before marking. Both T
  source/held images show contact and stable PINCH. Their releases are at
  **553 and 738**. Frame 664 is a stable re-entry after the first release.
- Third T attempt (867/883) has candidate PINCH but no stable PINCH. Entering
  geometry repeatedly traverses the candidate's narrow band; the final pending
  dwell is approximately 0.23832 s, below the unchanged 0.25 s requirement.
  The run ended without a final U. Do not hide this miss or count an unobserved
  eventual stable transition.
- Clean negative run: stable enters **336 and 600** occur after the preceding
  clear-release states and before V markers 370 and 680. The protocol and
  explicit no-contact confirmation associate these with the two negative trials.
  Literal phase-only counting would call them U-label transitions because the
  operator marks after establishing the new state. All four V images independently
  confirm false active stable states. Releases occur at **430 and 727**.
- Strict release and readiness work. Earned arming is retained through release
  rather than unnecessarily disarming each cycle; a preserved armed state is
  not a new false-to-true rearm event. The positive run has two successful
  releases/readiness continuations and one subsequent positive stable re-entry.
  The negative run also releases and re-enters, but those entries are classifier
  failures, not successful contact recognition.
- False-to-true armed transitions across complete runs: 2 / 2 / 1, including
  initialization/reacquisition. There is no demonstrated stuck REARM_PENDING
  or stable PINCH latch. Last recorded states have no PINCH latch; the first
  run's pending PINCH has action blocked. Shutdown resets the observer.
- No UNKNOWN snapshot authorizes full-hand action, no unsafe loss state, no
  observer diagnostic errors. Total tracking: 2886 VALID / 319 NO_HAND across
  3205 frames, including startup/unlabeled withdrawal; no unintended-drop rate
  is inferred from those totals.
- Same-sample legacy GestureEngine replay matches **3205/3205 InteractionState
  records**, zero mismatches. Raw/filtered measurements match 3205/3205 with
  this RAW profile. Additional diagnostic I/O is not claimed to preserve
  wall-clock performance. All three processes exited 0 and closed cleanly.

## Interpretation and smallest next action

Raising ENTER improves sampled contact detection over the baseline, but it also
admits clearly non-contact geometry. The negative distances overlap contact
distances; in these captured poses, a single threshold low enough to reject
all clean negatives would also miss the measured contacts. No revised scalar
ENTER value is justified by this dataset. Do not lower/raise it again blindly,
weaken dwell, change normalization meaning or compensate in Core/provider.

Keep baseline **0.20/0.35** as default and retain **0.33/0.35** only as a rejected
experimental observation profile. The smallest next diagnostic would compare
contact versus controlled near-gap geometry with matched orientation and fully
centered hands before proposing any extra Extension-only geometry predicate or
orientation-specific calibration. Neither that diagnostic nor a classifier fix
or A6 commands is implemented here.

## Changed files and integrity

- New `config/extensions/full_hand_pinch_candidate.yaml`.
- `extensions/stem3d/full_hand_app.py`: explicit profile/default constants,
  candidate legacy guard, console profile identity and opt-in label flag.
- `extensions/stem3d/full_hand/pinch_diagnostic.py` and `pinch_visual.py`:
  opt-in four-class physical annotations and matching local image samples.
- New `tests/extensions/full_hand/test_pinch_candidate.py` and this report.

No changes to the baseline profile, FIST/pose classifier, temporal implementation,
normalization, legacy interaction/sensitivity, InteractionState, scenes/router/UI,
Core, frozen report/evidence/final experiments or G7 artifacts. Frozen paths match
`g7-final`, peeled commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
G9 remains stashed and all five G9 source paths are absent. Logs/PNGs and local
analysis stay under ignored `runs/`. No stage, commit, push, tag, universal
threshold promotion, command enablement or further-phase implementation occurred.
