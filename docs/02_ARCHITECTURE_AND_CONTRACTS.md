# 02 — Architecture and Contracts

**Specification set:** Canonical v1.2  
**Status:** Normative for module boundaries, public semantics, and runtime/data contracts

## 1. Architectural goals

The system MUST be:

- small enough for a final-term project;
- modular enough to test without a physical webcam or renderer;
- deterministic enough for paired experiments;
- explicit enough for a new human or AI contributor to implement correctly;
- replaceable at external-provider boundaries;
- free of unnecessary service/framework complexity.

Microservices, distributed backends, plugin marketplaces, and dependency-injection frameworks are not required.

## 2. Logical pipeline

```text
FrameSource
   ↓
FramePacket
   ↓
ROIManager
   ↓
IlluminationAnalyzer
   ↓
AdaptivePreprocessor
   ↓
LandmarkProvider
   ↓
MeasurementValidator
   ↓
TemporalFilter
   ↓
TrackingFrame
   ↓
GestureEngine
   ↓
InteractionState
   ↓
3D STEM Extension
```

Cross-cutting research output:

```text
Frame/Tracking diagnostics + timings
                 ↓
             RunLogger
                 ↓
         versioned run artifacts
```

## 3. Runtime separation

### 3.1 RealtimeRuntime

Purpose: interactive demonstration and operational smoke testing.

It MUST:

- acquire webcam frames;
- assign/propagate monotonic timestamps;
- execute the same Core components used by replay;
- expose the latest `InteractionState`;
- remain safe when no hand is present or tracking is lost;
- collect diagnostics without redefining algorithm semantics.

The course baseline SHOULD use synchronous processing for clarity. Async/latest-frame execution is FUTURE unless separately specified and tested.

### 3.2 ReplayRuntime

Purpose: deterministic experiments and regression tests.

It MUST:

- consume a recorded/synthetic ordered source;
- preserve deterministic frame order;
- preserve recorded timestamps or construct them by a documented fixed rule;
- run alternative configurations on the same source sequence;
- produce the same public contracts/log artifacts as RealtimeRuntime where applicable.

Paired algorithm comparisons SHOULD use ReplayRuntime. Realtime behavior may be measured separately when the live camera itself is part of the question.

## 4. Component boundaries

### 4.1 `FrameSource`

Required implementations:

- `OpenCVCameraSource`;
- `ReplayFrameSource`.

Recommended test implementation:

- synthetic/mock source.

Acquisition MUST NOT perform hidden preprocessing.

### 4.2 `ROIManager`

Owns ROI state and geometry only. It does not call MediaPipe and does not alter pixels.

### 4.3 `IlluminationAnalyzer`

Reads ROI pixels and produces illumination descriptors/state. It does not mutate the frame.

### 4.4 `AdaptivePreprocessor`

Applies bypass/CLAHE behavior selected from configuration and illumination state. The course baseline preserves full-frame dimensions and detector geometry.

### 4.5 `LandmarkProvider`

Project-owned interface around an external hand-landmark implementation. The required course provider is a MediaPipe Hand Landmarker adapter.

Provider-specific classes MUST NOT leak into downstream Core modules.

### 4.6 `MeasurementValidator`

Converts provider output into project-domain status/contracts and decides whether a usable observation exists. It also carries optional documented measurement quality; it MUST NOT synthesize one merely because the filter can consume one.

### 4.7 `TemporalFilter`

Required modes:

```text
RAW
ONE_EURO_FIXED
ONE_EURO_ADAPTIVE
```

Algorithm semantics are defined only in `03_ALGORITHM_AND_EXPERIMENTS.md`.

### 4.8 `GestureEngine`

Consumes filtered project-domain landmarks and emits renderer-independent interaction state. It does not know MediaPipe objects or scene classes.

### 4.9 `RunLogger`

Records machine-readable run artifacts. Logger failure MUST be explicit and MUST NOT fabricate missing measurements.

### 4.10 `3D STEM Extension`

Consumes `InteractionState` only. It MAY manage renderer/scene/application behavior but MUST NOT reach into ROI, tracking, filtering, or experiment internals.

