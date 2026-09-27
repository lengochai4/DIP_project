# 03 — Algorithm and Experiments

**Specification set:** Canonical v1.2  
**Status:** Normative for processing behavior, equations, baselines, minimum experiment design/metrics, and optional statistical methods when used

## 1. Processing sequence

For each valid frame, the baseline Core processes:

```text
validate frame/timestamp
→ choose ROI state/geometry
→ measure ROI illumination
→ choose CLAHE or bypass
→ composite processed ROI into unchanged full-size frame
→ explicit BGR→RGB provider conversion
→ landmark observation + validation
→ raw/fixed/adaptive temporal path
→ tracking-loss/reacquisition handling
→ gesture mapping
→ TrackingFrame + InteractionState + logs
```

The public data semantics are defined in `02_ARCHITECTURE_AND_CONTRACTS.md`.

## 2. Frame timing

For ordinary filter updates:

```text
dt > 0
timestamp finite
inputs finite
```

`dt` is computed from the current and previous accepted filter-update timestamps.

If `dt <= 0`, non-finite, or greater than configured `reset_gap_s`, the sample is a discontinuity: do not perform an ordinary continuous update; follow the reset/reinitialization behavior in Section 9 and log the event.

## 3. ROI management

### 3.1 ROI state machine

Required states:

```text
SEARCHING
  full-frame ROI
  ↓ valid hand bbox
TRACKING
  prior valid bbox + ratio padding
  ↓ temporary loss
COASTING
  expanded last valid ROI for a bounded number of frames
  ↓ timeout / unusable ROI
SEARCHING
```

Requirements:

- ROI uses full-frame pixel coordinates;
- ROI MUST be clamped to frame bounds;
- width/height MUST remain positive and satisfy configured minimum dimensions;
- padding SHOULD be ratio-based rather than a fixed pixel assumption;
- invalid bbox/ROI falls back safely to SEARCHING/full frame.

### 3.2 Detector-geometry baseline

For the course baseline, ROI preprocessing MUST NOT change detector frame size or normalized-coordinate semantics.

Required flow:

```text
select ROI in full frame
→ preprocess only ROI
→ paste ROI back into same-size full frame
→ run landmark provider on full-size frame
```

ROI-only detector inference is FUTURE unless separately specified, coordinate-remapped, tested, and evaluated.

## 4. Illumination assessment

Convert the selected BGR ROI to HSV and analyze the `V` channel.

Required descriptors:


a. mean:

\[
\mu_V = mean(V)
\]

b. standard deviation:

\[
\sigma_V = std(V)
\]

c. percentiles:

\[
P_{10}(V),\quad P_{90}(V)
\]

d. robust range:

\[
C_V=P_{90}(V)-P_{10}(V)
\]

Required classification states:

```text
NORMAL
LOW_LIGHT
LOW_CONTRAST
DIFFICULT
```

Exact thresholds are tunable configuration parameters, not universal facts.

### 4.1 Temporal stability

The illumination decision MUST avoid uncontrolled on/off chatter around one threshold. Use at least one of:

- EMA-smoothed descriptors;
- separate enter/exit hysteresis thresholds.

If hysteresis is used, threshold ordering MUST make exit from a difficult state require a sufficiently improved condition rather than the same noisy boundary.

### 4.2 Baseline illumination-state decision

The course baseline uses two EMA-smoothed decision signals:

\[
\bar{\mu}_{V,t}
=
\alpha \mu_{V,t}
+
(1-\alpha)\bar{\mu}_{V,t-1}
\]

and

\[
\bar{C}_{V,t}
=
\alpha C_{V,t}
+
(1-\alpha)\bar{C}_{V,t-1}
\]

where:

```text
0 < ema_alpha <= 1
C_V = P90(V) - P10(V)
```
The first valid sample initializes each EMA directly from the current
measurement; it is not blended with an invented zero state.
The baseline uses separate enter/exit thresholds:
```
low-light enters when:
    EMA mean V < low_light_enter_v

low-light exits when:
    EMA mean V >= low_light_exit_v

low-contrast enters when:
    EMA robust range V < low_contrast_enter_range_v

low-contrast exits when:
    EMA robust range V >= low_contrast_exit_range_v
```
Required threshold ordering:
```0 <= low_light_enter_v < low_light_exit_v <= 255
0 <= low_contrast_enter_range_v
  < low_contrast_exit_range_v <= 255
```
The stabilized state is:
low_light  low_contrast  state
false      false         NORMAL
true       false         LOW_LIGHT
false      true          LOW_CONTRAST
true       true          DIFFICULT

