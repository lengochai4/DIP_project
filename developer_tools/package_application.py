"""Build a reviewable source snapshot without staging/committing or bundling local runs."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"src", "extensions", "application_adapters", "config", "tests", "docs", "submission",
           "experiments", "analysis", "developer_tools", "release", "models"}
ROOT_FILES = {"README.md", "pyproject.toml", "AGENTS.md", "FINAL_REPORT.md", "launch_application.ps1", ".gitignore"}
FROZEN_TAGS = {"g7-final": "f454c6b8325c85199c0122c0e822fe8e76c1526c",
               "dip-touchless-stem-v1.0": "2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2"}
FROZEN_PATHS = ("src", "FINAL_REPORT.md", "submission/evidence", "experiments/final")
FORBIDDEN_G9 = ("product_interaction", "product_demo.py", "07_G9_PRODUCT_INTERACTION.md", "product_interaction.yaml")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def files_for_package():
    paths = []
    for relative in git("ls-files", "--cached", "--others", "--exclude-standard").splitlines():
        p = Path(relative)
        if p.parts[0] not in ALLOWED and p.as_posix() not in ROOT_FILES:
            continue
        if any(part in {"__pycache__", ".pytest_cache", ".git", ".venv"} for part in p.parts):
            continue
        if p.suffix in {".task", ".pyc", ".pyo"}:
            continue
        if any(part in FORBIDDEN_G9 for part in p.parts):
            raise ValueError(f"Deferred G9 file present: {p}")
        if (ROOT/p).is_file():
            paths.append(p)
    return sorted(set(paths), key=lambda p: p.as_posix())


def verify_frozen():
    for tag, expected in FROZEN_TAGS.items():
        if git("rev-parse", f"{tag}^{{commit}}") != expected:
            raise ValueError(f"Frozen tag identity changed: {tag}")
    if git("diff", "g7-final", "--", *FROZEN_PATHS):
        raise ValueError("Frozen Core/G7 paths differ")
    for name in git("ls-files", "--others", "--exclude-standard").splitlines():
        if any(name == p or name.startswith(p+"/") for p in FROZEN_PATHS):
            raise ValueError(f"Untracked file under a frozen path: {name}")
    for p in ("config/product_interaction.yaml", "docs/07_G9_PRODUCT_INTERACTION.md",
              "extensions/stem3d/product_demo.py", "extensions/stem3d/product_interaction",
              "tests/extensions/product_interaction"):
        if (ROOT/p).exists(): raise ValueError(f"Deferred G9 path present: {p}")


def build_package(output):
    verify_frozen()
    files = files_for_package()
    manifest = dict(schema="stem-source-snapshot-v1.1", revision=git("rev-parse", "HEAD"),
        dirty_tree=bool(git("status", "--porcelain")), publication=False,
        validation="physical v1.1 acceptance pending; local review snapshot",
        model="separate download/checksum: models/README.md", frozen_tags=FROZEN_TAGS,
        files={p.as_posix():hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Refuse overwrite so an earlier handoff is not silently replaced.
    with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED) as archive:
        for p in files: archive.write(ROOT/p, f"DIP_project/{p.as_posix()}")
        archive.writestr("DIP_project/SOURCE_SNAPSHOT.json",json.dumps(manifest,indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None: raise OSError("Archive CRC failed")
        for name, sha in manifest["files"].items():
            if hashlib.sha256(archive.read(f"DIP_project/{name}")).hexdigest() != sha:
                raise OSError(f"Packaged hash mismatch: {name}")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"runs/distribution/DIP-Touchless-STEM-v1.1-review.zip")
    args = parser.parse_args(argv)
    manifest = build_package(args.output)
    print(json.dumps(dict(output=str(args.output),files=len(manifest["files"]),dirty_tree=manifest["dirty_tree"],crc="PASS")))


if __name__ == "__main__": main()
