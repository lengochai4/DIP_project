"""Run paired replay conditions from one experiment manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from experiments.manifest import (
    ExperimentManifest,
    load_experiment_manifest,
)
from experiments.run_replay import (
    run_single_replay,
)


@dataclass(frozen=True)
class BatchRunResult:
    experiment_id: str
    trial_id: str
    profile: str
    source: Path
    run_id: str
    processed_frames: int


@dataclass(frozen=True)
class BatchIndex:
    batch_id: str
    experiment_id: str
    manifest_path: str | None
    analysis_start_s: float
    analysis_end_s: float | None
    primary_metric: str
    planned_comparisons: tuple[
        tuple[str, str], ...
    ]
    exclusion_rules: tuple[str, ...]
    runs: tuple[BatchRunResult, ...]


SingleReplayRunner = Callable[..., tuple[str, int]]


def create_batch_id(
    experiment_id: str,
) -> str:
    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")

    safe_experiment_id = "".join(
        character
        if (
            character.isalnum()
            or character in {"-", "_"}
        )
        else "-"
        for character in experiment_id
    )

    return (
        f"{safe_experiment_id}-"
        f"{timestamp}"
    )


def write_batch_index(
    index: BatchIndex,
    *,
    index_root: Path,
) -> Path:
    """Persist exact raw-run identity for later regeneration."""

    batch_dir = (
        index_root / index.batch_id
    )

    batch_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    path = (
        batch_dir / "batch_index.json"
    )

    payload = {
        "schema_version": "1",
        "batch_id": index.batch_id,
        "experiment_id": (
            index.experiment_id
        ),
        "manifest_path": (
            index.manifest_path
        ),
        "analysis_window": {
            "start_s": (
                index.analysis_start_s
            ),
            "end_s": (
                index.analysis_end_s
            ),
        },
        "primary_metric": (
            index.primary_metric
        ),
        "planned_comparisons": [
            [left, right]
            for left, right
            in index.planned_comparisons
        ],
        "exclusion_rules": list(
            index.exclusion_rules
        ),
        "runs": [
            {
                "experiment_id": (
                    result.experiment_id
                ),
                "trial_id": (
                    result.trial_id
                ),
                "profile": result.profile,
                "source": str(
                    result.source
                ),
                "run_id": result.run_id,
                "processed_frames": (
                    result.processed_frames
                ),
            }
            for result in index.runs
        ],
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def build_batch_index(
    manifest: ExperimentManifest,
    results: tuple[
        BatchRunResult, ...
    ],
    *,
    manifest_path: Path | None = None,
    batch_id: str | None = None,
) -> BatchIndex:
    return BatchIndex(
        batch_id=(
            batch_id
            or create_batch_id(
                manifest.experiment_id
            )
        ),
        experiment_id=(
            manifest.experiment_id
        ),
        manifest_path=(
            str(
                manifest_path.resolve()
            )
            if manifest_path is not None
            else None
        ),
        analysis_start_s=(
            manifest.analysis_start_s
        ),
        analysis_end_s=(
            manifest.analysis_end_s
        ),
        primary_metric=(
            manifest.primary_metric
        ),
        planned_comparisons=(
            manifest.planned_comparisons
        ),
        exclusion_rules=(
            manifest.exclusion_rules
        ),
        runs=results,
    )


def run_experiment_batch(
    manifest: ExperimentManifest,
    *,
    output_dir: Path,
    runner: SingleReplayRunner = (
        run_single_replay
    ),
) -> tuple[BatchRunResult, ...]:
    """Run every profile for every trial deterministically."""

    results: list[BatchRunResult] = []

    for trial in manifest.trials:
        for profile in manifest.profiles:
            run_id, processed_frames = runner(
                profile_name=profile,
                source=trial.source,
                model=manifest.model,
                experiment_id=(
                    manifest.experiment_id
                ),
                trial_id=trial.trial_id,
                warmup_s=manifest.warmup_s,
                output_dir=output_dir,
            )

            results.append(
                BatchRunResult(
                    experiment_id=(
                        manifest.experiment_id
                    ),
                    trial_id=trial.trial_id,
                    profile=profile,
                    source=trial.source,
                    run_id=run_id,
                    processed_frames=(
                        processed_frames
                    ),
                )
            )

    return tuple(results)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run paired replay experiment "
            "conditions from a manifest."
        )
    )

    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs"),
    )

    parser.add_argument(
        "--index-root",
        type=Path,
        default=Path("results") / "batches",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    manifest = load_experiment_manifest(
        args.manifest
    )

    results = run_experiment_batch(
        manifest,
        output_dir=args.output_dir,
    )

    index = build_batch_index(
        manifest,
        results,
        manifest_path=args.manifest,
    )

    index_path = write_batch_index(
        index,
        index_root=args.index_root,
    )

    for result in results:
        print(
            f"{result.trial_id} "
            f"{result.profile.upper()} "
            f"{result.run_id} "
            f"{result.processed_frames}"
        )

    print(f"completed_runs: {len(results)}")
    print(f"batch_id: {index.batch_id}")
    print(f"batch_index: {index_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