## 5. Dependency direction

Allowed conceptual direction:

```text
domain/contracts
    ↑
capture | preprocessing | tracking-provider | filtering | interaction
    ↑
pipeline/runtime

telemetry/logging reads public Core data
extension reads public InteractionState
analysis reads run artifacts
```

Forbidden examples:

```text
Core → Pygame/OpenGL scene classes
filtering → MediaPipe classes
preprocessing → renderer classes
analysis → renderer internals
extension → mutable filter/ROI internals
```

Circular dependencies across these boundaries are not allowed.

## 6. Color-space contract

The baseline image path is explicit:

```text
OpenCV capture/replay image: BGR uint8
        ↓
ROI illumination/preprocessing: explicit BGR → HSV
        ↓
CLAHE modifies V only when active
        ↓
explicit HSV → BGR
        ↓
enhanced ROI composited into unchanged full-size BGR frame
        ↓
provider adapter: explicit BGR → RGB
        ↓
MediaPipe
```

No module may silently reinterpret BGR as RGB. Any additional color space requires an explicit contract change or an optional experiment branch that does not alter the baseline semantics.

## 7. Coordinate-space contract

The project distinguishes these spaces:

```text
FRAME_PIXEL       full-frame integer pixel coordinates
FRAME_NORMALIZED  normalized image coordinates associated with full-frame geometry
VIEWPORT          renderer/window coordinates
NDC               normalized device coordinates for rendering
WORLD_RENDER      renderer world coordinates
MODEL_RELATIVE_Z  provider/model-relative landmark z semantics
```

Rules:

- ROI rectangles use `FRAME_PIXEL` coordinates.
- MediaPipe normalized x/y are converted into project landmarks tagged `FRAME_NORMALIZED`.
- Provider `z` MUST remain explicitly model-relative unless a separately specified calibration/reconstruction method exists.
- `MODEL_RELATIVE_Z` MUST NOT be labeled centimeters, physical depth, or distance from camera.
- Transformations between frame coordinates and renderer spaces MUST be explicit and testable.

## 8. Timestamp/frame contract

Within each run:

- `frame_id` MUST be a monotonically increasing integer;
- `timestamp_s` MUST be finite and monotonic for ordinary continuous updates;
- timestamps are seconds in a documented monotonic/source time domain;
- filter update interval is derived from timestamps, not assumed solely from requested camera FPS;
- requested FPS and observed timing are distinct values.

If a timestamp is invalid, non-increasing, or produces a gap beyond the configured filter-reset threshold, the sample MUST NOT be processed as an ordinary continuous filter update. Exact reset behavior belongs to `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 9. Public enums

Code names may differ, but semantics MUST map unambiguously to:

```python
ColorSpace = {BGR, RGB, HSV, GRAY}
TrackingStatus = {NO_HAND, VALID, TEMPORARY_LOSS, REACQUIRED, INVALID}
ROIState = {SEARCHING, TRACKING, COASTING}
IlluminationState = {NORMAL, LOW_LIGHT, LOW_CONTRAST, DIFFICULT}
FilterMode = {RAW, ONE_EURO_FIXED, ONE_EURO_ADAPTIVE}
QualitySource = {NONE, PROVIDER_DOCUMENTED, EXPERIMENTAL_DERIVED}
CoordinateSpace = {
    FRAME_PIXEL,
    FRAME_NORMALIZED,
    VIEWPORT,
    NDC,
    WORLD_RENDER,
    MODEL_RELATIVE_Z
}
```

`EXPERIMENTAL_DERIVED` quality is disabled by default and requires an explicit experimental definition before it may influence final course results.

## 10. Public data contracts

Python snippets are semantic examples; exact syntax is implementation detail.

### 10.1 `FramePacket`

```python
@dataclass(frozen=True)
class FramePacket:
    run_id: str
    frame_id: int
    timestamp_s: float
    image: np.ndarray
    color_space: ColorSpace
    source_name: str
```

Invariants: non-empty image, finite timestamp, correct explicit color space, increasing frame ID.

### 10.2 `ROI`

```python
@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    width: int
    height: int
    state: ROIState