For the adaptive preprocessing baseline:
NORMAL        -> enhancement inactive
LOW_LIGHT     -> enhancement active
LOW_CONTRAST  -> enhancement active
DIFFICULT     -> enhancement active

IlluminationMetrics stores the current raw ROI descriptors while its
state and enhancement_active fields are produced by the stabilized
EMA/hysteresis decision above.
std_v, p10_v, and p90_v remain required measured diagnostics but
are not additional classification thresholds in the course baseline.
Default threshold values are engineering starting parameters stored in
configuration. They MUST NOT be presented as universal illumination
boundaries or as measured project results.

Rule này rất rõ và dễ reproducible:

```text
mean V       → brightness
robust range → usable contrast
```

## 5. Adaptive CLAHE

Required baseline path:

```text
BGR ROI
→ HSV
→ V channel
→ CLAHE when policy activates enhancement
→ HSV reconstruction
→ BGR ROI
→ paste into unchanged full-size BGR frame
```
Policy resolution is:

```text
policy = bypass
    -> CLAHE not applied

policy = always
    -> CLAHE applied

policy = adaptive
    -> CLAHE applied when stabilized illumination state != NORMAL
```

For final/logged IlluminationMetrics,
enhancement_active means CLAHE was actually applied after policy
resolution.
The illumination decision stage may request adaptive enhancement from
the stabilized state, but AdaptivePreprocessor is the owner of the
actual policy resolution.
Only post-preprocessor IlluminationMetrics should be serialized as the
final per-frame illumination diagnostics.


Required tunable parameters:

```text
policy: adaptive | always | bypass
clip_limit > 0
tile_grid_size positive integer pair
```

`adaptive` uses the illumination state. `bypass` leaves the image semantically unenhanced.

Lab/L-channel CLAHE is an optional future/research ablation and MUST NOT replace the course baseline silently.

## 6. Landmark-provider and measurement-quality behavior

The baseline provider is MediaPipe Hand Landmarker through the project adapter.

This algorithm layer consumes `LandmarkObservation` and `MeasurementQuality` exactly as defined in `02_ARCHITECTURE_AND_CONTRACTS.md`; it MUST NOT reinterpret provider metadata or construct a substitute quality value.

If `MeasurementQuality.valid == false`, quality-aware adaptation is disabled for that update/configuration and the adaptive filter follows its non-quality path in Section 8.

## 7. Canonical fixed 1-Euro baseline

### 7.1 Canonical scalar structure

The required fixed baseline follows the canonical derivative-filtered 1-Euro structure.

For scalar input `x_t` with update interval `dt`:

\[
rate = \frac{1}{\Delta t}
\]

On the first sample, initialize filter state deterministically and use derivative `0`.

Otherwise derive:

\[
d_t=(x_t-\hat{x}_{t-1})\,rate
\]

where \(\hat{x}_{t-1}\) is the previous output stored by the signal low-pass filter.

Derivative low-pass cutoff is fixed at `d_cutoff`:

\[
\tau_d=\frac{1}{2\pi f_d}
\]

\[
\alpha_d=\frac{1}{1+\tau_d/\Delta t}
\]

\[
\hat d_t=\alpha_d d_t+(1-\alpha_d)\hat d_{t-1}
\]

Signal cutoff:

\[
f_c=f_{min}+\beta|\hat d_t|
\]

Signal low-pass coefficient:

\[
\tau=\frac{1}{2\pi f_c}
\]

\[
\alpha=\frac{1}{1+\tau/\Delta t}
\]

Filtered output:

\[
\hat{x}_t=\alpha x_t+(1-\alpha)\hat{x}_{t-1}
\]

The fixed baseline MUST use constant configured `f_min`, `beta`, and `d_cutoff`. A filter omitting derivative low-pass filtering MUST NOT be named the canonical fixed 1-Euro baseline.

### 7.1.1 Canonical source and project integration boundary

