import csv
import pytest
from app.config import ProductConfig
from app.extensions.registry import ExtensionRegistry
from app.extensions.measurement_export import export_csv


@pytest.mark.parametrize("failure", ["write", "replace"])
def test_csv_failure_keeps_previous_export_and_cleans_only_its_temp_file(
    tmp_path, monkeypatch, failure
):
    from pathlib import Path

    lab = ExtensionRegistry(ProductConfig()).current
    lab.constructions = [("Distance", ((0, 0, 0), (3, 4, 0)))]
    path = tmp_path / "measurements.csv"
    path.write_text("previous export", encoding="utf-8")
    if failure == "write":
        real_writer = csv.writer

        class FailedWriter:
            def __init__(self, stream):
                self.real = real_writer(stream)
                self.rows = 0

            def writerow(self, row):
                self.rows += 1
                if self.rows > 1:
                    raise OSError("simulated disk write failure")
                self.real.writerow(row)

        monkeypatch.setattr(csv, "writer", FailedWriter)
    else:
        monkeypatch.setattr(
            Path,
            "replace",
            lambda *args: (_ for _ in ()).throw(PermissionError("destination locked")),
        )
    with pytest.raises(OSError):
        export_csv(lab, path)
    assert path.read_text(encoding="utf-8") == "previous export"
    assert list(tmp_path.iterdir()) == [path]
