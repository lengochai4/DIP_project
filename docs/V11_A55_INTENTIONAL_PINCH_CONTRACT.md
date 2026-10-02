# v1.1 A5.5 — intentional PINCH semantic contract proposal

**DESIGN ONLY.** This is a non-canonical Extension proposal, not an implemented
behavior or an amendment to frozen Core/G7 contracts. No code, profile, command,
UI, FIST logic or existing A3/A4 semantics change. No new physical run is requested.

## 1. Meaning and boundary

PINCH means a deliberate thumb-index **closing sequence from a verified released
reference**, followed by a stable closed hold. Skin contact is unnecessary. A
comfortable small remaining gap is allowed when the closing sequence qualifies.
"Intentional" is this observable sequence, not a claim to read mental intent.
Identical visible movements with different mental intentions remain indistinguishable.

A static close hand at startup/reacquisition cannot activate. A thumb-index
distance alone cannot activate. CONTACT/NEAR labels in P1d–P1f can inform geometry
and noise analysis but are not intention-positive/negative labels for this contract.
In particular, deliberate movement into a near pose can now be a legitimate PINCH;
old near-touch false-positive counts must not be relabeled as new accuracy results.

Proposed additive data flow:

```text
read-only filtered TrackingFrame + actual FrameGeometry
  -> A2 geometry / available A5.4 features
  -> reference validity + relative closure observation
  -> independent intentional-PINCH temporal state
  -> observation snapshot and diagnostics only

existing GestureEngine -> unchanged InteractionState -> existing application
```

The new intentional state has its own type and schema. Do not overload HandPose,
PoseObservation, StablePoseState or InteractionState. Existing A3 scalar-band
UNKNOWN remains unchanged in its own diagnostics. It is not the input definition
of intentional PINCH. Any UNKNOWN in the **new intentional observation**, invalid
geometry or lost tracking always forbids active evidence.

## 2. Proposed immutable contracts

| Contract | Required content |
| --- | --- |
| ReleaseReference | ID/version, session/run scope, source frame/time window, acquisition method, release distance median, measured dispersion/sample count, optional intentional-closed endpoint, compatibility metadata, validity/reasons |
| RelativeClosureObservation | run/frame/timestamp, actual frame geometry, geometry/reference validity, distance/numerator/palm denominator, unclipped closure/progress, release/closing/enter/hold evidence, predicate diagnostics and reasons |
| IntentPinchSnapshot | state, armed, waiting-for-release, active-evidence flag, pending dwell timestamps, reference ID, cycle/transition/reset IDs, typed transition/reset reasons |
| IntentPinchProfile | semantic/schema version, reference policy, noise/progress rules, enter/exit closure bounds, timing and compatibility parameters; resolved hash |

Missing values are None with reasons; never zero-filled observations. Diagnostics
are not tracking confidence. No handedness score or metric-z/depth feature is used.
No output contains rotation, scale, click or scene commands. `active_evidence`
is an observation of this proposed gesture, not permission to drive the application.
The earliest eligible observation after any reset is neutral.

## 3. Reference and relative closure

Using actual image width W and height H:

```text
n(t) = hypot((x4-x8) * W/H, y4-y8)
p(t) = hypot((x5-x17) * W/H, y5-y17)
d(t) = n(t) / p(t)
r    = robust median of a verified comfortable-apart release window
c(t) = (r - d(t)) / r
```

c=0 denotes the enrolled release separation. Positive c denotes closure relative
to that reference. Negative c denotes wider separation; do not silently clamp
decision data. No universal absolute tip-distance ENTER value defines PINCH.

Optional personal range calibration can additionally enroll k, a comfortable
intentional-closed endpoint, without asserting physical contact:

```text
s    = r - k
c(t) = (r - d(t)) / s
```

The reference kind is explicit and hashed; do not silently switch formulas.
r, p and optional s must be finite and nondegenerate. The enrolled span must
exceed the measured noise allowance. Bad/unstable enrollment is rejected; do not
repair a small span by inventing an epsilon or an optimistically wide range.
Noise allowance is a documented engineering dispersion rule, not provider confidence.

Also record progress from the most recent confirmed release, c(t)-c_at_release.
Entry needs a credible net closing excursion above the configured noise allowance
and a subsequent continuous enter dwell. A strict minimum closing speed is not
required; slow comfortable gestures should remain possible. Signed trend/rate
may be diagnostic. A bounded history/candidate lifetime prevents arbitrarily old
motion from qualifying a new activation. Exact values are deferred, not tuned here.

The palm/reference domain must remain comparable. Translation and positive
uniform image scaling should not by themselves produce closing evidence. Out-of-plane
orientation and denominator changes can alter projected ratios; detect incompatibility
using available palm shape/orientation/scale diagnostics and return UNKNOWN when
comparison is unreliable. No 3D orientation or depth is inferred from x/y.