The canonical fixed 1-Euro scalar baseline is based on:

Casiez, G., Roussel, N., & Vogel, D. (2012).
*1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input
in Interactive Systems.* CHI 2012, 2527–2530.
DOI: 10.1145/2207676.2208639.

Appendix A is the normative algorithm reference for the course
baseline.

Canonical scalar terminology:

```text
x_i       current raw measurement
x_hat_i   filtered output
dx_i      raw derivative estimate
dx_hat_i  low-pass filtered derivative
dt_i      accepted timestamp interval
f_c_i     adaptive signal cutoff
```
For an ordinary update:
dx_i = (x_i - x_hat_{i-1}) / dt_i
dx_hat_i = LPF(dx_i, d_cutoff)
f_c_i = f_min + beta * abs(dx_hat_i)
x_hat_i = LPF(x_i, f_c_i)

The previous term in the derivative is the previous filtered signal
output, not the previous raw measurement.
On the first accepted sample after initialization or reset:
dx_i = 0
x_hat_i initializes from x_i

The project derives:
dt_i = timestamp_i - timestamp_previous_accepted

rather than assuming a requested camera FPS.
The following behaviors are project integration contracts and MUST NOT
be presented as contributions of the original 1-Euro paper:
- tracking-loss handling;
- timestamp-discontinuity detection;
- reset-gap behavior;
- reacquisition initialization;
- landmark-vector/shared-speed application;
- project logging and diagnostics.
The project scalar F1 implementation MUST remain numerically consistent
with the Appendix A structure before project-specific vectorization and
runtime integration are applied.
The authors' reference implementation and published ground-truth data
MAY be used as additional regression evidence. They do not replace the
project's explicit unit tests for equations, timestamps, initialization,
reset, and loss behavior.

### 7.2 Project vectorization

The canonical algorithm above is scalar. For landmark vectors, the project baseline defines this application rule:

1. derivative-filter each configured coordinate component;
2. compute a shared speed from the filtered derivative vector;
3. derive one shared signal cutoff from that speed;
4. filter each coordinate using that shared cutoff.

For interaction speed, x/y normalized-frame motion is the default. Including model-relative z requires an explicit justification because its scale/semantics differ.

This vector application is a project design choice; it is not claimed as part of the original canonical scalar algorithm.

## 8. Proposed bounded adaptive 1-Euro

The proposed method extends Section 7 without removing derivative filtering.

### 8.1 Velocity-dependent beta — required proposed behavior

Let `v_t` be the norm of the configured filtered derivative vector:

\[
v_t=\|\hat{\mathbf d}_t\|
\]

Optional configured safety cap:

\[
v_t \leftarrow min(v_t, v_{max})
\]

Adaptive beta:

\[
\beta(v_t)=clip(\beta_{base}+k_vv_t,\beta_{min},\beta_{max})
\]

Required invariants:

```text
0 <= beta_min <= beta_base <= beta_max
k_v >= 0
```

### 8.2 Quality-dependent minimum cutoff — optional

Only if a valid documented quality \(Q_t\in[0,1]\) exists and quality adaptation is explicitly enabled:

\[
f_{min}(Q_t)=f_{low}+Q_t(f_{high}-f_{low})
\]

with:

```text
0 < f_low <= f_high
```

Intended monotonic semantics:

```text
lower valid quality → lower minimum cutoff → stronger smoothing
higher valid quality → higher minimum cutoff → greater responsiveness
```

If quality is unavailable or disabled:

\[
f_{min}=f_{base}
\]

No synthetic `Q_t` may be inserted.

### 8.3 Bounded final cutoff

Candidate cutoff:

\[
f_c^*=f_{min}+\beta(v_t)v_t
\]

Implemented cutoff:

\[
f_c=clip(f_c^*, f_{c,min}, f_{c,max})
\]

with:

```text
0 < f_c,min < f_c,max
```

Then calculate signal `alpha` and filtered output using the same low-pass equations as Section 7.

### 8.4 Numerical safety

For any accepted update:

```text
dt > 0
all input/state values finite
d_cutoff > 0
min cutoff > 0
0 < signal alpha <= 1
0 < derivative alpha <= 1
finite derivative
finite speed
finite cutoff
finite output
```

