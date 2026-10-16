"""Install the submission from a source checkout using Python's standard library."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ensure_model(root: Path = ROOT) -> Path:
    """Download the pinned model atomically; never replace a different local model."""
    target = root / "models" / "hand_landmarker.task"
    if target.is_file():
        if sha256(target) != MODEL_SHA256:
            raise RuntimeError(
                "Model hiện có khác SHA-256 bản nộp. Hãy giữ bản sao rồi đổi tên "
                "models/hand_landmarker.task và chạy cài đặt lại."
            )
        print("Model: SHA-256 đúng bản đã kiểm tra.", flush=True)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download", delete=False) as f:
        temporary = Path(f.name)
    try:
        print("Đang tải Hand Landmarker từ Google…", flush=True)
        with urllib.request.urlopen(MODEL_URL, timeout=90) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(temporary) != MODEL_SHA256:
            raise RuntimeError("SHA-256 model tải về không khớp; không sử dụng file này.")
        # A concurrent setup must not silently replace a model that appeared meanwhile.
        if target.exists():
            if not target.is_file() or sha256(target) != MODEL_SHA256:
                raise RuntimeError("Model đích đã thay đổi trong khi tải; giữ nguyên file đích.")
        else:
            temporary.rename(target)
        print("Model đã tải và kiểm tra SHA-256.", flush=True)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    try:
        if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
            raise RuntimeError("Bộ cài đã chốt cho Windows và Python 3.12 64-bit. Chạy: py -3.12 -m submission.setup_ui")
        folder = ROOT / ".venv-ui"
        python = folder / "Scripts" / "python.exe"
        if folder.exists():
            if not python.is_file():
                raise RuntimeError(".venv-ui chưa hoàn chỉnh. Hãy đổi tên thư mục này rồi cài lại.")
            subprocess.run(
                [str(python), "-c", "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8"],
                cwd=ROOT, check=True,
            )
        else:
            print("Tạo .venv-ui riêng cho bản nộp…", flush=True)
            venv.EnvBuilder(with_pip=True).create(folder)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", "requirements-ui.lock.txt", "-e", ".[dev,demo3d]"],
            cwd=ROOT, check=True,
        )
        ensure_model()
        subprocess.run([str(python), "-X", "utf8", "-m", "submission.check_setup"], cwd=ROOT, check=True)
        print("\nCài đặt hoàn tất. Chạy Chay_UI.bat hoặc:", flush=True)
        print(r".\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nCài đặt chưa hoàn tất: {exc}", file=sys.stderr)
        print("Xem HUONG_DAN_CHAY.md; kiểm tra Internet, Python 3.12 và thông báo phía trên.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