Freeze the reference for the complete released/closing/active/rearm cycle.
First prototype: freeze it for the session. No rolling maximum, per-frame anchor
reset, or automatic adaptation during CLOSING/HOLD. A later explicit refresh only
occurs while safely released, creates a new reference version and clears motion
history before rearming.

## 4. State semantics and transitions

Define configured bounds 0 < c_exit < c_enter < 1. Release evidence is strictly
c < c_exit; enter evidence is strictly c > c_enter. Equality belongs to the band.
These are relative bounds, not proposed numeric defaults.

| State | Meaning | Armed / active evidence | Ordinary transition |
| --- | --- | --- | --- |
| UNKNOWN | Missing, invalid, incompatible or ambiguous evidence; neutral waiting for trustworthy release | false / false | Verified geometric release completes rearm -> RELEASED |
| RELEASED | Comparable reference plus completed release/rearm dwell; ready for a fresh closing sequence | true / false | Credible new net closure -> CLOSING |
| CLOSING | Fresh local closing sequence; entry extent/dwell not yet complete | true / false | Continuous qualified enter dwell -> PINCH_ACTIVE; confirmed reopening -> RELEASED |
| PINCH_ACTIVE | The entry transition of one new qualified episode | true / true on this valid frame | Next valid supported frame -> HOLD |
| HOLD | Current usable geometry supports continuation of that episode | true / true | First strict release evidence -> RELEASE |
| RELEASE | Active evidence revoked; confirming release and preparing the next cycle | false / false | Continuous release/rearm evidence -> RELEASED |

PINCH_ACTIVE produces exactly one diagnostic enter identity per episode, not a
repeated event every held frame. HOLD has no extra dwell beyond the completed
entry dwell. Duplicate frames never advance dwell or create another enter.

Rules, in priority order:

1. Loss, invalid geometry/reference, reset or genuinely ambiguous intentional
   evidence cancels all pending entry/exit timers, revokes active evidence and
   enters UNKNOWN. This immediate safety path overrides any exit delay.
2. Initial arming requires valid **release geometry**, independent of OPEN/POINT/
   FIST classification. A scalar A3 pose label does not grant or block rearm.
3. CLOSING only starts from an armed release and a fresh closing excursion.
   Entry dwell starts once all enter predicates pass; any failing/UNKNOWN frame
   cancels that dwell. Reopening abandons the closing candidate. Stale candidate
   history expires safely; it cannot trigger after a long unrelated pause.
4. A valid hysteresis-band frame can remain CLOSING or HOLD only when current
   comparable geometry supports that state's interpretation. This is explicit
   hysteresis evidence, not an UNKNOWN frame retaining an old permission.
5. At first strict release evidence, revoke active evidence immediately and
   enter RELEASE. Release confirmation and rearm have separate configurable
   durations measured from the same continuous released interval. Readiness
   returns after max(release_dwell, rearm_dwell), avoiding accidental double dwell.
   The frame completing rearm is neutral; new entry begins on a later valid frame.
6. The band never counts as release. In RELEASE/UNKNOWN waiting-for-release it
   cancels release dwell but preserves that waiting status. Returning toward
   closed also cancels release dwell. Neither restores HOLD or re-arms. Only a
   subsequent continuous strict release can establish readiness.

Release-confirmed, rearmed, enter and safety-cancel observations carry unique
transition/cycle identities and reasons. They are diagnostics, not click events.
No stuck active state is tolerated; a closed hand legitimately waiting for release
is distinguishable from a stuck REARM_PENDING despite adequate release evidence.

## 5. Reset and reacquisition

Run change, duplicate/out-of-order timestamp or frame identity, configured long
gap, filter reset, explicit reset, tracking loss and incompatible source geometry
all neutralize the new tracker. Timings come from source timestamps, never frame
counts or wall-clock assumptions. Reset/transition IDs do not silently rewind.

After brief loss, a still-compatible reference may be retained as unverified
metadata. It cannot resume an old episode: reacquisition is neutral, then fresh
strict release dwell is required before a new closing sequence. A hand returning
already closed stays unarmed. UNKNOWN never implicitly restores an active hold.

New session/run, camera/provider/profile changes or uncertain reference-domain
changes invalidate the session reference. A stored personal template may be offered
for explicit revalidation; do not silently reuse it or identify a user/hand by
handedness score. Missing compatibility information produces explicit unavailability.

## 6. Calibration model

**Recommended first prototype:** explicit per-session release enrollment using
an operator-labeled, comfortable-apart held window. It does not require all fingers
OPEN or physical contact calibration. Capture actual geometry, dispersion and
provenance, then independently rearm. Never treat the first observed hand, largest
distance so far or an already closed hand as a trustworthy released reference.

A release reference is required for relative operation. A two-endpoint personal
calibration is optional. Persistent per-user storage is optional and explicit;
no enrollment data are saved by default. Saved templates require session revalidation.

