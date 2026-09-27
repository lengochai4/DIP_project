# 00 — Governance

**Specification set:** Canonical v1.2  
**Status:** Normative  
**Project:** DIP Touchless STEM

## 1. Purpose

This file defines how humans and AI agents interpret, change, and implement the project specifications. It is the governance source of truth and supersedes governance/change-control rules scattered across earlier v1.0/v1.1 documents.

The project has exactly six canonical specification files:

```text
docs/
00_GOVERNANCE.md
01_MASTER_SPEC.md
02_ARCHITECTURE_AND_CONTRACTS.md
03_ALGORITHM_AND_EXPERIMENTS.md
04_IMPLEMENTATION_TESTING_GUIDE.md
05_PROJECT_STATUS_AND_ROADMAP.md
```

No additional document is canonical unless this file is explicitly revised.

## 2. Normative language

- **MUST / MUST NOT** — mandatory for compliance.
- **SHOULD / SHOULD NOT** — expected unless a documented reason exists.
- **MAY** — optional.
- **FUTURE** — intentionally outside the current course scope.

Examples, pseudocode, starter parameter values, and repository names are non-normative unless explicitly marked otherwise.

## 3. Source-of-truth ownership

Each normative topic has one owner:

| Topic | Canonical owner |
|---|---|
| governance, precedence, change policy, evidence policy | `00_GOVERNANCE.md` |
| problem, scope, non-goals, RQs, contribution boundary | `01_MASTER_SPEC.md` |
| system boundaries, dependency direction, public data/interface semantics | `02_ARCHITECTURE_AND_CONTRACTS.md` |
| algorithm equations/behavior, baselines, experiment design, metrics/statistics | `03_ALGORITHM_AND_EXPERIMENTS.md` |
| repository/implementation process, testing, quality gates, AI coding rules | `04_IMPLEMENTATION_TESTING_GUIDE.md` |
| current status/task, roadmap, risks, final Definition of Done | `05_PROJECT_STATUS_AND_ROADMAP.md` |

A lower-level file MUST NOT redefine a rule owned by another file. It may only reference it.

## 4. Conflict precedence

When statements conflict, resolve them in this order:

1. safety, correctness, and observed evidence;
2. `00_GOVERNANCE.md`;
3. `01_MASTER_SPEC.md`;
4. `02_ARCHITECTURE_AND_CONTRACTS.md`;
5. `03_ALGORITHM_AND_EXPERIMENTS.md`;
6. `04_IMPLEMENTATION_TESTING_GUIDE.md`;
7. `05_PROJECT_STATUS_AND_ROADMAP.md`.

If a meaningful conflict remains, implementation MUST stop at the ambiguous behavior and the specification MUST be corrected before proceeding. Do not choose silently.

## 5. Frozen decisions requiring explicit spec change

The following MUST NOT change silently:

- research questions or course scope;
- Core vs 3D Extension boundary;
- dependency direction;
- public data-contract semantics;
- coordinate/color/timestamp semantics;
- canonical fixed 1-Euro equations;
- adaptive-filter equation or parameter meaning;
- measurement-quality semantics;
- Raw / Fixed / Adaptive experimental baselines;
- replay pairing policy or statistical unit of analysis;
- experiment metrics used to support a final claim;
- tracking-loss/reacquisition semantics;
- log schema semantics used by final experiments.

A refactor that preserves observable semantics may change internal helper structure without changing the specs.

## 6. Required change record

Any behavior-changing architecture, equation, public-interface, experiment, or schema change MUST record:

```text
Change:
Reason:
Canonical file/section changed:
Code/modules affected:
Algorithmic impact:
Experimental impact:
Compatibility impact:
Tests added/updated:
Existing results invalidated: yes/no + reason
```

A change that alters algorithm behavior, detector/model version, preprocessing semantics, filter parameters, data schema, or experiment protocol may invalidate old results. Invalidated results MUST NOT be mixed into final tables as if equivalent.

## 7. Evidence and claims

No quantitative result may be invented, hard-coded, inferred from visual appearance, or copied from a target expectation.

The following statements require recorded evidence from the documented pipeline:

- FPS or processing latency;
- jitter reduction;
- tracking/detection robustness;
- accuracy or valid-observation rate;
- p-values, confidence intervals, effect sizes;
- claims that one configuration outperforms another.

A successful demo proves only that the demo executed under that condition. It does not prove algorithm superiority.

Final Results/Conclusion claims MUST be traceable:

```text
claim
→ metric
→ analysis output
→ run/trial IDs
→ resolved configuration
→ code/model/schema version
→ source data
```

## 8. Configuration discipline

Any tunable algorithm, gesture, runtime, logging, or experiment parameter MUST be external configuration or an explicit command-line override captured in the resolved run configuration.

Source-code constants MAY be used only for structural facts that are not tuning parameters, such as canonical landmark indices or enum values.

Starter values are engineering defaults, not research findings and not claimed optima.

## 9. External-provider discipline

External-provider semantics MUST NOT be reinterpreted for convenience. The concrete `MeasurementQuality` contract, including what is and is not a valid quality source, is owned only by `02_ARCHITECTURE_AND_CONTRACTS.md`.

## 10. Canonical-algorithm naming discipline

Names MUST match the algorithm actually implemented. The exact criteria for the canonical fixed 1-Euro baseline are owned only by `03_ALGORITHM_AND_EXPERIMENTS.md`. A project-modified variant MUST be labeled as a project variant rather than silently replacing the canonical baseline.

## 11. Scope-control rule

Course scope and non-goals are owned only by `01_MASTER_SPEC.md`. Implementation MUST NOT expand scope to solve unrelated product/research problems without an explicit Master Spec change. Commercial readiness means clean extension seams, not speculative product implementation during the course project.

## 12. Privacy and data defaults

Default processing is local. Raw video storage SHOULD be off unless a specific experiment requires recording and the run configuration states it.

Do not commit secrets or personally identifying research data. Participant/session identifiers, if used, SHOULD be pseudonymous.

## 13. Versioning

The specification version is independent from:

- application/package version;
- log schema version;
- model asset version;
- experiment/run version.

Breaking semantic changes MUST update the appropriate version and document result compatibility.
