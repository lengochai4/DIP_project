"""Three separately preregistered supported-hand static trials."""
from datetime import datetime, timezone
import csv
import json
from pathlib import Path

import cv2
import yaml

from dip_touchless.configuration import resolve_config
from dip_touchless.telemetry import build_run_metadata
from experiments.record_source import record_frame_source
from experiments.round2.session import (
    ROOT, WINDOW, make_camera, preflight, PreviewRecordingSource, validate_recorded_source, sha, save_json,
)
from experiments.manifest import load_experiment_manifest
from experiments.run_batch import run_experiment_batch, build_batch_index, write_batch_index
from analysis.regenerate import regenerate_batch

IDENTITY = "ROUND2-20261014-HELD-STATIC"
PLAN = Path(__file__).with_name("HELD_STATIC_PLAN.md")


def manifest_payload(folder: Path):
    payload = yaml.safe_load((ROOT / "experiments/final/g7_a1_static.yaml").read_text(encoding="utf-8"))
    payload["experiment_id"] = IDENTITY
    payload["model"] = str(ROOT / "models/hand_landmarker.task")
    for trial in payload["trials"]:
        trial["source"] = str(folder / "sources" / f"{trial['trial_id']}.avi")
    return payload


def main():
    folder = ROOT / "runs/round2" / IDENTITY
    folder.mkdir(exist_ok=False)
    (folder / "PLAN.md").write_bytes(PLAN.read_bytes())
    (folder / "a1_static.yaml").write_text(yaml.safe_dump(manifest_payload(folder), sort_keys=False), encoding="utf-8")
    resolved = resolve_config(ROOT / "config/default.yaml", overrides={"tracking": {"model_path": str(ROOT / "models/hand_landmarker.task")}, "renderer": {"enabled": False}})
    config = resolved.to_dict()
    metadata = build_run_metadata(resolved, run_id=IDENTITY)
    metadata.update({"session_id": IDENTITY, "camera_config": config["camera"], "status": "collecting",
                     "role": "separate supported-hand A1; original trials retained", "planned_sources": 3,
                     "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "plan_sha256": sha(folder / "PLAN.md"),
                     "manifest_sha256": sha(folder / "a1_static.yaml")})
    save_json(folder / "session.json", metadata)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL); cv2.resizeWindow(WINDOW, 1100, 750)
    try:
        for n in range(1, 4):
            trial = f"trial-{n:03d}"
            preflight(folder, metadata, "static_normal", trial)
            source = PreviewRecordingSource(make_camera(config["camera"], IDENTITY), "static_normal", trial, settle_s=3)
            output = folder / "sources" / f"{trial}.avi"
            record_frame_source(source=source, output_path=output, frame_count=360, encoded_fps=30, settle_s=3,
                requested_camera=config["camera"], lighting_label="normal-room-supported-hand", auto_exposure_status="unknown",
                auto_white_balance_status="unknown", notes="Supported wrist/forearm, stationary fingertip task; no physical ground truth.")
            with output.with_suffix(".timestamps.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(("video_frame_id", "camera_frame_id", "acquisition_timestamp_s")); writer.writerows(source.timeline)
            validate_recorded_source(output)
            print(f"Supported-hand source recorded: {trial}", flush=True)
        metadata["status"] = "recorded"
    except BaseException as error:
        metadata["status"] = "interrupted"; metadata["last_error"] = str(error)
        raise
    finally:
        save_json(folder / "session.json", metadata)
        cv2.destroyAllWindows()
    manifest = load_experiment_manifest(folder / "a1_static.yaml")
    runs = run_experiment_batch(manifest, output_dir=folder / "replay")
    index = write_batch_index(build_batch_index(manifest, runs, manifest_path=folder / "a1_static.yaml"), index_root=folder / "batches")
    result = regenerate_batch(batch_index=index, runs_root=folder / "replay", output_root=folder / "analysis")
    save_json(folder / "analysis_index.json", {"a1_static": str(result)})
    metadata["status"] = "analyzed"; save_json(folder / "session.json", metadata)
    print(f"Analysis: {result}", flush=True)


if __name__ == "__main__": main()
