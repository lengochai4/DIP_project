# v1.1 A5.6 — Relative Intentional PINCH Foundation

Additive Extension foundation implementing the first unit of the frozen
[A5.5 proposal](V11_A55_INTENTIONAL_PINCH_CONTRACT.md). This is pure geometry
and explicit enrollment/lifecycle data, not a temporal state machine, pose
classifier, runtime integration, or command implementation. No physical values
have been chosen and no new physical validation is claimed.

## Contracts and entry points

`extensions/stem3d/full_hand/intent_pinch_contracts.py` provides frozen, slotted
contracts with typed immutable collections:

- `ReferenceScope`: session/run, camera/provider/profile, coordinate domain and
  reset identity. These are caller-supplied provenance, not hand recognition.
- `ReleaseSample` and `ConfirmedReleaseWindow`: A2 geometry, explicit tracking
  status/filter reset flags, comfortable-apart confirmation ID and projected
  comparison confirmation. No OPEN/POINT/FIST requirement or skin-contact label.
- `ReleaseReferencePolicy`: required enrollment parameters, with no defaults.
- `ReleaseReference`: versioned, frozen distance/dispersion/palm summary, source
  frame/time identities and policy; ACTIVE, UNVERIFIED or INVALIDATED metadata.
- `ReferenceBuildResult`: reference or explicit rejection reasons/predicates.
- `RelativeClosureThresholds`: required bounds `0 < exit < enter < 1`.
- `RelativeClosureObservation`: actual frame identity, reference lifecycle result,
  geometry/reference validity, metric components, extent zone, independent
  evidence flags and diagnostic reasons. No active/armed/command fields.

Use direct module imports. No runtime/observer composition imports or calls these
new modules. Existing baseline and rejected experimental scalar profiles are
unchanged; no new YAML/default/CLI profile is added.

## Exact enrollment rules

`pinch_reference.build_release_reference(window, policy, reference_id=..., version=...)`
returns an immutable result. All samples are used, or the whole window is rejected;
there is no outlier trimming, automatic bootstrap, first-hand guess or rolling maximum.

Required checks:

1. Explicit confirmed comfortable-apart label and CONFIRMED projected comparison.
2. At least configured `min_samples` (policy requires >=2); source timestamp span
   >= `min_duration_s`; strict increasing frame IDs and timestamps, with each gap
   <= `max_sample_gap_s`. Frame-ID skips are allowed; order/gap are not guessed.
3. Every A2 hand is valid, palm/distance available, tracking VALID (not REACQUIRED),
   no filter reset, matching run scope, finite positive release distance/denominator.
4. `r = median(d_i)`, `MAD = median(abs(d_i-r))`, `dev = max(abs(d_i-r))`.
   Accept `MAD/r <= max_relative_mad` and `dev/r <= max_relative_deviation`.
   The maximum-deviation check catches a single outlier even when MAD is zero.
5. Enrollment denominator ratio `max(p_i)/min(p_i) <= max_palm_width_ratio`.
6. Measured relative noise allowance `noise_multiplier * dev/r < 1`, with
   multiplier >=1. The release span must exceed its noise allowance. No epsilon,
   repaired span or physical confidence is fabricated.

All policy values are explicit arguments; numerical fixture values in tests are
synthetic only. The even-sample median avoids overflow from adding large finite
positive values. Store source identities, measured dispersion, denominator
min/median/max, confirmation ID, version and scope with the result.

## Relative evidence

`relative_closure.evaluate_relative_closure(...)` uses A2's aspect-corrected
thumb-index distance `d = n/p`, where x is scaled by actual W/H and p is MCP 5–17
palm width. It evaluates exactly:

```text
relative_closure = (reference_distance - current_distance) / reference_distance
```

Decision values are not clipped: zero is the enrolled separation, negative is
wider, positive is closer. Zero current distance is valid geometry; zero reference
distance is not. Numerator `n = d*p` is reconstructed from A2 and labeled as such;
the API does not claim to retain raw fingertip coordinates.

| Evidence | Predicate | Meaning at this gate |
| --- | --- | --- |
| RELEASED | c < exit | Strict geometric release, no confirmed rearm/dwell |
| CLOSING | c > measured relative noise allowance | Noise-separated positive extent from reference, not observed velocity/history |
| BAND | exit <= c <= enter | Inclusive hysteresis band; never release evidence |
| ENTRY | c > enter AND CLOSING | Enter extent evidence; no stable activation |
| UNKNOWN | Unusable geometry/reference/domain/lifecycle | Closure/evidence unavailable (`None`), with reasons |

