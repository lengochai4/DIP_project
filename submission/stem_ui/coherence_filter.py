"""Directional Velocity Coherence landmark filter for touchless STEM UI.

Replaces the adaptive 1-Euro filter in the UI runtime with a Sliding-Window
Cosine Directional Coherence filter:
1. Sliding window of N frame-to-frame displacement vectors + cosine turn-angle
   alignment between the latest step and the prior window trajectory.
   Back-and-forth jitter yields coherence C ~ 0 (locking the filter to an
   ultra-calm base cutoff + cubic micro-deadband), while genuine unidirectional
   hand motion yields C -> 1 (opening the cutoff and applying a non-accumulating
   velocity phase compensation so tracking lag drops to ~0).
2. Rigid palm-centroid coherence coupling across palm anchors (0, 5, 9, 13, 17).
3. Directional coherence + deadband filtering on monocular relative depth (z) to
   eliminate 3D palm-normal wobble during object manipulation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

from dip_touchless.core import (
    CoordinateSpace,
    FilterDiagnostics,
    FilterMode,
    Landmark,
    LandmarkObservation,
)
from dip_touchless.filtering.adaptive_one_euro_landmarks import (
    AdaptiveLandmarkDiagnostics,
    AdaptiveLandmarkResult,
)
from dip_touchless.filtering.low_pass import low_pass_alpha
from dip_touchless.filtering.temporal_controller import (
    OneEuroTemporalController,
)

PALM_INDICES = (0, 5, 9, 13, 17)


def _window_coherence(
    history: deque[tuple[float, float, float]],
    path_floor: float,
    *,
    allow_fast_two_step: bool = False,
) -> tuple[float, float, float]:
    """Compute directional coherence and velocity from a sliding window of steps."""
    if not history:
        return 0.0, 0.0, 0.0
    n = len(history)
    dx1, dy1, dt1 = history[-1]
    if n < 2:
        dt_safe = max(0.028, dt1)
        return 0.0, dx1 / dt_safe, dy1 / dt_safe

    dx0, dy0, dt0 = history[-2]
    d0 = math.hypot(dx0, dy0)
    d1 = math.hypot(dx1, dy1)
    dot2 = dx0 * dx1 + dy0 * dy1
    cos2 = max(0.0, dot2 / (d0 * d1 + 1e-9))
    net2_x = dx0 + dx1
    net2_y = dy0 + dy1
    net2_d = math.hypot(net2_x, net2_y)

    # Full-window horizon: bridges sub-frame USB burst pairs and cancels single-point noise
    net_x = sum(h[0] for h in history)
    net_y = sum(h[1] for h in history)
    net_d = math.hypot(net_x, net_y)
    path_d = sum(math.hypot(h[0], h[1]) for h in history) + path_floor
    half = n // 2
    ux = sum(history[k][0] for k in range(half))
    uy = sum(history[k][1] for k in range(half))
    vx_half = net_x - ux
    vy_half = net_y - uy
    dot = ux * vx_half + uy * vy_half
    denom = math.hypot(ux, uy) * math.hypot(vx_half, vy_half) + 1e-9
    cos_align = max(0.0, dot / denom)
    ratio = net_d / path_d
    coh_win = (ratio * ratio) * (0.08 + 0.92 * cos_align)

    if allow_fast_two_step:
        # Safe on the 21-landmark centroid where independent noise is reduced by sqrt(21) = 4.58x
        path2_d = d0 + d1 + path_floor * 0.75
        ratio2 = net2_d / path2_d
        coh2 = (ratio2 * ratio2) * (0.05 + 0.95 * cos2)
        coherence = min(1.0, max(coh2, coh_win))
    else:
        coherence = min(1.0, coh_win)

    # Unbiased 2-step velocity when the last 2 steps are aligned so turns never lag
    if cos2 > 0.15:
        dt2 = max(0.028, dt0 + dt1)
        vx = net2_x / dt2
        vy = net2_y / dt2
    elif allow_fast_two_step and d1 > d0 * 1.25 and dot2 < 0.0:
        dt_safe = max(0.028, dt1)
        vx = dx1 / dt_safe
        vy = dy1 / dt_safe
    else:
        total_dt = max(0.028, sum(h[2] for h in history))
        vx = net_x / total_dt
        vy = net_y / total_dt

    return coherence, vx, vy


@dataclass
class _CoherentLandmarkState:
    """Per-landmark state for sliding-window cosine directional coherence."""

    raw_x: float = 0.0
    raw_y: float = 0.0
    raw_z: float = 0.0
    filt_x: float = 0.0
    filt_y: float = 0.0
    filt_z: float = 0.0
    history: deque[tuple[float, float, float]] = field(
        default_factory=lambda: deque(maxlen=5)
    )
    z_history: deque[tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=5)
    )

    def initialize(self, x: float, y: float, z: float, window_size: int = 5) -> None:
        self.raw_x = x
        self.raw_y = y
        self.raw_z = z
        self.filt_x = x
        self.filt_y = y
        self.filt_z = z
        self.history = deque(maxlen=window_size)
        self.z_history = deque(maxlen=window_size)


class DirectionalCoherenceMeasurementCore:
    """Sliding-Window Cosine Directional Coherence + Non-Accumulating Phase Lead."""

    def __init__(
        self,
        *,
        window_size: int = 5,
        base_cutoff_hz: float = 0.30,
        coherent_velocity_gain: float = 75.0,
        final_cutoff_min_hz: float = 0.30,
        final_cutoff_max_hz: float = 48.0,
        path_floor: float = 0.016,
        deadband_radius: float = 0.011,
        phase_lead_s: float = 0.014,
        phase_lead_max_s: float = 0.009,
        base_z_cutoff_hz: float = 0.40,
        deadband_z_radius: float = 0.018,
        min_vel_dt_s: float = 0.024,
    ) -> None:
        self._window_size = max(2, int(window_size))
        self._base_cutoff_hz = float(base_cutoff_hz)
        self._coherent_velocity_gain = float(coherent_velocity_gain)
        self._final_cutoff_min_hz = float(final_cutoff_min_hz)
        self._final_cutoff_max_hz = float(final_cutoff_max_hz)
        self._path_floor = float(path_floor)
        self._deadband_radius = float(deadband_radius)
        self._phase_lead_s = float(phase_lead_s)
        self._phase_lead_max_s = float(phase_lead_max_s)
        self._base_z_cutoff_hz = float(base_z_cutoff_hz)
        self._deadband_z_radius = float(deadband_z_radius)
        self._min_vel_dt_s = float(min_vel_dt_s)

        self._states: dict[int, _CoherentLandmarkState] = {}
        self._palm_state = _CoherentLandmarkState()
        self._expected_indices: tuple[int, ...] | None = None

    @property
    def initialized(self) -> bool:
        return self._expected_indices is not None

    def reset(self) -> None:
        self._states.clear()
        self._palm_state = _CoherentLandmarkState()
        self._expected_indices = None

    def update(
        self,
        observation: LandmarkObservation,
        *,
        dt_s: float | None,
    ) -> AdaptiveLandmarkResult:
        landmarks = observation.landmarks
        indices = tuple(l.index for l in landmarks)

        if not self.initialized:
            if dt_s is not None:
                raise ValueError("dt_s must be None for initialization")
            self._expected_indices = indices
            return self._initialize(landmarks)

        if indices != self._expected_indices:
            raise ValueError("landmark indices/order changed after initialization")
        if dt_s is None or not math.isfinite(dt_s) or dt_s <= 0.0:
            raise ValueError("dt_s must be finite and positive")

        # 1. Whole-hand centroid temporal + spatial coherence (noise reduced by sqrt(21) = 4.58x)
        palm_pts = list(landmarks)
        pdx = 0.0
        pdy = 0.0
        palm_vx = 0.0
        palm_vy = 0.0
        palm_spatial_coh = 0.0
        if palm_pts:
            px = sum(l.x for l in palm_pts) / len(palm_pts)
            py = sum(l.y for l in palm_pts) / len(palm_pts)
            pdx = px - self._palm_state.raw_x
            pdy = py - self._palm_state.raw_y
            self._palm_state.raw_x = px
            self._palm_state.raw_y = py
            self._palm_state.history.append((pdx, pdy, dt_s))
            palm_coh, palm_vx, palm_vy = _window_coherence(
                self._palm_state.history,
                self._path_floor * 0.72,
                allow_fast_two_step=True,
            )
            # Multi-landmark spatial coherence on the current frame (Frame-1 response):
            # Over 21 landmarks, independent noise cancels by sqrt(21) (sp_ratio^2 < 0.08),
            # whereas whole-hand translation moves all 21 landmarks in unison (sp_ratio^2 > 0.50).
            palm_step_lens = [
                math.hypot(
                    l.x - self._states[l.index].raw_x,
                    l.y - self._states[l.index].raw_y,
                )
                for l in palm_pts
                if l.index in self._states
            ]
            if palm_step_lens:
                palm_net_d = math.hypot(pdx, pdy)
                palm_mean_d = sum(palm_step_lens) / len(palm_step_lens)
                sp_ratio = palm_net_d / (palm_mean_d + self._path_floor * 0.70)
                palm_spatial_coh = max(
                    0.0, min(1.0, (sp_ratio * sp_ratio - 0.16) * 1.45)
                )
        else:
            palm_coh = 0.0

        filtered_landmarks: list[Landmark] = []
        diagnostics: list[AdaptiveLandmarkDiagnostics] = []

        for landmark in landmarks:
            state = self._states[landmark.index]

            dx = landmark.x - state.raw_x
            dy = landmark.y - state.raw_y
            dz = landmark.z - state.raw_z
            state.raw_x = landmark.x
            state.raw_y = landmark.y
            state.raw_z = landmark.z

            state.history.append((dx, dy, dt_s))
            state.z_history.append((dz, dt_s))

            local_coh, vec_vx, vec_vy = _window_coherence(
                state.history,
                self._path_floor,
                allow_fast_two_step=False,
            )
            step_d = math.hypot(dx, dy)
            palm_d = math.hypot(pdx, pdy)
            if palm_spatial_coh > 0.0 and step_d > 1e-6 and palm_d > 1e-6:
                cos_palm = max(0.0, (dx * pdx + dy * pdy) / (step_d * palm_d + 1e-9))
                lm_spatial_coh = (
                    palm_spatial_coh
                    * cos_palm
                    * min(1.0, step_d / (self._path_floor * 0.60))
                )
            else:
                lm_spatial_coh = 0.0

            # Couple local 4-step coherence, 21-point centroid fast coherence, and Frame-1 spatial coherence
            coh = min(1.0, max(local_coh, 0.92 * palm_coh, lm_spatial_coh))
            eff_coh = max(0.0, (coh - 0.08) / 0.92)

            if palm_coh >= local_coh:
                lead_vx = 0.65 * palm_vx + 0.35 * vec_vx
                lead_vy = 0.65 * palm_vy + 0.35 * vec_vy
            else:
                lead_vx = vec_vx
                lead_vy = vec_vy

            vec_speed = math.hypot(lead_vx, lead_vy)
            coherent_speed = vec_speed * eff_coh
            beta = self._coherent_velocity_gain * eff_coh
            unbounded_cutoff = (
                self._base_cutoff_hz + self._coherent_velocity_gain * coherent_speed
            )
            cutoff_hz = min(
                self._final_cutoff_max_hz,
                max(self._final_cutoff_min_hz, unbounded_cutoff),
            )

            signal_alpha = low_pass_alpha(dt_s=dt_s, cutoff_hz=cutoff_hz)

            err_x = landmark.x - state.filt_x
            err_y = landmark.y - state.filt_y
            err_d = math.hypot(err_x, err_y)

            if self._deadband_radius > 0.0 and err_d < self._deadband_radius:
                ratio = err_d / self._deadband_radius
                deadband_weight = min(
                    1.0,
                    (ratio * ratio) * (0.25 + 0.75 * eff_coh)
                    + max(0.0, eff_coh - 0.16) * 4.0,
                )
            else:
                deadband_weight = 1.0

            eff_alpha = min(1.0, signal_alpha * deadband_weight)
            state.filt_x += eff_alpha * err_x
            state.filt_y += eff_alpha * err_y

            # Non-accumulating coherent velocity phase compensation:
            # zero when stationary/jittering (eff_coh <= 0.18), smoothly cancels
            # phase lag across medium and high speeds using the low-noise lead velocity.
            lead_t = min(
                self._phase_lead_max_s,
                self._phase_lead_s * max(0.0, eff_coh - 0.18),
            )
            out_x = state.filt_x + lead_vx * lead_t
            out_y = state.filt_y + lead_vy * lead_t

            # Filter monocular relative z using directional coherence + deadband
            net_z = sum(h[0] for h in state.z_history)
            path_z = sum(abs(h[0]) for h in state.z_history) + 0.025
            z_coh = (abs(net_z) / path_z) ** 2 if len(state.z_history) >= 2 else 0.0
            z_fc = self._base_z_cutoff_hz + 12.0 * z_coh
            z_alpha = low_pass_alpha(dt_s=dt_s, cutoff_hz=z_fc)
            err_z = landmark.z - state.filt_z
            if self._deadband_z_radius > 0.0 and abs(err_z) < self._deadband_z_radius:
                z_ratio = abs(err_z) / self._deadband_z_radius
                z_db = min(1.0, z_ratio * z_ratio + z_coh * 2.0)
            else:
                z_db = 1.0
            state.filt_z += min(1.0, z_alpha * z_db) * err_z

            filtered_landmarks.append(
                Landmark(
                    index=landmark.index,
                    x=out_x,
                    y=out_y,
                    z=state.filt_z,
                    coordinate_space=landmark.coordinate_space,
                )
            )
            diagnostics.append(
                AdaptiveLandmarkDiagnostics(
                    landmark_index=landmark.index,
                    filtered_dx=vec_vx,
                    filtered_dy=vec_vy,
                    speed=coherent_speed,
                    beta=beta,
                    min_cutoff_hz=self._base_cutoff_hz,
                    cutoff_hz=cutoff_hz,
                    signal_alpha=eff_alpha,
                    derivative_alpha=coh,
                    initialization_occurred=False,
                )
            )

        return AdaptiveLandmarkResult(
            landmarks=tuple(filtered_landmarks),
            diagnostics=tuple(diagnostics),
        )

    def _initialize(self, landmarks: tuple[Landmark, ...]) -> AdaptiveLandmarkResult:
        self._states.clear()
        palm_pts = list(landmarks)
        if palm_pts:
            self._palm_state.initialize(
                sum(l.x for l in palm_pts) / len(palm_pts),
                sum(l.y for l in palm_pts) / len(palm_pts),
                sum(l.z for l in palm_pts) / len(palm_pts),
                window_size=self._window_size,
            )
        filtered_landmarks: list[Landmark] = []
        diagnostics: list[AdaptiveLandmarkDiagnostics] = []
        for landmark in landmarks:
            state = _CoherentLandmarkState()
            state.initialize(
                landmark.x,
                landmark.y,
                landmark.z,
                window_size=self._window_size,
            )
            self._states[landmark.index] = state
            filtered_landmarks.append(
                Landmark(
                    index=landmark.index,
                    x=landmark.x,
                    y=landmark.y,
                    z=landmark.z,
                    coordinate_space=CoordinateSpace.FRAME_NORMALIZED
                    if landmark.coordinate_space is None
                    else landmark.coordinate_space,
                )
            )
            diagnostics.append(
                AdaptiveLandmarkDiagnostics(
                    landmark_index=landmark.index,
                    filtered_dx=0.0,
                    filtered_dy=0.0,
                    speed=0.0,
                    beta=0.0,
                    min_cutoff_hz=self._base_cutoff_hz,
                    cutoff_hz=self._base_cutoff_hz,
                    signal_alpha=None,
                    derivative_alpha=None,
                    initialization_occurred=True,
                )
            )
        return AdaptiveLandmarkResult(
            landmarks=tuple(filtered_landmarks),
            diagnostics=tuple(diagnostics),
        )


class DirectionalCoherenceLandmarkFilter:
    """Drop-in replacement for AdaptiveOneEuroLandmarkFilter using Directional Coherence."""

    def __init__(
        self,
        *,
        window_size: int = 5,
        base_cutoff_hz: float = 0.30,
        coherent_velocity_gain: float = 75.0,
        final_cutoff_min_hz: float = 0.30,
        final_cutoff_max_hz: float = 48.0,
        path_floor: float = 0.016,
        deadband_radius: float = 0.011,
        phase_lead_s: float = 0.014,
        phase_lead_max_s: float = 0.009,
        base_z_cutoff_hz: float = 0.40,
        deadband_z_radius: float = 0.018,
        reset_gap_s: float = 0.50,
    ) -> None:
        self._base_cutoff_hz = float(base_cutoff_hz)
        self._controller = OneEuroTemporalController[AdaptiveLandmarkDiagnostics](
            measurement_core=DirectionalCoherenceMeasurementCore(
                window_size=window_size,
                base_cutoff_hz=base_cutoff_hz,
                coherent_velocity_gain=coherent_velocity_gain,
                final_cutoff_min_hz=final_cutoff_min_hz,
                final_cutoff_max_hz=final_cutoff_max_hz,
                path_floor=path_floor,
                deadband_radius=deadband_radius,
                phase_lead_s=phase_lead_s,
                phase_lead_max_s=phase_lead_max_s,
                base_z_cutoff_hz=base_z_cutoff_hz,
                deadband_z_radius=deadband_z_radius,
            ),
            reset_gap_s=reset_gap_s,
        )

    def reset(self) -> None:
        self._controller.reset()

    def update(
        self,
        observation: LandmarkObservation,
    ) -> tuple[tuple[Landmark, ...], FilterDiagnostics]:
        result = self._controller.update(observation)
        if not result.measurement_accepted:
            return (
                result.landmarks,
                FilterDiagnostics(
                    mode=FilterMode.ONE_EURO_ADAPTIVE,
                    dt_s=None,
                    speed=None,
                    beta=None,
                    min_cutoff_hz=self._base_cutoff_hz,
                    final_cutoff_hz=None,
                    signal_alpha=None,
                    derivative_alpha=None,
                    reset_occurred=result.reset_occurred,
                    events=() if result.event is None else (result.event,),
                ),
            )
        rep = max(
            result.landmark_diagnostics,
            key=lambda item: (item.speed, -item.landmark_index),
        )
        return (
            result.landmarks,
            FilterDiagnostics(
                mode=FilterMode.ONE_EURO_ADAPTIVE,
                dt_s=result.dt_s,
                speed=rep.speed,
                beta=rep.beta,
                min_cutoff_hz=rep.min_cutoff_hz,
                final_cutoff_hz=rep.cutoff_hz,
                signal_alpha=rep.signal_alpha,
                derivative_alpha=rep.derivative_alpha,
                reset_occurred=result.reset_occurred,
                events=() if result.event is None else (result.event,),
            ),
        )


def build_ui_landmark_filter(settings: dict, cfg: dict) -> DirectionalCoherenceLandmarkFilter:
    """Build the Directional Velocity Coherence filter configured by settings.yaml."""
    coh_cfg = settings.get("coherence_filter", {})
    reset_gap_s = float(cfg.get("filter", {}).get("reset_gap_s", 0.50))
    return DirectionalCoherenceLandmarkFilter(
        window_size=int(coh_cfg.get("window_size", 5)),
        base_cutoff_hz=float(coh_cfg.get("base_cutoff_hz", 0.30)),
        coherent_velocity_gain=float(coh_cfg.get("coherent_velocity_gain", 75.0)),
        final_cutoff_min_hz=float(coh_cfg.get("final_cutoff_min_hz", 0.30)),
        final_cutoff_max_hz=float(coh_cfg.get("final_cutoff_max_hz", 48.0)),
        path_floor=float(coh_cfg.get("path_floor", 0.016)),
        deadband_radius=float(coh_cfg.get("deadband_radius", 0.011)),
        phase_lead_s=float(coh_cfg.get("phase_lead_s", 0.014)),
        phase_lead_max_s=float(coh_cfg.get("phase_lead_max_s", 0.009)),
        base_z_cutoff_hz=float(coh_cfg.get("base_z_cutoff_hz", 0.40)),
        deadband_z_radius=float(coh_cfg.get("deadband_z_radius", 0.018)),
        reset_gap_s=reset_gap_s,
    )
