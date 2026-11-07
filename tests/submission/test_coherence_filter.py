"""Tests for the Directional Velocity Coherence landmark filter."""

import numpy as np
from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import AdaptiveOneEuroLandmarkFilter
from submission.stem_ui.coherence_filter import DirectionalCoherenceLandmarkFilter


def test_directional_coherence_filter_beats_adaptive_one_euro_on_jitter_and_lag():
    rng = np.random.default_rng(42)
    f_one_euro = AdaptiveOneEuroLandmarkFilter(
        base_cutoff_hz=0.85,
        beta_min=0.0,
        beta_base=0.0,
        beta_max=4.5,
        velocity_gain=1.2,
        velocity_max=10.0,
        final_cutoff_min_hz=0.85,
        final_cutoff_max_hz=15.0,
        derivative_cutoff_hz=1.0,
        reset_gap_s=0.5,
    )
    f_coherence = DirectionalCoherenceLandmarkFilter()

    def run_profile(flt):
        rng_local = np.random.default_rng(42)
        t = 0.0
        prev_x = None
        prev_z = None
        step_jitter_x = []
        step_jitter_z = []
        fast_lag = []
        for i in range(120):
            dt = 0.005 if i % 2 == 1 else 0.058
            t += dt
            true_x = 0.2 if i < 60 else min(0.95, 0.2 + (t - 1.9) * 1.2)
            noise = rng_local.normal(0.0, 0.010, size=(21, 3))
            lms = tuple(
                Landmark(
                    j,
                    float(true_x + noise[j, 0]),
                    float(0.5 + noise[j, 1]),
                    float(noise[j, 2]),
                    CoordinateSpace.FRAME_NORMALIZED,
                )
                for j in range(21)
            )
            obs = LandmarkObservation(
                i,
                t,
                TrackingStatus.VALID,
                lms,
                None,
                None,
                MeasurementQuality.unavailable(),
                None,
                "test",
            )
            out, diag = flt.update(obs)
            assert len(out) == 21
            assert diag.final_cutoff_hz is not None
            if 10 <= i < 60 and prev_x is not None:
                step_jitter_x.append(abs(out[8].x - prev_x))
                step_jitter_z.append(abs(out[8].z - prev_z))
            elif 65 <= i < 82:
                fast_lag.append(true_x - out[8].x)
            prev_x = out[8].x
            prev_z = out[8].z
        return (
            float(np.sqrt(np.mean(np.square(step_jitter_x)))),
            float(np.sqrt(np.mean(np.square(step_jitter_z)))),
            abs(float(np.mean(fast_lag))),
        )

    jitter_x_1e, jitter_z_1e, lag_1e = run_profile(f_one_euro)
    jitter_x_coh, jitter_z_coh, lag_coh = run_profile(f_coherence)

    # Directional coherence achieves significantly lower XY jitter, Z jitter, AND fast-motion lag
    assert jitter_x_coh < jitter_x_1e * 0.5
    assert jitter_z_coh < jitter_z_1e * 0.25
    assert lag_coh < lag_1e * 0.25


def test_directional_coherence_medium_speed_and_direction_reversal_beats_one_euro():
    f_one_euro = AdaptiveOneEuroLandmarkFilter(
        base_cutoff_hz=1.8,
        beta_min=0.0,
        beta_base=0.0,
        beta_max=18.0,
        velocity_gain=4.5,
        velocity_max=10.0,
        final_cutoff_min_hz=1.8,
        final_cutoff_max_hz=45.0,
        derivative_cutoff_hz=2.5,
        reset_gap_s=0.5,
    )
    f_coherence = DirectionalCoherenceLandmarkFilter()

    def run_turn_profile(flt):
        t = 0.0
        accel_err = []
        turn_err = []
        for i in range(60):
            dt = 0.033
            t += dt
            if i < 15:
                tx = 0.2
            elif i < 35:
                tx = 0.2 + (i - 15) * dt * 0.55
            else:
                tx = 0.2 + 20 * dt * 0.55 - (i - 35) * dt * 0.55
            lms = tuple(
                Landmark(j, tx, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED)
                for j in range(21)
            )
            obs = LandmarkObservation(
                i,
                t,
                TrackingStatus.VALID,
                lms,
                None,
                None,
                MeasurementQuality.unavailable(),
                None,
                "test",
            )
            out, _ = flt.update(obs)
            err = abs(tx - out[8].x)
            if 15 <= i < 25:
                accel_err.append(err)
            elif 35 <= i < 45:
                turn_err.append(err)
        return float(np.mean(accel_err)), float(np.mean(turn_err))

    accel_1e, turn_1e = run_turn_profile(f_one_euro)
    accel_coh, turn_coh = run_turn_profile(f_coherence)
    assert accel_coh < accel_1e * 0.35
    assert turn_coh < turn_1e * 0.35
