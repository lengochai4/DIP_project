"""Read-only presentation access to the frozen G7 evidence package."""

from .presentation import (
    EvidenceAsset,
    EvidenceBatch,
    EvidenceCatalog,
    EvidenceContent,
    EvidenceMetric,
    EvidenceMetricRow,
    EvidencePageSpec,
    load_evidence_catalog,
)

__all__ = [
    "EvidenceAsset",
    "EvidenceBatch",
    "EvidenceCatalog",
    "EvidenceContent",
    "EvidenceMetric",
    "EvidenceMetricRow",
    "EvidencePageSpec",
    "load_evidence_catalog",
]
