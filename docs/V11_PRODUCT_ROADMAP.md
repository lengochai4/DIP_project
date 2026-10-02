# v1.1 application continuation — active roadmap

Latest product decision: [practical SIMPLE controls](V11_SIMPLE_PRODUCT_DECISION.md)
are implemented as the default launch path: POINT rotation, OPEN menu/hover-select,
two OPEN palms scale, no PINCH calibration dependency. Legacy remains selectable;
the PINCH foundation below is an optional lab path, not the product gate.
Current automatic suite: **1332 passed**. Complete-application physical smoke is
next; no release/commercial validation claim follows from synthetic tests.
This update supersedes the prior PINCH-first opt-in/default plan below.

This is the user-authorized post-v1.0 Extension/product continuation. It does
not replace canonical research specifications or reinterpret frozen results.
The application is a scientific prototype undergoing engineering validation;
commercial validation, production readiness and universal gesture accuracy are
not established. No G9 code is restored/copied.

## Immutable baselines

- `g7-final^{commit}`: `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- `dip-touchless-stem-v1.0^{commit}`: `2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`.
- Frozen Core, G7 report/evidence/experiments and their provenance stay unchanged.
- Legacy v1.0 remains selectable via `python -m extensions.stem3d.live_demo` or
  `python -m extensions.stem3d.full_hand_app --mode LEGACY`.

## Ordered work and gates

| Phase | Current status | Next scope |
| --- | --- | --- |
| 1. Intentional PINCH | IMPLEMENTED, physical pending | Explicit release lifecycle, relative evidence, temporal dwell/hysteresis/rearm and OBSERVE parity |
| 2. One-hand commands | IMPLEMENTED, experimental opt-in | POINT rotation/pointer, PINCH selection/vertical scale, OPEN release, FIST diagnostic-only; exclusive ownership/focus |
| 3. Calibration/sensitivity | IMPLEMENTED | Explicit K/click enrollment, retry/reset, three Extension sensitivity profiles, locally saved ergonomic preferences; no reference auto-restore |
| 4. Product UX | IMPLEMENTED | Settings, candidate/stable/finger/intent feedback, Help/onboarding, mirror mapping, keyboard/mouse fallback, modal safety; 10 synthetic screenshots |
| 5. Two hands | IMPLEMENTED, separately experimental opt-in | Independent application provider, deterministic projected association, OPEN-pair scale, ambiguity/loss neutral; physical stability pending |
| 6. Reliability | AUTOMATIC TESTS PASS | Camera/model/logger startup/read faults, cleanup errors, duplicate delivery, owner/focus/reset/loss/restart safety; physical smoke pending |
| 7. Performance | PROFILED CPU UI ONLY | Proven background-fill hot path optimized with bounded immutable template; no webcam FPS claim |
| 8. Final packaging | LOCAL CANDIDATE PREPARED | Source snapshot, launcher, setup/walkthrough, synthetic screenshots, release notes/limitations; publish only after physical acceptance |

The user explicitly moved physical testing to the end: complete the application,
then test and fix observed issues. This supersedes the earlier implementation stop
before the command bridge. Development commands are now explicit experimental
opt-ins, never promoted to validated/default interaction. One-hand deterministic
tests preceded the two-hand prototype; its physical gate remains pending.
Stop now for final physical acceptance, a genuine blocker or a proposed frozen
research/Core change. Never substitute synthetic data for physical evidence or
publish automatically. No stage/commit/tag, stash deletion or tag rewrite performed.

Current setup, walkthrough, acceptance procedure and release candidate notes:
[`release/v1.1/README.md`](../release/v1.1/README.md).

## Units completed before the first physical gate

### Temporal intentional-PINCH diagnostics

New `full_hand/intent_temporal.py` consumes A5.6 evidence independently of old
A3/A4 pose classification. UNKNOWN/input failure revokes immediately. Initial
release/rearm is mandatory; static closed startup never enters. Enter needs fresh
net closing progress above both configured minimum and measured reference noise,
then continuous enter dwell. Band cancels entry dwell, never counts as release.
Valid supported band can continue HOLD. First strict release revokes active
evidence immediately. Release confirmation and rearm share an interval and readiness
uses their maximum, not their sum. Interrupted release cannot restore HOLD.
Closing candidate lifetime is bounded; slow movement is not rejected by velocity.
Run/reference/time/gap/reset discontinuities neutralize; IDs never rewind.

### Reference lifecycle

`full_hand/intent_session.py` enrolls only on focused **K**, the operator's
confirmation that thumb/index are comfortably apart for the configured window.
No first-hand/automatic/largest-distance guess. Builder uses ALL held samples or
rejects the whole window. Interrupted/noisy enrollment requires explicit retry.
K refresh and X reset revoke old intent immediately. Each enrollment has a new
reference ID/version, source identities, immutable dispersion and profile hash.

Projection guard compares 10 x/y palm distance ratios (wrist/MCP 5/9/13/17)
and a configured scale domain against enrolled medians. This is projected-domain
compatibility, not hand recognition, quality/confidence or 3D orientation/depth.
Shape-incompatible or changed source dimensions/run/filter/time domain requires
explicit recalibration. F0 and all Core algorithms stay unchanged.

Brief tracking loss retains reference as UNVERIFIED metadata. Reacquisition is
neutral. A proof-only branch checks compatible, ordinary-valid **strict release**
continuously before restoring reference validity. Proof enter/hold never reaches
the tracker or UI. Return already closed or through the band cannot revalidate.
After revalidation, the tracker begins neutral and independently requires fresh
release/rearm; no old episode resumes. Reference numbers never adapt or drift.
The verification interval is distinct from ordinary cycle release/rearm dwell.

A5.6's missing-comparison invalidation was corrected narrowly: unavailable
projection during lost/invalid input can retain unverified metadata, whereas
an actually incompatible or unconfirmed ordinary-valid domain invalidates it.
This changes no legacy/public Core behavior or scalar pose thresholds.

### OBSERVE composition and feedback

```text
camera -> unchanged Core/filtered TrackingFrame -> legacy GestureEngine
                                            -> unchanged InteractionState -> router/scenes

