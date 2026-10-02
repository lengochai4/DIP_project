"""Reproducible source archive with content manifest; no environment or private runs."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from app.config import ROOT

MODEL_HASH = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


def build(output, *, include_model=False):
    paths = []
    for name in (
        "app",
        "src",
        "extensions",
        "config",
        "docs",
        "tests",
        "models",
        "submission",
        "experiments",
        "analysis",
        "release/v2",
        "developer_tools",
    ):
        directory = ROOT / name
        if directory.exists():
            paths.extend(
                p
                for p in directory.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and not any(part.endswith(".egg-info") for part in p.parts)
                and not p.suffix in {".pyc", ".task"}
                and not any(x.startswith(".") for x in p.relative_to(ROOT).parts)
            )
    paths.extend(
        ROOT / name
        for name in (
            "pyproject.toml",
            "README.md",
            "AGENTS.md",
            "FINAL_REPORT.md",
            "launch_v2.ps1",
            "setup_v2.ps1",
        )
        if (ROOT / name).exists()
    )
    if include_model:
        path = ROOT / "models/hand_landmarker.task"
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_HASH
        ):
            raise ValueError("missing or mismatched model; see models/README.md")
        paths.append(path)
    paths = sorted(set(paths))
    manifest = {
        "version": "2.0.0rc1",
        "physical_validation": "NOT RUN",
        "model_included": include_model,
        "files": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    def add(archive, name, data):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 2, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, data)

    with zipfile.ZipFile(output, "w") as archive:
        for path in paths:
            add(archive, path.relative_to(ROOT).as_posix(), path.read_bytes())
        add(
            archive,
            "PACKAGE_MANIFEST.json",
            json.dumps(manifest, indent=2).encode("utf-8"),
        )
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runs/releases/dip-touchless-stem-2.0.0rc1.zip",
    )
    parser.add_argument("--include-model", action="store_true")
    args = parser.parse_args(argv)
    manifest = build(args.output, include_model=args.include_model)
    print(f"Verified {len(manifest['files'])} files in {args.output}")


if __name__ == "__main__":
    main()
