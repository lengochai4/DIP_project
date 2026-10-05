"""Export local educational constructions; no camera, hands or session references."""

import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np


@dataclass(frozen=True)
class MeasurementSnapshot:
    id: str
    preset: str
    config: object
    constructions: tuple

    def export_constructions(self):
        return self.constructions


def snapshot(lab):
    return MeasurementSnapshot(
        lab.id,
        lab.preset,
        lab.config,
        tuple(
            (kind, tuple(tuple(float(v) for v in p) for p in points))
            for kind, points in lab.export_constructions()
        ),
    )


def export_csv(lab, path):
    destination = Path(path).resolve()
    temporary = None
    try:
        with NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
        _write_csv(lab, temporary)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_csv(lab, path):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "lab",
                "preset",
                "tool",
                "points_scene_xyz",
                "distance_scene_units",
                "vector_scene_xyz",
                "angle_degrees",
                "triangle_area_scene_units_squared",
            )
        )
        for tool, points in lab.export_constructions():
            p = np.asarray(points, dtype=float)
            vector = p[1] - p[0] if len(p) >= 2 else None
            angle = area = ""
            if len(p) >= 3:
                a, b = p[0] - p[1], p[2] - p[1]
                denom = np.linalg.norm(a) * np.linalg.norm(b)
                if denom > lab.config.palm_epsilon:
                    angle = math.degrees(
                        math.acos(float(np.clip(np.dot(a, b) / denom, -1, 1)))
                    )
                area = float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) / 2)
            writer.writerow(
                (
                    lab.id,
                    lab.preset,
                    tool,
                    json.dumps(p.tolist()),
                    float(np.linalg.norm(vector)) if vector is not None else "",
                    json.dumps(vector.tolist()) if vector is not None else "",
                    angle,
                    area,
                )
            )
