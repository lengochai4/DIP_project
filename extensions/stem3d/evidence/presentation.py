"""Immutable presentation values loaded from frozen G7 evidence artifacts."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


G7_RELEASE_TAG = "g7-final"
G7_RELEASE_COMMIT = "f454c6b8325c85199c0122c0e822fe8e76c1526c"
G7_LIVE_DEMO_RUN_ID = "g7-demo-20260929-192030"
G7_LIVE_DEMO_REVISION = "6a87dc50f9d3920ed9fd39a2669e266be00f9735"
G7_LIVE_DEMO_FRAMES = 1188


@dataclass(frozen=True, slots=True)
class EvidenceAsset:
    asset_id: str
    title: str
    relative_path: Path


@dataclass(frozen=True, slots=True)
class EvidencePageSpec:
    key: str
    title: str
    subtitle: str


@dataclass(frozen=True, slots=True)
class EvidenceContent:
    """Frozen report-bounded interpretation text for Evidence Mode."""

    overview_rq1_setup: str
    overview_rq1_result: str
    overview_rq1_limitation: str
    overview_a1_result: str
    overview_a1_caution: str
    overview_a2_status: str
    overview_a2_reason: str
    overview_a2_summary: str
    overview_rq3_interaction: str
    overview_rq3_resets: str
    overview_rq3_false_positive: str
    overview_rq3_claim_boundary: str
    provenance_panel_title: str
    b_normal_result: str
    b_lowlight_result: str
    b_no_improvement: str
    b_clahe_limitation: str
    a1_result: str
    a1_caution: str
    a2_primary_heading: str
    a2_status: str
    a2_reason: str
    a2_figure_title: str
    a2_summary: str
    a2_zero_boundary: str
    rq3_rotation: str
    rq3_scaling_and_states: str
    rq3_false_positive: str
    rq3_claim_boundary: str
    dip_title: str
    dip_result_boundary: str


_EVIDENCE_PAGES = (
    EvidencePageSpec(
        "OVERVIEW",
        "Frozen G7 findings at a glance",
        "Frozen G7 source artifacts  |  read-only  |  no results recalculated",
    ),
    EvidencePageSpec(
        "B NORMAL",
        "RQ1 / Normal-light preprocessing comparison",
        "PRIMARY OUTCOME: VALID HAND-OBSERVATION RATE  |  P0/P1 paired by retained trial",
    ),
    EvidencePageSpec(
        "B LOW-LIGHT",
        "RQ1 / Low-light preprocessing comparison",
        "PRIMARY OUTCOME: VALID HAND-OBSERVATION RATE  |  P0/P1 paired by retained trial",
    ),
    EvidencePageSpec(
        "A1 STATIC",
        "RQ2 / Static temporal stability",
        "Radial RMS jitter  |  filtered landmark 8  |  FRAME_NORMALIZED",
    ),
    EvidencePageSpec(
        "A2 DYNAMIC",
        "RQ2 / Dynamic responsiveness availability",
        "Trajectory-deviation RMSE relative to F0 on the same dynamic source",
    ),
    EvidencePageSpec(
        "RQ3 + DIP",
        "Practical interaction and image-domain evidence",
        "Recorded G7 demonstration identity  |  DIP image illustration is not tracking evidence",
    ),
)

_EVIDENCE_CONTENT = EvidenceContent(
    overview_rq1_setup=(
        "P0 bypass versus adaptive P1 preprocessing; temporal filter held at F0 / Raw."
    ),
    overview_rq1_result=(
        "No valid-hand-rate improvement was observed in the retained trials."
    ),
    overview_rq1_limitation=(
        "P1 never activated CLAHE in analyzed B frames; the active CLAHE path was not tested."
    ),
    overview_a1_result=(
        "F1 and F2 were close; both had lower measured jitter than F0 in two evaluable trials."
    ),
    overview_a1_caution=(
        "One evaluable A1 trial had only five common usable frames."
    ),
    overview_a2_status="A2 UNAVAILABLE",
    overview_a2_reason="no_common_usable_frames",
    overview_a2_summary="All three final trials: {reason}.",
    overview_rq3_interaction=(
        "Realtime webcam input drove rotation and pinch-based scaling."
    ),
    overview_rq3_resets=(
        "Reset, tracking loss, reacquisition, and clean shutdown were exercised."
    ),
    overview_rq3_false_positive=(
        "An occasional face/background hand-like false-positive caused a small unintended rotation."
    ),
    overview_rq3_claim_boundary=(
        "This is practical interaction evidence, not an accuracy claim."
    ),
    provenance_panel_title="FROZEN G7 PROVENANCE  /  G8 VIEWER IS SEPARATE",
    b_normal_result=(
        "P0 and P1 had equal valid-hand-observation rates in all three retained normal-light trials."
    ),
    b_lowlight_result=(
        "P0 and P1 both had zero valid-hand-observation rate in all three retained low-light trials."
    ),
    b_no_improvement=(
        "No valid-hand-observation-rate improvement was observed under the retained tested conditions."
    ),
    b_clahe_limitation=(
        "P1 remained NORMAL and enhancement_active=False throughout analyzed B frames. CLAHE did not activate, so this comparison does not establish whether active CLAHE is effective."
    ),
    a1_result=(
        "In both evaluable trials F1 and F2 had lower radial RMS jitter than F0. F1 and F2 were very close."
    ),
    a1_caution=(
        "One evaluable trial contained only five common usable frames, so it provides weak descriptive evidence by itself."
    ),
    a2_primary_heading="PRIMARY RESPONSIVENESS RESULT",
    a2_status="UNAVAILABLE",
    a2_reason="no_common_usable_frames",
    a2_figure_title="A2 UNAVAILABLE PRIMARY-METRIC FIGURE",
    a2_summary=(
        "All three final A2 trial metrics are unavailable. No numeric outcome was recorded."
    ),
    a2_zero_boundary=(
        "Do not replace unavailable values with zero. Static jitter alone does not complete the responsiveness comparison."
    ),
    rq3_rotation="Recorded realtime webcam input drove 3D object rotation.",
    rq3_scaling_and_states=(
        "Pinch-based scaling worked; reset, loss, reacquisition, and clean shutdown were exercised."
    ),
    rq3_false_positive=(
        "An occasional face/background hand-like false-positive caused a small unintended rotation."
    ),
    rq3_claim_boundary=(
        "This is practical demonstration evidence, not tracking-accuracy or superiority evidence."
    ),
    dip_title="DIP VISUAL  /  IMAGE-DOMAIN METHOD ILLUSTRATION",
    dip_result_boundary=(
        "method illustration only  |  not a primary P1 Experiment B result"
    ),
)


@dataclass(frozen=True, slots=True)
class EvidenceMetric:
    trial_id: str
    condition: str
    value_text: str | None
    sample_count: int | None
    available: bool
    unavailable_reason: str | None


@dataclass(frozen=True, slots=True)
class EvidenceMetricRow:
    trial_id: str
    metrics: tuple[EvidenceMetric, ...]


@dataclass(frozen=True, slots=True)
class EvidenceBatch:
    key: str
    experiment_id: str | None
    batch_id: str | None
    analysis_revision: str | None
    recorded_trial_count: int | None
    evaluable_trial_count: int | None
    metrics: tuple[EvidenceMetric, ...]
    metrics_available: bool

    @property
    def metric_rows(self) -> tuple[EvidenceMetricRow, ...]:
        by_trial: dict[str, list[EvidenceMetric]] = {}
        for metric in self.metrics:
            by_trial.setdefault(metric.trial_id, []).append(metric)
        return tuple(
            EvidenceMetricRow(
                trial_id=trial_id,
                metrics=tuple(
                    sorted(
                        metrics,
                        key=lambda metric: metric.condition,
                    )
                ),
            )
            for trial_id, metrics in sorted(by_trial.items())
        )


@dataclass(frozen=True, slots=True)
class EvidenceCatalog:
    """Selected frozen evidence plus read-only access to its source assets."""

    root: Path
    assets: tuple[EvidenceAsset, ...]
    pages: tuple[EvidencePageSpec, ...]
    content: EvidenceContent
    batches: tuple[EvidenceBatch, ...]
    dip_policy: str | None
    dip_primary_experiment_result: bool | None
    _image_cache: dict[str, np.ndarray | None] = field(
        init=False,
        repr=False,
        compare=False,
    )
    release_tag: str = G7_RELEASE_TAG
    release_commit: str = G7_RELEASE_COMMIT
    live_demo_run_id: str = G7_LIVE_DEMO_RUN_ID
    live_demo_revision: str = G7_LIVE_DEMO_REVISION
    live_demo_frames: int = G7_LIVE_DEMO_FRAMES

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())
        object.__setattr__(self, "_image_cache", {})

    def asset(self, asset_id: str) -> EvidenceAsset | None:
        return next(
            (
                asset
                for asset in self.assets
                if asset.asset_id == asset_id
            ),
            None,
        )

    def asset_path(self, asset_id: str) -> Path | None:
        asset = self.asset(asset_id)
        if asset is None:
            return None
        return self.root / asset.relative_path

    def load_image(self, asset_id: str) -> np.ndarray | None:
        """Read and cache an image without changing the source asset."""

        cache = self._image_cache
        if asset_id in cache:
            return cache[asset_id]
        path = self.asset_path(asset_id)
        if path is None:
            cache[asset_id] = None
            return None
        try:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        except (cv2.error, OSError, ValueError):
            image = None
        if (
            not isinstance(image, np.ndarray)
            or image.ndim != 3
            or image.shape[2] != 3
            or image.size == 0
        ):
            image = None
        elif image.flags.writeable:
            image.setflags(write=False)
        cache[asset_id] = image
        return image

    def batch(self, key: str) -> EvidenceBatch:
        for batch in self.batches:
            if batch.key == key:
                return batch
        raise KeyError(f"unknown evidence batch: {key}")


_ASSET_DEFINITIONS = (
    EvidenceAsset(
        "a1_static_jitter",
        "A1 static radial RMS jitter",
        Path("a1_static") / "static_jitter.png",
    ),
    EvidenceAsset(
        "a2_unavailable",
        "A2 responsiveness unavailable",
        Path("a2_dynamic") / "responsiveness_unavailable.png",
    ),
    EvidenceAsset(
        "b_normal",
        "Experiment B normal-light valid hand rate",
        Path("b_normal") / "valid_hand_rate.png",
    ),
    EvidenceAsset(
        "b_lowlight",
        "Experiment B low-light valid hand rate",
        Path("b_lowlight") / "valid_hand_rate.png",
    ),
    EvidenceAsset(
        "dip_visual",
        "DIP image-domain method illustration",
        Path("dip_visual") / "dip_clahe_frame161.png",
    ),
)

_BATCH_DEFINITIONS = (
    ("a1_static", Path("a1_static")),
    ("a2_dynamic", Path("a2_dynamic")),
    ("b_normal", Path("b_normal")),
    ("b_lowlight", Path("b_lowlight")),
)


def load_evidence_catalog(
    evidence_root: str | Path | None = None,
) -> EvidenceCatalog:
    """Load presentation-safe metadata; missing optional files stay optional."""

    if evidence_root is None:
        root = Path(__file__).resolve().parents[3] / "submission" / "evidence"
    else:
        root = Path(evidence_root)

    batches = tuple(
        _load_batch(root, key, relative_dir)
        for key, relative_dir in _BATCH_DEFINITIONS
    )
    dip_metadata = _read_json_mapping(
        root / "dip_visual" / "dip_clahe_frame161.json"
    )
    visualization = dip_metadata.get("visualization_preprocessing")
    if not isinstance(visualization, Mapping):
        visualization = {}
    primary_result = dip_metadata.get("primary_experiment_result")
    if not isinstance(primary_result, bool):
        primary_result = None

    return EvidenceCatalog(
        root=root,
        assets=_ASSET_DEFINITIONS,
        pages=_EVIDENCE_PAGES,
        content=_EVIDENCE_CONTENT,
        batches=batches,
        dip_policy=_optional_text(visualization.get("policy")),
        dip_primary_experiment_result=primary_result,
    )


def _load_batch(
    root: Path,
    key: str,
    relative_dir: Path,
) -> EvidenceBatch:
    provenance = _read_json_mapping(
        root / relative_dir / "provenance.json"
    )
    experiment_id = _optional_text(provenance.get("experiment_id"))
    analysis = provenance.get("analysis")
    if not isinstance(analysis, Mapping):
        analysis = {}
    batch_id = _optional_text(provenance.get("batch_id"))
    analysis_revision = _optional_text(
        analysis.get("code_revision")
    )
    recorded_count = _optional_non_negative_int(
        analysis.get("recorded_trial_count")
    )
    evaluable_count = _optional_non_negative_int(
        analysis.get("evaluable_trial_count")
    )
    metrics, metrics_available = _read_metrics(
        root / relative_dir / "metrics.csv"
    )
    return EvidenceBatch(
        key=key,
        experiment_id=experiment_id,
        batch_id=batch_id,
        analysis_revision=analysis_revision,
        recorded_trial_count=recorded_count,
        evaluable_trial_count=evaluable_count,
        metrics=metrics,
        metrics_available=metrics_available,
    )


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, Mapping) else {}


def _read_metrics(
    path: Path,
) -> tuple[tuple[EvidenceMetric, ...], bool]:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            required_fields = {
                "trial_id",
                "profile",
                "available",
                "value",
                "sample_count",
                "unavailable_reason",
            }
            if (
                reader.fieldnames is None
                or not required_fields.issubset(reader.fieldnames)
            ):
                return (), False
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error):
        return (), False

    if not rows:
        return (), False

    metrics: list[EvidenceMetric] = []
    try:
        for row in rows:
            trial_id = row.get("trial_id", "")
            condition = row.get("profile", "")
            availability = row.get("available", "")
            if not trial_id or not condition:
                return (), False
            if availability not in {"true", "false"}:
                return (), False
            available = availability == "true"
            raw_value = row.get("value", "")
            reason = row.get("unavailable_reason", "") or None
            sample_count = _optional_non_negative_int(
                _parse_csv_integer(row.get("sample_count", ""))
            )
            if available:
                if raw_value == "":
                    return (), False
                value = float(raw_value)
                if not math.isfinite(value):
                    return (), False
                value_text = f"{value:.6f}"
                if reason is not None:
                    return (), False
            else:
                if raw_value != "" or reason is None:
                    return (), False
                value_text = None
            metrics.append(
                EvidenceMetric(
                    trial_id=trial_id,
                    condition=condition.upper(),
                    value_text=value_text,
                    sample_count=sample_count,
                    available=available,
                    unavailable_reason=reason,
                )
            )
    except (TypeError, ValueError, OverflowError):
        return (), False
    return tuple(metrics), True


def _parse_csv_integer(value: str) -> int | None:
    if value == "":
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError("sample_count must be non-negative")
    return parsed


def _optional_non_negative_int(value: Any) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        return None
    return value


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
