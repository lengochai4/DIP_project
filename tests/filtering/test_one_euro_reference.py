"""Regression against the OneEuroFilter authors' published ground truth."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from dip_touchless.filtering import ScalarOneEuroFilter


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "one_euro_ground_truth.csv"
)


def test_scalar_one_euro_matches_author_ground_truth() -> None:
    with FIXTURE.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert rows

    required_columns = {
        "timestamp",
        "noisy",
        "filtered",
    }

    assert required_columns.issubset(
        rows[0].keys()
    )

    one_euro = ScalarOneEuroFilter(
        min_cutoff_hz=1.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    previous_timestamp: float | None = None

    for index, row in enumerate(rows):
        timestamp = float(row["timestamp"])
        noisy = float(row["noisy"])
        expected = float(row["filtered"])

        if previous_timestamp is None:
            dt_s = None
        else:
            dt_s = (
                timestamp
                - previous_timestamp
            )

            assert dt_s > 0.0

        result = one_euro.update(
            noisy,
            dt_s=dt_s,
        )

        assert result.filtered_value == pytest.approx(
            expected,
            abs=1e-4,
        ), (
            f"ground-truth mismatch at row {index}, "
            f"timestamp={timestamp}"
        )

        previous_timestamp = timestamp