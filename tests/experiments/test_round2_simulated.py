import csv
import json

import cv2
import numpy as np
import pytest

from experiments.round2.simulated_study import attenuate, derive
from experiments.round2.session import sha


def test_attenuation_is_fixed_all_channel_transform_without_mutating_input():
    source = np.array([[[200, 100, 0], [255, 255, 255]]], dtype=np.uint8)
    before = source.copy()
    output = attenuate(source)
    np.testing.assert_array_equal(output, [[[70, 35, 0], [89, 89, 89]]])
    np.testing.assert_array_equal(source, before)
    assert output.dtype == np.uint8 and output.shape == source.shape


@pytest.mark.parametrize("gain", [0, 1, -1, float("nan"), float("inf")])
def test_invalid_attenuation_is_not_a_plausible_source(gain):
    with pytest.raises(ValueError): attenuate(np.zeros((2, 2, 3), dtype=np.uint8), gain)


def test_derivation_preserves_source_identity_timeline_and_simulated_label(tmp_path):
    source = tmp_path / "original.avi"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 30, (32, 24))
    assert writer.isOpened()
    for _ in range(360): writer.write(np.full((24, 32, 3), 200, dtype=np.uint8))
    writer.release()
    metadata = {"video": {"encoded_width": 32, "encoded_height": 24, "encoded_fps": 30, "frame_count": 360, "sha256": sha(source)},
                "lighting": {"label": "fixture", "auto_exposure": "unknown"}, "acquisition": {"source_timestamp_span_s": 359/30}}
    source.with_suffix(".json").write_text(json.dumps(metadata))
    with source.with_suffix(".timestamps.csv").open("w", newline="") as f:
        output = csv.writer(f); output.writerow(["video_frame_id", "camera_frame_id", "acquisition_timestamp_s"])
        output.writerows((n, n, n/30) for n in range(360))
    original_hash = sha(source)
    destination = tmp_path / "derived" / "dim.avi"
    sidecar = derive(source, destination)
    assert sha(source) == original_hash
    assert sidecar["processing"]["source_sha256"] == original_hash
    assert sidecar["processing"]["gain"] == .35
    assert sidecar["lighting"]["label"] == "simulated-input-attenuation"
    assert sidecar["acquisition"]["inherited_from_source"] is True
    assert destination.with_suffix(".timestamps.csv").read_bytes() == source.with_suffix(".timestamps.csv").read_bytes()
    cap = cv2.VideoCapture(str(destination)); ok, image = cap.read(); cap.release()
    assert ok and np.all(np.abs(image.astype(int)-70) <= 2)
    with pytest.raises(FileExistsError): derive(source, destination)