Invalid values trigger explicit failure/reset handling; they are not silently converted into plausible measurements.

## 9. Tracking loss, discontinuity, and reacquisition

### 9.1 Invalid/no-hand observation

When no usable hand measurement exists:

- do not update filters with zeros;
- do not generate motion deltas from absent data;
- mark interaction invalid;
- advance ROI loss state;
- preserve/log tracking status.

### 9.2 Short loss

During a configured short gap, filter state MAY be retained, but no fake measurement update occurs.

### 9.3 Long loss or timestamp discontinuity

After the configured loss/reset condition, reset the temporal filter and gesture state.

### 9.4 First valid reacquired frame after reset

Initialize filtered state from the current valid measurement and emit a neutral interaction transition:

```text
rotation_delta = (0, 0)
scale_delta = 0
pinch_active = false until gesture state is re-established
interaction_valid = false or neutral on initialization frame
```

This prevents jump impulses and stuck gestures.

## 10. Gesture mapping

### 10.1 Rotation

Use filtered index-fingertip x/y displacement:

\[
\Delta x=x_t-x_{t-1},\qquad \Delta y=y_t-y_{t-1}
\]

Apply configured deadzone, gain, and maximum-delta clamp before emitting yaw/pitch-style rotation deltas.

Quaternion composition MAY be used by the extension for stable 3D rotation accumulation.

### 10.2 Scale-normalized pinch

Thumb-index 2D distance:

\[
d_p=\|p_{index}-p_{thumb}\|_{xy}
\]

Define documented hand scale from a configured stable landmark pair/palm measure:

\[
r_p=\frac{d_p}{max(s_h,\epsilon)}
\]

Use `r_p` rather than a fixed absolute image-normalized distance.

Hysteresis is required:

```text
inactive → active when r_p < pinch_on
active   → inactive when r_p > pinch_off
pinch_on < pinch_off
```

Tracking loss invalidates/releases pinch safely.

### 10.3 Render selection — optional

If implemented, selection uses a **render-view picking ray**:

```text
filtered x/y
→ viewport
→ NDC
→ inverse projection/view
→ renderer world ray
→ ray-object/plane intersection
```

It MUST NOT be described as physical touch sensing or metric camera-ray depth reconstruction. It is optional if it threatens completion of core DIP experiments.

## 11. Required filter/config invariants

Configuration validation MUST enforce at least:

```text
d_cutoff > 0
fixed f_min > 0
fixed beta >= 0
adaptive f_base > 0
0 <= beta_min <= beta_base <= beta_max
velocity_gain >= 0
velocity_max > 0 when enabled
0 < final_cutoff_min < final_cutoff_max
0 < quality_low_cutoff <= quality_high_cutoff when quality branch enabled
reset_gap_s > 0
pinch_on < pinch_off
hand-scale denominator protected by epsilon/minimum validity
```

Quality adaptation MUST fail validation or remain disabled when no accepted quality source is configured.

# Part II — Experiments and Evaluation

## 12. Evaluation principles

- All quantitative claims come from recorded measurements.
- Do not define a desired numerical result and later present it as observed evidence.
- Use the smallest credible set of experiments that answers RQ1–RQ3.
- Do not select only favorable time segments after viewing outcomes.
- Keep raw run artifacts immutable; analyses create derived outputs.

## 13. Required baselines

### Temporal filtering

```text
F0 — Raw landmarks
F1 — Canonical fixed 1-Euro
F2 — Proposed bounded adaptive 1-Euro
```

If a quality-aware adaptive branch is evaluated, it is labeled separately with the exact quality source and is not allowed to blur the F2 definition used for primary comparison.

### Preprocessing

```text
P0 — Unprocessed input/full frame
P1 — Adaptive ROI CLAHE composited into unchanged full frame
```

## 14. Pairing and replay rule

For algorithm comparisons, the preferred design is:

```text
one recorded source sequence
        ↓
ReplayRuntime
  ↙      ↓      ↘
 F0      F1      F2
```

and similarly for P0/P1.

The same source frames/timestamps SHOULD be used for paired methods whenever possible. This reduces motion/content differences between conditions.

Live-camera tests are still appropriate for demo behavior and live operational performance, but they are not a substitute for deterministic paired replay when method comparison is the goal.

