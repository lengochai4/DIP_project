"""Controlled input-attenuation study, explicitly distinct from physical low light."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
import yaml

from analysis.regenerate import regenerate_batch
from experiments.manifest import load_experiment_manifest
from experiments.run_batch import run_experiment_batch, build_batch_index, write_batch_index
from experiments.round2.session import ROOT, sha, save_json, verify_session, validate_recorded_source

GAIN = .35
PLAN = Path(__file__).with_name("SIMULATED_PLAN.md")
NAMES = ("a1_static", "a2_dynamic", "b_normal", "b_simulated")


def attenuate(image: np.ndarray, gain: float = GAIN) -> np.ndarray:
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("attenuation requires HxWx3 uint8 BGR")
    if not np.isfinite(gain) or not 0 < gain < 1:
        raise ValueError("gain must be finite and between zero and one")
    return np.rint(image.astype(np.float32) * gain).astype(np.uint8)


def derive(source: Path, output: Path) -> dict:
    metadata = validate_recorded_source(source)
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = metadata["video"]["encoded_width"], metadata["video"]["encoded_height"]
    fps = metadata["video"]["encoded_fps"]
    capture = cv2.VideoCapture(str(source))
    writer = None
    count = 0
    success = False
    try:
        if not capture.isOpened(): raise ValueError(f"cannot read {source}")
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
        if not writer.isOpened(): raise RuntimeError(f"cannot write {output}")
        while True:
            ok, image = capture.read()
            if not ok: break
            writer.write(attenuate(image))
            count += 1
        if count != metadata["video"]["frame_count"]:
            raise ValueError("source decoded count differs from frozen metadata")
        success = True
    finally:
        capture.release()
        if writer is not None: writer.release()
        if not success: output.unlink(missing_ok=True)
    payload = dict(metadata)
    payload["video"] = dict(metadata["video"], path=str(output), sha256=sha(output))
    payload["lighting"] = dict(metadata["lighting"], label="simulated-input-attenuation", notes="Digital BGR gain 0.35; NOT physical low-light capture.")
    payload["processing"] = {"preprocessing": "controlled_linear_attenuation", "gain": GAIN, "formula": "round(BGR * 0.35)",
                             "source_path": str(source), "source_sha256": sha(source), "codec": "MJPG re-encoding"}
    payload["derived_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["acquisition"] = dict(metadata["acquisition"], inherited_from_source=True)
    save_json(output.with_suffix(".json"), payload)
    shutil.copyfile(source.with_suffix(".timestamps.csv"), output.with_suffix(".timestamps.csv"))
    validate_recorded_source(output)
    return payload


def prepare_study(source_session: Path, *, study_id="ROUND2-20261014-SIM035") -> Path:
    session = verify_session(source_session)
    folder = source_session.parent / study_id
    if folder.exists(): raise FileExistsError(folder)
    inputs = {group: [source_session / "sources" / group / f"trial-{n:03d}.avi" for n in range(1, 4)]
              for group in ("static_normal", "dynamic_normal")}
    for paths in inputs.values():
        for path in paths: validate_recorded_source(path)
    folder.mkdir()
    (folder / "PLAN.md").write_bytes(PLAN.read_bytes())
    study = {"study_id": study_id, "source_session": str(source_session), "status": "planned", "gain": GAIN,
             "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "simulated image-domain attenuation, not real environmental low light",
             "plan_sha256": sha(folder / "PLAN.md"), "source_sha256": {str(p): sha(p) for paths in inputs.values() for p in paths},
             "source_environment": {k: session[k] for k in ("python_version", "dependency_versions", "provider", "code_revision")}}
    save_json(folder / "study.json", study)
    # Establish all source choices before generating any result.
    for name in NAMES:
        template = "b_lowlight" if name == "b_simulated" else name
        data = yaml.safe_load((source_session / f"{template}.yaml").read_text(encoding="utf-8"))
        data["experiment_id"] = f"{study_id}-{name.upper()}"
        group = "dynamic_normal" if name == "a2_dynamic" else "static_normal"
        for trial, source in zip(data["trials"], inputs[group]):
            trial["source"] = str(folder / "sources/simulated" / source.name) if name == "b_simulated" else str(source)
        (folder / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    study["manifest_sha256"] = {name: sha(folder / f"{name}.yaml") for name in NAMES}
    save_json(folder / "study.json", study)
    for source in inputs["static_normal"]:
        derive(source, folder / "sources/simulated" / source.name)
    study["status"] = "sources_ready"
    save_json(folder / "study.json", study)
    return folder


def run_study(folder: Path) -> dict:
    study = json.loads((folder / "study.json").read_text(encoding="utf-8"))
    verify_session(Path(study["source_session"]))
    if sha(folder / "PLAN.md") != study["plan_sha256"]: raise ValueError("study plan changed")
    for path, digest in study["source_sha256"].items():
        if sha(Path(path)) != digest: raise ValueError(f"source changed: {path}")
    for name, digest in study["manifest_sha256"].items():
        if sha(folder / f"{name}.yaml") != digest: raise ValueError(f"manifest changed: {name}")
    outputs = {}
    for name in NAMES:
        print(f"Paired replay: {name}", flush=True)
        manifest = load_experiment_manifest(folder / f"{name}.yaml")
        for trial in manifest.trials: validate_recorded_source(trial.source)
        runs = run_experiment_batch(manifest, output_dir=folder / "replay")
        index = write_batch_index(build_batch_index(manifest, runs, manifest_path=folder / f"{name}.yaml"), index_root=folder / "batches")
        outputs[name] = str(regenerate_batch(batch_index=index, runs_root=folder / "replay", output_root=folder / "analysis"))
    save_json(folder / "analysis_index.json", outputs)
    study["status"] = "analyzed"
    save_json(folder / "study.json", study)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-session", type=Path, required=True)
    parser.add_argument("--study", type=Path, help="analyze an already prepared study")
    args = parser.parse_args()
    folder = args.study or prepare_study(args.source_session.resolve())
    print(f"Study: {folder}", flush=True)
    print(json.dumps(run_study(folder), indent=2), flush=True)


if __name__ == "__main__": main()