```

ROI coordinates are full-frame pixels, clamped to valid frame bounds, with positive dimensions.

### 10.3 `IlluminationMetrics`

```python
@dataclass(frozen=True)
class IlluminationMetrics:
    mean_v: float
    std_v: float
    p10_v: float
    p90_v: float
    robust_range_v: float
    state: IlluminationState
    enhancement_active: bool
```

### 10.4 `Landmark`

```python
@dataclass(frozen=True)
class Landmark:
    index: int
    x: float
    y: float
    z: float
    coordinate_space: CoordinateSpace
```

A representation MAY separate x/y space from z semantics if that makes the implementation safer; it MUST preserve the coordinate meanings above.

### 10.5 `MeasurementQuality`

```python
@dataclass(frozen=True)
class MeasurementQuality:
    value: float | None
    source: QualitySource
    valid: bool
    semantic_name: str | None
```

Normative semantics:

- baseline invalid quality: `value=None`, `source=NONE`, `valid=False`;
- a valid value MUST be finite and in `[0,1]`;
- `semantic_name` MUST describe the real provider/experimental quantity;
- MediaPipe threshold configuration is not a per-frame quality output;
- handedness classification score is handedness metadata, not tracking confidence;
- hard-coded `1.0` for “hand exists” is invalid;
- downstream code MUST function when quality is unavailable.

### 10.6 `LandmarkObservation`

```python
@dataclass(frozen=True)
class LandmarkObservation:
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    landmarks: tuple[Landmark, ...]
    handedness_label: str | None
    handedness_score: float | None
    quality: MeasurementQuality
    hand_bbox: ROI | None
    provider_name: str
```

Downstream modules MUST check `status`; missing/invalid observations are never represented by fake zero landmarks.

### 10.7 `FilterDiagnostics`

```python
@dataclass(frozen=True)
class FilterDiagnostics:
    mode: FilterMode
    dt_s: float | None
    speed: float | None
    beta: float | None
    min_cutoff_hz: float | None
    final_cutoff_hz: float | None
    signal_alpha: float | None
    derivative_alpha: float | None
    reset_occurred: bool
```

### 10.8 `StageTimings`

```python
@dataclass(frozen=True)
class StageTimings:
    preprocess_ms: float
    tracking_ms: float
    filtering_ms: float
    gesture_ms: float
    compute_total_ms: float
```

`compute_total_ms` MUST have one documented calculation used consistently in all final runs.

### 10.9 `TrackingFrame`

```python
@dataclass(frozen=True)
class TrackingFrame:
    run_id: str
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    raw_landmarks: tuple[Landmark, ...]
    filtered_landmarks: tuple[Landmark, ...]
    quality: MeasurementQuality
    roi: ROI | None
    illumination: IlluminationMetrics | None
    filter_diagnostics: FilterDiagnostics
    timings: StageTimings
    events: tuple[str, ...]
```

This is the primary research/logging boundary. Analysis SHOULD depend on this contract or serialized equivalents, not on the renderer.
For pre-G2 Raw-baseline runs, `roi` and `illumination` MAY be `None`
when those stages have not been executed.

`None` means explicitly unavailable/not executed; it MUST NOT be
replaced by fabricated zero-valued ROI or illumination measurements.

Once the G2 preprocessing path is enabled, both fields MUST be populated.
### 10.10 `InteractionState`

```python
@dataclass(frozen=True)
class InteractionState:
    run_id: str
    frame_id: int
    timestamp_s: float
    interaction_valid: bool
    pointer_xy: tuple[float, float] | None
    pinch_ratio: float | None
    pinch_active: bool
    rotation_delta: tuple[float, float]
    scale_delta: float
```

The renderer may derive application-specific state but MUST NOT mutate Core state.

## 11. Public interfaces

```python
class FrameSource(Protocol):
    def open(self) -> None: ...
    def read(self) -> FramePacket | None: ...
    def close(self) -> None: ...
```

Replay EOF may return `None`; camera failure must be distinguishable from normal replay EOF.

```python
class LandmarkProvider(Protocol):
    def process(self, frame: FramePacket) -> LandmarkObservation: ...
    def close(self) -> None: ...
