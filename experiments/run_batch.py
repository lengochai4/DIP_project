"""Run paired replay conditions from one experiment manifest."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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


SingleReplayRunner = Callable[..., tuple[str, int]]


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

    for result in results:
        print(
            f"{result.trial_id} "
            f"{result.profile.upper()} "
            f"{result.run_id} "
            f"{result.processed_frames}"
        )

    print(f"completed_runs: {len(results)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
