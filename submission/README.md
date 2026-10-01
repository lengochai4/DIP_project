# Final submission and application package

This guide covers the final presentation application and its source package.
The frozen scientific report is [FINAL_REPORT.md](../FINAL_REPORT.md); selected
G7 evidence and provenance are in [evidence/README.md](evidence/README.md).
The post-G7 UI does not replace those results or create a new evaluation.

## Setup and run

Use Python 3.11 (the verified interpreter) and a desktop with OpenGL support.
Run all commands from the extracted repository root, not this directory.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,demo3d]"
python -m pip check
```

If PowerShell activation is unavailable, invoke `.\.venv\Scripts\python.exe`
directly instead of `python`; use `-m pytest` for tests.
Install the model using [models/README.md](../models/README.md), including its
SHA-256 check. Do this before an offline presentation; the app does not
automatically download a model.

```powershell
python -m extensions.stem3d.live_demo
```

S / Enter / Space starts from Welcome. Q / Escape or window close exits.
The default camera is index 0. Close other camera applications before starting.
The application loads `config/default.yaml` and the model relative to the
repository, then writes local session output under `runs/`. Keep that location
writable. Startup failures identify the affected component; dismiss the error
and correct the model, camera, graphics or output-directory issue before retrying.
These technical entry points have no conventional `--help` CLI; use F1 in the app.

Optional renderer-only smoke (synthetic interaction, no webcam/model):

```powershell
python -m extensions.stem3d.demo
```

That smoke is not the submission application or physical tracking validation.
See the [application walkthrough](DEMO_GUIDE.md) for keyboard fallback and screenshots.

## Source package contents

| Path | Purpose |
| --- | --- |
| `README.md`, `pyproject.toml`, `AGENTS.md` | Entry instructions, dependencies and project rules |
| `src/dip_touchless/` | DIP Core |
| `extensions/stem3d/` | Final application, scenes, renderer, read-only evidence UI |
| `config/` | Runtime and experiment configuration |
| `tests/` | Automated validation |
| `docs/00` through `docs/06` | Canonical specifications and supplemental UI direction |
| `FINAL_REPORT.md` | Frozen G7 report |
| `submission/` | This guide, application walkthrough/checklist and selected frozen evidence |
| `experiments/`, `analysis/` | Reproducible experiment/analysis tooling; frozen final plans under `experiments/final/` |
| `models/README.md` | External model download and checksum instructions |

Deliver the repository source archive. A wheel alone installs the Core under
`src/`; it does not provide the Extension, config or evidence resources needed
for the final application. Preserve paths when extracting. The ignored model binary is
not in a Git source archive: download it before going offline, or supply a
separate verified local model copy with the source package.

Do not include `.git/`, `.venv/`, caches, local `runs/`, local `data/` or
`results/`, or the deferred G9 stash in the hand-in archive. Raw trial sources
and complete generated run directories are not bundled; the selected evidence
contains metrics/provenance, not enough input data to rerun every trial offline.
Do not regenerate frozen evidence as part of packaging.

After an approved documentation commit, a source-only archive can be produced
from a clean tree (these commands are recommendations, not executed release steps):

```powershell
git status --short
git archive --format=zip --prefix=DIP_project/ --output=../DIP_project-submission.zip HEAD
```

Extract the ZIP elsewhere and repeat setup, model verification and the application
command before distributing it. A ZIP has no Git revision context; preserve
the source commit in the handoff notes. The committed R2 screenshots and frozen
evidence are included by `git archive`. The ignored model and any additional
uncommitted captures are separate additions; they are not automatically included.

## Verification recorded on 2026-10-01

Starting revision: `7bd1ebb` (`feat(stem3d): finalize product presentation`).
This preparation changes documentation only. No dependency installation into
a fresh environment is claimed; the existing Python 3.11 environment was checked.

- `pytest -q` (via `.venv\Scripts\python.exe -m pytest -q`): **555 passed**.
- `python -m compileall extensions/stem3d`: passed.
- `git diff --check`: passed.
- `python -m pip check`: no broken requirements.
- Actual local MediaPipe model initialization and close: passed, without camera.
- A local working-tree source preview with 173 files passed ZIP CRC/content
  checks, extracted Core/application imports and config/evidence path checks. It is
  ignored under `runs/u10-preparation/`, not a final release archive.
- Startup, cancellation, component failure, partial initialization and shutdown
  are covered by existing automated tests; this is not a physical camera smoke.
- Physical webcam smoke (R3, after U10 preparation): **PASS with usability
  limitations**; see [R3_PHYSICAL_SMOKE.md](R3_PHYSICAL_SMOKE.md) for exact runs,
  checklist attribution, orientation/sensitivity feedback and validation.
- Final screenshot capture (R2): 15 synthetic 1600 × 900 presentation captures,
  contact sheet and manifest in [screenshots/](screenshots/README.md).
  Real webcam captures are not included in R2; R3 was separately run physically.

## Provenance and known limitations

The immutable research release `g7-final` resolves to
`f454c6b8325c85199c0122c0e822fe8e76c1526c`. The historical primary G7 live-demo
execution revision `6a87dc50f9d3920ed9fd39a2669e266be00f9735` is distinct from
that release and from the current presentation revision.

- One RGB camera and one hand; no metric camera depth. Handedness scores are
  not tracking confidence. Lighting, occlusion and background can affect tracking.
- Historical G7 live validation recorded occasional face/background false
  positives and unintended rotation. That finding remains; this preparation
  does not demonstrate that final physical interaction is reliable.
- The live entry point explicitly uses Raw/F0 and the legacy GestureEngine.
  Fixed/F1 and Adaptive/F2 are preserved research baselines, not live UI modes.
- A1 has two evaluable trials out of three; one evaluable trial has only five
  frames. The observed F1/F2 reduction versus F0 supports only that limited sample.
- A2 has no evaluable primary metrics (`no_common_usable_frames`); do not claim
  a responsiveness gain or display unavailable values as zero.
- B recorded equal P0/P1 valid-observation rates while adaptive P1 never activated
  CLAHE in the analyzed windows. This does not establish CLAHE ineffectiveness.
- Orbital motion is an educational deterministic visualization, not a physical
  simulator. No new performance or commercial-readiness claim is made.
- G9 Product V2 remains deferred/stashed. No SPACE clutch or replacement gestures
  belong to this final application. Sensitivity and interaction semantics are unchanged.

G8 final desktop application and U10 packaging are complete. The release roadmap
is R1 terminology/docs alignment → R2 final screenshots → R3 final application
smoke → R4 final release/tag. R2 synthetic presentation screenshots are complete;
real webcam captures are not included in R2. R3 physical smoke passed with
documented orientation discomfort and low sensitivity; functional readiness is
READY FOR RELEASE with documented limitations. R4 review is READY TO RELEASE;
commit/tag publication remains pending. See [v1.0 release notes](RELEASE_NOTES_v1.0.md).
Advanced interaction, including the deferred
G9 Product V2 prototype, belongs to the backlog after v1.0 and is not required
for this release. Recommend `dip-touchless-stem-v1.0` after review and release
checks; never move or rewrite `g7-final`.

User-adjustable sensitivity Settings remain a post-v1.0 backlog item; no gains,
thresholds or preview mapping were changed to make R3 pass. R4 review changed
documentation only; no stage, commit, push or tag was performed.