actual source FrameGeometry + same filtered frame
  -> A2/A3/A4 observation (unchanged)
  -> explicit release lifecycle -> A5.6 relative evidence -> intentional tracker
  -> local diagnostic journal + opt-in Live Vision feedback ONLY
```

`--intent-pinch-observe` explicitly selects the new branch. It cannot be used in
LEGACY or combined with old CONTACT/NEAR marker collection. Old default OBSERVE
and legacy output paths remain available. T/U now mark intended close/open;
N labels non-intent exposure, not skin-contact detection. A separate shadow legacy
engine compares all InteractionState fields on the same filtered frame.

New `IntentObservationDashboard` subclasses the existing shell. Only an opt-in
dashboard factory seam is added to `live_demo`; the default dashboard/controller/
router remains unchanged. Feedback has calibration status, unclipped closure,
intent state/cycle and keyboard guidance. Stale frame identities display unavailable;
failure/close clears feedback. No image storage by default or research-log schema
change. Local sidecars under `runs/full-hand-observe/<run>/intent_pinch/` are
development diagnostics, not G7/submission evidence.

`intent_pinch_observe.yaml` holds **unvalidated engineering starters**, fixed before
collection: relative enter 0.60 / exit 0.25; enter dwell 0.20 s, release confirmation
0.15 s, rearm 0.25 s; no skin-contact/near-touch threshold tuning. The A5.6 pure
contracts still have no default physical values. Existing baseline 0.20/0.35 and
rejected 0.33/0.35 scalar profiles are not promoted or modified.

## Original P-INTENT-1 procedure — superseded by final practical acceptance

The following preserves the original observation-only decision/procedure. The
active final gate is now [`PHYSICAL_ACCEPTANCE.md`](../release/v1.1/PHYSICAL_ACCEPTANCE.md).

Decision: does the enrolled relative closing sequence reliably enter/hold/release/
rearm, reject ordinary non-intent activity, and neutralize/reacquire safely? This
is intentional interaction, not contact-vs-gap classification.

Launch from repository root:

```powershell
.venv\Scripts\python.exe -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND --intent-pinch-observe
```

One focused session, normal lighting, one hand at medium distance:

1. Enter/S starts; A opens Analysis for larger feedback. Keep thumb/index
   comfortably apart, press K once and hold steady until READY + RELEASED.
2. Press T once to start the intentional phase. Make **20 natural close -> hold
   -> open cycles**, checking the displayed cycle count rises once each time and
   RELEASED returns after opening. Skin contact is unnecessary. Count missed
   attempts, extra entries and release/rearm failures. Do not change settings.
3. Press U after the final opening, then N. Spend **2 minutes** pointing,
   translating/rotating the wrist and neutral holding, without intentional pinch.
   Include comfortable moderate angle/distance variation. Note any unintended
   cycle increment. Report if the non-intent segment was not completed.
4. Press T to end the non-intent segment. Briefly remove the hand, return with thumb/index closed (must remain neutral),
   then open to revalidate/rearm. Do one deliberate closing cycle. Press X while
   holding: intent must stop and require calibration. Q shuts down.

Report attempts/successes, release/rearm failures, false entries during the neutral
segment, stuck states, loss/reacquisition behavior and whether legacy still feels
unchanged. Ground-truth attempts and intentions require this user confirmation;
detected entries alone are not an accuracy measurement.

Engineering targets: >=90% intentional success; <=0.1 false activation per valid
tracked minute; >=95% release/rearm; zero stuck actions or UNKNOWN/loss/reacquisition
safety violations. Also require exact legacy parity, no diagnostic errors and clean
shutdown. Report observed counts/exposure separately, with limitations. The journal
also measures non-intent exposure with a usable reference and armed state; an
unavailable/disarmed branch must not manufacture a good false-activation rate.
Loss/incompatible-domain intervals remain visible, not silently scored as success. This short
first gate does not replace broader user/device/condition validation or establish
commercial readiness; longer evidence may be needed before a release gate. No
commands are promoted to validated/default interaction until the applicable validation gate is assessed as passed.

If failure occurs, inspect synchronized identity/geometry/timing/reasons and
recommend the smallest correction with a clear decision question. No threshold
chasing, repeated contact collection or fabricated physical claims.

## Change record

Change: independent relative intention tracker/lifecycle and opt-in observation
composition/feedback. Reason: operational intention contract A5.5 replaces the
unsupported assumption that RGB x/y landmarks detect skin contact. Canonical
research sections changed: NONE. Modules: Extension, additive profile, tests and
this roadmap. Algorithmic impact: new observation branch only. Experimental/G7
impact: NONE. Legacy compatibility: field parity tested; legacy alone owns output.
Existing results invalidated: NO; old CONTACT/NEAR results retain their original
meaning and are not relabeled as intention performance.

## Executed checks before P-INTENT-1

- Temporal unit: 28 focused tests; full suite 1192 passed at that unit.
- Lifecycle unit: 22 new tests plus foundation regression (142 passed); full
  suite 1214 passed at that unit.
- Final focused full-hand/shell/presentation: **749 passed**, including 66 new
  tests in this continuation (28 temporal, 23 lifecycle, 15 observation).
- Final full `pytest -q`: **1230 passed**.
- `python -m compileall extensions/stem3d`: exit 0.
- `git diff --check` and separate checks of new untracked files: passed.
- Two local 1600x900 synthetic layout QA views inspected (Workspace/Analysis);
  feedback wrapping/card bounds corrected. These are ignored local QA artifacts,
  not final screenshots, physical validation or frozen evidence.
- Core/G7 frozen-path comparison and both immutable tag identities: unchanged.
  G9 paths absent, deferred stash retained; no Git publication operations.
- Physical validation: **NOT RUN / waiting at P-INTENT-1**. No commands enabled.

Remaining limitations: classifier FIST reliability has not been repaired or newly
physically validated; its diagnostic-only role remains. Projection guard is an
engineering compatibility test, not multi-user association. The first intent
profile is unvalidated. No persisted user calibration, sensitivity settings,
two-hand interaction, performance result or commercial readiness is claimed.

The preceding execution record describes the first OBSERVE unit. The later user
instruction authorized completing the product before physical testing; the
implementation and checks below supersede its NOT STARTED/pending product items.

## Final application implementation — 2026-10-02

```text
camera -> unchanged Core/provider/filter/legacy GestureEngine -> unchanged Core log
           | read-only public frame outputs + actual source FrameGeometry
           v
      A2/A3/A4 diagnostics + explicit release lifecycle + relative intent tracker
           v
      single application owner: LEGACY (default/fallback), OBSERVE or opt-in FULL_HAND
           v
      unchanged public InteractionState -> existing focus router -> scenes -> renderer

