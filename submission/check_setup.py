"""Validate source assets, exact installed dependencies and model without a webcam."""
from __future__ import annotations

import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import struct
import sys

from .setup_ui import MODEL_SHA256, ROOT, sha256


def main() -> int:
    errors = []
    print(f"Python: {sys.version.split()[0]} / {struct.calcsize('P') * 8}-bit\n{sys.executable}")
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        errors.append("Bản cài nộp được kiểm tra trên Windows / Python 3.12 64-bit.")
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
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runs" / "matplotlib-cache"))
    for name in ("cv2", "numpy", "yaml", "mediapipe", "pygame", "OpenGL.GL", "OpenGL.GLU", "dip_touchless"):
        try:
            importlib.import_module(name)
        except Exception as exc:
            errors.append(f"Không import được {name}: {exc}")
    for relative in ("config/default.yaml", "config/experiments/f2.yaml", "submission/stem_ui/settings.yaml"):
        if not (ROOT / relative).is_file():
            errors.append(f"Thiếu {relative}.")
    try:
        elements = json.loads((ROOT / "submission/stem_ui/data/pubchem-periodic-table.json").read_text(encoding="utf-8"))
        if len(elements["Table"]["Row"]) != 118:
            errors.append("Dữ liệu nguyên tố không đủ 118 hàng.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Lỗi dữ liệu nguyên tố: {exc}")
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
    print("[OK] Thư viện khớp bản khóa, tài nguyên đủ, model đúng SHA-256 và khởi tạo được.")
    print("Kiểm tra này không mở camera/cửa sổ; quyền camera và OpenGL cần có trên máy chạy UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
