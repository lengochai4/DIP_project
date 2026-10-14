from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np

from extensions.stem3d.evidence import load_evidence_catalog
from extensions.stem3d.ui import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    FilterPresentation,
    InteractionPresentation,
    LiveDashboard,
    PresentationState,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = PROJECT_ROOT / "submission" / "evidence"


def _presentation() -> PresentationState:
    return PresentationState(
        run_id="g8-viewer-session",
        frame_id=0,
        timestamp_s=0.0,
        tracking_status="NO_HAND",
        raw_landmarks=(),
        filtered_landmarks=(),
        roi=None,
        illumination=None,
        filter=FilterPresentation(
            mode="RAW",
            dt_s=None,
            speed=None,
            beta=None,
            cutoff_hz=None,
            compute_total_ms=0.0,
        ),
        interaction=InteractionPresentation(
            available=False,
            valid=False,
            pointer_xy=None,
            pinch_active=None,
            pinch_ratio=None,
            rotation_delta=None,
            scale_delta=None,
        ),
    )


def _render_evidence_page(
    dashboard: LiveDashboard,
    *,
    width: int = 1280,
    height: int = 720,
) -> np.ndarray:
    state = _presentation()
    return dashboard.build_dashboard(
        np.zeros((12, 16, 3), dtype=np.uint8),
        state,
        ApplicationState(
            run_id=state.run_id,
            phase=ApplicationPhase.RUNNING,
        ),
        width=width,
        height=height,
    )


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(EVIDENCE_ROOT)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(EVIDENCE_ROOT.rglob("*"))
        if path.is_file()
    }


def test_catalog_contains_ordered_frozen_g7_groups_and_metadata() -> None:
    catalog = load_evidence_catalog()

    assert [batch.key for batch in catalog.batches] == [
        "a1_static",
        "a2_dynamic",
        "b_normal",
        "b_lowlight",
    ]
    assert [page.key for page in catalog.pages] == [
        "OVERVIEW",
        "B NORMAL",
        "B LOW-LIGHT",
        "A1 STATIC",
        "A2 DYNAMIC",
        "RQ3 + DIP",
    ]
    assert [asset.asset_id for asset in catalog.assets] == [
        "a1_static_jitter",
        "a2_unavailable",
        "b_normal",
        "b_lowlight",
        "dip_visual",
    ]
    assert all(
        catalog.asset_path(asset.asset_id).is_file()
        for asset in catalog.assets
    )
    assert catalog.release_tag == "g7-final"
    assert catalog.release_commit == (
        "f454c6b8325c85199c0122c0e822fe8e76c1526c"
    )
    assert catalog.live_demo_run_id == "g7-demo-20260929-192030"
    assert catalog.live_demo_revision == (
        "6a87dc50f9d3920ed9fd39a2669e266be00f9735"
    )
    assert catalog.batch("a1_static").recorded_trial_count == 3
    assert catalog.batch("a1_static").evaluable_trial_count == 2
    assert catalog.batch("a2_dynamic").recorded_trial_count == 3
    assert catalog.batch("a2_dynamic").evaluable_trial_count == 0
    assert catalog.batch("a1_static").batch_id == (
        "G7-A1-STATIC-20260928T144254479591Z"
    )
    assert catalog.batch("a2_dynamic").batch_id == (
        "G7-A2-DYNAMIC-20260928T151157912799Z"
    )
    assert catalog.batch("b_normal").batch_id == (
        "G7-B-NORMAL-20260928T151702564004Z"
    )
    assert catalog.batch("b_lowlight").batch_id == (
        "G7-B-LOWLIGHT-20260928T152103579608Z"
    )
    assert catalog.dip_policy == "always"
    assert catalog.dip_primary_experiment_result is False


def test_a2_is_unavailable_and_never_exposed_as_numeric_zero() -> None:
    batch = load_evidence_catalog().batch("a2_dynamic")

    assert batch.metrics_available is True
    assert len(batch.metrics) == 9
    assert all(not metric.available for metric in batch.metrics)
    assert all(metric.value_text is None for metric in batch.metrics)
    assert all(
        metric.unavailable_reason == "no_common_usable_frames"
        for metric in batch.metrics
    )


def test_experiment_b_rates_preserve_recorded_values_including_real_zeros() -> None:
    catalog = load_evidence_catalog()
    normal = catalog.batch("b_normal")
    low_light = catalog.batch("b_lowlight")

    assert normal.metrics_available is True
    assert all(
        row.metrics[0].value_text == row.metrics[1].value_text
        for row in normal.metric_rows
    )
    assert [
        row.metrics[0].value_text
        for row in normal.metric_rows
    ] == ["0.020747", "0.000000", "0.531120"]
    assert low_light.metrics_available is True
    assert all(
        metric.available and metric.value_text == "0.000000"
        for metric in low_light.metrics
    )


