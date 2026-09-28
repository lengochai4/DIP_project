"""Run one deterministic replay experiment condition."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from dip_touchless.capture import ReplayFrameSource
from dip_touchless.configuration import (
    ResolvedConfig,
    resolve_config,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkFilter,
    FixedOneEuroLandmarkFilter,
    RawLandmarkFilter,
)
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
    ROIManager,
)
from dip_touchless.runtime import ReplayRuntime
from dip_touchless.telemetry import FileRunLogger
from dip_touchless.telemetry.metadata import (
    build_run_metadata,
    create_run_id,
)
from dip_touchless.tracking import (
    MediaPipeHandLandmarkerProvider,
    MeasurementValidator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"
PROFILE_DIR = PROJECT_ROOT / "config" / "experiments"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "hand_landmarker.task"

PROFILE_NAMES = (
    "f0",
    "f1",
    "f2",
    "p0",
    "p1",
)


def build_landmark_filter(
    config: Mapping[str, Any],
):
    """Build the configured public landmark-filter baseline."""

    filter_config = config["filter"]
    mode = filter_config["mode"]

    if mode == "RAW":
        return RawLandmarkFilter()

    if mode == "ONE_EURO_FIXED":
        return FixedOneEuroLandmarkFilter(
            min_cutoff_hz=filter_config[
                "min_cutoff_hz"
            ],
            beta=filter_config["beta"],
            derivative_cutoff_hz=filter_config[
                "derivative_cutoff_hz"
            ],
            reset_gap_s=filter_config[
                "reset_gap_s"
            ],
        )

    if mode == "ONE_EURO_ADAPTIVE":
        adaptive = filter_config["adaptive"]

        return AdaptiveOneEuroLandmarkFilter(
            base_cutoff_hz=adaptive[
                "base_cutoff_hz"
            ],
            beta_min=adaptive["beta_min"],
            beta_base=adaptive["beta_base"],
            beta_max=adaptive["beta_max"],
            velocity_gain=adaptive[
                "velocity_gain"
            ],
            velocity_max=adaptive[
                "velocity_max"
            ],
            final_cutoff_min_hz=adaptive[
                "final_cutoff_min_hz"
            ],
            final_cutoff_max_hz=adaptive[
                "final_cutoff_max_hz"
            ],
            derivative_cutoff_hz=filter_config[
                "derivative_cutoff_hz"
            ],
            reset_gap_s=filter_config[
                "reset_gap_s"
            ],
        )

    raise ValueError(
        f"unsupported filter mode: {mode}"
    )


def build_replay_runtime(
    resolved: ResolvedConfig,
    *,
    run_id: str,
) -> ReplayRuntime:
    """Compose one ReplayRuntime from a frozen resolved config."""

    config = resolved.to_dict()

    runtime_config = config["runtime"]
    tracking_config = config["tracking"]
    roi_config = config["roi"]
    illumination_config = config["illumination"]
    clahe_config = config["clahe"]
    logging_config = config["logging"]

    replay_source = runtime_config[
        "replay_source"
    ]

    if not replay_source:
        raise ValueError(
            "runtime.replay_source is required"
        )

    model_path = tracking_config[
        "model_path"
    ]

    if not model_path:
        raise ValueError(
            "tracking.model_path is required"
        )

    source_path = Path(replay_source)
    model_file = Path(model_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"replay source not found: {source_path}"
        )

    if not model_file.is_file():
        raise FileNotFoundError(
            f"tracking model not found: {model_file}"
        )

    return ReplayRuntime(
        source=ReplayFrameSource(
            source_path,
            run_id=run_id,
        ),
        provider=MediaPipeHandLandmarkerProvider(
            model_file,
            num_hands=tracking_config[
                "num_hands"
            ],
            min_hand_detection_confidence=(
                tracking_config[
                    "min_hand_detection_confidence"
                ]
            ),
            min_hand_presence_confidence=(
                tracking_config[
                    "min_hand_presence_confidence"
                ]
            ),
            min_tracking_confidence=(
                tracking_config[
                    "min_tracking_confidence"
                ]
            ),
        ),
        validator=MeasurementValidator(),
        landmark_filter=build_landmark_filter(
            config
        ),
        logger=FileRunLogger(
            logging_config["output_dir"]
        ),
        roi_manager=ROIManager(
            padding_ratio=roi_config[
                "padding_ratio"
            ],
            coast_expand_ratio=roi_config[
                "coast_expand_ratio"
            ],
            coast_frames=roi_config[
                "coast_frames"
            ],
            min_width=roi_config[
                "min_width"
            ],
            min_height=roi_config[
                "min_height"
            ],
        ),
        illumination_analyzer=(
            IlluminationAnalyzer()
        ),
        illumination_decision=(
            IlluminationDecisionStabilizer(
                ema_alpha=illumination_config[
                    "ema_alpha"
                ],
                low_light_enter_v=(
                    illumination_config[
                        "low_light_enter_v"
                    ]
                ),
                low_light_exit_v=(
                    illumination_config[
                        "low_light_exit_v"
                    ]
                ),
                low_contrast_enter_range_v=(
                    illumination_config[
                        "low_contrast_enter_range_v"
                    ]
                ),
                low_contrast_exit_range_v=(
                    illumination_config[
                        "low_contrast_exit_range_v"
                    ]
                ),
            )
        ),
        adaptive_preprocessor=AdaptivePreprocessor(
            policy=clahe_config["policy"],
            clip_limit=clahe_config[
                "clip_limit"
            ],
            tile_grid_size=tuple(
                clahe_config[
                    "tile_grid_size"
                ]
            ),
        ),
    )


def resolve_experiment_config(
    *,
    profile_name: str,
    source: Path,
    model: Path,
    experiment_id: str,
    trial_id: str,
    warmup_s: float,
    output_dir: Path,
) -> ResolvedConfig:
    """Resolve one experiment profile plus explicit run identity."""

    profile_path = (
        PROFILE_DIR
        / f"{profile_name}.yaml"
    )

    if not profile_path.is_file():
        raise FileNotFoundError(
            f"experiment profile not found: {profile_path}"
        )

    return resolve_config(
        DEFAULT_CONFIG,
        profile_path=profile_path,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": str(source),
            },
            "tracking": {
                "model_path": str(model),
            },
            "logging": {
                "output_dir": str(output_dir),
            },
            "experiment": {
                "experiment_id": experiment_id,
                "trial_id": trial_id,
                "warmup_s": warmup_s,
            },
            "renderer": {
                "enabled": False,
            },
        },
    )


def run_single_replay(
    *,
    profile_name: str,
    source: Path,
    model: Path,
    experiment_id: str,
    trial_id: str,
    warmup_s: float,
    output_dir: Path,
) -> tuple[str, int]:
    """Execute one deterministic experiment replay."""

    resolved = resolve_experiment_config(
        profile_name=profile_name,
        source=source,
        model=model,
        experiment_id=experiment_id,
        trial_id=trial_id,
        warmup_s=warmup_s,
        output_dir=output_dir,
    )

    run_id = create_run_id()

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
    )

    runtime = build_replay_runtime(
        resolved,
        run_id=run_id,
    )

    processed_frames = runtime.run(
        metadata=metadata,
        resolved_config=resolved.to_dict(),
    )

    return run_id, processed_frames


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one deterministic DIP Touchless "
            "STEM replay experiment condition."
        )
    )

    parser.add_argument(
        "--profile",
        required=True,
        choices=PROFILE_NAMES,
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--experiment-id",
        required=True,
    )
    parser.add_argument(
        "--trial-id",
        required=True,
    )
    parser.add_argument(
        "--warmup-s",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "runs",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    run_id, processed_frames = run_single_replay(
        profile_name=args.profile,
        source=args.source,
        model=args.model,
        experiment_id=args.experiment_id,
        trial_id=args.trial_id,
        warmup_s=args.warmup_s,
        output_dir=args.output_dir,
    )

    print(f"run_id: {run_id}")
    print(f"profile: {args.profile.upper()}")
    print(f"processed_frames: {processed_frames}")
    print(
        "run_dir:",
        args.output_dir / run_id,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
