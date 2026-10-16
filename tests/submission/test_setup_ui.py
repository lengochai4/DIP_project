"""Model provenance and non-destructive installation behavior."""
import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from submission import setup_ui


@pytest.mark.parametrize("version", [(3, 11), (3, 12), (3, 13), (3, 14)])
def test_bootstrap_accepts_declared_python_floor_without_claiming_wheel_support(version):
    setup_ui.validate_python(version=version, platform="win32", bits=64)


@pytest.mark.parametrize("version,platform,bits", [((3, 10), "win32", 64), ((3, 11), "win32", 32), ((3, 11), "linux", 64)])
def test_windows_bootstrap_rejects_incompatible_interpreter(version, platform, bits):
    with pytest.raises(RuntimeError):
        setup_ui.validate_python(version=version, platform=platform, bits=bits)


def test_snapshot_is_opt_in_and_does_not_restrict_normal_python311_install():
    normal = setup_ui.pip_install_args()
    locked = setup_ui.pip_install_args(locked=True)
    assert "requirements-ui.lock.txt" not in normal
    assert "--only-binary=:all:" in normal
    assert normal[-2:] == ["-e", ".[dev,demo3d]"]
    assert "requirements-ui.lock.txt" in locked
    setup_ui.validate_python(version=(3, 12), platform="win32", bits=64, locked=True)
    with pytest.raises(RuntimeError, match="--locked"):
        setup_ui.validate_python(version=(3, 11), platform="win32", bits=64, locked=True)


def test_download_is_verified_before_installing(tmp_path, monkeypatch):
    payload = b"verified-model-test-fixture"
    monkeypatch.setattr(setup_ui, "MODEL_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(setup_ui.urllib.request, "urlopen", lambda *a, **kw: BytesIO(payload))
    target = setup_ui.ensure_model(tmp_path)
    assert target.read_bytes() == payload
    assert list(target.parent.iterdir()) == [target]


def test_corrupt_download_is_not_installed_and_temporary_is_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_ui.urllib.request, "urlopen", lambda *a, **kw: BytesIO(b"corrupt"))
    with pytest.raises(RuntimeError, match="SHA-256"):
        setup_ui.ensure_model(tmp_path)
    assert list((tmp_path / "models").iterdir()) == []


def test_existing_different_model_is_preserved_without_network(tmp_path, monkeypatch):
    folder = tmp_path / "models"
    folder.mkdir()
    target = folder / "hand_landmarker.task"
    target.write_bytes(b"custom-local-model")
    monkeypatch.setattr(setup_ui.urllib.request, "urlopen", lambda *a, **kw: pytest.fail("network must not be called"))
    with pytest.raises(RuntimeError, match="hiện có"):
        setup_ui.ensure_model(tmp_path)
    assert target.read_bytes() == b"custom-local-model"


def test_existing_matching_model_is_reused_offline(tmp_path, monkeypatch):
    target = tmp_path / "models" / "hand_landmarker.task"
    target.parent.mkdir()
    target.write_bytes(b"known-good")
    monkeypatch.setattr(setup_ui, "MODEL_SHA256", setup_ui.sha256(target))
    monkeypatch.setattr(setup_ui.urllib.request, "urlopen", lambda *a, **kw: pytest.fail("offline reuse"))
    assert setup_ui.ensure_model(tmp_path) == target


def test_interrupted_download_removes_only_its_temporary_file(tmp_path, monkeypatch):
    folder = tmp_path / "models"
    folder.mkdir()
    unrelated = folder / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    def failed_request(*args, **kwargs):
        raise OSError("network interrupted")
    monkeypatch.setattr(setup_ui.urllib.request, "urlopen", failed_request)
    with pytest.raises(OSError, match="interrupted"):
        setup_ui.ensure_model(tmp_path)
    assert list(folder.iterdir()) == [unrelated]
