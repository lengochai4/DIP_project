"""Validate installed dependencies and model; optional exact snapshot verification."""
from __future__ import annotations

import argparse
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from .setup_ui import MODEL_SHA256, ROOT, sha256, validate_python


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra cài UI, không mở camera.")
    parser.add_argument("--locked", action="store_true", help="Đối chiếu cả snapshot thư viện Python 3.12.")
    args = parser.parse_args()
    errors = []
    print(f"Python: {sys.version.split()[0]} / {struct.calcsize('P') * 8}-bit\n{sys.executable}")
    try:
        validate_python(locked=args.locked)
    except RuntimeError as exc:
        errors.append(str(exc))
    if args.locked:
        for line in (ROOT / "requirements-ui.lock.txt").read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            name, expected = line.split("==", 1)
            try:
                installed = metadata.version(name)
                if installed != expected:
                    errors.append(f"{name}: {installed}; bản khóa là {expected}.")
            except metadata.PackageNotFoundError:
                errors.append(f"Thiếu thư viện {name}.")
    else:
        try:
            from packaging.requirements import Requirement
            # Check this project's direct requirements including installed UI/dev
            # extras; pip check also verifies transitive dependency compatibility.
            for text in metadata.requires("dip-touchless-stem") or ():
                requirement = Requirement(text)
                if requirement.marker and not any(requirement.marker.evaluate({"extra": extra}) for extra in ("", "dev", "demo3d")):
                    continue
                installed = metadata.version(requirement.name)
                if installed not in requirement.specifier:
                    errors.append(f"{requirement.name}: {installed}; yêu cầu {requirement.specifier}.")
            subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
        except (ImportError, metadata.PackageNotFoundError, subprocess.CalledProcessError) as exc:
            errors.append(f"Thư viện chưa đúng yêu cầu pyproject.toml: {exc}")
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runs" / "matplotlib-cache"))
    for name in ("cv2", "numpy", "yaml", "mediapipe", "pygame", "OpenGL.GL", "OpenGL.GLU", "dip_touchless"):
        try:
            importlib.import_module(name)
        except Exception as exc:
            errors.append(f"Không import được {name}: {exc}")
    for relative in ("config/default.yaml", "config/experiments/f2.yaml", "submission/stem_ui/settings.yaml",
                     "submission/stem_ui/physics_labs.yaml"):
        if not (ROOT / relative).is_file():
            errors.append(f"Thiếu {relative}.")
    try:
        elements = json.loads((ROOT / "submission/stem_ui/data/pubchem-periodic-table.json").read_text(encoding="utf-8"))
        if len(elements["Table"]["Row"]) != 118:
            errors.append("Dữ liệu nguyên tố không đủ 118 hàng.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Lỗi dữ liệu nguyên tố: {exc}")
    try:
        from .stem_ui.physics import load_catalog
        if len(load_catalog()['labs'])!=8: errors.append('Dữ liệu thí nghiệm vật lý không đủ 8 bài.')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append(f'Lỗi dữ liệu vật lý: {exc}')
    model = ROOT / "models/hand_landmarker.task"
    if not model.is_file() or sha256(model) != MODEL_SHA256:
        errors.append("Thiếu model hoặc SHA-256 khác bản nộp; chạy cài đặt lại.")
    if not errors:
        try:
            import mediapipe as mp
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2,
            )
            with mp.tasks.vision.HandLandmarker.create_from_options(options):
                pass
        except Exception as exc:
            errors.append(f"Không khởi tạo được model MediaPipe: {exc}")
    if errors:
        for error in errors:
            print("[LỖI] " + error)
        return 1
    print("[OK] Thư viện hợp lệ, tài nguyên đủ, model đúng SHA-256 và khởi tạo được.")
    if args.locked:
        print("[OK] Khớp cả snapshot thư viện Python 3.12.")
    print("Kiểm tra này không mở camera/cửa sổ; quyền camera và OpenGL cần có trên máy chạy UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
