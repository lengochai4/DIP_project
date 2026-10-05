"""Verify extracted source delivery with an existing or freshly installed environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from app.config import ROOT

WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}


def validate_archive(archive, directory):
    """Check local package integrity before extracting/executing; not a signature."""
    names = archive.namelist()
    if len({n.casefold() for n in names}) != len(names):
        raise ValueError("duplicate archive paths")
    for name in names:
        parts = name.split("/")
        if any(
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.partition(".")[0].rstrip().upper() in WINDOWS_DEVICES
            or any(char in '<>:"\\|?*' or ord(char) < 32 for char in part)
            for part in parts
        ):
            raise ValueError("unsafe archive path")
        target = (directory / name).resolve()
        if not target.is_relative_to(directory):
            raise ValueError("archive path escapes verification directory")
    if archive.testzip() is not None:
        raise ValueError("corrupt archive")
    manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
    files = manifest["files"]
    if set(names) != set(files) | {"PACKAGE_MANIFEST.json"}:
        raise ValueError("archive contents differ from manifest")
    for name, expected in files.items():
        if hashlib.sha256(archive.read(name)).hexdigest() != expected:
            raise ValueError(f"package hash mismatch: {name}")


SMOKE = """
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import QApplication
from app.config import ROOT, ProductConfig, Settings
from app.ui.shell import ProductWindow
from app.runtime.hand_runtime import ProductHandRuntime
from dip_touchless.configuration import resolve_config
from dip_touchless.core import FramePacket, ColorSpace
assert ROOT == Path.cwd()
application = QApplication([])
window = ProductWindow(ProductConfig.load(), Settings(), software=True)
window.show()
application.processEvents()
window.navigate("Explore")
application.processEvents()
assert not window.viewport.grab().isNull()
assert (ROOT / "models/hand_landmarker.task").is_file()
window.close()
runtime = ProductHandRuntime(ROOT / "models/hand_landmarker.task",
                            resolve_config(ROOT / "config/default.yaml").to_dict(),
                            ProductConfig.load())
try:
    hands, valid, reason = runtime.process(FramePacket("install-smoke", 0, 1.0,
        np.zeros((480, 640, 3), np.uint8), ColorSpace.BGR, "synthetic blank image"))
    assert not hands and not valid
finally:
    runtime.close()
print("Extracted V2 source, resources, native UI, model inference and cleanup: passed (no webcam)")
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "runs/releases/dip-touchless-stem-2.0.0rc1.zip",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runs/releases/extracted-v2-check"
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Dependency environment to verify; use the extracted .venv for a fresh setup check",
    )
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Verify extraction/UI/model without repeating already-passed regression",
    )
    args = parser.parse_args(argv)
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        validate_archive(archive, directory)
        archive.extractall(directory)
    env = dict(
        os.environ, PYTHONPATH=str(directory / "src") + os.pathsep + str(directory)
    )
    python = str(args.python.resolve())
    subprocess.run([python, "-c", SMOKE], cwd=directory, env=env, check=True)
    if not args.smoke_only:
        subprocess.run(
            [python, "-m", "pytest", "-q", "--tb=short"],
            cwd=directory,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
