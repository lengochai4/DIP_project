# R2 final application screenshots

**R2: COMPLETE using synthetic presentation input.** All 15 full-window captures
are 1600 × 900 PNGs. These are final-application presentation images, separate
from immutable research assets under `../evidence/`.

Source application revision: `760021aab254c930b6eea8ff068ee16d4f53aa75`.
The existing R1 documentation changes were present during capture; application
code was unchanged. Capture date: 2026-10-01 (UTC+7). The exact timestamp,
frame/run identity, image hashes and frozen-asset hashes are in
[manifest.json](manifest.json). [Contact sheet](contact-sheet-synthetic.png).

## Source and interpretation

The capture harness used the existing `ProductDashboard` and
`ApplicationShellRenderer`, rendering the actual scenes and UI to an OpenGL
framebuffer. It supplied a hand-authored 21-point schematic and synthetic
presentation states. No webcam, model inference or research processing ran.
All live diagnostics are fixtures, including illumination, tracking validity,
camera-ready status, pinch values and the displayed 3.3 ms compute time.
They are not measurements, tracking success or performance evidence.
Raw and filtered landmark coordinates are identical for the displayed Raw/F0 path.

Every capture has a visible synthetic label; filenames also include `synthetic`.
The footer annotation comes from the capture harness, not an application change.
Evidence screenshots show original frozen G7 figures/findings through the existing
read-only viewer. Those historical values were neither invented nor regenerated;
“synthetic” describes the viewer capture/input, not the historical research assets.
The No Hand image is an explicitly supplied state, not an observed tracking loss.

## Image index

| Capture | File |
| --- | --- |
| Workspace — Coordinate Geometry | [01](01-workspace-coordinate-geometry-synthetic.png) |
| Workspace — Molecule / Water | [02](02-workspace-water-synthetic.png) |
| Workspace — Molecule / Methane | [03](03-workspace-methane-synthetic.png) |
| Workspace — Orbital | [04](04-workspace-orbital-synthetic.png) |
| Analysis — DIP pipeline / landmarks | [05](05-analysis-pipeline-landmarks-synthetic.png) |
| Evidence — Overview | [06](06-evidence-overview-synthetic.png) |
| Evidence — A1 Static | [07](07-evidence-a1-static-synthetic.png) |
| Evidence — A2 Dynamic / unavailable | [08](08-evidence-a2-dynamic-synthetic.png) |
| Evidence — B Normal | [09](09-evidence-b-normal-synthetic.png) |
| Evidence — B Low-light | [10](10-evidence-b-lowlight-synthetic.png) |
| Evidence — RQ3 / Demo | [11](11-evidence-rq3-dip-synthetic.png) |
| Control Space | [12](12-control-space-synthetic.png) |
| Help | [13](13-help-synthetic.png) |
| No Hand / tracking state | [14](14-no-hand-synthetic.png) |
| Welcome | [15](15-welcome-synthetic.png) |

## Verification and remaining gaps

All images decode at the recorded size; SHA-256 hashes match the manifest.
The complete contact sheet and full-size Analysis, Help and No Hand images were
visually inspected. Frozen report/evidence/experiment files and G9 stash were
checked unchanged. No Core, interaction or UI architecture files were edited.

All requested presentation categories are covered. Real webcam screenshots are
not included. Physical application smoke: **NOT RUN**. The capture harness is
not an R3 startup/interaction/shutdown validation. R3 and R4 were not started;
no release, stage, commit, push or tag was performed.