optional independent application adapter (2 hands / Raw x/y)
  -> deterministic association + OPEN dwell -> exclusive projected scale
```

`product/composition.py` suppresses duplicate application delivery of the Core
legacy callback, while the original Core output is still generated/logged unchanged.
The presentation seam computes one selected application state and delivers it once.
The legacy shadow checks all fields on identical filtered input. No Core reverse
dependency, InteractionState modification or scene/router semantic change.

POINT requires both current candidate and stable POINT; changing pose cancels
rotation immediately. Intentional PINCH requires valid reference and current
known relative evidence, separate from A3's old scalar/contact-like UNKNOWN band.
Action/owner/focus/scene/settings switches reset motion anchors and require release.
First clutch frame emits no scale displacement. Per-frame aspect-corrected motion
uses explicit deadzones/gains/caps in `config/extensions/application.yaml`, with
unvalidated ergonomic starters. Research/legacy sensitivity is unchanged.

Two-hand SDK calls live in `application_adapters/`, outside scene/UI code and
frozen Core. Existing architecture tests caught the initial boundary violation;
the adapter was relocated and the old tests were retained unchanged. Association
uses x/y palm continuity and ambiguity margins, not handedness confidence or
metric z. Both OPEN hands must dwell before scale; one-hand/invalid/ambiguous
pairs cannot resume old scale. Capability requires launch flag plus Settings;
one-hand commands and UI clicks are suppressed while a pair owns input.

New factory seams preserve the default v1.0 composition. The v1.1 app adds unique
microsecond run IDs, explicit camera selection and nonzero failure exit; default
legacy run IDs/exit behavior stay unchanged. Journals record selected commands,
ownership, settings, two-hand states, resolved profiles and current source hashes.
Frames/images are not stored by default. Startup/read/cleanup faults are tested.

CPU shell profiling (50 builds per view at 1600x900; no camera/model/Core): before
Workspace/Analysis/Evidence totals 0.383568/0.416879/0.360560 s; after
0.143249/0.170688/0.123138 s. `numpy.full` was the measured dominant path
(0.797 s cumulative across 150 builds). One current-size immutable background
template now yields independently owned copies; old surfaces and inputs stay
unchanged. Minor feedback-layout cleanup accompanied this comparison, so these
are observed UI totals, not an isolated causal estimate or end-to-end FPS claim.
Profile artifacts are local `runs/v11-ui-qa-before` and `runs/v11-ui-qa-after`.

Final release/physical readiness: **CANDIDATE, NOT YET PHYSICALLY ACCEPTED**.
See the final QA status in `release/v1.1/QA_STATUS.md`. Recommended future commit:
`feat: complete v1.1 intentional full-hand application`; future tag
`dip-touchless-stem-v1.1` only after physical acceptance/review. Frozen baselines
remain immutable and G9 remains deferred/stashed.
