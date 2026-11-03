# DIP Touchless STEM v1.0 — release notes

**Review: READY TO RELEASE (2026-10-01).** Recommended application tag:
`dip-touchless-stem-v1.0`, on the final reviewed documentation commit.
No commit or tag has been created by this review. The application code tested
in R3 is revision `21ab8cddf037c9f21f33ca6f2ec8fb237eaebb72`; pending changes
are release documentation only.

## Included

- Final integrated desktop application: Workspace, Analysis, read-only Evidence,
  Coordinate Geometry, Water/Methane and the educational Orbital scene.
- Existing one-hand index-motion rotation, pinch scaling, Control Space,
  keyboard fallback, Reset and explicit startup/error/shutdown states.
- Setup/package guides and application walkthrough.
- Fifteen labelled synthetic 1600 × 900 presentation screenshots, contact sheet
  and source/hash manifest in [screenshots/](screenshots/README.md).
- [Physical R3 smoke record](R3_PHYSICAL_SMOKE.md): real runs
  `g8-demo-20261001-184630` (1,197 frames) and `g8-demo-20261001-184818`
  (2,666 frames). All twelve checklist items were user-confirmed; direct UI/log
  observations are distinguished in the record. Both processes closed cleanly.

## Setup and launch

Use the repository source tree, Python 3.11, a webcam and an OpenGL-capable desktop.
From the root in an activated environment:

```powershell
python -m pip install -e ".[dev,demo3d]"
python -m extensions.stem3d.live_demo
```

Prepare `models/hand_landmarker.task` using the download and SHA-256 instructions
in [models/README.md](../models/README.md) before going offline. The ignored model
is not in a Git archive; committed screenshots and evidence are. Keep `runs/`
writable. S / Enter starts; Q / Escape exits. See [setup/package details](README.md).

## Validation and boundaries

555 tests passed; Extension compileall and `git diff --check` passed. Existing
environment dependency checks passed; a fresh-environment installation is not
claimed. A local working-tree source preview with 193 files passed ZIP CRC/content,
extracted imports/resource-path checks; 43 local documentation links and screenshot
hashes were checked. This preview is not the final committed/tagged archive.

The research release `g7-final` stays at
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. Core, experiment meanings, report,
evidence, legacy interaction, sensitivity and configuration remain unchanged.
This application release tag does not change the existing Python Core package
metadata version (`0.1.0`). G9 Product V2 remains stashed/deferred.

## Known limitations

- User-reported flipped-feeling preview and low sensitivity remain documented;
  preview/pointer currently use unmirrored coordinates. Sensitivity Settings
  are deferred after v1.0; no tuning was applied to pass R3.
- Tracking depends on lighting/background/occlusion. Historical false positives
  remain a limitation; this smoke does not prove their absence or reliability.
- Live processing uses Raw/F0. A1 has limited evaluable data; A2 remains
  unavailable. B did not activate adaptive CLAHE in the analyzed windows.
- Screenshots are synthetic presentation captures, not webcam/research evidence.
  The orbit is educational, not a physical simulator. No new quantitative
  performance or commercial-readiness claim is made.

Only commit/tag publication remains after this review. Preserve the frozen G7
identity and keep local environments, model binary, runtime logs and G9 stash
out of the source archive.