```
The provider receives the project-owned FramePacket so frame identity,
timestamp, and declared color space remain coupled.

For the required MediaPipe adapter, the input FramePacket MUST be BGR.
The adapter owns the explicit BGR → RGB conversion before constructing
the MediaPipe image.

The emitted LandmarkObservation MUST preserve frame.frame_id and
frame.timestamp_s exactly.

```python
class LandmarkFilter(Protocol):
    def update(self, observation: LandmarkObservation) -> tuple[tuple[Landmark, ...], FilterDiagnostics]: ...
    def reset(self) -> None: ...
```

```python
class RunLogger(Protocol):
    def start_run(self, metadata: dict, resolved_config: dict) -> None: ...
    def log_tracking_frame(self, frame: TrackingFrame) -> None: ...
    def log_interaction_state(self, state: InteractionState) -> None: ...
    def log_event(self, event: dict) -> None: ...
    def close(self) -> None: ...
```

## 12. Configuration contract

Configuration precedence:

```text
repository defaults
< experiment profile
< explicit CLI overrides
```

At run start the application MUST:

1. load and merge configuration;
2. validate semantic constraints;
3. create the resolved configuration;
4. serialize it deterministically;
5. compute/store a config hash;
6. use that frozen resolved configuration for the run.

Required configuration sections or equivalent grouping:

```text
project
camera
runtime
roi
illumination
clahe
tracking
filter
gesture
logging
experiment
renderer
```

Required parameter families include:

- requested camera size/FPS/backend;
- runtime mode and replay source;
- ROI padding/coasting/fallback limits;
- illumination EMA/hysteresis thresholds;
- CLAHE policy/clip/tile parameters;
- provider/model and provider threshold settings;
- filter mode, `derivative_cutoff_hz`, fixed and adaptive parameters, reset gap;
- gesture gains/deadzone/clamps and pinch hysteresis/hand-scale pair;
- logging schema/output/video policy;
- experiment ID/condition/trial/warmup metadata;
- renderer enable/window settings.

Algorithmic parameter invariants are defined with the algorithms in `03_ALGORITHM_AND_EXPERIMENTS.md`; configuration validation MUST enforce them.

## 13. Run artifact contract

A final experiment/demo run SHOULD produce:

```text
runs/<run_id>/
├── metadata.json
├── resolved_config.yaml
├── frames.csv
├── landmarks.csv
├── events.csv
└── optional/
    └── recorded_video.*
```

Raw video is optional and off by default unless explicitly required.

Minimum reproducibility identity stored in metadata:

```text
run_id
experiment_id / condition / trial index when applicable
spec version
code revision/commit
log schema version
config hash
Python + key dependency versions
provider/model filename + checksum
camera/backend and requested/observed properties when applicable
source-data identity/hash when practical
OS/hardware summary
```

`frames.csv` MUST carry enough fields to reconstruct status, ROI/illumination state, filter diagnostics, interaction validity, and stage timings. `landmarks.csv` MUST identify raw vs filtered stage and landmark index in a declared coordinate space. `events.csv` MUST carry frame/time, event type, severity, and details.

Breaking serialized semantic changes require a schema-version bump.

## 14. Failure containment

Failures MUST be explicit rather than converted into plausible-looking fake data:

```text
camera unavailable      → explicit startup/runtime failure
invalid ROI             → clamp/fallback/search state
no hand                 → invalid/no-hand observation
bad timestamp           → reset/discontinuity path, not ordinary update
tracking loss           → no zero-landmark injection
reacquisition           → initialized/neutral interaction transition
logger failure          → diagnostic/error, never fabricated log values
renderer failure        → must not rewrite already-computed research data
```

Exact algorithm response to tracking loss/reacquisition is owned by `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 15. Thin future seams

The architecture MAY expose clean seams for:

- alternate `FrameSource`;
- alternate `LandmarkProvider`;
- calibration/camera-capability service;
- alternate renderer;
- packaged desktop launcher;
- local diagnostic export.

These interfaces do not justify implementing speculative product features in the course baseline.
