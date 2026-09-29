"""Generate a reproducible DIP-focused CLAHE method visualization.

This is a method/processing illustration, not a primary Experiment-B result.
The production AdaptivePreprocessor is reused with policy="always" so the
CLAHE transform is visible even when the recorded adaptive P1 run resolved
to bypass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import yaml

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    IlluminationMetrics,
    IlluminationState,
    ROI,
    ROIState,
)
from dip_touchless.preprocessing.adaptive_preprocessor import (
    AdaptivePreprocessor,
)
from dip_touchless.preprocessing.illumination import (
    IlluminationAnalyzer,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _load_frame_row(
    frames_csv: Path,
    frame_id: int,
) -> dict[str, str]:
    with frames_csv.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        for row in csv.DictReader(handle):
            if int(row["frame_id"]) == frame_id:
                return row

    raise ValueError(
        f"frame_id {frame_id} not found in {frames_csv}"
    )


def _read_video_frame(
    source: Path,
    frame_id: int,
) -> np.ndarray:
    capture = cv2.VideoCapture(str(source))

    try:
        if not capture.isOpened():
            raise RuntimeError(
                f"could not open source video: {source}"
            )

        if not capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            float(frame_id),
        ):
            raise RuntimeError(
                f"could not seek to frame {frame_id}"
            )

        ok, image = capture.read()

        if not ok or image is None:
            raise RuntimeError(
                f"could not decode frame {frame_id}"
            )

        if (
            image.dtype != np.uint8
            or image.ndim != 3
            or image.shape[2] != 3
        ):
            raise RuntimeError(
                "decoded source frame is not uint8 HxWx3 BGR"
            )

        return image

    finally:
        capture.release()


def _logged_illumination(
    row: dict[str, str],
) -> IlluminationMetrics:
    return IlluminationMetrics(
        mean_v=float(row["mean_v"]),
        std_v=float(row["std_v"]),
        p10_v=float(row["p10_v"]),
        p90_v=float(row["p90_v"]),
        robust_range_v=float(
            row["robust_range_v"]
        ),
        state=IlluminationState[
            row["illumination_state"]
        ],
        enhancement_active=(
            row["enhancement_active"].lower()
            == "true"
        ),
    )


def _validate_descriptors(
    *,
    analyzer: IlluminationAnalyzer,
    packet: FramePacket,
    roi: ROI,
    logged: IlluminationMetrics,
) -> None:
    measured = analyzer.measure(
        packet,
        roi,
    )

    pairs = {
        "mean_v": (
            measured.mean_v,
            logged.mean_v,
        ),
        "std_v": (
            measured.std_v,
            logged.std_v,
        ),
        "p10_v": (
            measured.p10_v,
            logged.p10_v,
        ),
        "p90_v": (
            measured.p90_v,
            logged.p90_v,
        ),
        "robust_range_v": (
            measured.robust_range_v,
            logged.robust_range_v,
        ),
    }

    for name, (
        actual,
        expected,
    ) in pairs.items():
        if not np.isclose(
            actual,
            expected,
            rtol=0.0,
            atol=1e-6,
        ):
            raise RuntimeError(
                f"{name} mismatch: "
                f"decoded={actual}, "
                f"logged={expected}"
            )


def _plot_histogram(
    axis,
    value_channel: np.ndarray,
    title: str,
) -> None:
    axis.hist(
        value_channel.ravel(),
        bins=256,
        range=(0, 256),
    )
    axis.set_xlim(0, 255)
    axis.set_xlabel("V intensity")
    axis.set_ylabel("Pixel count")
    axis.set_title(title)


def generate(
    *,
    run_dir: Path,
    frame_id: int,
    output: Path,
    source_override: Path | None,
) -> None:
    frames_csv = run_dir / "frames.csv"
    metadata_path = run_dir / "metadata.json"
    config_path = run_dir / "resolved_config.yaml"

    row = _load_frame_row(
        frames_csv,
        frame_id,
    )

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    config = yaml.safe_load(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    if source_override is None:
        source = Path(
            metadata["source_data"]["identity"]
        )
    else:
        source = source_override

    if not source.is_file():
        raise FileNotFoundError(source)

    expected_sha256 = metadata[
        "source_data"
    ]["sha256"]

    actual_sha256 = _sha256(source)

    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            "source SHA-256 does not match "
            "the final run metadata"
        )

    image_bgr = _read_video_frame(
        source,
        frame_id,
    )

    roi = ROI(
        x=int(row["roi_x"]),
        y=int(row["roi_y"]),
        width=int(row["roi_width"]),
        height=int(row["roi_height"]),
        state=ROIState[row["roi_state"]],
    )

    packet = FramePacket(
        run_id=row["run_id"],
        frame_id=frame_id,
        timestamp_s=float(
            row["timestamp_s"]
        ),
        image=image_bgr,
        color_space=ColorSpace.BGR,
        source_name=str(source),
    )

    logged_illumination = (
        _logged_illumination(row)
    )

    _validate_descriptors(
        analyzer=IlluminationAnalyzer(),
        packet=packet,
        roi=roi,
        logged=logged_illumination,
    )

    original_roi = image_bgr[
        roi.y : roi.y + roi.height,
        roi.x : roi.x + roi.width,
    ].copy()

    clahe_config = config["clahe"]

    # Intentionally forced for method visualization.
    # This does NOT represent the adaptive P1 outcome of
    # the final Experiment-B run.
    preprocessor = AdaptivePreprocessor(
        policy="always",
        clip_limit=float(
            clahe_config["clip_limit"]
        ),
        tile_grid_size=tuple(
            int(value)
            for value in clahe_config[
                "tile_grid_size"
            ]
        ),
    )

    enhanced = preprocessor.process_roi(
        original_roi,
        logged_illumination,
    )

    if not enhanced.illumination.enhancement_active:
        raise RuntimeError(
            "forced CLAHE visualization "
            "did not activate enhancement"
        )

    reconstructed_roi = enhanced.image_bgr

    original_v = cv2.cvtColor(
        original_roi,
        cv2.COLOR_BGR2HSV,
    )[:, :, 2]

    reconstructed_v = cv2.cvtColor(
        reconstructed_roi,
        cv2.COLOR_BGR2HSV,
    )[:, :, 2]

    fig, axes = plt.subplots(
        2,
        3,
        figsize=(15, 8),
    )

    axes[0, 0].imshow(
        cv2.cvtColor(
            original_roi,
            cv2.COLOR_BGR2RGB,
        )
    )
    axes[0, 0].set_title(
        "Original logged ROI"
    )
    axes[0, 0].axis("off")

    axes[0, 1].imshow(
        original_v,
        cmap="gray",
        vmin=0,
        vmax=255,
    )
    axes[0, 1].set_title(
        "Original HSV V channel"
    )
    axes[0, 1].axis("off")

    _plot_histogram(
        axes[0, 2],
        original_v,
        "Original V histogram",
    )

    axes[1, 0].imshow(
        cv2.cvtColor(
            reconstructed_roi,
            cv2.COLOR_BGR2RGB,
        )
    )
    axes[1, 0].set_title(
        "Reconstructed ROI after CLAHE"
    )
    axes[1, 0].axis("off")

    axes[1, 1].imshow(
        reconstructed_v,
        cmap="gray",
        vmin=0,
        vmax=255,
    )
    axes[1, 1].set_title(
        "V channel after production CLAHE"
    )
    axes[1, 1].axis("off")

    _plot_histogram(
        axes[1, 2],
        reconstructed_v,
        "Post-CLAHE V histogram",
    )

    fig.suptitle(
        "DIP method visualization — "
        f"run {row['run_id']}, frame {frame_id}"
    )

    fig.text(
        0.5,
        0.01,
        (
            "Method illustration only: "
            "production AdaptivePreprocessor "
            'forced with policy="always". '
            "Not a primary P1 adaptive result."
        ),
        ha="center",
    )

    fig.tight_layout(
        rect=(0.0, 0.04, 1.0, 0.95)
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

    provenance = {
        "artifact_type": (
            "DIP method visualization"
        ),
        "primary_experiment_result": False,
        "note": (
            "CLAHE was forced with policy=always "
            "for visual illustration. The final "
            "adaptive P1 run for this frame logged "
            "illumination_state=NORMAL and "
            "enhancement_active=False."
        ),
        "run_id": row["run_id"],
        "experiment_id": metadata[
            "experiment_id"
        ],
        "condition": metadata["condition"],
        "trial_id": metadata["trial_id"],
        "frame_id": frame_id,
        "timestamp_s": float(
            row["timestamp_s"]
        ),
        "tracking_status": row[
            "tracking_status"
        ],
        "roi": {
            "x": roi.x,
            "y": roi.y,
            "width": roi.width,
            "height": roi.height,
            "state": roi.state.name,
        },
        "logged_illumination": {
            "state": (
                logged_illumination.state.name
            ),
            "enhancement_active": (
                logged_illumination
                .enhancement_active
            ),
            "mean_v": (
                logged_illumination.mean_v
            ),
            "std_v": (
                logged_illumination.std_v
            ),
            "p10_v": (
                logged_illumination.p10_v
            ),
            "p90_v": (
                logged_illumination.p90_v
            ),
            "robust_range_v": (
                logged_illumination
                .robust_range_v
            ),
        },
        "visualization_preprocessing": {
            "policy": "always",
            "clip_limit": float(
                clahe_config["clip_limit"]
            ),
            "tile_grid_size": [
                int(value)
                for value in clahe_config[
                    "tile_grid_size"
                ]
            ],
            "production_preprocessor": (
                "dip_touchless.preprocessing."
                "adaptive_preprocessor."
                "AdaptivePreprocessor"
            ),
        },
        "source": {
            "identity": str(source),
            "sha256": actual_sha256,
        },
        "source_run_code_revision": (
            metadata["code_revision"]
        ),
        "source_config_hash": (
            metadata["config_hash"]
        ),
        "spec_version": metadata[
            "spec_version"
        ],
        "log_schema_version": metadata[
            "log_schema_version"
        ],
    }

    provenance_path = output.with_suffix(
        ".json"
    )

    provenance_path.write_text(
        json.dumps(
            provenance,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("generated:", output)
    print("provenance:", provenance_path)
    print(
        "source_sha256:",
        actual_sha256,
    )
    print(
        "logged_state:",
        logged_illumination.state.name,
    )
    print(
        "logged_enhancement_active:",
        logged_illumination
        .enhancement_active,
    )
    print(
        "visualization_enhancement_active:",
        enhanced.illumination
        .enhancement_active,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--frame-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help=(
            "Optional source-video override. "
            "SHA-256 must still match metadata."
        ),
    )

    args = parser.parse_args()

    generate(
        run_dir=args.run_dir,
        frame_id=args.frame_id,
        output=args.output,
        source_override=args.source,
    )


if __name__ == "__main__":
    main()
