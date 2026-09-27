# AGENTS.md — DIP Touchless STEM

This file is the entry point for AI coding agents and contributors.

It does not redefine project architecture or algorithms.

## 1. Required reading

Before any nontrivial implementation change, read the canonical specifications in this order:

```text
docs/00_GOVERNANCE.md
docs/01_MASTER_SPEC.md
docs/02_ARCHITECTURE_AND_CONTRACTS.md
docs/03_ALGORITHM_AND_EXPERIMENTS.md
docs/04_IMPLEMENTATION_TESTING_GUIDE.md
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

Canonical specifications are the source of truth.

Do not override them with assumptions from this file, README, comments or existing legacy code.

---

## 2. Environment setup

Recommended environment:

```text
Python 3.11
```

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the package and development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
pytest
```

Do not claim the environment or test suite is working unless the relevant commands were actually executed.

---

## 3. Implementation discipline

For every task:

1. inspect the relevant canonical specifications;
2. inspect the current implementation and tests;
3. identify the smallest coherent change;
4. preserve public contracts unless the task explicitly changes them;
5. implement only the requested/current-gate behavior;
6. add or update tests for research-critical behavior;
7. run targeted tests;
8. run broader regression tests when shared components change;
9. inspect `git diff` and `git status`;
10. report what actually changed and what was actually tested.

Do not perform unrelated refactors during a narrow task.

---

## 4. Mandatory project rules

Agents MUST:

- preserve DIP Core / 3D Extension separation;
- preserve Raw and canonical Fixed 1-Euro baselines;
- follow public contracts from `02_ARCHITECTURE_AND_CONTRACTS.md`;
- follow algorithm semantics from `03_ALGORITHM_AND_EXPERIMENTS.md`;
- use explicit color-space and coordinate-space conversions;
- derive filter timing from timestamps as specified;
- keep missing/invalid observations explicit;
- handle tracking loss and reacquisition according to the canonical algorithm spec;
- keep configurable research parameters outside hard-coded business logic;
- preserve deterministic ReplayRuntime behavior for comparable experiments;
- keep experiment outputs reproducible.

---

## 5. Forbidden shortcuts

Agents MUST NOT:

- invent measurement quality or tracking confidence;
- use MediaPipe handedness score as tracking confidence;
- convert missing landmarks to zero-valued landmarks;
- call a derivative-less filter canonical 1-Euro;
- silently change filter equations or parameter meaning;
- silently change ROI/detector geometry;
- silently change public data contracts;
- silently change experiment baselines or protocol;
- fabricate benchmark values or experiment results;
- claim an unexecuted test passed;
- describe model-relative landmark `z` as metric camera depth;
- add YOLO, depth-camera, Transformer, cloud, multi-camera or unrelated large features without an approved scope change;
- couple DIP Core to Pygame/OpenGL scene implementation.

---

## 6. Quantitative claims

The specification contains no required target such as:

```text
FPS >= X
latency <= X ms
jitter reduction >= X%
accuracy >= X%
```

Do not introduce such targets unless an explicit approved specification change requires them.

Any reported numeric result must come from an actual recorded run.

Minimal course evaluation should remain minimal unless the current specification explicitly promotes additional analysis.

Advanced items such as detailed performance benchmarking, inferential statistics or broader ablation must not be turned into mandatory work merely because they could be implemented.

---

## 7. Git discipline

Do not commit generated environments or local experiment artifacts.

Before committing:

```powershell
pytest
git status
git diff
```

Stage only files belonging to the current task when practical:

```powershell
git add <files>
git commit -m "<type>: <description>"
```

Suggested commit prefixes:

```text
chore:
feat:
fix:
test:
docs:
refactor:
```

Do not rewrite shared Git history unless explicitly coordinated with the team.

---

## 8. Stop and surface conflicts

Do not guess when:

- two canonical files conflict materially;
- required provider semantics are unknown;
- a requested behavior violates frozen scope;
- implementing a change would invalidate existing experiment data;
- a required model/config/source file is missing;
- a research-critical test fails because of the proposed change.

Complete unrelated safe work when possible, but surface the conflicting portion clearly.

---

## 9. Current work

Before starting a task, inspect:

```text
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

The current gate/task in that file determines what should be implemented next.

Do not implement future roadmap features merely because they are listed.