Extent zones are RELEASED/BAND/ENTRY; CLOSING is an independent evidence flag and
can overlap a zone. ENTRY zone describes scalar extent; its `entry` predicate can
still fail the noise check. A later tracker must qualify a fresh release-to-close
sequence, bounded motion history, rearm and dwell. A static closed hand may have
ENTRY geometry but this foundation cannot activate it or authorize any action.

## Freeze and lifecycle boundary

Valid evaluations retain the exact same reference object and never adjust its
distance, noise, denominator summary, window or identity. Explicit refresh uses
a newly confirmed window and a new caller-assigned ID/version. No personal
closed endpoint or second formula is implemented.

`invalidate_reference(ref, event)` returns a neutral immutable copy. Loss, invalid
geometry and reacquisition may retain UNVERIFIED metadata; reset/run/session/
domain/discontinuity/gap events INVALIDATE. Already INVALIDATED never downgrades
to UNVERIFIED. None remains None. No invalidation or later valid frame can rearm
or silently restore the reference. Re-enrollment is the only activation path in
this unit; retained-reference revalidation/rearm belongs to a later explicit gate.

The evaluator checks actual geometry run/scope, reference scope, ordinary VALID
tracking, filter reset, explicit comparison and frames after enrollment. It
invalidates on failure and returns UNKNOWN. **Callers must thread the returned
`observation.reference` forward**; a pure function cannot revoke other copies of
an immutable object. No reference manager or timestamp history is introduced.
Long gaps and duplicate/out-of-order frames after enrollment need explicit
`ReferenceEvent` input from a future lifecycle owner; only ordering against the
enrollment endpoint can be checked without such history.

A2's current geometry contract does not carry enough palm shape/orientation
information to independently establish projection compatibility. Caller-supplied
`ProjectionCompatibility.CONFIRMED` attests comparability, not tracking confidence.
UNCONFIRMED/INCOMPATIBLE fails closed. Automatic perspective-change detection is
not implemented or claimed. Confirmed comparable uniform image scaling,
translation, mirror/in-plane rotation and aspect-corrected geometry preserve the
ratio; out-of-plane changes are not modeled as metric depth.

## Compatibility and next unit

Missing/rejected/inactive reference keeps the new branch UNKNOWN. Legacy v1.0
continues owning all application output; no command owner switch or per-frame
fallback mixing is introduced. No A3/A4/FIST, InteractionState, scene/router/UI,
Core/G7, evidence, experiments, sensitivity or G9 changes.

Change record: additive Extension contracts/math only; canonical sections unchanged;
experimental/G7 impact none; existing results not invalidated. Synthetic tests
cover enrollment, dispersion/outliers, strict boundaries, numerical failures,
invalidation, frozen reference, A2 similarities/aspect, deterministic replay,
input immutability and exact legacy InteractionState parity.

Smallest next unit: an independent timestamped intentional-PINCH tracker over
these evidence contracts, adding fresh closing history, release/rearm, dwell,
band rules and neutral reset/reacquisition tests. No runtime or commands should
be added to that unit. Begin only with separate authorization.

## Executed validation

- `.venv\Scripts\python.exe -m pytest -q tests/extensions/full_hand`: **609 passed**
  (including 120 new A5.6 synthetic cases).
- `.venv\Scripts\python.exe -m pytest -q`: **1164 passed**.
- `.venv\Scripts\python.exe -m compileall extensions/stem3d`: exit 0.
- `git diff --check` and separate whitespace checks on new untracked files: passed.
- Frozen `src/`, `FINAL_REPORT.md`, `submission/evidence/` and `experiments/final/`
  match `g7-final`; its commit remains `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- G9 source paths absent; deferred stash retained. No physical run, threshold
  tuning, full-hand commands, stage, commit, push or tag.

Five A5.6 files are added: the three modules described above, synthetic
`tests/extensions/full_hand/test_relative_intent_pinch.py`, and this handoff.
The pre-existing untracked P1f collection report remains untouched. A5.5 stays
unchanged. No implementation blocker; projected-comparison confirmation and
lifecycle history remain explicit caller responsibilities until later gates.
