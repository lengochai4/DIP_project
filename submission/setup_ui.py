"""Install the submission from a source checkout using Python's standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


def validate_python(version=None, platform=None, bits=None, *, locked=False) -> None:
    """Match the declared Python floor; the frozen snapshot is an optional profile."""
    version = sys.version_info[:2] if version is None else tuple(version[:2])
    platform = sys.platform if platform is None else platform
    bits = struct.calcsize("P") * 8 if bits is None else bits
    requirement = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["requires-python"]
    # This bootstrap runs before packaging is installed. Fail explicitly if the
    # project's currently simple >=major.minor contract changes shape.
    import re
    match = re.fullmatch(r">=(\d+)\.(\d+)", requirement.strip())
    if match is None:
        raise RuntimeError(f"Cần cập nhật bootstrap cho requires-python = {requirement!r}.")
    minimum = tuple(map(int, match.groups()))
    if platform != "win32" or version < minimum or bits != 64:
        raise RuntimeError(f"Bộ cài Windows yêu cầu Python {requirement} 64-bit theo pyproject.toml.")
    if locked and version != (3, 12):
        raise RuntimeError("--locked tái hiện snapshot Python 3.12; bỏ --locked để cài theo pyproject.toml.")


def pip_install_args(*, locked=False) -> list[str]:
    args = ["-m", "pip", "install", "--only-binary=:all:"]
    if locked:
        args += ["-r", "requirements-ui.lock.txt"]
    return args + ["-e", ".[dev,demo3d]"]


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
    parser = argparse.ArgumentParser(description="Cài UI theo pyproject.toml bằng Python đang chọn.")
    parser.add_argument("--locked", action="store_true", help="Tái hiện snapshot đã kiểm tra trên Python 3.12.")
    args = parser.parse_args()
    try:
        validate_python(locked=args.locked)
        print(f"Python {sys.version.split()[0]} · chế độ {'snapshot 3.12' if args.locked else 'theo pyproject.toml'}", flush=True)
        folder = ROOT / ".venv-ui"
        python = folder / "Scripts" / "python.exe"
        if folder.exists():
            if not python.is_file():
                raise RuntimeError(".venv-ui chưa hoàn chỉnh. Hãy đổi tên thư mục này rồi cài lại.")
            subprocess.run(
                [str(python), "-c", "import sys,struct; assert sys.version_info[:2]==tuple(map(int,sys.argv[1:3])) and struct.calcsize('P')==8", str(sys.version_info.major), str(sys.version_info.minor)],
                cwd=ROOT, check=True,
            )
        else:
            print("Tạo .venv-ui riêng cho bản nộp…", flush=True)
            venv.EnvBuilder(with_pip=True).create(folder)
        subprocess.run(
            [str(python), *pip_install_args(locked=args.locked)],
            cwd=ROOT, check=True,
        )
        ensure_model()
        check = [str(python), "-X", "utf8", "-m", "submission.check_setup"]
        if args.locked:
            check.append("--locked")
        subprocess.run(check, cwd=ROOT, check=True)
        record = ROOT / "runs" / "ui-install" / "environment.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        installed = subprocess.check_output([str(python), "-m", "pip", "freeze"], cwd=ROOT, text=True, encoding="utf-8")
        record.write_text(json.dumps({
            "python": sys.version, "locked_snapshot": args.locked,
            "model_sha256": MODEL_SHA256, "pip_freeze": installed.splitlines(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nCài đặt hoàn tất. Chạy Chay_UI.bat hoặc:", flush=True)
        print(r".\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nCài đặt chưa hoàn tất: {exc}", file=sys.stderr)
        print("Xem HUONG_DAN_CHAY.md; kiểm tra Python >=3.11 64-bit, Internet và thông báo phía trên.", file=sys.stderr)
        print("Nếu .venv-ui khác phiên bản Python đang chọn, dùng đúng Python cũ hoặc đổi tên .venv-ui trước khi cài lại.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