def test_evidence_mode_renders_frozen_claims_and_pages_without_mutation(
    monkeypatch,
) -> None:
    before = _source_hashes()
    catalog = load_evidence_catalog()
    dashboard = LiveDashboard(evidence_catalog=catalog)
    dashboard.set_mode(DashboardMode.EVIDENCE)
    rendered_text: list[str] = []

    def capture_text(
        _cls,
        _image,
        text,
        _x,
        _y,
        **_kwargs,
    ) -> None:
        rendered_text.append(text)

    monkeypatch.setattr(
        LiveDashboard,
        "_put_text",
        classmethod(capture_text),
    )

    for page_index in range(len(catalog.pages)):
        _render_evidence_page(dashboard)
        if page_index < len(catalog.pages) - 1:
            dashboard.handle_key(ord("]"))

    text = "\n".join(rendered_text).lower()
    assert "frozen g7 evidence" in text
    assert "g7-final" in text
    assert "6a87dc50f9d3920ed9fd39a2669e266be00f9735" in text
    assert "clahe did not activate" in text
    assert "very close" in text
    assert "primary responsiveness result" in text
    assert "unavailable" in text
    assert "no_common_usable_frames" in text
    assert "g7 demo run: g7-demo-20260929-192030" in text
    assert "image-domain method illustration" in text
    assert "not a primary p1 experiment b result" in text
    assert "0.000000" not in "\n".join(
        line
        for line in rendered_text
        if "A2" in line or "UNAVAILABLE" in line
    )
    assert _source_hashes() == before


def test_evidence_navigation_and_keyboard_mode_path() -> None:
    dashboard = LiveDashboard()
    transitions: list[DashboardMode] = []
    dashboard.set_mode_action(transitions.append)

    dashboard.handle_key(ord("e"))
    assert dashboard.mode is DashboardMode.EVIDENCE
    assert dashboard.evidence_page_index == 0
    dashboard.handle_key(ord("]"))
    assert dashboard.evidence_page_index == 1
    dashboard.handle_key(ord("a"))
    assert dashboard.mode is DashboardMode.ANALYSIS
    dashboard.handle_key(ord("e"))
    assert dashboard.mode is DashboardMode.EVIDENCE
    assert dashboard.evidence_page_index == 0
    dashboard.handle_key(ord("d"))
    assert dashboard.mode is DashboardMode.DEMO
    assert transitions == [
        DashboardMode.EVIDENCE,
        DashboardMode.ANALYSIS,
        DashboardMode.EVIDENCE,
        DashboardMode.DEMO,
    ]


def test_evidence_page_buttons_navigate_without_changing_mode() -> None:
    dashboard = LiveDashboard()
    dashboard.set_mode(DashboardMode.EVIDENCE)
    _render_evidence_page(dashboard)

    next_button = dashboard._evidence_next_button
    dashboard.handle_mouse_event(
        next_button.x,
        next_button.y,
        cv2.EVENT_LBUTTONUP,
    )
    assert dashboard.mode is DashboardMode.EVIDENCE
    assert dashboard.evidence_page_index == 1

    previous_button = dashboard._evidence_previous_button
    dashboard.handle_mouse_event(
        previous_button.x,
        previous_button.y,
        cv2.EVENT_LBUTTONUP,
    )
    assert dashboard.evidence_page_index == 0


def test_missing_unsupported_and_malformed_optional_assets_are_safe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "evidence"
    invalid_image = root / "a1_static" / "static_jitter.png"
    invalid_image.parent.mkdir(parents=True)
    invalid_image.write_bytes(b"not an image")
    malformed_metadata = root / "a1_static" / "provenance.json"
    malformed_metadata.write_text("{invalid", encoding="utf-8")
    malformed_metrics = root / "a1_static" / "metrics.csv"
    malformed_metrics.write_text("not,a,valid,metric\n", encoding="utf-8")
    malformed_dip_metadata = (
        root / "dip_visual" / "dip_clahe_frame161.json"
    )
    malformed_dip_metadata.parent.mkdir(parents=True)
    malformed_dip_metadata.write_text("{invalid", encoding="utf-8")

    catalog = load_evidence_catalog(root)
    assert catalog.batch("a1_static").batch_id is None
    assert catalog.batch("a1_static").metrics_available is False
    assert catalog.batch("a1_static").metrics == ()
    assert catalog.dip_policy is None
    assert catalog.dip_primary_experiment_result is None
    assert catalog.load_image("a1_static_jitter") is None
    assert catalog.load_image("b_normal") is None
    assert catalog.load_image("unknown-asset") is None

    dashboard = LiveDashboard(evidence_catalog=catalog)
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard.handle_key(ord("]"))
    dashboard.handle_key(ord("]"))
    rendered_text: list[str] = []

    def capture_text(
        _cls,
        _image,
        text,
        _x,
        _y,
        **_kwargs,
    ) -> None:
        rendered_text.append(text)

    monkeypatch.setattr(
        LiveDashboard,
        "_put_text",
        classmethod(capture_text),
    )
    _render_evidence_page(dashboard)

    assert "Evidence asset unavailable" in rendered_text
    assert "Recorded metric data unavailable" in rendered_text


def test_spatial_panel_exposes_evidence_mode_action() -> None:
    from extensions.stem3d.ui import build_spatial_panel_layout

    layout = build_spatial_panel_layout(
        1280,
        720,
        mode=DashboardMode.EVIDENCE,
    )

    evidence = next(
        button
        for button in layout.buttons
        if button.button_id == "mode:EVIDENCE"
    )
    assert evidence.label == "Evidence"
    assert evidence.selected is True
    assert layout.hit_test(
        (evidence.rect.x, evidence.rect.y)
    ) == "mode:EVIDENCE"