## 15. Analysis unit and optional inference

Adjacent frames are temporally correlated. They MUST NOT automatically be counted as independent statistical samples.

For the required course evaluation, descriptive comparison is sufficient. Metrics SHOULD be summarized per predefined trial/run or per deterministic replay sequence so that compared methods use the same underlying input.

No inferential hypothesis test is required by the course baseline.

If the team later chooses to perform inferential statistics, the default inferential unit is:

```text
one trial/run/session → one primary metric value per compared method
```

Any paired test MUST operate on matched trial-level values unless a more advanced time-series method is explicitly justified.

## 16. Experiment A — Temporal stability and responsiveness

### A1. Static jitter — required

Procedure:

1. warm up camera/pipeline;
2. record an approximately stationary fingertip trial for a predefined interval;
3. replay the identical source through F0/F1/F2;
4. analyze a predefined window according to documented exclusion rules.

Required recorded data:

- timestamps;
- raw/filtered landmarks;
- tracking status;
- filter diagnostics.

Before final comparison, choose **one primary jitter metric** and use it consistently across F0/F1/F2. Recommended simple options are:

- radial RMS jitter; or
- a predefined x/y standard-deviation aggregate.

Additional jitter/validity metrics are OPTIONAL.

Radial RMS jitter around trial mean, when selected, is:

\[
J_{RMS}=\sqrt{\frac{1}{N}\sum_i[(x_i-\bar{x})^2+(y_i-\bar{y})^2]}
\]

No required percentage reduction is specified. The measured result may favor, tie, or disfavor the proposed method.

### A2. Dynamic responsiveness — required, one primary metric only

RQ2 is not answered by static jitter alone.

Use at least one known/repeatable dynamic source:

```text
synthetic step/ramp/sine/known trajectory + noise
and/or
recorded real motion with predefined event/trajectory analysis
```

Choose **one primary responsiveness metric** before final comparison. Simple acceptable choices include:

- RMSE to a known synthetic reference;
- transition/threshold delay;
- cross-correlation lag;
- trajectory deviation.

Additional responsiveness metrics are OPTIONAL.

Interpretation MUST discuss the observed jitter-vs-responsiveness trade-off. The specification does not define a required latency value, required percentage improvement, or universal winner.

## 17. Experiment B — Illumination robustness — required

Required conditions:

1. normal illumination;
2. challenging low-light or low-contrast illumination.

Optional condition:

3. backlight/high dynamic contrast.

Compare P0 vs P1 on matched source content when possible.

For the course baseline, choose **one primary tracking/stability outcome** before final comparison, for example:

- valid hand-observation rate; or
- valid landmark rate; or
- landmark jitter/stability under the lighting condition.

Illumination descriptors/state MUST be recorded so the image-processing condition is documented.

The following are OPTIONAL descriptive diagnostics:

- preprocessing time;
- failure/loss frequency;
- additional tracking metrics.

A per-frame quality metric may be reported only if it satisfies the `MeasurementQuality` contract owned by `02_ARCHITECTURE_AND_CONTRACTS.md`.

No required detection-rate, accuracy, or percentage-improvement target is specified.

### 17.1 Lighting documentation

If a lux meter is available, measured lux MAY be recorded. A lux meter is not required. If lux is unavailable, describe the setup honestly: room/lamp/backlight condition, camera-subject geometry, and relevant environmental factors.

### 17.2 Camera auto controls

If stable manual controls are supported, exposure/white balance MAY be locked per trial. Otherwise allow automatic controls to settle and record that auto controls remained enabled; treat this as a limitation.

## 18. Optional descriptive software-processing diagnostics

Software-processing timing is useful engineering telemetry but is **not a required performance claim, success threshold, or research contribution** for the course baseline.

The existing timing fields may be logged:

```text
preprocess_ms
tracking_ms
filtering_ms
gesture_ms
compute_total_ms
```

If timing is reported:

- use a monotonic high-resolution timer such as `time.perf_counter()`;
- keep disk logging outside stage timing when practical;
- clearly distinguish configured/requested FPS from observed behavior;
- describe the measurement as software-processing cost, not physical sensor-to-photon latency;
- report only actually observed values;
- do not introduce a required FPS, latency, P90/P95, throughput, or other numerical target after the fact.

