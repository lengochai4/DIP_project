# DIP Touchless STEM

**Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing and Motion Signal Filtering with a Single RGB Camera**

## 1. Overview

DIP Touchless STEM is a Digital Image Processing final-term project that uses a single RGB webcam for real-time touchless interaction with rendered 3D STEM objects.

The project focuses on the processing pipeline rather than building a feature-heavy 3D application.

Main topics:

- ROI-based image processing;
- illumination assessment;
- adaptive CLAHE;
- hand landmark tracking through MediaPipe;
- canonical Fixed 1-Euro filtering;
- bounded Adaptive 1-Euro filtering;
- gesture mapping;
- renderer-independent `InteractionState`;
- reproducible comparison of Raw / Fixed / Adaptive processing.

The 3D STEM application is an extension/demo layer. The DIP Core is the primary academic component.

---

## 2. Requirements

Recommended development environment:

```text
Python 3.11
Git
Windows PowerShell
```

Python compatibility is defined by `pyproject.toml`.

Do not assume that a globally installed Python package is part of the project environment.

---

## 3. Setup

Clone the repository:

```powershell
git clone https://github.com/lengochai4/DIP_project.git
cd DIP_project
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Verify the environment:

```powershell
python --version
pytest --version
```

Run the test suite:

```powershell
pytest
```

---

## 4. Project structure

```text
DIP_project/
├── src/
│   └── dip_touchless/       # DIP Core package
├── extensions/
│   └── stem3d/              # 3D STEM application layer
├── tests/                   # Automated tests
├── config/                  # Runtime / experiment configuration
├── experiments/             # Experiment runners
├── analysis/                # Metrics, plots and result analysis
├── data/                    # Local/recorded experiment inputs
├── results/                 # Generated experiment results
├── docs/                    # Canonical specifications
├── AGENTS.md                # AI/contributor entry instructions
├── pyproject.toml
└── README.md
```

Generated/local data under `data/`, `results/`, runtime logs and `.venv/` should not be committed unless explicitly required.

---

## 5. Canonical specifications

The README is an introduction only.

Normative project decisions are defined in exactly these six files:

```text
docs/
├── 00_GOVERNANCE.md
├── 01_MASTER_SPEC.md
├── 02_ARCHITECTURE_AND_CONTRACTS.md
├── 03_ALGORITHM_AND_EXPERIMENTS.md
├── 04_IMPLEMENTATION_TESTING_GUIDE.md
└── 05_PROJECT_STATUS_AND_ROADMAP.md
```

Their responsibilities are:

- `00_GOVERNANCE.md` — source-of-truth, precedence and change discipline;
- `01_MASTER_SPEC.md` — scope, non-goals, research questions and contribution boundary;
- `02_ARCHITECTURE_AND_CONTRACTS.md` — architecture, module boundaries and public contracts;
- `03_ALGORITHM_AND_EXPERIMENTS.md` — algorithms, baselines and experiment definitions;
- `04_IMPLEMENTATION_TESTING_GUIDE.md` — implementation gates, testing and coding rules;
- `05_PROJECT_STATUS_AND_ROADMAP.md` — current stage, tasks, risks and Definition of Done.

If this README conflicts with a canonical specification, the canonical specification takes precedence.

---

## 6. Development workflow

The project is developed incrementally by gates:

```text
G0 — Foundation / contracts / config / logging
G1 — Raw + Replay baseline
G2 — DIP preprocessing
G3 — Canonical Fixed 1-Euro
G4 — Bounded Adaptive 1-Euro
G5 — Gesture + 3D STEM extension
G6 — Minimal experiment tooling
G7 — Final evaluation and delivery
```

Do not skip ahead to renderer polish before the DIP Core is stable.

Each meaningful task should follow:

```text
implement
→ run targeted tests
→ inspect git diff/status
→ commit
```

Example:

```powershell
pytest
git status
git diff

git add <task-files>
git commit -m "feat: describe the completed task"
```

Do not claim tests passed unless they were actually executed.

---

## 7. Branch workflow

`main` contains stable shared work.

Each team member should develop on their own branch.

Example:

```text
main
loc
member-a
member-b
```

Typical workflow:

```powershell
git switch loc

# work + commits

pytest
git status
git push
```

For this project, small commits may be kept locally during a gate and pushed when the gate is complete or when a remote backup/share point is needed.

Merge into `main` only after the relevant tests pass and the changes have been reviewed.

---

## 8. Important project rules

- DIP Core is the academic center of the project.
- The 3D application consumes `InteractionState` and must not control Core algorithms directly.
- Raw and canonical Fixed 1-Euro must remain available as baselines.
- Canonical Fixed 1-Euro includes derivative low-pass filtering with `d_cutoff`.
- Missing hand tracking must not be represented by fake zero landmarks.
- Do not invent tracking confidence or measurement quality.
- Handedness score is not tracking confidence.
- Do not silently change algorithm equations, contracts or experiment protocol.
- Do not fabricate FPS, latency, jitter reduction, accuracy or other experimental results.
- Do not add YOLO, depth cameras, Transformers, cloud inference or multi-camera processing unless the project scope is explicitly changed.
- Any quantitative result must come from an actual recorded experiment.

---

## 9. Current status

See:

```text
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

for the current project gate, task, blockers and Definition of Done.

Do not infer implementation completion from this README.