"No calibration" must have an honest meaning: use unchanged legacy v1.0, or an
explicitly selected compatible template after verified release. It cannot mean
silently guessing a reference. Automatic reference enrollment is deferred until
its independent trustworthy-release bootstrap is designed and validated.

## 7. Validation diagnostics

Record frame/run/source identity, revision/model/profile hashes, geometry validity,
tracking status, filtered tip and palm reference coordinates, numerator/denominator,
reference ID/method/status, measured noise, unclipped relative closure, release-anchor
progress, history age, every predicate's pass/fail/unavailable reason, state,
armed/waiting flags, dwell start/elapsed/cancel reasons, cycle/transition/reset IDs.
Log reference capture/change/reset explicitly so unexpected anchor resets are visible.

For future opt-in physical validation, mark intended close/open and non-intent
intervals; store marker timing uncertainty. Use synchronized local images when
authorized. Evaluate comfortable natural movement, not a mandatory skin-contact
endpoint. Preserve tracking interruptions, missed entries and false entries as
failures where applicable; ambiguous labels remain explicitly unscored.

## 8. Later prototype usability gate

These are **proposed engineering acceptance targets**, not measured results,
implemented thresholds, universal guarantees or G7 research requirements. Freeze
the accepted targets and trial definitions before later validation; no validation
or threshold choice starts in A5.5.

| Metric | Definition | Proposed gate |
| --- | --- | --- |
| Intentional pinch success | Confirmed intentional attempts yielding exactly one entry within the declared response window and a supported intended hold / all confirmed attempts | >=90% |
| False activation rate | Unintended entry events / valid tracked minutes in labeled non-intent activity; also report events/negative episodes and total wall-clock exposure | <=0.1 per tracked minute |
| Release/rearm success | Active episodes intentionally opened, safely deactivated and ready within the declared deadline / all active episodes with an intended release | >=95% |
| Full-cycle success | Intended close/hold/open/ready cycles completed / all confirmed attempted cycles, plus next-cycle re-entry | Report separately; no missed entry omitted |
| Stuck state | Active evidence survives release/loss, or readiness never returns despite sustained eligible release within its deadline | 0 |
| Safe loss/reacquisition | UNKNOWN/loss/reset never active; no old episode or closed-hand reacquisition enters before fresh rearm | 0 violations |

Proposed minimum for interpreting the rates: at least 20 confirmed intentional
cycles and 10 valid tracked minutes of non-intent exposure per tested profile/user,
with normal-light medium/near distance, frontal/moderate side views and comfortable
finger configurations represented. Report each condition and counts; pooled success
must not conceal a systematically failing condition. Small counts remain limited
prototype evidence. Latency windows/deadlines and tracking coverage must be reported
and agreed before testing, not retroactively selected to turn failures into success.

Negative activity includes neutral holds, pointing, translation, wrist rotation,
unrelated finger movement and a static close hand without a qualified entry sequence.
"Near but not touching" alone is not a negative label. No entry after loss/UNKNOWN
or duplicate entry during one hold is allowed, regardless of aggregate success rate.
Label/tracking failures are recorded honestly; tracking loss during a confirmed
intentional attempt counts against usability while its neutralization can pass safety.

## 9. Legacy fallback and smallest implementation unit

Existing LEGACY and OBSERVE_FULL_HAND modes retain the same GestureEngine output.
No full-hand command ownership is introduced. Missing reference, unsupported
geometry or rejected enrollment leave the proposed branch observation-only and
legacy usable. Any eventual control mode must be explicitly selected with one
command owner; no automatic per-frame blending/fallback that could duplicate events.

Smallest next unit, only when implementation is explicitly requested:

1. Add immutable reference/relative-observation contracts under `full_hand/`.
2. Add a pure builder for an explicitly labeled release window and a pure relative
   closure evaluator over A2 geometry; no tracker, runtime injection or commands.
3. Test missing/unstable/degenerate references, exact metric formulas and boundaries,
   frame/reference identity, immutability, mirror/aspect/similarity invariance,
   denominator/domain incompatibility, reset invalidation and frozen-reference behavior.

Suggested later files: `intent_pinch_contracts.py`, `pinch_reference.py`,
`relative_closure.py` and corresponding focused tests. A separate later unit can
add the timestamped state machine with synthetic replay tests for dwell, band,
rearm, UNKNOWN, loss/reacquisition and duplicate transitions. Physical usability
and any command bridge remain separate gates. Do not modify A3/A4 to implement
this design implicitly; no FIST/two-hand/G9 work is included.

## Design handoff

Only this proposal document is added by A5.5. The pending P1f report remains
untouched. No implementation, runtime, webcam or pytest execution is claimed;
documentation whitespace and frozen-path integrity are checked at handoff.
No stage, commit, push or tag.
