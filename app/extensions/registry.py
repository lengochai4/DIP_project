"""Deterministic local registry; selection always runs deactivate/activate."""

from .labs import (
    CoordinateLab,
    MoleculeLab,
    OrbitalLab,
    VectorLab,
    SurfaceLab,
    WaveLab,
    FieldLab,
    OpticsLab,
    CrystalLab,
)


class ExtensionRegistry:
    def __init__(self, config):
        self.extensions = {
            cls.id: cls(config)
            for cls in (
                CoordinateLab,
                MoleculeLab,
                OrbitalLab,
                VectorLab,
                SurfaceLab,
                WaveLab,
                FieldLab,
                OpticsLab,
                CrystalLab,
            )
        }
        self.current = self.extensions["molecule"]
        self.current.activate()

    def select(self, key):
        target = self.extensions[key]
        self.current.deactivate()
        self.current = target
        self.current.activate()
        return target

    def close(self):
        for extension in self.extensions.values():
            extension.deactivate()
