import hashlib
import io
import json
import zipfile
import pytest
from developer_tools.verify_v2_package import validate_archive


@pytest.mark.parametrize(
    "name",
    [
        "app/../app/main.py",
        "app/./main.py",
        "app//main.py",
        "app/main.py.",
        "app /main.py",
        "app/NUL.txt",
        "app/COM¹.py",
        "app/bad?.py",
    ],
)
def test_archive_rejects_windows_aliases_and_device_names(tmp_path, name):
    stream = io.BytesIO()
    content = b"source"
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, content)
        archive.writestr(
            "PACKAGE_MANIFEST.json",
            json.dumps({"files": {name: hashlib.sha256(content).hexdigest()}}),
        )
    with zipfile.ZipFile(stream) as archive:
        with pytest.raises(ValueError):
            validate_archive(archive, tmp_path.resolve())


@pytest.mark.parametrize(
    "problem", [None, "hash", "extra", "traversal", "duplicate", "windows_path"]
)
def test_package_rejects_altered_or_unsafe_members_before_execution(tmp_path, problem):
    stream = io.BytesIO()
    name = "app/main.py"
    if problem == "traversal":
        name = "../outside.py"
    if problem == "windows_path":
        name = "C:\\outside.py"
    content = b"print('local source')"
    files = {name: hashlib.sha256(content).hexdigest()}
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, b"modified" if problem == "hash" else content)
        if problem == "extra":
            archive.writestr("extra.py", b"extra")
        if problem == "duplicate":
            archive.writestr("APP/main.py", content)
        archive.writestr("PACKAGE_MANIFEST.json", json.dumps({"files": files}))
    with zipfile.ZipFile(stream) as archive:
        if problem is None:
            validate_archive(archive, tmp_path.resolve())
        else:
            with pytest.raises(ValueError):
                validate_archive(archive, tmp_path.resolve())
