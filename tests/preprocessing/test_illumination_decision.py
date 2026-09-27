import pytest

from dip_touchless.core import IlluminationState
from dip_touchless.preprocessing import (
    IlluminationDecisionStabilizer,
    IlluminationDescriptors,
)


def _decision(
    *,
    alpha: float = 1.0,
) -> IlluminationDecisionStabilizer:
    return IlluminationDecisionStabilizer(
        ema_alpha=alpha,
        low_light_enter_v=70.0,
        low_light_exit_v=85.0,
        low_contrast_enter_range_v=35.0,
        low_contrast_exit_range_v=45.0,
    )


def _descriptors(
    *,
    mean_v: float,
    robust_range_v: float,
) -> IlluminationDescriptors:
    return IlluminationDescriptors(
        mean_v=mean_v,
        std_v=10.0,
        p10_v=20.0,
        p90_v=20.0 + robust_range_v,
        robust_range_v=robust_range_v,
    )


def test_normal_state() -> None:
    decision = _decision()

    result = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=80.0,
        )
    )

    assert result.state is IlluminationState.NORMAL
    assert result.enhancement_active is False


def test_low_light_state() -> None:
    decision = _decision()

    result = decision.update(
        _descriptors(
            mean_v=50.0,
            robust_range_v=80.0,
        )
    )

    assert result.state is IlluminationState.LOW_LIGHT
    assert result.enhancement_active is True


def test_low_contrast_state() -> None:
    decision = _decision()

    result = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=20.0,
        )
    )

    assert (
        result.state
        is IlluminationState.LOW_CONTRAST
    )


def test_difficult_when_both_conditions_are_active() -> None:
    decision = _decision()

    result = decision.update(
        _descriptors(
            mean_v=50.0,
            robust_range_v=20.0,
        )
    )

    assert result.state is IlluminationState.DIFFICULT


def test_low_light_hysteresis_prevents_chatter() -> None:
    decision = _decision()

    first = decision.update(
        _descriptors(
            mean_v=60.0,
            robust_range_v=80.0,
        )
    )

    middle = decision.update(
        _descriptors(
            mean_v=80.0,
            robust_range_v=80.0,
        )
    )

    recovered = decision.update(
        _descriptors(
            mean_v=90.0,
            robust_range_v=80.0,
        )
    )

    assert first.state is IlluminationState.LOW_LIGHT
    assert middle.state is IlluminationState.LOW_LIGHT
    assert recovered.state is IlluminationState.NORMAL


def test_low_contrast_hysteresis_prevents_chatter() -> None:
    decision = _decision()

    first = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=20.0,
        )
    )

    middle = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=40.0,
        )
    )

    recovered = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=50.0,
        )
    )

    assert (
        first.state
        is IlluminationState.LOW_CONTRAST
    )

    assert (
        middle.state
        is IlluminationState.LOW_CONTRAST
    )

    assert recovered.state is IlluminationState.NORMAL


def test_first_sample_initializes_ema_without_zero_bias() -> None:
    decision = _decision(
        alpha=0.2
    )

    decision.update(
        _descriptors(
            mean_v=100.0,
            robust_range_v=60.0,
        )
    )

    assert decision.ema_mean_v == pytest.approx(
        100.0
    )

    assert (
        decision.ema_robust_range_v
        == pytest.approx(60.0)
    )


def test_ema_updates_deterministically() -> None:
    decision = _decision(
        alpha=0.2
    )

    decision.update(
        _descriptors(
            mean_v=100.0,
            robust_range_v=60.0,
        )
    )

    decision.update(
        _descriptors(
            mean_v=50.0,
            robust_range_v=20.0,
        )
    )

    assert decision.ema_mean_v == pytest.approx(
        90.0
    )

    assert (
        decision.ema_robust_range_v
        == pytest.approx(52.0)
    )


def test_reset_clears_temporal_state() -> None:
    decision = _decision()

    decision.update(
        _descriptors(
            mean_v=40.0,
            robust_range_v=20.0,
        )
    )

    decision.reset()

    assert decision.ema_mean_v is None
    assert decision.ema_robust_range_v is None

    result = decision.update(
        _descriptors(
            mean_v=120.0,
            robust_range_v=80.0,
        )
    )

    assert result.state is IlluminationState.NORMAL


def test_metrics_keep_current_raw_descriptors() -> None:
    decision = _decision(
        alpha=0.2
    )

    descriptors = IlluminationDescriptors(
        mean_v=75.0,
        std_v=11.0,
        p10_v=30.0,
        p90_v=90.0,
        robust_range_v=60.0,
    )

    result = decision.update(descriptors)

    assert result.mean_v == pytest.approx(75.0)
    assert result.std_v == pytest.approx(11.0)
    assert result.p10_v == pytest.approx(30.0)
    assert result.p90_v == pytest.approx(90.0)
    assert result.robust_range_v == pytest.approx(
        60.0
    )