from pathlib import Path
import json
import zipfile
import pytest
from developer_tools import package_application as package


def test_review_package_contains_application_resources_hashes_and_no_local_data(tmp_path, monkeypatch):
    root = tmp_path/"source"
    root.mkdir()
    for name in ("README.md", "extensions/stem3d/app.py", "config/extensions/application.yaml", "models/README.md"):
        p = root/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text("synthetic package fixture",encoding="utf-8")
    monkeypatch.setattr(package,"ROOT",root)
    monkeypatch.setattr(package,"verify_frozen",lambda: None)
    monkeypatch.setattr(package,"git",lambda *args:
        "\n".join(("README.md", "extensions/stem3d/app.py", "config/extensions/application.yaml", "models/README.md",
                   "runs/private.json", "models/hand_landmarker.task", "extensions/__pycache__/x.pyc"))
        if args[0] == "ls-files" else "dirty" if args[0] == "status" else "fixture-revision")
    path = tmp_path/"review.zip"
    manifest = package.build_package(path)
    assert len(manifest["files"]) == 4 and manifest["dirty_tree"] and not manifest["publication"]
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert not any("private" in n or ".task" in n or "__pycache__" in n for n in archive.namelist())
        assert json.loads(archive.read("DIP_project/SOURCE_SNAPSHOT.json"))["revision"] == "fixture-revision"
    with pytest.raises(FileExistsError): package.build_package(path)


def test_wrong_frozen_tag_blocks_packaging(monkeypatch):
    monkeypatch.setattr(package,"git",lambda *args: "wrong-revision")
    with pytest.raises(ValueError,match="Frozen tag"):
        package.verify_frozen()