Detailed percentile/throughput analysis is OPTIONAL and belongs to an extended engineering/research evaluation, not the minimum course evidence.

## 19. Optional ablation

Ablation is useful for stronger research evidence but is not mandatory for the minimum final-term project.

If performed, recommended configurations are:

```text
D0 Raw / no adaptive preprocessing
D1 Adaptive CLAHE only
D2 Fixed 1-Euro only
D3 Adaptive CLAHE + Fixed 1-Euro
D4 Adaptive CLAHE + Adaptive 1-Euro
```

The purpose is to separate image-preprocessing contribution from temporal-filter contribution. If omitted, the required F0/F1/F2 and P0/P1 comparisons still remain.

## 20. Trial plan and exclusion policy

Before final data collection, define:

```text
experiment ID
conditions
number of trials/runs actually planned
trial duration/window
warmup rule
exclusion rule
primary metric
planned comparisons
```

This specification does not prescribe a numerical minimum trial count. The report MUST state the actual number used and acknowledge limitations of small samples.

Exclusions SHOULD be defined before inspecting final results.

Valid examples: startup warmup, corrupted source, invalid timestamps, complete camera failure.

Invalid example: removing a noisy segment because it makes the proposed method look worse.

## 21. Descriptive analysis required; inferential statistics optional

The minimum final-term analysis is descriptive and evidence-based.

Required:

- report the actual number of trials/runs used;
- report the selected primary metric for each required experiment;
- compare methods on matched input where applicable;
- show observed values without inventing target thresholds;
- discuss limitations and practical behavior.

Inferential statistics are OPTIONAL. If the team chooses to use them, it MUST use an appropriate trial/run-level analysis and document the method. Examples include paired t-test or Wilcoxon signed-rank when justified.

Only when inferential statistics are actually performed should the report consider items such as:

```text
p-value
confidence interval
effect size
multiple-comparison correction
```

None of those items is required by the course baseline, and they MUST NOT be fabricated or included merely to make the report look more scientific.

## 22. Reproducibility record

Every final required experiment MUST retain enough information to reproduce/identify the run:

- run/experiment/trial identifiers;
- timestamp/date;
- source sequence identity;
- resolved config + config hash;
- spec/code revision;
- log schema version;
- Python/key dependency versions;
- provider/model filename + checksum;
- hardware/OS;
- camera/backend and requested/observed properties when applicable;
- lighting condition and auto-exposure/white-balance status when known;
- analysis code revision/version.

## 23. Required result assets

Minimum final outputs:

1. raw vs fixed vs adaptive trajectory/time-series example;
2. one primary static-jitter comparison for F0/F1/F2;
3. one primary responsiveness characterization for F0/F1/F2;
4. one P0 vs P1 illumination robustness comparison using the predefined primary outcome;
5. at least one DIP-focused visual example showing original ROI, V/histogram, CLAHE result/histogram, and reconstructed ROI.

Optional outputs include:

- software-stage timing breakdown;
- percentile/throughput diagnostics;
- ablation summary;
- inferential-statistics tables;
- additional secondary metrics.

An image-domain contrast change MUST NOT be described as tracking improvement unless downstream tracking metrics support it.

## 24. Report structure

Recommended final report:

```text
1 Introduction
  problem, objective, scope, RQs, contribution boundary
2 Theoretical Background
  ROI, HSV, CLAHE, external landmark detection, canonical 1-Euro
3 System Design
  architecture, contracts, runtime split, failure behavior
4 Proposed Method
  ROI/illumination/CLAHE, fixed baseline, adaptive filter, gestures
5 Experimental Methodology
  setup, baselines, primary metrics, pairing, reproducibility; optional statistics if used
6 Results
  measured outputs only
7 Discussion
  trade-offs, failures, limitations, threats to validity, RQ interpretation
8 Conclusion
  only claims supported by results
```

## 25. Research upgrade path

After the course prototype is validated, a research-paper branch MAY strengthen evidence through larger controlled datasets, more sessions/participants where relevant, stronger ablation, fixed/preregistered analysis, and broader failure analysis.

Adding more prose without stronger evidence is not a research upgrade.
